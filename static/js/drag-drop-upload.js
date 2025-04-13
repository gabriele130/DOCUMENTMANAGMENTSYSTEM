document.addEventListener('DOMContentLoaded', function() {
    // Riferimenti agli elementi del DOM
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('document');
    const fileList = document.getElementById('file-list');
    const uploadForm = document.getElementById('uploadForm');
    const uploadBtn = document.getElementById('uploadBtn');
    const progressBar = document.getElementById('upload-progress');
    const progressContainer = document.getElementById('progress-container');
    
    // Se gli elementi non esistono, esci dalla funzione
    if (!dropArea || !fileInput) return;
    
    // Previene il comportamento predefinito (apertura del file come link)
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // Evidenzia l'area di drop quando si trascina un file su di essa
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        dropArea.classList.add('highlight');
    }
    
    function unhighlight() {
        dropArea.classList.remove('highlight');
    }
    
    // Gestisce il file rilasciato
    dropArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }
    
    // Gestisce il file selezionato tramite input file
    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });
    
    function handleFiles(files) {
        if (!files.length) return;
        
        // Aggiorna il fileinput con il file selezionato
        fileInput.files = files;
        
        // Visualizza i file selezionati nell'elenco
        displayFiles(files);
        
        // Compila il titolo del documento se il campo è vuoto
        const titleInput = document.getElementById('title');
        if (titleInput && !titleInput.value && files[0]) {
            const filename = files[0].name;
            const nameWithoutExt = filename.split('.').slice(0, -1).join('.');
            titleInput.value = nameWithoutExt;
        }
    }
    
    function displayFiles(files) {
        if (!fileList) return;
        
        fileList.innerHTML = '';
        
        Array.from(files).forEach(file => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item mb-2 p-2 border rounded';
            
            // Determina l'icona in base al tipo di file
            let fileIcon = 'bi-file-earmark';
            if (file.type.includes('pdf')) {
                fileIcon = 'bi-file-earmark-pdf';
            } else if (file.type.includes('image')) {
                fileIcon = 'bi-file-earmark-image';
            } else if (file.type.includes('word') || file.name.endsWith('.docx') || file.name.endsWith('.doc')) {
                fileIcon = 'bi-file-earmark-word';
            } else if (file.type.includes('excel') || file.name.endsWith('.xlsx') || file.name.endsWith('.xls')) {
                fileIcon = 'bi-file-earmark-excel';
            }
            
            // Dimensione del file in formato leggibile
            const fileSize = file.size < 1024 * 1024 
                ? Math.round(file.size / 1024) + ' KB' 
                : Math.round(file.size / (1024 * 1024) * 10) / 10 + ' MB';
            
            fileItem.innerHTML = `
                <div class="d-flex align-items-center">
                    <i class="bi ${fileIcon} fs-4 me-2"></i>
                    <div>
                        <div class="fw-bold">${file.name}</div>
                        <div class="small text-muted">${file.type || 'Documento'} - ${fileSize}</div>
                    </div>
                    <button type="button" class="btn-close ms-auto remove-file" aria-label="Rimuovi"></button>
                </div>
            `;
            
            fileList.appendChild(fileItem);
            
            // Gestisce la rimozione del file
            const removeBtn = fileItem.querySelector('.remove-file');
            removeBtn.addEventListener('click', function() {
                // Reimposta l'input file
                fileInput.value = '';
                fileList.innerHTML = '';
                
                // Visualizza il messaggio di trascinamento
                if (document.querySelector('.drag-text')) {
                    document.querySelector('.drag-text').style.display = 'block';
                }
            });
        });
        
        // Nascondi il messaggio di trascinamento
        if (document.querySelector('.drag-text')) {
            document.querySelector('.drag-text').style.display = 'none';
        }
    }
    
    // Gestione del form di upload
    if (uploadForm) {
        uploadForm.addEventListener('submit', function() {
            // Verifica che sia stato selezionato un file
            if (fileInput.files.length === 0) {
                alert('Seleziona un file da caricare');
                return false;
            }
            
            // Disabilita il pulsante e mostra lo stato di caricamento
            if (uploadBtn) {
                uploadBtn.disabled = true;
                uploadBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Caricamento...';
            }
            
            // Mostra la barra di avanzamento
            if (progressContainer) {
                progressContainer.classList.remove('d-none');
            }
            
            // Simula l'avanzamento del caricamento
            if (progressBar) {
                let width = 0;
                const interval = setInterval(function() {
                    if (width >= 90) {
                        clearInterval(interval);
                    } else {
                        width += 5;
                        progressBar.style.width = width + '%';
                        progressBar.setAttribute('aria-valuenow', width);
                    }
                }, 200);
            }
            
            return true;
        });
    }
});