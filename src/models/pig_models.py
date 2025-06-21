from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Any, Optional, Set
from enum import Enum
import uuid
from datetime import datetime

class NodeType(str, Enum):
    PARAMETER = "parameter"
    OPERATION = "operation"
    CONSTRAINT = "constraint"

class ParameterType(str, Enum):
    NUMERIC = "numeric"
    STRING = "string"
    BOOLEAN = "boolean"
    VECTOR = "vector"
    GEOMETRY_REF = "geometry_ref"

class PIGNode(BaseModel):
    """Nó do Grafo de Intenção Paramétrica"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            set: list
        }
    )
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    node_type: NodeType
    value: Any
    description: Optional[str] = None
    dependencies: Set[str] = Field(default_factory=set)
    dependents: Set[str] = Field(default_factory=set)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ParameterNode(PIGNode):
    """Nó de parâmetro no PIG"""
    node_type: NodeType = NodeType.PARAMETER
    parameter_type: ParameterType
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    units: Optional[str] = None
    
class OperationNode(PIGNode):
    """Nó de operação no PIG"""
    node_type: NodeType = NodeType.OPERATION
    operation_type: str  # "extrude", "cut", "fillet", etc.
    cadquery_code: Optional[str] = None
    inputs: Dict[str, str] = Field(default_factory=dict)  # nome_input -> node_id
    
class ParametricIntentionGraph(BaseModel):
    """Grafo de Intenção Paramétrica completo"""
    nodes: Dict[str, PIGNode] = Field(default_factory=dict)
    execution_order: List[str] = Field(default_factory=list)
    root_nodes: Set[str] = Field(default_factory=set)
    
    def add_node(self, node: PIGNode) -> str:
        """Adiciona um nó ao grafo"""
        self.nodes[node.id] = node
        if not node.dependencies:
            self.root_nodes.add(node.id)
        return node.id
    
    def add_dependency(self, dependent_id: str, dependency_id: str):
        """Adiciona uma dependência entre nós"""
        if dependent_id in self.nodes and dependency_id in self.nodes:
            self.nodes[dependent_id].dependencies.add(dependency_id)
            self.nodes[dependency_id].dependents.add(dependent_id)
            # Remove da lista de root nodes se agora tem dependências
            if dependent_id in self.root_nodes and self.nodes[dependent_id].dependencies:
                self.root_nodes.remove(dependent_id)
    
    def get_execution_order(self) -> List[str]:
        """Calcula a ordem de execução topológica dos nós"""
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(node_id: str):
            if node_id in temp_visited:
                raise ValueError(f"Dependência circular detectada envolvendo {node_id}")
            if node_id in visited:
                return
                
            temp_visited.add(node_id)
            
            # Visita todas as dependências primeiro
            for dep_id in self.nodes[node_id].dependencies:
                visit(dep_id)
                
            temp_visited.remove(node_id)
            visited.add(node_id)
            order.append(node_id)
        
        # Visita todos os nós
        for node_id in self.nodes:
            if node_id not in visited:
                visit(node_id)
                
        self.execution_order = order
        return order
    
    def update_parameter(self, node_id: str, new_value: Any) -> List[str]:
        """Atualiza um parâmetro e retorna lista de nós afetados"""
        if node_id not in self.nodes:
            raise ValueError(f"Nó {node_id} não encontrado")
            
        self.nodes[node_id].value = new_value
        
        # Encontra todos os nós dependentes que precisam ser recalculados
        affected_nodes = set()
        to_visit = [node_id]
        
        while to_visit:
            current = to_visit.pop()
            for dependent in self.nodes[current].dependents:
                if dependent not in affected_nodes:
                    affected_nodes.add(dependent)
                    to_visit.append(dependent)
        
        # Retorna em ordem topológica
        execution_order = self.get_execution_order()
        return [node_id for node_id in execution_order if node_id in affected_nodes]
    
    def find_parameter_by_name(self, name: str) -> Optional[str]:
        """Encontra ID do nó por nome do parâmetro"""
        for node_id, node in self.nodes.items():
            if node.name.lower() == name.lower() and node.node_type == NodeType.PARAMETER:
                return node_id
        return None 