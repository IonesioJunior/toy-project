/**
 * Utility functions for the ChromaDB Document Manager
 */

/**
 * Toast notification system
 */
class ToastManager {
    constructor() {
        this.container = document.getElementById('toast-container');
        this.toasts = new Map();
    }

    show(message, type = 'info', duration = 5000) {
        const toastId = 'toast_' + Date.now();
        const toast = this.createToast(toastId, message, type);
        
        this.container.appendChild(toast);
        this.toasts.set(toastId, toast);

        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                this.remove(toastId);
            }, duration);
        }

        return toastId;
    }

    createToast(id, message, type) {
        const toast = document.createElement('div');
        toast.id = id;
        toast.className = `toast toast-${type}`;
        
        const iconMap = {
            success: 'check-circle',
            error: 'x-circle',
            warning: 'alert-triangle',
            info: 'info'
        };

        toast.innerHTML = `
            <div class="toast-content">
                <div class="flex items-start">
                    <div class="flex-shrink-0">
                        <i data-feather="${iconMap[type] || 'info'}" class="w-5 h-5 text-${type === 'error' ? 'red' : type === 'success' ? 'green' : type === 'warning' ? 'yellow' : 'blue'}-500"></i>
                    </div>
                    <div class="ml-3 flex-1">
                        <p class="toast-message">${message}</p>
                    </div>
                    <div class="ml-4 flex-shrink-0">
                        <button onclick="window.toastManager.remove('${id}')" class="text-gray-400 hover:text-gray-600">
                            <i data-feather="x" class="w-4 h-4"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Initialize feather icons for the toast
        setTimeout(() => feather.replace(), 0);
        
        return toast;
    }

    remove(toastId) {
        const toast = this.toasts.get(toastId);
        if (toast) {
            toast.style.animation = 'slideOutRight 0.3s ease-in forwards';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
                this.toasts.delete(toastId);
            }, 300);
        }
    }

    success(message, duration) {
        return this.show(message, 'success', duration);
    }

    error(message, duration) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration) {
        return this.show(message, 'info', duration);
    }
}

/**
 * Modal management
 */
class ModalManager {
    constructor() {
        this.activeModal = null;
    }

    show(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
            this.activeModal = modalId;
            document.body.style.overflow = 'hidden';
        }
    }

    hide(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
            this.activeModal = null;
            document.body.style.overflow = '';
        }
    }

    confirm(title, message, onConfirm, onCancel) {
        const modal = document.getElementById('confirm-modal');
        const titleEl = document.getElementById('confirm-title');
        const messageEl = document.getElementById('confirm-message');
        const confirmBtn = document.getElementById('confirm-proceed');
        const cancelBtn = document.getElementById('confirm-cancel');

        titleEl.textContent = title;
        messageEl.textContent = message;

        // Remove existing event listeners
        const newConfirmBtn = confirmBtn.cloneNode(true);
        const newCancelBtn = cancelBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
        cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);

        // Add new event listeners
        newConfirmBtn.addEventListener('click', () => {
            this.hide('confirm-modal');
            onConfirm && onConfirm();
        });

        newCancelBtn.addEventListener('click', () => {
            this.hide('confirm-modal');
            onCancel && onCancel();
        });

        this.show('confirm-modal');
    }
}

/**
 * Loading overlay management
 */
class LoadingManager {
    constructor() {
        this.overlay = document.getElementById('loading-overlay');
        this.isLoading = false;
    }

    show(message = 'Loading...') {
        if (this.overlay) {
            const messageEl = this.overlay.querySelector('span');
            if (messageEl) {
                messageEl.textContent = message;
            }
            this.overlay.classList.remove('hidden');
            this.isLoading = true;
        }
    }

    hide() {
        if (this.overlay) {
            this.overlay.classList.add('hidden');
            this.isLoading = false;
        }
    }
}

/**
 * Debounce function for search inputs
 */
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func.apply(this, args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(this, args);
    };
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return 'Unknown';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
        return 'Today ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    } else if (diffDays === 1) {
        return 'Yesterday ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    } else if (diffDays < 7) {
        return `${diffDays} days ago`;
    } else {
        return date.toLocaleDateString();
    }
}

/**
 * Truncate text to specified length
 */
function truncateText(text, maxLength = 100) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

/**
 * Highlight search terms in text
 */
function highlightText(text, searchTerm) {
    if (!searchTerm || !text) return text;
    
    const regex = new RegExp(`(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return text.replace(regex, '<span class="highlight">$1</span>');
}

/**
 * Generate a random color for categories
 */
function generateCategoryColor(category) {
    const colors = [
        'bg-blue-100 text-blue-800',
        'bg-green-100 text-green-800',
        'bg-yellow-100 text-yellow-800',
        'bg-red-100 text-red-800',
        'bg-purple-100 text-purple-800',
        'bg-pink-100 text-pink-800',
        'bg-indigo-100 text-indigo-800',
    ];
    
    let hash = 0;
    for (let i = 0; i < category.length; i++) {
        hash = category.charCodeAt(i) + ((hash << 5) - hash);
    }
    
    return colors[Math.abs(hash) % colors.length];
}

/**
 * Validate file types for upload
 */
function validateFileType(file) {
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
    
    return hasValidType || hasValidExtension;
}

/**
 * Format file size for display
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        window.toastManager.success('Copied to clipboard');
    } catch (err) {
        console.error('Failed to copy text: ', err);
        window.toastManager.error('Failed to copy to clipboard');
    }
}

/**
 * Download text as file
 */
function downloadAsFile(content, filename, contentType = 'text/plain') {
    const blob = new Blob([content], { type: contentType });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
}

/**
 * Pagination helper
 */
class PaginationManager {
    constructor(totalItems, itemsPerPage, currentPage = 1) {
        this.totalItems = totalItems;
        this.itemsPerPage = itemsPerPage;
        this.currentPage = currentPage;
    }

    get totalPages() {
        return Math.ceil(this.totalItems / this.itemsPerPage);
    }

    get hasNext() {
        return this.currentPage < this.totalPages;
    }

    get hasPrev() {
        return this.currentPage > 1;
    }

    get startItem() {
        return (this.currentPage - 1) * this.itemsPerPage + 1;
    }

    get endItem() {
        return Math.min(this.currentPage * this.itemsPerPage, this.totalItems);
    }

    getPageNumbers(maxVisible = 5) {
        const pages = [];
        const startPage = Math.max(1, this.currentPage - Math.floor(maxVisible / 2));
        const endPage = Math.min(this.totalPages, startPage + maxVisible - 1);

        for (let i = startPage; i <= endPage; i++) {
            pages.push(i);
        }

        return pages;
    }
}

// Initialize global utilities
document.addEventListener('DOMContentLoaded', function() {
    // Initialize global managers
    window.toastManager = new ToastManager();
    window.modalManager = new ModalManager();
    window.loadingManager = new LoadingManager();

    // Global keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K for global search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('#global-search');
            if (searchInput) {
                searchInput.focus();
            } else {
                // Navigate to search page
                window.location.href = '/search';
            }
        }

        // Escape to close modals
        if (e.key === 'Escape') {
            if (window.modalManager.activeModal) {
                window.modalManager.hide(window.modalManager.activeModal);
            }
        }
    });

    // Handle clicks outside modals
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('fixed') && e.target.classList.contains('inset-0')) {
            if (window.modalManager.activeModal) {
                window.modalManager.hide(window.modalManager.activeModal);
            }
        }
    });
});

// Add CSS for slide out animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);