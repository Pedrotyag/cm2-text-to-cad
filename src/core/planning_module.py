import os
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
import textwrap
import re

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
    Módulo de Planejamento - Interface com o Gemini para gerar planos de ação.
    Converte linguagem natural em árvores de execução abstratas (AST).
    """
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
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
        
        # Documentação da API CadQuery disponível para o LLM
        self.cadquery_api_docs = self._load_cadquery_api_docs()
        
        # Diretório para salvar respostas do Gemini
        self.gemini_responses_dir = Path("gemini_responses")
        self.gemini_responses_dir.mkdir(exist_ok=True)
        logger.info(f"Respostas do Gemini serão salvas em: {self.gemini_responses_dir.absolute()}")
        
    def _save_gemini_interaction(self, prompt: str, response: str, context: str = "plan_generation") -> str:
        """
        Salva interação com Gemini (prompt + resposta) em arquivo para análise.
        
        Args:
            prompt: Prompt enviado ao Gemini
            response: Resposta recebida do Gemini
            context: Contexto da interação
            
        Returns:
            Caminho do arquivo salvo
        """
        try:
            # Criar timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            
            # Criar nome do arquivo
            filename = f"{timestamp}_{context}.json"
            file_path = self.gemini_responses_dir / filename
            
            # Criar estrutura de dados
            interaction_data = {
                "timestamp": datetime.now().isoformat(),
                "context": context,
                "prompt": prompt,
                "response": response,
                "model": self.current_model_name,
                "prompt_length": len(prompt),
                "response_length": len(response)
            }
            
            # Salvar arquivo JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(interaction_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Interação Gemini salva: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Erro ao salvar interação Gemini: {e}")
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
            model_choice = query.get('model_choice') or self.current_model_name
            if model_choice != self.current_model_name:
                self._initialize_model(model_choice)

            # Construir prompt estruturado para o Gemini
            prompt = self._build_prompt(query)
            
            # Fazer chamada para o Gemini
            response = await self._call_gemini(prompt, "plan_generation")
            
            # Parsear resposta do Gemini
            llm_response = self._parse_gemini_response(response)
            
            # Validar plano de execução se presente
            if llm_response.execution_plan:
                validation = self._validate_execution_plan(llm_response.execution_plan)
                if not validation.is_valid:
                    logger.warning(f"Plano inválido: {validation.errors}")
                    # Tentar auto-correção
                    llm_response = await self._auto_correct_plan(
                        query, llm_response, validation
                    )
            
            return llm_response
            
        except Exception as e:
            logger.error(f"Erro ao gerar plano: {e}")
            return LLMResponse(
                intention_type="error",
                response_text=f"Erro interno do sistema de planejamento: {str(e)}",
                requires_clarification=False
            )
    
    def _build_prompt(self, query: Dict[str, Any]) -> str:
        """Constrói prompt estruturado para o Gemini com schema JSON definido"""
        
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

            ## JSON Schema
            {json.dumps(json_schema)}

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
    
    async def _call_gemini(self, prompt: str, context: str = "plan_generation") -> str:
        """Faz chamada assíncrona para o Gemini"""
        try:
            import asyncio
            logger.info(f"Enviando prompt para Gemini (contexto: {context})")
            
            # Gemini não é nativamente async, então executamos em thread
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.model.generate_content, prompt
            )
            
            response_text = response.text
            logger.info(f"Resposta recebida do Gemini: {len(response_text)} caracteres")
            
            # Salvar interação para análise
            self._save_gemini_interaction(prompt, response_text, context)
            
            return response_text
        except Exception as e:
            logger.error(f"Erro na chamada do Gemini: {e}")
            raise
    
    def _parse_gemini_response(self, response_text: str) -> LLMResponse:
        """Parseia resposta JSON estruturada do Gemini com validação robusta"""
        try:
            # Limpar resposta de possíveis artefatos
            cleaned_response = self._clean_json_response(response_text)
            
            # Validar se é JSON válido
            try:
                data = json.loads(cleaned_response)
            except json.JSONDecodeError as e:
                logger.error(f"JSON inválido recebido do Gemini: {e}")
                logger.error(f"Resposta limpa: {cleaned_response[:500]}...")
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

            logger.info(f"Resposta do Gemini parseada com sucesso: {response.intention_type}")
            return response
            
        except Exception as e:
            logger.error(f"Erro inesperado ao parsear resposta do Gemini: {e}")
            logger.error(f"Resposta original: {response_text[:200]}...")
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
        logger.debug(f"Texto original: {response_text[:300]}...")
        
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
            response = await self._call_gemini(corrected_prompt, "auto_correction")

            return self._parse_gemini_response(response)
        except Exception as e:
            logger.error(f"Erro na auto-correção: {e}")
            return failed_response  # Retorna original se não conseguir corrigir 

    def _initialize_model(self, model_name: str):
        self.current_model_name = model_name
        self.model = genai.GenerativeModel(
            model_name,
            generation_config=self.generation_config
        ) 