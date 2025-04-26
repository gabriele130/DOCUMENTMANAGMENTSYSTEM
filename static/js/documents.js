/**
 * Documents page functionality for Document Management System
 */

document.addEventListener('DOMContentLoaded', () => {
    initDocumentsPage();
});

/**
 * Initialize the documents page
 */
function initDocumentsPage() {
    // Setup document filter functionality
    setupDocumentFilters();
    
    // Setup document action buttons
    setupDocumentActions();
    
    // Initialize tags input if present
    initializeTagsInput();
    
    // Setup document sharing functionality
    setupSharingModal();
}

/**
 * Setup document filtering functionality
 */
function setupDocumentFilters() {
    const filterForm = document.getElementById('documentFilterForm');
    if (!filterForm) return;
    
    // Handle filter form submission
    filterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        applyFilters();
    });
    
    // Handle filter reset
    const resetButton = document.getElementById('resetFilters');
    if (resetButton) {
        resetButton.addEventListener('click', function() {
            filterForm.reset();
            applyFilters();
        });
    }
}

/**
 * Apply document filters
 */
function applyFilters() {
    const tagFilter = document.getElementById('tagFilter');
    const typeFilter = document.getElementById('typeFilter');
    const dateFilter = document.getElementById('dateFilter');
    
    const selectedTags = tagFilter ? Array.from(tagFilter.selectedOptions).map(opt => opt.value) : [];
    const selectedType = typeFilter ? typeFilter.value : '';
    const selectedDate = dateFilter ? dateFilter.value : '';
    
    // Get all document items
    const documentItems = document.querySelectorAll('.document-item');
    
    documentItems.forEach(item => {
        let visible = true;
        
        // Filter by tag
        if (selectedTags.length > 0) {
            const documentTags = item.dataset.tags ? item.dataset.tags.split(',') : [];
            if (!selectedTags.some(tag => documentTags.includes(tag))) {
                visible = false;
            }
        }
        
        // Filter by document type
        if (selectedType && item.dataset.type !== selectedType) {
            visible = false;
        }
        
        // Filter by date (simplified)
        if (selectedDate) {
            const documentDate = item.dataset.date || '';
            if (documentDate < selectedDate) {
                visible = false;
            }
        }
        
        // Show/hide the document based on filters
        item.style.display = visible ? '' : 'none';
    });
    
    // Update UI to show filter status
    updateFilterStatus();
}

/**
 * Update the filter status display
 */
function updateFilterStatus() {
    const documentItems = document.querySelectorAll('.document-item');
    const visibleCount = Array.from(documentItems).filter(item => item.style.display !== 'none').length;
    
    const statusElement = document.getElementById('filterStatus');
    if (statusElement) {
        statusElement.textContent = `Showing ${visibleCount} of ${documentItems.length} documents`;
    }
}

/**
 * Setup document action buttons (view, download, share, etc.)
 */
function setupDocumentActions() {
    // Non ci sono più pulsanti per l'archiviazione
    // La funzionalità è stata sostituita dall'eliminazione permanente
    
    // Setup delete buttons for permanent deletion
    const deleteButtons = document.querySelectorAll('.btn-delete-document');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const documentId = this.dataset.documentId;
            const documentName = this.dataset.documentName || 'questo documento';
            
            confirmAction(
                'Elimina Definitivamente',
                `ATTENZIONE: Stai per eliminare definitivamente "${documentName}". Questa azione non può essere annullata. Sei sicuro di voler procedere?`,
                () => {
                    // Trova il form associato a questo pulsante e invialo
                    const parentForm = this.closest('form');
                    if (parentForm) {
                        parentForm.submit();
                    }
                }
            );
        });
    });
}

/**
 * Initialize tags input field with select2 if available
 */
function initializeTagsInput() {
    const tagsInput = document.querySelector('.tags-select');
    if (tagsInput && typeof $ !== 'undefined' && $.fn.select2) {
        $(tagsInput).select2({
            theme: 'bootstrap4',
            placeholder: 'Select tags',
            allowClear: true,
            tags: true
        });
    }
}

/**
 * Setup document sharing modal
 */
function setupSharingModal() {
    // Handle user search in sharing modal
    const userSearchInput = document.getElementById('userSearch');
    if (userSearchInput) {
        userSearchInput.addEventListener('input', debounce(function() {
            searchUsers(this.value);
        }, 300));
    }
    
    // Handle share form submission
    const shareForm = document.getElementById('shareDocumentForm');
    if (shareForm) {
        shareForm.addEventListener('submit', function(e) {
            const selectedUsers = document.querySelectorAll('input[name="users"]:checked');
            if (selectedUsers.length === 0) {
                e.preventDefault();
                alert('Please select at least one user to share with.');
            }
        });
    }
}

/**
 * Search for users to share with
 */
function searchUsers(query) {
    if (!query || query.length < 2) {
        document.getElementById('userSearchResults').innerHTML = '<p>Enter at least 2 characters to search</p>';
        return;
    }
    
    fetch(`/api/users/search?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(users => {
            const resultsContainer = document.getElementById('userSearchResults');
            
            if (users.length === 0) {
                resultsContainer.innerHTML = '<p>No users found</p>';
                return;
            }
            
            let html = '<div class="list-group">';
            users.forEach(user => {
                const fullName = user.full_name ? ` (${user.full_name})` : '';
                html += `
                    <label class="list-group-item">
                        <input class="form-check-input me-1" type="checkbox" name="users" value="${user.id}">
                        <strong>${user.username}</strong>${fullName} - ${user.email}
                    </label>
                `;
            });
            html += '</div>';
            
            resultsContainer.innerHTML = html;
        })
        .catch(error => {
            console.error('Error searching for users:', error);
            document.getElementById('userSearchResults').innerHTML = 
                '<p class="text-danger">Error searching for users</p>';
        });
}

/**
 * Preview a document in a modal
 */
function previewDocument(documentId) {
    const previewModal = new bootstrap.Modal(document.getElementById('documentPreviewModal'));
    const previewContainer = document.getElementById('documentPreviewContainer');
    
    // Show loading indicator
    previewContainer.innerHTML = '<div class="text-center p-5"><div class="spinner-border" role="status"></div><p class="mt-2">Loading preview...</p></div>';
    
    // Fetch document preview
    fetch(`/api/documents/preview/${documentId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                previewContainer.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            } else {
                previewContainer.innerHTML = data.preview_html;
            }
        })
        .catch(error => {
            console.error('Error loading preview:', error);
            previewContainer.innerHTML = `<div class="alert alert-danger">Error loading preview: ${error.message}</div>`;
        });
    
    previewModal.show();
}

/**
 * Utility function for debouncing inputs
 */
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}
