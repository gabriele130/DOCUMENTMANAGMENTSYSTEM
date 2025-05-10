"""
Modelli semplificati per la gestione dei documenti.
Mantiene solo le funzionalità essenziali.
"""

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
    shared_documents = relationship('Document', secondary=document_user, back_populates='shared_with')
    companies = relationship('Company', secondary=user_company, back_populates='users')
    reminders = relationship('Reminder', back_populates='created_by', foreign_keys='Reminder.created_by_id')
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
    tags = relationship('Tag', secondary=document_tag, back_populates='documents')
    shared_with = relationship('User', secondary=document_user, back_populates='shared_documents')
    reminders = relationship('Reminder', back_populates='document', cascade='all, delete-orphan')
    activity_logs = relationship('ActivityLog', back_populates='document')
    
    # Status flags
    expiry_date = db.Column(db.Date, nullable=True)  # For documents with expiration
    document_status = db.Column(db.String(50), default='active')  # active, expired, pending_review
    
    def __repr__(self):
        return f'<Document {self.title or self.original_filename}>'

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    color = db.Column(db.String(7), default='#6c757d')  # Hex color code
    description = db.Column(db.String(255))
    documents = relationship('Document', secondary=document_tag, back_populates='tags')
    
    def __repr__(self):
        return f'<Tag {self.name}>'

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
    notify_users = db.Column(db.Text)  # Comma-separated list of user IDs to notify
    
    def __repr__(self):
        return f'<Reminder {self.title} due={self.due_date}>'

class ActivityLog(db.Model):
    """Activity log for audit trail"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = relationship('User', back_populates='activity_logs')
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=True)
    document = relationship('Document', back_populates='activity_logs')
    action = db.Column(db.String(50), nullable=False)  # upload, view, download, edit, delete, share, etc.
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    details = db.Column(db.Text)
    
    def __repr__(self):
        return f'<ActivityLog {self.action} user={self.user_id} doc={self.document_id}>'