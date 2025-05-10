"""
Sistema di storage semplificato per i documenti.

Questo servizio sostituisce il complesso sistema di storage attuale,
fornendo un'implementazione semplice e diretta che garantisce la persistenza dei documenti.
"""

import os
import logging
import datetime
import uuid
import shutil
from werkzeug.utils import secure_filename
from flask import current_app
from app import db

# Configurazione directory di upload
UPLOADS_DIR = 'uploads'

def setup_storage():
    """
    Configura le directory di storage e assicura che esistano.
    """
    # Crea la directory di upload se non esiste
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    logging.info(f"Directory di upload: {os.path.abspath(UPLOADS_DIR)}")
    return True

def allowed_file(filename, allowed_extensions=None):
    """
    Verifica se l'estensione del file è consentita.
    """
    if allowed_extensions is None:
        allowed_extensions = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'jpg', 'jpeg', 'png', 'gif'}
    
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_document(file, owner_id):
    """
    Versione semplificata per salvare un documento.
    Sostituisce l'implementazione complessa precedente.
    
    Args:
        file: L'oggetto file da salvare
        owner_id: ID dell'utente proprietario
        
    Returns:
        dict: Dizionario con i metadati del file salvato
    """
    try:
        # Genera un nome file unico ma leggibile
        original_filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())[:8]  # Usa solo i primi 8 caratteri dell'UUID
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        unique_filename = f"{unique_id}_{timestamp}_{original_filename}"
        
        # Crea path assoluto per il file
        upload_dir = os.path.abspath(UPLOADS_DIR)
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Assicurati che la directory esista
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Salva il file
        file.save(file_path)
        
        # Ottieni dimensione e tipo
        file_size = os.path.getsize(file_path)
        file_type = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'unknown'
        
        logging.info(f"File salvato: {file_path}")
        
        return {
            'filename': unique_filename,
            'original_filename': original_filename,
            'file_path': file_path,
            'file_type': file_type,
            'file_size': file_size
        }
    except Exception as e:
        logging.error(f"Errore durante il salvataggio del documento: {str(e)}")
        return None

def get_file_path(filename):
    """
    Ottiene il percorso assoluto di un file.
    """
    if not filename:
        return None
    
    # Prova prima con il percorso completo se sembra essere assoluto
    if os.path.exists(filename) and os.path.isabs(filename):
        return filename
    
    # Altrimenti cerca nella directory uploads
    file_path = os.path.join(os.path.abspath(UPLOADS_DIR), filename)
    if os.path.exists(file_path):
        return file_path
    
    return None

def verify_document_file(document):
    """
    Verifica che il file del documento sia accessibile e restituisce un risultato.
    
    Args:
        document: Oggetto documento da verificare
        
    Returns:
        dict: Risultato della verifica con stato e messaggi
    """
    if not document:
        return {'status': 'error', 'message': 'Documento non valido'}
    
    # Verifica se il file esiste nel percorso registrato
    if document.file_path and os.path.exists(document.file_path):
        return {
            'status': 'ok',
            'message': 'Il file esiste',
            'path': document.file_path
        }
    
    # Prova a cercare nella directory uploads usando il filename
    if document.filename:
        alt_path = os.path.join(os.path.abspath(UPLOADS_DIR), document.filename)
        if os.path.exists(alt_path):
            # Aggiorna il percorso nel database
            old_path = document.file_path
            document.file_path = alt_path
            db.session.commit()
            
            logging.info(f"Percorso documento aggiornato: da {old_path} a {alt_path}")
            
            return {
                'status': 'fixed',
                'message': 'Percorso file aggiornato',
                'path': alt_path
            }
    
    # Se non è stato possibile trovare il file
    return {
        'status': 'error',
        'message': 'File non trovato',
        'path': document.file_path
    }

def extract_document_metadata(file_path, file_type):
    """
    Estrae metadati di base dal documento.
    Versione semplificata che restituisce solo il tipo di file.
    """
    return {
        'content_type': file_type,
        'page_count': None,
        'created_date': None,
        'modified_date': None,
        'author': None
    }

def get_document_preview(file_path, file_type):
    """
    Genera un'anteprima per il documento.
    Versione semplificata che restituisce solo il percorso del file.
    """
    return {
        'preview_type': 'none',
        'preview_path': None,
        'thumbnail_path': None,
        'can_preview': False
    }