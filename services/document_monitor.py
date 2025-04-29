import os
import logging
from models import Document, db, ActivityLog
from services.file_recovery import recover_missing_file
from services.audit_service import log_activity

logger = logging.getLogger(__name__)

def verify_before_access(document_id, user_id):
    """
    Verifica che il file esista prima dell'accesso e tenta di recuperarlo se mancante.
    
    Args:
        document_id: ID del documento da verificare
        user_id: ID dell'utente che sta tentando di accedere
        
    Returns:
        tuple: (document, status_code, message)
            - document: Oggetto Document o None se non trovato
            - status_code: 200 = success, 404 = non trovato, 500 = errore, 409 = recuperato
            - message: Messaggio informativo
    """
    document = Document.query.get(document_id)
    
    if not document:
        return None, 404, "Documento non trovato nel database."
    
    # Verifica se il file esiste nel percorso originale
    if os.path.exists(document.file_path) and os.path.isfile(document.file_path):
        # Il file esiste, registra l'accesso
        log_activity(
            user_id=user_id,
            action='view',
            document_id=document.id,
            action_category='ACCESS',
            details="Accesso al documento",
            result='success'
        )
        return document, 200, "File disponibile"
    
    # File mancante, tenta di recuperarlo
    logger.warning(f"File mancante: {document.file_path} per documento ID: {document.id}, tentativo di recupero...")
    
    # Tenta di recuperare il file
    if recover_missing_file(document):
        # File recuperato con successo
        log_activity(
            user_id=user_id,
            action='recover_file',
            document_id=document.id,
            action_category='MAINTENANCE',
            details=f"File recuperato automaticamente durante l'accesso: {document.file_path}",
            result='success'
        )
        return document, 409, "File recuperato automaticamente da un backup"
    
    # Non è stato possibile recuperare il file
    log_activity(
        user_id=user_id,
        action='view',
        document_id=document.id,
        action_category='ACCESS',
        details="Tentativo di accesso a file mancante",
        result='failure'
    )
    return document, 500, "Il file non è disponibile e non è stato possibile recuperarlo automaticamente."

def check_missing_files(limit=100):
    """
    Verifica documenti con file mancanti e tenta di recuperarli
    
    Args:
        limit: Numero massimo di documenti da verificare
        
    Returns:
        dict: Statistiche sul risultato dell'operazione
    """
    documents = Document.query.limit(limit).all()
    
    stats = {
        'total': len(documents),
        'missing': 0,
        'recovered': 0,
        'still_missing': 0
    }
    
    for doc in documents:
        if not os.path.exists(doc.file_path) or not os.path.isfile(doc.file_path):
            stats['missing'] += 1
            
            if recover_missing_file(doc):
                stats['recovered'] += 1
            else:
                stats['still_missing'] += 1
    
    return stats