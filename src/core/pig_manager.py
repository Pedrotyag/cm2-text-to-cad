import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import re
import json

from ..models import (
    ParametricIntentionGraph, PIGNode, ParameterNode, OperationNode,
    NodeType, ParameterType, ExecutionPlan, ExecutionResult
)

logger = logging.getLogger(__name__)

class PIGManager:
    """
    Gerenciador do Grafo de Intenção Paramétrica (PIG).
    A alma do modelo - mantém a representação semântica das intenções de design.
    """
    
    def __init__(self):
        # Armazenamento em memória (em produção, usar persistência)
        self.graphs: Dict[str, ParametricIntentionGraph] = {}
        # Histórico de versões para cada sessão
        self.version_history: Dict[str, List[Dict[str, Any]]] = {}
        # Cache de códigos gerados
        self.generated_code_cache: Dict[str, str] = {}
        
        # Diretório de códigos gerados (compartilhado com SandboxedExecutor)
        self.generated_code_dir = Path("generated_codes")
        
    async def initialize_empty_graph(self, session_id: str):
        """Inicializa PIG vazio para uma nova sessão"""
        self.graphs[session_id] = ParametricIntentionGraph()
        self.version_history[session_id] = []
        logger.info(f"PIG inicializado para sessão {session_id}")
    
    async def get_graph(self, session_id: str) -> ParametricIntentionGraph:
        """Retorna o PIG da sessão"""
        if session_id not in self.graphs:
            await self.initialize_empty_graph(session_id)
        return self.graphs[session_id]
    
    async def get_graph_state(self, session_id: str) -> Dict[str, Any]:
        """Retorna estado serializado do PIG"""
        pig = await self.get_graph(session_id)
        
        return {
            "nodes": {node_id: self._serialize_node(node) for node_id, node in pig.nodes.items()},
            "execution_order": pig.execution_order,
            "root_nodes": list(pig.root_nodes),
            "parameters": self._extract_parameters(pig),
            "operations": self._extract_operations(pig),
            "version_history": self.version_history.get(session_id, []),
            "latest_generated_file": await self._get_latest_generated_file(session_id)
        }
    
    async def update_from_execution_plan(
        self, session_id: str, plan: ExecutionPlan, result: ExecutionResult
    ):
        """
        Atualiza PIG baseado no plano de execução e resultado.
        Adiciona novos parâmetros e operações ao grafo.
        """
        pig = await self.get_graph(session_id)
        
        try:
            # 1. Adicionar novos parâmetros
            for param_name, param_value in plan.new_parameters.items():
                await self._add_parameter_to_pig(pig, param_name, param_value)
            
            # 2. Adicionar operações do AST
            for ast_node in plan.ast_nodes:
                await self._add_ast_node_to_pig(pig, ast_node, plan.new_parameters)
            
            # 3. Recalcular ordem de execução
            pig.get_execution_order()
            
            logger.info(f"PIG atualizado com {len(plan.ast_nodes)} nós para sessão {session_id}")
            
        except Exception as e:
            logger.error(f"Erro ao atualizar PIG: {e}")
            raise
    
    async def add_parameter(
        self, 
        session_id: str, 
        name: str, 
        value: Any, 
        param_type: ParameterType = ParameterType.NUMERIC,
        description: str = None,
        units: str = None,
        min_value: float = None,
        max_value: float = None
    ) -> str:
        """Adiciona um parâmetro ao PIG"""
        pig = await self.get_graph(session_id)
        
        param_node = ParameterNode(
            name=name,
            value=value,
            parameter_type=param_type,
            description=description,
            units=units,
            min_value=min_value,
            max_value=max_value
        )
        
        node_id = pig.add_node(param_node)
        logger.debug(f"Parâmetro '{name}' adicionado ao PIG: {node_id}")
        return node_id
    
    async def add_operation(
        self,
        session_id: str,
        name: str,
        operation_type: str,
        cadquery_code: str,
        inputs: Dict[str, str] = None,
        description: str = None
    ) -> str:
        """Adiciona uma operação ao PIG"""
        pig = await self.get_graph(session_id)
        
        operation_node = OperationNode(
            name=name,
            value=None,  # OperationNode usa valor nulo
            operation_type=operation_type,
            cadquery_code=cadquery_code,
            inputs=inputs or {},
            description=description
        )
        
        node_id = pig.add_node(operation_node)
        
        # Adicionar dependências baseadas nos inputs
        if inputs:
            for input_name, param_node_id in inputs.items():
                if param_node_id in pig.nodes:
                    pig.add_dependency(node_id, param_node_id)
        
        logger.debug(f"Operação '{name}' adicionada ao PIG: {node_id}")
        return node_id
    
    async def update_parameter_value(
        self, session_id: str, parameter_name: str, new_value: Any
    ) -> List[str]:
        """
        Atualiza valor de um parâmetro e retorna nós afetados.
        Esta é a funcionalidade central da modelagem paramétrica.
        """
        pig = await self.get_graph(session_id)
        
        # Encontrar parâmetro por nome
        param_id = pig.find_parameter_by_name(parameter_name)
        if not param_id:
            raise ValueError(f"Parâmetro '{parameter_name}' não encontrado")
        
        # Atualizar valor e obter nós afetados
        affected_nodes = pig.update_parameter(param_id, new_value)
        
        logger.info(
            f"Parâmetro '{parameter_name}' atualizado para {new_value}. "
            f"Nós afetados: {len(affected_nodes)}"
        )
        
        return affected_nodes
    
    async def get_parameters(self, session_id: str) -> Dict[str, Any]:
        """Retorna todos os parâmetros do modelo"""
        pig = await self.get_graph(session_id)
        return self._extract_parameters(pig)
    
    async def get_operations(self, session_id: str) -> List[Dict[str, Any]]:
        """Retorna todas as operações do modelo"""
        pig = await self.get_graph(session_id)
        return self._extract_operations(pig)
    
    async def get_dependencies(self, session_id: str, node_id: str) -> Dict[str, Any]:
        """Retorna dependências de um nó específico"""
        pig = await self.get_graph(session_id)
        
        if node_id not in pig.nodes:
            raise ValueError(f"Nó {node_id} não encontrado")
        
        node = pig.nodes[node_id]
        
        return {
            "dependencies": list(node.dependencies),
            "dependents": list(node.dependents),
            "dependency_details": {
                dep_id: self._serialize_node(pig.nodes[dep_id]) 
                for dep_id in node.dependencies 
                if dep_id in pig.nodes
            },
            "dependent_details": {
                dep_id: self._serialize_node(pig.nodes[dep_id]) 
                for dep_id in node.dependents 
                if dep_id in pig.nodes
            }
        }
    
    def _serialize_node(self, node: PIGNode) -> Dict[str, Any]:
        """Serializa nó do PIG para JSON"""
        base_data = {
            "id": node.id,
            "name": node.name,
            "node_type": node.node_type.value,
            "value": node.value,
            "description": node.description,
            "dependencies": list(node.dependencies),
            "dependents": list(node.dependents),
            "metadata": node.metadata
        }
        
        # Adicionar campos específicos do tipo
        if isinstance(node, ParameterNode):
            base_data.update({
                "parameter_type": node.parameter_type.value,
                "min_value": node.min_value,
                "max_value": node.max_value,
                "units": node.units
            })
        elif isinstance(node, OperationNode):
            base_data.update({
                "operation_type": node.operation_type,
                "cadquery_code": node.cadquery_code,
                "inputs": node.inputs
            })
        
        return base_data
    
    def _extract_parameters(self, pig: ParametricIntentionGraph) -> Dict[str, Any]:
        """Extrai apenas os parâmetros do PIG"""
        parameters = {}
        
        for node_id, node in pig.nodes.items():
            if node.node_type == NodeType.PARAMETER:
                parameters[node.name] = {
                    "id": node_id,
                    "value": node.value,
                    "type": node.parameter_type.value if hasattr(node, 'parameter_type') else 'unknown',
                    "units": getattr(node, 'units', None),
                    "description": node.description
                }
        
        return parameters
    
    def _extract_operations(self, pig: ParametricIntentionGraph) -> List[Dict[str, Any]]:
        """Extrai apenas as operações do PIG"""
        operations = []
        
        execution_order = pig.get_execution_order()
        
        for node_id in execution_order:
            node = pig.nodes[node_id]
            if node.node_type == NodeType.OPERATION:
                operations.append({
                    "id": node_id,
                    "name": node.name,
                    "type": node.operation_type if hasattr(node, 'operation_type') else 'unknown',
                    "description": node.description,
                    "inputs": getattr(node, 'inputs', {}),
                    "code": getattr(node, 'cadquery_code', '')
                })
        
        return operations
    
    async def _add_parameter_to_pig(self, pig: ParametricIntentionGraph, name: str, value: Any):
        """Adiciona parâmetro ao PIG (método interno)"""
        
        # Determinar tipo do parâmetro baseado no valor
        if isinstance(value, (int, float)):
            param_type = ParameterType.NUMERIC
        elif isinstance(value, bool):
            param_type = ParameterType.BOOLEAN
        elif isinstance(value, str):
            param_type = ParameterType.STRING
        elif isinstance(value, (list, tuple)) and len(value) in [2, 3]:
            param_type = ParameterType.VECTOR
        else:
            param_type = ParameterType.STRING  # Default
        
        # Verificar se parâmetro já existe
        existing_id = pig.find_parameter_by_name(name)
        if existing_id:
            # Atualizar valor existente
            pig.nodes[existing_id].value = value
        else:
            # Criar novo parâmetro
            param_node = ParameterNode(
                name=name,
                value=value,
                parameter_type=param_type
            )
            pig.add_node(param_node)
    
    async def _add_ast_node_to_pig(
        self, pig: ParametricIntentionGraph, ast_node, parameters: Dict[str, Any]
    ):
        """Converte nó AST para nó do PIG"""
        
        if ast_node.node_type.value in ["primitive", "operation"]:
            # Gerar código CadQuery para este nó
            cadquery_code = self._generate_cadquery_code_for_node(ast_node, parameters)
            
            operation_node = OperationNode(
                name=f"{ast_node.operation}_{ast_node.id[:8]}",
                value=None,  # OperationNode usa valor nulo
                operation_type=ast_node.operation or "unknown",
                cadquery_code=cadquery_code,
                inputs=self._extract_parameter_references(ast_node, parameters)
            )
            
            node_id = pig.add_node(operation_node)
            
            # Adicionar dependências para parâmetros referenciados
            for param_name in ast_node.parameters.values():
                if isinstance(param_name, str) and param_name in parameters:
                    param_id = pig.find_parameter_by_name(param_name)
                    if param_id:
                        pig.add_dependency(node_id, param_id)
    
    def _generate_cadquery_code_for_node(self, ast_node, parameters: Dict[str, Any]) -> str:
        """Gera código CadQuery para um nó AST"""
        
        operation = ast_node.operation
        params = ast_node.parameters
        
        # Templates básicos de código
        templates = {
            "box": "result = cq.Workplane('XY').box({width}, {height}, {depth})",
            "cylinder": "result = cq.Workplane('XY').cylinder({height}, {radius})",
            "sphere": "result = cq.Workplane('XY').sphere({radius})",
            "extrude": "result = result.extrude({distance})",
            "cut": "result = result.cut({cutter})",
            "fillet": "result = result.fillet({radius})"
        }
        
        if operation in templates:
            try:
                return templates[operation].format(**params)
            except KeyError as e:
                return f"# ERRO: Parâmetro ausente {e} para operação {operation}"
        else:
            return f"# ERRO: Template não encontrado para operação {operation}"
    
    def _extract_parameter_references(self, ast_node, parameters: Dict[str, Any]) -> Dict[str, str]:
        """Extrai referências a parâmetros de um nó AST"""
        refs = {}
        
        for param_name, param_value in ast_node.parameters.items():
            if isinstance(param_value, str) and param_value in parameters:
                refs[param_name] = param_value
        
        return refs 

    async def load_previous_generation(self, session_id: str, file_path: str = None) -> Dict[str, Any]:
        """
        Load Previous Generation: Carrega uma geração anterior do modelo
        
        Args:
            session_id: ID da sessão
            file_path: Caminho específico do arquivo (opcional, usa o mais recente se não especificado)
            
        Returns:
            Dados da geração carregada incluindo parâmetros e código
        """
        try:
            if not file_path:
                file_path = await self._get_latest_generated_file(session_id)
                
            if not file_path or not Path(file_path).exists():
                raise FileNotFoundError(f"Arquivo de geração não encontrado para sessão {session_id}")
            
            # Carregar metadados do cabeçalho do arquivo
            metadata = await self._extract_file_metadata(file_path)
            
            # Carregar código Python
            with open(file_path, 'r', encoding='utf-8') as f:
                full_code = f.read()
            
            # Extrair parâmetros do código
            parameters = await self._extract_parameters_from_code(full_code)
            
            # Extrair operações CadQuery
            cadquery_code = await self._extract_cadquery_operations(full_code)
            
            # Atualizar PIG com os dados carregados
            await self._update_pig_from_loaded_data(session_id, parameters, cadquery_code, metadata)
            
            loaded_data = {
                "file_path": file_path,
                "metadata": metadata,
                "parameters": parameters,
                "cadquery_code": cadquery_code,
                "load_timestamp": datetime.now().isoformat(),
                "success": True
            }
            
            # Adicionar ao histórico de versões
            await self._add_version_to_history(session_id, "load_previous", loaded_data)
            
            logger.info(f"Geração anterior carregada com sucesso: {file_path}")
            return loaded_data
            
        except Exception as e:
            logger.error(f"Erro ao carregar geração anterior: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    async def enable_direct_code_editing(self, session_id: str, 
                                       operation_id: str, 
                                       new_cadquery_code: str) -> Dict[str, Any]:
        """
        Enable Direct Code Editing: Permite edição direta do código CadQuery
        
        Args:
            session_id: ID da sessão
            operation_id: ID da operação a ser editada
            new_cadquery_code: Novo código CadQuery
            
        Returns:
            Resultado da edição incluindo nós afetados
        """
        try:
            pig = await self.get_graph(session_id)
            
            if operation_id not in pig.nodes:
                raise ValueError(f"Operação {operation_id} não encontrada")
            
            node = pig.nodes[operation_id]
            if node.node_type != NodeType.OPERATION:
                raise ValueError(f"Nó {operation_id} não é uma operação")
            
            # Salvar estado anterior para rollback
            previous_code = getattr(node, 'cadquery_code', '')
            
            # Validar novo código
            validation_result = await self._validate_cadquery_code(new_cadquery_code)
            if not validation_result['is_valid']:
                return {
                    "success": False,
                    "error": f"Código inválido: {validation_result['error']}",
                    "validation_details": validation_result
                }
            
            # Atualizar código da operação
            node.cadquery_code = new_cadquery_code
            
            # Detectar novos parâmetros no código
            new_parameters = await self._detect_parameters_in_code(new_cadquery_code)
            
            # Adicionar novos parâmetros ao PIG se necessário
            for param_name, param_info in new_parameters.items():
                if not pig.find_parameter_by_name(param_name):
                    await self.add_parameter(
                        session_id, 
                        param_name, 
                        param_info['default_value'],
                        param_info['type'],
                        f"Detectado automaticamente do código editado"
                    )
            
            # Recalcular dependências
            affected_nodes = await self._recalculate_dependencies(session_id, operation_id)
            
            # Adicionar ao histórico de versões
            edit_data = {
                "operation_id": operation_id,
                "previous_code": previous_code,
                "new_code": new_cadquery_code,
                "new_parameters": new_parameters,
                "affected_nodes": affected_nodes
            }
            await self._add_version_to_history(session_id, "direct_edit", edit_data)
            
            logger.info(f"Código editado diretamente para operação {operation_id}")
            
            return {
                "success": True,
                "operation_id": operation_id,
                "affected_nodes": affected_nodes,
                "new_parameters": new_parameters,
                "validation_result": validation_result
            }
            
        except Exception as e:
            logger.error(f"Erro na edição direta do código: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation_id": operation_id
            }
    
    async def create_version_checkpoint(self, session_id: str, description: str = None) -> str:
        """
        Version Control: Cria um checkpoint de versão
        
        Args:
            session_id: ID da sessão
            description: Descrição do checkpoint
            
        Returns:
            ID do checkpoint criado
        """
        try:
            pig = await self.get_graph(session_id)
            
            # Gerar timestamp único para o checkpoint
            checkpoint_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            
            # Serializar estado completo do PIG
            checkpoint_data = {
                "checkpoint_id": checkpoint_id,
                "description": description or f"Checkpoint automático - {datetime.now().isoformat()}",
                "timestamp": datetime.now().isoformat(),
                "pig_state": await self.get_graph_state(session_id),
                "parameters": self._extract_parameters(pig),
                "operations": self._extract_operations(pig)
            }
            
            # Salvar checkpoint no histórico
            if session_id not in self.version_history:
                self.version_history[session_id] = []
            
            self.version_history[session_id].append({
                "type": "checkpoint",
                "data": checkpoint_data
            })
            
            logger.info(f"Checkpoint criado: {checkpoint_id} para sessão {session_id}")
            return checkpoint_id
            
        except Exception as e:
            logger.error(f"Erro ao criar checkpoint: {e}")
            raise
    
    async def rollback_to_version(self, session_id: str, checkpoint_id: str) -> Dict[str, Any]:
        """
        Version Control: Faz rollback para uma versão específica
        
        Args:
            session_id: ID da sessão
            checkpoint_id: ID do checkpoint para rollback
            
        Returns:
            Resultado do rollback
        """
        try:
            if session_id not in self.version_history:
                raise ValueError(f"Nenhum histórico encontrado para sessão {session_id}")
            
            # Encontrar checkpoint
            checkpoint = None
            for entry in self.version_history[session_id]:
                if (entry.get('type') == 'checkpoint' and 
                    entry.get('data', {}).get('checkpoint_id') == checkpoint_id):
                    checkpoint = entry['data']
                    break
            
            if not checkpoint:
                raise ValueError(f"Checkpoint {checkpoint_id} não encontrado")
            
            # Criar checkpoint atual antes do rollback
            current_checkpoint = await self.create_version_checkpoint(
                session_id, f"Backup antes do rollback para {checkpoint_id}"
            )
            
            # Restaurar estado do PIG
            await self._restore_pig_from_checkpoint(session_id, checkpoint)
            
            logger.info(f"Rollback realizado para checkpoint {checkpoint_id}")
            
            return {
                "success": True,
                "rolled_back_to": checkpoint_id,
                "backup_checkpoint": current_checkpoint,
                "restored_parameters": checkpoint.get('parameters', {}),
                "restored_operations": len(checkpoint.get('operations', []))
            }
            
        except Exception as e:
            logger.error(f"Erro no rollback: {e}")
            return {
                "success": False,
                "error": str(e),
                "checkpoint_id": checkpoint_id
            }
    
    async def get_version_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Version Control: Retorna histórico de versões
        """
        return self.version_history.get(session_id, [])
    
    async def enhanced_parameter_update(self, session_id: str, 
                                      parameter_updates: Dict[str, Any],
                                      auto_regenerate: bool = True) -> Dict[str, Any]:
        """
        Live Parameter Updates: Versão aprimorada da atualização de parâmetros
        
        Args:
            session_id: ID da sessão
            parameter_updates: Dicionário de parâmetros para atualizar
            auto_regenerate: Se deve regenerar código automaticamente
            
        Returns:
            Resultado da atualização incluindo nós afetados
        """
        try:
            pig = await self.get_graph(session_id)
            all_affected_nodes = []
            update_results = {}
            
            # Criar checkpoint antes da atualização
            checkpoint_id = await self.create_version_checkpoint(
                session_id, f"Antes da atualização de parâmetros: {list(parameter_updates.keys())}"
            )
            
            # Atualizar cada parâmetro
            for param_name, new_value in parameter_updates.items():
                try:
                    # Validar novo valor
                    validation_result = await self._validate_parameter_value(
                        session_id, param_name, new_value
                    )
                    
                    if validation_result['is_valid']:
                        # Atualizar parâmetro
                        affected_nodes = await self.update_parameter_value(
                            session_id, param_name, new_value
                        )
                        all_affected_nodes.extend(affected_nodes)
                        
                        update_results[param_name] = {
                            "success": True,
                            "new_value": new_value,
                            "affected_nodes": affected_nodes
                        }
                    else:
                        update_results[param_name] = {
                            "success": False,
                            "error": validation_result['error'],
                            "validation_details": validation_result
                        }
                        
                except Exception as e:
                    update_results[param_name] = {
                        "success": False,
                        "error": str(e)
                    }
            
            # Remover duplicatas dos nós afetados
            all_affected_nodes = list(set(all_affected_nodes))
            
            # Adicionar ao histórico
            await self._add_version_to_history(session_id, "parameter_update", {
                "parameter_updates": parameter_updates,
                "update_results": update_results,
                "affected_nodes": all_affected_nodes,
                "checkpoint_before": checkpoint_id
            })
            
            logger.info(f"Parâmetros atualizados: {len(parameter_updates)} parâmetros, {len(all_affected_nodes)} nós afetados")
            
            return {
                "success": True,
                "updated_parameters": list(parameter_updates.keys()),
                "update_results": update_results,
                "affected_nodes": all_affected_nodes,
                "checkpoint_before": checkpoint_id,
                "total_affected": len(all_affected_nodes)
            }
            
        except Exception as e:
            logger.error(f"Erro na atualização aprimorada de parâmetros: {e}")
            return {
                "success": False,
                "error": str(e),
                "parameter_updates": parameter_updates
            } 

    # HELPER METHODS FOR EDIT FUNCTIONALITY
    
    async def _get_latest_generated_file(self, session_id: str) -> Optional[str]:
        """Encontra o arquivo gerado mais recente para uma sessão"""
        try:
            if not self.generated_code_dir.exists():
                return None
            
            # Procurar arquivos que contenham o session_id
            session_files = []
            for file_path in self.generated_code_dir.glob("*.py"):
                if session_id[:8] in file_path.name:
                    session_files.append(file_path)
            
            if not session_files:
                return None
            
            # Ordenar por timestamp (mais recente primeiro)
            session_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return str(session_files[0])
            
        except Exception as e:
            logger.error(f"Erro ao buscar arquivo mais recente: {e}")
            return None
    
    async def _extract_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extrai metadados do cabeçalho do arquivo gerado"""
        try:
            metadata = {}
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('# Timestamp:'):
                        metadata['timestamp'] = line.split(':', 1)[1].strip()
                    elif line.startswith('# Session ID:'):
                        metadata['session_id'] = line.split(':', 1)[1].strip()
                    elif line.startswith('# Plan ID:'):
                        metadata['plan_id'] = line.split(':', 1)[1].strip()
                    elif line.startswith('# Context:'):
                        metadata['context'] = line.split(':', 1)[1].strip()
                    elif line.startswith('# ==='):
                        break
            
            return metadata
            
        except Exception as e:
            logger.error(f"Erro ao extrair metadados: {e}")
            return {}
    
    async def _extract_parameters_from_code(self, code: str) -> Dict[str, Any]:
        """Extrai parâmetros do código Python gerado"""
        try:
            parameters = {}
            
            # Procurar linhas de atribuição de parâmetros
            param_pattern = r'^\s*(\w+)\s*=\s*(.+?)(?:\s*#.*)?$'
            
            in_parameters_section = False
            for line in code.split('\n'):
                line = line.strip()
                
                # Detectar início da seção de parâmetros
                if '# Parâmetros' in line or 'Parameters' in line:
                    in_parameters_section = True
                    continue
                
                # Detectar fim da seção de parâmetros
                if in_parameters_section and ('# Operações' in line or 'Operations' in line):
                    break
                
                # Extrair parâmetros
                if in_parameters_section and line and not line.startswith('#'):
                    match = re.match(param_pattern, line)
                    if match:
                        param_name = match.group(1)
                        param_value_str = match.group(2)
                        
                        # Tentar converter o valor
                        try:
                            param_value = eval(param_value_str)
                            parameters[param_name] = param_value
                        except:
                            parameters[param_name] = param_value_str
            
            return parameters
            
        except Exception as e:
            logger.error(f"Erro ao extrair parâmetros do código: {e}")
            return {}
    
    async def _extract_cadquery_operations(self, code: str) -> str:
        """Extrai operações CadQuery do código Python"""
        try:
            lines = code.split('\n')
            cadquery_lines = []
            
            in_operations_section = False
            for line in lines:
                # Detectar início da seção de operações
                if '# Operações' in line or 'Operations' in line:
                    in_operations_section = True
                    continue
                
                # Detectar fim da seção de operações
                if in_operations_section and ('# Extrair informações' in line or 'if \'result\' in locals():' in line):
                    break
                
                # Coletar linhas de operações
                if in_operations_section and line.strip():
                    cadquery_lines.append(line)
            
            return '\n'.join(cadquery_lines)
            
        except Exception as e:
            logger.error(f"Erro ao extrair operações CadQuery: {e}")
            return ""
    
    async def _update_pig_from_loaded_data(self, session_id: str, 
                                         parameters: Dict[str, Any], 
                                         cadquery_code: str, 
                                         metadata: Dict[str, Any]):
        """Atualiza PIG com dados carregados de arquivo anterior"""
        try:
            pig = await self.get_graph(session_id)
            
            # Limpar PIG atual
            pig.nodes.clear()
            pig.execution_order.clear()
            pig.root_nodes.clear()
            
            # Adicionar parâmetros
            for param_name, param_value in parameters.items():
                await self._add_parameter_to_pig(pig, param_name, param_value)
            
            # Criar operação principal com o código CadQuery
            if cadquery_code.strip():
                operation_node = OperationNode(
                    name=f"loaded_operation_{metadata.get('plan_id', 'unknown')[:8]}",
                    value=None,
                    operation_type="loaded",
                    cadquery_code=cadquery_code,
                    inputs={}
                )
                pig.add_node(operation_node)
            
            # Recalcular ordem de execução
            pig.get_execution_order()
            
        except Exception as e:
            logger.error(f"Erro ao atualizar PIG com dados carregados: {e}")
            raise
    
    async def _validate_cadquery_code(self, code: str) -> Dict[str, Any]:
        """Valida código CadQuery"""
        try:
            # Validações básicas
            if not code.strip():
                return {"is_valid": False, "error": "Código vazio"}
            
            # Verificar imports necessários
            if 'cq.' in code and 'import cadquery as cq' not in code:
                return {"is_valid": False, "error": "Import 'cadquery as cq' necessário"}
            
            # Verificar sintaxe Python básica
            try:
                compile(code, '<string>', 'exec')
            except SyntaxError as e:
                return {"is_valid": False, "error": f"Erro de sintaxe: {str(e)}"}
            
            # Verificar se usa variável 'result'
            if 'result' not in code:
                return {"is_valid": False, "error": "Código deve definir variável 'result'"}
            
            return {"is_valid": True, "warnings": []}
            
        except Exception as e:
            return {"is_valid": False, "error": f"Erro na validação: {str(e)}"}
    
    async def _detect_parameters_in_code(self, code: str) -> Dict[str, Dict[str, Any]]:
        """Detecta parâmetros utilizados no código CadQuery"""
        try:
            parameters = {}
            
            # Procurar por variáveis que parecem parâmetros
            var_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
            
            # Palavras-chave do CadQuery e Python que não são parâmetros
            excluded_words = {
                'cq', 'result', 'Workplane', 'box', 'cylinder', 'sphere', 'extrude', 
                'cut', 'union', 'fillet', 'chamfer', 'faces', 'edges', 'vertices',
                'XY', 'XZ', 'YZ', 'import', 'as', 'from', 'def', 'class', 'if', 
                'else', 'elif', 'for', 'while', 'try', 'except', 'finally',
                'and', 'or', 'not', 'in', 'is', 'True', 'False', 'None'
            }
            
            variables = set(re.findall(var_pattern, code))
            
            for var in variables:
                if (var not in excluded_words and 
                    not var.startswith('_') and
                    not var.isupper() and  # Constantes
                    len(var) > 1):
                    
                    # Tentar inferir tipo baseado no contexto
                    param_type = self._infer_parameter_type(var, code)
                    default_value = param_type.get('default_value', 10.0)
                    
                    parameters[var] = {
                        'type': param_type.get('type', ParameterType.NUMERIC),
                        'default_value': default_value,
                        'inferred_from': 'code_analysis'
                    }
            
            return parameters
            
        except Exception as e:
            logger.error(f"Erro ao detectar parâmetros: {e}")
            return {}
    
    def _infer_parameter_type(self, var_name: str, code: str) -> Dict[str, Any]:
        """Infere tipo de parâmetro baseado no nome e contexto"""
        var_name_lower = var_name.lower()
        
        # Inferir tipo baseado no nome
        if any(keyword in var_name_lower for keyword in ['width', 'height', 'depth', 'length', 'size', 'radius', 'diameter']):
            return {'type': ParameterType.NUMERIC, 'default_value': 10.0}
        elif any(keyword in var_name_lower for keyword in ['count', 'number', 'num']):
            return {'type': ParameterType.NUMERIC, 'default_value': 4}
        elif any(keyword in var_name_lower for keyword in ['angle', 'rotation']):
            return {'type': ParameterType.NUMERIC, 'default_value': 90.0}
        elif any(keyword in var_name_lower for keyword in ['enable', 'show', 'visible']):
            return {'type': ParameterType.BOOLEAN, 'default_value': True}
        elif any(keyword in var_name_lower for keyword in ['name', 'label', 'text']):
            return {'type': ParameterType.STRING, 'default_value': "Parameter"}
        else:
            return {'type': ParameterType.NUMERIC, 'default_value': 10.0}
    
    async def _recalculate_dependencies(self, session_id: str, operation_id: str) -> List[str]:
        """Recalcula dependências após edição de código"""
        try:
            pig = await self.get_graph(session_id)
            
            if operation_id not in pig.nodes:
                return []
            
            node = pig.nodes[operation_id]
            
            # Obter todos os nós que dependem desta operação
            affected_nodes = [operation_id]
            
            def collect_dependents(node_id):
                current_node = pig.nodes.get(node_id)
                if current_node:
                    for dependent_id in current_node.dependents:
                        if dependent_id not in affected_nodes:
                            affected_nodes.append(dependent_id)
                            collect_dependents(dependent_id)
            
            collect_dependents(operation_id)
            
            # Recalcular ordem de execução
            pig.get_execution_order()
            
            return affected_nodes
            
        except Exception as e:
            logger.error(f"Erro ao recalcular dependências: {e}")
            return [operation_id]
    
    async def _validate_parameter_value(self, session_id: str, 
                                      param_name: str, 
                                      new_value: Any) -> Dict[str, Any]:
        """Valida novo valor de parâmetro"""
        try:
            pig = await self.get_graph(session_id)
            param_id = pig.find_parameter_by_name(param_name)
            
            if not param_id:
                return {"is_valid": False, "error": f"Parâmetro '{param_name}' não encontrado"}
            
            param_node = pig.nodes[param_id]
            
            # Validar tipo
            if hasattr(param_node, 'parameter_type'):
                param_type = param_node.parameter_type
                
                if param_type == ParameterType.NUMERIC:
                    if not isinstance(new_value, (int, float)):
                        return {"is_valid": False, "error": "Valor deve ser numérico"}
                    
                    # Verificar limites se definidos
                    if hasattr(param_node, 'min_value') and param_node.min_value is not None:
                        if new_value < param_node.min_value:
                            return {"is_valid": False, "error": f"Valor deve ser >= {param_node.min_value}"}
                    
                    if hasattr(param_node, 'max_value') and param_node.max_value is not None:
                        if new_value > param_node.max_value:
                            return {"is_valid": False, "error": f"Valor deve ser <= {param_node.max_value}"}
                
                elif param_type == ParameterType.BOOLEAN:
                    if not isinstance(new_value, bool):
                        return {"is_valid": False, "error": "Valor deve ser booleano"}
                
                elif param_type == ParameterType.STRING:
                    if not isinstance(new_value, str):
                        return {"is_valid": False, "error": "Valor deve ser string"}
            
            return {"is_valid": True}
            
        except Exception as e:
            logger.error(f"Erro na validação do parâmetro: {e}")
            return {"is_valid": False, "error": str(e)}
    
    async def _add_version_to_history(self, session_id: str, action_type: str, data: Dict[str, Any]):
        """Adiciona entrada ao histórico de versões"""
        try:
            if session_id not in self.version_history:
                self.version_history[session_id] = []
            
            self.version_history[session_id].append({
                "type": action_type,
                "timestamp": datetime.now().isoformat(),
                "data": data
            })
            
            # Manter apenas os últimos 100 registros
            if len(self.version_history[session_id]) > 100:
                self.version_history[session_id] = self.version_history[session_id][-100:]
                
        except Exception as e:
            logger.error(f"Erro ao adicionar ao histórico: {e}")
    
    async def _restore_pig_from_checkpoint(self, session_id: str, checkpoint_data: Dict[str, Any]):
        """Restaura PIG de um checkpoint"""
        try:
            # Limpar PIG atual
            self.graphs[session_id] = ParametricIntentionGraph()
            pig = self.graphs[session_id]
            
            # Restaurar parâmetros
            parameters = checkpoint_data.get('parameters', {})
            for param_name, param_info in parameters.items():
                param_value = param_info.get('value')
                param_type_str = param_info.get('type', 'numeric')
                
                # Converter string do tipo para enum
                param_type = ParameterType.NUMERIC
                if param_type_str == 'boolean':
                    param_type = ParameterType.BOOLEAN
                elif param_type_str == 'string':
                    param_type = ParameterType.STRING
                elif param_type_str == 'vector':
                    param_type = ParameterType.VECTOR
                
                await self.add_parameter(
                    session_id, param_name, param_value, param_type,
                    param_info.get('description')
                )
            
            # Restaurar operações
            operations = checkpoint_data.get('operations', [])
            for op in operations:
                await self.add_operation(
                    session_id,
                    op.get('name', 'restored_operation'),
                    op.get('type', 'unknown'),
                    op.get('code', ''),
                    op.get('inputs', {}),
                    op.get('description')
                )
            
            logger.info(f"PIG restaurado de checkpoint com {len(parameters)} parâmetros e {len(operations)} operações")
            
        except Exception as e:
            logger.error(f"Erro ao restaurar PIG: {e}")
            raise 