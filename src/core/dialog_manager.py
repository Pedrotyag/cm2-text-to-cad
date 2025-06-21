import asyncio
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime
import re

from ..models import (
    UserMessage, SystemResponse, ConversationHistory,
    ModelState, IntentionType
)

logger = logging.getLogger(__name__)

class DialogManager:
    """
    A Memória - Mantém contexto da conversa e estado do design.
    Resolve intenção do usuário e gerencia histórico de interações.
    """
    
    def __init__(self):
        # Armazenamento em memória (em produção, usar Redis ou banco)
        self.sessions: Dict[str, ConversationHistory] = {}
        self.model_states: Dict[str, ModelState] = {}
        
    async def create_session(self, conversation: ConversationHistory):
        """Cria uma nova sessão de conversa"""
        self.sessions[conversation.session_id] = conversation
        self.model_states[conversation.session_id] = ModelState()
        logger.info(f"Sessão criada: {conversation.session_id}")
    
    async def add_message(
        self, session_id: str, message: Union[UserMessage, SystemResponse]
    ):
        """Adiciona mensagem ao histórico da sessão"""
        if session_id not in self.sessions:
            raise ValueError(f"Sessão {session_id} não encontrada")
        
        self.sessions[session_id].add_message(message)
        logger.debug(f"Mensagem adicionada à sessão {session_id}: {message.content[:50]}...")
    
    async def get_conversation_history(self, session_id: str) -> ConversationHistory:
        """Retorna histórico da conversa"""
        if session_id not in self.sessions:
            raise ValueError(f"Sessão {session_id} não encontrada")
        
        return self.sessions[session_id]
    
    async def get_model_state(self, session_id: str) -> Optional[ModelState]:
        """Retorna estado atual do modelo"""
        return self.model_states.get(session_id)
    
    async def update_model_state(self, session_id: str, model_data: Dict[str, Any]):
        """Atualiza estado do modelo"""
        if session_id not in self.model_states:
            self.model_states[session_id] = ModelState()
        
        self.model_states[session_id].geometry_data = model_data
        self.model_states[session_id].last_modified = datetime.now()
    
    async def resolve_intention(
        self, session_id: str, user_message: UserMessage
    ) -> 'IntentionResult':
        """
        Analisa a mensagem do usuário e resolve sua intenção.
        
        Returns:
            IntentionResult com tipo de intenção e contexto adicional
        """
        text = user_message.content.lower().strip()
        
        # Padrões para identificar intenções
        intention_type = self._classify_intention(text)
        
        # Contexto adicional baseado na intenção
        context = await self._extract_context(session_id, user_message, intention_type)
        
        return IntentionResult(
            intention_type=intention_type,
            confidence=0.8,  # Poderia usar ML para calcular confiança
            context=context
        )
    
    def _classify_intention(self, text: str) -> IntentionType:
        """Classifica intenção baseada em padrões de texto"""
        
        # Comandos meta (sistema)
        meta_patterns = [
            r"desfaz", r"undo", r"voltar", r"anterior",
            r"salvar", r"exportar", r"limpar", r"reset"
        ]
        if any(re.search(pattern, text) for pattern in meta_patterns):
            return IntentionType.META_COMMAND
        
        # Perguntas
        question_patterns = [
            r"qual", r"como", r"onde", r"quando", r"por que",
            r"quantos?", r"quanto", r"que tamanho", r"dimensão"
        ]
        if any(re.search(pattern, text) for pattern in question_patterns):
            return IntentionType.QUESTION
        
        # Modificações (palavras-chave de mudança)
        modification_patterns = [
            r"aument", r"diminu", r"reduz", r"mude", r"alter", r"modif",
            r"faça.*maior", r"faça.*menor", r"torne.*mais", r"configure",
            r"ajuste", r"corrija"
        ]
        if any(re.search(pattern, text) for pattern in modification_patterns):
            return IntentionType.MODIFICATION
        
        # Novas instruções (palavras de criação)
        creation_patterns = [
            r"crie", r"faça", r"adicione", r"desenhe", r"construa",
            r"gere", r"caixa", r"cilindro", r"esfera", r"furo", r"flange"
        ]
        if any(re.search(pattern, text) for pattern in creation_patterns):
            return IntentionType.NEW_INSTRUCTION
        
        # Default: nova instrução
        return IntentionType.NEW_INSTRUCTION
    
    async def _extract_context(
        self, session_id: str, message: UserMessage, intention_type: IntentionType
    ) -> Dict[str, Any]:
        """Extrai contexto adicional baseado na intenção"""
        
        context = {
            "has_selection": message.selected_geometry is not None,
            "selected_geometry": message.selected_geometry
        }
        
        if intention_type == IntentionType.MODIFICATION:
            # Para modificações, tentar extrair parâmetros mencionados
            context.update(await self._extract_modification_context(message.content))
        
        elif intention_type == IntentionType.QUESTION:
            # Para perguntas, identificar o que está sendo perguntado
            context.update(self._extract_question_context(message.content))
        
        elif intention_type == IntentionType.NEW_INSTRUCTION:
            # Para novas instruções, identificar tipo de geometria
            context.update(self._extract_creation_context(message.content))
        
        return context
    
    async def _extract_modification_context(self, text: str) -> Dict[str, Any]:
        """Extrai contexto de modificação (parâmetros, valores)"""
        context = {}
        
        # Buscar menções a parâmetros comuns
        parameter_patterns = {
            'altura': r'altura|alto|height',
            'largura': r'largura|largo|width',
            'espessura': r'espessura|grossura|thickness',
            'diametro': r'diâmetro|diametro|diameter',
            'raio': r'raio|radius',
            'comprimento': r'comprimento|length'
        }
        
        mentioned_parameters = []
        for param_name, pattern in parameter_patterns.items():
            if re.search(pattern, text.lower()):
                mentioned_parameters.append(param_name)
        
        context['mentioned_parameters'] = mentioned_parameters
        
        # Buscar valores numéricos
        numbers = re.findall(r'\d+(?:\.\d+)?', text)
        if numbers:
            context['mentioned_values'] = [float(n) for n in numbers]
        
        return context
    
    def _extract_question_context(self, text: str) -> Dict[str, Any]:
        """Extrai contexto de pergunta"""
        context = {}
        
        # Identificar tipo de pergunta
        if re.search(r'qual.*dimensão|tamanho|medida', text.lower()):
            context['question_type'] = 'dimensions'
        elif re.search(r'como.*funciona|como.*fazer', text.lower()):
            context['question_type'] = 'how_to'
        elif re.search(r'quantos|quanto', text.lower()):
            context['question_type'] = 'quantity'
        else:
            context['question_type'] = 'general'
        
        return context
    
    def _extract_creation_context(self, text: str) -> Dict[str, Any]:
        """Extrai contexto de criação (tipo de geometria, parâmetros)"""
        context = {}
        
        # Identificar tipo de geometria
        geometry_patterns = {
            'box': r'caixa|cubo|bloco|box',
            'cylinder': r'cilindro|tubo|cylinder',
            'sphere': r'esfera|bola|sphere',
            'flange': r'flange|flanche',
            'hole': r'furo|buraco|hole',
            'slot': r'ranhura|slot|canal'
        }
        
        detected_geometry = []
        for geom_type, pattern in geometry_patterns.items():
            if re.search(pattern, text.lower()):
                detected_geometry.append(geom_type)
        
        context['geometry_types'] = detected_geometry
        
        # Extrair dimensões mencionadas
        dimensions = {}
        
        # Padrões para capturar dimensões específicas
        dimension_patterns = [
            (r'(\d+(?:\.\d+)?)\s*mm.*diâmetro', 'diameter'),
            (r'diâmetro.*?(\d+(?:\.\d+)?)', 'diameter'),
            (r'(\d+(?:\.\d+)?)\s*mm.*altura', 'height'),
            (r'altura.*?(\d+(?:\.\d+)?)', 'height'),
            (r'(\d+(?:\.\d+)?)\s*mm.*espessura', 'thickness'),
            (r'espessura.*?(\d+(?:\.\d+)?)', 'thickness'),
        ]
        
        for pattern, dim_name in dimension_patterns:
            match = re.search(pattern, text.lower())
            if match:
                dimensions[dim_name] = float(match.group(1))
        
        context['dimensions'] = dimensions
        
        return context

class IntentionResult:
    """Resultado da análise de intenção"""
    
    def __init__(self, intention_type: IntentionType, confidence: float, context: Dict[str, Any]):
        self.intention_type = intention_type
        self.confidence = confidence
        self.context = context 