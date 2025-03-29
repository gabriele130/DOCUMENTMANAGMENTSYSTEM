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
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(file_path)
    
    file_size = os.path.getsize(file_path)
    file_type = filename.rsplit('.', 1)[1].lower()
    
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
                        metadata[clean_key] = str(value)
                metadata['page_count'] = len(pdf.pages)
                
        elif file_type in ['docx', 'doc']:
            doc = DocxDocument(file_path)
            metadata['page_count'] = len(doc.paragraphs)
            
            # Extract core properties if available
            core_props = getattr(doc, 'core_properties', None)
            if core_props:
                if core_props.author:
                    metadata['author'] = core_props.author
                if core_props.created:
                    metadata['created'] = str(core_props.created)
                if core_props.modified:
                    metadata['modified'] = str(core_props.modified)
                if core_props.title:
                    metadata['title'] = core_props.title
                if core_props.subject:
                    metadata['subject'] = core_props.subject
            
        elif file_type in ['xlsx', 'xls']:
            wb = load_workbook(file_path, read_only=True)
            metadata['sheet_count'] = len(wb.sheetnames)
            metadata['sheet_names'] = ', '.join(wb.sheetnames)
            
            # Extract document properties if available
            props = wb.properties
            if props:
                if props.creator:
                    metadata['author'] = props.creator
                if props.created:
                    metadata['created'] = str(props.created)
                if props.modified:
                    metadata['modified'] = str(props.modified)
                if props.title:
                    metadata['title'] = props.title
                if props.subject:
                    metadata['subject'] = props.subject
        
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
                <h4>Preview not available</h4>
                <p>File type '{file_type}' cannot be previewed. Please download the file to view its contents.</p>
            </div>
            """
    
    except Exception as e:
        current_app.logger.error(f"Error generating preview: {str(e)}")
        preview_html = f"""
        <div class="alert alert-danger">
            <h4>Preview Error</h4>
            <p>An error occurred while generating the preview: {str(e)}</p>
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
