/**
 * Search functionality for ChromaDB Document Manager
 * Handles semantic search, keyword search, and result management
 */

class SearchManager {
    constructor() {
        this.currentResults = [];
        this.searchHistory = this.loadSearchHistory();
        this.filters = {
            category: '',
            author: ''
        };
        this.resultsCount = 10;
        this.currentQuery = '';
        this.searchType = 'semantic';
        
        // Debounced search function
        this.debouncedSearch = debounce(this.performSearch.bind(this), 500);
    }

    static init() {
        const manager = new SearchManager();
        manager.initializeElements();
        manager.loadFilterOptions();
        manager.renderSearchHistory();
        window.searchManager = manager;
    }

    initializeElements() {
        // Search input
        const searchInput = document.getElementById('search-query');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.currentQuery = e.target.value;
                if (this.currentQuery.length > 2) {
                    this.debouncedSearch();
                } else if (this.currentQuery.length === 0) {
                    this.showWelcomeState();
                }
            });
            
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performSearch();
                }
            });
        }

        // Search button
        const searchBtn = document.getElementById('search-btn');
        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                this.performSearch();
            });
        }

        // Search type radio buttons
        const searchTypeInputs = document.querySelectorAll('input[name="search-type"]');
        searchTypeInputs.forEach(input => {
            input.addEventListener('change', (e) => {
                this.searchType = e.target.value;
                if (this.currentQuery) {
                    this.performSearch();
                }
            });
        });

        // Results count slider
        const slider = document.getElementById('results-count-slider');
        const sliderValue = document.getElementById('slider-value');
        if (slider && sliderValue) {
            slider.addEventListener('input', (e) => {
                this.resultsCount = parseInt(e.target.value);
                sliderValue.textContent = this.resultsCount;
                if (this.currentQuery) {
                    this.performSearch();
                }
            });
        }

        // Filter selects
        const categoryFilter = document.getElementById('search-category-filter');
        if (categoryFilter) {
            categoryFilter.addEventListener('change', (e) => {
                this.filters.category = e.target.value;
                if (this.currentQuery) {
                    this.performSearch();
                }
            });
        }

        const authorFilter = document.getElementById('search-author-filter');
        if (authorFilter) {
            authorFilter.addEventListener('change', (e) => {
                this.filters.author = e.target.value;
                if (this.currentQuery) {
                    this.performSearch();
                }
            });
        }

        // Export results
        const exportBtn = document.getElementById('export-results');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportResults();
            });
        }

        // Clear results
        const clearBtn = document.getElementById('clear-results');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearSearch();
            });
        }

        // Clear history
        const clearHistoryBtn = document.getElementById('clear-history');
        if (clearHistoryBtn) {
            clearHistoryBtn.addEventListener('click', () => {
                this.clearSearchHistory();
            });
        }

        // Document preview modal
        const closePreview = document.getElementById('close-preview');
        if (closePreview) {
            closePreview.addEventListener('click', () => {
                this.closeDocumentPreview();
            });
        }

        const openDocument = document.getElementById('open-document');
        if (openDocument) {
            openDocument.addEventListener('click', () => {
                this.openCurrentDocument();
            });
        }
    }

    async loadFilterOptions() {
        try {
            // Load documents to populate filter options
            const response = await window.chromaAPI.listDocuments({ limit: 1000, offset: 0 });
            const documents = response.documents || [];

            const categories = new Set();
            const authors = new Set();

            documents.forEach(doc => {
                if (doc.metadata && doc.metadata.category) {
                    categories.add(doc.metadata.category);
                }
                if (doc.metadata && doc.metadata.author) {
                    authors.add(doc.metadata.author);
                }
            });

            this.populateSelect('search-category-filter', Array.from(categories));
            this.populateSelect('search-author-filter', Array.from(authors));

        } catch (error) {
            console.error('Error loading filter options:', error);
        }
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

    async performSearch() {
        if (!this.currentQuery.trim()) {
            this.showWelcomeState();
            return;
        }

        try {
            this.showLoadingState();

            // Build metadata filter
            const metadataFilter = {};
            if (this.filters.category) {
                metadataFilter.category = this.filters.category;
            }
            if (this.filters.author) {
                metadataFilter.author = this.filters.author;
            }

            let results;
            
            if (this.searchType === 'semantic') {
                // Use ChromaDB semantic search
                const searchData = {
                    query_text: this.currentQuery,
                    n_results: this.resultsCount,
                    metadata_filter: Object.keys(metadataFilter).length > 0 ? metadataFilter : null
                };
                
                results = await window.chromaAPI.searchDocuments(searchData);
                
                // Transform results to standard format
                this.currentResults = results.ids.map((id, index) => ({
                    id: id,
                    content: results.documents[index],
                    metadata: results.metadatas[index],
                    distance: results.distances[index],
                    relevance: 1 - results.distances[index] // Convert distance to relevance score
                }));
            } else {
                // Keyword search - get all documents and filter client-side
                const allDocuments = await window.chromaAPI.listDocuments({ limit: 1000, offset: 0 });
                const documents = allDocuments.documents || [];
                
                const searchTerm = this.currentQuery.toLowerCase();
                const filteredDocs = documents.filter(doc => {
                    // Text search
                    const searchableText = `${doc.id} ${doc.content} ${JSON.stringify(doc.metadata)}`.toLowerCase();
                    if (!searchableText.includes(searchTerm)) {
                        return false;
                    }
                    
                    // Apply metadata filters
                    if (this.filters.category && doc.metadata?.category !== this.filters.category) {
                        return false;
                    }
                    if (this.filters.author && doc.metadata?.author !== this.filters.author) {
                        return false;
                    }
                    
                    return true;
                });

                // Calculate simple relevance score based on term frequency
                this.currentResults = filteredDocs.slice(0, this.resultsCount).map(doc => {
                    const searchableText = `${doc.id} ${doc.content}`.toLowerCase();
                    const matches = (searchableText.match(new RegExp(searchTerm, 'g')) || []).length;
                    const relevance = Math.min(matches / 10, 1); // Normalize to 0-1
                    
                    return {
                        ...doc,
                        distance: 1 - relevance,
                        relevance: relevance
                    };
                });
            }

            if (this.currentResults.length > 0) {
                this.showSearchResults();
                this.addToSearchHistory(this.currentQuery);
            } else {
                this.showNoResults();
            }

        } catch (error) {
            console.error('Search error:', error);
            window.toastManager.error('Search failed: ' + error.message);
            this.showWelcomeState();
        }
    }

    showWelcomeState() {
        this.hideAllStates();
        document.getElementById('welcome-state').classList.remove('hidden');
    }

    showLoadingState() {
        this.hideAllStates();
        document.getElementById('search-loading').classList.remove('hidden');
    }

    showSearchResults() {
        this.hideAllStates();
        
        const resultsContainer = document.getElementById('search-results');
        const resultsList = document.getElementById('results-list');
        const resultsCount = document.getElementById('results-count');
        
        resultsContainer.classList.remove('hidden');
        resultsCount.textContent = `${this.currentResults.length} result${this.currentResults.length !== 1 ? 's' : ''} for "${this.currentQuery}"`;
        
        resultsList.innerHTML = this.currentResults.map((result, index) => `
            <div class="search-result fade-in" style="animation-delay: ${index * 0.05}s">
                <div class="flex items-start justify-between mb-2">
                    <div class="flex items-center space-x-3">
                        <h3 class="text-lg font-medium text-gray-900">${result.id}</h3>
                        <div class="flex items-center space-x-2">
                            <span class="relevance-score">
                                ${Math.round(result.relevance * 100)}% match
                            </span>
                            ${result.metadata?.category ? `<span class="badge badge-secondary">${result.metadata.category}</span>` : ''}
                            ${result.metadata?.author ? `<span class="badge badge-primary">${result.metadata.author}</span>` : ''}
                        </div>
                    </div>
                    <div class="flex space-x-2">
                        <button onclick="window.searchManager.previewDocument('${result.id}')" 
                                class="text-gray-400 hover:text-blue-600" title="Preview">
                            <i data-feather="eye" class="w-4 h-4"></i>
                        </button>
                        <button onclick="window.location.href='/document/${result.id}'" 
                                class="text-gray-400 hover:text-green-600" title="Open">
                            <i data-feather="external-link" class="w-4 h-4"></i>
                        </button>
                        <button onclick="copyToClipboard('${result.id}')" 
                                class="text-gray-400 hover:text-gray-600" title="Copy ID">
                            <i data-feather="copy" class="w-4 h-4"></i>
                        </button>
                    </div>
                </div>
                <div class="document-match">
                    ${this.highlightSearchTerms(truncateText(result.content, 300), this.currentQuery)}
                </div>
                <div class="flex items-center justify-between mt-3 text-xs text-gray-500">
                    <div class="flex items-center space-x-4">
                        <span>Distance: ${result.distance?.toFixed(3) || 'N/A'}</span>
                        ${result.metadata?.filename ? `<span>File: ${result.metadata.filename}</span>` : ''}
                        <span>Updated: ${formatTimestamp(result.updated_at)}</span>
                    </div>
                    <div class="flex items-center space-x-1">
                        ${[1,2,3,4,5].map(i => `
                            <div class="w-2 h-2 rounded-full ${i <= Math.ceil(result.relevance * 5) ? 'bg-blue-500' : 'bg-gray-200'}"></div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `).join('');
        
        feather.replace();
    }

    showNoResults() {
        this.hideAllStates();
        document.getElementById('no-results').classList.remove('hidden');
    }

    hideAllStates() {
        ['welcome-state', 'search-loading', 'search-results', 'no-results'].forEach(id => {
            document.getElementById(id).classList.add('hidden');
        });
    }

    highlightSearchTerms(text, searchTerm) {
        if (!searchTerm || this.searchType === 'semantic') {
            return text;
        }
        
        const regex = new RegExp(`(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        return text.replace(regex, '<span class="highlight">$1</span>');
    }

    async previewDocument(documentId) {
        try {
            window.loadingManager.show('Loading document preview...');
            
            const document = await window.chromaAPI.getDocument(documentId);
            this.showDocumentPreview(document);
            
        } catch (error) {
            console.error('Error loading document preview:', error);
            window.toastManager.error('Failed to load document preview: ' + error.message);
        } finally {
            window.loadingManager.hide();
        }
    }

    showDocumentPreview(document) {
        const modal = document.getElementById('document-preview-modal');
        const title = document.getElementById('preview-title');
        const content = document.getElementById('preview-content');

        title.textContent = document.id;
        content.innerHTML = `
            <div class="space-y-4">
                <div class="flex items-start justify-between">
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900">${document.id}</h3>
                        <div class="flex items-center space-x-2 mt-1">
                            ${document.metadata?.category ? `<span class="badge badge-secondary">${document.metadata.category}</span>` : ''}
                            ${document.metadata?.author ? `<span class="badge badge-primary">${document.metadata.author}</span>` : ''}
                            <span class="text-sm text-gray-500">${formatTimestamp(document.updated_at)}</span>
                        </div>
                    </div>
                </div>
                
                <div class="border-t border-gray-200 pt-4">
                    <div class="prose max-w-none">
                        <div class="whitespace-pre-wrap text-gray-700 leading-relaxed">
                            ${this.highlightSearchTerms(document.content, this.currentQuery)}
                        </div>
                    </div>
                </div>
                
                ${Object.keys(document.metadata || {}).length > 0 ? `
                <div class="border-t border-gray-200 pt-4">
                    <h4 class="text-sm font-medium text-gray-900 mb-2">Metadata</h4>
                    <div class="bg-gray-50 rounded-lg p-3">
                        <pre class="text-xs text-gray-600">${JSON.stringify(document.metadata, null, 2)}</pre>
                    </div>
                </div>
                ` : ''}
            </div>
        `;

        modal.classList.remove('hidden');
        this.currentPreviewDocumentId = document.id;
    }

    closeDocumentPreview() {
        const modal = document.getElementById('document-preview-modal');
        modal.classList.add('hidden');
        this.currentPreviewDocumentId = null;
    }

    openCurrentDocument() {
        if (this.currentPreviewDocumentId) {
            window.location.href = `/document/${this.currentPreviewDocumentId}`;
        }
    }

    exportResults() {
        if (this.currentResults.length === 0) {
            window.toastManager.warning('No results to export');
            return;
        }

        const exportData = {
            query: this.currentQuery,
            searchType: this.searchType,
            timestamp: new Date().toISOString(),
            resultsCount: this.currentResults.length,
            results: this.currentResults.map(result => ({
                id: result.id,
                content: result.content,
                metadata: result.metadata,
                relevance: result.relevance,
                distance: result.distance
            }))
        };

        const jsonStr = JSON.stringify(exportData, null, 2);
        const filename = `search_results_${this.currentQuery.replace(/[^a-zA-Z0-9]/g, '_')}_${new Date().toISOString().split('T')[0]}.json`;
        
        downloadAsFile(jsonStr, filename, 'application/json');
        window.toastManager.success('Search results exported successfully');
    }

    clearSearch() {
        document.getElementById('search-query').value = '';
        this.currentQuery = '';
        this.currentResults = [];
        this.showWelcomeState();
    }

    setQuery(query) {
        document.getElementById('search-query').value = query;
        this.currentQuery = query;
        this.performSearch();
    }

    addToSearchHistory(query) {
        // Remove if already exists
        this.searchHistory = this.searchHistory.filter(item => item.query !== query);
        
        // Add to beginning
        this.searchHistory.unshift({
            query: query,
            timestamp: new Date().toISOString(),
            resultsCount: this.currentResults.length
        });

        // Keep only last 10 searches
        this.searchHistory = this.searchHistory.slice(0, 10);
        
        this.saveSearchHistory();
        this.renderSearchHistory();
    }

    renderSearchHistory() {
        const historyContainer = document.getElementById('search-history');
        
        if (this.searchHistory.length === 0) {
            historyContainer.innerHTML = '<div class="text-sm text-gray-500 text-center py-4">No recent searches</div>';
            return;
        }

        historyContainer.innerHTML = this.searchHistory.map(item => `
            <div class="flex items-center justify-between p-2 hover:bg-gray-50 rounded cursor-pointer"
                 onclick="window.searchManager.setQuery('${item.query}')">
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-gray-900 truncate">${item.query}</div>
                    <div class="text-xs text-gray-500">${item.resultsCount} results • ${formatTimestamp(item.timestamp)}</div>
                </div>
                <button onclick="event.stopPropagation(); window.searchManager.removeFromHistory('${item.query}')" 
                        class="text-gray-400 hover:text-gray-600 ml-2">
                    <i data-feather="x" class="w-3 h-3"></i>
                </button>
            </div>
        `).join('');

        feather.replace();
    }

    removeFromHistory(query) {
        this.searchHistory = this.searchHistory.filter(item => item.query !== query);
        this.saveSearchHistory();
        this.renderSearchHistory();
    }

    clearSearchHistory() {
        this.searchHistory = [];
        this.saveSearchHistory();
        this.renderSearchHistory();
        window.toastManager.success('Search history cleared');
    }

    loadSearchHistory() {
        try {
            const saved = localStorage.getItem('chromadb_search_history');
            return saved ? JSON.parse(saved) : [];
        } catch (error) {
            console.error('Error loading search history:', error);
            return [];
        }
    }

    saveSearchHistory() {
        try {
            localStorage.setItem('chromadb_search_history', JSON.stringify(this.searchHistory));
        } catch (error) {
            console.error('Error saving search history:', error);
        }
    }
}

// Export for use in other scripts
window.SearchManager = SearchManager;