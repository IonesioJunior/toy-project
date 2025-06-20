/**
 * ChromaDB API Client
 * Handles all API interactions with the FastAPI backend
 */
class ChromaDBClient {
    constructor(baseUrl = '/api/v1') {
        this.baseUrl = baseUrl;
        this.headers = {
            'Content-Type': 'application/json',
        };
    }

    /**
     * Generic request method with error handling
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            ...options,
            headers: {
                ...this.headers,
                ...options.headers,
            },
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            return await response.text();
        } catch (error) {
            console.error('API Request Error:', error);
            throw error;
        }
    }

    // Document CRUD Operations

    /**
     * Create a new document
     */
    async createDocument(data) {
        return this.request('/documents', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    /**
     * Get a document by ID
     */
    async getDocument(id) {
        return this.request(`/documents/${encodeURIComponent(id)}`);
    }

    /**
     * Update an existing document
     */
    async updateDocument(id, data) {
        return this.request(`/documents/${encodeURIComponent(id)}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    /**
     * Delete a document by ID
     */
    async deleteDocument(id) {
        return this.request(`/documents/${encodeURIComponent(id)}`, {
            method: 'DELETE',
        });
    }

    /**
     * List all documents with pagination
     */
    async listDocuments(params = {}) {
        const searchParams = new URLSearchParams();
        
        if (params.limit) searchParams.append('limit', params.limit);
        if (params.offset) searchParams.append('offset', params.offset);
        
        const queryString = searchParams.toString();
        const endpoint = `/documents${queryString ? `?${queryString}` : ''}`;
        
        return this.request(endpoint);
    }

    /**
     * Search for similar documents
     */
    async searchDocuments(queryData) {
        return this.request('/documents/search', {
            method: 'POST',
            body: JSON.stringify(queryData),
        });
    }

    /**
     * Create multiple documents in batch
     */
    async batchCreateDocuments(documents) {
        return this.request('/documents/batch', {
            method: 'POST',
            body: JSON.stringify({ documents }),
        });
    }

    /**
     * Delete all documents (requires confirmation)
     */
    async deleteAllDocuments() {
        return this.request('/documents?confirm=true', {
            method: 'DELETE',
        });
    }

    // Health and Status

    /**
     * Check API health
     */
    async checkHealth() {
        return this.request('/health', { method: 'GET' }, true);
    }

    /**
     * Check API readiness
     */
    async checkReady() {
        return this.request('/ready', { method: 'GET' }, true);
    }
}

/**
 * File Upload Handler
 * Handles file uploads with progress tracking
 */
class FileUploader {
    constructor(apiClient) {
        this.api = apiClient;
        this.uploadQueue = [];
        this.activeUploads = new Map();
    }

    /**
     * Add files to upload queue
     */
    addFiles(files) {
        const fileArray = Array.from(files);
        fileArray.forEach(file => {
            const fileId = this.generateFileId();
            this.uploadQueue.push({
                id: fileId,
                file: file,
                status: 'pending',
                progress: 0,
                metadata: {},
            });
        });
        return this.uploadQueue.slice(-fileArray.length);
    }

    /**
     * Start uploading files
     */
    async startUploads(onProgress, onComplete, onError) {
        const pendingFiles = this.uploadQueue.filter(item => item.status === 'pending');
        
        for (const fileItem of pendingFiles) {
            try {
                fileItem.status = 'uploading';
                onProgress && onProgress(fileItem);

                // Extract text content from file
                const content = await this.extractTextFromFile(fileItem.file);
                
                // Create document data
                const documentData = {
                    id: this.generateDocumentId(fileItem.file.name),
                    content: content,
                    metadata: {
                        filename: fileItem.file.name,
                        filesize: fileItem.file.size,
                        filetype: fileItem.file.type,
                        upload_date: new Date().toISOString(),
                        ...fileItem.metadata,
                    },
                };

                // Upload to API
                const result = await this.api.createDocument(documentData);
                
                fileItem.status = 'completed';
                fileItem.progress = 100;
                fileItem.result = result;
                
                onProgress && onProgress(fileItem);
                onComplete && onComplete(fileItem, result);
                
            } catch (error) {
                fileItem.status = 'error';
                fileItem.error = error.message;
                
                onProgress && onProgress(fileItem);
                onError && onError(fileItem, error);
            }
        }
    }

    /**
     * Extract text content from file
     */
    async extractTextFromFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = (e) => {
                let content = e.target.result;
                
                // For plain text files
                if (file.type.startsWith('text/')) {
                    resolve(content);
                    return;
                }
                
                // For other files, use filename and basic info as content
                resolve(`Document: ${file.name}\nFile Type: ${file.type}\nSize: ${this.formatFileSize(file.size)}\nUploaded: ${new Date().toLocaleString()}`);
            };
            
            reader.onerror = () => {
                reject(new Error('Failed to read file'));
            };
            
            reader.readAsText(file);
        });
    }

    /**
     * Generate unique file ID
     */
    generateFileId() {
        return 'file_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Generate document ID from filename
     */
    generateDocumentId(filename) {
        const baseName = filename.replace(/\.[^/.]+$/, ''); // Remove extension
        const cleanName = baseName.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
        const timestamp = Date.now();
        return `doc_${cleanName}_${timestamp}`;
    }

    /**
     * Format file size for display
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Clear completed uploads from queue
     */
    clearCompleted() {
        this.uploadQueue = this.uploadQueue.filter(item => 
            item.status !== 'completed' && item.status !== 'error'
        );
    }

    /**
     * Get upload statistics
     */
    getStats() {
        const total = this.uploadQueue.length;
        const completed = this.uploadQueue.filter(item => item.status === 'completed').length;
        const errors = this.uploadQueue.filter(item => item.status === 'error').length;
        const pending = this.uploadQueue.filter(item => item.status === 'pending').length;
        const uploading = this.uploadQueue.filter(item => item.status === 'uploading').length;
        
        return { total, completed, errors, pending, uploading };
    }
}

// Global instances
window.chromaAPI = new ChromaDBClient();
window.fileUploader = new FileUploader(window.chromaAPI);