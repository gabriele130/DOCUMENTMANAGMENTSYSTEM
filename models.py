import datetime
import json
from app import db, login_manager
from flask_login import UserMixin
from sqlalchemy.orm import relationship, backref
from werkzeug.security import generate_password_hash, check_password_hash

# Association tables for many-to-many relationships
document_tag = db.Table('document_tag',
    db.Column('document_id', db.Integer, db.ForeignKey('document.id')),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
)

document_user = db.Table('document_user',
    db.Column('document_id', db.Integer, db.ForeignKey('document.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
)

user_company = db.Table('user_company',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('company_id', db.Integer, db.ForeignKey('company.id'))
)

# Define access levels for permissions
class AccessLevel:
    NONE = 0
    READ = 1
    WRITE = 2
    MANAGE = 3
    ADMIN = 4

class Company(db.Model):
    """Company/Organization model for multi-tenant support"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = relationship('User', foreign_keys=[created_by_id])
    
    # Relations
    users = relationship('User', secondary=user_company, back_populates='companies')
    folders = relationship('Folder', back_populates='company')
    documents = relationship('Document', back_populates='company')
    
    def __repr__(self):
        return f'<Company {self.name}>'

class Folder(db.Model):
    """Folder model for hierarchical document structure"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    company = relationship('Company', back_populates='folders')
    parent_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=True)
    children = relationship('Folder', 
                           backref=backref('parent', remote_side=[id]),
                           cascade='all, delete-orphan')
    documents = relationship('Document', back_populates='folder')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = relationship('User')
    
    def __repr__(self):
        return f'<Folder {self.name}>'
    
    def get_path(self):
        """Return full path of folder"""
        path = [self.name]
        current = self.parent
        while current:
            path.insert(0, current.name)
            current = current.parent
        return '/' + '/'.join(path)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    role = db.Column(db.String(20), default='user')  # 'admin', 'user', 'reviewer'
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relations
    documents = relationship('Document', back_populates='owner', foreign_keys='Document.owner_id')
    workflow_tasks = relationship('WorkflowTask', back_populates='assigned_to')
    shared_documents = relationship('Document', secondary=document_user, back_populates='shared_with')
    companies = relationship('Company', secondary=user_company, back_populates='users')
    permissions = relationship('Permission', back_populates='user', foreign_keys='Permission.user_id', cascade='all, delete-orphan')
    notifications = relationship('Notification', back_populates='user', cascade='all, delete-orphan')
    activity_logs = relationship('ActivityLog', back_populates='user')
    
    @property
    def full_name(self):
        """Ritorna il nome completo dell'utente (Nome Cognome)"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def has_permission(self, folder_id, access_level):
        """Check if user has specific permission level for a folder"""
        # Admins have all permissions
        if self.is_admin():
            return True
        
        # Check specific permissions
        permission = Permission.query.filter_by(
            user_id=self.id, 
            folder_id=folder_id
        ).first()
        
        if permission and permission.access_level >= access_level:
            return True
        
        return False

    def __repr__(self):
        return f'<User {self.username}>'

class Permission(db.Model):
    """User permissions for folders"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = relationship('User', back_populates='permissions', foreign_keys=[user_id])
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'))
    folder = relationship('Folder')
    access_level = db.Column(db.Integer, default=AccessLevel.READ)  # 0=none, 1=read, 2=write, 3=manage, 4=admin
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = relationship('User', foreign_keys=[created_by_id])
    
    def __repr__(self):
        return f'<Permission {self.user_id} on {self.folder_id} level={self.access_level}>'

# Tabella di associazione per i documenti allegati
document_attachment = db.Table('document_attachment',
    db.Column('parent_document_id', db.Integer, db.ForeignKey('document.id'), primary_key=True),
    db.Column('attached_document_id', db.Integer, db.ForeignKey('document.id'), primary_key=True),
    db.Column('attachment_type', db.String(50), default='attachment'), # tipo: 'amendment', 'supplement', 'attachment'
    db.Column('created_at', db.DateTime, default=datetime.datetime.utcnow),
    db.Column('attachment_note', db.Text)
)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # Size in bytes
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    content_text = db.Column(db.Text)  # Extracted text from OCR
    classification = db.Column(db.String(100))  # AI-determined document type
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Owner and permissions
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = relationship('User', back_populates='documents', foreign_keys=[owner_id])
    
    # Organization and structure
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)
    company = relationship('Company', back_populates='documents')
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=True)
    folder = relationship('Folder', back_populates='documents')
    
    # Relations
    versions = relationship('DocumentVersion', back_populates='document', cascade='all, delete-orphan')
    doc_metadata = relationship('DocumentMetadata', back_populates='document', cascade='all, delete-orphan')
    tags = relationship('Tag', secondary=document_tag, back_populates='documents')
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow.id'), nullable=True)
    workflow = relationship('Workflow', back_populates='documents')
    shared_with = relationship('User', secondary=document_user, back_populates='shared_documents')
    reminders = relationship('Reminder', back_populates='document', cascade='all, delete-orphan')
    activity_logs = relationship('ActivityLog', back_populates='document')
    
    # Allegati e documenti collegati
    attachments = relationship(
        'Document', 
        secondary=document_attachment,
        primaryjoin=(id == document_attachment.c.parent_document_id),
        secondaryjoin=(id == document_attachment.c.attached_document_id),
        backref=backref('attached_to', lazy='dynamic')
    )
    
    # Status flags
    is_archived = db.Column(db.Boolean, default=False)
    expiry_date = db.Column(db.Date, nullable=True)  # For documents with expiration
    document_status = db.Column(db.String(50), default='active')  # active, expired, pending_review
    
    @property
    def full_path(self):
        if self.folder:
            return self.folder.get_path() + '/' + self.filename
        return '/' + self.filename
    
    def get_metadata(self, key=None):
        """Get document metadata, either all or by key"""
        if key:
            metadata = DocumentMetadata.query.filter_by(document_id=self.id, key=key).first()
            return metadata.value if metadata else None
        
        result = {}
        for metadata in self.doc_metadata:
            result[metadata.key] = metadata.value
        return result
    
    def set_metadata(self, key, value, user_id=None):
        """Set document metadata"""
        metadata = DocumentMetadata.query.filter_by(document_id=self.id, key=key).first()
        
        if metadata:
            old_value = metadata.value
            metadata.value = value
            
            # Log the change
            if user_id and old_value != value:
                log = ActivityLog(
                    user_id=user_id,
                    document_id=self.id,
                    action="update_metadata",
                    details=json.dumps({
                        "key": key,
                        "old_value": old_value,
                        "new_value": value
                    })
                )
                db.session.add(log)
        else:
            metadata = DocumentMetadata(document_id=self.id, key=key, value=value)
            db.session.add(metadata)
            
            # Log the addition
            if user_id:
                log = ActivityLog(
                    user_id=user_id,
                    document_id=self.id,
                    action="add_metadata",
                    details=json.dumps({
                        "key": key,
                        "value": value
                    })
                )
                db.session.add(log)
        
        db.session.commit()
        return metadata

    def __repr__(self):
        return f'<Document {self.title or self.original_filename}>'

class DocumentVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'))
    document = relationship('Document', back_populates='versions')
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = relationship('User')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    change_summary = db.Column(db.Text)

    def __repr__(self):
        return f'<DocumentVersion {self.document_id}-v{self.version_number}>'

class DocumentMetadata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'))
    document = relationship('Document', back_populates='doc_metadata')
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(512))
    last_modified = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    modified_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    modified_by = relationship('User')
    
    def __repr__(self):
        return f'<DocumentMetadata {self.key}={self.value}>'

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    color = db.Column(db.String(7), default='#6c757d')  # Hex color code
    description = db.Column(db.String(255))
    documents = relationship('Document', secondary=document_tag, back_populates='tags')
    
    def __repr__(self):
        return f'<Tag {self.name}>'

class Workflow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = relationship('User')
    status = db.Column(db.String(50), default='active')  # active, complete, cancelled
    documents = relationship('Document', back_populates='workflow')
    tasks = relationship('WorkflowTask', back_populates='workflow', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Workflow {self.name}>'

class WorkflowTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow.id'))
    workflow = relationship('Workflow', back_populates='tasks')
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    order = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, in_progress, complete, rejected
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    assigned_to = relationship('User', back_populates='workflow_tasks')
    due_date = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    comments = db.Column(db.Text)
    
    def __repr__(self):
        return f'<WorkflowTask {self.name} ({self.status})>'

class Reminder(db.Model):
    """Reminders for documents, deadlines, and tasks"""
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=True)
    document = relationship('Document', back_populates='reminders')
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    reminder_type = db.Column(db.String(50), nullable=False)  # 'deadline', 'renewal', 'activity', 'verification', etc.
    due_date = db.Column(db.DateTime, nullable=False)
    frequency = db.Column(db.String(50))  # 'once', 'daily', 'weekly', 'monthly', 'yearly'
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    completed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    completed_by = relationship('User', foreign_keys=[completed_by_id])
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = relationship('User', foreign_keys=[created_by_id])
    
    # Notification settings
    notify_days_before = db.Column(db.Integer, default=7)  # Send notification X days before due date
    notify_users = db.Column(db.Text)  # JSON array of user IDs to notify
    extra_notifications = db.Column(db.Text)  # JSON array of additional notification settings
    
    def __repr__(self):
        return f'<Reminder {self.title} due={self.due_date}>'
    
    def is_due_soon(self, days=None):
        """Check if reminder is due soon"""
        if days is None:
            days = self.notify_days_before
            
        if not self.due_date:
            return False
            
        now = datetime.datetime.now()
        delta = self.due_date - now
        return delta.days <= days and delta.days >= 0
    
    def is_overdue(self):
        """Check if reminder is overdue"""
        if not self.due_date:
            return False
            
        now = datetime.datetime.now()
        return now > self.due_date and not self.is_completed
    
    def get_notify_users_list(self):
        """Get list of user IDs to notify"""
        if not self.notify_users:
            return []
        try:
            return json.loads(self.notify_users)
        except:
            return []

class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = relationship('User')
    query = db.Column(db.String(255), nullable=False)
    filters = db.Column(db.Text)  # JSON string of filters
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f'<SearchHistory {self.query}>'

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = relationship('User', back_populates='notifications')
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(512), nullable=True)  # Optional URL to redirect when clicked
    notification_type = db.Column(db.String(50), default='info')  # info, warning, reminder, task
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f'<Notification {self.id} for User {self.user_id}>'

class ActivityLog(db.Model):
    """Activity log for tracking user actions with enhanced security for ISO 27001, GDPR, eIDAS compliance"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = relationship('User', back_populates='activity_logs')
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=True)
    document = relationship('Document', back_populates='activity_logs')
    
    # Enhanced action tracking - more specific categories
    action = db.Column(db.String(50), nullable=False)  # view, upload, update, delete, share, print, download, etc.
    action_category = db.Column(db.String(50))  # CRUD, ACCESS, ADMIN, SECURITY
    
    # Enhanced details
    details = db.Column(db.Text)  # JSON with action-specific details
    context_metadata = db.Column(db.Text)  # JSON with contextual metadata (document version, size, etc.)
    result = db.Column(db.String(20))  # success, failure, denied
    
    # Enhanced device and location tracking
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(256))  # Browser/client info
    device_info = db.Column(db.String(256))  # Device type/OS
    geolocation = db.Column(db.String(150), nullable=True)  # Optional geolocation data if available
    
    # Enhanced temporal data for audit trails
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Integrity assurance
    record_hash = db.Column(db.String(256), nullable=True)  # Hash of log entry for tamper detection
    
    # Security classification for the log entry itself
    security_level = db.Column(db.String(20), default='standard')  # standard, sensitive, critical
    
    # Verification of log integrity
    verified = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<ActivityLog {self.action} by {self.user_id} on {self.document_id}>'
    
    def calculate_hash(self):
        """Calculate a hash of the log entry to detect tampering"""
        from hashlib import sha256
        data = f"{self.user_id}:{self.document_id}:{self.action}:{self.details}:{self.context_metadata}:{self.ip_address}:{self.created_at}"
        return sha256(data.encode()).hexdigest()
        
    def verify_integrity(self):
        """Verify that the log entry has not been tampered with"""
        return self.record_hash == self.calculate_hash()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
