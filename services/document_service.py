"""
Servizio per la gestione dei documenti.

Questo modulo fornisce funzioni per la gestione completa dei documenti:
- Upload e salvataggio
- Recupero e download
- Modifica metadati
- Gestione tag e promemoria
"""

import os
import logging
import datetime
from flask import current_app
from werkzeug.utils import secure_filename
from app import db
from models import Document, Tag, DocumentMetadata, ActivityLog
from services.simple_storage import save_file, get_file_path, file_exists, delete_file

# Tipi di file consentiti
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'jpg', 'jpeg', 'png', 'gif'}

def allowed_file(filename):
    """
    Verifica se l'estensione del file è consentita.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_document(file_obj, owner_id, title=None, description=None, tags=None, 
                   expiry_date=None, folder_id=None, company_id=None):
    """
    Carica un nuovo documento nel sistema.
    
    Args:
        file_obj: Oggetto file da caricare
        owner_id: ID dell'utente proprietario
        title: Titolo del documento (opzionale)
        description: Descrizione del documento (opzionale)
        tags: Lista di tag da assegnare al documento (opzionale)
        expiry_date: Data di scadenza del documento (opzionale)
        folder_id: ID della cartella in cui salvare il documento (opzionale)
        company_id: ID dell'azienda associata al documento (opzionale)
        
    Returns:
        Document: Oggetto documento creato o None in caso di errore
    """
    try:
        if not file_obj or file_obj.filename == '':
            logging.error("Tentativo di caricamento di un file vuoto")
            return None
        
        # Verifica estensione permessa
        if not allowed_file(file_obj.filename):
            logging.error(f"Estensione non consentita: {file_obj.filename}")
            return None
        
        # Salva il file utilizzando il servizio di storage semplificato
        storage_result = save_file(file_obj)
        
        if not storage_result:
            logging.error("Errore durante il salvataggio del file")
            return None
        
        # Prepara i dati del documento
        original_filename = secure_filename(file_obj.filename)
        filename = storage_result['filename']
        file_path = storage_result['file_path']
        file_size = storage_result['file_size']
        file_type = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'unknown'
        
        # Crea il documento nel database
        document = Document(
            filename=filename,
            original_filename=original_filename,
            file_path=file_path,
            file_type=file_type,
            file_size=file_size,
            title=title or original_filename,
            description=description,
            owner_id=owner_id,
            folder_id=folder_id,
            company_id=company_id,
            expiry_date=expiry_date
        )
        
        db.session.add(document)
        db.session.flush()  # Ottieni l'ID documento senza fare commit
        
        # Aggiungi i tag se specificati
        if tags:
            for tag_name in tags:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                    db.session.flush()
                document.tags.append(tag)
        
        # Registra l'operazione
        log = ActivityLog(
            user_id=owner_id,
            document_id=document.id,
            action="upload",
            details=f"Documento caricato: {original_filename}"
        )
        db.session.add(log)
        
        # Commit alla fine
        db.session.commit()
        
        logging.info(f"Documento creato con successo: ID {document.id}, {file_path}")
        return document
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Errore durante il caricamento del documento: {str(e)}")
        return None

def get_document(document_id, user_id):
    """
    Recupera un documento dal database e verifica che l'utente abbia accesso.
    
    Args:
        document_id: ID del documento da recuperare
        user_id: ID dell'utente che fa la richiesta
        
    Returns:
        Document: Oggetto documento o None se non trovato o accesso negato
    """
    try:
        document = Document.query.get(document_id)
        
        if not document:
            return None
        
        # Verifica se l'utente ha accesso (proprietario, amministratore o condivisione)
        from models import User
        user = User.query.get(user_id)
        
        if not user:
            return None
        
        # Gli amministratori hanno accesso a tutti i documenti
        if user.is_admin():
            return document
        
        # Il proprietario ha accesso
        if document.owner_id == user_id:
            return document
        
        # Controlla se il documento è condiviso con l'utente
        if user in document.shared_with:
            return document
        
        # Se siamo qui, l'utente non ha accesso
        return None
    
    except Exception as e:
        logging.error(f"Errore durante il recupero del documento: {str(e)}")
        return None

def verify_document_accessibility(document):
    """
    Verifica che il file del documento sia accessibile.
    
    Args:
        document: Oggetto documento da verificare
        
    Returns:
        tuple: (status_code, message)
            status_code: 200 se accessibile, altro se problemi
            message: Messaggio descrittivo
    """
    if not document:
        return 404, "Documento non trovato nel database"
    
    # Verifica se il file esiste nel percorso registrato
    if os.path.exists(document.file_path):
        return 200, "File accessibile"
    
    # Se il percorso registrato non esiste, verifica utilizzando il nome file
    if file_exists(document.filename):
        # Aggiorna il percorso nel database
        document.file_path = get_file_path(document.filename)
        db.session.commit()
        
        # Registra l'operazione
        logging.info(f"Percorso documento aggiornato: ID {document.id}, {document.file_path}")
        return 200, "File accessibile (percorso aggiornato)"
    
    # Se arriviamo qui, il file non è accessibile
    return 404, f"File non trovato: {document.file_path}"

def update_document(document_id, user_id, **kwargs):
    """
    Aggiorna i metadati di un documento.
    
    Args:
        document_id: ID del documento da aggiornare
        user_id: ID dell'utente che fa la richiesta
        **kwargs: Campi da aggiornare (title, description, expiry_date, tags, ecc.)
        
    Returns:
        Document: Oggetto documento aggiornato o None in caso di errore
    """
    try:
        # Recupera il documento
        document = get_document(document_id, user_id)
        
        if not document:
            return None
        
        # Verifica che l'utente sia il proprietario o un amministratore
        from models import User
        user = User.query.get(user_id)
        
        if not user.is_admin() and document.owner_id != user_id:
            logging.error(f"L'utente {user_id} non ha i permessi per modificare il documento {document_id}")
            return None
        
        # Aggiorna i campi specificati
        changes = []
        
        if 'title' in kwargs and kwargs['title'] is not None:
            old_title = document.title
            document.title = kwargs['title']
            changes.append(f"Titolo: '{old_title}' -> '{document.title}'")
        
        if 'description' in kwargs and kwargs['description'] is not None:
            old_desc = document.description or ''
            document.description = kwargs['description']
            changes.append(f"Descrizione modificata")
        
        if 'expiry_date' in kwargs:
            old_date = document.expiry_date
            document.expiry_date = kwargs['expiry_date']
            changes.append(f"Data di scadenza: '{old_date}' -> '{document.expiry_date}'")
        
        if 'tags' in kwargs and kwargs['tags'] is not None:
            # Rimuovi tutti i tag esistenti
            document.tags = []
            
            # Aggiungi i nuovi tag
            for tag_name in kwargs['tags']:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                    db.session.flush()
                document.tags.append(tag)
            
            changes.append("Tag aggiornati")
        
        # Aggiorna la data di modifica
        document.updated_at = datetime.datetime.utcnow()
        
        # Registra l'operazione nel log attività
        if changes:
            log = ActivityLog(
                user_id=user_id,
                document_id=document_id,
                action="update",
                details=", ".join(changes)
            )
            db.session.add(log)
        
        db.session.commit()
        
        logging.info(f"Documento {document_id} aggiornato da utente {user_id}")
        return document
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Errore durante l'aggiornamento del documento: {str(e)}")
        return None

def delete_document(document_id, user_id):
    """
    Elimina un documento dal sistema.
    
    Args:
        document_id: ID del documento da eliminare
        user_id: ID dell'utente che fa la richiesta
        
    Returns:
        bool: True se l'eliminazione è riuscita, False altrimenti
    """
    try:
        # Recupera il documento
        document = get_document(document_id, user_id)
        
        if not document:
            return False
        
        # Verifica che l'utente sia il proprietario o un amministratore
        from models import User
        user = User.query.get(user_id)
        
        if not user.is_admin() and document.owner_id != user_id:
            logging.error(f"L'utente {user_id} non ha i permessi per eliminare il documento {document_id}")
            return False
        
        # Elimina il file dal file system
        filename = document.filename
        file_deleted = delete_file(filename)
        
        if not file_deleted:
            logging.warning(f"File non trovato o impossibile da eliminare: {document.file_path}")
        
        # Elimina il documento dal database
        db.session.delete(document)
        
        # Registra l'operazione
        log = ActivityLog(
            user_id=user_id,
            action="delete",
            details=f"Documento eliminato: {document.title or document.original_filename}"
        )
        db.session.add(log)
        
        db.session.commit()
        
        logging.info(f"Documento {document_id} eliminato da utente {user_id}")
        return True
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Errore durante l'eliminazione del documento: {str(e)}")
        return False