import asyncio
import logging
import traceback
import time
import json
import tempfile
import os
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import textwrap
import ast

from ..models import (
    ExecutionPlan, ExecutionResult, ASTNode, ASTNodeType, 
    ParametricIntentionGraph
)

logger = logging.getLogger(__name__)

class SandboxedExecutor:
    """
    A Célula de Execução Segura - Executa código CadQuery em ambiente isolado.
    Converte AST em código Python e executa com limites de recursos.
    """
    
    def __init__(self):
        self.max_execution_time = int(os.getenv("MAX_EXECUTION_TIME", "30"))
        self.max_memory_mb = int(os.getenv("MAX_MEMORY_MB", "512"))
        self.docker_enabled = os.getenv("DOCKER_ENABLED", "false").lower() == "true"
        
        # Templates de código CadQuery
        self.code_templates = self._load_code_templates()
        
        # Diretório para salvar códigos gerados
        self.generated_code_dir = Path("generated_codes")
        self.generated_code_dir.mkdir(exist_ok=True)
        logger.info(f"Códigos gerados serão salvos em: {self.generated_code_dir.absolute()}")
        
    def _save_generated_code(self, python_code: str, session_id: str, plan_id: str = None, context: str = "execution") -> str:
        """
        Salva código Python gerado em arquivo para análise posterior.
        
        Args:
            python_code: Código Python gerado
            session_id: ID da sessão
            plan_id: ID do plano (opcional)
            context: Contexto da geração (execution, pig_update, etc.)
            
        Returns:
            Caminho do arquivo salvo
        """
        try:
            # Criar timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # microsegundos até milissegundos
            
            # Criar nome do arquivo
            plan_suffix = f"_{plan_id[:8]}" if plan_id else ""
            filename = f"{timestamp}_{context}_{session_id[:8]}{plan_suffix}.py"
            
            # Caminho completo
            file_path = self.generated_code_dir / filename
            
            # Criar cabeçalho com metadados
            header = f"""# Código gerado automaticamente pelo CM² Text-to-CAD
# Timestamp: {datetime.now().isoformat()}
# Session ID: {session_id}
# Plan ID: {plan_id or 'N/A'}
# Context: {context}
# ===================================================

"""
            
            # Salvar arquivo
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(header + python_code)
            
            logger.info(f"Código salvo em: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Erro ao salvar código gerado: {e}")
            return ""
    
    def _load_code_templates(self) -> Dict[str, str]:
        """Carrega templates de código com indentação padronizada e ESTÁVEL"""
        return {
            "base_template": '''import cadquery as cq
import json
import sys
import traceback
from typing import Dict, Any

try:
    # Parâmetros
{parameters}
    
    # Operações de modelagem
{operations}
    
    # Extrair informações do modelo
    if 'result' in locals():
        solid = result.val()
        bbox = solid.BoundingBox()
        volume = solid.Volume()
        center_of_mass = cq.Shape.centerOfMass(solid)

        # =========================================================
        # EXPORTAR MESH 3D REAL PARA VISUALIZAÇÃO GENÉRICA
        # =========================================================
        
        # Tesselar o sólido para obter triangulação
        from cadquery import exporters
        import tempfile
        import os
        
        # Exportar como STL temporário e ler vertices/faces
        with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as temp_file:
            temp_path = temp_file.name
            
        try:
            # Exportar como STL
            exporters.export(result, temp_path)
            
            # Ler STL e extrair mesh data
            with open(temp_path, 'rb') as f:
                stl_content = f.read()
                
            # Converter STL para base64 para envio
            import base64
            stl_base64 = base64.b64encode(stl_content).decode('utf-8')
            
        finally:
            # Limpar arquivo temporário
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        model_info = {{
            "type": "solid",
            "bounding_box": {{
                "min": [bbox.xmin, bbox.ymin, bbox.zmin],
                "max": [bbox.xmax, bbox.ymax, bbox.zmax]
            }},
            "volume": volume,
            "center_of_mass": [center_of_mass.x, center_of_mass.y, center_of_mass.z],
            "mesh_data": {{
                "format": "stl",
                "data_base64": stl_base64,
                "vertex_count": "calculated_from_stl",
                "face_count": "calculated_from_stl"
            }},
            "cad_formats": {{
                "step_available": True,
                "iges_available": True,
                "stl_available": True
            }}
        }}

        print("EXECUTION_SUCCESS")
        print(json.dumps(model_info, indent=4))
    else:
        print("EXECUTION_ERROR: Nenhum objeto 'result' foi criado")
        
except Exception as e:
    print(f"EXECUTION_ERROR: {{str(e)}}")
    traceback.print_exc()''',
            
            # Templates para primitivas com indentação correta
            "box": "    {result_id} = cq.Workplane('XY').box({width}, {height}, {depth})",
            "cylinder": "    {result_id} = cq.Workplane('XY').cylinder({height}, {radius})",
            "sphere": "    {result_id} = cq.Workplane('XY').sphere({radius})",
            
            # Templates para operações com indentação correta
            "extrude": "    {result_id} = {target_id}.extrude({distance})",
            "cut": "    {result_id} = {target_id}.cut({cutter})",
            "union": "    {result_id} = {target_id}.union({other})",
            "fillet": "    {result_id} = {target_id}.fillet({radius})",
            "chamfer": "    {result_id} = {target_id}.chamfer({distance})"
        }
    
    async def execute_plan(self, session_id: str, plan: ExecutionPlan) -> ExecutionResult:
        """
        Executa plano de execução completo.
        
        Args:
            session_id: ID da sessão
            plan: Plano de execução a ser executado
            
        Returns:
            Resultado da execução com status e dados do modelo
        """
        start_time = time.time()
        logger.info(f"Iniciando execução do plano {plan.id} para sessão {session_id}")
        
        try:
            # 1. Converter AST para código Python
            logger.debug(f"Convertendo AST para Python. Nós AST: {len(plan.ast_nodes)}")
            python_code = self._ast_to_python(plan, session_id)
            
            # 2. Executar código em ambiente sandboxed
            logger.info(f"Executando código Python gerado...")
            if self.docker_enabled:
                logger.debug("Usando execução em Docker")
                result_data = await self._execute_in_docker(python_code)
            else:
                logger.debug("Usando execução em processo local")
                result_data = await self._execute_in_process(python_code)
            
            logger.info(f"Resultado da execução: {result_data.get('status', 'unknown')}")
            
            execution_time = time.time() - start_time
            
            # 3. Processar resultado
            if result_data.get("status") == "success":
                return ExecutionResult(
                    plan_id=plan.id,
                    status="success",
                    execution_time=execution_time,
                    generated_code=python_code,
                    model_data=result_data.get("model_info"),
                    updated_pig_nodes=plan.affected_operations
                )
            else:
                return ExecutionResult(
                    plan_id=plan.id,
                    status="error",
                    execution_time=execution_time,
                    generated_code=python_code,
                    error_message=result_data.get("error_message"),
                    error_traceback=result_data.get("error_traceback")
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Erro na execução do plano {plan.id}: {e}")
            
            return ExecutionResult(
                plan_id=plan.id,
                status="error",
                execution_time=execution_time,
                error_message=str(e),
                error_traceback=traceback.format_exc()
            )
    
    async def execute_pig_nodes(
        self, session_id: str, node_ids: List[str], pig: ParametricIntentionGraph
    ) -> ExecutionResult:
        """
        Executa nós específicos do PIG (para regeneração paramétrica).
        
        Args:
            session_id: ID da sessão
            node_ids: Lista de IDs dos nós a executar
            pig: Grafo de Intenção Paramétrica
        """
        start_time = time.time()
        
        try:
            # 1. Gerar código para executar apenas os nós especificados
            python_code = self._pig_nodes_to_python(node_ids, pig, session_id)
            
            # 2. Executar código
            if self.docker_enabled:
                result_data = await self._execute_in_docker(python_code)
            else:
                result_data = await self._execute_in_process(python_code)
            
            execution_time = time.time() - start_time
            
            if result_data.get("status") == "success":
                return ExecutionResult(
                    plan_id=f"pig_update_{session_id}",
                    status="success",
                    execution_time=execution_time,
                    generated_code=python_code,
                    model_data=result_data.get("model_info"),
                    updated_pig_nodes=node_ids
                )
            else:
                return ExecutionResult(
                    plan_id=f"pig_update_{session_id}",
                    status="error",
                    execution_time=execution_time,
                    error_message=result_data.get("error_message"),
                    error_traceback=result_data.get("error_traceback")
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                plan_id=f"pig_update_{session_id}",
                status="error",
                execution_time=execution_time,
                error_message=str(e),
                error_traceback=traceback.format_exc()
            )
    
    def _ast_to_python(self, plan: ExecutionPlan, session_id: str = None) -> str:
        """Converte AST do plano para código Python ESTÁVEL e SEM BUGS"""
        
        # NOVA ABORDAGEM: Usar código CadQuery direto se disponível
        if hasattr(plan, 'cadquery_code') and plan.cadquery_code:
            logger.info("🚀 Usando código CadQuery direto do plano - TOTAL LIBERDADE!")
            
            # 1. Gerar código de parâmetros
            parameters_code = self._generate_parameters_code(
                getattr(plan, 'parameters', {}) or plan.new_parameters
            )
            logger.debug(f"Parâmetros: {parameters_code}")
            
            # 2. Processar código CadQuery (substituir \n por quebras de linha reais)
            cadquery_operations = plan.cadquery_code.replace('\\n', '\n')
            
            # 3. Garantir indentação correta (4 espaços)
            cadquery_lines = []
            for line in cadquery_operations.split('\n'):
                if line.strip():
                    # Adicionar indentação se não existir
                    if not line.startswith('    '):
                        line = '    ' + line
                    cadquery_lines.append(line)
                else:
                    cadquery_lines.append('')
            
            operations_code = '\n'.join(cadquery_lines)
            logger.debug(f"Código CadQuery processado: {operations_code[:200]}...")
            
            context = "cadquery_direct"
            
        else:
            # Abordagem tradicional com AST
            logger.info("Usando abordagem tradicional AST")
            
            # 1. Gerar código de parâmetros (sempre com 4 espaços de indentação)
            parameters_code = self._generate_parameters_code(plan.new_parameters)
            logger.debug(f"Código de parâmetros gerado: {parameters_code}")
            
            # 2. Gerar código de operações (sempre com 4 espaços de indentação)
            operations_code = self._generate_operations_code(plan.ast_nodes)
            logger.debug(f"Código de operações gerado: {operations_code}")
            
            context = "ast_execution"
        
        # 3. Construir código final - TEMPLATE JÁ TEM INDENTAÇÃO CORRETA
        python_code = self.code_templates["base_template"].format(
            parameters=parameters_code,
            operations=operations_code
        )
        
        logger.info(f"✅ Código Python gerado com {context}")
        logger.debug(f"Preview do código:\n{python_code[:300]}...")
        
        # 4. Salvar código gerado
        if session_id:
            saved_path = self._save_generated_code(
                python_code, 
                session_id, 
                plan.id, 
                context
            )
            logger.info(f"Código salvo: {saved_path}")
        
        return python_code
    
    def _pig_nodes_to_python(self, node_ids: List[str], pig: ParametricIntentionGraph, session_id: str = None) -> str:
        """Converte nós do PIG para código Python ESTÁVEL e SEM BUGS"""
        
        # Obter ordem de execução
        execution_order = pig.get_execution_order()
        
        # Filtrar apenas os nós solicitados e suas dependências
        nodes_to_execute = set(node_ids)
        for node_id in node_ids:
            # Adicionar dependências
            node = pig.nodes[node_id]
            nodes_to_execute.update(node.dependencies)
        
        # Ordenar nós
        ordered_nodes = [nid for nid in execution_order if nid in nodes_to_execute]
        
        # Gerar código para parâmetros
        parameters = {}
        operations = []
        
        for node_id in ordered_nodes:
            node = pig.nodes[node_id]
            
            if node.node_type.value == "parameter":
                parameters[node.name] = node.value
            elif node.node_type.value == "operation":
                operations.append(node)
        
        # Gerar código - SEMPRE COM INDENTAÇÃO CORRETA
        parameters_code = self._generate_parameters_code(parameters)
        operations_code = self._generate_pig_operations_code(operations)
        
        python_code = self.code_templates["base_template"].format(
            parameters=parameters_code,
            operations=operations_code
        )
        
        # Salvar código gerado
        if session_id:
            node_ids_str = "_".join(node_ids[:3])  # Primeiros 3 IDs para identificação
            saved_path = self._save_generated_code(
                python_code, 
                session_id, 
                f"pig_{node_ids_str}", 
                "pig_update"
            )
            logger.info(f"Código PIG salvo: {saved_path}")
        
        return python_code
    
    def _generate_parameters_code(self, parameters: Dict[str, Any]) -> str:
        """Gera código de parâmetros com INDENTAÇÃO SEMPRE CORRETA (4 espaços)"""
        if not parameters:
            return "    # Nenhum parâmetro definido"
            
        lines = []
        for name, value in parameters.items():
            if isinstance(value, str):
                lines.append(f'    {name} = "{value}"')
            else:
                lines.append(f'    {name} = {value}')
        
        return "\n".join(lines)
    
    def _generate_operations_code(self, ast_nodes: List[ASTNode]) -> str:
        """Gera código de operações com INDENTAÇÃO SEMPRE CORRETA (4 espaços)"""
        if not ast_nodes:
            return "    # Nenhuma operação definida"
            
        lines = []
        primitives = []
        
        # Primeira passada: gerar código para primitivas e operações
        for i, node in enumerate(ast_nodes):
            if node.node_type == ASTNodeType.PRIMITIVE:
                # Atribuir um ID único para cada primitiva
                result_id = f"primitive_{i}" if i > 0 else "result"
                node.result_id = result_id
                primitives.append(result_id)
                
                line = self._generate_primitive_code(node)
            elif node.node_type == ASTNodeType.OPERATION:
                line = self._generate_operation_code(node)
            else:
                continue
            
            if line:
                lines.append(line)
        
        # Se há múltiplas primitivas, adicionar união automaticamente
        if len(primitives) > 1:
            union_line = f"    result = {primitives[0]}"
            for prim_id in primitives[1:]:
                union_line += f".union({prim_id})"
            lines.append(union_line)
        
        return "\n".join(lines)
    
    def _generate_pig_operations_code(self, operation_nodes: List) -> str:
        """Gera código de operações a partir dos nós do PIG com indentação correta"""
        if not operation_nodes:
            return "    # Nenhuma operação definida"
            
        lines = []
        
        for node in operation_nodes:
            if hasattr(node, 'cadquery_code') and node.cadquery_code:
                # Garantir que o código do PIG tem indentação correta
                code_line = node.cadquery_code.strip()
                if not code_line.startswith('    '):
                    code_line = '    ' + code_line
                lines.append(code_line)
        
        return "\n".join(lines)
    
    def _generate_primitive_code(self, node: ASTNode) -> str:
        """Gera código para primitivas geométricas com indentação correta"""
        operation = node.operation
        params = node.parameters.copy()
        
        if operation in self.code_templates:
            template = self.code_templates[operation]
            
            # Determinar result_id (se não especificado, usar 'result')
            result_id = getattr(node, 'result_id', None) or params.get('result_id', 'result')
            params['result_id'] = result_id
            
            # Mapear parâmetros para nomenclatura CadQuery
            if operation == "cylinder":
                params['height'] = params.get('height', params.get('param_cylinder_height', 10))
                params['radius'] = params.get('radius', params.get('param_cylinder_radius', 5))
            elif operation == "box":
                params['width'] = params.get('width', params.get('param_base_width', 10))
                params['height'] = params.get('height', params.get('param_base_height', 10))
                params['depth'] = params.get('depth', params.get('param_base_depth', 10))
            elif operation == "sphere":
                params['radius'] = params.get('radius', params.get('param_sphere_radius', 5))
            
            # Substituir parâmetros no template
            try:
                return template.format(**params)
            except KeyError as e:
                logger.error(f"Parâmetro ausente no template {operation}: {e}")
                logger.error(f"Parâmetros disponíveis: {list(params.keys())}")
                return f"    # ERRO: Parâmetro ausente para {operation}: {e}"
        
        return f"    # ERRO: Template não encontrado para {operation}"
    
    def _generate_operation_code(self, node: ASTNode) -> str:
        """Gera código para operações de modelagem com indentação correta"""
        operation = node.operation
        params = node.parameters.copy()
        
        if operation in self.code_templates:
            template = self.code_templates[operation]
            
            # Determinar result_id e target_id
            result_id = getattr(node, 'result_id', None) or params.get('result_id', 'result')
            target_id = getattr(node, 'target_id', None) or params.get('target_id', 'result')
            
            params['result_id'] = result_id
            params['target_id'] = target_id
            
            # Substituir parâmetros no template
            try:
                return template.format(**params)
            except KeyError as e:
                logger.error(f"Parâmetro ausente no template {operation}: {e}")
                return f"    # ERRO: Parâmetro ausente para {operation}: {e}"
        
        return f"    # ERRO: Template não encontrado para {operation}"
    
    async def _execute_in_docker(self, python_code: str) -> Dict[str, Any]:
        """Executa código em container Docker isolado"""
        # Implementação simplificada - em produção usar Docker API
        return await self._execute_in_process(python_code)
    
    async def _execute_in_process(self, python_code: str) -> Dict[str, Any]:
        """Executa código em processo Python isolado"""
        
        logger.info(f"Iniciando execução do código em processo isolado")
        logger.debug(f"Tamanho do código: {len(python_code)} caracteres")
        
        try:
            # Criar arquivo temporário com o código
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(python_code)
                temp_file = f.name
            
            logger.debug(f"Código salvo em arquivo temporário: {temp_file}")
            
            # Executar com timeout
            logger.debug(f"Criando subprocess Python para executar {temp_file}")
            process = await asyncio.create_subprocess_exec(
                'python', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tempfile.gettempdir()
            )
            logger.debug(f"Subprocess criado, aguardando execução...")
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=self.max_execution_time
                )
                
                # Processar saída
                output = stdout.decode('utf-8')
                error = stderr.decode('utf-8')
                
                logger.debug(f"Execução concluída. Return code: {process.returncode}")
                logger.debug(f"STDOUT: {output[:200]}..." if len(output) > 200 else f"STDOUT: {output}")
                if error:
                    logger.debug(f"STDERR: {error[:200]}..." if len(error) > 200 else f"STDERR: {error}")
                
                if "EXECUTION_SUCCESS" in output:
                    # Extrair informações do modelo - JSON pode ser multilinha
                    lines = output.strip().split('\n')
                    model_info_lines = []
                    
                    # Encontrar início do JSON após EXECUTION_SUCCESS
                    start_collecting = False
                    for line in lines:
                        if "EXECUTION_SUCCESS" in line:
                            start_collecting = True
                            continue
                        if start_collecting:
                            model_info_lines.append(line)
                    
                    logger.info(f"Resultado da execução: success")
                    logger.debug(f"Linhas do model_info coletadas: {len(model_info_lines)}")
                    
                    model_info = {}
                    if model_info_lines:
                        try:
                            # Juntar todas as linhas para formar o JSON completo
                            model_info_text = '\n'.join(model_info_lines)
                            logger.debug(f"JSON completo extraído: {model_info_text[:200]}...")
                            
                            model_info = json.loads(model_info_text)
                            logger.debug(f"model_info parsed com sucesso: chaves = {list(model_info.keys())}")
                        except Exception as e:
                            logger.error(f"Erro ao fazer parse do model_info: {e}")
                            logger.error(f"JSON original: {model_info_text}")
                    else:
                        logger.warning("Nenhuma linha de model_info encontrada após EXECUTION_SUCCESS")
                    
                    return {
                        "status": "success",
                        "model_info": model_info,
                        "output": output
                    }
                else:
                    return {
                        "status": "error",
                        "error_message": error or "Erro desconhecido na execução",
                        "error_traceback": output + "\n" + error
                    }
                    
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "status": "error",
                    "error_message": f"Execução excedeu tempo limite de {self.max_execution_time}s",
                    "error_traceback": "TimeoutError"
                }
            
        except Exception as e:
            return {
                "status": "error",
                "error_message": str(e),
                "error_traceback": traceback.format_exc()
            }
        
        finally:
            # Limpar arquivo temporário
            try:
                os.unlink(temp_file)
            except:
                pass 