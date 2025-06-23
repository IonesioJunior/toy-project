// DOM elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');
const clearBtn = document.getElementById('clearBtn');
const uploadBtn = document.getElementById('uploadBtn');
const notifications = document.getElementById('notifications');

// File storage
let selectedFiles = new Map();

// Supported file types and their icons
const fileTypes = {
    'text/plain': { ext: '.txt', icon: '📄' },
    'application/pdf': { ext: '.pdf', icon: '📕' },
    'application/msword': { ext: '.doc', icon: '📘' },
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': { ext: '.docx', icon: '📘' },
    'text/csv': { ext: '.csv', icon: '📊' },
    'application/json': { ext: '.json', icon: '📋' },
    'text/markdown': { ext: '.md', icon: '📝' }
};

// Initialize event listeners
function init() {
    // Drag and drop events
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
    
    // File input change
    fileInput.addEventListener('change', handleFileSelect);
    
    // Button events
    clearBtn.addEventListener('click', clearAllFiles);
    uploadBtn.addEventListener('click', uploadFiles);
    
    // Prevent default drag behavior on document
    document.addEventListener('dragover', (e) => e.preventDefault());
    document.addEventListener('drop', (e) => e.preventDefault());
}

// Handle drag over
function handleDragOver(e) {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
}

// Handle drag leave
function handleDragLeave(e) {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
}

// Handle file drop
function handleDrop(e) {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    
    const files = Array.from(e.dataTransfer.files);
    processFiles(files);
}

// Handle file selection from input
function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    processFiles(files);
}

// Process selected files
function processFiles(files) {
    files.forEach(file => {
        if (isValidFileType(file)) {
            selectedFiles.set(file.name, file);
        } else {
            showNotification(`File type not supported: ${file.name}`, 'error');
        }
    });
    
    updateFileList();
    updateButtonStates();
}

// Check if file type is valid
function isValidFileType(file) {
    const validExtensions = ['.txt', '.pdf', '.doc', '.docx', '.csv', '.json', '.md'];
    const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    return validExtensions.includes(fileExtension);
}

// Update file list display
function updateFileList() {
    fileList.innerHTML = '';
    
    selectedFiles.forEach((file, name) => {
        const fileItem = createFileItem(file);
        fileList.appendChild(fileItem);
    });
}

// Create file item element
function createFileItem(file) {
    const div = document.createElement('div');
    div.className = 'file-item';
    
    const fileIcon = getFileIcon(file);
    
    div.innerHTML = `
        <div class="file-info">
            <span class="file-icon">${fileIcon}</span>
            <div class="file-details">
                <div class="file-name">${file.name}</div>
                <div class="file-size">${formatFileSize(file.size)}</div>
            </div>
        </div>
        <button class="remove-btn" onclick="removeFile('${file.name}')">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M6 18L18 6M6 6l12 12" />
            </svg>
        </button>
    `;
    
    return div;
}

// Get file icon based on type
function getFileIcon(file) {
    const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    const icons = {
        '.txt': '📄',
        '.pdf': '📕',
        '.doc': '📘',
        '.docx': '📘',
        '.csv': '📊',
        '.json': '📋',
        '.md': '📝'
    };
    return icons[fileExtension] || '📎';
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Remove file from list
window.removeFile = function(fileName) {
    selectedFiles.delete(fileName);
    updateFileList();
    updateButtonStates();
};

// Clear all files
function clearAllFiles() {
    selectedFiles.clear();
    fileInput.value = '';
    updateFileList();
    updateButtonStates();
}

// Update button states
function updateButtonStates() {
    const hasFiles = selectedFiles.size > 0;
    clearBtn.disabled = !hasFiles;
    uploadBtn.disabled = !hasFiles;
}

// Upload files to API
async function uploadFiles() {
    if (selectedFiles.size === 0) return;
    
    // Show loading state
    uploadBtn.classList.add('loading');
    uploadBtn.disabled = true;
    clearBtn.disabled = true;
    
    try {
        // Process files and create documents
        const documents = await processFilesForUpload();
        
        // Send to API
        const response = await fetch('/api/v1/documents/batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ documents })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showNotification(
                `Successfully uploaded ${result.successful} of ${result.total} files`,
                result.failed === 0 ? 'success' : 'warning'
            );
            
            // Clear files after successful upload
            if (result.successful > 0) {
                clearAllFiles();
            }
        } else {
            throw new Error(result.detail || 'Upload failed');
        }
    } catch (error) {
        showNotification(`Error: ${error.message}`, 'error');
    } finally {
        // Reset loading state
        uploadBtn.classList.remove('loading');
        updateButtonStates();
    }
}

// Process files for upload
async function processFilesForUpload() {
    const documents = [];
    
    for (const [name, file] of selectedFiles) {
        try {
            const content = await readFileContent(file);
            const timestamp = Date.now();
            const id = `${name.replace(/[^a-zA-Z0-9]/g, '_')}_${timestamp}`;
            
            documents.push({
                id: id,
                content: content,
                metadata: {
                    filename: name,
                    size: file.size,
                    type: file.type || 'unknown',
                    uploaded_at: new Date().toISOString()
                }
            });
        } catch (error) {
            console.error(`Error processing file ${name}:`, error);
            showNotification(`Failed to process ${name}`, 'error');
        }
    }
    
    return documents;
}

// Read file content as text
async function readFileContent(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            resolve(e.target.result);
        };
        
        reader.onerror = (e) => {
            reject(new Error('Failed to read file'));
        };
        
        // For now, read all files as text
        // In a production app, you'd want to handle PDFs and other formats differently
        reader.readAsText(file);
    });
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    notifications.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease forwards';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Add slide out animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOutRight {
        to {
            opacity: 0;
            transform: translateX(100%);
        }
    }
`;
document.head.appendChild(style);

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', init);