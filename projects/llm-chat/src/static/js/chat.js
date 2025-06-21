// File Selection functionality
class FileSelector {
    constructor(chatApp) {
        this.chatApp = chatApp;
        this.selectedFiles = new Map(); // Map of file_id -> file_info
        this.modal = document.getElementById('file-modal');
        this.fileList = document.getElementById('file-list');
        this.fileListLoading = document.getElementById('file-list-loading');
        this.fileListError = document.getElementById('file-list-error');
        this.selectedFilesDiv = document.getElementById('selected-files');
        this.selectedFilesList = document.getElementById('selected-files-list');
        this.attachButton = document.getElementById('attach-button');
        
        this.init();
    }
    
    init() {
        this.attachButton.addEventListener('click', () => this.openModal());
        
        // Close modal when clicking outside
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.closeModal();
            }
        });
    }
    
    async openModal() {
        this.modal.style.display = 'block';
        await this.loadFiles();
    }
    
    closeModal() {
        this.modal.style.display = 'none';
    }
    
    async loadFiles() {
        this.fileListLoading.style.display = 'block';
        this.fileList.style.display = 'none';
        this.fileListError.style.display = 'none';
        
        try {
            const response = await fetch('/api/files/');
            if (!response.ok) {
                throw new Error('Failed to load files');
            }
            
            const files = await response.json();
            this.displayFiles(files);
            
        } catch (error) {
            console.error('Error loading files:', error);
            this.fileListError.textContent = 'Failed to load files. Please try again.';
            this.fileListError.style.display = 'block';
            this.fileListLoading.style.display = 'none';
        }
    }
    
    displayFiles(files) {
        this.fileListLoading.style.display = 'none';
        this.fileList.style.display = 'block';
        
        if (files.length === 0) {
            this.fileList.innerHTML = '<div class="file-list-empty">No files available</div>';
            return;
        }
        
        this.fileList.innerHTML = files.map(file => {
            const isSelected = this.selectedFiles.has(file.id);
            const fileSize = this.formatFileSize(file.size);
            const uploadDate = new Date(file.upload_date).toLocaleDateString();
            
            return `
                <div class="file-item ${isSelected ? 'selected' : ''}" data-file-id="${file.id}">
                    <input type="checkbox" class="file-checkbox" ${isSelected ? 'checked' : ''} />
                    <div class="file-info">
                        <div class="file-name">${this.escapeHtml(file.filename)}</div>
                        <div class="file-meta">
                            <span>${fileSize}</span>
                            <span>${uploadDate}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        // Add click handlers
        this.fileList.querySelectorAll('.file-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const fileId = item.dataset.fileId;
                const file = files.find(f => f.id === fileId);
                this.toggleFileSelection(fileId, file, item);
            });
        });
    }
    
    toggleFileSelection(fileId, fileInfo, itemElement) {
        const checkbox = itemElement.querySelector('.file-checkbox');
        
        if (this.selectedFiles.has(fileId)) {
            this.selectedFiles.delete(fileId);
            itemElement.classList.remove('selected');
            checkbox.checked = false;
        } else {
            if (this.selectedFiles.size >= 10) {
                this.chatApp.showError('Maximum 10 files can be selected');
                return;
            }
            this.selectedFiles.set(fileId, fileInfo);
            itemElement.classList.add('selected');
            checkbox.checked = true;
        }
    }
    
    confirmSelection() {
        this.closeModal();
        this.updateSelectedFilesDisplay();
    }
    
    updateSelectedFilesDisplay() {
        if (this.selectedFiles.size === 0) {
            this.selectedFilesDiv.style.display = 'none';
            return;
        }
        
        this.selectedFilesDiv.style.display = 'block';
        this.selectedFilesList.innerHTML = Array.from(this.selectedFiles.entries()).map(([id, file]) => `
            <div class="file-chip" data-file-id="${id}">
                <span class="file-chip-name">${this.escapeHtml(file.filename)}</span>
                <button class="file-chip-remove" onclick="window.chatApp.fileSelector.removeFile('${id}')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
        `).join('');
    }
    
    removeFile(fileId) {
        this.selectedFiles.delete(fileId);
        this.updateSelectedFilesDisplay();
    }
    
    clearSelection() {
        this.selectedFiles.clear();
        this.updateSelectedFilesDisplay();
    }
    
    getSelectedFileIds() {
        return Array.from(this.selectedFiles.keys());
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

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
        
        // Initialize file selector
        this.fileSelector = new FileSelector(this);
        
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
            // Clear file selection after successful send
            this.fileSelector.clearSelection();
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
            // Get selected file IDs
            const fileIds = this.fileSelector.getSelectedFileIds();
            
            const response = await fetch('/api/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId,
                    file_ids: fileIds.length > 0 ? fileIds : null
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
    window.chatApp = new ChatApp();
});