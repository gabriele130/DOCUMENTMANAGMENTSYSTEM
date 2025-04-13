import os
import json
import datetime
from functools import wraps
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, abort
from flask_login import login_required, current_user
from app import app, db
from models import (User, Document, Company, Folder, Permission, ActivityLog, AccessLevel, 
                   Reminder, Tag, DocumentMetadata)
from routes import log_activity, admin_required

# Company management routes
@app.route('/companies')
@login_required
def companies():
    """List all companies the user has access to"""
    if current_user.is_admin():
        companies = Company.query.all()
    else:
        companies = current_user.companies
    
    return render_template('companies.html', companies=companies)

@app.route('/companies/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_company():
    """Create a new company"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        if not name:
            flash('Company name is required', 'danger')
            return redirect(request.url)
            
        # Check if company already exists
        if Company.query.filter_by(name=name).first():
            flash('A company with this name already exists', 'danger')
            return redirect(request.url)
            
        company = Company(
            name=name,
            description=description,
            created_by_id=current_user.id
        )
        
        # Add current user to the company
        company.users.append(current_user)
        
        # Create root folder for company
        root_folder = Folder(
            name=name,
            description=f"Root folder for {name}",
            company=company,
            created_by_id=current_user.id
        )
        
        db.session.add(company)
        db.session.add(root_folder)
        db.session.commit()
        
        flash('Company created successfully', 'success')
        return redirect(url_for('company_detail', company_id=company.id))
        
    return render_template('create_company.html')

@app.route('/companies/<int:company_id>')
@login_required
def company_detail(company_id):
    """View company details and structure"""
    company = Company.query.get_or_404(company_id)
    
    # Check if user has access to this company
    if not current_user.is_admin() and company not in current_user.companies:
        flash('You do not have access to this company', 'danger')
        return redirect(url_for('companies'))
    
    # Get root folders for the company
    root_folders = Folder.query.filter_by(company_id=company.id, parent_id=None).all()
    
    # Get recent documents
    recent_documents = Document.query.filter_by(
        company_id=company.id, 
        is_archived=False
    ).order_by(Document.created_at.desc()).limit(10).all()
    
    return render_template('company_detail.html', 
                          company=company, 
                          root_folders=root_folders,
                          recent_documents=recent_documents)

@app.route('/companies/<int:company_id>/update', methods=['GET', 'POST'])
@login_required
@admin_required
def update_company(company_id):
    """Update company details"""
    company = Company.query.get_or_404(company_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        if not name:
            flash('Company name is required', 'danger')
            return redirect(request.url)
            
        # Check if name already exists for a different company
        existing = Company.query.filter_by(name=name).first()
        if existing and existing.id != company.id:
            flash('A company with this name already exists', 'danger')
            return redirect(request.url)
            
        company.name = name
        company.description = description
        db.session.commit()
        
        flash('Company updated successfully', 'success')
        return redirect(url_for('company_detail', company_id=company.id))
        
    return render_template('update_company.html', company=company)

@app.route('/companies/<int:company_id>/users')
@login_required
@admin_required
def company_users(company_id):
    """Manage users for a company"""
    company = Company.query.get_or_404(company_id)
    
    # Get all users for the company
    company_users = company.users
    
    # Get all users not in the company
    other_users = User.query.filter(User.id.notin_([u.id for u in company_users])).all()
    
    return render_template('company_users.html', 
                          company=company,
                          company_users=company_users,
                          other_users=other_users)

@app.route('/companies/<int:company_id>/users/add', methods=['POST'])
@login_required
@admin_required
def add_company_user(company_id):
    """Add user to company"""
    company = Company.query.get_or_404(company_id)
    
    user_id = request.form.get('user_id')
    if not user_id:
        flash('No user selected', 'danger')
        return redirect(url_for('company_users', company_id=company.id))
        
    user = User.query.get_or_404(user_id)
    
    if user in company.users:
        flash(f'{user.username} is already a member of this company', 'warning')
    else:
        company.users.append(user)
        db.session.commit()
        flash(f'{user.username} added to company', 'success')
        
        # Log activity
        log_activity(
            user_id=current_user.id,
            action="add_user_to_company",
            details=json.dumps({
                "company_id": company.id,
                "company_name": company.name,
                "user_id": user.id,
                "username": user.username
            })
        )
    
    return redirect(url_for('company_users', company_id=company.id))

@app.route('/companies/<int:company_id>/users/remove/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def remove_company_user(company_id, user_id):
    """Remove user from company"""
    company = Company.query.get_or_404(company_id)
    user = User.query.get_or_404(user_id)
    
    if user not in company.users:
        flash(f'{user.username} is not a member of this company', 'warning')
    else:
        # Don't remove the company creator
        if user.id == company.created_by_id:
            flash('Cannot remove the company creator', 'danger')
        else:
            company.users.remove(user)
            db.session.commit()
            flash(f'{user.username} removed from company', 'success')
            
            # Log activity
            log_activity(
                user_id=current_user.id,
                action="remove_user_from_company",
                details=json.dumps({
                    "company_id": company.id,
                    "company_name": company.name,
                    "user_id": user.id,
                    "username": user.username
                })
            )
    
    return redirect(url_for('company_users', company_id=company.id))

# Folder structure routes
@app.route('/folders/<int:folder_id>')
@login_required
def folder_detail(folder_id):
    """View folder contents"""
    folder = Folder.query.get_or_404(folder_id)
    company = folder.company
    
    # Check if user has access to this company
    if not current_user.is_admin() and company not in current_user.companies:
        flash('You do not have access to this folder', 'danger')
        return redirect(url_for('companies'))
    
    # Check if user has at least read permission on this folder
    if not current_user.is_admin() and not current_user.has_permission(folder_id, AccessLevel.READ):
        flash('You do not have permission to view this folder', 'danger')
        return redirect(url_for('company_detail', company_id=company.id))
    
    # Get subfolders
    subfolders = folder.children
    
    # Get documents in this folder
    documents = Document.query.filter_by(folder_id=folder.id, is_archived=False).all()
    
    # Get folder breadcrumbs
    breadcrumbs = []
    current = folder
    while current:
        breadcrumbs.insert(0, current)
        current = current.parent
    
    # Log the view activity
    log_activity(
        user_id=current_user.id,
        action="view_folder",
        details=json.dumps({
            "folder_id": folder.id,
            "folder_name": folder.name,
            "folder_path": folder.get_path()
        })
    )
    
    return render_template('folder_detail.html', 
                          folder=folder,
                          company=company,
                          subfolders=subfolders,
                          documents=documents,
                          breadcrumbs=breadcrumbs)

@app.route('/folders/create/<int:parent_id>', methods=['GET', 'POST'])
@login_required
def create_folder(parent_id):
    """Create a new folder"""
    parent_folder = Folder.query.get_or_404(parent_id)
    company = parent_folder.company
    
    # Check if user has access to this company
    if not current_user.is_admin() and company not in current_user.companies:
        flash('You do not have access to this company', 'danger')
        return redirect(url_for('companies'))
    
    # Check if user has write permission on parent folder
    if not current_user.is_admin() and not current_user.has_permission(parent_id, AccessLevel.WRITE):
        flash('You do not have permission to create folders here', 'danger')
        return redirect(url_for('folder_detail', folder_id=parent_id))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        if not name:
            flash('Folder name is required', 'danger')
            return redirect(request.url)
            
        # Check if folder with same name already exists at this level
        existing = Folder.query.filter_by(parent_id=parent_id, name=name).first()
        if existing:
            flash('A folder with this name already exists in this location', 'danger')
            return redirect(request.url)
            
        folder = Folder(
            name=name,
            description=description,
            parent_id=parent_id,
            company_id=company.id,
            created_by_id=current_user.id
        )
        
        db.session.add(folder)
        db.session.commit()
        
        # Log the creation
        log_activity(
            user_id=current_user.id,
            action="create_folder",
            details=json.dumps({
                "folder_id": folder.id,
                "folder_name": folder.name,
                "folder_path": folder.get_path(),
                "parent_id": parent_id
            })
        )
        
        flash('Folder created successfully', 'success')
        return redirect(url_for('folder_detail', folder_id=folder.id))
        
    return render_template('create_folder.html', parent=parent_folder)

@app.route('/folders/<int:folder_id>/update', methods=['GET', 'POST'])
@login_required
def update_folder(folder_id):
    """Update folder details"""
    folder = Folder.query.get_or_404(folder_id)
    company = folder.company
    
    # Check if user has access to this company
    if not current_user.is_admin() and company not in current_user.companies:
        flash('You do not have access to this company', 'danger')
        return redirect(url_for('companies'))
    
    # Check if user has write permission on this folder
    if not current_user.is_admin() and not current_user.has_permission(folder_id, AccessLevel.WRITE):
        flash('You do not have permission to update this folder', 'danger')
        return redirect(url_for('folder_detail', folder_id=folder_id))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        if not name:
            flash('Folder name is required', 'danger')
            return redirect(request.url)
            
        # Check if folder with same name already exists at this level
        existing = Folder.query.filter_by(
            parent_id=folder.parent_id, 
            name=name
        ).filter(Folder.id != folder_id).first()
        
        if existing:
            flash('A folder with this name already exists in this location', 'danger')
            return redirect(request.url)
            
        # Save old values for logging
        old_name = folder.name
        old_description = folder.description
        
        folder.name = name
        folder.description = description
        db.session.commit()
        
        # Log the update
        log_activity(
            user_id=current_user.id,
            action="update_folder",
            details=json.dumps({
                "folder_id": folder.id,
                "folder_path": folder.get_path(),
                "changes": {
                    "name": {"old": old_name, "new": name},
                    "description": {"old": old_description, "new": description}
                }
            })
        )
        
        flash('Folder updated successfully', 'success')
        return redirect(url_for('folder_detail', folder_id=folder.id))
        
    return render_template('update_folder.html', folder=folder)

@app.route('/folders/<int:folder_id>/permissions')
@login_required
def folder_permissions(folder_id):
    """Manage folder permissions"""
    folder = Folder.query.get_or_404(folder_id)
    company = folder.company
    
    # Check if user has access to this company
    if not current_user.is_admin() and company not in current_user.companies:
        flash('You do not have access to this company', 'danger')
        return redirect(url_for('companies'))
    
    # Check if user has manage permission on this folder
    if not current_user.is_admin() and not current_user.has_permission(folder_id, AccessLevel.MANAGE):
        flash('You do not have permission to manage this folder', 'danger')
        return redirect(url_for('folder_detail', folder_id=folder_id))
    
    # Get all permissions for this folder
    permissions = Permission.query.filter_by(folder_id=folder_id).all()
    
    # Get all users in this company that don't have explicit permissions yet
    users_with_permissions = [p.user_id for p in permissions]
    available_users = User.query.filter(
        User.companies.any(id=company.id),
        User.id.notin_(users_with_permissions)
    ).all()
    
    return render_template('folder_permissions.html', 
                          folder=folder,
                          permissions=permissions,
                          available_users=available_users,
                          access_levels=AccessLevel)

@app.route('/folders/<int:folder_id>/permissions/add', methods=['POST'])
@login_required
def add_folder_permission(folder_id):
    """Add permission for a user on a folder"""
    folder = Folder.query.get_or_404(folder_id)
    company = folder.company
    
    # Check if user has access to this company
    if not current_user.is_admin() and company not in current_user.companies:
        flash('You do not have access to this company', 'danger')
        return redirect(url_for('companies'))
    
    # Check if user has manage permission on this folder
    if not current_user.is_admin() and not current_user.has_permission(folder_id, AccessLevel.MANAGE):
        flash('You do not have permission to manage this folder', 'danger')
        return redirect(url_for('folder_detail', folder_id=folder_id))
    
    user_id = request.form.get('user_id')
    access_level = request.form.get('access_level', AccessLevel.READ)
    
    if not user_id:
        flash('No user selected', 'danger')
        return redirect(url_for('folder_permissions', folder_id=folder_id))
    
    user = User.query.get_or_404(user_id)
    
    # Check if user is part of this company
    if user not in company.users:
        flash('Selected user is not a member of this company', 'danger')
        return redirect(url_for('folder_permissions', folder_id=folder_id))
    
    # Check if permission already exists
    existing = Permission.query.filter_by(user_id=user_id, folder_id=folder_id).first()
    if existing:
        flash(f'Permission already exists for {user.username}', 'warning')
        return redirect(url_for('folder_permissions', folder_id=folder_id))
    
    # Create new permission
    permission = Permission(
        user_id=user_id,
        folder_id=folder_id,
        access_level=access_level,
        created_by_id=current_user.id
    )
    
    db.session.add(permission)
    db.session.commit()
    
    # Log the addition
    log_activity(
        user_id=current_user.id,
        action="add_folder_permission",
        details=json.dumps({
            "folder_id": folder.id,
            "folder_path": folder.get_path(),
            "user_id": user.id,
            "username": user.username,
            "access_level": access_level
        })
    )
    
    flash(f'Permission added for {user.username}', 'success')
    return redirect(url_for('folder_permissions', folder_id=folder_id))

@app.route('/permissions/<int:permission_id>/update', methods=['POST'])
@login_required
def update_permission(permission_id):
    """Update permission level"""
    permission = Permission.query.get_or_404(permission_id)
    folder = permission.folder
    company = folder.company
    
    # Check if user has access to this company
    if not current_user.is_admin() and company not in current_user.companies:
        flash('You do not have access to this company', 'danger')
        return redirect(url_for('companies'))
    
    # Check if user has manage permission on this folder
    if not current_user.is_admin() and not current_user.has_permission(folder.id, AccessLevel.MANAGE):
        flash('You do not have permission to manage this folder', 'danger')
        return redirect(url_for('folder_detail', folder_id=folder.id))
    
    access_level = request.form.get('access_level', AccessLevel.READ)
    
    old_level = permission.access_level
    permission.access_level = access_level
    db.session.commit()
    
    # Log the update
    log_activity(
        user_id=current_user.id,
        action="update_folder_permission",
        details=json.dumps({
            "folder_id": folder.id,
            "folder_path": folder.get_path(),
            "user_id": permission.user_id,
            "username": permission.user.username,
            "old_level": old_level,
            "new_level": access_level
        })
    )
    
    flash(f'Permission updated for {permission.user.username}', 'success')
    return redirect(url_for('folder_permissions', folder_id=folder.id))

@app.route('/permissions/<int:permission_id>/delete', methods=['POST'])
@login_required
def delete_permission(permission_id):
    """Delete a permission"""
    permission = Permission.query.get_or_404(permission_id)
    folder = permission.folder
    company = folder.company
    user = permission.user
    
    # Check if user has access to this company
    if not current_user.is_admin() and company not in current_user.companies:
        flash('You do not have access to this company', 'danger')
        return redirect(url_for('companies'))
    
    # Check if user has manage permission on this folder
    if not current_user.is_admin() and not current_user.has_permission(folder.id, AccessLevel.MANAGE):
        flash('You do not have permission to manage this folder', 'danger')
        return redirect(url_for('folder_detail', folder_id=folder.id))
    
    # Log before deletion
    log_activity(
        user_id=current_user.id,
        action="delete_folder_permission",
        details=json.dumps({
            "folder_id": folder.id,
            "folder_path": folder.get_path(),
            "user_id": user.id,
            "username": user.username,
            "access_level": permission.access_level
        })
    )
    
    db.session.delete(permission)
    db.session.commit()
    
    flash(f'Permission removed for {user.username}', 'success')
    return redirect(url_for('folder_permissions', folder_id=folder.id))

# Upload document to folder
@app.route('/folders/<int:folder_id>/upload', methods=['GET', 'POST'])
@login_required
def upload_document_to_folder(folder_id):
    """Upload document to a specific folder"""
    folder = Folder.query.get_or_404(folder_id)
    company = folder.company
    
    # Check if user has access to this company
    if not current_user.is_admin() and company not in current_user.companies:
        flash('You do not have access to this company', 'danger')
        return redirect(url_for('companies'))
    
    # Check if user has write permission on this folder
    if not current_user.is_admin() and not current_user.has_permission(folder_id, AccessLevel.WRITE):
        flash('You do not have permission to upload to this folder', 'danger')
        return redirect(url_for('folder_detail', folder_id=folder_id))
    
    if request.method == 'POST':
        # Handle file upload (similar to the main upload_document function)
        if 'document' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['document']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        from services.document_processor import allowed_file, extract_document_metadata
        from services.ai_classifier import classify_document
        from services.ocr import extract_text_from_document
        
        if file and allowed_file(file.filename):
            # Save the uploaded file
            from werkzeug.utils import secure_filename
            import uuid
            
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
                owner_id=current_user.id,
                company_id=company.id,
                folder_id=folder_id
            )
            
            # Add tags if provided
            tag_ids = request.form.getlist('tags')
            if tag_ids:
                from models import Tag
                tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
                document.tags.extend(tags)
            
            # Set expiry date if provided
            expiry_date = request.form.get('expiry_date')
            if expiry_date:
                document.expiry_date = datetime.datetime.strptime(expiry_date, '%Y-%m-%d').date()
            
            db.session.add(document)
            db.session.commit()
            
            # Process the document asynchronously (in a real app, this would be a background task)
            try:
                # Extract text with OCR if applicable
                document.content_text = extract_text_from_document(file_path, file_type)
                
                # Classify the document using AI
                document.classification = classify_document(document.content_text or '', file_type)
                
                # Extract metadata from document
                metadata_dict = extract_document_metadata(file_path, file_type)
                from models import DocumentMetadata
                for key, value in metadata_dict.items():
                    metadata = DocumentMetadata(
                        document_id=document.id,
                        key=key,
                        value=str(value),
                        modified_by_id=current_user.id
                    )
                    db.session.add(metadata)
                
                db.session.commit()
                
                # Log activity
                log_activity(
                    user_id=current_user.id,
                    document_id=document.id,
                    action="upload_document",
                    details=json.dumps({
                        "folder_id": folder_id,
                        "folder_path": folder.get_path(),
                        "document_name": filename,
                        "document_type": file_type,
                        "document_size": file_size
                    })
                )
                
                flash('Document uploaded and processed successfully!', 'success')
            except Exception as e:
                app.logger.error(f"Error processing document: {str(e)}")
                flash(f'Document uploaded but processing failed: {str(e)}', 'warning')
            
            return redirect(url_for('folder_detail', folder_id=folder_id))
        else:
            flash('File type not allowed', 'danger')
            return redirect(request.url)
    
    # Get all tags for the upload form
    from models import Tag
    tags = Tag.query.all()
    
    return render_template('upload_to_folder.html', folder=folder, tags=tags)

# Reminder management routes
@app.route('/reminders')
@login_required
def reminders():
    """View all reminders"""
    # Get current date for calculation
    now = datetime.datetime.now()
    
    # Filtri
    reminder_type = request.args.get('reminder_type')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    status = request.args.get('status', '')
    
    # Base query
    query = Reminder.query
    
    # Apply filters
    if reminder_type:
        query = query.filter(Reminder.reminder_type == reminder_type)
    
    if date_from:
        try:
            from_date = datetime.datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Reminder.due_date >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(Reminder.due_date <= to_date)
        except ValueError:
            pass
    
    if status == 'active':
        query = query.filter(Reminder.is_completed == False)
    elif status == 'completed':
        query = query.filter(Reminder.is_completed == True)
    elif status == 'overdue':
        query = query.filter(
            Reminder.is_completed == False,
            Reminder.due_date < datetime.datetime.now()
        )
    
    # Get all reminders
    reminders = query.order_by(Reminder.due_date).all()
    
    # Get upcoming reminders for the sidebar widget
    upcoming_reminders = Reminder.query.filter(
        Reminder.is_completed == False,
        Reminder.due_date >= datetime.datetime.now(),
        Reminder.due_date <= datetime.datetime.now() + datetime.timedelta(days=7)
    ).order_by(Reminder.due_date).limit(5).all()
    
    # Calculate statistics
    total_count = Reminder.query.count()
    active_count = Reminder.query.filter_by(is_completed=False).count()
    overdue_count = Reminder.query.filter(
        Reminder.is_completed == False,
        Reminder.due_date < datetime.datetime.now()
    ).count()
    completed_count = Reminder.query.filter_by(is_completed=True).count()
    due_soon_count = Reminder.query.filter(
        Reminder.is_completed == False,
        Reminder.due_date >= datetime.datetime.now(),
        Reminder.due_date <= datetime.datetime.now() + datetime.timedelta(days=7)
    ).count()
    
    stats = {
        'total': total_count,
        'active': active_count,
        'overdue': overdue_count,
        'completed': completed_count,
        'due_soon': due_soon_count
    }
    
    return render_template('reminders.html', 
                          reminders=reminders,
                          upcoming_reminders=upcoming_reminders,
                          stats=stats,
                          now=now,
                          form=app.context_processor_functions['inject_csrf_form']()['form'])

@app.route('/documents/<int:document_id>/reminders/add', methods=['GET', 'POST'])
@login_required
def add_document_reminder(document_id):
    """Add a reminder for a document"""
    document = Document.query.get_or_404(document_id)
    
    # Check if user has permission to add reminders to this document
    if document.owner_id != current_user.id and current_user not in document.shared_with:
        flash('Non hai i permessi per aggiungere promemoria a questo documento', 'danger')
        return redirect(url_for('documents'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description', '')
        reminder_type = request.form.get('reminder_type')
        due_date = request.form.get('due_date')
        frequency = request.form.get('frequency', 'once')
        
        # Gestione notifiche con unità di tempo personalizzate
        notify_amount = int(request.form.get('notify_amount', 7))
        notify_unit = request.form.get('notify_unit', 'days')
        
        # Calcola giorni prima in base all'unità selezionata
        notify_days_before = notify_amount
        if notify_unit == 'weeks':
            notify_days_before = notify_amount * 7
        elif notify_unit == 'months':
            notify_days_before = notify_amount * 30
        
        # Gestione notifiche multiple
        notify_multiple = 'notify_multiple' in request.form
        extra_notifications = []
        
        if notify_multiple:
            extra_amounts = request.form.getlist('extra_notify_amount[]')
            extra_units = request.form.getlist('extra_notify_unit[]')
            
            for i in range(len(extra_amounts)):
                if i < len(extra_units):
                    try:
                        amount = int(extra_amounts[i])
                        unit = extra_units[i]
                        
                        days = amount
                        if unit == 'weeks':
                            days = amount * 7
                        elif unit == 'months':
                            days = amount * 30
                        
                        extra_notifications.append({
                            'days': days,
                            'amount': amount,
                            'unit': unit
                        })
                    except ValueError:
                        # Ignora valori non numerici
                        continue
        
        notify_users = request.form.getlist('notify_users')
        
        if not title or not due_date or not reminder_type:
            flash('Titolo, tipo e data di scadenza sono obbligatori', 'danger')
            return redirect(request.url)
        
        # Converte la data di scadenza da stringa a datetime
        due_date = datetime.datetime.strptime(due_date, '%Y-%m-%d')
        
        # Crea il promemoria
        reminder = Reminder(
            document_id=document.id,
            title=title,
            description=description,
            reminder_type=reminder_type,
            due_date=due_date,
            frequency=frequency,
            notify_days_before=notify_days_before,
            notify_users=json.dumps(notify_users) if notify_users else None,
            created_by_id=current_user.id
        )
        
        # Salva le notifiche aggiuntive nei metadati
        if extra_notifications:
            reminder.extra_notifications = json.dumps(extra_notifications)
        
        db.session.add(reminder)
        db.session.commit()
        
        # Log activity
        log_activity(
            user_id=current_user.id,
            document_id=document.id,
            action="create_reminder",
            details=json.dumps({
                "reminder_id": reminder.id,
                "title": title,
                "due_date": due_date.strftime('%Y-%m-%d'),
                "reminder_type": reminder_type
            })
        )
        
        flash('Reminder created successfully', 'success')
        return redirect(url_for('view_document', document_id=document.id))
    
    # Get company users if document is in a company folder
    company_users = []
    if document.company_id:
        company = document.company
        company_users = company.users
    
    return render_template('add_reminder.html', document=document, company_users=company_users, form=app.context_processor_functions['inject_csrf_form']()['form'])

@app.route('/reminders/<int:reminder_id>/complete', methods=['POST'])
@login_required
def complete_reminder(reminder_id):
    """Mark a reminder as completed"""
    reminder = Reminder.query.get_or_404(reminder_id)
    
    # Check if user has permission
    document = reminder.document
    if document and document.owner_id != current_user.id and current_user not in document.shared_with:
        flash('You do not have permission to complete this reminder', 'danger')
        return redirect(url_for('reminders'))
    
    reminder.is_completed = True
    reminder.completed_at = datetime.datetime.now()
    reminder.completed_by_id = current_user.id
    db.session.commit()
    
    # Log activity
    log_activity(
        user_id=current_user.id,
        document_id=reminder.document_id,
        action="complete_reminder",
        details=json.dumps({
            "reminder_id": reminder.id,
            "title": reminder.title,
            "completed_at": reminder.completed_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    )
    
    flash('Reminder marked as completed', 'success')
    
    # If request came from document page, redirect back there
    referrer = request.referrer
    if referrer and 'documents' in referrer and str(document.id) in referrer:
        return redirect(url_for('view_document', document_id=document.id))
        
    return redirect(url_for('reminders'))

@app.route('/reminders/<int:reminder_id>/delete', methods=['POST'])
@login_required
def delete_reminder(reminder_id):
    """Delete a reminder"""
    reminder = Reminder.query.get_or_404(reminder_id)
    
    # Check if user has permission
    document = reminder.document
    if document and document.owner_id != current_user.id:
        flash('You do not have permission to delete this reminder', 'danger')
        return redirect(url_for('reminders'))
    
    document_id = reminder.document_id
    
    # Log before deletion
    log_activity(
        user_id=current_user.id,
        document_id=document_id,
        action="delete_reminder",
        details=json.dumps({
            "reminder_id": reminder.id,
            "title": reminder.title,
            "due_date": reminder.due_date.strftime('%Y-%m-%d')
        })
    )
    
    db.session.delete(reminder)
    db.session.commit()
    
    flash('Reminder deleted', 'success')
    
    # If request came from document page, redirect back there
    referrer = request.referrer
    if referrer and 'documents' in referrer and str(document_id) in referrer:
        return redirect(url_for('view_document', document_id=document_id))
        
    return redirect(url_for('reminders'))

# Activity log routes
@app.route('/activity-log')
@login_required
@admin_required
def activity_log():
    """View activity log (admin only)"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).paginate(
        page=page, per_page=per_page
    )
    
    return render_template('activity_log.html', logs=logs)

@app.route('/users/<int:user_id>/activity')
@login_required
def user_activity(user_id):
    """View activity for a specific user"""
    # Check permissions
    if current_user.id != user_id and not current_user.is_admin():
        flash('You do not have permission to view this user\'s activity', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    page = request.args.get('page', 1, type=int)
    per_page = 30
    
    logs = ActivityLog.query.filter_by(user_id=user_id).order_by(
        ActivityLog.created_at.desc()
    ).paginate(page=page, per_page=per_page)
    
    return render_template('user_activity.html', user=user, logs=logs)

@app.route('/documents/<int:document_id>/activity')
@login_required
def document_activity(document_id):
    """View activity for a specific document"""
    document = Document.query.get_or_404(document_id)
    
    # Check permissions
    if document.owner_id != current_user.id and current_user not in document.shared_with and not current_user.is_admin():
        flash('You do not have permission to view this document\'s activity', 'danger')
        return redirect(url_for('documents'))
    
    logs = ActivityLog.query.filter_by(document_id=document_id).order_by(
        ActivityLog.created_at.desc()
    ).all()
    
    return render_template('document_activity.html', document=document, logs=logs)