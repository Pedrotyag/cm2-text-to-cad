// Cliente WebSocket para benchmark - baseado no index.html
class BenchmarkWebSocketClient {
    constructor() {
        this.socket = null;
        this.sessionId = null;
        this.callbacks = {};
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 3;
        this.reconnectDelay = 2000;
        this.isConnected = false;
    }
    
    async connect(callbacks = {}) {
        this.callbacks = callbacks;
        
        try {
            // Iniciar nova sessão
            const sessionResponse = await fetch('/api/session/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!sessionResponse.ok) {
                throw new Error(`Erro ao iniciar sessão: ${sessionResponse.status}`);
            }
            
            const sessionData = await sessionResponse.json();
            this.sessionId = sessionData.session_id;
            
            console.log('🆔 Sessão iniciada:', this.sessionId);
            
            // Conectar WebSocket
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${wsProtocol}//${window.location.host}/ws/${this.sessionId}`;
            
            console.log('🔌 Conectando WebSocket:', wsUrl);
            
            this.socket = new WebSocket(wsUrl);
            
            this.socket.onopen = (event) => {
                console.log('✅ WebSocket conectado');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                
                if (this.callbacks.onOpen) {
                    this.callbacks.onOpen(event);
                }
            };
            
            this.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('📨 Mensagem recebida:', data.type);
                    
                    if (this.callbacks.onMessage) {
                        this.callbacks.onMessage(data);
                    }
                } catch (error) {
                    console.error('❌ Erro ao parsear mensagem:', error);
                }
            };
            
            this.socket.onclose = (event) => {
                console.log('🔌 WebSocket fechado:', event.code);
                this.isConnected = false;
                
                if (this.callbacks.onClose) {
                    this.callbacks.onClose(event);
                }
            };
            
            this.socket.onerror = (error) => {
                console.error('❌ Erro no WebSocket:', error);
                this.isConnected = false;
                
                if (this.callbacks.onError) {
                    this.callbacks.onError(error);
                }
            };
            
            return this.sessionId;
            
        } catch (error) {
            console.error('❌ Erro ao conectar:', error);
            throw error;
        }
    }
    
    send(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            try {
                const message = JSON.stringify(data);
                this.socket.send(message);
                console.log('📤 Mensagem enviada:', data.type);
            } catch (error) {
                console.error('❌ Erro ao enviar mensagem:', error);
                throw error;
            }
        } else {
            throw new Error('WebSocket não está conectado');
        }
    }
    
    sendUserMessage(message) {
        this.send({
            type: 'user_message',
            content: message,
            selected_geometry: null
        });
    }
    
    disconnect() {
        if (this.socket) {
            this.isConnected = false;
            this.socket.close(1000, 'Desconexão intencional');
            this.socket = null;
        }
    }
    
    getConnectionStatus() {
        return {
            connected: this.isConnected,
            sessionId: this.sessionId,
            readyState: this.socket ? this.socket.readyState : null
        };
    }
}

// Instância global
window.benchmarkWebSocket = new BenchmarkWebSocketClient(); 