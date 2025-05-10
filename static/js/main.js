/**
 * Main JavaScript file for Document Management System
 */

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initApp();
    setupEventListeners();
    // Attiva il contatore delle notifiche
    updateNotificationCount();
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
 * Initialize theme - sempre modalità chiara
 */
function initTheme() {
    const htmlRoot = document.getElementById('htmlRoot');
    const themeLink = document.getElementById('themeLink');
    const navbar = document.querySelector('.navbar');
    const sidebar = document.querySelector('.sidebar');
    
    // Set light theme sempre
    if (htmlRoot) {
        htmlRoot.setAttribute('data-bs-theme', 'light');
    }
    
    if (themeLink) {
        themeLink.href = 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css';
    }
    
    // Correzione per elementi navbar in tema chiaro
    if (navbar) {
        navbar.classList.remove('navbar-dark', 'bg-dark');
        navbar.classList.add('navbar-light', 'bg-light');
    }
    
    // Correzione per i colori del sidebar in tema chiaro
    if (sidebar) {
        sidebar.classList.add('sidebar-light');
    }
    
    // Salva il tema chiaro come predefinito
    localStorage.setItem('theme', 'light');
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
    
    // Setup notification refresh ogni minuto
    setInterval(updateNotificationCount, 60000); // Update every minute
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
        
        // Correzione per elementi navbar in tema chiaro
        const navbar = document.querySelector('.navbar');
        if (navbar) {
            navbar.classList.remove('navbar-dark', 'bg-dark');
            navbar.classList.add('navbar-light', 'bg-light');
        }
        
        // Correzione per i colori del sidebar in tema chiaro
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            sidebar.classList.add('sidebar-light');
        }
    } else {
        // Switch to dark theme
        htmlRoot.setAttribute('data-bs-theme', 'dark');
        lightIcon.classList.remove('d-none');
        darkIcon.classList.add('d-none');
        themeLink.href = 'https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css';
        localStorage.setItem('theme', 'dark');
        
        // Ripristina navbar dark
        const navbar = document.querySelector('.navbar');
        if (navbar) {
            navbar.classList.remove('navbar-light', 'bg-light');
            navbar.classList.add('navbar-dark', 'bg-dark');
        }
        
        // Ripristina sidebar in tema scuro
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            sidebar.classList.remove('sidebar-light');
        }
    }
}

/**
 * Toggle sidebar visibility on mobile
 */
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.overlay');
    
    if (sidebar) {
        sidebar.classList.toggle('active');
    }
    
    if (overlay) {
        overlay.classList.toggle('active');
    }
    
    // Log per debugging
    console.log('Sidebar toggle clicked', { 
        sidebar: sidebar ? 'found' : 'not found', 
        overlay: overlay ? 'found' : 'not found',
        sidebarClass: sidebar ? sidebar.className : 'N/A'
    });
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
 * Update the notification count in the navbar and load notifications in dropdown
 */
function updateNotificationCount() {
    // Controllo se l'utente è autenticato - cerca elementi che esistono solo se autenticati
    const sidebar = document.querySelector('.sidebar');
    const notificationBadge = document.getElementById('notificationBadge');
    const notificationList = document.querySelector('.notification-list');
    
    // Se questi elementi non esistono, probabilmente l'utente non è autenticato
    if (!sidebar || !notificationBadge) {
        return; // Esci dalla funzione
    }
    
    fetch('/api/notifications/count')
        .then(response => {
            if (!response.ok) {
                // Se la risposta non è OK (es. 302 redirect a login)
                throw new Error(`Risposta non valida: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.count > 0) {
                notificationBadge.textContent = data.count;
                notificationBadge.classList.remove('d-none');
                
                // Carica le notifiche solo se ci sono notifiche non lette
                fetchNotifications(notificationList);
            } else {
                notificationBadge.classList.add('d-none');
                
                // Se non ci sono notifiche non lette, mostra messaggio predefinito
                if (notificationList) {
                    notificationList.innerHTML = `
                        <div class="p-3 text-center text-muted">
                            <i class="bi bi-check2-circle"></i>
                            <p class="mb-0 small">Nessuna nuova notifica</p>
                        </div>
                    `;
                }
            }
        })
        .catch(error => {
            console.log('Errore nel recupero delle notifiche:', error.message);
            // Nascondi badge se c'è un errore
            if (notificationBadge) {
                notificationBadge.classList.add('d-none');
            }
            
            // Mostra messaggio di errore nel container delle notifiche
            if (notificationList) {
                notificationList.innerHTML = `
                    <div class="p-3 text-center text-danger">
                        <i class="bi bi-exclamation-triangle"></i>
                        <p class="mb-0 small">Impossibile caricare le notifiche</p>
                    </div>
                `;
            }
        });
}

/**
 * Fetch and display notifications in dropdown
 */
function fetchNotifications(container) {
    if (!container) return;
    
    // Fetch recent unread notifications (max 5)
    fetch('/api/notifications/recent')
        .then(response => response.json())
        .then(data => {
            if (data.notifications && data.notifications.length > 0) {
                let html = '';
                
                data.notifications.forEach(notification => {
                    const date = new Date(notification.created_at);
                    const formattedDate = date.toLocaleDateString('it-IT', {
                        day: '2-digit', 
                        month: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit'
                    });
                    
                    html += `
                        <div class="notification-item p-2 border-bottom" data-id="${notification.id}">
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="notification-dot me-2">
                                    <i class="bi bi-circle-fill text-danger" style="font-size: 0.5rem;"></i>
                                </span>
                                <div class="notification-content flex-grow-1">
                                    <p class="mb-1 small">${notification.message}</p>
                                    <small class="text-muted">${formattedDate}</small>
                                </div>
                                <button class="btn btn-sm mark-read-btn" data-id="${notification.id}" 
                                    onclick="markNotificationRead(${notification.id}, event)">
                                    <i class="bi bi-check"></i>
                                </button>
                            </div>
                        </div>
                    `;
                });
                
                container.innerHTML = html;
                
                // Add event listener for clicking on notification to mark as read
                document.querySelectorAll('.notification-item').forEach(item => {
                    item.addEventListener('click', function() {
                        const id = this.dataset.id;
                        if (id) {
                            markNotificationRead(id);
                        }
                    });
                });
            } else {
                container.innerHTML = `
                    <div class="p-3 text-center text-muted">
                        <i class="bi bi-check2-circle"></i>
                        <p class="mb-0 small">Nessuna nuova notifica</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error fetching notifications:', error);
            container.innerHTML = `
                <div class="p-3 text-center text-danger">
                    <i class="bi bi-exclamation-circle"></i>
                    <p class="mb-0 small">Errore durante il caricamento delle notifiche</p>
                </div>
            `;
        });
}

/**
 * Mark a notification as read
 */
function markNotificationRead(id, event) {
    if (event) {
        event.stopPropagation();
    }
    
    fetch(`/notifications/mark_read/${id}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update UI
            const item = document.querySelector(`.notification-item[data-id="${id}"]`);
            if (item) {
                item.querySelector('.notification-dot i').classList.remove('text-danger');
                item.querySelector('.notification-dot i').classList.add('text-secondary');
                item.querySelector('.mark-read-btn').classList.add('d-none');
            }
            
            // Update notification count
            updateNotificationCount();
        }
    })
    .catch(error => console.error('Error marking notification as read:', error));
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
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annulla</button>
                    <button type="button" class="btn btn-danger" id="confirmButton">Conferma</button>
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
