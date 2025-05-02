"""
Servizio di storage centralizzato per i documenti
Gestisce tutti i file in un'unica posizione per evitare problemi di accesso
"""

import os
import shutil
import hashlib
import logging
import datetime
from flask import current_app
from models import db, Document

# Directory principale per tutti i file
CENTRAL_STORAGE_DIR = 'document_storage'

# Sottodirectory specifiche
ORIGINAL_FILES_DIR = os.path.join(CENTRAL_STORAGE_DIR, 'originals')  # File originali
BACKUP_FILES_DIR = os.path.join(CENTRAL_STORAGE_DIR, 'backup')       # Backup automatici
VERSIONS_DIR = os.path.join(CENTRAL_STORAGE_DIR, 'versions')         # Versioni dei file

# Assicurarsi che le cartelle esistano
def ensure_storage_directories():
    """Crea tutte le directory di storage necessarie se non esistono già"""
    for directory in [CENTRAL_STORAGE_DIR, ORIGINAL_FILES_DIR, BACKUP_FILES_DIR, VERSIONS_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logging.info(f"Directory creata: {directory}")

# Funzione per salvare un file nel repository centralizzato
def save_file_to_central_storage(file_obj, original_filename, document_id=None, create_backup=True):
    """
    Salva un file nel repository centralizzato e restituisce il percorso salvato
    
    Args:
        file_obj: L'oggetto file da salvare
        original_filename: Il nome originale del file
        document_id: ID del documento associato (se esistente)
        create_backup: Se True, crea un backup immediato del file
        
    Returns:
        dict: Dizionario con i dettagli del file salvato
    """
    # Assicura che le directory esistano
    ensure_storage_directories()
    
    # Genera un hash del contenuto del file per creare un nome univoco
    file_obj.seek(0)
    file_content = file_obj.read()
    content_hash = hashlib.sha256(file_content).hexdigest()
    
    # Estrai l'estensione dal nome del file originale
    _, file_extension = os.path.splitext(original_filename)
    
    # Crea un nome univoco basato su timestamp, hash e ID documento
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{content_hash[:10]}"
    
    if document_id:
        filename += f"_doc{document_id}"
        
    filename += file_extension
    
    # Percorso completo per il file originale
    file_path = os.path.join(ORIGINAL_FILES_DIR, filename)
    
    # Salva il file
    with open(file_path, 'wb') as f:
        f.write(file_content)
    
    logging.info(f"File salvato nel repository centralizzato: {file_path}")
    
    # Crea un backup immediato se richiesto
    backup_path = None
    if create_backup:
        backup_path = os.path.join(BACKUP_FILES_DIR, filename)
        shutil.copy2(file_path, backup_path)
        logging.info(f"Backup creato: {backup_path}")
    
    # Ripristina il puntatore al file per letture successive
    file_obj.seek(0)
    
    return {
        'filename': filename,
        'original_filename': original_filename,
        'file_path': file_path,
        'backup_path': backup_path,
        'content_hash': content_hash,
        'file_size': len(file_content)
    }

# Funzione per recuperare un file dal repository
def get_file_from_storage(filename, document_id=None):
    """
    Recupera un file dal repository centralizzato
    
    Args:
        filename: Il nome del file da recuperare
        document_id: ID del documento associato (per logging)
        
    Returns:
        str: Percorso completo al file o None se non trovato
    """
    # Cerca prima nella directory principale
    file_path = os.path.join(ORIGINAL_FILES_DIR, filename)
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        logging.info(f"File trovato nel percorso originale: {file_path}")
        return file_path
    
    # Se non trovato, cerca nel backup
    backup_path = os.path.join(BACKUP_FILES_DIR, filename)
    
    if os.path.exists(backup_path) and os.path.isfile(backup_path):
        logging.warning(f"File non trovato nel percorso originale, utilizzo backup: {backup_path}")
        
        # Ripristina il file originale dal backup
        try:
            shutil.copy2(backup_path, file_path)
            logging.info(f"File ripristinato dal backup: {file_path}")
            return file_path
        except Exception as e:
            logging.error(f"Errore durante il ripristino dal backup: {str(e)}")
            return backup_path
    
    # Se ha un ID documento, prova a recuperarlo dal database
    if document_id:
        try:
            document = Document.query.get(document_id)
            if document and document.file_path and os.path.exists(document.file_path):
                logging.info(f"File trovato usando percorso dal database: {document.file_path}")
                return document.file_path
        except Exception as e:
            logging.error(f"Errore durante il recupero dal database: {str(e)}")
    
    logging.error(f"File non trovato in nessuna posizione: {filename}")
    return None

# Funzione per aggiornare un file esistente
def update_file_in_storage(file_obj, document_id, original_filename=None):
    """
    Aggiorna un file esistente nel repository centralizzato
    
    Args:
        file_obj: Il nuovo contenuto del file
        document_id: ID del documento da aggiornare
        original_filename: Nome originale del file (opzionale)
        
    Returns:
        dict: Dizionario con i dettagli del file aggiornato
    """
    try:
        # Recupera il documento dal database
        document = Document.query.get(document_id)
        if not document:
            logging.error(f"Documento non trovato: ID {document_id}")
            return None
        
        # Se non è specificato il nome del file originale, usa quello esistente
        if not original_filename:
            original_filename = document.original_filename
        
        # Crea una versione del file attuale prima di aggiornarlo
        existing_file_path = document.file_path
        if os.path.exists(existing_file_path):
            # Estrai il nome del file dal percorso
            existing_filename = os.path.basename(existing_file_path)
            
            # Crea un nome per la versione
            version_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            version_filename = f"v_{version_timestamp}_{existing_filename}"
            version_path = os.path.join(VERSIONS_DIR, version_filename)
            
            # Salva la versione precedente
            shutil.copy2(existing_file_path, version_path)
            logging.info(f"Versione precedente salvata: {version_path}")
        
        # Salva il nuovo file
        result = save_file_to_central_storage(
            file_obj=file_obj,
            original_filename=original_filename,
            document_id=document_id,
            create_backup=True
        )
        
        if result:
            # Aggiorna il record nel database
            document.filename = result['filename']
            document.file_path = result['file_path']
            document.file_size = result['file_size']
            if original_filename != document.original_filename:
                document.original_filename = original_filename
                
            document.updated_at = datetime.datetime.utcnow()
            
            db.session.commit()
            logging.info(f"Documento aggiornato: ID {document_id}, nuovo percorso: {result['file_path']}")
            
            return result
    except Exception as e:
        db.session.rollback()
        logging.error(f"Errore durante l'aggiornamento del file: {str(e)}")
    
    return None

# Funzione per eliminare un file
def delete_file_from_storage(document_id, keep_backup=True):
    """
    Elimina un file dal repository centralizzato
    
    Args:
        document_id: ID del documento da eliminare
        keep_backup: Se True, mantiene il backup anche dopo l'eliminazione
        
    Returns:
        bool: True se l'eliminazione è riuscita, False altrimenti
    """
    try:
        # Recupera il documento dal database
        document = Document.query.get(document_id)
        if not document:
            logging.error(f"Documento non trovato: ID {document_id}")
            return False
        
        # Ottieni il percorso del file
        file_path = document.file_path
        if not file_path or not os.path.exists(file_path):
            logging.warning(f"File non trovato per il documento: ID {document_id}, percorso {file_path}")
            return False
        
        # Ottieni il nome del file
        filename = os.path.basename(file_path)
        
        # Controlla se esiste un backup
        backup_path = os.path.join(BACKUP_FILES_DIR, filename)
        has_backup = os.path.exists(backup_path)
        
        # Elimina il file originale
        try:
            os.remove(file_path)
            logging.info(f"File eliminato: {file_path}")
        except Exception as e:
            logging.error(f"Errore durante l'eliminazione del file: {str(e)}")
            return False
        
        # Se richiesto, elimina anche il backup
        if not keep_backup and has_backup:
            try:
                os.remove(backup_path)
                logging.info(f"Backup eliminato: {backup_path}")
            except Exception as e:
                logging.warning(f"Errore durante l'eliminazione del backup: {str(e)}")
        
        return True
    except Exception as e:
        logging.error(f"Errore durante l'eliminazione del file: {str(e)}")
    
    return False

# Funzione per verificare e riparare lo storage
def verify_and_repair_storage():
    """
    Verifica l'integrità di tutti i file nel repository e ripara eventuali problemi
    
    Returns:
        dict: Rapporto sui file verificati e riparati
    """
    report = {
        'total_documents': 0,
        'verified_ok': 0,
        'files_missing': 0,
        'files_restored': 0,
        'files_unrepairable': 0,
        'errors': []
    }
    
    try:
        # Ottieni tutti i documenti dal database
        documents = Document.query.all()
        report['total_documents'] = len(documents)
        
        for document in documents:
            try:
                # Verifica se il file esiste
                if os.path.exists(document.file_path) and os.path.isfile(document.file_path):
                    report['verified_ok'] += 1
                    continue
                
                # Il file non esiste, tenta di ripararlo
                report['files_missing'] += 1
                
                # Ottieni il nome del file
                filename = os.path.basename(document.file_path)
                
                # Cerca nel backup
                backup_path = os.path.join(BACKUP_FILES_DIR, filename)
                if os.path.exists(backup_path) and os.path.isfile(backup_path):
                    # Ripristina dal backup
                    try:
                        target_path = os.path.join(ORIGINAL_FILES_DIR, filename)
                        shutil.copy2(backup_path, target_path)
                        
                        # Aggiorna il percorso nel database
                        document.file_path = target_path
                        db.session.commit()
                        
                        report['files_restored'] += 1
                        logging.info(f"File ripristinato dal backup: ID {document.id}, percorso {target_path}")
                    except Exception as e:
                        report['errors'].append(f"Errore durante il ripristino del documento ID {document.id}: {str(e)}")
                else:
                    report['files_unrepairable'] += 1
                    report['errors'].append(f"Documento ID {document.id} non riparabile: nessun backup trovato")
            except Exception as e:
                report['errors'].append(f"Errore durante la verifica del documento ID {document.id}: {str(e)}")
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        report['errors'].append(f"Errore generale durante la verifica: {str(e)}")
    
    return report

# Funzione per migrare i file esistenti al nuovo sistema di storage
def migrate_files_to_central_storage(update_database=True):
    """
    Migra i file esistenti dal vecchio sistema al nuovo repository centralizzato
    
    Args:
        update_database: Se True, aggiorna i percorsi nel database
    
    Returns:
        dict: Rapporto sulla migrazione
    """
    report = {
        'total_documents': 0,
        'migrated_successfully': 0,
        'migration_failed': 0,
        'already_migrated': 0,
        'errors': []
    }
    
    # Ottieni tutti i documenti dal database
    documents = Document.query.all()
    report['total_documents'] = len(documents)
    
    # Assicura che le directory esistano
    ensure_storage_directories()
    
    for document in documents:
        try:
            # Verifica se il file è già nel repository centralizzato
            if ORIGINAL_FILES_DIR in document.file_path:
                report['already_migrated'] += 1
                continue
            
            # Verifica se il file esiste
            if not os.path.exists(document.file_path) or not os.path.isfile(document.file_path):
                report['migration_failed'] += 1
                report['errors'].append(f"File non trovato: ID {document.id}, percorso {document.file_path}")
                continue
            
            # Crea un nuovo nome per il file
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            _, file_extension = os.path.splitext(document.original_filename)
            
            # Leggi il contenuto del file per generare un hash
            with open(document.file_path, 'rb') as f:
                file_content = f.read()
                content_hash = hashlib.sha256(file_content).hexdigest()
            
            # Crea il nuovo nome file
            new_filename = f"{timestamp}_{content_hash[:10]}_doc{document.id}{file_extension}"
            
            # Percorsi per il file originale e il backup
            new_file_path = os.path.join(ORIGINAL_FILES_DIR, new_filename)
            backup_path = os.path.join(BACKUP_FILES_DIR, new_filename)
            
            # Copia il file nella nuova posizione
            shutil.copy2(document.file_path, new_file_path)
            
            # Crea un backup
            shutil.copy2(document.file_path, backup_path)
            
            # Aggiorna il database se richiesto
            if update_database:
                document.filename = new_filename
                document.file_path = new_file_path
            
            report['migrated_successfully'] += 1
            logging.info(f"File migrato con successo: ID {document.id}, nuovo percorso {new_file_path}")
        except Exception as e:
            report['migration_failed'] += 1
            report['errors'].append(f"Errore durante la migrazione del documento ID {document.id}: {str(e)}")
    
    # Commit delle modifiche al database
    if update_database:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            report['errors'].append(f"Errore durante il commit delle modifiche al database: {str(e)}")
    
    return report