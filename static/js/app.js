// App principal - Coordena todos os módulos
class CM2App {
    constructor() {
        this.sessionId = null;
        this.websocket = null;
        this.isConnected = false;
        this.isProcessing = false;
        this.messageCount = 0;
        this.selectedModel = 'gemini-2.5-flash';
        this.currentModelInfo = null;
        
        // Inicializar componentes
        this.threeSetup = new ThreeSetup('viewport-3d');
        this.websocketClient = new WebSocketClient();
        this.uiControls = new UIControls();
        
        this.init();
    }
    
    async init() {
        console.log('🚀 Inicializando CM² Text-to-CAD...');
        
        try {
            // Mostrar loading inicial
            this.showLoadingState();
            
            // 1. Iniciar sessão
            await this.startSession();
            
            // 2. Configurar WebSocket
            this.setupWebSocket();
            
            // 3. Configurar controles UI
            this.setupUIControls();
            
            // 4. Configurar Three.js
            this.threeSetup.init();
            
            // 5. Adicionar efeitos visuais
            this.setupVisualEffects();
            
            console.log('✅ CM² inicializado com sucesso!');
            // Não atualizar status aqui - será atualizado quando WebSocket conectar
            
            // Esconder loading
            this.hideLoadingState();
            
            // Animação de entrada
            this.playWelcomeAnimation();
            
        } catch (error) {
            console.error('❌ Erro ao inicializar CM²:', error);
            this.showError('Erro ao inicializar aplicação: ' + error.message);
            this.hideLoadingState();
        }
    }
    
    async startSession() {
        try {
            const response = await fetch('/api/session/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.sessionId = data.session_id;
            
            // Atualizar informações do modelo se disponíveis
            if (data.model_info) {
                this.currentModelInfo = data.model_info;
                this.updateModelDisplay();
            } else {
                // Se não veio na resposta, buscar separadamente
                await this.refreshModelInfo();
            }
            
            console.log('📝 Sessão iniciada:', this.sessionId);
            console.log('🤖 Modelo atual:', this.currentModelInfo);
            document.getElementById('session-info').textContent = `Conectando WebSocket...`;
            
        } catch (error) {
            throw new Error('Falha ao iniciar sessão: ' + error.message);
        }
    }
    
    setupWebSocket() {
        // Mostrar estado de conexão
        document.getElementById('session-info').textContent = 'Conectando WebSocket...';
        
        this.websocketClient.connect(this.sessionId, {
            onOpen: () => {
                console.log('🔌 WebSocket conectado');
                this.isConnected = true;
                this.updateConnectionStatus(true);
                
                // Solicitar informações do modelo se ainda não temos
                if (!this.currentModelInfo) {
                    this.refreshModelInfo();
                }
            },
            
            onClose: (event) => {
                console.log('🔌 WebSocket desconectado');
                this.isConnected = false;
                this.updateConnectionStatus(false);
                
                // Se não foi uma desconexão limpa, mostrar tentativa de reconexão
                if (!event.wasClean) {
                    document.getElementById('session-info').textContent = 'Tentando reconectar...';
                }
            },
            
            onMessage: (data) => {
                this.handleWebSocketMessage(data);
            },
            
            onError: (error) => {
                console.error('❌ Erro no WebSocket:', error);
                this.showError('Erro de comunicação: ' + error.message);
            }
        });
    }
    
    setupUIControls() {
        // Configurar envio de mensagens
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.getElementById('send-message');
        
        // Habilitar botão quando há texto
        chatInput.addEventListener('input', (e) => {
            const hasText = e.target.value.trim().length > 0;
            sendButton.disabled = !hasText || this.isProcessing;
            
            // Atualizar contador
            const counter = document.getElementById('input-counter');
            counter.textContent = `${e.target.value.length}/500`;
        });
        
        // Enviar com Enter
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Enviar com botão
        sendButton.addEventListener('click', () => {
            this.sendMessage();
        });
        
        // Quick actions
        document.querySelectorAll('.quick-action').forEach(button => {
            button.addEventListener('click', () => {
                const text = button.getAttribute('data-text');
                chatInput.value = text;
                chatInput.dispatchEvent(new Event('input'));
                chatInput.focus();
            });
        });
        
        // Controles do viewport
        document.getElementById('reset-view').addEventListener('click', () => {
            this.threeSetup.resetView();
        });
        
        document.getElementById('fit-view').addEventListener('click', () => {
            this.threeSetup.fitView();
        });
        
        document.getElementById('export-model').addEventListener('click', () => {
            this.exportModel();
        });
        
        // Refresh buttons
        document.getElementById('refresh-params').addEventListener('click', () => {
            this.refreshParameters();
        });
        
        document.getElementById('refresh-timeline').addEventListener('click', () => {
            this.refreshTimeline();
        });
        
        // Clear chat
        document.getElementById('clear-chat').addEventListener('click', () => {
            this.clearChat();
        });
        
        // Fechar modal de erro
        document.getElementById('close-error').addEventListener('click', () => {
            document.getElementById('error-modal').style.display = 'none';
        });
        
        const modelSelect = document.getElementById('model-select');
        if (modelSelect) {
            this.selectedModel = modelSelect.value;
            modelSelect.addEventListener('change', () => {
                this.selectedModel = modelSelect.value;
            });
        }
    }
    
    async sendMessage() {
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.getElementById('send-message');
        const message = chatInput.value.trim();
        
        if (!message || this.isProcessing || !this.isConnected) return;
        
        // Animação do botão de envio
        this.animateSendButton(sendButton, true);
        
        this.isProcessing = true;
        this.updateProcessingState(true);
        
        try {
            // Adicionar mensagem do usuário ao chat com animação
            this.addMessageToChat(message, 'user');
            
            // Animação de limpeza do input
            this.animateInputClear(chatInput);
            
            // Enviar via WebSocket
            this.websocketClient.send({
                type: 'user_message',
                content: message,
                selected_geometry: this.threeSetup.getSelectedGeometry(),
                selected_model: this.selectedModel
            });
            
        } catch (error) {
            console.error('❌ Erro ao enviar mensagem:', error);
            this.showError('Erro ao enviar mensagem: ' + error.message);
            this.isProcessing = false;
            this.updateProcessingState(false);
            this.animateSendButton(sendButton, false);
        }
    }
    
    handleWebSocketMessage(data) {
        console.log('📨 Mensagem recebida:', data);
        
        try {
            // Atualizar informações do modelo se disponíveis
            if (data.model_info) {
                this.currentModelInfo = data.model_info;
                this.updateModelDisplay();
            }
            
            switch (data.type) {
                case 'model_info':
                    // Mensagem específica de informações do modelo
                    if (data.model_info) {
                        this.currentModelInfo = data.model_info;
                        this.updateModelDisplay();
                        console.log('🤖 Model info received:', this.currentModelInfo);
                    }
                    break;
                    
                case 'system_response':
                    this.handleSystemResponse(data.response);
                    break;
                    
                case 'parameter_update':
                    this.handleParameterUpdate(data);
                    break;
                    
                case 'session_state':
                    this.handleSessionState(data.state);
                    break;
                    
                case 'error':
                    this.showError(data.message || 'Erro desconhecido');
                    break;
                    
                default:
                    console.warn('Tipo de mensagem desconhecido:', data.type);
            }
        } catch (error) {
            console.error('❌ Erro ao processar mensagem:', error);
            this.showError('Erro ao processar resposta do servidor');
        }
    }
    
    handleSystemResponse(response) {
        this.isProcessing = false;
        this.updateProcessingState(false);
        
        // Resetar botão de envio
        const sendButton = document.getElementById('send-message');
        this.animateSendButton(sendButton, false);
        
        // DEBUG: Log completo da resposta
        console.log('🔍 RESPOSTA COMPLETA:', JSON.stringify(response, null, 2));
        
        // Extrair content corretamente da estrutura  
        const content = response.content || 'Resposta recebida';
        
        // Adicionar resposta do sistema com animação
        this.addMessageToChat(content, 'system');
        
        // Mostrar notificação sutil
        this.showNotification('Nova resposta recebida', 'success');
        
        // DEBUG: Log completo para verificar model_state
        console.log('🔍 VERIFICANDO MODEL_STATE NA RESPOSTA:');
        console.log('  response.model_state:', response.model_state);
        console.log('  typeof model_state:', typeof response.model_state);
        console.log('  model_state existe?', !!response.model_state);
        
        // Atualizar modelo se presente
        const modelState = response.model_state;
        if (modelState && typeof modelState === 'object') {
            console.log('🎨 Modelo recebido via model_state, removendo overlay e carregando modelo...');
            console.log('🔍 Dados do model_state:', modelState);
            this.hideViewportOverlay();
            if (modelState.code) {
                this.threeSetup.loadModel(modelState.code);
            } else {
                // Se não há código mas há dados do modelo, usar updateModel
                this.threeSetup.updateModel(modelState);
            }
        } else {
            console.log('⚠️ Nenhum model_state válido encontrado na resposta');
            console.log('📋 Tentando fallback com execution_plan...');
            
            // FALLBACK: Verificar se há dados de execução bem-sucedida nos logs do servidor
            // Parece que o modelo é gerado mas não está sendo enviado no model_state
            if (response.execution_plan) {
                console.log('🔧 Tentando gerar modelo a partir do execution_plan...');
                // Criar dados de modelo genérico baseado nos parâmetros
                const params = response.execution_plan.new_parameters;
                if (params) {
                    console.log('📊 Parâmetros encontrados:', params);
                    // IMPORTANTE: Criar um modelo básico baseado nos parâmetros para visualização
                    const genericModel = this.createModelFromParameters(params);
                    this.hideViewportOverlay();
                    this.threeSetup.updateModel(genericModel);
                    console.log('✅ Modelo genérico criado para visualização');
                    console.log('🎯 Modelo genérico:', genericModel);
                } else {
                    console.log('❌ Nenhum parâmetro encontrado no execution_plan');
                }
            } else {
                console.log('❌ Nenhum execution_plan encontrado na resposta');
            }
        }
        
        // Atualizar parâmetros com animação
        const parameters = response.execution_plan?.new_parameters || response.parameters;
        if (parameters) {
            this.updateParametersPanel(parameters);
            
            // Se há parâmetros, significa que o modelo foi gerado com sucesso
            // Forçar remoção do overlay caso ainda esteja visível
            console.log('📊 Parâmetros recebidos, garantindo que overlay seja removido...');
            this.hideViewportOverlay();
        }
    }
    
    handleParameterUpdate(data) {
        console.log('🔧 Parâmetro atualizado:', data.parameter_name, '=', data.new_value);
        
        // Atualizar modelo se a execução foi bem-sucedida
        if (data.execution_result.status === 'success') {
            this.threeSetup.updateModel(data.execution_result.model_data);
            this.addMessageToChat(
                `Parâmetro "${data.parameter_name}" atualizado para ${data.new_value}. Modelo regenerado.`,
                'system'
            );
        } else {
            this.showError('Erro ao atualizar parâmetro: ' + data.execution_result.error_message);
        }
        
        this.refreshParameters();
    }
    
    handleSessionState(state) {
        console.log('📊 Estado da sessão recebido:', state);
        
        // Atualizar modelo se houver
        if (state.model_state) {
            this.threeSetup.updateModel(state.model_state);
            this.hideViewportOverlay();
        }
        
        // Atualizar parâmetros e timeline
        this.refreshParameters();
        this.refreshTimeline();
    }
    
    addMessageToChat(content, type = 'system') {
        const chatMessages = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        // Incrementar contador de mensagens para animação
        this.messageCount++;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = type === 'user' ? '👤' : '🤖';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = this.formatMessageContent(content);
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        
        // Adicionar com animação
        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateY(20px)';
        messageDiv.style.animationDelay = '0s';
        
        chatMessages.appendChild(messageDiv);
        
        // Animar entrada
        requestAnimationFrame(() => {
            messageDiv.style.transition = 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
            messageDiv.style.opacity = '1';
            messageDiv.style.transform = 'translateY(0)';
        });
        
        // Auto-scroll suave
        this.smoothScrollToBottom(chatMessages);
        
        // Vibração sutil para feedback (se suportado)
        if (navigator.vibrate) {
            navigator.vibrate(10);
        }
    }
    
    formatMessageContent(content) {
        // Verificar se content é válido
        if (!content || typeof content !== 'string') {
            console.warn('⚠️ Content inválido para formatação:', content);
            return 'Conteúdo inválido';
        }
        
        // Converter quebras de linha e formatação básica
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
    }
    
    async refreshParameters() {
        if (!this.sessionId) return;
        
        try {
            const response = await fetch(`/api/session/${this.sessionId}/parameters`);
            const data = await response.json();
            
            this.updateParametersPanel(data.parameters);
            
        } catch (error) {
            console.error('❌ Erro ao buscar parâmetros:', error);
        }
    }
    
    async refreshTimeline() {
        if (!this.sessionId) return;
        
        try {
            const response = await fetch(`/api/session/${this.sessionId}/operations`);
            const data = await response.json();
            
            this.updateTimelinePanel(data.operations);
            
        } catch (error) {
            console.error('❌ Erro ao buscar operações:', error);
        }
    }
    
    updateParametersPanel(parameters) {
        const parametersList = document.getElementById('parameters-list');
        
        if (!parameters || Object.keys(parameters).length === 0) {
            parametersList.innerHTML = `
                <div class="no-parameters">
                    <p>Nenhum parâmetro ainda. Crie um modelo para ver os parâmetros!</p>
                </div>
            `;
            return;
        }
        
        // Animação de saída
        parametersList.style.opacity = '0.5';
        parametersList.style.transform = 'translateY(10px)';
        
        setTimeout(() => {
            parametersList.innerHTML = '';
            
            Object.entries(parameters).forEach(([name, value], index) => {
                const paramItem = document.createElement('div');
                paramItem.className = 'parameter-item';
                paramItem.style.animationDelay = `${index * 0.1}s`;
                
                paramItem.innerHTML = `
                    <div class="parameter-name">${name}</div>
                    <div class="parameter-value">
                        <input type="number" 
                               class="parameter-input" 
                               value="${value}" 
                               data-param="${name}"
                               step="0.1">
                        <span class="parameter-unit">mm</span>
                    </div>
                `;
                
                // Adicionar event listener para mudanças
                const input = paramItem.querySelector('.parameter-input');
                input.addEventListener('change', (e) => {
                    this.updateParameter(name, parseFloat(e.target.value));
                    
                    // Feedback visual
                    input.style.borderColor = '#2ecc71';
                    setTimeout(() => {
                        input.style.borderColor = '';
                    }, 1000);
                });
                
                parametersList.appendChild(paramItem);
            });
            
            // Animação de entrada
            setTimeout(() => {
                parametersList.style.transition = 'all 0.3s ease-out';
                parametersList.style.opacity = '1';
                parametersList.style.transform = 'translateY(0)';
            }, 50);
        }, 200);
    }
    
    updateTimelinePanel(operations) {
        const timeline = document.getElementById('operations-timeline');
        
        if (operations.length === 0) {
            timeline.innerHTML = '<div class="no-operations"><p>Nenhuma operação ainda. As operações aparecerão aqui conforme você cria o modelo.</p></div>';
            return;
        }
        
        timeline.innerHTML = '';
        
        operations.forEach((operation, index) => {
            const opDiv = document.createElement('div');
            opDiv.className = 'operation-item';
            
            const icon = this.getOperationIcon(operation.type);
            
            opDiv.innerHTML = `
                <div class="operation-icon">${icon}</div>
                <div class="operation-details">
                    <div class="operation-name">${operation.name}</div>
                    <div class="operation-description">${operation.description || operation.type}</div>
                </div>
            `;
            
            timeline.appendChild(opDiv);
        });
    }
    
    getOperationIcon(operationType) {
        const icons = {
            'box': '📦',
            'cylinder': '🥫',
            'sphere': '⚾',
            'extrude': '↗️',
            'cut': '✂️',
            'fillet': '🔄',
            'chamfer': '📐'
        };
        
        return icons[operationType] || '⚙️';
    }
    
    updateParameter(paramName, newValue) {
        if (!this.isConnected) {
            this.showError('Não conectado ao servidor');
            return;
        }
        
        this.websocketClient.send({
            type: 'parameter_update',
            parameter_name: paramName,
            new_value: newValue
        });
    }
    
    clearChat() {
        const chatMessages = document.getElementById('chat-messages');
        const systemMessage = chatMessages.querySelector('.system-message');
        
        // Manter apenas a mensagem inicial do sistema
        chatMessages.innerHTML = '';
        if (systemMessage) {
            chatMessages.appendChild(systemMessage);
        }
    }
    
    hideViewportOverlay() {
        const overlay = document.querySelector('.viewport-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }
    
    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('session-info');
        const statusIndicator = document.getElementById('connection-status');
        
        if (connected) {
            statusElement.innerHTML = `
                <div class="status-container">
                    <span class="status-text">Sessão: ${this.sessionId}</span>
                    ${this.getModelStatusHTML()}
                </div>
            `;
            statusIndicator.className = 'status-indicator connected';
            statusIndicator.title = 'Conectado';
        } else {
            statusElement.textContent = 'Desconectado - Tentando reconectar...';
            statusIndicator.className = 'status-indicator disconnected';
            statusIndicator.title = 'Desconectado';
        }
    }
    
    updateProcessingState(processing) {
        const indicator = document.getElementById('processing-indicator');
        const sendButton = document.getElementById('send-message');
        const chatInput = document.getElementById('chat-input');
        
        if (processing) {
            indicator.style.cssText = `
                display: flex;
                opacity: 0;
                transform: translateY(10px);
                transition: all 0.3s ease-out;
            `;
            
            requestAnimationFrame(() => {
                indicator.style.opacity = '1';
                indicator.style.transform = 'translateY(0)';
            });
            
            sendButton.disabled = true;
            chatInput.style.opacity = '0.7';
            
        } else {
            indicator.style.opacity = '0';
            indicator.style.transform = 'translateY(10px)';
            
            setTimeout(() => {
                indicator.style.display = 'none';
            }, 300);
            
            sendButton.disabled = chatInput.value.trim() === '';
            chatInput.style.opacity = '1';
        }
    }
    
    async exportModel() {
        console.log('📥 Iniciando exportação de modelo...');
        
        if (!this.sessionId) {
            this.showError('Nenhuma sessão ativa para exportar');
            return;
        }
        
        try {
            // Mostrar dialog de seleção de formato
            const format = await this.showExportDialog();
            if (!format) return; // Usuário cancelou
            
            console.log(`📥 Exportando modelo em formato: ${format}`);
            this.showNotification(`Exportando modelo em formato ${format.toUpperCase()}...`, 'info');
            
            // Fazer requisição de exportação
            const response = await fetch(`/api/session/${this.sessionId}/export/${format}`);
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Erro na exportação');
            }
            
            // Baixar arquivo
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `modelo_cm2.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            console.log('✅ Modelo exportado com sucesso!');
            this.showNotification(`Modelo exportado em ${format.toUpperCase()} com sucesso!`, 'success');
            
        } catch (error) {
            console.error('❌ Erro na exportação:', error);
            this.showError(`Erro na exportação: ${error.message}`);
        }
    }
    
    showExportDialog() {
        return new Promise((resolve) => {
            // Criar modal de exportação
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
                backdrop-filter: blur(10px);
            `;
            
            modal.innerHTML = `
                <div class="modal-content" style="
                    background: white;
                    border-radius: 12px;
                    padding: 30px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    max-width: 400px;
                    width: 90%;
                    text-align: center;
                ">
                    <h3 style="margin-bottom: 20px; color: #2c3e50;">📥 Exportar Modelo CAD</h3>
                    <p style="margin-bottom: 25px; color: #7f8c8d;">
                        Escolha o formato de exportação:
                    </p>
                    
                    <div style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 25px;">
                        <button class="export-format-btn" data-format="step" style="
                            padding: 15px 20px;
                            border: 2px solid #3498db;
                            background: white;
                            border-radius: 8px;
                            cursor: pointer;
                            transition: all 0.2s;
                            font-weight: 500;
                            color: #3498db;
                        ">
                            📐 STEP (.step) - Recomendado para CAD
                        </button>
                        
                        <button class="export-format-btn" data-format="iges" style="
                            padding: 15px 20px;
                            border: 2px solid #9b59b6;
                            background: white;
                            border-radius: 8px;
                            cursor: pointer;
                            transition: all 0.2s;
                            font-weight: 500;
                            color: #9b59b6;
                        ">
                            🔧 IGES (.iges) - Compatibilidade Universal
                        </button>
                        
                        <button class="export-format-btn" data-format="stl" style="
                            padding: 15px 20px;
                            border: 2px solid #e74c3c;
                            background: white;
                            border-radius: 8px;
                            cursor: pointer;
                            transition: all 0.2s;
                            font-weight: 500;
                            color: #e74c3c;
                        ">
                            🖨️ STL (.stl) - Para Impressão 3D
                        </button>
                    </div>
                    
                    <div style="display: flex; gap: 12px; justify-content: center;">
                        <button id="cancel-export" style="
                            padding: 12px 25px;
                            border: 1px solid #bdc3c7;
                            background: white;
                            border-radius: 6px;
                            cursor: pointer;
                            color: #7f8c8d;
                        ">Cancelar</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Adicionar eventos
            const formatButtons = modal.querySelectorAll('.export-format-btn');
            const cancelBtn = modal.querySelector('#cancel-export');
            
            formatButtons.forEach(btn => {
                btn.addEventListener('mouseenter', () => {
                    btn.style.background = btn.style.borderColor;
                    btn.style.color = 'white';
                });
                
                btn.addEventListener('mouseleave', () => {
                    btn.style.background = 'white';
                    btn.style.color = btn.style.borderColor;
                });
                
                btn.addEventListener('click', () => {
                    const format = btn.dataset.format;
                    document.body.removeChild(modal);
                    resolve(format);
                });
            });
            
            cancelBtn.addEventListener('click', () => {
                document.body.removeChild(modal);
                resolve(null);
            });
            
            // Fechar clicando fora
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    document.body.removeChild(modal);
                    resolve(null);
                }
            });
        });
    }
    
    showError(message) {
        const modal = document.getElementById('error-modal');
        const errorMessage = document.getElementById('error-message');
        
        errorMessage.textContent = message;
        modal.style.display = 'flex';
        
        // Animação de entrada
        modal.style.opacity = '0';
        requestAnimationFrame(() => {
            modal.style.transition = 'opacity 0.3s ease-out';
            modal.style.opacity = '1';
        });
        
        // Vibração para feedback de erro
        if (navigator.vibrate) {
            navigator.vibrate([100, 50, 100]);
        }
        
        // Mostrar notificação também
        this.showNotification(message, 'error');
    }

    showLoadingState() {
        const overlay = document.querySelector('.viewport-overlay');
        if (overlay) {
            overlay.innerHTML = `
                <div class="loading-message">
                    <div class="loading-spinner"></div>
                    <p>Inicializando CM²...</p>
                </div>
            `;
            overlay.style.cssText = `
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(15px);
            `;
        }
    }

    hideLoadingState() {
        const overlay = document.querySelector('.viewport-overlay');
        if (overlay) {
            overlay.style.cssText = `
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(15px);
                transition: opacity 0.5s ease-out;
            `;
            
            setTimeout(() => {
                overlay.innerHTML = `
                    <div class="no-model-message">
                        <p>Comece conversando para criar seu primeiro modelo!</p>
                    </div>
                `;
            }, 500);
        }
    }

    playWelcomeAnimation() {
        // Animar elementos da interface
        const elements = [
            '.app-header',
            '.viewport-panel',
            '.chat-panel',
            '.parameters-panel',
            '.timeline-panel'
        ];
        
        elements.forEach((selector, index) => {
            const element = document.querySelector(selector);
            if (element) {
                element.style.opacity = '0';
                element.style.transform = 'translateY(20px)';
                element.style.transition = 'all 0.6s cubic-bezier(0.16, 1, 0.3, 1)';
                
                setTimeout(() => {
                    element.style.opacity = '1';
                    element.style.transform = 'translateY(0)';
                }, index * 100);
            }
        });
    }

    setupVisualEffects() {
        // Adicionar efeito ripple aos botões
        this.addRippleEffect();
        
        // Configurar parallax sutil
        this.setupParallax();
        
        // Adicionar feedback visual às interações
        this.setupInteractionFeedback();
        
        // Animações de entrada suaves
        this.setupScrollAnimations();
    }

    addRippleEffect() {
        const rippleButtons = document.querySelectorAll('.btn-primary, .btn-icon, .quick-action');
        
        rippleButtons.forEach(button => {
            button.addEventListener('mousedown', (e) => {
                const rect = button.getBoundingClientRect();
                const size = Math.max(rect.width, rect.height);
                const x = e.clientX - rect.left - size / 2;
                const y = e.clientY - rect.top - size / 2;
                
                const ripple = document.createElement('span');
                ripple.className = 'ripple-effect';
                ripple.style.cssText = `
                    width: ${size}px;
                    height: ${size}px;
                    left: ${x}px;
                    top: ${y}px;
                `;
                
                button.appendChild(ripple);
                
                setTimeout(() => {
                    ripple.remove();
                }, 600);
            });
        });
    }

    setupParallax() {
        const header = document.querySelector('.app-header');
        if (header) {
            document.addEventListener('mousemove', (e) => {
                const x = (e.clientX / window.innerWidth) * 2 - 1;
                const y = (e.clientY / window.innerHeight) * 2 - 1;
                
                header.style.transform = `translate3d(${x * 2}px, ${y * 2}px, 0)`;
            });
        }
    }

    setupInteractionFeedback() {
        // Feedback visual para inputs
        const inputs = document.querySelectorAll('input, textarea');
        inputs.forEach(input => {
            input.addEventListener('focus', () => {
                input.parentElement?.classList.add('focused');
            });
            
            input.addEventListener('blur', () => {
                input.parentElement?.classList.remove('focused');
            });
        });

        // Feedback para mensagens
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) {
            chatMessages.addEventListener('scroll', () => {
                const messages = chatMessages.querySelectorAll('.message');
                messages.forEach(message => {
                    const rect = message.getBoundingClientRect();
                    const chatRect = chatMessages.getBoundingClientRect();
                    
                    if (rect.top >= chatRect.top && rect.bottom <= chatRect.bottom) {
                        message.classList.add('in-view');
                    }
                });
            });
        }
    }

    setupScrollAnimations() {
        // Observador de interseção para animações
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        // Observar elementos que devem ser animados
        const animatedElements = document.querySelectorAll('.parameter-item, .operation-item');
        animatedElements.forEach(el => observer.observe(el));
    }

    animateSendButton(button, sending) {
        const btnText = button.querySelector('.btn-text');
        const btnLoading = button.querySelector('.btn-loading');
        
        if (sending) {
            button.style.transform = 'scale(0.95)';
            setTimeout(() => {
                button.style.transform = 'scale(1)';
                if (btnText) btnText.style.display = 'none';
                if (btnLoading) btnLoading.style.display = 'inline-flex';
            }, 150);
        } else {
            if (btnText) btnText.style.display = 'inline';
            if (btnLoading) btnLoading.style.display = 'none';
        }
    }

    animateInputClear(input) {
        input.style.transform = 'scale(0.98)';
        input.value = '';
        input.dispatchEvent(new Event('input'));
        
        setTimeout(() => {
            input.style.transform = 'scale(1)';
        }, 200);
    }

    smoothScrollToBottom(container) {
        const targetScroll = container.scrollHeight - container.clientHeight;
        const startScroll = container.scrollTop;
        const distance = targetScroll - startScroll;
        const duration = 500;
        
        let startTime = null;
        
        const animateScroll = (currentTime) => {
            if (startTime === null) startTime = currentTime;
            const timeElapsed = currentTime - startTime;
            const progress = Math.min(timeElapsed / duration, 1);
            
            // Easing function (easeOutCubic)
            const easeProgress = 1 - Math.pow(1 - progress, 3);
            
            container.scrollTop = startScroll + (distance * easeProgress);
            
            if (timeElapsed < duration) {
                requestAnimationFrame(animateScroll);
            }
        };
        
        requestAnimationFrame(animateScroll);
    }

    createModelFromParameters(params) {
        console.log('🏗️ Criando modelo genérico a partir dos parâmetros:', params);
        
        // Analisar parâmetros para determinar tipo de geometria
        const paramNames = Object.keys(params);
        console.log('📋 Nomes dos parâmetros:', paramNames);
        
        // Detectar se é cilindro SIMPLES
        if (paramNames.some(name => name.includes('cylinder_radius') || name.includes('cylinder_height')) && 
            !paramNames.some(name => name.includes('base_') || name.includes('box_'))) {
            
            const radius = params.cylinder_radius || params.radius || 50;
            const height = params.cylinder_height || params.height || 100;
            
            console.log('🎯 DETECTADO: Cilindro Simples');
            console.log(`   Raio: ${radius}, Altura: ${height}`);
            
            return {
                type: "solid",
                bounding_box: {
                    min: [-radius, -radius, -height/2],
                    max: [radius, radius, height/2]
                },
                volume: Math.PI * radius * radius * height,
                center_of_mass: [0, 0, 0],
                geometry_hint: "cylinder"
            };
        }
        
        // Detectar se é GEOMETRIA COMPLEXA (união de primitivas)
        if (paramNames.some(name => name.includes('cylinder_')) && 
            paramNames.some(name => name.includes('base_'))) {
            
            console.log('🎯 DETECTADO: Geometria Complexa (Cilindro + Base)');
            
            // Calcular dimensões da união
            const cylinderRadius = params.cylinder_radius || 100;
            const cylinderHeight = params.cylinder_height || 200;
            const baseWidth = params.base_width || 100;
            const baseHeight = params.base_height || 20;
            const baseDepth = params.base_depth || 50;
            
            console.log(`   Cilindro: raio=${cylinderRadius}, altura=${cylinderHeight}`);
            console.log(`   Base: largura=${baseWidth}, altura=${baseHeight}, profundidade=${baseDepth}`);
            
            // Calcular bounding box da união
            const maxRadius = Math.max(cylinderRadius, baseWidth/2, baseDepth/2);
            const totalHeight = baseHeight + cylinderHeight;
            const minZ = -baseHeight/2;
            const maxZ = baseHeight/2 + cylinderHeight;
            
            // Estimar volume (cilindro + caixa, mas com possível sobreposição)
            const cylinderVolume = Math.PI * cylinderRadius * cylinderRadius * cylinderHeight;
            const baseVolume = baseWidth * baseHeight * baseDepth;
            const estimatedVolume = cylinderVolume + baseVolume * 0.8; // Reduzir para simular sobreposição
            
            console.log(`   Volume estimado: ${estimatedVolume.toFixed(2)}`);
            console.log(`   Bounding box: [${-maxRadius}, ${-maxRadius}, ${minZ}] até [${maxRadius}, ${maxRadius}, ${maxZ}]`);
            
            return {
                type: "solid",
                bounding_box: {
                    min: [-maxRadius, -maxRadius, minZ],
                    max: [maxRadius, maxRadius, maxZ]
                },
                volume: estimatedVolume,
                center_of_mass: [0, 0, (minZ + maxZ) / 2],
                geometry_hint: "cylinder" // Usar hint de cilindro para renderização
            };
        }
        
        // Detectar se é caixa simples
        if (paramNames.some(name => name.includes('width') || name.includes('base_')) && 
            !paramNames.some(name => name.includes('cylinder_'))) {
            
            const width = params.base_width || params.width || 100;
            const height = params.base_height || params.height || 50;
            const depth = params.base_depth || params.depth || 50;
            
            console.log('🎯 DETECTADO: Caixa Simples');
            console.log(`   Dimensões: ${width} x ${height} x ${depth}`);
            
            return {
                type: "solid",
                bounding_box: {
                    min: [-width/2, -depth/2, -height/2],
                    max: [width/2, depth/2, height/2]
                },
                volume: width * height * depth,
                center_of_mass: [0, 0, 0],
                geometry_hint: "box"
            };
        }
        
        // Modelo genérico se não conseguir determinar
        console.log('🎯 DETECTADO: Geometria Genérica (fallback)');
        return {
            type: "solid",
            bounding_box: {
                min: [-50, -50, -25],
                max: [50, 50, 25]
            },
            volume: 125000,
            center_of_mass: [0, 0, 0],
            geometry_hint: "generic"
        };
    }

    showNotification(message, type = 'info') {
        // Criar notificação toast
        const notification = document.createElement('div');
        notification.className = `notification toast-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#2ecc71' : type === 'error' ? '#e74c3c' : '#3498db'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1001;
            transform: translateX(100%);
            transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            font-weight: 500;
            backdrop-filter: blur(10px);
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Animar entrada
        requestAnimationFrame(() => {
            notification.style.transform = 'translateX(0)';
        });
        
        // Auto-remover
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }

    updateModelDisplay() {
        // Atualizar display do modelo na interface
        const modelDisplays = document.querySelectorAll('.model-info-display');
        modelDisplays.forEach(display => {
            display.innerHTML = this.getModelStatusHTML();
        });
        
        // Atualizar status na barra superior se conectado
        if (this.isConnected) {
            this.updateConnectionStatus(true);
        }
        
        // Atualizar seletor de modelo baseado no provider
        this.updateModelSelector();
        
        // Log detalhado
        if (this.currentModelInfo) {
            console.log(`🤖 Modelo ativo: ${this.currentModelInfo.provider} - ${this.currentModelInfo.model_name}`);
            if (this.currentModelInfo.is_local) {
                console.log(`🏠 Modelo local em: ${this.currentModelInfo.base_url}`);
            }
        }
    }

    updateModelSelector() {
        const modelSelect = document.getElementById('model-select');
        if (!modelSelect || !this.currentModelInfo) return;
        
        if (this.currentModelInfo.is_local) {
            // Ollama - desabilitar seletor e mostrar modelo atual
            modelSelect.disabled = true;
            modelSelect.innerHTML = `
                <option value="${this.currentModelInfo.model_name}">
                    🏠 ${this.currentModelInfo.model_name}
                </option>
            `;
            modelSelect.title = `Usando Ollama - Modelo configurado no servidor: ${this.currentModelInfo.model_name}`;
        } else {
            // Gemini - habilitar seletor
            modelSelect.disabled = false;
            modelSelect.innerHTML = `
                <option value="gemini-2.5-flash">☁️ Gemini Flash</option>
                <option value="gemini-2.5-pro">☁️ Gemini Pro</option>
            `;
            modelSelect.value = this.currentModelInfo.model_name;
            modelSelect.title = "Selecione o modelo Gemini";
        }
    }

    getModelStatusHTML() {
        if (!this.currentModelInfo) {
            return '<span class="model-status loading">🔄 Carregando modelo...</span>';
        }
        
        // Check if model info has error
        if (this.currentModelInfo.status === 'error') {
            return '<span class="model-status error">❌ Erro no modelo</span>';
        }
        
        const isLocal = this.currentModelInfo.is_local;
        const provider = this.currentModelInfo.provider;
        const modelName = this.currentModelInfo.model_name;
        
        // Encurtar nome do modelo se muito longo
        const shortModelName = modelName.length > 30 
            ? modelName.substring(0, 30) + '...' 
            : modelName;
        
        const statusClass = isLocal ? 'local' : 'cloud';
        const icon = isLocal ? '🏠' : '☁️';
        const tooltip = `${provider} - ${modelName} (${isLocal ? 'Local' : 'Cloud'})`;
        
        return `
            <span class="model-status ${statusClass}" title="${tooltip}">
                ${icon} ${provider}: ${shortModelName}
            </span>
        `;
    }

    async refreshModelInfo() {
        try {
            console.log('🔄 Refreshing model info...');
            const response = await fetch('/api/model/info');
            if (response.ok) {
                const modelInfo = await response.json();
                this.currentModelInfo = modelInfo;
                this.updateModelDisplay();
                console.log('✅ Model info refreshed:', modelInfo);
            } else {
                console.error('❌ Failed to fetch model info:', response.status);
            }
        } catch (error) {
            console.error('❌ Erro ao atualizar informações do modelo:', error);
        }
    }
}

// Inicializar aplicação quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.cm2App = new CM2App();
}); 