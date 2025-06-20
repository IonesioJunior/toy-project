// Chat functionality
class ChatApp {
    constructor() {
        this.chatForm = document.getElementById('chat-form');
        this.userInput = document.getElementById('user-input');
        this.chatMessages = document.getElementById('chat-messages');
        this.sendButton = document.getElementById('send-button');
        this.clearButton = document.getElementById('clear-chat');
        this.errorMessage = document.getElementById('error-message');
        
        this.sessionId = null;
        this.isStreaming = false;
        
        this.init();
    }
    
    init() {
        // Set up event listeners
        this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        this.clearButton.addEventListener('click', () => this.clearChat());
        
        // Auto-resize input
        this.userInput.addEventListener('input', () => this.autoResizeInput());
        
        // Handle Enter key (submit) vs Shift+Enter (new line)
        this.userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.chatForm.dispatchEvent(new Event('submit'));
            }
        });
        
        // Focus input on load
        this.userInput.focus();
    }
    
    async handleSubmit(e) {
        e.preventDefault();
        
        if (this.isStreaming) return;
        
        const message = this.userInput.value.trim();
        if (!message) return;
        
        // Clear input and disable while processing
        this.userInput.value = '';
        this.setInputState(false);
        this.hideError();
        
        // Add user message to chat
        this.addMessage('user', message);
        
        // Create assistant message placeholder
        const assistantMessageEl = this.addMessage('assistant', '', true);
        
        try {
            await this.streamChat(message, assistantMessageEl);
        } catch (error) {
            this.showError('Failed to send message. Please try again.');
            assistantMessageEl.remove();
        } finally {
            this.setInputState(true);
            this.userInput.focus();
        }
    }
    
    async streamChat(message, messageElement) {
        this.isStreaming = true;
        const contentEl = messageElement.querySelector('.message-content');
        
        try {
            const response = await fetch('/api/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data) {
                            try {
                                const parsed = JSON.parse(data);
                                this.handleStreamData(parsed, contentEl);
                            } catch (e) {
                                console.error('Failed to parse SSE data:', e);
                            }
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Stream error:', error);
            throw error;
        } finally {
            this.isStreaming = false;
        }
    }
    
    handleStreamData(data, contentEl) {
        switch (data.type) {
            case 'session':
                this.sessionId = data.session_id;
                break;
                
            case 'content':
                // Clear typing indicator on first content
                if (contentEl.querySelector('.typing-indicator')) {
                    contentEl.innerHTML = '';
                }
                contentEl.textContent += data.content;
                this.scrollToBottom();
                break;
                
            case 'error':
                this.showError(data.error);
                break;
                
            case 'done':
                // Stream completed
                break;
        }
    }
    
    addMessage(role, content, showTyping = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        if (showTyping && role === 'assistant') {
            contentDiv.innerHTML = this.createTypingIndicator();
        } else {
            contentDiv.textContent = content;
        }
        
        messageDiv.appendChild(contentDiv);
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        return messageDiv;
    }
    
    createTypingIndicator() {
        return `
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
    }
    
    async clearChat() {
        if (!confirm('Are you sure you want to clear the chat history?')) return;
        
        try {
            const response = await fetch('/api/chat/history', {
                method: 'DELETE',
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                throw new Error('Failed to clear history');
            }
            
            // Clear messages except the initial greeting
            const messages = this.chatMessages.querySelectorAll('.message');
            messages.forEach((msg, index) => {
                if (index > 0) msg.remove();
            });
            
            this.sessionId = null;
            this.showSuccess('Chat history cleared');
            
        } catch (error) {
            this.showError('Failed to clear chat history');
        }
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    setInputState(enabled) {
        this.userInput.disabled = !enabled;
        this.sendButton.disabled = !enabled;
        
        // Update button appearance
        if (!enabled) {
            this.sendButton.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="opacity: 0.5;">
                    <circle cx="12" cy="12" r="10"></circle>
                </svg>
            `;
        } else {
            this.sendButton.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
            `;
        }
    }
    
    autoResizeInput() {
        // Reset height to auto to get the correct scrollHeight
        this.userInput.style.height = 'auto';
        
        // Calculate new height
        const newHeight = Math.min(this.userInput.scrollHeight, 120); // Max 120px height
        this.userInput.style.height = newHeight + 'px';
        
        // Adjust rows for better mobile experience
        const lineHeight = parseInt(window.getComputedStyle(this.userInput).lineHeight);
        const rows = Math.ceil(newHeight / lineHeight);
        this.userInput.rows = Math.min(rows, 4); // Max 4 rows
    }
    
    showError(message) {
        this.errorMessage.textContent = message;
        this.errorMessage.style.display = 'block';
        setTimeout(() => this.hideError(), 5000);
    }
    
    hideError() {
        this.errorMessage.style.display = 'none';
    }
    
    showSuccess(message) {
        // Temporarily show success in error div with different styling
        const originalBg = this.errorMessage.style.backgroundColor;
        this.errorMessage.style.backgroundColor = '#27ae60';
        this.errorMessage.textContent = message;
        this.errorMessage.style.display = 'block';
        
        setTimeout(() => {
            this.hideError();
            this.errorMessage.style.backgroundColor = originalBg;
        }, 3000);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});