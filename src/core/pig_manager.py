import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

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
        
    async def initialize_empty_graph(self, session_id: str):
        """Inicializa PIG vazio para uma nova sessão"""
        self.graphs[session_id] = ParametricIntentionGraph()
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
            "operations": self._extract_operations(pig)
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