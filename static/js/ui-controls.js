// Controles da interface de usuário
class UIControls {
    constructor() {
        this.shortcuts = {
            'Ctrl+Enter': 'send-message',
            'Escape': 'clear-selection',
            'F5': 'refresh-all'
        };
        this.contextMenu = null;
        this.fab = null;
        this.fabMenu = null;
        this.activeToasts = [];
        this.isResizing = false;
        this.currentResizer = null;
        this.panelStates = {
            parameters: true,
            timeline: true
        };
        this.init();
    }
    
    init() {
        this.setupKeyboardShortcuts();
        this.setupTooltips();
        this.setupAnimations();
        this.setupFAB();
        this.setupContextMenu();
        this.setupAdvancedInteractions();
        this.setupModalEnhancements();
        this.initializeResizers();
        this.initializePanelToggle();
        console.log('🎨 UI Controls avançados inicializados');
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            const key = this.getKeyCombo(e);
            
            if (this.shortcuts[key]) {
                e.preventDefault();
                this.executeShortcut(this.shortcuts[key]);
            }
        });
    }
    
    getKeyCombo(event) {
        const parts = [];
        
        if (event.ctrlKey) parts.push('Ctrl');
        if (event.shiftKey) parts.push('Shift');
        if (event.altKey) parts.push('Alt');
        
        parts.push(event.key);
        
        return parts.join('+');
    }
    
    executeShortcut(action) {
        switch (action) {
            case 'send-message':
                document.getElementById('send-message').click();
                break;
            case 'clear-selection':
                // Implementar limpeza de seleção
                break;
            case 'refresh-all':
                window.cm2App?.refreshParameters();
                window.cm2App?.refreshTimeline();
                break;
        }
    }
    
    setupTooltips() {
        // Tooltips simples para botões
        const buttons = document.querySelectorAll('[title]');
        buttons.forEach(button => {
            button.addEventListener('mouseenter', this.showTooltip.bind(this));
            button.addEventListener('mouseleave', this.hideTooltip.bind(this));
        });
    }
    
    showTooltip(event) {
        // Implementação simples de tooltip
        console.log('Tooltip:', event.target.title);
    }
    
    hideTooltip(event) {
        // Ocultar tooltip
    }
    
    setupAnimations() {
        // Adicionar animações suaves aos elementos
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                }
            });
        }, observerOptions);
        
        // Observar elementos que devem ter animação
        document.querySelectorAll('.parameter-item, .operation-item').forEach(el => {
            observer.observe(el);
        });
    }

    setupFAB() {
        this.fab = document.getElementById('fab-main');
        this.fabMenu = document.getElementById('fab-menu');
        
        if (this.fab && this.fabMenu) {
            // Toggle do menu FAB
            this.fab.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleFABMenu();
                this.addRippleEffect(this.fab, e);
            });

            // Fechar menu ao clicar fora
            document.addEventListener('click', () => {
                this.closeFABMenu();
            });

            // Ações do FAB
            this.fabMenu.addEventListener('click', (e) => {
                if (e.target.classList.contains('fab-item')) {
                    const action = e.target.getAttribute('data-action');
                    this.handleFABAction(action);
                    this.addRippleEffect(e.target, e);
                }
            });

            // Animação de entrada do FAB
            setTimeout(() => {
                this.fab.style.transform = 'translateY(0) scale(1)';
                this.fab.style.opacity = '1';
            }, 1000);
        }
    }

    toggleFABMenu() {
        const isActive = this.fabMenu.classList.contains('active');
        
        if (isActive) {
            this.closeFABMenu();
        } else {
            this.openFABMenu();
        }
    }

    openFABMenu() {
        this.fabMenu.classList.add('active');
        this.fab.style.transform = 'rotate(45deg)';
        
        // Animar itens do menu
        const items = this.fabMenu.querySelectorAll('.fab-item');
        items.forEach((item, index) => {
            setTimeout(() => {
                item.style.transform = 'translateY(0) scale(1)';
                item.style.opacity = '1';
            }, index * 50);
        });
    }

    closeFABMenu() {
        this.fabMenu.classList.remove('active');
        this.fab.style.transform = 'rotate(0deg)';
    }

    handleFABAction(action) {
        switch (action) {
            case 'new-model':
                this.showConfirmationModal(
                    'Novo Modelo',
                    'Deseja criar um novo modelo? Isso irá limpar o modelo atual.',
                    () => this.createNewModel()
                );
                break;
            case 'save-model':
                this.saveCurrentModel();
                break;
            case 'share-model':
                this.shareModel();
                break;
            case 'help':
                this.showHelpModal();
                break;
        }
        this.closeFABMenu();
    }

    setupContextMenu() {
        this.contextMenu = document.getElementById('context-menu');
        
        if (this.contextMenu) {
            // Mostrar menu de contexto em elementos específicos
            document.addEventListener('contextmenu', (e) => {
                const target = e.target.closest('.message, .parameter-item, .operation-item');
                if (target) {
                    e.preventDefault();
                    this.showContextMenu(e.clientX, e.clientY, target);
                }
            });

            // Fechar menu ao clicar fora
            document.addEventListener('click', () => {
                this.hideContextMenu();
            });

            // Ações do menu de contexto
            this.contextMenu.addEventListener('click', (e) => {
                if (e.target.classList.contains('context-item')) {
                    const action = e.target.getAttribute('data-action');
                    this.handleContextAction(action, this.contextTarget);
                    this.hideContextMenu();
                }
            });
        }
    }

    showContextMenu(x, y, target) {
        this.contextTarget = target;
        this.contextMenu.style.left = x + 'px';
        this.contextMenu.style.top = y + 'px';
        this.contextMenu.style.display = 'block';
        
        // Ajustar posição se sair da tela
        const rect = this.contextMenu.getBoundingClientRect();
        if (rect.right > window.innerWidth) {
            this.contextMenu.style.left = (x - rect.width) + 'px';
        }
        if (rect.bottom > window.innerHeight) {
            this.contextMenu.style.top = (y - rect.height) + 'px';
        }
    }

    hideContextMenu() {
        if (this.contextMenu) {
            this.contextMenu.style.display = 'none';
            this.contextTarget = null;
        }
    }

    handleContextAction(action, target) {
        switch (action) {
            case 'copy':
                this.copyToClipboard(target);
                break;
            case 'edit':
                this.editItem(target);
                break;
            case 'delete':
                this.deleteItem(target);
                break;
        }
    }

    setupAdvancedInteractions() {
        // Drag and drop para parâmetros
        this.setupParameterDragDrop();
        
        // Scroll infinito para timeline
        this.setupInfiniteScroll();
        
        // Auto-save dos parâmetros
        this.setupParameterAutoSave();
        
        // Feedback visual melhorado
        this.setupEnhancedFeedback();
    }

    setupParameterDragDrop() {
        const parametersList = document.getElementById('parameters-list');
        if (parametersList && typeof Sortable !== 'undefined') {
            new Sortable(parametersList, {
                animation: 200,
                ghostClass: 'sortable-ghost',
                chosenClass: 'sortable-chosen',
                dragClass: 'sortable-drag',
                onEnd: (evt) => {
                    this.onParameterReorder(evt.oldIndex, evt.newIndex);
                }
            });
        } else if (!window.Sortable) {
            console.log('📋 Sortable.js não carregado - funcionalidade de drag-and-drop desabilitada');
        }
    }

    setupInfiniteScroll() {
        const timeline = document.getElementById('operations-timeline');
        if (timeline) {
            timeline.addEventListener('scroll', () => {
                if (timeline.scrollTop + timeline.clientHeight >= timeline.scrollHeight - 5) {
                    this.loadMoreOperations();
                }
            });
        }
    }

    setupParameterAutoSave() {
        document.addEventListener('input', (e) => {
            if (e.target.classList.contains('parameter-input')) {
                clearTimeout(this.autoSaveTimer);
                this.autoSaveTimer = setTimeout(() => {
                    this.saveParameterChange(e.target);
                }, 1000);
            }
        });
    }

    setupEnhancedFeedback() {
        // Feedback haptico (vibração) se disponível
        document.addEventListener('click', (e) => {
            if (e.target.matches('.btn-primary, .fab, .fab-item')) {
                if (navigator.vibrate) {
                    navigator.vibrate(10);
                }
            }
        });

        // Som de feedback (opcional)
        this.setupAudioFeedback();
    }

    setupAudioFeedback() {
        // Criar contexto de áudio para feedback sonoro sutil
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.createAudioFeedback();
        } catch (e) {
            console.log('Áudio não disponível');
        }
    }

    createAudioFeedback() {
        if (this.audioContext) {
            // Som de clique sutil
            document.addEventListener('click', (e) => {
                if (e.target.matches('.btn-primary, .quick-action')) {
                    this.playTone(800, 50);
                }
            });
        }
    }

    playTone(frequency, duration) {
        if (!this.audioContext) return;
        
        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);
        
        oscillator.frequency.value = frequency;
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.1, this.audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + duration / 1000);
        
        oscillator.start(this.audioContext.currentTime);
        oscillator.stop(this.audioContext.currentTime + duration / 1000);
    }

    setupModalEnhancements() {
        // Melhorar modais existentes
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            // Fechar com clique no backdrop
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal(modal);
                }
            });

            // Animação de entrada melhorada
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.attributeName === 'style') {
                        if (modal.style.display === 'flex') {
                            modal.classList.add('modal-entering');
                            setTimeout(() => {
                                modal.classList.remove('modal-entering');
                            }, 300);
                        }
                    }
                });
            });
            observer.observe(modal, { attributes: true });
        });
    }

    // Métodos utilitários
    addRippleEffect(element, event) {
        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;
        
        const ripple = document.createElement('span');
        ripple.className = 'ripple-effect';
        ripple.style.cssText = `
            width: ${size}px;
            height: ${size}px;
            left: ${x}px;
            top: ${y}px;
        `;
        
        element.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    }

    showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: ${20 + this.activeToasts.length * 80}px;
            right: 20px;
            background: ${this.getToastColor(type)};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1001;
            transform: translateX(100%);
            transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            font-weight: 500;
            backdrop-filter: blur(10px);
            max-width: 300px;
            word-wrap: break-word;
        `;
        
        document.body.appendChild(toast);
        this.activeToasts.push(toast);
        
        // Animar entrada
        requestAnimationFrame(() => {
            toast.style.transform = 'translateX(0)';
        });
        
        // Auto-remover
        setTimeout(() => {
            this.removeToast(toast);
        }, duration);
    }

    getToastColor(type) {
        switch (type) {
            case 'success': return '#2ecc71';
            case 'error': return '#e74c3c';
            case 'warning': return '#f39c12';
            default: return '#3498db';
        }
    }

    removeToast(toast) {
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (toast.parentNode) {
                document.body.removeChild(toast);
            }
            this.activeToasts = this.activeToasts.filter(t => t !== toast);
            this.repositionToasts();
        }, 300);
    }

    repositionToasts() {
        this.activeToasts.forEach((toast, index) => {
            toast.style.top = `${20 + index * 80}px`;
        });
    }

    showConfirmationModal(title, message, onConfirm, onCancel = null) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(8px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.3s ease-out;
        `;
        
        modal.innerHTML = `
            <div class="modal-content" style="animation: modalSlideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);">
                <h3>${title}</h3>
                <p>${message}</p>
                <div class="modal-actions">
                    <button class="btn-secondary" id="cancel-btn">Cancelar</button>
                    <button class="btn-primary" id="confirm-btn">Confirmar</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Animar entrada
        requestAnimationFrame(() => {
            modal.style.opacity = '1';
        });
        
        // Event listeners
        modal.querySelector('#confirm-btn').addEventListener('click', () => {
            onConfirm();
            this.closeModal(modal);
        });
        
        modal.querySelector('#cancel-btn').addEventListener('click', () => {
            if (onCancel) onCancel();
            this.closeModal(modal);
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                if (onCancel) onCancel();
                this.closeModal(modal);
            }
        });
    }

    closeModal(modal) {
        modal.style.opacity = '0';
        setTimeout(() => {
            if (modal.parentNode) {
                document.body.removeChild(modal);
            }
        }, 300);
    }

    closeAllModals() {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            if (modal.style.display === 'flex' || modal.style.display === '') {
                this.closeModal(modal);
            }
        });
    }

    // Implementações específicas das ações
    createNewModel() {
        // Implementar criação de novo modelo
        this.showToast('Novo modelo criado!', 'success');
    }

    saveCurrentModel() {
        // Implementar salvamento do modelo atual
        this.showToast('Modelo salvo com sucesso!', 'success');
    }

    shareModel() {
        // Implementar compartilhamento do modelo
        if (navigator.share) {
            navigator.share({
                title: 'Modelo CAD - CM²',
                text: 'Confira este modelo CAD que criei!',
                url: window.location.href
            });
        } else {
            // Fallback para clipboard
            navigator.clipboard.writeText(window.location.href).then(() => {
                this.showToast('Link copiado para área de transferência!', 'success');
            });
        }
    }

    showHelpModal() {
        const helpContent = `
            <h3>🚀 Ajuda - CM² Text-to-CAD</h3>
            <div style="text-align: left; max-height: 400px; overflow-y: auto;">
                <h4>📝 Comandos Básicos:</h4>
                <ul>
                    <li><strong>Ctrl/Cmd + Enter:</strong> Enviar mensagem</li>
                    <li><strong>Ctrl/Cmd + K:</strong> Focar no campo de entrada</li>
                    <li><strong>Ctrl/Cmd + S:</strong> Salvar modelo</li>
                    <li><strong>Esc:</strong> Fechar menus e modais</li>
                </ul>
                
                <h4>🎯 Exemplos de Comandos:</h4>
                <ul>
                    <li>"Crie uma caixa de 100x50x25mm"</li>
                    <li>"Adicione um cilindro de 20mm de raio"</li>
                    <li>"Faça um furo de 5mm no centro"</li>
                    <li>"Adicione um filete de 3mm nas bordas"</li>
                </ul>
                
                <h4>⚙️ Dicas:</h4>
                <ul>
                    <li>Seja específico com as dimensões</li>
                    <li>Use unidades (mm, cm, m)</li>
                    <li>Descreva a posição relativa dos elementos</li>
                    <li>Experimente com diferentes formas geométricas</li>
                </ul>
            </div>
            <div class="modal-actions">
                <button class="btn-primary" onclick="this.closest('.modal').style.display='none'">Entendi!</button>
            </div>
        `;
        
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.display = 'flex';
        modal.innerHTML = `<div class="modal-content">${helpContent}</div>`;
        document.body.appendChild(modal);
    }

    copyToClipboard(element) {
        let text = '';
        if (element.classList.contains('message')) {
            text = element.querySelector('.message-content').textContent;
        } else if (element.classList.contains('parameter-item')) {
            text = element.textContent;
        }
        
        navigator.clipboard.writeText(text).then(() => {
            this.showToast('Copiado para área de transferência!', 'success');
        });
    }

    editItem(element) {
        // Implementar edição inline
        this.showToast('Funcionalidade de edição em desenvolvimento', 'info');
    }

    deleteItem(element) {
        this.showConfirmationModal(
            'Confirmar Exclusão',
            'Tem certeza que deseja excluir este item?',
            () => {
                element.style.animation = 'slideOut 0.3s ease-out forwards';
                setTimeout(() => {
                    element.remove();
                    this.showToast('Item excluído!', 'success');
                }, 300);
            }
        );
    }

    onParameterReorder(oldIndex, newIndex) {
        this.showToast(`Parâmetro movido da posição ${oldIndex + 1} para ${newIndex + 1}`, 'info');
    }

    loadMoreOperations() {
        // Implementar carregamento de mais operações
        console.log('Carregando mais operações...');
    }

    saveParameterChange(input) {
        input.setAttribute('data-changed', 'true');
        setTimeout(() => {
            input.removeAttribute('data-changed');
        }, 1000);
        
        this.showToast('Parâmetro atualizado!', 'success', 1500);
    }

    // ===== SISTEMA DE REDIMENSIONAMENTO =====
    initializeResizers() {
        const resizers = document.querySelectorAll('.resizer');
        
        resizers.forEach(resizer => {
            resizer.addEventListener('mousedown', (e) => this.startResize(e, resizer));
        });

        document.addEventListener('mousemove', (e) => this.handleResize(e));
        document.addEventListener('mouseup', () => this.stopResize());
        
        // Prevenir seleção de texto durante redimensionamento
        document.addEventListener('selectstart', (e) => {
            if (this.isResizing) {
                e.preventDefault();
            }
        });
    }

    startResize(e, resizer) {
        e.preventDefault();
        this.isResizing = true;
        this.currentResizer = resizer;
        
        document.body.style.cursor = resizer.classList.contains('vertical-resizer') ? 'col-resize' : 'row-resize';
        document.body.style.userSelect = 'none';
        
        // Adicionar classe para feedback visual
        resizer.classList.add('active');
    }

    handleResize(e) {
        if (!this.isResizing || !this.currentResizer) return;

        e.preventDefault();
        
        const resizer = this.currentResizer;
        const isVertical = resizer.classList.contains('vertical-resizer');
        
        if (isVertical) {
            this.handleVerticalResize(e, resizer);
        } else {
            this.handleHorizontalResize(e, resizer);
        }
    }

    handleVerticalResize(e, resizer) {
        const mainContent = document.querySelector('.main-content');
        const viewportPanel = document.querySelector('.viewport-panel');
        const sidePanel = document.querySelector('.side-panel');
        
        if (!mainContent || !viewportPanel || !sidePanel) return;

        const rect = mainContent.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const totalWidth = rect.width;
        
        // Limitar entre 25% e 75% da largura total
        const minViewportWidth = totalWidth * 0.25;
        const maxViewportWidth = totalWidth * 0.75;
        
        const newViewportWidth = Math.max(minViewportWidth, Math.min(maxViewportWidth, mouseX));
        const newSidePanelWidth = totalWidth - newViewportWidth - 4; // 4px para o resizer
        
        viewportPanel.style.flex = `0 0 ${newViewportWidth}px`;
        sidePanel.style.flex = `0 0 ${newSidePanelWidth}px`;
    }

    handleHorizontalResize(e, resizer) {
        const sidePanel = document.querySelector('.side-panel');
        const rect = sidePanel.getBoundingClientRect();
        const mouseY = e.clientY - rect.top;
        
        if (resizer.id === 'chat-params-resizer') {
            this.resizeChatParams(mouseY, rect.height);
        } else if (resizer.id === 'params-timeline-resizer') {
            this.resizeParamsTimeline(mouseY, rect.height);
        }
    }

    resizeChatParams(mouseY, totalHeight) {
        const chatPanel = document.querySelector('.chat-panel');
        const paramsPanel = document.querySelector('.parameters-panel');
        const timelinePanel = document.querySelector('.timeline-panel');
        
        if (!chatPanel || !paramsPanel || !timelinePanel) return;

        const timelineHeight = timelinePanel.offsetHeight;
        const availableHeight = totalHeight - timelineHeight - 8; // 8px para os resizers
        
        // Limitar alturas mínimas
        const minChatHeight = 200;
        const minParamsHeight = 150;
        
        const newChatHeight = Math.max(minChatHeight, mouseY - 4);
        const newParamsHeight = Math.max(minParamsHeight, availableHeight - newChatHeight);
        
        chatPanel.style.flex = `0 0 ${newChatHeight}px`;
        paramsPanel.style.flex = `0 0 ${newParamsHeight}px`;
    }

    resizeParamsTimeline(mouseY, totalHeight) {
        const chatPanel = document.querySelector('.chat-panel');
        const paramsPanel = document.querySelector('.parameters-panel');
        const timelinePanel = document.querySelector('.timeline-panel');
        
        if (!chatPanel || !paramsPanel || !timelinePanel) return;

        const chatHeight = chatPanel.offsetHeight;
        const availableHeight = totalHeight - chatHeight - 8; // 8px para os resizers
        
        // Calcular posição relativa no espaço disponível
        const relativeMouseY = mouseY - chatHeight - 4;
        
        // Limitar alturas mínimas
        const minParamsHeight = 150;
        const minTimelineHeight = 150;
        
        const newParamsHeight = Math.max(minParamsHeight, relativeMouseY);
        const newTimelineHeight = Math.max(minTimelineHeight, availableHeight - newParamsHeight);
        
        paramsPanel.style.flex = `0 0 ${newParamsHeight}px`;
        timelinePanel.style.flex = `0 0 ${newTimelineHeight}px`;
    }

    stopResize() {
        if (!this.isResizing) return;
        
        this.isResizing = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        
        // Remover classe de feedback visual
        if (this.currentResizer) {
            this.currentResizer.classList.remove('active');
        }
        
        this.currentResizer = null;
    }

    // ===== CONTROLES DE VISIBILIDADE DOS PAINÉIS =====
    initializePanelToggle() {
        // Botões de toggle nos controles do chat
        const toggleButtons = document.querySelectorAll('.toggle-panel');
        toggleButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const target = e.target.dataset.target;
                this.togglePanel(target, button);
            });
        });

        // Botões de collapse nos próprios painéis
        const collapseButtons = document.querySelectorAll('.collapse-btn');
        collapseButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const panel = e.target.closest('.parameters-panel, .timeline-panel');
                this.collapsePanel(panel);
            });
        });
    }

    togglePanel(panelType, button) {
        const panel = document.getElementById(`${panelType}-panel`);
        const resizer = document.getElementById(`chat-${panelType}-resizer`) || 
                       document.getElementById(`params-timeline-resizer`);
        
        if (!panel) return;

        const isHidden = panel.classList.contains('hidden');
        
        if (isHidden) {
            // Mostrar painel
            panel.classList.remove('hidden');
            if (resizer) resizer.style.display = 'block';
            button.classList.add('active');
            this.panelStates[panelType] = true;
            
            // Restaurar tamanho padrão
            panel.style.flex = '0 0 200px';
        } else {
            // Ocultar painel
            panel.classList.add('hidden');
            if (resizer) resizer.style.display = 'none';
            button.classList.remove('active');
            this.panelStates[panelType] = false;
        }

        // Salvar estado
        this.savePanelStates();
        
        // Reajustar layout
        this.adjustLayoutAfterToggle();
    }

    collapsePanel(panel) {
        if (!panel) return;

        const isCollapsed = panel.classList.contains('collapsed');
        const collapseBtn = panel.querySelector('.collapse-btn');
        
        if (isCollapsed) {
            // Expandir
            panel.classList.remove('collapsed');
            if (collapseBtn) collapseBtn.classList.remove('collapsed');
            panel.style.flex = '0 0 200px';
        } else {
            // Colapsar
            panel.classList.add('collapsed');
            if (collapseBtn) collapseBtn.classList.add('collapsed');
        }
    }

    adjustLayoutAfterToggle() {
        const chatPanel = document.querySelector('.chat-panel');
        const paramsPanel = document.querySelector('.parameters-panel');
        const timelinePanel = document.querySelector('.timeline-panel');
        
        // Contar painéis visíveis
        let visiblePanels = 1; // Chat sempre visível
        
        if (!paramsPanel.classList.contains('hidden')) visiblePanels++;
        if (!timelinePanel.classList.contains('hidden')) visiblePanels++;
        
        // Ajustar flex do chat baseado nos painéis visíveis
        if (visiblePanels === 1) {
            chatPanel.style.flex = '1'; // Chat ocupa todo o espaço
        } else if (visiblePanels === 2) {
            chatPanel.style.flex = '1';
        } else {
            chatPanel.style.flex = '1';
        }
    }

    savePanelStates() {
        localStorage.setItem('cm2-panel-states', JSON.stringify(this.panelStates));
    }

    loadPanelStates() {
        const saved = localStorage.getItem('cm2-panel-states');
        if (saved) {
            try {
                this.panelStates = { ...this.panelStates, ...JSON.parse(saved) };
                
                // Aplicar estados salvos
                Object.entries(this.panelStates).forEach(([panelType, isVisible]) => {
                    const button = document.querySelector(`[data-target="${panelType}"]`);
                    if (button && !isVisible) {
                        this.togglePanel(panelType, button);
                    }
                });
            } catch (e) {
                console.warn('Erro ao carregar estados dos painéis:', e);
            }
        }
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.uiControls = new UIControls();
    
    // Carregar estados salvos dos painéis após um pequeno delay
    setTimeout(() => {
        window.uiControls.loadPanelStates();
    }, 100);
});

// ===== FUNÇÕES UTILITÁRIAS =====
function createRippleEffect(element, event) {
    const ripple = document.createElement('span');
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;
    
    ripple.className = 'ripple-effect';
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    
    element.appendChild(ripple);
    
    setTimeout(() => {
        ripple.remove();
    }, 600);
}

// Adicionar efeito ripple aos botões
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.btn-icon, .btn-primary, .quick-action').forEach(button => {
        button.addEventListener('click', function(e) {
            createRippleEffect(this, e);
        });
    });
}); 