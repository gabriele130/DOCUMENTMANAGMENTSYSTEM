import datetime
from app import db, login_manager
from flask_login import UserMixin
from sqlalchemy.orm import relationship
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

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    role = db.Column(db.String(20), default='user')  # 'admin', 'user', 'reviewer'
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    documents = relationship('Document', back_populates='owner')
    workflow_tasks = relationship('WorkflowTask', back_populates='assigned_to')
    shared_documents = relationship('Document', secondary=document_user, back_populates='shared_with')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

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
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = relationship('User', back_populates='documents')
    versions = relationship('DocumentVersion', back_populates='document', cascade='all, delete-orphan')
    doc_metadata = relationship('DocumentMetadata', back_populates='document', cascade='all, delete-orphan')
    tags = relationship('Tag', secondary=document_tag, back_populates='documents')
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow.id'), nullable=True)
    workflow = relationship('Workflow', back_populates='documents')
    shared_with = relationship('User', secondary=document_user, back_populates='shared_documents')
    is_archived = db.Column(db.Boolean, default=False)
    expiry_date = db.Column(db.Date, nullable=True)  # For documents with expiration

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
    
    def __repr__(self):
        return f'<DocumentMetadata {self.key}={self.value}>'

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    color = db.Column(db.String(7), default='#6c757d')  # Hex color code
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
    user = relationship('User')
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f'<Notification {self.id} for User {self.user_id}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
