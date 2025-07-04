import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..models import (
    UserMessage, SystemResponse, ConversationHistory,
    ModelState, GeometrySelection, IntentionType
)
from .dialog_manager import DialogManager
from .planning_module import PlanningModule
from .executor import SandboxedExecutor
from .pig_manager import PIGManager
from .edit_manager import EditManager

logger = logging.getLogger(__name__)

class CentralOrchestrator:
    """
    O Maestro - Gerencia todo o fluxo de trabalho do sistema.
    Não executa tarefas, mas delega para os componentes corretos.
    """
    
    def __init__(self):
        self.dialog_manager = DialogManager()
        self.planning_module = PlanningModule()
        self.executor = SandboxedExecutor()
        self.pig_manager = PIGManager()
        
        # Novo: Gerenciador de Edições
        self.edit_manager = EditManager(self.pig_manager, self.executor)
        
        self.current_session_id: Optional[str] = None
        self.is_processing = False
        
    async def start_session(self) -> str:
        """Inicia uma nova sessão de design"""
        conversation = ConversationHistory()
        self.current_session_id = conversation.session_id
        await self.dialog_manager.create_session(conversation)
        
        # Inicializa PIG vazio
        await self.pig_manager.initialize_empty_graph(self.current_session_id)
        
        logger.info(f"Nova sessão iniciada: {self.current_session_id}")
        return self.current_session_id
    
    async def process_user_input(
        self,
        user_input: str,
        selected_geometry: Optional[GeometrySelection] = None,
        session_id: Optional[str] = None,
        selected_model: Optional[str] = None
    ) -> SystemResponse:
        """
        Processa entrada do usuário e orquestra resposta do sistema.
        
        Args:
            user_input: Texto enviado pelo usuário
            selected_geometry: Geometria selecionada na UI (opcional)
            session_id: ID da sessão (usa atual se não especificado)
            selected_model: Modelo selecionado para a requisição (opcional)
        """
        if self.is_processing:
            return SystemResponse(
                content="Sistema ocupado processando requisição anterior. Tente novamente.",
                message_type="error"
            )
        
        self.is_processing = True
        session_id = session_id or self.current_session_id
        
        try:
            # 1. Criar mensagem do usuário
            logger.debug(f"Criando UserMessage para entrada: {user_input[:50]}...")
            user_message = UserMessage(
                content=user_input,
                selected_geometry=selected_geometry.model_dump() if selected_geometry else None
            )
            logger.debug(f"UserMessage criada com timestamp: {user_message.timestamp}")
            
            # 2. Adicionar ao histórico de conversas
            await self.dialog_manager.add_message(session_id, user_message)
            
            # 3. Analisar intenção do usuário
            intention_result = await self.dialog_manager.resolve_intention(
                session_id, user_message
            )
            
            logger.info(f"Intenção detectada: {intention_result.intention_type}")
            
            # 4. Decidir fluxo baseado na intenção
            if intention_result.intention_type == IntentionType.MODIFICATION:
                # Verifica se é modificação paramétrica simples
                param_update = await self._try_parameter_update(
                    session_id, user_input
                )
                if param_update:
                    return param_update
            
            # 5. Se não é modificação paramétrica simples, consultar LLM
            response = await self._process_with_llm(
                session_id,
                user_message,
                intention_result,
                selected_model
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Erro ao processar entrada do usuário: {e}")
            error_response = SystemResponse(
                content=f"Erro interno: {str(e)}",
                message_type="error"
            )
            await self.dialog_manager.add_message(session_id, error_response)
            return error_response
            
        finally:
            self.is_processing = False
    
    async def _try_parameter_update(
        self, session_id: str, user_input: str
    ) -> Optional[SystemResponse]:
        """
        Tenta resolver modificação como atualização paramétrica direta.
        Retorna None se não conseguir resolver automaticamente.
        """
        try:
            # Usar regex/NLP simples para detectar padrões como:
            # "aumente X para Y", "mude altura para Z", etc.
            param_match = await self._extract_parameter_modification(user_input)
            
            if param_match:
                param_name, new_value = param_match
                
                # Buscar parâmetro no PIG
                pig = await self.pig_manager.get_graph(session_id)
                param_id = pig.find_parameter_by_name(param_name)
                
                if param_id:
                    # Atualizar parâmetro e recalcular dependências
                    affected_nodes = pig.update_parameter(param_id, new_value)
                    
                    # Executar nós afetados
                    execution_result = await self.executor.execute_pig_nodes(
                        session_id, affected_nodes, pig
                    )
                    
                    if execution_result.status == "success":
                        # Atualizar estado do modelo
                        await self.dialog_manager.update_model_state(
                            session_id, execution_result.model_data
                        )
                        
                        response = SystemResponse(
                            content=f"Parâmetro '{param_name}' atualizado para {new_value}. Modelo regenerado.",
                            model_state=execution_result.model_data
                        )
                        
                        await self.dialog_manager.add_message(session_id, response)
                        return response
            
            return None
            
        except Exception as e:
            logger.warning(f"Falha na atualização paramétrica automática: {e}")
            return None
    
    async def _process_with_llm(
        self,
        session_id: str,
        user_message: UserMessage,
        intention_result,
        selected_model: Optional[str] = None
    ) -> SystemResponse:
        """Processa requisição usando o módulo de planejamento (LLM)"""
        
        # 1. Obter contexto atual
        conversation_history = await self.dialog_manager.get_conversation_history(session_id)
        model_state = await self.dialog_manager.get_model_state(session_id)
        pig_state = await self.pig_manager.get_graph_state(session_id)
        
        # 2. Formular consulta para o LLM
        llm_query = {
            "user_request": user_message.content,
            "conversation_history": [msg.model_dump() for msg in conversation_history.get_recent_context()],
            "current_model_state": model_state.model_dump() if model_state else None,
            "pig_state": pig_state,
            "selected_geometry": user_message.selected_geometry,
            "intention_type": intention_result.intention_type.value,
            "model_choice": selected_model or "gemini-2.5-flash"
        }
        
        # 3. Obter plano do LLM
        llm_response = await self.planning_module.generate_plan(llm_query)
        
        # 4. Se requer clarificação, retornar perguntas
        if llm_response.requires_clarification:
            response = SystemResponse(
                content=llm_response.response_text,
                execution_plan={"clarification_questions": llm_response.clarification_questions}
            )
            await self.dialog_manager.add_message(session_id, response)
            return response
        
        # 5. Se tem plano de execução, executar
        if llm_response.execution_plan:
            execution_result = await self._execute_plan_with_retry(
                session_id, llm_response.execution_plan
            )
            
            # 6. Atualizar PIG com novas operações/parâmetros
            await self.pig_manager.update_from_execution_plan(
                session_id, llm_response.execution_plan, execution_result
            )
            
            # 7. Criar resposta
            if execution_result.status == "success":
                await self.dialog_manager.update_model_state(
                    session_id, execution_result.model_data
                )
                
                # Salvar último código executado para exportação
                # Usar get_session_state do próprio orchestrator ao invés do dialog_manager
                if not hasattr(self, '_session_codes'):
                    self._session_codes = {}
                self._session_codes[session_id] = execution_result.generated_code
                
                logger.debug(f"Criando SystemResponse com sucesso")
                logger.debug(f"execution_result.model_data = {execution_result.model_data}")
                logger.debug(f"Tipo dos model_data: {type(execution_result.model_data)}")
                
                response = SystemResponse(
                    content=llm_response.response_text,
                    execution_plan=llm_response.execution_plan.model_dump(),
                    model_state=execution_result.model_data
                )
                logger.debug(f"SystemResponse criada com timestamp: {response.timestamp}")
                logger.debug(f"model_state na response: {response.model_state}")
            else:
                logger.debug(f"Criando SystemResponse com erro")
                response = SystemResponse(
                    content=f"Erro na execução: {execution_result.error_message}",
                    message_type="error"
                )
                logger.debug(f"SystemResponse de erro criada com timestamp: {response.timestamp}")
        else:
            # Resposta apenas informativa
            logger.debug(f"Criando SystemResponse informativa")
            response = SystemResponse(content=llm_response.response_text)
            logger.debug(f"SystemResponse informativa criada com timestamp: {response.timestamp}")
        
        await self.dialog_manager.add_message(session_id, response)
        logger.debug(f"Retornando resposta do tipo: {type(response)}")
        logger.debug(f"Tentando serializar resposta final...")
        try:
            test_serialization = response.model_dump()
            logger.debug(f"Serialização da resposta final bem-sucedida")
        except Exception as e:
            logger.error(f"Erro ao serializar resposta final: {e}")
            logger.error(f"Atributos da resposta: {dir(response)}")
            raise
        return response
    
    async def _execute_plan_with_retry(self, session_id: str, execution_plan) -> Any:
        """Executa plano com ciclo de auto-correção em caso de erro"""
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            try:
                # Executar plano
                result = await self.executor.execute_plan(session_id, execution_plan)
                
                if result.status == "success":
                    return result
                elif attempt < max_retries:
                    # Tentar auto-correção via LLM
                    logger.info(f"Tentativa {attempt + 1} falhou, tentando auto-correção...")
                    
                    correction_query = {
                        "original_plan": execution_plan.model_dump(),
                        "error_message": result.error_message,
                        "error_traceback": result.error_traceback,
                        "request_type": "error_correction"
                    }
                    
                    corrected_response = await self.planning_module.generate_plan(correction_query)
                    
                    if corrected_response.execution_plan:
                        execution_plan = corrected_response.execution_plan
                    else:
                        return result  # Não conseguiu corrigir
                else:
                    return result  # Esgotaram tentativas
                    
            except Exception as e:
                logger.error(f"Erro na execução do plano (tentativa {attempt + 1}): {e}")
                if attempt == max_retries:
                    return {"status": "error", "error_message": str(e)}
    
    async def _extract_parameter_modification(self, text: str) -> Optional[tuple]:
        """Extrai nome do parâmetro e novo valor do texto"""
        import re
        
        # Padrões para detectar modificações de parâmetros
        patterns = [
            r"(?:aumente|mude|altere|defina|configure)\s+(?:o\s+)?(\w+)\s+para\s+(\d+(?:\.\d+)?)",
            r"(\w+)\s*=\s*(\d+(?:\.\d+)?)",
            r"(?:faça|torne)\s+(?:o\s+)?(\w+)\s+(?:de\s+)?(\d+(?:\.\d+)?)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                param_name = match.group(1)
                try:
                    new_value = float(match.group(2))
                    return (param_name, new_value)
                except ValueError:
                    continue
        
        return None
    
    async def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Retorna estado completo da sessão"""
        conversation = await self.dialog_manager.get_conversation_history(session_id)
        model_state = await self.dialog_manager.get_model_state(session_id)
        pig_state = await self.pig_manager.get_graph_state(session_id)
        
        return {
            "session_id": session_id,
            "conversation_history": [msg.model_dump() for msg in conversation.messages],
            "model_state": model_state.model_dump() if model_state else None,
            "pig_state": pig_state,
            "is_processing": self.is_processing,
            "last_execution_code": getattr(self, '_session_codes', {}).get(session_id),
            "edit_capabilities": {
                "can_load_previous": True,
                "can_edit_code": True,
                "can_edit_parameters": True,
                "can_create_checkpoints": True,
                "has_version_history": len(pig_state.get('version_history', [])) > 0
            }
        }
    
    # NEW EDIT FUNCTIONALITY METHODS
    
    async def load_for_editing(self, session_id: str, file_path: str = None) -> Dict[str, Any]:
        """
        Carrega uma geração anterior para edição
        
        Args:
            session_id: ID da sessão
            file_path: Caminho específico do arquivo (opcional)
            
        Returns:
            SystemResponse com dados de edição
        """
        try:
            result = await self.edit_manager.load_for_editing(session_id, file_path)
            
            if result.get('success'):
                response = SystemResponse(
                    content=f"Modelo carregado para edição: {result['data']['loaded_file']}",
                    message_type="success",
                    execution_plan=result['data']
                )
            else:
                response = SystemResponse(
                    content=f"Erro ao carregar modelo: {result.get('error')}",
                    message_type="error"
                )
            
            await self.dialog_manager.add_message(session_id, response)
            return result
            
        except Exception as e:
            logger.error(f"Erro no carregamento para edição: {e}")
            return {"success": False, "error": str(e)}
    
    async def edit_code_directly(self, session_id: str, 
                               operation_id: str, 
                               new_code: str,
                               auto_regenerate: bool = True) -> Dict[str, Any]:
        """
        Edita código CadQuery diretamente
        
        Args:
            session_id: ID da sessão
            operation_id: ID da operação
            new_code: Novo código CadQuery
            auto_regenerate: Se deve regenerar automaticamente
            
        Returns:
            Resultado da edição
        """
        try:
            result = await self.edit_manager.edit_code_directly(
                session_id, operation_id, new_code, auto_regenerate
            )
            
            if result.get('success'):
                # Atualizar estado do modelo se regenerado
                if auto_regenerate and result.get('regeneration_result', {}).get('success'):
                    model_data = result['regeneration_result'].get('model_data')
                    if model_data:
                        await self.dialog_manager.update_model_state(session_id, model_data)
                
                response = SystemResponse(
                    content=f"Código editado com sucesso. {len(result.get('affected_nodes', []))} nós afetados.",
                    message_type="success",
                    model_state=result.get('regeneration_result', {}).get('model_data')
                )
            else:
                response = SystemResponse(
                    content=f"Erro na edição: {result.get('error')}",
                    message_type="error"
                )
            
            await self.dialog_manager.add_message(session_id, response)
            return result
            
        except Exception as e:
            logger.error(f"Erro na edição direta: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_parameters_batch(self, session_id: str, 
                                    parameter_updates: Dict[str, Any],
                                    auto_regenerate: bool = True) -> Dict[str, Any]:
        """
        Atualiza múltiplos parâmetros
        
        Args:
            session_id: ID da sessão
            parameter_updates: Parâmetros para atualizar
            auto_regenerate: Se deve regenerar automaticamente
            
        Returns:
            Resultado da atualização
        """
        try:
            result = await self.edit_manager.update_parameters_batch(
                session_id, parameter_updates, auto_regenerate
            )
            
            if result.get('success'):
                # Atualizar estado do modelo se regenerado
                if auto_regenerate and result.get('regeneration_result', {}).get('success'):
                    model_data = result['regeneration_result'].get('model_data')
                    if model_data:
                        await self.dialog_manager.update_model_state(session_id, model_data)
                
                updated_params = result.get('updated_parameters', [])
                response = SystemResponse(
                    content=f"Parâmetros atualizados: {', '.join(updated_params)}",
                    message_type="success",
                    model_state=result.get('regeneration_result', {}).get('model_data')
                )
            else:
                response = SystemResponse(
                    content=f"Erro na atualização: {result.get('error')}",
                    message_type="error"
                )
            
            await self.dialog_manager.add_message(session_id, response)
            return result
            
        except Exception as e:
            logger.error(f"Erro na atualização de parâmetros: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_checkpoint(self, session_id: str, description: str = None) -> Dict[str, Any]:
        """
        Cria checkpoint de versão
        
        Args:
            session_id: ID da sessão
            description: Descrição do checkpoint
            
        Returns:
            Resultado da criação do checkpoint
        """
        try:
            result = await self.edit_manager.create_checkpoint(session_id, description)
            
            if result.get('success'):
                response = SystemResponse(
                    content=f"Checkpoint criado: {result.get('checkpoint_id')}",
                    message_type="success"
                )
            else:
                response = SystemResponse(
                    content=f"Erro ao criar checkpoint: {result.get('error')}",
                    message_type="error"
                )
            
            await self.dialog_manager.add_message(session_id, response)
            return result
            
        except Exception as e:
            logger.error(f"Erro ao criar checkpoint: {e}")
            return {"success": False, "error": str(e)}
    
    async def rollback_to_checkpoint(self, session_id: str, checkpoint_id: str) -> Dict[str, Any]:
        """
        Faz rollback para checkpoint
        
        Args:
            session_id: ID da sessão
            checkpoint_id: ID do checkpoint
            
        Returns:
            Resultado do rollback
        """
        try:
            result = await self.edit_manager.rollback_to_checkpoint(session_id, checkpoint_id)
            
            if result.get('success'):
                # Atualizar estado do modelo após rollback
                if result.get('regeneration_result', {}).get('success'):
                    model_data = result['regeneration_result'].get('model_data')
                    if model_data:
                        await self.dialog_manager.update_model_state(session_id, model_data)
                
                response = SystemResponse(
                    content=f"Rollback realizado para checkpoint {checkpoint_id}",
                    message_type="success",
                    model_state=result.get('regeneration_result', {}).get('model_data')
                )
            else:
                response = SystemResponse(
                    content=f"Erro no rollback: {result.get('error')}",
                    message_type="error"
                )
            
            await self.dialog_manager.add_message(session_id, response)
            return result
            
        except Exception as e:
            logger.error(f"Erro no rollback: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_edit_history(self, session_id: str) -> Dict[str, Any]:
        """
        Retorna histórico de edições
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Histórico de edições
        """
        try:
            return await self.edit_manager.get_edit_history(session_id)
            
        except Exception as e:
            logger.error(f"Erro ao obter histórico: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_editable_content(self, session_id: str) -> Dict[str, Any]:
        """
        Retorna conteúdo editável
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Conteúdo editável
        """
        try:
            return await self.edit_manager.get_editable_content(session_id)
            
        except Exception as e:
            logger.error(f"Erro ao obter conteúdo editável: {e}")
            return {"success": False, "error": str(e)}
    
    async def validate_edit(self, session_id: str, 
                          edited_code: str = None,
                          parameter_updates: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Valida edições antes de aplicar
        
        Args:
            session_id: ID da sessão
            edited_code: Código editado (opcional)
            parameter_updates: Parâmetros atualizados (opcional)
            
        Returns:
            Resultado da validação
        """
        try:
            return await self.edit_manager.validate_edit(
                session_id, edited_code, parameter_updates
            )
            
        except Exception as e:
            logger.error(f"Erro na validação: {e}")
            return {"success": False, "error": str(e)} 