/**
 * Main JavaScript file for Document Management System
 */

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initApp();
    setupEventListeners();
    // Notification count disabled temporarily
});

/**
 * Initialize the application
 */
function initApp() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Initialize theme preference
    initTheme();
    
    // Set active navigation item based on current page
    setActiveNavItem();
}

/**
 * Initialize theme based on user preference
 */
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const htmlRoot = document.getElementById('htmlRoot');
    const lightIcon = document.getElementById('lightIcon');
    const darkIcon = document.getElementById('darkIcon');
    const themeLink = document.getElementById('themeLink');
    
    if (savedTheme === 'light') {
        // Set light theme
        htmlRoot.setAttribute('data-bs-theme', 'light');
        lightIcon.classList.add('d-none');
        darkIcon.classList.remove('d-none');
        themeLink.href = 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css';
    } else {
        // Set dark theme (default)
        htmlRoot.setAttribute('data-bs-theme', 'dark');
        lightIcon.classList.remove('d-none');
        darkIcon.classList.add('d-none');
        themeLink.href = 'https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css';
    }
}

/**
 * Set up global event listeners
 */
function setupEventListeners() {
    // Toggle sidebar on mobile
    const sidebarToggler = document.getElementById('sidebarToggler');
    if (sidebarToggler) {
        sidebarToggler.addEventListener('click', toggleSidebar);
    }
    
    // Setup document search
    const searchForm = document.getElementById('searchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', handleSearch);
    }
    
    // Setup theme toggle
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', toggleTheme);
    }
    
    // Setup notification refresh - disabled temporarily
    // setInterval(updateNotificationCount, 60000); // Update every minute
}

/**
 * Toggle between light and dark theme
 */
function toggleTheme() {
    const htmlRoot = document.getElementById('htmlRoot');
    const lightIcon = document.getElementById('lightIcon');
    const darkIcon = document.getElementById('darkIcon');
    const themeLink = document.getElementById('themeLink');
    
    if (htmlRoot.getAttribute('data-bs-theme') === 'dark') {
        // Switch to light theme
        htmlRoot.setAttribute('data-bs-theme', 'light');
        lightIcon.classList.add('d-none');
        darkIcon.classList.remove('d-none');
        themeLink.href = 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css';
        localStorage.setItem('theme', 'light');
    } else {
        // Switch to dark theme
        htmlRoot.setAttribute('data-bs-theme', 'dark');
        lightIcon.classList.remove('d-none');
        darkIcon.classList.add('d-none');
        themeLink.href = 'https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css';
        localStorage.setItem('theme', 'dark');
    }
}

/**
 * Toggle sidebar visibility on mobile
 */
function toggleSidebar() {
    document.querySelector('.sidebar').classList.toggle('show');
    document.querySelector('.overlay').classList.toggle('show');
}

/**
 * Set active navigation item based on current URL
 */
function setActiveNavItem() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.sidebar .nav-link');
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        
        const href = link.getAttribute('href');
        if (href === currentPath || 
            (href !== '/' && currentPath.startsWith(href))) {
            link.classList.add('active');
        }
    });
}

/**
 * Handle document search form submission
 */
function handleSearch(event) {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput.value.trim()) {
        event.preventDefault();
    }
}

/**
 * Update the notification count in the navbar
 */
function updateNotificationCount() {
    fetch('/api/notifications/count')
        .then(response => response.json())
        .then(data => {
            const notificationBadge = document.getElementById('notificationBadge');
            if (notificationBadge) {
                if (data.count > 0) {
                    notificationBadge.textContent = data.count;
                    notificationBadge.classList.remove('d-none');
                } else {
                    notificationBadge.classList.add('d-none');
                }
            }
        })
        .catch(error => console.error('Error fetching notification count:', error));
}

/**
 * Format a date string to a readable format
 */
function formatDate(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Format file size in bytes to a human-readable format
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Show a toast notification
 */
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastElement = document.createElement('div');
    toastElement.className = `toast align-items-center text-white bg-${type}`;
    toastElement.setAttribute('role', 'alert');
    toastElement.setAttribute('aria-live', 'assertive');
    toastElement.setAttribute('aria-atomic', 'true');
    
    toastElement.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toastElement);
    
    // Initialize and show toast
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: 5000
    });
    toast.show();
    
    // Remove toast after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

/**
 * Confirm an action with a modal dialog
 */
function confirmAction(title, message, confirmCallback, cancelCallback = null) {
    // Create modal element
    const modalElement = document.createElement('div');
    modalElement.className = 'modal fade';
    modalElement.setAttribute('tabindex', '-1');
    modalElement.setAttribute('aria-hidden', 'true');
    
    modalElement.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">${title}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <p>${message}</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-danger" id="confirmButton">Confirm</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modalElement);
    
    // Initialize modal
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
    
    // Setup event handlers
    const confirmButton = modalElement.querySelector('#confirmButton');
    confirmButton.addEventListener('click', () => {
        modal.hide();
        if (typeof confirmCallback === 'function') {
            confirmCallback();
        }
    });
    
    modalElement.addEventListener('hidden.bs.modal', () => {
        if (modalElement.parentNode) {
            modalElement.parentNode.removeChild(modalElement);
        }
        if (modal._isShown === false && typeof cancelCallback === 'function') {
            cancelCallback();
        }
    });
}

/**
 * Fetch data from an API endpoint
 */
async function fetchAPI(url, options = {}) {
    try {
        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        showToast(`API request failed: ${error.message}`, 'danger');
        throw error;
    }
}
