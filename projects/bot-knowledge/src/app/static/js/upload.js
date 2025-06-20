/**
 * Upload functionality for ChromaDB Document Manager
 * Handles file uploads, text document creation, and bulk operations
 */

class UploadManager {
    constructor() {
        this.selectedFiles = [];
        this.uploadQueue = [];
        this.isUploading = false;
        this.recentUploads = [];
    }

    static init() {
        const manager = new UploadManager();
        manager.initializeElements();
        manager.loadRecentUploads();
        window.uploadManager = manager;
    }

    initializeElements() {
        // Drop zone
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');

        if (dropZone && fileInput) {
            // Click to browse
            dropZone.addEventListener('click', () => {
                fileInput.click();
            });

            // File input change
            fileInput.addEventListener('change', (e) => {
                this.handleFiles(e.target.files);
            });

            // Drag and drop events
            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.classList.add('drag-over');
            });

            dropZone.addEventListener('dragleave', (e) => {
                e.preventDefault();
                dropZone.classList.remove('drag-over');
            });

            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('drag-over');
                this.handleFiles(e.dataTransfer.files);
            });
        }

        // File upload controls
        const clearFiles = document.getElementById('clear-files');
        if (clearFiles) {
            clearFiles.addEventListener('click', () => {
                this.clearFiles();
            });
        }

        const uploadFiles = document.getElementById('upload-files');
        if (uploadFiles) {
            uploadFiles.addEventListener('click', () => {
                this.startFileUpload();
            });
        }

        // Text form
        const textForm = document.getElementById('text-form');
        if (textForm) {
            textForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.createTextDocument();
            });
        }

        // Character counter
        const contentTextarea = document.getElementById('document-content');
        const charCount = document.getElementById('char-count');
        if (contentTextarea && charCount) {
            contentTextarea.addEventListener('input', () => {
                charCount.textContent = contentTextarea.value.length;
            });
        }

        // Document ID validation
        const documentId = document.getElementById('document-id');
        if (documentId) {
            documentId.addEventListener('input', () => {
                this.validateDocumentId();
            });
        }

        // Upload summary actions
        const viewDocuments = document.getElementById('view-documents');
        if (viewDocuments) {
            viewDocuments.addEventListener('click', () => {
                window.location.href = '/documents';
            });
        }

        const uploadMore = document.getElementById('upload-more');
        if (uploadMore) {
            uploadMore.addEventListener('click', () => {
                this.resetUpload();
            });
        }

        // Recent uploads refresh
        const refreshRecent = document.getElementById('refresh-recent');
        if (refreshRecent) {
            refreshRecent.addEventListener('click', () => {
                this.loadRecentUploads();
            });
        }

        // Bulk metadata modal
        const closeBulkModal = document.getElementById('close-bulk-modal');
        if (closeBulkModal) {
            closeBulkModal.addEventListener('click', () => {
                this.closeBulkMetadataModal();
            });
        }

        const cancelBulkMetadata = document.getElementById('cancel-bulk-metadata');
        if (cancelBulkMetadata) {
            cancelBulkMetadata.addEventListener('click', () => {
                this.closeBulkMetadataModal();
            });
        }

        const applyBulkMetadata = document.getElementById('apply-bulk-metadata');
        if (applyBulkMetadata) {
            applyBulkMetadata.addEventListener('click', () => {
                this.applyBulkMetadata();
            });
        }
    }

    handleFiles(files) {
        const fileArray = Array.from(files);
        const validFiles = [];
        const invalidFiles = [];

        fileArray.forEach(file => {
            if (this.validateFile(file)) {
                validFiles.push(file);
            } else {
                invalidFiles.push(file);
            }
        });

        if (invalidFiles.length > 0) {
            window.toastManager.warning(
                `${invalidFiles.length} file(s) skipped due to invalid type or size`
            );
        }

        if (validFiles.length > 0) {
            this.selectedFiles = [...this.selectedFiles, ...validFiles];
            this.renderFileList();
            this.showUploadControls();
        }
    }

    validateFile(file) {
        // Check file type
        const allowedTypes = [
            'text/plain',
            'text/csv',
            'text/markdown',
            'application/json',
            'text/html',
            'text/xml'
        ];

        const allowedExtensions = [
            '.txt', '.md', '.csv', '.json', '.html', '.xml', '.log'
        ];

        const hasValidType = allowedTypes.includes(file.type);
        const hasValidExtension = allowedExtensions.some(ext => 
            file.name.toLowerCase().endsWith(ext)
        );

        if (!hasValidType && !hasValidExtension) {
            return false;
        }

        // Check file size (10MB limit)
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            return false;
        }

        return true;
    }

    renderFileList() {
        const fileList = document.getElementById('file-list');
        const fileItems = document.getElementById('file-items');
        const fileCount = document.getElementById('file-count');

        if (this.selectedFiles.length === 0) {
            fileList.classList.add('hidden');
            return;
        }

        fileList.classList.remove('hidden');
        fileCount.textContent = this.selectedFiles.length;

        fileItems.innerHTML = this.selectedFiles.map((file, index) => `
            <div class="file-item">
                <div class="file-info">
                    <div class="flex items-center space-x-2">
                        <i data-feather="file-text" class="w-4 h-4 text-gray-400"></i>
                        <div>
                            <div class="file-name">${file.name}</div>
                            <div class="file-size">${formatFileSize(file.size)}</div>
                        </div>
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <button onclick="window.uploadManager.removeFile(${index})" 
                            class="text-gray-400 hover:text-red-600" title="Remove">
                        <i data-feather="x" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>
        `).join('');

        feather.replace();
    }

    removeFile(index) {
        this.selectedFiles.splice(index, 1);
        this.renderFileList();
        
        if (this.selectedFiles.length === 0) {
            this.hideUploadControls();
        }
    }

    clearFiles() {
        this.selectedFiles = [];
        this.renderFileList();
        this.hideUploadControls();
        
        // Reset file input
        const fileInput = document.getElementById('file-input');
        if (fileInput) {
            fileInput.value = '';
        }
    }

    showUploadControls() {
        const uploadControls = document.getElementById('upload-controls');
        uploadControls.classList.remove('hidden');
    }

    hideUploadControls() {
        const uploadControls = document.getElementById('upload-controls');
        uploadControls.classList.add('hidden');
    }

    async startFileUpload() {
        if (this.selectedFiles.length === 0) {
            window.toastManager.warning('No files selected');
            return;
        }

        if (this.selectedFiles.length > 1) {
            // Show bulk metadata modal for multiple files
            this.showBulkMetadataModal();
        } else {
            // Upload single file directly
            this.performFileUpload({});
        }
    }

    showBulkMetadataModal() {
        const modal = document.getElementById('bulk-metadata-modal');
        modal.classList.remove('hidden');
    }

    closeBulkMetadataModal() {
        const modal = document.getElementById('bulk-metadata-modal');
        modal.classList.add('hidden');
        
        // Clear form
        document.getElementById('bulk-metadata-form').reset();
    }

    applyBulkMetadata() {
        const category = document.getElementById('bulk-category').value;
        const author = document.getElementById('bulk-author').value;
        const tags = document.getElementById('bulk-tags').value;

        const metadata = {};
        if (category) metadata.category = category;
        if (author) metadata.author = author;
        if (tags) metadata.tags = tags.split(',').map(tag => tag.trim()).filter(tag => tag);

        this.closeBulkMetadataModal();
        this.performFileUpload(metadata);
    }

    async performFileUpload(bulkMetadata = {}) {
        this.isUploading = true;
        this.showUploadProgress();

        try {
            const uploader = window.fileUploader;
            
            // Add files to uploader
            const fileItems = uploader.addFiles(this.selectedFiles);
            
            // Apply bulk metadata
            fileItems.forEach(item => {
                item.metadata = { ...bulkMetadata, ...item.metadata };
            });

            // Start upload with progress callbacks
            await uploader.startUploads(
                (fileItem) => this.updateFileProgress(fileItem),
                (fileItem, result) => this.onFileComplete(fileItem, result),
                (fileItem, error) => this.onFileError(fileItem, error)
            );

            this.onUploadComplete();

        } catch (error) {
            console.error('Upload error:', error);
            window.toastManager.error('Upload failed: ' + error.message);
        } finally {
            this.isUploading = false;
        }
    }

    showUploadProgress() {
        const progressCard = document.getElementById('upload-progress');
        progressCard.classList.remove('hidden');
        
        // Hide upload controls
        this.hideUploadControls();
        
        // Initialize progress
        this.updateOverallProgress(0);
        this.renderUploadItems();
    }

    renderUploadItems() {
        const container = document.getElementById('upload-items');
        container.innerHTML = this.selectedFiles.map((file, index) => `
            <div class="file-item" id="upload-item-${index}">
                <div class="file-info">
                    <div class="flex items-center space-x-2">
                        <i data-feather="file-text" class="w-4 h-4 text-gray-400"></i>
                        <div>
                            <div class="file-name">${file.name}</div>
                            <div class="file-size">${formatFileSize(file.size)}</div>
                        </div>
                    </div>
                </div>
                <div class="flex items-center space-x-3">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: 0%"></div>
                    </div>
                    <div class="file-status text-gray-500">Pending</div>
                    <div class="w-5 h-5 flex items-center justify-center">
                        <i data-feather="clock" class="w-4 h-4 text-gray-400"></i>
                    </div>
                </div>
            </div>
        `).join('');

        feather.replace();
    }

    updateFileProgress(fileItem) {
        const fileIndex = this.selectedFiles.findIndex(f => f.name === fileItem.file.name);
        if (fileIndex === -1) return;

        const item = document.getElementById(`upload-item-${fileIndex}`);
        if (!item) return;

        const progressFill = item.querySelector('.progress-fill');
        const statusEl = item.querySelector('.file-status');
        const iconEl = item.querySelector('.w-5 i');

        if (progressFill) {
            progressFill.style.width = `${fileItem.progress}%`;
        }

        if (statusEl) {
            statusEl.textContent = fileItem.status === 'uploading' ? 'Uploading...' : 
                                   fileItem.status === 'completed' ? 'Completed' :
                                   fileItem.status === 'error' ? 'Failed' : 'Pending';
        }

        if (iconEl) {
            const iconName = fileItem.status === 'uploading' ? 'loader' :
                            fileItem.status === 'completed' ? 'check-circle' :
                            fileItem.status === 'error' ? 'x-circle' : 'clock';
            iconEl.setAttribute('data-feather', iconName);
            
            const colorClass = fileItem.status === 'completed' ? 'text-green-500' :
                              fileItem.status === 'error' ? 'text-red-500' : 'text-gray-400';
            iconEl.className = `w-4 h-4 ${colorClass}`;
        }

        feather.replace();
        this.updateOverallProgress();
    }

    updateOverallProgress() {
        const stats = window.fileUploader.getStats();
        const progress = stats.total > 0 ? ((stats.completed + stats.errors) / stats.total) * 100 : 0;
        
        const progressBar = document.getElementById('overall-progress-bar');
        const percentage = document.getElementById('overall-percentage');
        const progressText = document.getElementById('progress-text');

        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
        
        if (percentage) {
            percentage.textContent = `${Math.round(progress)}%`;
        }

        if (progressText) {
            if (stats.uploading > 0) {
                progressText.textContent = `Uploading ${stats.uploading} of ${stats.total} files...`;
            } else if (progress === 100) {
                progressText.textContent = 'Upload complete!';
            } else {
                progressText.textContent = 'Preparing upload...';
            }
        }
    }

    onFileComplete(fileItem, result) {
        window.toastManager.success(`Successfully uploaded: ${fileItem.file.name}`);
    }

    onFileError(fileItem, error) {
        window.toastManager.error(`Failed to upload ${fileItem.file.name}: ${error.message}`);
    }

    onUploadComplete() {
        const stats = window.fileUploader.getStats();
        
        // Update summary
        document.getElementById('success-count').textContent = stats.completed;
        document.getElementById('error-count').textContent = stats.errors;
        document.getElementById('total-count').textContent = stats.total;
        
        // Show summary
        const summary = document.getElementById('upload-summary');
        summary.classList.remove('hidden');

        // Show toast notification
        if (stats.completed > 0) {
            window.toastManager.success(`Successfully uploaded ${stats.completed} document(s)`);
        }

        if (stats.errors > 0) {
            window.toastManager.error(`${stats.errors} upload(s) failed`);
        }

        // Refresh recent uploads
        this.loadRecentUploads();
    }

    async createTextDocument() {
        const id = document.getElementById('document-id').value.trim();
        const content = document.getElementById('document-content').value.trim();
        const category = document.getElementById('document-category').value.trim();
        const author = document.getElementById('document-author').value.trim();
        const tags = document.getElementById('document-tags').value.trim();

        if (!id || !content) {
            window.toastManager.error('Document ID and content are required');
            return;
        }

        const metadata = {};
        if (category) metadata.category = category;
        if (author) metadata.author = author;
        if (tags) metadata.tags = tags.split(',').map(tag => tag.trim()).filter(tag => tag);

        const documentData = {
            id: id,
            content: content,
            metadata: metadata
        };

        try {
            window.loadingManager.show('Creating document...');
            
            const result = await window.chromaAPI.createDocument(documentData);
            window.toastManager.success('Document created successfully');
            
            // Clear form
            document.getElementById('text-form').reset();
            document.getElementById('char-count').textContent = '0';
            document.getElementById('id-error').textContent = '';
            
            // Refresh recent uploads
            this.loadRecentUploads();
            
        } catch (error) {
            console.error('Error creating document:', error);
            window.toastManager.error('Failed to create document: ' + error.message);
        } finally {
            window.loadingManager.hide();
        }
    }

    validateDocumentId() {
        const input = document.getElementById('document-id');
        const error = document.getElementById('id-error');
        const value = input.value.trim();

        if (!value) {
            error.textContent = '';
            return;
        }

        // Validate ID format (alphanumeric, underscores, hyphens)
        const validPattern = /^[a-zA-Z0-9_-]+$/;
        if (!validPattern.test(value)) {
            error.textContent = 'ID can only contain letters, numbers, underscores, and hyphens';
            return;
        }

        // Clear error if valid
        error.textContent = '';
    }

    async loadRecentUploads() {
        const loadingEl = document.getElementById('recent-loading');
        const listEl = document.getElementById('recent-list');
        const emptyEl = document.getElementById('recent-empty');

        // Show loading
        loadingEl.classList.remove('hidden');
        listEl.classList.add('hidden');
        emptyEl.classList.add('hidden');

        try {
            const response = await window.chromaAPI.listDocuments({ limit: 10, offset: 0 });
            const documents = response.documents || [];

            // Filter recent uploads (last 24 hours)
            const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000);
            this.recentUploads = documents.filter(doc => {
                if (!doc.created_at) return false;
                const createdDate = new Date(doc.created_at);
                return createdDate > yesterday;
            });

            this.renderRecentUploads();

        } catch (error) {
            console.error('Error loading recent uploads:', error);
            window.toastManager.error('Failed to load recent uploads');
            this.showRecentEmpty();
        } finally {
            loadingEl.classList.add('hidden');
        }
    }

    renderRecentUploads() {
        const listEl = document.getElementById('recent-list');
        const emptyEl = document.getElementById('recent-empty');

        if (this.recentUploads.length === 0) {
            this.showRecentEmpty();
            return;
        }

        listEl.classList.remove('hidden');
        emptyEl.classList.add('hidden');

        listEl.innerHTML = this.recentUploads.map(doc => `
            <div class="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                <div class="flex items-center space-x-3">
                    <div class="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                        <i data-feather="file-text" class="w-4 h-4 text-green-600"></i>
                    </div>
                    <div>
                        <div class="text-sm font-medium text-gray-900">${doc.id}</div>
                        <div class="text-xs text-gray-500">
                            ${formatTimestamp(doc.created_at)} • ${truncateText(doc.content, 50)}
                        </div>
                        <div class="flex items-center space-x-1 mt-1">
                            ${doc.metadata?.category ? `<span class="badge badge-secondary">${doc.metadata.category}</span>` : ''}
                            ${doc.metadata?.author ? `<span class="badge badge-primary">${doc.metadata.author}</span>` : ''}
                        </div>
                    </div>
                </div>
                <div class="flex space-x-2">
                    <button onclick="window.location.href='/document/${doc.id}'" 
                            class="text-gray-400 hover:text-blue-600" title="View">
                        <i data-feather="eye" class="w-4 h-4"></i>
                    </button>
                    <button onclick="copyToClipboard('${doc.id}')" 
                            class="text-gray-400 hover:text-gray-600" title="Copy ID">
                        <i data-feather="copy" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>
        `).join('');

        feather.replace();
    }

    showRecentEmpty() {
        const listEl = document.getElementById('recent-list');
        const emptyEl = document.getElementById('recent-empty');
        
        listEl.classList.add('hidden');
        emptyEl.classList.remove('hidden');
    }

    resetUpload() {
        // Clear files
        this.clearFiles();
        
        // Hide progress
        const progressCard = document.getElementById('upload-progress');
        progressCard.classList.add('hidden');
        
        // Hide summary
        const summary = document.getElementById('upload-summary');
        summary.classList.add('hidden');
        
        // Reset file uploader
        window.fileUploader.clearCompleted();
        
        // Reset form
        document.getElementById('text-form').reset();
        document.getElementById('char-count').textContent = '0';
        
        // Show upload controls if files are selected
        if (this.selectedFiles.length > 0) {
            this.showUploadControls();
        }
    }
}

// Export for use in other scripts
window.UploadManager = UploadManager;