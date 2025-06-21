class EditManager {
    constructor(websocket) {
        this.ws = websocket;
        this.currentSessionId = null;
        this.editHistory = [];
        this.editCapabilities = {};
        this.setupEventListeners();
    }

    setSession(sessionId) {
        this.currentSessionId = sessionId;
        this.loadEditCapabilities();
    }

    setupEventListeners() {
        // Event listener para respostas de edição
        if (this.ws) {
            this.ws.addEventListener('message', (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'edit_response') {
                    this.handleEditResponse(data.data);
                }
            });
        }
    }

    // LOAD PREVIOUS GENERATION
    async loadForEditing(filePath = null) {
        try {
            const response = await fetch('/api/edit/load', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.currentSessionId,
                    file_path: filePath
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showEditInterface(result.data);
                this.showMessage('Modelo carregado para edição', 'success');
            } else {
                this.showMessage(`Erro ao carregar: ${result.error}`, 'error');
            }

            return result;
        } catch (error) {
            console.error('Erro ao carregar para edição:', error);
            this.showMessage('Erro ao carregar modelo', 'error');
            return { success: false, error: error.message };
        }
    }

    // DIRECT CODE EDITING
    async editCodeDirectly(operationId, newCode, autoRegenerate = true) {
        try {
            const response = await fetch('/api/edit/code', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.currentSessionId,
                    operation_id: operationId,
                    new_code: newCode,
                    auto_regenerate: autoRegenerate
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showMessage('Código editado com sucesso', 'success');
                if (autoRegenerate && result.regeneration_result) {
                    this.updateModelViewer(result.regeneration_result.model_data);
                }
            } else {
                this.showMessage(`Erro na edição: ${result.error}`, 'error');
            }

            return result;
        } catch (error) {
            console.error('Erro na edição de código:', error);
            this.showMessage('Erro ao editar código', 'error');
            return { success: false, error: error.message };
        }
    }

    // PARAMETER UPDATES
    async updateParametersBatch(parameterUpdates, autoRegenerate = true) {
        try {
            const response = await fetch('/api/edit/parameters', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.currentSessionId,
                    parameter_updates: parameterUpdates,
                    auto_regenerate: autoRegenerate
                })
            });

            const result = await response.json();
            
            if (result.success) {
                const updatedParams = result.updated_parameters || [];
                this.showMessage(`Parâmetros atualizados: ${updatedParams.join(', ')}`, 'success');
                
                if (autoRegenerate && result.regeneration_result) {
                    this.updateModelViewer(result.regeneration_result.model_data);
                }
            } else {
                this.showMessage(`Erro na atualização: ${result.error}`, 'error');
            }

            return result;
        } catch (error) {
            console.error('Erro na atualização de parâmetros:', error);
            this.showMessage('Erro ao atualizar parâmetros', 'error');
            return { success: false, error: error.message };
        }
    }

    // VERSION CONTROL
    async createCheckpoint(description = null) {
        try {
            const response = await fetch('/api/edit/checkpoint', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.currentSessionId,
                    description: description
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showMessage(`Checkpoint criado: ${result.checkpoint_id}`, 'success');
                this.refreshEditHistory();
            } else {
                this.showMessage(`Erro ao criar checkpoint: ${result.error}`, 'error');
            }

            return result;
        } catch (error) {
            console.error('Erro ao criar checkpoint:', error);
            this.showMessage('Erro ao criar checkpoint', 'error');
            return { success: false, error: error.message };
        }
    }

    async rollbackToCheckpoint(checkpointId) {
        try {
            const response = await fetch('/api/edit/rollback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.currentSessionId,
                    checkpoint_id: checkpointId
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showMessage(`Rollback realizado para ${checkpointId}`, 'success');
                this.refreshEditHistory();
                
                if (result.regeneration_result) {
                    this.updateModelViewer(result.regeneration_result.model_data);
                }
            } else {
                this.showMessage(`Erro no rollback: ${result.error}`, 'error');
            }

            return result;
        } catch (error) {
            console.error('Erro no rollback:', error);
            this.showMessage('Erro no rollback', 'error');
            return { success: false, error: error.message };
        }
    }

    // VALIDATION
    async validateEdit(editedCode = null, parameterUpdates = null) {
        try {
            const response = await fetch('/api/edit/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.currentSessionId,
                    edited_code: editedCode,
                    parameter_updates: parameterUpdates
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showValidationResults(result);
            } else {
                this.showMessage(`Erro na validação: ${result.error}`, 'error');
            }

            return result;
        } catch (error) {
            console.error('Erro na validação:', error);
            this.showMessage('Erro na validação', 'error');
            return { success: false, error: error.message };
        }
    }

    // UTILITY METHODS
    async loadEditCapabilities() {
        try {
            const response = await fetch(`/api/sessions/${this.currentSessionId}/state`);
            const state = await response.json();
            
            if (state.edit_capabilities) {
                this.editCapabilities = state.edit_capabilities;
                this.updateEditUI();
            }
        } catch (error) {
            console.error('Erro ao carregar capacidades de edição:', error);
        }
    }

    async refreshEditHistory() {
        try {
            const response = await fetch(`/api/edit/history/${this.currentSessionId}`);
            const result = await response.json();
            
            if (result.success) {
                this.editHistory = result.history;
                this.updateHistoryUI();
            }
        } catch (error) {
            console.error('Erro ao carregar histórico:', error);
        }
    }

    async getEditableContent() {
        try {
            const response = await fetch(`/api/edit/content/${this.currentSessionId}`);
            const result = await response.json();
            
            if (result.success) {
                return result;
            } else {
                this.showMessage(`Erro ao obter conteúdo: ${result.error}`, 'error');
                return null;
            }
        } catch (error) {
            console.error('Erro ao obter conteúdo editável:', error);
            return null;
        }
    }

    // UI METHODS
    showEditInterface(editData) {
        const editPanel = document.getElementById('edit-panel');
        if (!editPanel) return;

        // Mostrar informações do arquivo carregado
        const fileInfo = document.getElementById('loaded-file-info');
        if (fileInfo) {
            fileInfo.innerHTML = `
                <h3>Arquivo Carregado</h3>
                <p><strong>Arquivo:</strong> ${editData.loaded_file}</p>
                <p><strong>Parâmetros:</strong> ${Object.keys(editData.parameters).length}</p>
                <p><strong>Operações:</strong> ${editData.operations.length}</p>
            `;
        }

        // Mostrar editor de código
        const codeEditor = document.getElementById('code-editor');
        if (codeEditor) {
            codeEditor.value = editData.editable_code;
        }

        // Mostrar parâmetros editáveis
        this.showParameterEditor(editData.parameters);

        // Mostrar controles de edição
        editPanel.style.display = 'block';
    }

    showParameterEditor(parameters) {
        const paramContainer = document.getElementById('parameter-editor');
        if (!paramContainer) return;

        paramContainer.innerHTML = '<h3>Parâmetros</h3>';
        
        for (const [paramName, paramInfo] of Object.entries(parameters)) {
            const paramDiv = document.createElement('div');
            paramDiv.className = 'parameter-item';
            
            paramDiv.innerHTML = `
                <label for="param-${paramName}">${paramName}:</label>
                <input 
                    type="number" 
                    id="param-${paramName}" 
                    value="${paramInfo.value}" 
                    step="0.1"
                    data-param-name="${paramName}"
                />
                <span class="param-type">${paramInfo.type}</span>
            `;
            
            paramContainer.appendChild(paramDiv);
        }

        // Adicionar botão para aplicar mudanças
        const applyButton = document.createElement('button');
        applyButton.textContent = 'Aplicar Mudanças';
        applyButton.onclick = () => this.applyParameterChanges();
        paramContainer.appendChild(applyButton);
    }

    applyParameterChanges() {
        const paramInputs = document.querySelectorAll('[data-param-name]');
        const updates = {};
        
        paramInputs.forEach(input => {
            const paramName = input.dataset.paramName;
            const newValue = parseFloat(input.value);
            updates[paramName] = newValue;
        });
        
        this.updateParametersBatch(updates);
    }

    updateEditUI() {
        const editButtons = document.querySelectorAll('.edit-button');
        editButtons.forEach(button => {
            const capability = button.dataset.capability;
            button.disabled = !this.editCapabilities[capability];
        });
    }

    updateHistoryUI() {
        const historyContainer = document.getElementById('edit-history');
        if (!historyContainer) return;

        historyContainer.innerHTML = '<h3>Histórico de Edições</h3>';
        
        this.editHistory.forEach(entry => {
            const entryDiv = document.createElement('div');
            entryDiv.className = 'history-entry';
            
            entryDiv.innerHTML = `
                <div class="history-timestamp">${new Date(entry.timestamp).toLocaleString()}</div>
                <div class="history-description">${entry.description}</div>
                ${entry.can_rollback ? `<button onclick="editManager.rollbackToCheckpoint('${entry.checkpoint_id}')">Rollback</button>` : ''}
            `;
            
            historyContainer.appendChild(entryDiv);
        });
    }

    showValidationResults(validationResult) {
        const resultsContainer = document.getElementById('validation-results');
        if (!resultsContainer) return;

        resultsContainer.innerHTML = `
            <h3>Resultados da Validação</h3>
            <p><strong>Válido:</strong> ${validationResult.is_valid ? 'Sim' : 'Não'}</p>
            <p><strong>Erros:</strong> ${validationResult.summary.total_errors}</p>
            <p><strong>Avisos:</strong> ${validationResult.summary.total_warnings}</p>
        `;

        validationResult.validation_results.forEach(result => {
            const resultDiv = document.createElement('div');
            resultDiv.className = `validation-result ${result.is_valid ? 'valid' : 'invalid'}`;
            
            resultDiv.innerHTML = `
                <strong>${result.type}:</strong> ${result.is_valid ? 'Válido' : 'Inválido'}
                ${result.errors.length > 0 ? `<br>Erros: ${result.errors.join(', ')}` : ''}
            `;
            
            resultsContainer.appendChild(resultDiv);
        });
    }

    updateModelViewer(modelData) {
        // Atualizar visualizador 3D (integração com three-setup.js)
        if (window.threeSetup && modelData) {
            window.threeSetup.updateModel(modelData);
        }
    }

    showMessage(message, type = 'info') {
        const messageContainer = document.getElementById('edit-messages');
        if (!messageContainer) {
            console.log(`[${type.toUpperCase()}] ${message}`);
            return;
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${type}`;
        messageDiv.textContent = message;
        
        messageContainer.appendChild(messageDiv);
        
        // Remover mensagem após 5 segundos
        setTimeout(() => {
            messageDiv.remove();
        }, 5000);
    }

    handleEditResponse(data) {
        // Processar respostas de edição via WebSocket
        if (data.type === 'model_updated') {
            this.updateModelViewer(data.model_data);
        } else if (data.type === 'parameter_updated') {
            this.refreshEditHistory();
        }
    }
}

// Inicializar gerenciador de edições quando a página carregar
let editManager = null;

document.addEventListener('DOMContentLoaded', () => {
    // Aguardar inicialização do WebSocket
    setTimeout(() => {
        if (window.websocket) {
            editManager = new EditManager(window.websocket);
            window.editManager = editManager;
        }
    }, 1000);
}); 