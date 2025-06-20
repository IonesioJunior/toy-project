/**
 * Document Management JavaScript
 * Handles document listing, searching, filtering, and CRUD operations
 */

class DocumentManager {
    constructor() {
        this.currentPage = 1;
        this.itemsPerPage = 12;
        this.totalDocuments = 0;
        this.documents = [];
        this.filteredDocuments = [];
        this.selectedDocuments = new Set();
        this.viewMode = 'grid'; // 'grid' or 'list'
        this.filters = {
            search: '',
            category: '',
            author: '',
            dateRange: ''
        };
        
        // Debounced search function
        this.debouncedSearch = debounce(this.performSearch.bind(this), 300);
    }

    static init() {
        const manager = new DocumentManager();
        manager.initializeElements();
        manager.loadDocuments();
        window.documentManager = manager;
    }

    initializeElements() {
        // Search input
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filters.search = e.target.value;
                this.debouncedSearch();
            });
        }

        // View toggle
        const viewToggle = document.getElementById('view-toggle');
        if (viewToggle) {
            viewToggle.addEventListener('click', () => {
                this.toggleView();
            });
        }

        // Filter toggle
        const filterToggle = document.getElementById('filter-toggle');
        if (filterToggle) {
            filterToggle.addEventListener('click', () => {
                this.toggleFilters();
            });
        }

        // Clear filters
        const clearFilters = document.getElementById('clear-filters');
        if (clearFilters) {
            clearFilters.addEventListener('click', () => {
                this.clearFilters();
            });
        }

        // Filter inputs
        ['category-filter', 'author-filter', 'date-filter'].forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', () => {
                    this.updateFilters();
                });
            }
        });

        // Bulk actions
        const bulkDelete = document.getElementById('bulk-delete');
        if (bulkDelete) {
            bulkDelete.addEventListener('click', () => {
                this.bulkDeleteDocuments();
            });
        }

        const deselectAll = document.getElementById('deselect-all');
        if (deselectAll) {
            deselectAll.addEventListener('click', () => {
                this.deselectAllDocuments();
            });
        }

        // Pagination
        const prevPage = document.getElementById('prev-page');
        if (prevPage) {
            prevPage.addEventListener('click', () => {
                if (this.currentPage > 1) {
                    this.currentPage--;
                    this.renderDocuments();
                }
            });
        }

        const nextPage = document.getElementById('next-page');
        if (nextPage) {
            nextPage.addEventListener('click', () => {
                const totalPages = Math.ceil(this.totalDocuments / this.itemsPerPage);
                if (this.currentPage < totalPages) {
                    this.currentPage++;
                    this.renderDocuments();
                }
            });
        }

        // Modal handlers
        const closeModal = document.getElementById('close-modal');
        if (closeModal) {
            closeModal.addEventListener('click', () => {
                this.closeDocumentModal();
            });
        }

        const editDocument = document.getElementById('edit-document');
        if (editDocument) {
            editDocument.addEventListener('click', () => {
                this.editCurrentDocument();
            });
        }

        const deleteDocument = document.getElementById('delete-document');
        if (deleteDocument) {
            deleteDocument.addEventListener('click', () => {
                this.deleteCurrentDocument();
            });
        }
    }

    async loadDocuments() {
        try {
            window.loadingManager.show('Loading documents...');
            
            const response = await window.chromaAPI.listDocuments({
                limit: 1000, // Load all for client-side filtering
                offset: 0
            });

            this.documents = response.documents || [];
            this.totalDocuments = response.total || 0;
            this.filteredDocuments = [...this.documents];

            this.populateFilterOptions();
            this.renderDocuments();
            
        } catch (error) {
            console.error('Error loading documents:', error);
            window.toastManager.error('Failed to load documents: ' + error.message);
            this.showEmptyState();
        } finally {
            window.loadingManager.hide();
        }
    }

    populateFilterOptions() {
        // Populate category filter
        const categories = new Set();
        const authors = new Set();

        this.documents.forEach(doc => {
            if (doc.metadata && doc.metadata.category) {
                categories.add(doc.metadata.category);
            }
            if (doc.metadata && doc.metadata.author) {
                authors.add(doc.metadata.author);
            }
        });

        this.populateSelect('category-filter', Array.from(categories));
        this.populateSelect('author-filter', Array.from(authors));
    }

    populateSelect(selectId, options) {
        const select = document.getElementById(selectId);
        if (!select) return;

        // Keep the first option (All)
        const firstOption = select.children[0];
        select.innerHTML = '';
        select.appendChild(firstOption);

        options.forEach(option => {
            const optionElement = document.createElement('option');
            optionElement.value = option;
            optionElement.textContent = option;
            select.appendChild(optionElement);
        });
    }

    updateFilters() {
        this.filters.category = document.getElementById('category-filter')?.value || '';
        this.filters.author = document.getElementById('author-filter')?.value || '';
        this.filters.dateRange = document.getElementById('date-filter')?.value || '';

        this.applyFilters();
        this.updateFilterCount();
    }

    applyFilters() {
        this.filteredDocuments = this.documents.filter(doc => {
            // Search filter
            if (this.filters.search) {
                const searchTerm = this.filters.search.toLowerCase();
                const searchable = `${doc.id} ${doc.content} ${JSON.stringify(doc.metadata)}`.toLowerCase();
                if (!searchable.includes(searchTerm)) {
                    return false;
                }
            }

            // Category filter
            if (this.filters.category && doc.metadata?.category !== this.filters.category) {
                return false;
            }

            // Author filter
            if (this.filters.author && doc.metadata?.author !== this.filters.author) {
                return false;
            }

            // Date range filter
            if (this.filters.dateRange && doc.updated_at) {
                const docDate = new Date(doc.updated_at);
                const now = new Date();
                
                switch (this.filters.dateRange) {
                    case 'today':
                        if (docDate.toDateString() !== now.toDateString()) return false;
                        break;
                    case 'week':
                        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                        if (docDate < weekAgo) return false;
                        break;
                    case 'month':
                        const monthAgo = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
                        if (docDate < monthAgo) return false;
                        break;
                    case 'year':
                        const yearAgo = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
                        if (docDate < yearAgo) return false;
                        break;
                }
            }

            return true;
        });

        this.currentPage = 1; // Reset to first page
        this.renderDocuments();
    }

    updateFilterCount() {
        const activeFilters = Object.values(this.filters).filter(val => val !== '').length;
        const filterCount = document.getElementById('filter-count');
        
        if (filterCount) {
            if (activeFilters > 0) {
                filterCount.textContent = activeFilters;
                filterCount.classList.remove('hidden');
            } else {
                filterCount.classList.add('hidden');
            }
        }
    }

    performSearch() {
        this.applyFilters();
    }

    clearFilters() {
        this.filters = {
            search: '',
            category: '',
            author: '',
            dateRange: ''
        };

        // Clear form inputs
        document.getElementById('search-input').value = '';
        document.getElementById('category-filter').value = '';
        document.getElementById('author-filter').value = '';
        document.getElementById('date-filter').value = '';

        this.filteredDocuments = [...this.documents];
        this.currentPage = 1;
        this.renderDocuments();
        this.updateFilterCount();
    }

    toggleView() {
        this.viewMode = this.viewMode === 'grid' ? 'list' : 'grid';
        
        const viewToggle = document.getElementById('view-toggle');
        const icon = viewToggle.querySelector('i');
        
        if (this.viewMode === 'grid') {
            icon.setAttribute('data-feather', 'grid');
            viewToggle.childNodes[2].textContent = 'Grid View';
        } else {
            icon.setAttribute('data-feather', 'list');
            viewToggle.childNodes[2].textContent = 'List View';
        }
        
        feather.replace();
        this.renderDocuments();
    }

    toggleFilters() {
        const sidebar = document.getElementById('filter-sidebar');
        sidebar.classList.toggle('hidden');
    }

    renderDocuments() {
        const documentsGrid = document.getElementById('documents-grid');
        const documentsList = document.getElementById('documents-list');
        const loadingState = document.getElementById('loading-documents');
        const emptyState = document.getElementById('empty-state');

        // Hide loading state
        loadingState.classList.add('hidden');

        if (this.filteredDocuments.length === 0) {
            this.showEmptyState();
            return;
        }

        // Hide empty state
        emptyState.classList.add('hidden');

        // Calculate pagination
        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = Math.min(startIndex + this.itemsPerPage, this.filteredDocuments.length);
        const pageDocuments = this.filteredDocuments.slice(startIndex, endIndex);

        if (this.viewMode === 'grid') {
            documentsGrid.classList.remove('hidden');
            documentsList.classList.add('hidden');
            this.renderGridView(pageDocuments, documentsGrid);
        } else {
            documentsGrid.classList.add('hidden');
            documentsList.classList.remove('hidden');
            this.renderListView(pageDocuments, documentsList);
        }

        this.renderPagination();
    }

    renderGridView(documents, container) {
        container.innerHTML = documents.map(doc => `
            <div class="document-card" data-document-id="${doc.id}">
                <div class="flex items-start justify-between mb-2">
                    <input type="checkbox" class="document-checkbox" data-document-id="${doc.id}" 
                           ${this.selectedDocuments.has(doc.id) ? 'checked' : ''}>
                    <div class="document-actions">
                        <button onclick="window.documentManager.viewDocument('${doc.id}')" 
                                class="text-gray-400 hover:text-blue-600" title="View">
                            <i data-feather="eye" class="w-4 h-4"></i>
                        </button>
                        <button onclick="window.documentManager.editDocument('${doc.id}')" 
                                class="text-gray-400 hover:text-green-600" title="Edit">
                            <i data-feather="edit" class="w-4 h-4"></i>
                        </button>
                        <button onclick="window.documentManager.deleteDocument('${doc.id}')" 
                                class="text-gray-400 hover:text-red-600" title="Delete">
                            <i data-feather="trash-2" class="w-4 h-4"></i>
                        </button>
                    </div>
                </div>
                <div class="document-id">${doc.id}</div>
                <div class="document-preview">${truncateText(doc.content, 120)}</div>
                <div class="document-meta">
                    <div class="flex flex-wrap gap-1">
                        ${doc.metadata?.category ? `<span class="badge badge-secondary">${doc.metadata.category}</span>` : ''}
                        ${doc.metadata?.author ? `<span class="badge badge-primary">${doc.metadata.author}</span>` : ''}
                    </div>
                    <span class="text-xs text-gray-400">${formatTimestamp(doc.updated_at)}</span>
                </div>
            </div>
        `).join('');

        this.attachDocumentEventListeners(container);
        feather.replace();
    }

    renderListView(documents, container) {
        container.innerHTML = documents.map(doc => `
            <div class="flex items-center space-x-4 p-4 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow" 
                 data-document-id="${doc.id}">
                <input type="checkbox" class="document-checkbox" data-document-id="${doc.id}"
                       ${this.selectedDocuments.has(doc.id) ? 'checked' : ''}>
                <div class="flex-shrink-0">
                    <div class="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                        <i data-feather="file-text" class="w-5 h-5 text-blue-600"></i>
                    </div>
                </div>
                <div class="flex-1 min-w-0">
                    <h4 class="text-sm font-medium text-gray-900 mb-1">${doc.id}</h4>
                    <p class="text-sm text-gray-600 line-clamp-2">${truncateText(doc.content, 150)}</p>
                    <div class="flex items-center mt-2 space-x-2">
                        ${doc.metadata?.category ? `<span class="badge badge-secondary">${doc.metadata.category}</span>` : ''}
                        ${doc.metadata?.author ? `<span class="badge badge-primary">${doc.metadata.author}</span>` : ''}
                        <span class="text-xs text-gray-400">${formatTimestamp(doc.updated_at)}</span>
                    </div>
                </div>
                <div class="flex-shrink-0 flex space-x-2">
                    <button onclick="window.documentManager.viewDocument('${doc.id}')" 
                            class="text-gray-400 hover:text-blue-600" title="View">
                        <i data-feather="eye" class="w-4 h-4"></i>
                    </button>
                    <button onclick="window.documentManager.editDocument('${doc.id}')" 
                            class="text-gray-400 hover:text-green-600" title="Edit">
                        <i data-feather="edit" class="w-4 h-4"></i>
                    </button>
                    <button onclick="window.documentManager.deleteDocument('${doc.id}')" 
                            class="text-gray-400 hover:text-red-600" title="Delete">
                        <i data-feather="trash-2" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>
        `).join('');

        this.attachDocumentEventListeners(container);
        feather.replace();
    }

    attachDocumentEventListeners(container) {
        // Checkbox event listeners
        const checkboxes = container.querySelectorAll('.document-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const documentId = e.target.dataset.documentId;
                if (e.target.checked) {
                    this.selectedDocuments.add(documentId);
                } else {
                    this.selectedDocuments.delete(documentId);
                }
                this.updateBulkActions();
            });
        });

        // Click to view document
        const cards = container.querySelectorAll('.document-card, [data-document-id]');
        cards.forEach(card => {
            card.addEventListener('click', (e) => {
                // Don't trigger if clicking on checkbox or action buttons
                if (e.target.type === 'checkbox' || e.target.closest('button')) {
                    return;
                }
                const documentId = card.dataset.documentId;
                this.viewDocument(documentId);
            });
        });
    }

    renderPagination() {
        const totalPages = Math.ceil(this.filteredDocuments.length / this.itemsPerPage);
        const paginationContainer = document.getElementById('pagination-container');
        
        if (totalPages <= 1) {
            paginationContainer.classList.add('hidden');
            return;
        }

        paginationContainer.classList.remove('hidden');

        // Update pagination info
        const startItem = (this.currentPage - 1) * this.itemsPerPage + 1;
        const endItem = Math.min(this.currentPage * this.itemsPerPage, this.filteredDocuments.length);
        
        document.getElementById('page-start').textContent = startItem;
        document.getElementById('page-end').textContent = endItem;
        document.getElementById('total-documents').textContent = this.filteredDocuments.length;

        // Update pagination buttons
        const prevButton = document.getElementById('prev-page');
        const nextButton = document.getElementById('next-page');
        
        prevButton.disabled = this.currentPage === 1;
        nextButton.disabled = this.currentPage === totalPages;

        // Update page numbers
        const pageNumbersContainer = document.getElementById('page-numbers');
        const pagination = new PaginationManager(this.filteredDocuments.length, this.itemsPerPage, this.currentPage);
        const pageNumbers = pagination.getPageNumbers();

        pageNumbersContainer.innerHTML = pageNumbers.map(pageNum => `
            <button class="pagination-btn ${pageNum === this.currentPage ? 'active' : ''}" 
                    onclick="window.documentManager.goToPage(${pageNum})">
                ${pageNum}
            </button>
        `).join('');
    }

    goToPage(pageNum) {
        this.currentPage = pageNum;
        this.renderDocuments();
    }

    updateBulkActions() {
        const bulkActions = document.getElementById('bulk-actions');
        const selectedCount = document.getElementById('selected-count');
        
        if (this.selectedDocuments.size > 0) {
            bulkActions.classList.remove('hidden');
            selectedCount.textContent = this.selectedDocuments.size;
        } else {
            bulkActions.classList.add('hidden');
        }
    }

    async viewDocument(documentId) {
        try {
            window.loadingManager.show('Loading document...');
            
            const document = await window.chromaAPI.getDocument(documentId);
            this.showDocumentModal(document);
            
        } catch (error) {
            console.error('Error loading document:', error);
            window.toastManager.error('Failed to load document: ' + error.message);
        } finally {
            window.loadingManager.hide();
        }
    }

    showDocumentModal(document) {
        const modal = document.getElementById('document-modal');
        const title = document.getElementById('modal-title');
        const content = document.getElementById('modal-content');

        title.textContent = document.id;
        content.innerHTML = `
            <div class="space-y-6">
                <div>
                    <label class="form-label">Document ID</label>
                    <div class="font-mono text-sm bg-gray-50 p-2 rounded border">${document.id}</div>
                </div>
                
                <div>
                    <label class="form-label">Content</label>
                    <div class="bg-gray-50 p-4 rounded border max-h-64 overflow-y-auto whitespace-pre-wrap">${document.content}</div>
                </div>
                
                <div>
                    <label class="form-label">Metadata</label>
                    <div class="bg-gray-50 p-4 rounded border">
                        <pre class="text-sm">${JSON.stringify(document.metadata, null, 2)}</pre>
                    </div>
                </div>
                
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="form-label">Created</label>
                        <div class="text-sm text-gray-600">${formatTimestamp(document.created_at)}</div>
                    </div>
                    <div>
                        <label class="form-label">Updated</label>
                        <div class="text-sm text-gray-600">${formatTimestamp(document.updated_at)}</div>
                    </div>
                </div>
            </div>
        `;

        modal.classList.remove('hidden');
        this.currentDocumentId = document.id;
    }

    closeDocumentModal() {
        const modal = document.getElementById('document-modal');
        modal.classList.add('hidden');
        this.currentDocumentId = null;
    }

    async editDocument(documentId) {
        // For now, just show an alert. In a full implementation, 
        // this would open an edit form
        window.toastManager.info('Edit functionality would be implemented here');
    }

    editCurrentDocument() {
        if (this.currentDocumentId) {
            this.editDocument(this.currentDocumentId);
        }
    }

    async deleteDocument(documentId) {
        window.modalManager.confirm(
            'Delete Document',
            `Are you sure you want to delete document "${documentId}"? This action cannot be undone.`,
            async () => {
                try {
                    await window.chromaAPI.deleteDocument(documentId);
                    window.toastManager.success('Document deleted successfully');
                    
                    // Remove from local arrays
                    this.documents = this.documents.filter(doc => doc.id !== documentId);
                    this.filteredDocuments = this.filteredDocuments.filter(doc => doc.id !== documentId);
                    this.selectedDocuments.delete(documentId);
                    
                    // Re-render
                    this.renderDocuments();
                    this.updateBulkActions();
                    
                    // Close modal if this document was being viewed
                    if (this.currentDocumentId === documentId) {
                        this.closeDocumentModal();
                    }
                    
                } catch (error) {
                    console.error('Error deleting document:', error);
                    window.toastManager.error('Failed to delete document: ' + error.message);
                }
            }
        );
    }

    deleteCurrentDocument() {
        if (this.currentDocumentId) {
            this.deleteDocument(this.currentDocumentId);
        }
    }

    async bulkDeleteDocuments() {
        const selectedIds = Array.from(this.selectedDocuments);
        
        window.modalManager.confirm(
            'Delete Documents',
            `Are you sure you want to delete ${selectedIds.length} selected documents? This action cannot be undone.`,
            async () => {
                try {
                    window.loadingManager.show('Deleting documents...');
                    
                    // Delete documents one by one
                    const results = await Promise.allSettled(
                        selectedIds.map(id => window.chromaAPI.deleteDocument(id))
                    );
                    
                    const successful = results.filter(r => r.status === 'fulfilled').length;
                    const failed = results.filter(r => r.status === 'rejected').length;
                    
                    if (successful > 0) {
                        window.toastManager.success(`${successful} documents deleted successfully`);
                        
                        // Remove from local arrays
                        this.documents = this.documents.filter(doc => !selectedIds.includes(doc.id));
                        this.filteredDocuments = this.filteredDocuments.filter(doc => !selectedIds.includes(doc.id));
                        this.selectedDocuments.clear();
                        
                        // Re-render
                        this.renderDocuments();
                        this.updateBulkActions();
                    }
                    
                    if (failed > 0) {
                        window.toastManager.error(`${failed} documents failed to delete`);
                    }
                    
                } catch (error) {
                    console.error('Error in bulk delete:', error);
                    window.toastManager.error('Failed to delete documents: ' + error.message);
                } finally {
                    window.loadingManager.hide();
                }
            }
        );
    }

    deselectAllDocuments() {
        this.selectedDocuments.clear();
        
        // Uncheck all checkboxes
        const checkboxes = document.querySelectorAll('.document-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
        
        this.updateBulkActions();
    }

    showEmptyState() {
        document.getElementById('loading-documents').classList.add('hidden');
        document.getElementById('documents-grid').classList.add('hidden');
        document.getElementById('documents-list').classList.add('hidden');
        document.getElementById('empty-state').classList.remove('hidden');
        document.getElementById('pagination-container').classList.add('hidden');
    }
}

// Export for use in other scripts
window.DocumentManager = DocumentManager;