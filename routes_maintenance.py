import os
import logging
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from models import Document, db, AccessLevel, ActivityLog, User
from services.file_recovery import verify_document_file_exists, recover_missing_file
from services.audit_service import log_activity

maintenance = Blueprint('maintenance', __name__)
logger = logging.getLogger(__name__)

@maintenance.route('/admin/verifica-documenti')
@login_required
def verify_documents():
    """
    Pagina admin per verificare lo stato di tutti i documenti
    """
    if not current_user.is_admin():
        flash('Accesso non autorizzato. Solo gli amministratori possono accedere a questa pagina.', 'danger')
        return redirect(url_for('index'))
        
    return render_template('admin/verify_documents.html')

@maintenance.route('/api/admin/verifica-documenti')
@login_required
def api_verify_documents():
    """
    API per verificare lo stato di tutti i documenti e tentare il recupero automatico
    """
    if not current_user.is_admin():
        return jsonify({'error': 'Accesso non autorizzato'}), 403
    
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
    except ValueError:
        page = 1
        per_page = 50
    
    # Get all documents paginated
    documents = Document.query.paginate(page=page, per_page=per_page, error_out=False)
    
    results = []
    
    for doc in documents.items:
        # Check if file exists and try to recover if missing
        status, file_path = verify_document_file_exists(doc.id)
        
        # Creating result object
        result = {
            'id': doc.id,
            'filename': doc.filename,
            'title': doc.title,
            'original_path': doc.file_path,
            'status': status,
            'current_path': file_path if status != 'not_found' else None
        }
        
        results.append(result)
        
        # Log the check activity
        if status == 'recovered':
            log_activity(
                user_id=current_user.id,
                action='recover_file',
                document_id=doc.id,
                action_category='MAINTENANCE',
                details=f"File recuperato: {file_path}",
                result='success'
            )
    
    return jsonify({
        'results': results,
        'total': documents.total,
        'pages': documents.pages,
        'current_page': page
    })

@maintenance.route('/api/admin/recupera-documento/<int:document_id>')
@login_required
def api_recover_document(document_id):
    """
    API per tentare il recupero manuale di un singolo documento
    """
    if not current_user.is_admin():
        return jsonify({'error': 'Accesso non autorizzato'}), 403
    
    document = Document.query.get(document_id)
    if not document:
        return jsonify({'error': 'Documento non trovato'}), 404
    
    force = request.args.get('force', 'false').lower() == 'true'
    
    # Check if file exists
    file_exists = os.path.exists(document.file_path)
    
    if file_exists and not force:
        return jsonify({
            'status': 'original',
            'message': 'Il file esiste già',
            'path': document.file_path
        })
    
    # Try to recover the file
    success = recover_missing_file(document)
    
    if success:
        log_activity(
            user_id=current_user.id,
            action='recover_file',
            document_id=document.id,
            action_category='MAINTENANCE',
            details=f"File recuperato manualmente: {document.file_path}",
            result='success'
        )
        
        return jsonify({
            'status': 'recovered',
            'message': 'File recuperato con successo',
            'path': document.file_path
        })
    
    return jsonify({
        'status': 'not_found',
        'message': 'Non è stato possibile recuperare il file',
        'path': None
    }), 404

@maintenance.route('/admin/statistiche-documenti')
@login_required
def document_statistics():
    """
    Pagina admin per visualizzare statistiche sui documenti
    """
    if not current_user.is_admin():
        flash('Accesso non autorizzato. Solo gli amministratori possono accedere a questa pagina.', 'danger')
        return redirect(url_for('index'))
    
    # Get total document count
    total_documents = Document.query.count()
    
    # Get count of documents by file type
    file_types = db.session.query(
        Document.file_type, 
        func.count(Document.id).label('count')
    ).group_by(Document.file_type).all()
    
    # Get count of documents by owner
    documents_by_owner = db.session.query(
        User.username,
        func.count(Document.id).label('count')
    ).join(Document, User.id == Document.owner_id).group_by(User.username).all()
    
    # Get average file size
    average_size = db.session.query(func.avg(Document.file_size)).scalar()
    if average_size:
        average_size = round(average_size / (1024 * 1024), 2)  # Convert to MB
    
    # Document count by month
    documents_by_month = db.session.query(
        func.date_format(Document.created_at, '%Y-%m').label('month'),
        func.count(Document.id).label('count')
    ).group_by('month').order_by('month').all()
    
    statistics = {
        'total_documents': total_documents,
        'file_types': file_types,
        'documents_by_owner': documents_by_owner,
        'average_size_mb': average_size or 0,
        'documents_by_month': documents_by_month
    }
    
    return render_template('admin/document_statistics.html', statistics=statistics)