import os
import json
import uuid
import datetime
from functools import wraps
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from app import app, db, EmptyForm, csrf
from models import (User, Document, DocumentVersion, DocumentMetadata, Tag, 
                    Workflow, WorkflowTask, SearchHistory, Notification,
                    Company, Folder, Permission, Reminder, ActivityLog, AccessLevel)
from services.document_processor import (allowed_file, save_document, 
                                        extract_document_metadata, get_document_preview)
from services.ai_classifier import classify_document, extract_data_from_document
from services.ocr import extract_text_from_document
from services.search import search_documents
from services.workflow import create_workflow, assign_workflow_task, complete_workflow_task

# Helper functions
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You need to be an administrator to access this page.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = 'remember' in request.form
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('register.html')
        
        # Create new user (first user is admin)
        is_first_user = User.query.count() == 0
        user = User(
            username=username, 
            email=email,
            first_name=request.form.get('first_name', ''),
            last_name=request.form.get('last_name', ''),
            role='admin' if is_first_user else 'user'
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Main application routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))
    
# Logging user activity
def log_activity(user_id, document_id=None, action=None, details=None, ip_address=None):
    """Log user activity"""
    if not action:
        return
        
    activity = ActivityLog(
        user_id=user_id,
        document_id=document_id,
        action=action,
        details=details,
        ip_address=ip_address or request.remote_addr
    )
    db.session.add(activity)
    db.session.commit()
    return activity

def get_document_preview(document):
    """Generate HTML preview for document"""
    preview_html = f"""
    <div class="document-preview">
        <div class="document-preview-header mb-4">
            <div class="d-flex align-items-center mb-3">
                <div class="document-icon me-3 
                    {'bg-danger bg-opacity-10 text-danger' if document.file_type == 'pdf' else
                    'bg-primary bg-opacity-10 text-primary' if document.file_type in ['docx', 'doc'] else
                    'bg-success bg-opacity-10 text-success' if document.file_type in ['xlsx', 'xls'] else
                    'bg-info bg-opacity-10 text-info' if document.file_type in ['jpg', 'jpeg', 'png', 'gif'] else
                    'bg-secondary bg-opacity-10 text-secondary'}">
                    <i class="bi 
                        {'bi-file-earmark-pdf' if document.file_type == 'pdf' else
                        'bi-file-earmark-word' if document.file_type in ['docx', 'doc'] else
                        'bi-file-earmark-excel' if document.file_type in ['xlsx', 'xls'] else
                        'bi-file-earmark-image' if document.file_type in ['jpg', 'jpeg', 'png', 'gif'] else
                        'bi-file-earmark'}"></i>
                </div>
                <div>
                    <h4 class="mb-1">{document.title or document.original_filename}</h4>
                    <p class="text-muted mb-0">
                        <span class="badge bg-secondary">{document.classification or 'Unclassified'}</span>
                        <small class="ms-2">{document.file_type.upper()} - {int(document.file_size / 1024)} KB</small>
                    </p>
                </div>
            </div>
        </div>
        
        <div class="document-preview-details mb-4">
            <h5 class="mb-3">Dettagli Documento</h5>
            <div class="row">
                <div class="col-md-6">
                    <p><strong>Nome File:</strong> {document.original_filename}</p>
                    <p><strong>Caricato il:</strong> {document.created_at.strftime('%d/%m/%Y %H:%M')}</p>
                    <p><strong>Caricato da:</strong> {document.owner.username}</p>
                </div>
                <div class="col-md-6">
                    <p><strong>Ultima Modifica:</strong> {document.updated_at.strftime('%d/%m/%Y %H:%M')}</p>
                    {'<p><strong>Scadenza:</strong> ' + document.expiry_date.strftime('%d/%m/%Y') + '</p>' if document.expiry_date else ''}
                    <p><strong>Versioni:</strong> {len(document.versions) + 1}</p>
                </div>
            </div>
        </div>
        
        <div class="document-preview-content mb-4">
            <h5 class="mb-3">Descrizione</h5>
            <div class="card card-body bg-light">
                {f'<p class="mb-0">{document.description}</p>' if document.description else '<p class="text-muted mb-0">Nessuna descrizione disponibile</p>'}
            </div>
        </div>
        
        <div class="document-preview-tags mb-4">
            <h5 class="mb-3">Tags</h5>
            <div>
                {''.join([f'<span class="document-tag" style="background-color: {tag.color}20; color: {tag.color};">{tag.name}</span>' for tag in document.tags]) if document.tags else '<span class="text-muted">Nessun tag assegnato</span>'}
            </div>
        </div>
        
        <div class="document-preview-actions text-center mt-4">
            <a href="{url_for('view_document', document_id=document.id)}" class="btn btn-primary">
                <i class="bi bi-eye"></i> Visualizza Completa
            </a>
            <a href="{url_for('download_document', document_id=document.id)}" class="btn btn-secondary ms-2">
                <i class="bi bi-download"></i> Scarica
            </a>
        </div>
    </div>
    """
    return preview_html

@app.route('/dashboard')
@login_required
def dashboard():
    # Get basic stats for the dashboard
    recent_documents = Document.query.filter_by(owner_id=current_user.id).order_by(Document.created_at.desc()).limit(5).all()
    document_count = Document.query.filter_by(owner_id=current_user.id).count()
    
    # Get pending workflow tasks
    tasks = WorkflowTask.query.filter_by(assigned_to_id=current_user.id, status='pending').order_by(WorkflowTask.due_date).all()
    
    # Get documents that will expire in the next 30 days
    thirty_days_from_now = datetime.datetime.now().date() + datetime.timedelta(days=30)
    expiring_documents = Document.query.filter(
        Document.owner_id == current_user.id,
        Document.expiry_date.is_not(None),
        Document.expiry_date <= thirty_days_from_now,
        Document.expiry_date >= datetime.datetime.now().date()
    ).order_by(Document.expiry_date).all()
    
    # Add current datetime for expiry calculations
    now = datetime.datetime.now()
    
    return render_template('dashboard.html', 
                          recent_documents=recent_documents,
                          document_count=document_count,
                          tasks=tasks,
                          expiring_documents=expiring_documents,
                          now=now)

# Document routes
@app.route('/documents')
@login_required
def documents():
    # Get all documents owned by the user or shared with them
    owned_documents = Document.query.filter_by(owner_id=current_user.id, is_archived=False).all()
    shared_documents = current_user.shared_documents
    
    # Get all tags for filtering
    all_tags = Tag.query.all()
    
    return render_template('documents.html', 
                          owned_documents=owned_documents,
                          shared_documents=shared_documents,
                          tags=all_tags)

@app.route('/documents/upload', methods=['GET', 'POST'])
@login_required
def upload_document():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'document' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['document']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Save the uploaded file
            filename = secure_filename(file.filename)
            unique_filename = f"{str(uuid.uuid4())}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Extract basic metadata
            file_type = filename.rsplit('.', 1)[1].lower()
            file_size = os.path.getsize(file_path)
            
            # Create new document record
            document = Document(
                filename=unique_filename,
                original_filename=filename,
                file_path=file_path,
                file_type=file_type,
                file_size=file_size,
                title=request.form.get('title', filename),
                description=request.form.get('description', ''),
                owner_id=current_user.id
            )
            
            # Add tags if provided
            tag_ids = request.form.getlist('tags')
            if tag_ids:
                tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
                document.tags.extend(tags)
            
            # Set expiry date if provided
            expiry_date = request.form.get('expiry_date')
            if expiry_date:
                document.expiry_date = datetime.datetime.strptime(expiry_date, '%Y-%m-%d').date()
            
            db.session.add(document)
            db.session.commit()
            
            # Create reminder if requested
            if 'create_reminder' in request.form:
                # Determine the reminder date (use expiry date if reminder date is not provided)
                reminder_date = request.form.get('reminder_date')
                if not reminder_date and expiry_date:
                    reminder_date = expiry_date
                
                if reminder_date:
                    reminder_date = datetime.datetime.strptime(reminder_date, '%Y-%m-%d')
                    
                    # Calculate notification days before
                    notify_days = int(request.form.get('notify_days', 7))
                    notify_unit = request.form.get('notify_unit', 'days')
                    
                    notify_days_before = notify_days
                    if notify_unit == 'weeks':
                        notify_days_before = notify_days * 7
                    elif notify_unit == 'months':
                        notify_days_before = notify_days * 30
                    
                    # Use document title as default reminder title if not provided
                    reminder_title = request.form.get('reminder_title')
                    if not reminder_title:
                        reminder_title = f"Scadenza: {document.title}"
                    
                    # Create the reminder
                    reminder = Reminder(
                        document_id=document.id,
                        title=reminder_title,
                        description=f"Promemoria creato automaticamente per il documento: {document.title}",
                        reminder_type=request.form.get('reminder_type', 'deadline'),
                        due_date=reminder_date,
                        frequency='once',
                        notify_days_before=notify_days_before,
                        notify_users=json.dumps([current_user.id]),
                        created_by_id=current_user.id
                    )
                    
                    db.session.add(reminder)
                    db.session.commit()
                    
                    # Log the reminder creation
                    log_activity(
                        user_id=current_user.id,
                        document_id=document.id,
                        action="create_reminder",
                        details=json.dumps({
                            "reminder_id": reminder.id,
                            "title": reminder_title,
                            "due_date": reminder_date.strftime('%Y-%m-%d'),
                            "reminder_type": reminder.reminder_type
                        })
                    )
                    
                    flash('Documento caricato e promemoria creato con successo!', 'success')
            
            # Process the document asynchronously (in a real app, this would be a background task)
            try:
                # Extract text with OCR if applicable
                document.content_text = extract_text_from_document(file_path, file_type)
                
                # Classify the document using AI
                document.classification = classify_document(document.content_text or '', file_type)
                
                # Extract metadata from document
                metadata_dict = extract_document_metadata(file_path, file_type)
                for key, value in metadata_dict.items():
                    metadata = DocumentMetadata(
                        document_id=document.id,
                        key=key,
                        value=str(value)
                    )
                    db.session.add(metadata)
                
                db.session.commit()
                if 'create_reminder' not in request.form:
                    flash('Documento caricato ed elaborato con successo!', 'success')
            except Exception as e:
                app.logger.error(f"Error processing document: {str(e)}")
                flash(f'Document uploaded but processing failed: {str(e)}', 'warning')
            
            return redirect(url_for('view_document', document_id=document.id))
        else:
            flash('File type not allowed', 'danger')
            return redirect(request.url)
    
    # Get all tags for the upload form
    tags = Tag.query.all()
    return render_template('upload_document.html', tags=tags, form=EmptyForm())

@app.route('/documents/<int:document_id>')
@login_required
def view_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Check if user has permission to view this document
    if document.owner_id != current_user.id and current_user not in document.shared_with:
        flash('You do not have permission to view this document.', 'danger')
        return redirect(url_for('documents'))
    
    # Get document preview if available
    preview_html = get_document_preview(document)
    
    # Get document versions
    versions = DocumentVersion.query.filter_by(document_id=document.id).order_by(DocumentVersion.version_number.desc()).all()
    
    # Get workflow information if assigned
    workflow_tasks = []
    if document.workflow_id:
        workflow_tasks = WorkflowTask.query.filter_by(workflow_id=document.workflow_id).order_by(WorkflowTask.order).all()
    
    return render_template('view_document.html', 
                          document=document,
                          preview_html=preview_html,
                          versions=versions,
                          workflow_tasks=workflow_tasks)

@app.route('/documents/<int:document_id>/download')
@login_required
def download_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Check if user has permission to download this document
    if document.owner_id != current_user.id and current_user not in document.shared_with:
        flash('You do not have permission to download this document.', 'danger')
        return redirect(url_for('documents'))
    
    return send_file(document.file_path, 
                    download_name=document.original_filename,
                    as_attachment=True)

@app.route('/documents/<int:document_id>/update', methods=['GET', 'POST'])
@login_required
def update_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Check if user has permission to update this document
    if document.owner_id != current_user.id:
        flash('You do not have permission to update this document.', 'danger')
        return redirect(url_for('documents'))
    
    if request.method == 'POST':
        # Update document metadata
        document.title = request.form.get('title', document.title)
        document.description = request.form.get('description', document.description)
        
        # Update tags
        document.tags.clear()
        tag_ids = request.form.getlist('tags')
        if tag_ids:
            tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
            document.tags.extend(tags)
        
        # Update expiry date if provided
        expiry_date = request.form.get('expiry_date')
        if expiry_date:
            document.expiry_date = datetime.datetime.strptime(expiry_date, '%Y-%m-%d').date()
        else:
            document.expiry_date = None
        
        # Handle new version upload if file is provided
        if 'document' in request.files and request.files['document'].filename:
            file = request.files['document']
            if allowed_file(file.filename):
                # Save the new version
                filename = secure_filename(file.filename)
                unique_filename = f"{str(uuid.uuid4())}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                
                # Get latest version number
                latest_version = DocumentVersion.query.filter_by(document_id=document.id).order_by(DocumentVersion.version_number.desc()).first()
                version_number = 1 if not latest_version else latest_version.version_number + 1
                
                # Create new version record
                version = DocumentVersion(
                    document_id=document.id,
                    filename=unique_filename,
                    file_path=file_path,
                    version_number=version_number,
                    created_by_id=current_user.id,
                    change_summary=request.form.get('change_summary', '')
                )
                db.session.add(version)
                
                # Update the main document record
                document.filename = unique_filename
                document.file_path = file_path
                document.file_type = filename.rsplit('.', 1)[1].lower()
                document.file_size = os.path.getsize(file_path)
                
                # Process the new version (in a real app, this would be a background task)
                try:
                    # Extract text with OCR if applicable
                    document.content_text = extract_text_from_document(file_path, document.file_type)
                    
                    # Classify the document using AI
                    document.classification = classify_document(document.content_text or '', document.file_type)
                    
                    # Extract and update metadata
                    metadata_dict = extract_document_metadata(file_path, document.file_type)
                    
                    # First, remove existing metadata
                    DocumentMetadata.query.filter_by(document_id=document.id).delete()
                    
                    # Add new metadata
                    for key, value in metadata_dict.items():
                        metadata = DocumentMetadata(
                            document_id=document.id,
                            key=key,
                            value=str(value)
                        )
                        db.session.add(metadata)
                except Exception as e:
                    app.logger.error(f"Error processing document update: {str(e)}")
                    flash(f'Document updated but processing failed: {str(e)}', 'warning')
        
        document.updated_at = datetime.datetime.utcnow()
        db.session.commit()
        flash('Document updated successfully!', 'success')
        return redirect(url_for('view_document', document_id=document.id))
    
    # Get all tags for the form
    all_tags = Tag.query.all()
    
    # Format the expiry date for the form
    expiry_date = None
    if document.expiry_date:
        expiry_date = document.expiry_date.strftime('%Y-%m-%d')
    
    return render_template('update_document.html', 
                          document=document,
                          tags=all_tags,
                          expiry_date=expiry_date)

@app.route('/documents/<int:document_id>/share', methods=['POST'])
@login_required
def share_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Check if user has permission to share this document
    if document.owner_id != current_user.id:
        flash('You do not have permission to share this document.', 'danger')
        return redirect(url_for('documents'))
    
    # Get users to share with
    user_ids = request.form.getlist('users')
    if not user_ids:
        flash('No users selected for sharing', 'warning')
        return redirect(url_for('view_document', document_id=document.id))
    
    # Add users to shared list
    users = User.query.filter(User.id.in_(user_ids)).all()
    for user in users:
        if user not in document.shared_with:
            document.shared_with.append(user)
            
            # Create notification for the user
            notification = Notification(
                user_id=user.id,
                message=f"{current_user.username} shared the document '{document.title or document.original_filename}' with you."
            )
            db.session.add(notification)
    
    db.session.commit()
    flash('Document shared successfully!', 'success')
    return redirect(url_for('view_document', document_id=document.id))

@app.route('/documents/<int:document_id>/unshare/<int:user_id>', methods=['POST'])
@login_required
def unshare_document(document_id, user_id):
    document = Document.query.get_or_404(document_id)
    user = User.query.get_or_404(user_id)
    
    # Check if current user is the owner
    if document.owner_id != current_user.id:
        flash('You do not have permission to unshare this document.', 'danger')
        return redirect(url_for('documents'))
    
    # Remove user from shared list
    if user in document.shared_with:
        document.shared_with.remove(user)
        db.session.commit()
        flash(f'Document no longer shared with {user.username}', 'success')
    
    return redirect(url_for('view_document', document_id=document.id))

@app.route('/documents/<int:document_id>/archive', methods=['POST'])
@login_required
def archive_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Check if user has permission to archive this document
    if document.owner_id != current_user.id:
        flash('You do not have permission to archive this document.', 'danger')
        return redirect(url_for('documents'))
    
    document.is_archived = True
    db.session.commit()
    flash('Document archived', 'success')
    return redirect(url_for('documents'))

@app.route('/documents/archived')
@login_required
def archived_documents():
    # Get all archived documents owned by the user
    documents = Document.query.filter_by(owner_id=current_user.id, is_archived=True).all()
    return render_template('archived_documents.html', documents=documents)

@app.route('/documents/<int:document_id>/unarchive', methods=['POST'])
@login_required
def unarchive_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Check if user has permission to unarchive this document
    if document.owner_id != current_user.id:
        flash('You do not have permission to unarchive this document.', 'danger')
        return redirect(url_for('archived_documents'))
    
    document.is_archived = False
    db.session.commit()
    flash('Document unarchived', 'success')
    return redirect(url_for('archived_documents'))

# Search routes
@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    if not query:
        return render_template('search.html', results=[], query='')
    
    # Get filter parameters
    doc_type = request.args.get('doc_type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    tags = request.args.getlist('tags')
    
    # Convert date strings to datetime objects if provided
    from_date = None
    to_date = None
    
    if date_from:
        try:
            from_date = datetime.datetime.strptime(date_from, '%Y-%m-%d')
        except ValueError:
            flash('Invalid from date format', 'warning')
    
    if date_to:
        try:
            to_date = datetime.datetime.strptime(date_to, '%Y-%m-%d')
        except ValueError:
            flash('Invalid to date format', 'warning')
    
    # Search for documents
    results = search_documents(
        query=query,
        user_id=current_user.id,
        doc_type=doc_type,
        from_date=from_date,
        to_date=to_date,
        tags=tags
    )
    
    # Save search history
    filters = {
        'doc_type': doc_type,
        'date_from': date_from,
        'date_to': date_to,
        'tags': tags
    }
    search_history = SearchHistory(
        user_id=current_user.id,
        query=query,
        filters=json.dumps(filters)
    )
    db.session.add(search_history)
    db.session.commit()
    
    # Get all document types and tags for filter options
    all_types = db.session.query(Document.classification).distinct().all()
    all_tags = Tag.query.all()
    
    return render_template('search.html', 
                          results=results, 
                          query=query,
                          doc_type=doc_type,
                          date_from=date_from,
                          date_to=date_to,
                          selected_tags=tags,
                          all_types=all_types,
                          all_tags=all_tags)

# Workflow routes
@app.route('/workflow')
@login_required
def workflow():
    # Get workflows created by the user
    created_workflows = Workflow.query.filter_by(created_by_id=current_user.id).all()
    
    # Get tasks assigned to the user
    assigned_tasks = WorkflowTask.query.filter_by(assigned_to_id=current_user.id).order_by(WorkflowTask.due_date).all()
    
    return render_template('workflow.html', 
                          created_workflows=created_workflows,
                          assigned_tasks=assigned_tasks)

@app.route('/workflow/create', methods=['GET', 'POST'])
@login_required
def create_workflow_route():
    if request.method == 'POST':
        # Extract workflow data from form
        workflow_name = request.form.get('workflow_name')
        workflow_description = request.form.get('workflow_description')
        document_id = request.form.get('document_id')
        
        # Extract task data from form - assumes form has numbered fields for tasks
        tasks = []
        i = 1
        while f'task_name_{i}' in request.form:
            task = {
                'name': request.form.get(f'task_name_{i}'),
                'description': request.form.get(f'task_description_{i}', ''),
                'assigned_to_id': request.form.get(f'task_assigned_to_{i}'),
                'order': i,
                'due_date': request.form.get(f'task_due_date_{i}')
            }
            tasks.append(task)
            i += 1
        
        if not tasks:
            flash('At least one task is required for a workflow', 'danger')
            return redirect(request.url)
        
        try:
            # Create workflow 
            workflow = create_workflow(
                name=workflow_name,
                description=workflow_description, 
                created_by_id=current_user.id,
                document_id=document_id,
                tasks=tasks
            )
            
            flash('Workflow created successfully!', 'success')
            return redirect(url_for('workflow_detail', workflow_id=workflow.id))
        except Exception as e:
            flash(f'Error creating workflow: {str(e)}', 'danger')
            return redirect(request.url)
    
    # Get documents owned by the user for the form
    documents = Document.query.filter_by(owner_id=current_user.id, is_archived=False).all()
    
    # Get all users for task assignment
    users = User.query.all()
    
    return render_template('create_workflow.html', 
                          documents=documents,
                          users=users)

@app.route('/workflow/<int:workflow_id>')
@login_required
def workflow_detail(workflow_id):
    workflow = Workflow.query.get_or_404(workflow_id)
    
    # Check if user has permission to view this workflow
    if workflow.created_by_id != current_user.id and not any(task.assigned_to_id == current_user.id for task in workflow.tasks):
        flash('You do not have permission to view this workflow.', 'danger')
        return redirect(url_for('workflow'))
    
    # Get tasks ordered by sequence
    tasks = WorkflowTask.query.filter_by(workflow_id=workflow.id).order_by(WorkflowTask.order).all()
    
    # Get documents in this workflow
    documents = Document.query.filter_by(workflow_id=workflow.id).all()
    
    return render_template('workflow_detail.html', 
                          workflow=workflow,
                          tasks=tasks,
                          documents=documents)

@app.route('/workflow/task/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    task = WorkflowTask.query.get_or_404(task_id)
    
    # Check if user is assigned to this task
    if task.assigned_to_id != current_user.id:
        flash('You are not assigned to this task.', 'danger')
        return redirect(url_for('workflow'))
    
    # Get action type (approve/reject)
    action = request.form.get('action', 'approve')
    comments = request.form.get('comments', '')
    
    try:
        # Update task status
        complete_workflow_task(task.id, action, comments)
        
        # Create notification for workflow creator
        workflow = Workflow.query.get(task.workflow_id)
        notification = Notification(
            user_id=workflow.created_by_id,
            message=f"{current_user.username} has {action}ed the task '{task.name}' in workflow '{workflow.name}'."
        )
        db.session.add(notification)
        db.session.commit()
        
        flash(f'Task {action}d successfully!', 'success')
    except Exception as e:
        flash(f'Error completing task: {str(e)}', 'danger')
    
    return redirect(url_for('workflow_detail', workflow_id=task.workflow_id))

# Tag management routes
@app.route('/tags')
@login_required
def manage_tags():
    tags = Tag.query.all()
    return render_template('manage_tags.html', tags=tags)

@app.route('/tags/create', methods=['POST'])
@login_required
def create_tag():
    tag_name = request.form.get('tag_name')
    tag_color = request.form.get('tag_color', '#6c757d')
    
    if not tag_name:
        flash('Tag name is required', 'danger')
        return redirect(url_for('manage_tags'))
    
    # Check if tag already exists
    existing_tag = Tag.query.filter_by(name=tag_name).first()
    if existing_tag:
        flash('Tag with this name already exists', 'warning')
        return redirect(url_for('manage_tags'))
    
    # Create new tag
    tag = Tag(name=tag_name, color=tag_color)
    db.session.add(tag)
    db.session.commit()
    flash('Tag created successfully!', 'success')
    return redirect(url_for('manage_tags'))

@app.route('/tags/<int:tag_id>/update', methods=['POST'])
@login_required
def update_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    
    tag_name = request.form.get('tag_name')
    tag_color = request.form.get('tag_color')
    
    if not tag_name:
        flash('Tag name is required', 'danger')
        return redirect(url_for('manage_tags'))
    
    # Check if new name conflicts with existing tag
    existing_tag = Tag.query.filter_by(name=tag_name).first()
    if existing_tag and existing_tag.id != tag.id:
        flash('Tag with this name already exists', 'warning')
        return redirect(url_for('manage_tags'))
    
    tag.name = tag_name
    tag.color = tag_color
    db.session.commit()
    flash('Tag updated successfully!', 'success')
    return redirect(url_for('manage_tags'))

@app.route('/tags/<int:tag_id>/delete', methods=['POST'])
@login_required
def delete_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    
    db.session.delete(tag)
    db.session.commit()
    flash('Tag deleted successfully!', 'success')
    return redirect(url_for('manage_tags'))

# Notification routes
@app.route('/notifications')
@login_required
def notifications():
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=user_notifications)

@app.route('/notifications/mark_read/<int:notification_id>', methods=['POST'])
@login_required
@csrf.exempt
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    
    # Check if notification belongs to current user
    if notification.user_id != current_user.id:
        abort(403)
    
    notification.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/notifications/mark_all_read', methods=['POST'])
@login_required
@csrf.exempt
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id).update({'is_read': True})
    db.session.commit()
    flash('Tutte le notifiche contrassegnate come lette', 'success')
    return redirect(url_for('notifications'))

# User settings and profile routes
@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/settings/profile', methods=['POST'])
@login_required
def update_profile():
    current_user.first_name = request.form.get('first_name', current_user.first_name)
    current_user.last_name = request.form.get('last_name', current_user.last_name)
    current_user.email = request.form.get('email', current_user.email)
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/settings/password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate inputs
    if not current_user.check_password(current_password):
        flash('Current password is incorrect', 'danger')
        return redirect(url_for('settings'))
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'danger')
        return redirect(url_for('settings'))
    
    # Update password
    current_user.set_password(new_password)
    db.session.commit()
    flash('Password changed successfully!', 'success')
    return redirect(url_for('settings'))

# Admin routes
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    # Get basic stats for admin dashboard
    user_count = User.query.count()
    document_count = Document.query.count()
    workflow_count = Workflow.query.count()
    tag_count = Tag.query.count()
    
    # Controlla la configurazione delle notifiche
    notification_config = {
        'reminder_count': Reminder.query.filter_by(is_completed=False).count(),
        'upcoming_reminders': Reminder.query.filter(
            Reminder.is_completed == False,
            Reminder.due_date >= datetime.datetime.now()
        ).order_by(Reminder.due_date).limit(5).all(),
        'notification_count': Notification.query.count(),
        'unread_notifications': Notification.query.filter_by(is_read=False).count()
    }
    
    # Get recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                          user_count=user_count,
                          document_count=document_count,
                          workflow_count=workflow_count,
                          tag_count=tag_count,
                          recent_users=recent_users,
                          notification_config=notification_config)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.username = request.form.get('username', user.username)
        user.email = request.form.get('email', user.email)
        user.first_name = request.form.get('first_name', user.first_name)
        user.last_name = request.form.get('last_name', user.last_name)
        user.role = request.form.get('role', user.role)
        
        # Update password if provided
        new_password = request.form.get('new_password')
        if new_password:
            user.set_password(new_password)
        
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin/edit_user.html', user=user)

@app.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        role = request.form.get('role', 'user')
        
        # Validate inputs
        if not username or not email or not password:
            flash('Username, email and password are required', 'danger')
            return redirect(request.url)
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(request.url)
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(request.url)
        
        # Create new user
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        flash('User created successfully!', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin/create_user.html')

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    if user_id == current_user.id:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('admin_users'))
    
    user = User.query.get_or_404(user_id)
    
    # Delete associated records
    Notification.query.filter_by(user_id=user.id).delete()
    SearchHistory.query.filter_by(user_id=user.id).delete()
    
    # Handle workflow tasks assigned to this user
    WorkflowTask.query.filter_by(assigned_to_id=user.id).update({'assigned_to_id': None})
    
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin_users'))

# API Endpoints for AJAX requests
@app.route('/api/notifications/count')
@login_required
def get_unread_notification_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})

@app.route('/api/notifications/recent')
@login_required
def get_recent_notifications():
    """Ottieni le notifiche recenti non lette per il dropdown"""
    notifications = Notification.query.filter_by(
        user_id=current_user.id, 
        is_read=False
    ).order_by(Notification.created_at.desc()).limit(5).all()
    
    result = [{
        'id': n.id,
        'message': n.message,
        'link': n.link,
        'notification_type': n.notification_type,
        'created_at': n.created_at.strftime('%Y-%m-%dT%H:%M:%S')
    } for n in notifications]
    
    return jsonify({'notifications': result})
    
@app.route('/api/reminders/check', methods=['POST'])
@login_required
@csrf.exempt
def manual_reminder_check():
    """Endpoint per eseguire manualmente la verifica dei promemoria"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Accesso non autorizzato'}), 403
    
    try:
        from services.reminder_service import check_reminders
        with app.app_context():
            count = check_reminders()
        return jsonify({'success': True, 'message': f'Verifica completata. Generate {count} notifiche.'})
    except Exception as e:
        app.logger.error(f"Errore durante la verifica manuale dei promemoria: {str(e)}")
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'}), 500

@app.route('/api/documents/preview/<int:document_id>')
@login_required
def api_document_preview(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Check if user has permission to view this document
    if document.owner_id != current_user.id and current_user not in document.shared_with:
        return jsonify({'error': 'Permission denied'}), 403
    
    preview_html = get_document_preview(document)
    return jsonify({'preview_html': preview_html})

@app.route('/api/documents/extract-text', methods=['POST'])
@login_required
def api_extract_text():
    if 'document' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['document']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join('/tmp', filename)
        file.save(temp_path)
        
        try:
            # Extract text
            file_type = filename.rsplit('.', 1)[1].lower()
            text = extract_text_from_document(temp_path, file_type)
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return jsonify({'text': text})
        except Exception as e:
            return jsonify({'error': f'Text extraction failed: {str(e)}'}), 500
    else:
        return jsonify({'error': 'File type not allowed'}), 400

@app.route('/api/documents/classify', methods=['POST'])
@login_required
def api_classify_document():
    text = request.json.get('text', '')
    file_type = request.json.get('file_type', '')
    
    if not text:
        return jsonify({'error': 'No text provided for classification'}), 400
    
    try:
        classification = classify_document(text, file_type)
        return jsonify({'classification': classification})
    except Exception as e:
        return jsonify({'error': f'Classification failed: {str(e)}'}), 500

@app.route('/api/documents/extract-data', methods=['POST'])
@login_required
def api_extract_data():
    text = request.json.get('text', '')
    document_type = request.json.get('document_type', '')
    
    if not text:
        return jsonify({'error': 'No text provided for data extraction'}), 400
    
    try:
        extracted_data = extract_data_from_document(text, document_type)
        return jsonify({'data': extracted_data})
    except Exception as e:
        return jsonify({'error': f'Data extraction failed: {str(e)}'}), 500

@app.route('/api/users/search')
@login_required
def api_search_users():
    query = request.args.get('q', '')
    if not query or len(query) < 2:
        return jsonify([])
    
    users = User.query.filter(
        (User.username.ilike(f'%{query}%')) | 
        (User.email.ilike(f'%{query}%')) |
        (User.first_name.ilike(f'%{query}%')) |
        (User.last_name.ilike(f'%{query}%'))
    ).limit(10).all()
    
    results = [{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': f"{user.first_name} {user.last_name}".strip()
    } for user in users if user.id != current_user.id]
    
    return jsonify(results)

@app.route('/api/tags/search')
@login_required
def api_search_tags():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    tags = Tag.query.filter(Tag.name.ilike(f'%{query}%')).limit(10).all()
    
    results = [{
        'id': tag.id,
        'name': tag.name,
        'color': tag.color
    } for tag in tags]
    
    return jsonify(results)
    
@app.route('/documents/<int:document_id>/view-content')
@login_required
def view_document_content(document_id):
    """Visualizza il contenuto del documento direttamente nel browser"""
    document = Document.query.get_or_404(document_id)
    
    # Verifica autorizzazioni
    if document.owner_id != current_user.id and current_user not in document.shared_with:
        flash('Non hai il permesso di visualizzare questo documento.', 'danger')
        return redirect(url_for('documents'))
    
    # Controlla che il file esista
    if not os.path.exists(document.file_path):
        flash('File non trovato nel sistema.', 'danger')
        return redirect(url_for('view_document', document_id=document.id))
    
    # Per immagini, PDF e altri tipi supportati dal browser, visualizzali direttamente
    if document.file_type in ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'svg']:
        # Log activity
        log_activity(current_user.id, document_id, 'view_content', 'Visualizzazione contenuto documento')
        
        # Invia il file al browser (ma non come download)
        return send_file(document.file_path,
                         mimetype=f'application/{document.file_type}' if document.file_type == 'pdf' else f'image/{document.file_type}',
                         as_attachment=False,
                         download_name=document.original_filename)
    
    # Per altri tipi, reindirizza al download
    flash(f'Visualizzazione diretta non supportata per i file {document.file_type.upper()}. Il file verrà scaricato.', 'info')
    return redirect(url_for('download_document', document_id=document.id))
