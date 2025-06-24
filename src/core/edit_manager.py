import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from .pig_manager import PIGManager
from .executor import SandboxedExecutor
from ..models import ExecutionPlan, ExecutionResult

logger = logging.getLogger(__name__)

class EditManager:
    """
    Gerenciador de Edições - Fornece API unificada para recursos de edição
    """
    
    def __init__(self, pig_manager: PIGManager, executor: SandboxedExecutor):
        self.pig_manager = pig_manager
        self.executor = executor
    
    async def load_for_editing(self, session_id: str, file_path: str = None) -> Dict[str, Any]:
        """
        Carrega uma geração anterior para edição
        
        Args:
            session_id: ID da sessão
            file_path: Caminho específico do arquivo (opcional)
            
        Returns:
            Dados completos para edição incluindo código editável
        """
        try:
            # Carregar geração anterior
            load_result = await self.pig_manager.load_previous_generation(session_id, file_path)
            
            if not load_result.get('success'):
                return load_result
            
            # Obter estado atual do PIG
            pig_state = await self.pig_manager.get_graph_state(session_id)
            
            # Preparar dados para edição
            edit_data = {
                "session_id": session_id,
                "loaded_file": load_result.get('file_path'),
                "parameters": pig_state.get('parameters', {}),
                "operations": pig_state.get('operations', []),
                "editable_code": load_result.get('cadquery_code', ''),
                "metadata": load_result.get('metadata', {}),
                "version_history": pig_state.get('version_history', []),
                "load_timestamp": datetime.now().isoformat(),
                "edit_capabilities": {
                    "can_edit_parameters": True,
                    "can_edit_code": True,
                    "can_create_checkpoints": True,
                    "can_rollback": len(pig_state.get('version_history', [])) > 0
                }
            }
            
            logger.info(f"Modelo carregado para edição: {load_result.get('file_path')}")
            return {"success": True, "data": edit_data}
            
        except Exception as e:
            logger.error(f"Erro ao carregar para edição: {e}")
            return {"success": False, "error": str(e)}
    
    async def edit_code_directly(self, session_id: str, 
                               operation_id: str, 
                               new_code: str,
                               auto_regenerate: bool = True) -> Dict[str, Any]:
        """
        Edita código CadQuery diretamente
        
        Args:
            session_id: ID da sessão
            operation_id: ID da operação a ser editada
            new_code: Novo código CadQuery
            auto_regenerate: Se deve regenerar o modelo automaticamente
            
        Returns:
            Resultado da edição e regeneração (se solicitada)
        """
        try:
            # Criar checkpoint antes da edição
            checkpoint_id = await self.pig_manager.create_version_checkpoint(
                session_id, f"Antes da edição direta da operação {operation_id}"
            )
            
            # Editar código
            edit_result = await self.pig_manager.enable_direct_code_editing(
                session_id, operation_id, new_code
            )
            
            if not edit_result.get('success'):
                return edit_result
            
            result = {
                "success": True,
                "operation_id": operation_id,
                "affected_nodes": edit_result.get('affected_nodes', []),
                "new_parameters": edit_result.get('new_parameters', {}),
                "checkpoint_before": checkpoint_id,
                "validation_result": edit_result.get('validation_result', {})
            }
            
            # Regenerar modelo se solicitado
            if auto_regenerate:
                regen_result = await self._regenerate_model(session_id, edit_result.get('affected_nodes', []))
                result["regeneration_result"] = regen_result
            
            return result
            
        except Exception as e:
            logger.error(f"Erro na edição direta: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_parameters_batch(self, session_id: str, 
                                    parameter_updates: Dict[str, Any],
                                    auto_regenerate: bool = True) -> Dict[str, Any]:
        """
        Atualiza múltiplos parâmetros de uma vez
        
        Args:
            session_id: ID da sessão
            parameter_updates: Dicionário de parâmetros para atualizar
            auto_regenerate: Se deve regenerar o modelo automaticamente
            
        Returns:
            Resultado da atualização e regeneração (se solicitada)
        """
        try:
            # Usar atualização aprimorada do PIG Manager
            update_result = await self.pig_manager.enhanced_parameter_update(
                session_id, parameter_updates, auto_regenerate=False
            )
            
            if not update_result.get('success'):
                return update_result
            
            result = {
                "success": True,
                "updated_parameters": update_result.get('updated_parameters', []),
                "update_results": update_result.get('update_results', {}),
                "affected_nodes": update_result.get('affected_nodes', []),
                "checkpoint_before": update_result.get('checkpoint_before')
            }
            
            # Regenerar modelo se solicitado
            if auto_regenerate:
                regen_result = await self._regenerate_model(session_id, update_result.get('affected_nodes', []))
                result["regeneration_result"] = regen_result
            
            return result
            
        except Exception as e:
            logger.error(f"Erro na atualização de parâmetros: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_checkpoint(self, session_id: str, description: str = None) -> Dict[str, Any]:
        """
        Cria um checkpoint de versão
        
        Args:
            session_id: ID da sessão
            description: Descrição do checkpoint
            
        Returns:
            Resultado da criação do checkpoint
        """
        try:
            checkpoint_id = await self.pig_manager.create_version_checkpoint(session_id, description)
            
            return {
                "success": True,
                "checkpoint_id": checkpoint_id,
                "description": description,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao criar checkpoint: {e}")
            return {"success": False, "error": str(e)}
    
    async def rollback_to_checkpoint(self, session_id: str, checkpoint_id: str) -> Dict[str, Any]:
        """
        Faz rollback para um checkpoint específico
        
        Args:
            session_id: ID da sessão
            checkpoint_id: ID do checkpoint
            
        Returns:
            Resultado do rollback
        """
        try:
            rollback_result = await self.pig_manager.rollback_to_version(session_id, checkpoint_id)
            
            if rollback_result.get('success'):
                # Regenerar modelo após rollback
                regen_result = await self._regenerate_model(session_id)
                rollback_result["regeneration_result"] = regen_result
            
            return rollback_result
            
        except Exception as e:
            logger.error(f"Erro no rollback: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_edit_history(self, session_id: str) -> Dict[str, Any]:
        """
        Retorna histórico de edições da sessão
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Histórico de edições formatado
        """
        try:
            version_history = await self.pig_manager.get_version_history(session_id)
            
            # Formatar histórico para apresentação
            formatted_history = []
            for entry in version_history:
                formatted_entry = {
                    "type": entry.get('type'),
                    "timestamp": entry.get('timestamp'),
                    "description": self._format_history_description(entry),
                    "can_rollback": entry.get('type') == 'checkpoint'
                }
                
                if entry.get('type') == 'checkpoint':
                    checkpoint_data = entry.get('data', {})
                    formatted_entry["checkpoint_id"] = checkpoint_data.get('checkpoint_id')
                    formatted_entry["description"] = checkpoint_data.get('description')
                
                formatted_history.append(formatted_entry)
            
            return {
                "success": True,
                "history": formatted_history,
                "total_entries": len(formatted_history)
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter histórico: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_editable_content(self, session_id: str) -> Dict[str, Any]:
        """
        Retorna conteúdo editável atual da sessão
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Dados editáveis incluindo parâmetros e código
        """
        try:
            pig_state = await self.pig_manager.get_graph_state(session_id)
            
            # Construir código editável completo
            parameters = pig_state.get('parameters', {})
            operations = pig_state.get('operations', [])
            
            # Gerar código CadQuery editável
            editable_code = await self._build_editable_code(parameters, operations)
            
            return {
                "success": True,
                "parameters": parameters,
                "operations": operations,
                "editable_code": editable_code,
                "code_structure": {
                    "parameters_section": "# Parâmetros",
                    "operations_section": "# Operações de modelagem",
                    "result_variable": "result"
                }
            }
            
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
            validation_results = []
            
            # Validar código se fornecido
            if edited_code:
                code_validation = await self.pig_manager._validate_cadquery_code(edited_code)
                validation_results.append({
                    "type": "code",
                    "is_valid": code_validation.get('is_valid'),
                    "errors": [code_validation.get('error')] if not code_validation.get('is_valid') else [],
                    "warnings": code_validation.get('warnings', [])
                })
            
            # Validar parâmetros se fornecidos
            if parameter_updates:
                for param_name, param_value in parameter_updates.items():
                    param_validation = await self.pig_manager._validate_parameter_value(
                        session_id, param_name, param_value
                    )
                    validation_results.append({
                        "type": "parameter",
                        "parameter_name": param_name,
                        "is_valid": param_validation.get('is_valid'),
                        "errors": [param_validation.get('error')] if not param_validation.get('is_valid') else [],
                        "warnings": []
                    })
            
            # Resumo da validação
            all_valid = all(result.get('is_valid', False) for result in validation_results)
            total_errors = sum(len(result.get('errors', [])) for result in validation_results)
            total_warnings = sum(len(result.get('warnings', [])) for result in validation_results)
            
            return {
                "success": True,
                "is_valid": all_valid,
                "validation_results": validation_results,
                "summary": {
                    "total_checks": len(validation_results),
                    "total_errors": total_errors,
                    "total_warnings": total_warnings,
                    "can_proceed": all_valid
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na validação: {e}")
            return {"success": False, "error": str(e)}
    
    # MÉTODOS AUXILIARES
    
    async def _regenerate_model(self, session_id: str, affected_nodes: List[str] = None) -> Dict[str, Any]:
        """Regenera modelo após edições"""
        try:
            pig_state = await self.pig_manager.get_graph_state(session_id)
            
            # Criar plano de execução temporário para regeneração
            execution_plan = ExecutionPlan(
                description="Regeneração após edição",
                ast_nodes=[],
                new_parameters=pig_state.get('parameters', {}),
                cadquery_code=await self._build_full_cadquery_code(pig_state)
            )
            
            # Executar regeneração
            execution_result = await self.executor.execute_plan(session_id, execution_plan)
            
            return {
                "success": execution_result.status == "success",
                "execution_time": execution_result.execution_time,
                "model_data": execution_result.model_data,
                "error": execution_result.error_message if execution_result.status != "success" else None
            }
            
        except Exception as e:
            logger.error(f"Erro na regeneração: {e}")
            return {"success": False, "error": str(e)}
    
    async def _build_editable_code(self, parameters: Dict[str, Any], operations: List[Dict[str, Any]]) -> str:
        """Constrói código CadQuery editável"""
        code_lines = []
        
        # Seção de parâmetros
        code_lines.append("# Parâmetros")
        for param_name, param_info in parameters.items():
            param_value = param_info.get('value')
            if isinstance(param_value, str):
                code_lines.append(f'{param_name} = "{param_value}"')
            else:
                code_lines.append(f'{param_name} = {param_value}')
        
        code_lines.append("")
        
        # Seção de operações
        code_lines.append("# Operações de modelagem")
        code_lines.append("import cadquery as cq")
        code_lines.append("")
        
        for operation in operations:
            operation_code = operation.get('code', '')
            if operation_code.strip():
                code_lines.append(operation_code)
        
        return '\n'.join(code_lines)
    
    async def _build_full_cadquery_code(self, pig_state: Dict[str, Any]) -> str:
        """Constrói código CadQuery completo para execução"""
        parameters = pig_state.get('parameters', {})
        operations = pig_state.get('operations', [])
        
        return await self._build_editable_code(parameters, operations)
    
    def _format_history_description(self, entry: Dict[str, Any]) -> str:
        """Formata descrição de entrada do histórico"""
        entry_type = entry.get('type', 'unknown')
        
        if entry_type == 'checkpoint':
            return entry.get('data', {}).get('description', 'Checkpoint')
        elif entry_type == 'direct_edit':
            op_id = entry.get('data', {}).get('operation_id', 'unknown')
            return f"Edição direta da operação {op_id[:8]}"
        elif entry_type == 'parameter_update':
            params = list(entry.get('data', {}).get('parameter_updates', {}).keys())
            return f"Atualização de parâmetros: {', '.join(params[:3])}" + ("..." if len(params) > 3 else "")
        elif entry_type == 'load_previous':
            return "Carregamento de geração anterior"
        else:
            return f"Ação: {entry_type}" 