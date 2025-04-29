import os
import re
import datetime
import tempfile
from flask import current_app
from werkzeug.utils import secure_filename
import PyPDF2
from docx import Document as DocxDocument
from openpyxl import load_workbook
import magic
import html

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def get_file_type(file_path):
    """Detect file type using python-magic."""
    mime = magic.Magic(mime=True)
    file_type = mime.from_file(file_path)
    return file_type

def save_document(file, owner_id):
    """Save a document to the upload folder and return metadata."""
    filename = secure_filename(file.filename)
    unique_filename = f"{owner_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
    
    # Salva il file nella directory principale di upload
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(file_path)
    
    # Salva anche una copia nella cache di backup per garantire la persistenza
    cache_path = os.path.join(current_app.config['DOCUMENT_CACHE'], unique_filename)
    import shutil
    shutil.copy2(file_path, cache_path)
    
    file_size = os.path.getsize(file_path)
    file_type = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown'
    
    # Registra entrambi i percorsi per maggiore ridondanza
    current_app.logger.info(f"Documento salvato in: {file_path} e {cache_path}")
    
    return {
        'filename': unique_filename,
        'original_filename': filename,
        'file_path': file_path,
        'file_type': file_type,
        'file_size': file_size
    }

def extract_document_metadata(file_path, file_type):
    """Extract metadata from a document file based on its type."""
    metadata = {}
    
    try:
        if file_type == 'pdf':
            with open(file_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                if pdf.metadata:
                    for key, value in pdf.metadata.items():
                        # Clean the key name
                        clean_key = key.replace('/', '_').lower()
                        # Gestione caratteri NULL nei valori dei metadati
                        str_value = str(value)
                        if '\x00' in str_value:
                            str_value = str_value.replace('\x00', ' ').strip()
                        metadata[clean_key] = str_value
                metadata['page_count'] = len(pdf.pages)
                
        elif file_type in ['docx', 'doc']:
            doc = DocxDocument(file_path)
            metadata['page_count'] = len(doc.paragraphs)
            
            # Extract core properties if available
            core_props = getattr(doc, 'core_properties', None)
            if core_props:
                if core_props.author:
                    author = str(core_props.author)
                    if '\x00' in author:
                        author = author.replace('\x00', ' ').strip()
                    metadata['author'] = author
                if core_props.created:
                    created = str(core_props.created)
                    if '\x00' in created:
                        created = created.replace('\x00', ' ').strip()
                    metadata['created'] = created
                if core_props.modified:
                    modified = str(core_props.modified)
                    if '\x00' in modified:
                        modified = modified.replace('\x00', ' ').strip()
                    metadata['modified'] = modified
                if core_props.title:
                    title = str(core_props.title)
                    if '\x00' in title:
                        title = title.replace('\x00', ' ').strip()
                    metadata['title'] = title
                if core_props.subject:
                    subject = str(core_props.subject)
                    if '\x00' in subject:
                        subject = subject.replace('\x00', ' ').strip()
                    metadata['subject'] = subject
            
        elif file_type in ['xlsx', 'xls']:
            wb = load_workbook(file_path, read_only=True)
            metadata['sheet_count'] = len(wb.sheetnames)
            sheet_names = ', '.join(wb.sheetnames)
            if '\x00' in sheet_names:
                sheet_names = sheet_names.replace('\x00', ' ').strip()
            metadata['sheet_names'] = sheet_names
            
            # Extract document properties if available
            props = wb.properties
            if props:
                if props.creator:
                    creator = str(props.creator)
                    if '\x00' in creator:
                        creator = creator.replace('\x00', ' ').strip()
                    metadata['author'] = creator
                if props.created:
                    created = str(props.created)
                    if '\x00' in created:
                        created = created.replace('\x00', ' ').strip()
                    metadata['created'] = created
                if props.modified:
                    modified = str(props.modified)
                    if '\x00' in modified:
                        modified = modified.replace('\x00', ' ').strip()
                    metadata['modified'] = modified
                if props.title:
                    title = str(props.title)
                    if '\x00' in title:
                        title = title.replace('\x00', ' ').strip()
                    metadata['title'] = title
                if props.subject:
                    subject = str(props.subject)
                    if '\x00' in subject:
                        subject = subject.replace('\x00', ' ').strip()
                    metadata['subject'] = subject
        
        # Add general file metadata
        file_stats = os.stat(file_path)
        metadata['file_size_bytes'] = file_stats.st_size
        metadata['file_size_kb'] = round(file_stats.st_size / 1024, 2)
        metadata['file_size_mb'] = round(file_stats.st_size / (1024 * 1024), 2)
        metadata['created_date'] = datetime.datetime.fromtimestamp(file_stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
        metadata['modified_date'] = datetime.datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        
    except Exception as e:
        current_app.logger.error(f"Error extracting metadata: {str(e)}")
        metadata['error'] = f"Metadata extraction failed: {str(e)}"
    
    return metadata

def get_document_preview(document):
    """Generate HTML preview content for a document."""
    file_path = document.file_path
    file_type = document.file_type
    preview_html = ""
    
    # Verifica che il file esista e controlla path alternativi
    if not os.path.exists(file_path):
        from flask import current_app
        # Prova a ricostruire il percorso file in diversi modi
        alternatives = [
            os.path.join(current_app.config['UPLOAD_FOLDER'], document.filename),
            os.path.join('uploads', document.filename),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads', document.filename),
            os.path.join(current_app.config['DOCUMENT_CACHE'], document.filename),
            os.path.join('document_cache', document.filename),
            os.path.join('attached_assets', document.filename),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'attached_assets', document.filename),
            # Cerca in tutte le directory principali
            os.path.join(os.getcwd(), document.filename),
            os.path.join('/home/runner/workspace', document.filename)
        ]
        
        # Cerca anche in document_cache con solo il nome del file (senza percorso)
        base_filename = os.path.basename(document.filename)
        alternatives.extend([
            os.path.join(current_app.config['UPLOAD_FOLDER'], base_filename),
            os.path.join(current_app.config['DOCUMENT_CACHE'], base_filename),
            os.path.join('attached_assets', base_filename)
        ])
        
        file_found = False
        for alternative_path in alternatives:
            if os.path.exists(alternative_path):
                # Se trovato, aggiorna il percorso nel db
                from app import db
                document.file_path = alternative_path
                db.session.commit()
                current_app.logger.info(f"Percorso file aggiornato per documento ID: {document.id}")
                file_path = alternative_path
                file_found = True
                break
        
        # Se il file non è stato trovato ma esiste nella cache di backup, ripristinalo
        if not file_found and os.path.exists(os.path.join(current_app.config['DOCUMENT_CACHE'], document.filename)):
            backup_path = os.path.join(current_app.config['DOCUMENT_CACHE'], document.filename)
            target_path = os.path.join(current_app.config['UPLOAD_FOLDER'], document.filename)
            
            # Assicurati che la directory di destinazione esista
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Copia il file dalla cache al percorso principale
            import shutil
            try:
                shutil.copy2(backup_path, target_path)
                current_app.logger.info(f"File ripristinato dalla cache per documento ID: {document.id}")
                document.file_path = target_path
                from app import db
                db.session.commit()
                file_path = target_path
                file_found = True
            except Exception as e:
                current_app.logger.error(f"Errore durante il ripristino del file dalla cache: {str(e)}")
        
        if not file_found:
            current_app.logger.error(f"File non trovato: {file_path} o alternative: {alternatives}")
            return f"""
            <div class="alert alert-danger">
                <h4>File non trovato</h4>
                <p>Il file non è stato trovato nel sistema. Contattare l'amministratore.</p>
                <p>ID documento: {document.id}, Filename: {document.filename}</p>
                <p>Percorso registrato: {document.file_path}</p>
            </div>
            """
    
    try:
        if file_type == 'pdf':
            preview_html = f"""
            <div class="pdf-viewer">
                <iframe src="data:application/pdf;base64,{get_base64_content(file_path)}" 
                    width="100%" height="600px" style="border: none;"></iframe>
            </div>
            """
        
        elif file_type in ['docx', 'doc']:
            # For Word documents, extract text and format as HTML
            doc = DocxDocument(file_path)
            content = []
            for para in doc.paragraphs:
                if para.text:
                    content.append(f"<p>{html.escape(para.text)}</p>")
            preview_html = f"<div class='document-preview'>{' '.join(content)}</div>"
        
        elif file_type in ['xlsx', 'xls']:
            # For Excel, display first sheet as table
            wb = load_workbook(file_path, read_only=True)
            sheet = wb.active
            content = ["<table class='table table-bordered table-striped'>"]
            
            # Limit to first 100 rows for performance
            max_rows = min(100, sheet.max_row)
            max_cols = min(10, sheet.max_column)
            
            for i, row in enumerate(sheet.iter_rows(max_row=max_rows, max_col=max_cols)):
                if i == 0:
                    content.append("<thead><tr>")
                    for cell in row:
                        content.append(f"<th>{html.escape(str(cell.value or ''))}</th>")
                    content.append("</tr></thead><tbody>")
                else:
                    content.append("<tr>")
                    for cell in row:
                        content.append(f"<td>{html.escape(str(cell.value or ''))}</td>")
                    content.append("</tr>")
            
            content.append("</tbody></table>")
            preview_html = ''.join(content)
        
        elif file_type in ['txt']:
            # For text files, just display the content
            with open(file_path, 'r', errors='ignore') as f:
                text_content = f.read(10000)  # Limit to first 10K chars
                preview_html = f"<pre>{html.escape(text_content)}</pre>"
        
        elif file_type in ['jpg', 'jpeg', 'png', 'gif']:
            # For images, use img tag with base64 encoding
            preview_html = f"""
            <div class="image-preview text-center">
                <img src="data:image/{file_type};base64,{get_base64_content(file_path)}" 
                    class="img-fluid" style="max-height: 600px;" alt="{document.original_filename}">
            </div>
            """
        
        else:
            preview_html = f"""
            <div class="alert alert-info">
                <h4>Anteprima non disponibile</h4>
                <p>Il tipo di file '{file_type}' non può essere visualizzato in anteprima. Scarica il file per visualizzarne il contenuto.</p>
            </div>
            """
    
    except Exception as e:
        current_app.logger.error(f"Error generating preview: {str(e)}")
        preview_html = f"""
        <div class="alert alert-danger">
            <h4>Errore anteprima</h4>
            <p>Si è verificato un errore durante la generazione dell'anteprima: {str(e)}</p>
        </div>
        """
    
    return preview_html

def get_base64_content(file_path):
    """Convert file content to base64 string."""
    import base64
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def sanitize_filename(filename):
    """Remove dangerous characters from a filename."""
    return re.sub(r'[^\w\.-]', '_', filename)
