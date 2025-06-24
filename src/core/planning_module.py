import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
import textwrap
import re
import requests
import asyncio

from ..models import (
    LLMQuery, LLMResponse, ExecutionPlan, ASTNode, 
    ASTNodeType, OperationType, ValidationResult
)

load_dotenv()
logger = logging.getLogger(__name__)

def safe_json_dumps(obj, **kwargs):
    """Serialização JSON segura que lida com objetos datetime"""
    def default_serializer(o):
        if isinstance(o, datetime):
            return o.isoformat()
        # Para objetos Pydantic, usar .model_dump() ao invés de serialização direta
        if hasattr(o, 'model_dump'):
            return o.model_dump()
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")
    
    return json.dumps(obj, default=default_serializer, **kwargs)

class PlanningModule:
    """
    Módulo de Planejamento - Interface com LLMs (Gemini e Ollama) para gerar planos de ação.
    Converte linguagem natural em árvores de execução abstratas (AST).
    """
    
    def __init__(self):
        # Configuração do provider de LLM
        self.llm_provider = os.getenv("LLM_PROVIDER", "gemini").lower()  # gemini ou ollama
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "")
        self.ollama_timeout = int(os.getenv("OLLAMA_TIMEOUT", "600"))  # 10 minutos por padrão
        
        # Configuração Gemini (manter compatibilidade)
        self.api_key = os.getenv("GEMINI_API_KEY")
        
        # Inicializar o provider selecionado
        if self.llm_provider == "ollama":
            self._initialize_ollama()
        else:
            self._initialize_gemini()
        
        # Documentação da API CadQuery disponível para o LLM
        self.cadquery_api_docs = self._load_cadquery_api_docs()
        
        # Diretório para salvar respostas do LLM
        self.llm_responses_dir = Path("llm_responses")
        self.llm_responses_dir.mkdir(exist_ok=True)
        logger.info(f"Respostas do LLM serão salvas em: {self.llm_responses_dir.absolute()}")
        
    def _initialize_gemini(self):
        """Inicializa configuração do Gemini"""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY não encontrada nas variáveis de ambiente")
        
        genai.configure(api_key=self.api_key)
        
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.1,
            response_mime_type="application/json",
            max_output_tokens=15000
        )

        self.current_model_name = 'gemini-2.5-flash'
        self.model = genai.GenerativeModel(
            self.current_model_name,
            generation_config=self.generation_config
        )
        
        logger.info(f"🤖 GEMINI INITIALIZED - Model: {self.current_model_name}")
        
    def _initialize_ollama(self):
        """Inicializa configuração do Ollama"""
        # Verificar se modelo foi configurado
        if not self.ollama_model:
            raise ValueError("OLLAMA_MODEL não configurado. Configure OLLAMA_MODEL no arquivo .env com o nome do modelo desejado.")
        
        self.current_model_name = self.ollama_model
        
        # Ollama não usa generation_config, mas vamos criar um placeholder para compatibilidade
        self.generation_config = None
        self.model = None  # Ollama não precisa de objeto model
        
        # Verificar se Ollama está disponível
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                available_models = response.json().get('models', [])
                model_names = [model.get('name', '') for model in available_models]
                
                logger.info(f"📋 OLLAMA - Modelos disponíveis: {model_names}")
                
                # Verificar se o modelo solicitado está disponível
                if self.current_model_name not in model_names:
                    logger.error(f"❌ OLLAMA - Modelo '{self.current_model_name}' não encontrado")
                    logger.info(f"💡 OLLAMA - Para instalar o modelo, execute:")
                    logger.info(f"   ollama pull {self.current_model_name}")
                    
                    # Tentar usar o primeiro modelo disponível como fallback
                    if model_names:
                        self.current_model_name = model_names[0]
                        logger.info(f"🔄 OLLAMA - Usando modelo fallback: {self.current_model_name}")
                    else:
                        raise ValueError("Nenhum modelo disponível no Ollama. Execute 'ollama pull <modelo>' para instalar um modelo.")
                
                logger.info(f"🤖 OLLAMA INITIALIZED - Model: {self.current_model_name}")
                logger.info(f"🌐 OLLAMA - Server: {self.ollama_base_url}")
                
            else:
                raise ValueError(f"Ollama não disponível em {self.ollama_base_url}. Verifique se o serviço está rodando com 'ollama serve'")
                
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Erro ao conectar com Ollama em {self.ollama_base_url}: {e}. Verifique se o Ollama está rodando com 'ollama serve'")
        
    def _save_llm_interaction(self, prompt: str, response: str, context: str = "plan_generation") -> str:
        """
        Salva interação com LLM (prompt + resposta) em arquivo para análise.
        
        Args:
            prompt: Prompt enviado ao LLM
            response: Resposta recebida do LLM
            context: Contexto da interação
            
        Returns:
            Caminho do arquivo salvo
        """
        try:
            # Criar timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            
            # Criar nome do arquivo
            filename = f"{timestamp}_{context}_{self.llm_provider}.json"
            file_path = self.llm_responses_dir / filename
            
            # Criar estrutura de dados
            interaction_data = {
                "timestamp": datetime.now().isoformat(),
                "context": context,
                "llm_provider": self.llm_provider,
                "model": self.current_model_name,
                "prompt": prompt,
                "response": response,
                "prompt_length": len(prompt),
                "response_length": len(response)
            }
            
            # Salvar arquivo JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(interaction_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Interação {self.llm_provider.upper()} salva: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Erro ao salvar interação {self.llm_provider.upper()}: {e}")
            return ""
    
    def _load_cadquery_api_docs(self) -> str:
        """Carrega documentação abrangente da API CadQuery para contexto do LLM"""
        return """
        # CadQuery API Completa para Engenharia Mecânica

        ## Primitivas Básicas:
        - cq.Workplane().box(width, height, depth) - Cria caixa
        - cq.Workplane().cylinder(height, radius) - Cria cilindro (altura, raio)
        - cq.Workplane().sphere(radius) - Cria esfera
        - cq.Workplane().cone(height, radius1, radius2) - Cria cone truncado
        - cq.Workplane().wedge(dx, dy, dz, xminorp, xmajorp, yminorp, ymajorp) - Cria cunha

        ## Sketching e Perfis 2D:
        - .rect(width, height) - Retângulo
        - .circle(radius) - Círculo
        - .ellipse(a, b) - Elipse (semi-eixos a, b)
        - .polygon(nSides, diameter) - Polígono regular
        - .slot2D(length, diameter) - Slot/ranhura 2D
        - .spline(listOfXYTuples) - Spline através de pontos
        - .polyline(listOfXYTuples) - Polilinha
        - .bezier(listOfXYTuples) - Curva Bézier
        - .parametricCurve(func, start, stop) - Curva paramétrica

        ## Workplanes Avançados:
        - .workplane(offset=distance) - Novo plano paralelo com offset
        - .workplane(origin=(x,y,z), normal=(x,y,z)) - Plano arbitrário
        - .rotateAboutCenter((x,y,z), angle) - Rotacionar workplane
        - .transformed(rotate=(rx,ry,rz), offset=(x,y,z)) - Transformação combinada
        - .faces(selector) - Selecionar faces (">Z", "<X", etc.)
        - .edges(selector) - Selecionar arestas
        - .vertices(selector) - Selecionar vértices

        ## Operações 3D Avançadas:
        - .extrude(distance, combine=True/False) - Extrusão linear
        - .revolve(angleDegrees, axisStart=(x,y,z), axisEnd=(x,y,z)) - Revolução em eixo arbitrário
        - .loft(otherProfile, ruled=False) - Transição suave entre perfis
        - .sweep(path) - Extrusão ao longo de caminho
        - .shell(thickness, faces=None) - Cria casca oca
        - .thicken(thickness) - Espessar superfície

        ## Operações Booleanas:
        - .cut(object) - Subtração booleana
        - .union(object) - União booleana
        - .intersect(object) - Interseção booleana
        - .combine() - Combinar com workplane atual

        ## Modificações e Acabamentos:
        - .fillet(radius) - Filete em arestas selecionadas
        - .chamfer(distance) - Chanfro em arestas
        - .chamfer(distance, distance2) - Chanfro assimétrico
        - .mirror(mirrorPlane="XY"/"XZ"/"YZ") - Espelhar objeto
        - .mirror(mirrorPlane=(px,py,pz,nx,ny,nz)) - Espelhar em plano arbitrário
        
        ## FILETES SEGUROS - Melhores Práticas:
        ```python
        # MÉTODO SEGURO - Calcular raio máximo permitido
        max_radius = min(height/2, (outer_diameter - inner_diameter)/4)
        safe_radius = min(desired_radius, max_radius)
        
        # SELEÇÃO SEGURA - Usar .edges() sem seletor específico
        filleted_part = base_part.edges().fillet(safe_radius)
        
        # ALTERNATIVA - Selecionar por face primeiro
        filleted_part = base_part.faces(">Z").edges().fillet(safe_radius)
        ```

        ## Padrões e Arrays:
        - .rarray(xSpacing, ySpacing, xCount, yCount, centerLast=False) - Padrão retangular
        - .polarArray(radius, startAngle, angle, count) - Padrão polar/circular
        - .cboreHole(diameter, cboreDiameter, cboreDepth, depth) - Furo escareado
        - .cskHole(diameter, cskDiameter, cskAngle, depth) - Furo chanfrado
        - .hole(diameter, depth) - Furo simples

        ## Transformações:
        - .translate((x, y, z)) - Translação
        - .rotate((x,y,z), (x,y,z), angle) - Rotação em eixo arbitrário
        - .scale(factor) - Escala uniforme
        - .scale(xFactor, yFactor, zFactor) - Escala não-uniforme

        ## Componentes Mecânicos Especializados:

        ### Roscas (Threads):
        ```python
        # Rosca externa (parafuso)
        thread = (cq.Workplane("XY")
                 .cylinder(thread_length, major_diameter/2)
                 .faces(">Z")
                 .workplane()
                 .parametricCurve(lambda t: (
                     (major_diameter/2 - thread_depth*t) * math.cos(t * pitch_factor),
                     (major_diameter/2 - thread_depth*t) * math.sin(t * pitch_factor),
                     t * thread_pitch
                 ), 0, thread_length * pitch_factor)
                 .sweep(thread_profile))
        
        # Rosca interna (porca)
        internal_thread = external_thread.mirror("XY").translate((0,0,offset))
        ```

        ### Engrenagens:
        ```python
        # Engrenagem dente de involuta
        gear = (cq.Workplane("XY")
               .parametricCurve(involute_curve_function, 0, 2*math.pi)
               .extrude(gear_width)
               .polarArray(radius=0, startAngle=0, angle=360, count=num_teeth))
        ```

        ### Molas:
        ```python
        # Mola helicoidal
        spring = (cq.Workplane("XY")
                 .parametricCurve(lambda t: (
                     spring_radius * math.cos(t),
                     spring_radius * math.sin(t),
                     t * spring_pitch
                 ), 0, spring_turns * 2 * math.pi)
                 .sweep(wire_profile))
        ```

        ## Seletores Seguros e Confiáveis:
        - ">X", "<X", ">Y", "<Y", ">Z", "<Z" - Faces nas direções cardinais (CONFIÁVEL)
        - ">X[1]" - Segunda face na direção +X (CONFIÁVEL)
        - "#Z" - Faces paralelas ao plano Z (CONFIÁVEL)
        - "%CIRCLE" - Faces circulares (CONFIÁVEL)
        - "%PLANE" - Faces planas (CONFIÁVEL)
        
        ## ATENÇÃO - Seletores de Arestas Problemáticos:
        - EVITAR: "|X", "|Y", "|Z" - Podem falhar em geometrias complexas
        - USAR: .edges() sem seletor específico para filetes seguros
        - ALTERNATIVA: .edges(">Z") para arestas de faces específicas

        ## Medições e Análise:
        - .val() - Obter valor numérico (área, volume, etc.)
        - .BoundingBox() - Caixa delimitadora
        - .Center() - Centro de massa
        - .Volume() - Volume do sólido
        - .Area() - Área de superfície

        ## Operações com Assemblies:
        ```python
        # Assembly com múltiplos componentes
        assembly = cq.Assembly()
        assembly.add(part1, name="base", loc=cq.Location((0,0,0)))
        assembly.add(part2, name="cover", loc=cq.Location((0,0,height)))
        assembly.constrain("base", "cover", "Fixed")
        ```

        ## Exemplos de Componentes Mecânicos Reais:

        ### Parafuso Phillips M6x25:
        ```python
        # Cabeça Phillips
        head_diameter = 10.0
        head_height = 4.0
        phillips_depth = 2.0
        
        screw = (cq.Workplane("XY")
                .cylinder(head_height, head_diameter/2)
                .faces(">Z").workplane()
                .rect(phillips_depth/3, phillips_depth).cutBlind(-phillips_depth*0.8)
                .rect(phillips_depth, phillips_depth/3).cutBlind(-phillips_depth*0.8)
                .faces("<Z").workplane()
                .cylinder(25, 3)  # Corpo M6
                # Adicionar rosca helicoidal
                .thread(6, 1.0, 25))  # M6x1.0 pitch
        ```

        ### Rolamento 6200:
        ```python
        bearing_od = 30.0
        bearing_id = 10.0  
        bearing_width = 9.0
        ball_diameter = 4.0
        
        outer_ring = (cq.Workplane("XY")
                     .cylinder(bearing_width, bearing_od/2)
                     .cylinder(bearing_width, (bearing_od-ball_diameter)/2, combine=False))
        
        balls = (cq.Workplane("XY")
                .center((bearing_od-ball_diameter)/2, 0)
                .sphere(ball_diameter/2)
                .polarArray(0, 0, 360, 8))
        
        bearing = outer_ring.union(balls).union(inner_ring)
        ```

        ### Chave Inglesa:
        ```python
        # Cabo com perfil ergonômico
        handle = (cq.Workplane("XY")
                 .spline([(0,8), (50,12), (100,10), (150,8)])
                 .revolve(360))
        
        # Cabeça ajustável com rosca sem-fim
        head = (cq.Workplane("XY")
               .rect(30, 15).extrude(20)
               .faces(">Z").workplane()
               .hole(12)  # Para a rosca de ajuste
               .cut(movable_jaw))
        ```

        ## Parâmetros SEMPRE Nomeados:
        ```python
        # CORRETO - usar variáveis nomeadas
        bolt_diameter = 8.0
        bolt_length = 25.0
        head_diameter = 12.0
        
        bolt = cq.Workplane("XY").cylinder(bolt_length, bolt_diameter/2)
        
        # INCORRETO - valores hardcoded
        bolt = cq.Workplane("XY").cylinder(25, 4)  # Nunca fazer assim!
        ```

        ## Convenções de Nomeação:
        - Dimensões em mm (padrão internacional)
        - Nomes descritivos: thread_pitch, gear_module, bearing_bore
        - Constantes em MAIÚSCULAS: STEEL_DENSITY, MAX_STRESS
        - Prefixos por tipo: bolt_, gear_, bearing_, spring_

        Esta documentação permite criar componentes mecânicos profissionais com CadQuery.
        """
    
    async def generate_plan(self, query: Dict[str, Any]) -> LLMResponse:
        """
        Gera plano de execução baseado na consulta do usuário.
        
        Args:
            query: Consulta estruturada contendo contexto e requisição
        """
        try:
            # Log do modelo atual sendo usado
            logger.info(f"🎯 PLANNING - Using {self.llm_provider.upper()} with model: {self.current_model_name}")
            
            # Para Ollama, sempre usar o modelo configurado, ignorar frontend
            if self.llm_provider == "ollama":
                # Não permitir mudança de modelo via frontend quando usando Ollama
                if query.get('model_choice') and query.get('model_choice') != self.current_model_name:
                    logger.warning(f"⚠️  OLLAMA - Ignorando seleção do frontend '{query.get('model_choice')}', usando modelo configurado: {self.current_model_name}")
            else:
                # Para Gemini, permitir mudança via frontend
                model_choice = query.get('model_choice') or self.current_model_name
                if model_choice != self.current_model_name:
                    self._initialize_model(model_choice)

            # Construir prompt estruturado para o LLM
            prompt = self._build_prompt(query)
            
            # Fazer chamada para o LLM
            response = await self._call_llm(prompt, "plan_generation")
            
            # Parsear resposta do LLM
            llm_response = self._parse_llm_response(response)
            
            # Validar plano de execução se presente
            if llm_response.execution_plan:
                validation = self._validate_execution_plan(llm_response.execution_plan)
                if not validation.is_valid:
                    logger.warning(f"Plano inválido: {validation.errors}")
                    # Tentar auto-correção
                    llm_response = await self._auto_correct_plan(
                        query, llm_response, validation
                    )
            
            logger.info(f"✅ PLANNING - Successfully generated plan using {self.llm_provider.upper()}")
            return llm_response
            
        except Exception as e:
            logger.error(f"❌ PLANNING ERROR - {self.llm_provider.upper()}: {e}")
            return LLMResponse(
                intention_type="error",
                response_text=f"Erro interno do sistema de planejamento: {str(e)}",
                requires_clarification=False
            )
    
    def _build_prompt(self, query: Dict[str, Any]) -> str:
        """Constrói prompt estruturado para o LLM com schema JSON definido"""
        
        # Schema JSON expandido para permitir código CadQuery direto
        json_schema = {
            "type": "object",
            "properties": {
                "intention_type": {
                    "type": "string",
                    "enum": ["creation", "modification", "query", "error"]
                },
                "response_text": {
                    "type": "string",
                    "description": "Resposta em linguagem natural para o usuário"
                },
                "execution_plan": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "description": {"type": "string"},
                        "cadquery_code": {
                            "type": "string",
                            "description": "Código CadQuery puro e completo para executar"
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Dicionário de parâmetros nomeados"
                        },
                        "ast_nodes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "node_type": {
                                        "type": "string",
                                        "enum": ["primitive", "operation", "parameter"]
                                    },
                                    "operation": {"type": "string"},
                                    "parameters": {"type": "object"},
                                    "position": {
                                        "type": "object",
                                        "properties": {
                                            "x": {"type": "number"},
                                            "y": {"type": "number"},
                                            "z": {"type": "number"}
                                        }
                                    },
                                    "children": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "metadata": {"type": "object"}
                                },
                                "required": ["id", "node_type", "operation", "parameters"]
                            }
                        },
                        "new_parameters": {"type": "object"},
                        "affected_operations": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                },
                "parameter_updates": {"type": "object"},
                "requires_clarification": {"type": "boolean"},
                "clarification_questions": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                }
            },
            "required": ["intention_type", "response_text"]
        }
        
        if query.get('request_type') == 'error_correction':
            prompt = self._build_error_correction_prompt(query)
            return prompt

        prompt_body = textwrap.dedent(f"""
            # ROLE: Expert CAD Design Assistant with CadQuery

            ## User Request
            {query.get('user_request', '')}

            ## Conversation History
            {self._format_conversation_history(query.get('conversation_history', []))}

            ## Current Model State
            {safe_json_dumps(query.get('current_model_state'), indent=2) if query.get('current_model_state') else 'No active model'}

            ## Available CadQuery Operations
            {self.cadquery_api_docs}

            # THINKING PROCESS (Chain-of-Thought):
            Before generating the JSON response, think through these steps:
            1. **Analyze Request**: What does the user want to create or modify?
            2. **Identify Type**: Is this creation, modification, query, or error handling?
            3. **Plan Operations**: What CadQuery operations are needed?
            4. **Parameter Setup**: What parameters should be configurable?
            5. **Validation**: Does this plan make geometric sense?

            # FEW-SHOT EXAMPLES:

            ## Example 1 - Simple Cylinder with Direct CadQuery Code:
            User Request: "Create a cylinder with radius 10 and height 20"
            
            Correct JSON Response:
            {{
                "intention_type": "creation",
                "response_text": "I'll create a cylinder with the specified dimensions using parametric CadQuery code.",
                "execution_plan": {{
                    "id": "cylinder_creation_001",
                    "description": "Create parametric cylinder",
                    "cadquery_code": "result = cq.Workplane('XY').cylinder(cylinder_height, cylinder_radius)",
                    "parameters": {{
                        "cylinder_height": 20.0,
                        "cylinder_radius": 10.0
                    }},
                    "ast_nodes": [],
                    "new_parameters": {{
                        "cylinder_height": 20.0,
                        "cylinder_radius": 10.0
                    }},
                    "affected_operations": []
                }},
                "parameter_updates": {{}},
                "requires_clarification": false,
                "clarification_questions": [],
                "confidence": 0.95
            }}

            ## Example 2 - Screw with Safe Fillet:
            User Request: "Create a screw with curved head using fillet"
            
            Correct JSON Response:
            {{
                "intention_type": "creation",
                "response_text": "I'll create a screw with a curved head using safe fillet techniques.",
                "execution_plan": {{
                    "id": "safe_fillet_screw",
                    "description": "Create screw with safe fillet on head",
                    "cadquery_code": "# Create screw body\\nscrew_body = cq.Workplane('XY').cylinder(body_length, body_diameter/2)\\n\\n# Create screw head\\nscrew_head = cq.Workplane('XY').cylinder(head_height, head_diameter/2)\\n\\n# Calculate safe fillet radius\\nsafe_fillet_radius = min(fillet_radius, head_height/2, (head_diameter - body_diameter)/4)\\n\\n# Apply safe fillet to head edges\\nscrew_head = screw_head.edges().fillet(safe_fillet_radius)\\n\\n# Position head on body\\nscrew_head = screw_head.translate((0, 0, body_length))\\n\\n# Combine parts\\nresult = screw_body.union(screw_head)",
                    "parameters": {{
                        "body_diameter": 6.0,
                        "body_length": 20.0,
                        "head_diameter": 10.0,
                        "head_height": 4.0,
                        "fillet_radius": 2.0
                    }},
                    "ast_nodes": [],
                    "new_parameters": {{
                        "body_diameter": 6.0,
                        "body_length": 20.0,
                        "head_diameter": 10.0,
                        "head_height": 4.0,
                        "fillet_radius": 2.0
                    }},
                    "affected_operations": []
                }},
                "parameter_updates": {{}},
                "requires_clarification": false,
                "clarification_questions": [],
                "confidence": 0.95
            }}

            ## Example 3 - Bearing with Advanced CadQuery Operations:
            User Request: "Create a ball bearing 6200 with outer ring, inner ring, and balls"
            
            Correct JSON Response:
            {{
                "intention_type": "creation",
                "response_text": "I'll create a complete ball bearing 6200 with all components.",
                "execution_plan": {{
                    "id": "bearing_6200_complete",
                    "description": "Create ball bearing with outer ring, inner ring, and balls",
                    "cadquery_code": "import math\\n\\n# Outer ring\\nouter_ring = (cq.Workplane('XY')\\n              .cylinder(bearing_width, bearing_od/2)\\n              .cylinder(bearing_width, (bearing_od - ball_diameter)/2, combine=False))\\n\\n# Inner ring\\ninner_ring = (cq.Workplane('XY')\\n              .cylinder(bearing_width, (bearing_id + ball_diameter)/2)\\n              .cylinder(bearing_width, bearing_id/2, combine=False))\\n\\n# Ball pitch circle\\npitch_radius = (bearing_od - bearing_id - ball_diameter) / 2 + bearing_id/2\\n\\n# Create single ball\\nball = cq.Workplane('XY').sphere(ball_diameter/2)\\n\\n# Create array of balls\\nballs = (cq.Workplane('XY')\\n         .center(pitch_radius, 0)\\n         .sphere(ball_diameter/2)\\n         .polarArray(radius=0, startAngle=0, angle=360, count=num_balls))\\n\\n# Combine all components\\nresult = outer_ring.union(inner_ring).union(balls)",
                    "parameters": {{
                        "bearing_od": 30.0,
                        "bearing_id": 10.0,
                        "bearing_width": 9.0,
                        "ball_diameter": 4.0,
                        "num_balls": 8
                    }},
                    "ast_nodes": [],
                    "new_parameters": {{
                        "bearing_od": 30.0,
                        "bearing_id": 10.0,
                        "bearing_width": 9.0,
                        "ball_diameter": 4.0,
                        "num_balls": 8
                    }},
                    "affected_operations": []
                }},
                "parameter_updates": {{}},
                "requires_clarification": false,
                "clarification_questions": [],
                "confidence": 0.85
            }}

            ## Example 4 - Cilindro com Furo Contextual (TÉCNICA CORRETA):
            User Request: "Create a cylinder with a hole through it"
            
            Correct JSON Response:
            {{
                "intention_type": "creation",
                "response_text": "I'll create a cylinder with a contextual hole using proper face selection to ensure correct positioning.",
                "execution_plan": {{
                    "id": "contextual_hole_cylinder",
                    "description": "Create cylinder with contextual hole using face selection",
                    "cadquery_code": "# Create cylinder with base on XY plane (not centered)\\nbase_cylinder = cq.Workplane('XY').cylinder(cylinder_height, cylinder_radius, centered=False)\\n\\n# Select top face and create contextual hole\\nresult = base_cylinder.faces('>Z').hole(hole_diameter)",
                    "parameters": {{
                        "cylinder_height": 40.0,
                        "cylinder_radius": 20.0,
                        "hole_diameter": 8.0
                    }},
                    "ast_nodes": [],
                    "new_parameters": {{
                        "cylinder_height": 40.0,
                        "cylinder_radius": 20.0,
                        "hole_diameter": 8.0
                    }},
                    "affected_operations": []
                }},
                "parameter_updates": {{}},
                "requires_clarification": false,
                "clarification_questions": [],
                "confidence": 0.95
            }}

            # JSON SCHEMA TO FOLLOW:
            {json.dumps(json_schema, indent=2)}

            # CRITICAL INSTRUCTIONS:
            1. **Output Format**: Return ONLY valid JSON - no markdown, no code blocks, no extra text
            2. **CadQuery Code**: Use the "cadquery_code" field for direct CadQuery Python code
            3. **Parameter Names**: Always use descriptive variable names, never hardcoded values
            4. **Code Freedom**: You have TOTAL FREEDOM to use any CadQuery operations from the API documentation
            5. **Complex Geometries**: Feel free to create sophisticated mechanical components with multiple operations
            6. **Code Structure**: Use \\n for line breaks in cadquery_code, create intermediate variables as needed
            7. **Final Result**: Always assign the final geometry to a variable named 'result'
            8. **Imports**: Include necessary imports like 'import math' if needed within the cadquery_code
            9. **Real Engineering**: Create actual engineering components, not simplified primitives
            10. **FILETES SEGUROS**: SEMPRE use .edges() sem seletores específicos para filetes, e calcule raio máximo seguro
            11. **EVITAR SELETORES**: NUNCA use "|X", "|Y", "|Z" para arestas - use .edges() ou .faces().edges()
            
            # PROBLEMA CRÍTICO: AMBIGUIDADE DO "MODELO MENTAL" vs. LÓGICA DO CÓDIGO
            12. **FUROS CONTEXTUAIS**: Ao gerar código CadQuery para adicionar furos ou recortes, SEMPRE que possível, selecione primeiro a face de referência (ex: .faces('>Z')) antes de aplicar a operação (.hole(), .cut(), etc.). Isso garante que a operação seja aplicada corretamente em relação à geometria existente.
            
            **Exemplo CORRETO para furos:**
            ```
            # 1. Criar cilindro com base no plano (não centralizado)
            base_cylinder = cq.Workplane("XY").cylinder(height, radius, centered=False)
            
            # 2. Selecionar face superior e fazer furo contextual
            result = base_cylinder.faces(">Z").hole(hole_diameter)
            ```
            
            **Exemplo INCORRETO (evitar):**
            ```
            # PROBLEMA: Furo "no vácuo" sem contexto da geometria
            cylinder = cq.Workplane("XY").cylinder(height, radius)
            hole = cq.Workplane("XY").hole(diameter)  # Posição ambígua!
            result = cylinder.cut(hole)
            ```
            
            13. **POSICIONAMENTO EXPLÍCITO**: Para geometrias que devem apoiar em uma base (como cilindros com furos), use `centered=False` para posicionar a base no plano XY, eliminando ambiguidade de coordenadas.
            
            14. **OPERAÇÕES RELACIONAIS**: Sempre que uma operação depende de outra geometria existente (furos, chanfros, filetes), use seletores de face/aresta (.faces(">Z"), .edges()) para estabelecer contexto geométrico claro.

            Provide a response in JSON only.
        """).strip()

        return prompt_body
    
    def _build_error_correction_prompt(self, query: Dict[str, Any]) -> str:
        """Constrói prompt específico para correção de erros usando Chain-of-Thought"""
        return textwrap.dedent(f"""
            # ROLE: Expert CAD Error Diagnostician & Plan Corrector
            You are a specialized assistant for debugging and correcting CAD execution plans in CadQuery.
            Your expertise includes analyzing error messages and generating corrected execution plans.

            # ERROR ANALYSIS CONTEXT:
            ## Original Plan That Failed:
            {safe_json_dumps(query.get('original_plan', {}), indent=2)}

            ## Error Message:
            {query.get('error_message', '')}

            ## Stack Trace:
            {query.get('error_traceback', '')}

            ## Available CadQuery API:
            {self.cadquery_api_docs}

            # THINKING PROCESS (Chain-of-Thought):
            Before generating the corrected JSON response, think through these steps:
            1. **Error Analysis**: What specific error occurred and why?
            2. **Root Cause**: What in the original plan caused this error?
            3. **API Validation**: Are we using CadQuery operations correctly?
            4. **Parameter Check**: Are all required parameters present and valid?
            5. **Logic Review**: Does the geometric operation sequence make sense?
            6. **Correction Strategy**: What specific changes are needed?

            # COMMON ERROR PATTERNS & FIXES:

            ## Pattern 1 - Fillet Edge Selection Errors:
            Error: "Fillets requires that edges be selected"
            Fix: Use .edges() without specific selectors, calculate safe radius
            Example: "geometry.edges().fillet(safe_radius)"

            ## Pattern 2 - Missing Parameters:
            Error: "missing 1 required positional argument"
            Fix: Add missing parameters to the operation

            ## Pattern 3 - Incorrect API Usage:
            Error: "centerOfMass() missing argument"
            Fix: Use correct API method like solid.centerOfMass() or CenterOfBoundBox()

            ## Pattern 4 - Invalid Object References:
            Error: "object has no attribute"
            Fix: Ensure target objects exist before operations

            ## Pattern 5 - Syntax Errors:
            Error: "expected 'except' or 'finally' block"
            Fix: Check code structure and indentation
            
            ## CRITICAL FILLET SAFETY RULES:
            - NEVER use "|X", "|Y", "|Z" selectors for edges
            - ALWAYS calculate safe_radius = min(desired_radius, dimension_constraints)
            - USE .edges() without selectors for reliable fillet application

            # CORRECTION INSTRUCTIONS:
            1. **Output Format**: Return ONLY valid JSON - no markdown, no code blocks, no extra text
            2. **Preserve Intent**: Keep the original geometric intention intact
            3. **Fix Specific Error**: Address the exact error identified
            4. **Validate Logic**: Ensure the corrected plan makes geometric sense
            5. **Parameter Safety**: Use only valid CadQuery parameters

            # YOUR TASK:
            Analyze the error systematically using the thinking process above, then generate a corrected JSON execution plan that resolves the specific error while maintaining the original design intent.
            
            Return ONLY the corrected JSON response, no additional text.
        """).strip()
    
    def _format_conversation_history(self, history: List[Dict]) -> str:
        """Formata histórico da conversa para o prompt"""
        if not history:
            return "Nenhuma conversa anterior."
        
        formatted = []
        for msg in history[-5:]:  # Últimas 5 mensagens
            role = "Usuário" if msg.get('message_type') == 'user_input' else "Sistema"
            content = msg.get('content', '')
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
    
    async def _call_llm(self, prompt: str, context: str = "plan_generation") -> str:
        """Faz chamada assíncrona para o LLM"""
        try:
            logger.info(f"Enviando prompt para {self.llm_provider.upper()} (contexto: {context})")
            
            if self.llm_provider == "ollama":
                response_text = await self._call_ollama(prompt)
            else:
                response_text = await self._call_gemini(prompt)
            
            logger.info(f"Resposta recebida do {self.llm_provider.upper()}: {len(response_text)} caracteres")
            
            # Salvar interação para análise
            self._save_llm_interaction(prompt, response_text, context)
            
            return response_text
        except Exception as e:
            logger.error(f"Erro na chamada do {self.llm_provider.upper()}: {e}")
            raise
    
    async def _call_ollama(self, prompt: str) -> str:
        """Faz chamada assíncrona para o Ollama com streaming para debug"""
        try:
            logger.info(f"⏱️  OLLAMA - Using timeout: {self.ollama_timeout} seconds")
            logger.info(f"📝 OLLAMA - Prompt length: {len(prompt)} characters")
            
            # Construir payload para Ollama com streaming
            payload = {
                "model": self.current_model_name,
                "prompt": prompt,
                "stream": True,  # Habilitar streaming para debug
                "options": {
                    "temperature": 0.1,
                    "num_predict": 15000,
                    "top_p": 0.9,
                    "top_k": 40
                }
            }
            
            logger.info(f"🚀 OLLAMA - Starting request to {self.ollama_base_url}/api/generate")
            logger.info(f"🤖 OLLAMA - Model: {self.current_model_name}")
            
            # Fazer requisição assíncrona com streaming
            loop = asyncio.get_event_loop()
            
            def make_streaming_request():
                """Função para fazer requisição com streaming"""
                import time
                start_time = time.time()
                
                try:
                    response = requests.post(
                        f"{self.ollama_base_url}/api/generate",
                        json=payload,
                        timeout=self.ollama_timeout,
                        stream=True  # Habilitar streaming
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"❌ OLLAMA - HTTP Error {response.status_code}: {response.text}")
                        raise ValueError(f"Ollama retornou status {response.status_code}: {response.text}")
                    
                    logger.info(f"✅ OLLAMA - Connection established, starting to receive data...")
                    
                    # Processar resposta em streaming
                    full_response = ""
                    chunk_count = 0
                    last_log_time = time.time()
                    
                    for line in response.iter_lines():
                        if line:
                            chunk_count += 1
                            current_time = time.time()

                            print("current line received: ", line)
                            
                            # Log progresso a cada 5 segundos
                            if current_time - last_log_time > 5:
                                elapsed = current_time - start_time
                                logger.info(f"⏳ OLLAMA - Receiving data... {chunk_count} chunks, {elapsed:.1f}s elapsed")
                                logger.info(f"📊 OLLAMA - Response so far: {len(full_response)} chars")
                                last_log_time = current_time
                            
                            try:
                                chunk_data = json.loads(line.decode('utf-8'))
                                
                                # Verificar se há erro no chunk
                                if 'error' in chunk_data:
                                    logger.error(f"❌ OLLAMA - Error in chunk: {chunk_data['error']}")
                                    raise ValueError(f"Ollama error: {chunk_data['error']}")
                                
                                # Adicionar resposta parcial
                                if 'response' in chunk_data:
                                    partial_response = chunk_data['response']
                                    full_response += partial_response
                                    
                                    # Log primeira resposta
                                    if chunk_count == 1:
                                        logger.info(f"🎉 OLLAMA - First response chunk received: '{partial_response[:50]}...'")
                                
                                # Verificar se terminou
                                if chunk_data.get('done', False):
                                    total_time = time.time() - start_time
                                    logger.info(f"✅ OLLAMA - Stream completed in {total_time:.1f}s")
                                    logger.info(f"📈 OLLAMA - Total chunks: {chunk_count}")
                                    logger.info(f"📝 OLLAMA - Final response length: {len(full_response)} chars")
                                    break
                                    
                            except json.JSONDecodeError as e:
                                logger.warning(f"⚠️  OLLAMA - Invalid JSON chunk: {line[:100]}...")
                                continue
                    
                    if not full_response:
                        logger.error("❌ OLLAMA - No response received from stream")
                        raise ValueError("Ollama retornou resposta vazia")
                    
                    logger.info(f"🎯 OLLAMA - Response preview: '{full_response[:100]}...'")
                    return full_response
                    
                except requests.exceptions.Timeout:
                    elapsed = time.time() - start_time
                    logger.error(f"⏰ OLLAMA - Timeout after {elapsed:.1f}s (limit: {self.ollama_timeout}s)")
                    raise
                except requests.exceptions.ConnectionError as e:
                    logger.error(f"🔌 OLLAMA - Connection error: {e}")
                    raise
                except Exception as e:
                    elapsed = time.time() - start_time
                    logger.error(f"💥 OLLAMA - Unexpected error after {elapsed:.1f}s: {e}")
                    raise
            
            # Executar requisição em thread separada
            response_text = await loop.run_in_executor(None, make_streaming_request)
            
            logger.info(f"✅ OLLAMA - Request completed successfully")
            return response_text
            
        except requests.exceptions.Timeout:
            logger.error(f"⏰ OLLAMA - Request timed out after {self.ollama_timeout} seconds")
            logger.error("💡 OLLAMA - Try increasing OLLAMA_TIMEOUT or using a smaller model")
            raise ValueError(f"Ollama timeout após {self.ollama_timeout} segundos. Considere aumentar OLLAMA_TIMEOUT no .env ou usar um modelo menor.")
        except requests.exceptions.RequestException as e:
            logger.error(f"🔌 OLLAMA - Connection error: {e}")
            raise ValueError(f"Erro de conexão com Ollama: {e}")
        except Exception as e:
            logger.error(f"💥 OLLAMA - Unexpected error: {e}")
            raise ValueError(f"Erro na chamada Ollama: {e}")
    
    async def _call_gemini(self, prompt: str) -> str:
        """Faz chamada assíncrona para o Gemini"""
        try:
            # Gemini não é nativamente async, então executamos em thread
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.model.generate_content, prompt
            )
            
            return response.text
            
        except Exception as e:
            raise ValueError(f"Erro na chamada Gemini: {e}")
    
    def _parse_llm_response(self, response_text: str) -> LLMResponse:
        """Parseia resposta JSON estruturada do LLM com validação robusta"""
        try:
            # Limpar resposta de possíveis artefatos
            cleaned_response = self._clean_json_response(response_text)
            
            # Validar se é JSON válido
            try:
                data = json.loads(cleaned_response)
            except json.JSONDecodeError as e:
                logger.error(f"JSON inválido recebido do Gemini: {e}")
                logger.error(f"Resposta limpa: {cleaned_response[:5000]}...")
                return self._create_error_response("Resposta do Gemini não é JSON válido")
            
            # Validar estrutura mínima
            if not isinstance(data, dict):
                logger.error("Resposta não é um objeto JSON")
                return self._create_error_response("Formato de resposta inválido")
            
            # Validar campos obrigatórios
            required_fields = ["intention_type", "response_text"]
            for field in required_fields:
                if field not in data:
                    logger.error(f"Campo obrigatório ausente: {field}")
                    return self._create_error_response(f"Campo '{field}' ausente na resposta")
            
            # Construir ExecutionPlan se presente e válido
            execution_plan = None
            if data.get('execution_plan') and isinstance(data['execution_plan'], dict):
                try:
                    execution_plan = self._build_execution_plan(data['execution_plan'])
                except Exception as e:
                    logger.error(f"Erro ao construir execution_plan: {e}")
                    # Continuar sem execution_plan ao invés de falhar
            
            # Construir LLMResponse com validação de tipos
            response = LLMResponse(
                intention_type=str(data.get('intention_type', 'unknown')),
                execution_plan=execution_plan,
                parameter_updates=dict(data.get('parameter_updates', {})),
                response_text=str(data.get('response_text', '')),
                confidence=float(data.get('confidence', 0.5)) if data.get('confidence') is not None else None,
                requires_clarification=bool(data.get('requires_clarification', False)),
                clarification_questions=list(data.get('clarification_questions', []))
            )

            logger.info(f"Resposta do {self.llm_provider.upper()} parseada com sucesso: {response.intention_type}")
            return response
            
        except Exception as e:
            logger.error(f"Erro inesperado ao parsear resposta do Gemini: {e}")
            logger.error(f"Resposta original: {response_text[:5000]}...")
            return self._create_error_response(f"Erro interno: {str(e)}")
    
    def _clean_json_response(self, response_text: str) -> str:
        """
        Extrai JSON da resposta do LLM usando múltiplas estratégias robustas.
        Baseado em melhores práticas de engenharia de prompt para parsing de structured output.
        """
        if not response_text:
            return "{}"
        
        logger.debug(f"Limpando resposta (tamanho: {len(response_text)})")
        
        # Estratégia 1: Remover markdown code blocks
        cleaned = response_text.strip()
        
        # Remover ```json ou ``` no início
        cleaned = re.sub(r'^```(?:json|JSON)?\s*\n?', '', cleaned, flags=re.MULTILINE)
        # Remover ``` no final
        cleaned = re.sub(r'\n?\s*```\s*$', '', cleaned, flags=re.MULTILINE)
        
        # Estratégia 2: Extrair JSON usando regex mais robusta
        # Procurar por estruturas JSON válidas (balanceadas)
        json_patterns = [
            # Padrão 1: JSON completo do início ao fim da string
            r'^\s*(\{.*\})\s*$',
            # Padrão 2: JSON em qualquer lugar da string
            r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})',
            # Padrão 3: JSON multi-linha com indentação
            r'(\{(?:[^{}]|(?:\{[^{}]*\}))*\})'
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, cleaned, re.DOTALL | re.MULTILINE)
            if matches:
                # Pegar o match mais longo (mais provável de ser o JSON completo)
                potential_json = max(matches, key=len) if isinstance(matches[0], str) else matches[0]
                
                # Validar se é JSON válido
                try:
                    json.loads(potential_json)
                    logger.debug("JSON válido encontrado usando regex")
                    return potential_json.strip()
                except json.JSONDecodeError:
                    continue
        
        # Estratégia 3: Tentar balancear chaves manualmente
        try:
            json_candidate = self._extract_balanced_json(cleaned)
            if json_candidate:
                json.loads(json_candidate)  # Validar
                logger.debug("JSON válido encontrado por balanceamento de chaves")
                return json_candidate
        except json.JSONDecodeError:
            pass
        
        # Estratégia 4: Tentar extrair linha por linha
        lines = cleaned.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('{'):
                # Tentar construir JSON a partir desta linha
                remaining_lines = '\n'.join(lines[i:])
                try:
                    json_candidate = self._extract_balanced_json(remaining_lines)
                    if json_candidate:
                        json.loads(json_candidate)
                        logger.debug("JSON válido encontrado linha por linha")
                        return json_candidate
                except json.JSONDecodeError:
                    continue
        
        # Estratégia 5: Se tudo falhar, tentar usar o texto original limpo
        if cleaned.strip().startswith('{') and cleaned.strip().endswith('}'):
            try:
                json.loads(cleaned)
                logger.debug("Usando texto original como JSON")
                return cleaned
            except json.JSONDecodeError:
                pass
        
        logger.warning("Não foi possível extrair JSON válido da resposta")
        logger.debug(f"Texto original: {response_text[:5000]}...")
        
        # Retornar JSON de erro como fallback
        return json.dumps({
            "intention_type": "error",
            "response_text": "Erro: Não foi possível extrair JSON válido da resposta do LLM",
            "requires_clarification": True,
            "clarification_questions": ["Por favor, reformule sua solicitação de forma mais específica."]
        })
    
    def _extract_balanced_json(self, text: str) -> str:
        """Extrai JSON balanceado (chaves abertas = chaves fechadas) do texto"""
        text = text.strip()
        if not text.startswith('{'):
            return ""
        
        brace_count = 0
        start_found = False
        
        for i, char in enumerate(text):
            if char == '{':
                brace_count += 1
                start_found = True
            elif char == '}':
                brace_count -= 1
                
                # Se chegamos a 0 e já começamos, encontramos o JSON completo
                if start_found and brace_count == 0:
                    return text[:i+1]
        
        return ""
    
    def _build_execution_plan(self, plan_data: Dict[str, Any]) -> ExecutionPlan:
        """Constrói ExecutionPlan com validação robusta"""
        # Validar e construir AST nodes
        ast_nodes = []
        for node_data in plan_data.get('ast_nodes', []):
            try:
                # Validar campos obrigatórios do nó
                required_node_fields = ["id", "node_type", "operation", "parameters"]
                for field in required_node_fields:
                    if field not in node_data:
                        raise ValueError(f"Campo obrigatório '{field}' ausente no nó AST")
                
                # Construir nó AST
                ast_node = ASTNode(
                    id=str(node_data['id']),
                    node_type=ASTNodeType(node_data['node_type']),
                    operation=str(node_data['operation']),
                    parameters=dict(node_data['parameters']),
                    children=list(node_data.get('children', [])),
                    metadata=dict(node_data.get('metadata', {}))
                )
                ast_nodes.append(ast_node)
                
            except Exception as e:
                logger.error(f"Erro ao construir nó AST: {e}")
                logger.error(f"Dados do nó: {node_data}")
                # Pular nó inválido ao invés de falhar completamente
                continue
        
        return ExecutionPlan(
            id=str(plan_data.get('id', '')),
            description=str(plan_data.get('description', '')),
            ast_nodes=ast_nodes,
            new_parameters=dict(plan_data.get('new_parameters', {})),
            affected_operations=list(plan_data.get('affected_operations', [])),
            # Incluir novos campos para código CadQuery direto
            cadquery_code=plan_data.get('cadquery_code'),
            parameters=plan_data.get('parameters')
        )
    
    def _create_error_response(self, error_message: str) -> LLMResponse:
        """Cria resposta de erro padronizada"""
        return LLMResponse(
            intention_type="error",
            response_text=f"Erro ao processar resposta: {error_message}",
            requires_clarification=False
        )
    
    def _validate_execution_plan(self, plan: ExecutionPlan) -> ValidationResult:
        """Valida plano de execução antes da execução"""
        errors = []
        warnings = []
        
        for node in plan.ast_nodes:
            # Validar tipo de nó
            if node.node_type not in [e.value for e in ASTNodeType]:
                errors.append({
                    "node_id": node.id,
                    "error_type": "invalid_node_type",
                    "message": f"Tipo de nó inválido: {node.node_type}"
                })
            
            # Validar operações
            if node.node_type == ASTNodeType.OPERATION:
                if not node.operation:
                    errors.append({
                        "node_id": node.id,
                        "error_type": "missing_operation",
                        "message": "Nó de operação sem operação especificada"
                    })
            
            # Validar parâmetros obrigatórios
            if node.operation == "cylinder":
                required_params = ["radius", "height"]
                for param in required_params:
                    if param not in node.parameters:
                        errors.append({
                            "node_id": node.id,
                            "error_type": "missing_parameter",
                            "message": f"Parâmetro obrigatório '{param}' ausente"
                        })
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def _auto_correct_plan(
        self, original_query: Dict, failed_response: LLMResponse, validation: ValidationResult
    ) -> LLMResponse:
        """Tenta auto-correção do plano baseado nos erros de validação"""
        
        correction_query = {
            **original_query,
            "request_type": "validation_correction",
            "original_plan": failed_response.execution_plan.model_dump() if failed_response.execution_plan else None,
            "validation_errors": [error for error in validation.errors]
        }
        
        corrected_prompt = f"""
            O plano gerado tem erros de validação. Corrija-os:

            ## PLANO ORIGINAL:
            {safe_json_dumps(correction_query.get('original_plan'), indent=2)}

            ## ERROS DE VALIDAÇÃO:
            {safe_json_dumps(correction_query.get('validation_errors'), indent=2)}

            Gere um plano corrigido no mesmo formato JSON.
            """
        
        try:
            response = await self._call_llm(corrected_prompt, "auto_correction")

            return self._parse_llm_response(response)
        except Exception as e:
            logger.error(f"Erro na auto-correção: {e}")
            return failed_response  # Retorna original se não conseguir corrigir 

    def _initialize_model(self, model_name: str):
        """Inicializa modelo específico (compatibilidade com código existente)"""
        if self.llm_provider == "ollama":
            # Para Ollama, apenas atualizar o nome do modelo
            old_model = self.current_model_name
            self.current_model_name = model_name
            logger.info(f"🔄 OLLAMA - Model changed from {old_model} to {model_name}")
        else:
            # Para Gemini, recriar o modelo
            try:
                self.current_model_name = model_name
                self.model = genai.GenerativeModel(
                    model_name,
                    generation_config=self.generation_config
                )
                logger.info(f"🔄 GEMINI - Model changed to {model_name}")
            except Exception as e:
                logger.error(f"❌ GEMINI - Error changing model to {model_name}: {e}")
                # Manter modelo anterior em caso de erro
                raise 