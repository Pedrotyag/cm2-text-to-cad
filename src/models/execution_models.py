from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Any, Optional
from enum import Enum
import uuid
from datetime import datetime

class ASTNodeType(str, Enum):
    PRIMITIVE = "primitive"
    OPERATION = "operation"
    PARAMETER = "parameter"  # Adicionado para compatibilidade com LLM
    PARAMETER_REF = "parameter_ref"
    EXPRESSION = "expression"

class PrimitiveType(str, Enum):
    BOX = "box"
    CYLINDER = "cylinder"
    SPHERE = "sphere"
    SKETCH = "sketch"

class OperationType(str, Enum):
    EXTRUDE = "extrude"
    CUT = "cut"
    UNION = "union"
    FILLET = "fillet"
    CHAMFER = "chamfer"
    PATTERN_LINEAR = "pattern_linear"
    PATTERN_POLAR = "pattern_polar"

class ASTNode(BaseModel):
    """Nó da Árvore de Execução Abstrata"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_type: ASTNodeType
    operation: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    children: List['ASTNode'] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    result_id: Optional[str] = None  # ID do resultado para referência no código gerado
    target_id: Optional[str] = None  # ID do objeto alvo para operações

class ExecutionPlan(BaseModel):
    """Plano de execução gerado pelo LLM"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    ast_nodes: List[ASTNode]
    new_parameters: Dict[str, Any] = Field(default_factory=dict)
    affected_operations: List[str] = Field(default_factory=list)
    estimated_execution_time: Optional[float] = None
    # Novos campos para código CadQuery direto
    cadquery_code: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    
class ExecutionResult(BaseModel):
    """Resultado da execução de um plano"""
    plan_id: str
    status: str  # "success", "error", "timeout"
    execution_time: float
    generated_code: Optional[str] = None
    model_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    updated_pig_nodes: List[str] = Field(default_factory=list)
    
class LLMQuery(BaseModel):
    """Consulta estruturada para o LLM"""
    user_request: str
    conversation_history: List[Dict[str, Any]]
    current_model_state: Optional[Dict[str, Any]] = None
    pig_state: Optional[Dict[str, Any]] = None
    available_operations: List[str] = Field(default_factory=list)
    context_metadata: Dict[str, Any] = Field(default_factory=dict)
    
class LLMResponse(BaseModel):
    """Resposta estruturada do LLM"""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    intention_type: str
    execution_plan: Optional[ExecutionPlan] = None
    parameter_updates: Dict[str, Any] = Field(default_factory=dict)
    response_text: str
    confidence: Optional[float] = None
    requires_clarification: bool = False
    clarification_questions: List[str] = Field(default_factory=list)

class ValidationError(BaseModel):
    """Erro de validação do plano de execução"""
    node_id: str
    error_type: str
    message: str
    suggested_fix: Optional[str] = None

class ValidationResult(BaseModel):
    """Resultado da validação de um plano"""
    is_valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
# Permite referências circulares nos modelos
ASTNode.model_rebuild() 