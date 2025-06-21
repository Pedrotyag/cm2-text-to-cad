import os
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import asyncio
import json

from src.core import CentralOrchestrator
from src.models import GeometrySelection
from src.core.planning_module import safe_json_dumps

# Configurar logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(
    title="Motor de Modelagem Conversacional Paramétrico (CM²)",
    description="Sistema Text-to-CAD com diálogo conversacional e modelagem paramétrica",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar arquivos estáticos e templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Inicializar orquestrador central
orchestrator = CentralOrchestrator()

# Modelos Pydantic para API
class UserInputRequest(BaseModel):
    message: str
    selected_geometry: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None

class SessionResponse(BaseModel):
    session_id: str
    status: str

# Gerenciador de conexões WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket conectado para sessão: {session_id}")
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket desconectado para sessão: {session_id}")
    
    async def send_personal_message(self, message: dict, session_id: str):
        if session_id in self.active_connections:
            try:
                websocket = self.active_connections[session_id]
                logger.info(f"Tentando enviar mensagem via WebSocket para sessão {session_id}")
                logger.debug(f"Tipo da mensagem: {message.get('type', 'unknown')}")
                
                # Serializar com função segura
                message_json = safe_json_dumps(message)
                logger.debug(f"Mensagem serializada com sucesso: {len(message_json)} caracteres")
                
                await websocket.send_text(message_json)
                logger.info(f"Mensagem enviada com sucesso para sessão {session_id}")
                
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem WebSocket para sessão {session_id}: {e}")
                logger.error(f"Tipo do erro: {type(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise

manager = ConnectionManager()

# Rotas principais
@app.get("/", response_class=HTMLResponse)
async def get_homepage(request: Request):
    """Página principal da aplicação"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/test", response_class=HTMLResponse)
async def get_test_page(request: Request):
    """Página de teste de detecção de geometria"""
    with open("test_detection.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

@app.get("/test_visualization", response_class=HTMLResponse)
async def get_test_visualization_page(request: Request):
    """Página de teste de visualização 3D"""
    with open("test_visualization.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

@app.get("/debug_viewport", response_class=HTMLResponse)
async def get_debug_viewport_page(request: Request):
    """Página de debug do viewport 3D"""
    with open("debug_viewport.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

@app.get("/test_websocket", response_class=HTMLResponse)
async def get_test_websocket_page(request: Request):
    """Página de teste de conectividade WebSocket"""
    with open("test_websocket.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

@app.get("/debug_connection", response_class=HTMLResponse)
async def get_debug_connection_page(request: Request):
    """Página de debug detalhado de conexão"""
    with open("test_connection_debug.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

@app.post("/api/session/start", response_model=SessionResponse)
async def start_session():
    """Inicia uma nova sessão de design"""
    try:
        session_id = await orchestrator.start_session()
        return SessionResponse(session_id=session_id, status="success")
    except Exception as e:
        logger.error(f"Erro ao iniciar sessão: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/send")
async def send_message(request: UserInputRequest):
    """Envia mensagem para o sistema (endpoint REST alternativo)"""
    try:
        # Converter selected_geometry se presente
        selected_geometry = None
        if request.selected_geometry:
            selected_geometry = GeometrySelection(**request.selected_geometry)
        
        # Processar mensagem
        response = await orchestrator.process_user_input(
            user_input=request.message,
            selected_geometry=selected_geometry,
            session_id=request.session_id
        )
        
        return {
            "response": response.model_dump(),
            "session_id": request.session_id or orchestrator.current_session_id
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/{session_id}/state")
async def get_session_state(session_id: str):
    """Retorna estado completo da sessão"""
    try:
        state = await orchestrator.get_session_state(session_id)
        return state
    except Exception as e:
        logger.error(f"Erro ao obter estado da sessão: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/{session_id}/parameters")
async def get_parameters(session_id: str):
    """Retorna parâmetros do modelo"""
    try:
        parameters = await orchestrator.pig_manager.get_parameters(session_id)
        return {"parameters": parameters}
    except Exception as e:
        logger.error(f"Erro ao obter parâmetros: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/{session_id}/operations")
async def get_operations(session_id: str):
    """Retorna operações do modelo"""
    try:
        operations = await orchestrator.pig_manager.get_operations(session_id)
        return {"operations": operations}
    except Exception as e:
        logger.error(f"Erro ao obter operações: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """Endpoint WebSocket para comunicação em tempo real"""
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receber mensagem do cliente
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Processar baseado no tipo de mensagem
            message_type = message_data.get("type")
            
            if message_type == "user_message":
                # Processar mensagem do usuário
                user_input = message_data.get("content", "")
                selected_geometry = message_data.get("selected_geometry")
                
                logger.info(f"Processando mensagem do usuário: '{user_input}' na sessão {session_id}")
                
                # Converter selected_geometry se presente
                geometry_selection = None
                if selected_geometry:
                    geometry_selection = GeometrySelection(**selected_geometry)
                    logger.debug(f"Geometria selecionada convertida: {geometry_selection}")
                
                # Processar com orquestrador
                logger.info(f"Chamando orquestrador para processar entrada do usuário")
                response = await orchestrator.process_user_input(
                    user_input=user_input,
                    selected_geometry=geometry_selection,
                    session_id=session_id
                )
                logger.info(f"Resposta recebida do orquestrador: {type(response)}")
                
                # Verificar se a resposta é serializável
                try:
                    response_data = response.model_dump()
                    logger.debug(f"Resposta serializada com sucesso: {len(str(response_data))} caracteres")
                except Exception as e:
                    logger.error(f"Erro ao serializar resposta: {e}")
                    logger.error(f"Tipo da resposta: {type(response)}")
                    logger.error(f"Atributos da resposta: {dir(response)}")
                    raise
                
                # Enviar resposta
                logger.info(f"Enviando resposta via WebSocket")
                await manager.send_personal_message({
                    "type": "system_response",
                    "data": response_data
                }, session_id)
                
            elif message_type == "parameter_update":
                # Atualização de parâmetro direto
                param_name = message_data.get("parameter_name")
                new_value = message_data.get("new_value")
                
                if param_name and new_value is not None:
                    try:
                        # Atualizar parâmetro via PIG
                        affected_nodes = await orchestrator.pig_manager.update_parameter_value(
                            session_id, param_name, new_value
                        )
                        
                        # Executar nós afetados
                        pig = await orchestrator.pig_manager.get_graph(session_id)
                        execution_result = await orchestrator.executor.execute_pig_nodes(
                            session_id, affected_nodes, pig
                        )
                        
                        # Enviar resultado
                        await manager.send_personal_message({
                            "type": "parameter_updated",
                            "data": {
                                "parameter_name": param_name,
                                "new_value": new_value,
                                "execution_result": execution_result.model_dump(),
                                "affected_nodes": affected_nodes
                            }
                        }, session_id)
                        
                    except Exception as e:
                        await manager.send_personal_message({
                            "type": "error",
                            "data": {"message": str(e)}
                        }, session_id)
            
            elif message_type == "get_state":
                # Solicitar estado atual
                state = await orchestrator.get_session_state(session_id)
                await manager.send_personal_message({
                    "type": "session_state",
                    "data": state
                }, session_id)
                
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"Erro no WebSocket: {e}")
        manager.disconnect(session_id)

@app.get("/api/session/{session_id}/export/{format}")
async def export_model(session_id: str, format: str):
    """Exportar modelo em formato CAD (STEP, IGES, STL)"""
    try:
        # Verificar se formato é suportado
        supported_formats = ["step", "iges", "stl"]
        if format.lower() not in supported_formats:
            raise HTTPException(
                status_code=400, 
                detail=f"Formato {format} não suportado. Formatos suportados: {supported_formats}"
            )
        
        # Obter código Python mais recente da sessão
        session_state = await orchestrator.get_session_state(session_id)
        
        if not session_state.get("last_execution_code"):
            raise HTTPException(
                status_code=404, 
                detail="Nenhum modelo encontrado para exportar"
            )
        
        # Executar código modificado para exportar no formato desejado
        from src.core.executor import SandboxedExecutor
        import tempfile
        import os
        from datetime import datetime
        
        executor = SandboxedExecutor()
        
        # EXTRAIR E INDENTAR CORRETAMENTE o código do modelo
        original_code = session_state["last_execution_code"]
        
        # Encontrar onde termina a criação do modelo
        if "# Extrair informações do modelo" in original_code:
            model_creation_code = original_code.split("# Extrair informações do modelo")[0]
        else:
            if "if 'result' in locals():" in original_code:
                model_creation_code = original_code.split("if 'result' in locals():")[0]
            else:
                lines = original_code.split('\n')
                model_lines = []
                for line in lines:
                    if 'print(' in line or 'EXECUTION_SUCCESS' in line:
                        break
                    model_lines.append(line)
                model_creation_code = '\n'.join(model_lines)
        
        # REMOVER imports duplicados e try/except aninhados
        lines = model_creation_code.split('\n')
        clean_lines = []
        skip_until_try = False
        
        for line in lines:
            stripped = line.strip()
            # Pular linhas que criam conflito
            if stripped.startswith('import cadquery as cq') and len(clean_lines) > 0:
                continue  # Pular import duplicado
            if stripped.startswith('import json') or stripped.startswith('import sys') or stripped.startswith('import traceback'):
                continue  # Pular imports desnecessários
            if stripped.startswith('from typing import'):
                continue  # Pular typing import
            if stripped.startswith('try:') and len(clean_lines) > 0:
                skip_until_try = True
                continue  # Pular try aninhado
            if skip_until_try and stripped and not stripped.startswith('#') and not stripped.startswith('    '):
                skip_until_try = False  # Chegou no código real
            if skip_until_try:
                continue
            
            # Garantir indentação correta para código dentro do try
            if stripped and not stripped.startswith('#'):
                if not line.startswith('    '):
                    line = '    ' + stripped
            
            clean_lines.append(line)
        
        clean_model_code = '\n'.join(clean_lines)
        
        # TEMPLATE FINAL PARA EXPORTAÇÃO
        export_code = f'''import cadquery as cq
from cadquery import exporters
import tempfile
import os

try:
{clean_model_code}
    
    # Exportar modelo
    if 'result' in locals():
        # Criar arquivo temporário
        with tempfile.NamedTemporaryFile(suffix='.{format}', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Exportar no formato solicitado
            exporters.export(result, temp_path)
            
            # Ler arquivo
            with open(temp_path, 'rb') as f:
                file_content = f.read()
                
            # Codificar em base64
            import base64
            file_base64 = base64.b64encode(file_content).decode('utf-8')
            
            print("EXPORT_SUCCESS")
            print(file_base64)
            
        finally:
            # Limpar arquivo temporário
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    else:
        print("EXPORT_ERROR: Nenhum objeto 'result' encontrado")
        
except Exception as e:
    print(f"EXPORT_ERROR: {{e}}")
    import traceback
    traceback.print_exc()
'''
        
        # SALVAR CÓDIGO DE EXPORTAÇÃO FINAL PARA DEBUG
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        debug_filename = f"debug_export_{timestamp}_{session_id[:8]}_{format}.py"
        debug_path = f"generated_codes/{debug_filename}"
        
        with open(debug_path, 'w', encoding='utf-8') as f:
            f.write(f"# Código de exportação CORRIGIDO gerado em {datetime.now().isoformat()}\n")
            f.write(f"# Session: {session_id}\n")
            f.write(f"# Format: {format}\n")
            f.write("# " + "="*60 + "\n\n")
            f.write(export_code)
        
        logger.info(f"Código de exportação CORRIGIDO salvo: {debug_path}")
        
        # USAR ARQUIVO LOCAL EM VEZ DE /tmp
        execution_filename = f"temp_export_{timestamp}_{session_id[:8]}_{format}.py"
        execution_path = f"generated_codes/{execution_filename}"
        
        with open(execution_path, 'w', encoding='utf-8') as f:
            f.write(export_code)
        
        logger.info(f"Código de execução salvo em: {execution_path}")
        
        # Executar código de exportação usando arquivo local
        import subprocess
        import asyncio
        
        try:
            process = await asyncio.create_subprocess_exec(
                'python', execution_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=30
            )
            
            output = stdout.decode('utf-8')
            error = stderr.decode('utf-8')
            
            if "EXPORT_SUCCESS" in output:
                # Extrair dados do arquivo
                lines = output.strip().split('\n')
                file_base64 = None
                
                for i, line in enumerate(lines):
                    if "EXPORT_SUCCESS" in line and i + 1 < len(lines):
                        file_base64 = lines[i + 1]
                        break
                
                if file_base64:
                    from fastapi.responses import Response
                    import base64
                    
                    # Decodificar e retornar arquivo
                    file_content = base64.b64decode(file_base64)
                    
                    # Definir MIME type
                    mime_types = {
                        "step": "application/stp",
                        "iges": "application/iges", 
                        "stl": "application/vnd.ms-pki.stl"
                    }
                    
                    # Limpar arquivo de execução temporário
                    try:
                        os.unlink(execution_path)
                    except:
                        pass
                    
                    return Response(
                        content=file_content,
                        media_type=mime_types.get(format, "application/octet-stream"),
                        headers={
                            "Content-Disposition": f"attachment; filename=modelo.{format}"
                        }
                    )
                else:
                    raise HTTPException(status_code=500, detail="Erro ao extrair dados exportados")
            else:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Erro na exportação: {error or 'Erro desconhecido'}"
                )
                
        except asyncio.TimeoutError:
            raise HTTPException(status_code=500, detail="Timeout na exportação")
        finally:
            # Limpar arquivo de execução se ainda existir
            try:
                if os.path.exists(execution_path):
                    os.unlink(execution_path)
            except:
                pass
            
    except Exception as e:
        logger.error(f"Erro ao exportar modelo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Endpoint de verificação de saúde"""
    return {"status": "healthy", "service": "CM² Text-to-CAD"}

if __name__ == "__main__":
    # Verificar variáveis de ambiente obrigatórias
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY não encontrada! Configure no arquivo .env")
        exit(1)
    
    # Iniciar servidor
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_excludes=[
            "gemini_responses/*",
            "generated_codes/*",
            "*.json",
            "*.py.tmp"
        ],
        log_level="info"
    ) 