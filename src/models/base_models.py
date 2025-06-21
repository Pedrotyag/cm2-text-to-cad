from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import uuid
from datetime import datetime

class MessageType(str, Enum):
    USER_INPUT = "user_input"
    SYSTEM_RESPONSE = "system_response"
    ERROR = "error"
    OPERATION_COMPLETE = "operation_complete"

class IntentionType(str, Enum):
    NEW_INSTRUCTION = "new_instruction"
    MODIFICATION = "modification"
    QUESTION = "question"
    META_COMMAND = "meta_command"

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"

class UserMessage(BaseModel):
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    selected_geometry: Optional[Dict[str, Any]] = None
    message_type: MessageType = MessageType.USER_INPUT

class SystemResponse(BaseModel):
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    execution_plan: Optional[Dict[str, Any]] = None
    model_state: Optional[Dict[str, Any]] = None
    message_type: MessageType = MessageType.SYSTEM_RESPONSE

class ConversationHistory(BaseModel):
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    messages: List[Union[UserMessage, SystemResponse]] = []
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    
    def add_message(self, message: Union[UserMessage, SystemResponse]):
        self.messages.append(message)
        
    def get_recent_context(self, limit: int = 10) -> List[Union[UserMessage, SystemResponse]]:
        return self.messages[-limit:]

class ModelState(BaseModel):
    """Representação serializável do estado atual do modelo 3D"""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    geometry_data: Optional[Dict[str, Any]] = None
    parameters: Dict[str, Any] = {}
    operations: List[Dict[str, Any]] = []
    last_modified: datetime = Field(default_factory=datetime.now)
    
class GeometrySelection(BaseModel):
    """Dados de seleção de geometria 3D"""
    element_type: str  # "face", "edge", "vertex"
    element_id: str
    coordinates: List[float]
    normal: Optional[List[float]] = None 