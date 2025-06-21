// Cliente WebSocket para comunicação em tempo real
class WebSocketClient {
    constructor() {
        this.socket = null;
        this.sessionId = null;
        this.callbacks = {};
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
    }
    
    connect(sessionId, callbacks = {}) {
        this.sessionId = sessionId;
        this.callbacks = callbacks;
        
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/${sessionId}`;
        
        console.log('🔌 Conectando WebSocket:', wsUrl);
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = (event) => {
            console.log('✅ WebSocket conectado');
            this.reconnectAttempts = 0;
            
            if (this.callbacks.onOpen) {
                this.callbacks.onOpen(event);
            }
        };
        
        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('📨 Mensagem recebida via WebSocket:', data.type);
                
                if (this.callbacks.onMessage) {
                    this.callbacks.onMessage(data);
                }
            } catch (error) {
                console.error('❌ Erro ao parsear mensagem WebSocket:', error);
                console.error('Raw data:', event.data);
            }
        };
        
        this.socket.onclose = (event) => {
            console.log('🔌 WebSocket fechado:', event.code, event.reason);
            
            if (this.callbacks.onClose) {
                this.callbacks.onClose(event);
            }
            
            // Tentar reconexão automática
            if (this.reconnectAttempts < this.maxReconnectAttempts && !event.wasClean) {
                this.scheduleReconnect();
            }
        };
        
        this.socket.onerror = (error) => {
            console.error('❌ Erro no WebSocket:', error);
            
            if (this.callbacks.onError) {
                this.callbacks.onError(error);
            }
        };
    }
    
    send(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            try {
                const message = JSON.stringify(data);
                this.socket.send(message);
                console.log('📤 Mensagem enviada via WebSocket:', data.type);
            } catch (error) {
                console.error('❌ Erro ao enviar mensagem WebSocket:', error);
                throw error;
            }
        } else {
            throw new Error('WebSocket não está conectado');
        }
    }
    
    scheduleReconnect() {
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // Backoff exponencial
        
        console.log(`🔄 Tentativa de reconexão ${this.reconnectAttempts}/${this.maxReconnectAttempts} em ${delay}ms`);
        
        setTimeout(() => {
            if (this.sessionId) {
                this.connect(this.sessionId, this.callbacks);
            }
        }, delay);
    }
    
    disconnect() {
        if (this.socket) {
            this.socket.close(1000, 'Desconexão intencional');
            this.socket = null;
        }
    }
    
    isConnected() {
        return this.socket && this.socket.readyState === WebSocket.OPEN;
    }
} 