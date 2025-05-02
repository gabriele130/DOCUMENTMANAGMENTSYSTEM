"""
Sistema di storage centralizzato per i documenti.

Questo modulo implementa un sistema di storage centralizzato per tutti i documenti,
con funzioni per salvare, recuperare e verificare i file.
"""

import os
import logging
import shutil
import datetime
import uuid
import json
from flask import current_app
from werkzeug.utils import secure_filename
from app import db
from models import Document

# Configurazione delle directory di storage
STORAGE_ROOT = 'document_storage'
ORIGINAL_FILES_DIR = os.path.join(STORAGE_ROOT, 'originals')
BACKUP_FILES_DIR = os.path.join(STORAGE_ROOT, 'backup')

def ensure_storage_directories():
    """
    Assicura che le directory di storage esistano.
    Crea le directory se non esistono.
    """
    os.makedirs(ORIGINAL_FILES_DIR, exist_ok=True)
    os.makedirs(BACKUP_FILES_DIR, exist_ok=True)
    
    # Log informativo
    logging.info(f"Directory storage centralizzato: {ORIGINAL_FILES_DIR} e {BACKUP_FILES_DIR}")
    return True

def generate_unique_filename(original_filename):
    """
    Genera un nome file unico per lo storage centralizzato.
    
    Args:
        original_filename: Nome file originale
        
    Returns:
        str: Nome file unico per lo storage
    """
    # Genera un UUID unico
    unique_id = str(uuid.uuid4())
    
    # Ottieni l'estensione del file originale
    if '.' in original_filename:
        base, ext = os.path.splitext(original_filename)
        # Pulisci il nome base rimuovendo caratteri problematici
        clean_base = secure_filename(base)
        # Crea un nome unico con il formato: UUID_nome-originale-pulito.estensione
        return f"{unique_id}_{clean_base}{ext}"
    else:
        # Se non c'è estensione, usa solo l'UUID e il nome pulito
        clean_name = secure_filename(original_filename)
        return f"{unique_id}_{clean_name}"

def save_file_to_central_storage(file_obj=None, file_path=None, original_filename=None, create_backup=True):
    """
    Salva un file nel sistema di storage centralizzato.
    
    Args:
        file_obj: Oggetto file da salvare (opzionale)
        file_path: Percorso del file esistente da spostare nel sistema (opzionale)
        original_filename: Nome originale del file
        create_backup: Se True, crea una copia di backup
        
    Returns:
        dict: Informazioni sul file salvato o None in caso di errore
    """
    try:
        # Controlla che almeno uno tra file_obj e file_path sia fornito
        if file_obj is None and file_path is None:
            raise ValueError("È necessario fornire o un oggetto file o un percorso di file")
        
        # Se non è specificato il nome originale, estrailo dal percorso o dall'oggetto file
        if original_filename is None:
            if file_path:
                original_filename = os.path.basename(file_path)
            elif hasattr(file_obj, 'filename'):
                original_filename = file_obj.filename
            else:
                original_filename = f"file_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Genera un nome file unico
        unique_filename = generate_unique_filename(original_filename)
        
        # Percorsi di destinazione
        destination_path = os.path.join(ORIGINAL_FILES_DIR, unique_filename)
        backup_path = os.path.join(BACKUP_FILES_DIR, unique_filename) if create_backup else None
        
        # Assicurati che le directory esistano
        ensure_storage_directories()
        
        # Salva o sposta il file nella directory principale
        if file_obj:
            file_obj.save(destination_path)
        elif file_path and os.path.exists(file_path):
            shutil.copy2(file_path, destination_path)
        else:
            raise FileNotFoundError(f"Il file {file_path} non esiste")
        
        # Crea una copia di backup se richiesto
        if create_backup and os.path.exists(destination_path):
            shutil.copy2(destination_path, backup_path)
        
        # Ottieni la dimensione del file
        file_size = os.path.getsize(destination_path)
        
        # Registra l'operazione
        logging.info(f"File salvato nel repository centralizzato: {destination_path}")
        if backup_path:
            logging.info(f"Backup creato: {backup_path}")
        
        # Restituisci le informazioni sul file
        return {
            'filename': unique_filename,
            'file_path': destination_path,
            'backup_path': backup_path,
            'file_size': file_size,
            'timestamp': datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Errore durante il salvataggio del file: {str(e)}")
        return None

def get_file_from_storage(filename, document_id=None):
    """
    Recupera un file dal sistema di storage centralizzato.
    
    Args:
        filename: Nome del file da recuperare
        document_id: ID del documento nel database (opzionale)
        
    Returns:
        str: Percorso del file recuperato o None se non trovato
    """
    try:
        # Controlla se il file esiste nella directory principale
        main_path = os.path.join(ORIGINAL_FILES_DIR, filename)
        if os.path.exists(main_path):
            return main_path
        
        # Se non esiste nella directory principale, controlla il backup
        backup_path = os.path.join(BACKUP_FILES_DIR, filename)
        if os.path.exists(backup_path):
            # Se esiste nel backup, ripristinalo nella directory principale
            shutil.copy2(backup_path, main_path)
            logging.info(f"File ripristinato dal backup: {main_path}")
            return main_path
        
        # Se abbiamo l'ID del documento, prova a cercarlo nel database
        if document_id:
            doc = Document.query.get(document_id)
            if doc and doc.file_path and os.path.exists(doc.file_path):
                # Se il file esiste nel percorso registrato, copialo nel sistema centralizzato
                unique_filename = generate_unique_filename(doc.original_filename)
                destination_path = os.path.join(ORIGINAL_FILES_DIR, unique_filename)
                backup_path = os.path.join(BACKUP_FILES_DIR, unique_filename)
                
                shutil.copy2(doc.file_path, destination_path)
                shutil.copy2(doc.file_path, backup_path)
                
                # Aggiorna il percorso nel database
                doc.file_path = destination_path
                doc.filename = unique_filename
                db.session.commit()
                
                logging.info(f"File migrato al sistema centralizzato: {destination_path}")
                return destination_path
        
        # Se non trovato in nessuna posizione, restituisci None
        logging.warning(f"File non trovato nel sistema centralizzato: {filename}")
        return None
    except Exception as e:
        logging.error(f"Errore durante il recupero del file: {str(e)}")
        return None

def verify_and_repair_storage():
    """
    Verifica e ripara eventuali problemi nello storage centralizzato.
    
    Returns:
        dict: Report della verifica e riparazione
    """
    report = {
        'verified_total': 0,
        'verified_ok': 0,
        'verified_missing': 0,
        'files_restored': 0,
        'errors': []
    }
    
    try:
        # Assicurati che le directory esistano
        ensure_storage_directories()
        
        # Ottieni tutti i documenti dal database
        documents = Document.query.filter_by(is_deleted=False).all()
        report['verified_total'] = len(documents)
        
        for doc in documents:
            try:
                # Controlla se il file esiste
                if doc.file_path and os.path.exists(doc.file_path):
                    report['verified_ok'] += 1
                else:
                    report['verified_missing'] += 1
                    
                    # Prova a recuperare il file dal backup
                    if doc.filename:
                        backup_path = os.path.join(BACKUP_FILES_DIR, doc.filename)
                        if os.path.exists(backup_path):
                            # Crea la directory di destinazione se non esiste
                            destination_dir = os.path.dirname(doc.file_path)
                            os.makedirs(destination_dir, exist_ok=True)
                            
                            # Ripristina il file dal backup
                            shutil.copy2(backup_path, doc.file_path)
                            report['files_restored'] += 1
                            logging.info(f"File ripristinato per documento ID {doc.id}: {doc.file_path}")
                        else:
                            # Se non esiste nel backup, prova a migrarlo al sistema centralizzato
                            # cercando il file in altre posizioni note
                            result = migrate_document_to_central_storage(doc)
                            if result and result.get('status') == 'migrated':
                                report['files_restored'] += 1
                            else:
                                report['errors'].append(f"Documento ID {doc.id}: File non trovato in nessuna posizione")
            except Exception as e:
                error_msg = f"Errore durante la verifica del documento ID {doc.id}: {str(e)}"
                report['errors'].append(error_msg)
                logging.error(error_msg)
        
        return report
    except Exception as e:
        error_msg = f"Errore durante la verifica dello storage: {str(e)}"
        report['errors'].append(error_msg)
        logging.error(error_msg)
        return report

def validate_document_storage(document):
    """
    Valida e ripara il storage di un singolo documento.
    
    Args:
        document: Oggetto documento da validare
        
    Returns:
        dict: Risultato della validazione
    """
    try:
        # Controlla se il file esiste nel percorso corrente
        if document.file_path and os.path.exists(document.file_path):
            return {
                'status': 'ok',
                'message': 'Il file esiste nel percorso registrato',
                'path': document.file_path
            }
        
        # Controlla se il file è già nel sistema centralizzato
        if document.filename:
            central_path = os.path.join(ORIGINAL_FILES_DIR, document.filename)
            if os.path.exists(central_path):
                # Aggiorna il percorso nel database
                document.file_path = central_path
                db.session.commit()
                return {
                    'status': 'updated',
                    'message': 'Percorso aggiornato al sistema centralizzato',
                    'path': central_path
                }
            
            # Controlla se esiste nel backup
            backup_path = os.path.join(BACKUP_FILES_DIR, document.filename)
            if os.path.exists(backup_path):
                # Ripristina il file dal backup
                destination_path = os.path.join(ORIGINAL_FILES_DIR, document.filename)
                shutil.copy2(backup_path, destination_path)
                
                # Aggiorna il percorso nel database
                document.file_path = destination_path
                db.session.commit()
                
                return {
                    'status': 'restored',
                    'message': 'File ripristinato dal backup',
                    'path': destination_path
                }
        
        # Prova a migrare il documento al sistema centralizzato
        migration_result = migrate_document_to_central_storage(document)
        if migration_result and migration_result.get('status') == 'migrated':
            return {
                'status': 'restored',
                'message': migration_result.get('message', 'File migrato al sistema centralizzato'),
                'path': migration_result.get('path')
            }
        
        # Se non è stato possibile ripristinare il file, restituisci un errore
        return {
            'status': 'error',
            'message': 'Il file non è stato trovato in nessuna posizione conosciuta'
        }
    except Exception as e:
        error_msg = f"Errore durante la validazione del documento: {str(e)}"
        logging.error(error_msg)
        return {
            'status': 'error',
            'message': error_msg
        }

def migrate_document_to_central_storage(document):
    """
    Migra un singolo documento al sistema di storage centralizzato.
    
    Args:
        document: Oggetto documento da migrare
        
    Returns:
        dict: Risultato della migrazione
    """
    try:
        # Se il documento è già nel sistema centralizzato, non fare nulla
        if document.file_path and document.file_path.startswith(ORIGINAL_FILES_DIR):
            return {
                'status': 'already_migrated',
                'message': 'Il documento è già nel sistema centralizzato',
                'path': document.file_path
            }
        
        # Se il file esiste nel percorso registrato, migralo
        if document.file_path and os.path.exists(document.file_path):
            # Genera un nome file unico
            unique_filename = generate_unique_filename(document.original_filename)
            
            # Salva il file nel sistema centralizzato
            storage_result = save_file_to_central_storage(
                file_path=document.file_path,
                original_filename=document.original_filename,
                create_backup=True
            )
            
            if storage_result:
                # Aggiorna il documento nel database
                document.filename = storage_result['filename']
                document.file_path = storage_result['file_path']
                db.session.commit()
                
                return {
                    'status': 'migrated',
                    'message': 'Documento migrato con successo',
                    'path': storage_result['file_path']
                }
        
        # Se il file non esiste nel percorso registrato, cerca in percorsi alternativi
        alternative_paths = []
        
        # Estrai nome file dalla parte finale del path
        if document.file_path:
            original_file = os.path.basename(document.file_path)
            
            # Estrai nome file senza UUID e timestamp (se presente)
            original_name_parts = original_file.split('_', 1)
            simplified_original = original_name_parts[1] if len(original_name_parts) > 1 else original_file
            
            # Liste di nomi file e directory da controllare
            alternative_filenames = [
                document.filename,
                document.original_filename,
                simplified_original,
                document.original_filename.replace(' ', '_')
            ]
            
            possible_dirs = [
                'uploads',
                'document_cache',
                'attached_assets',
                os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads'),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'document_cache'),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'attached_assets')
            ]
            
            # Genera tutte le possibili combinazioni
            for dir_path in possible_dirs:
                for filename in alternative_filenames:
                    if filename:
                        alternative_paths.append(os.path.join(dir_path, filename))
        
        # Controlla tutti i percorsi alternativi
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                # Se trovato, migra il file
                storage_result = save_file_to_central_storage(
                    file_path=alt_path,
                    original_filename=document.original_filename,
                    create_backup=True
                )
                
                if storage_result:
                    # Aggiorna il documento nel database
                    document.filename = storage_result['filename']
                    document.file_path = storage_result['file_path']
                    db.session.commit()
                    
                    return {
                        'status': 'migrated',
                        'message': f'Documento migrato da percorso alternativo: {alt_path}',
                        'path': storage_result['file_path']
                    }
        
        # Se non è stato possibile migrare il documento, restituisci un errore
        return {
            'status': 'error',
            'message': 'Impossibile trovare il file in nessuna posizione conosciuta'
        }
    except Exception as e:
        error_msg = f"Errore durante la migrazione del documento: {str(e)}"
        logging.error(error_msg)
        return {
            'status': 'error',
            'message': error_msg
        }

def migrate_files_to_central_storage(update_database=True):
    """
    Migra tutti i file dei documenti al sistema di storage centralizzato.
    
    Args:
        update_database: Se True, aggiorna i percorsi nel database
        
    Returns:
        dict: Report della migrazione
    """
    report = {
        'total_documents': 0,
        'migrated_successfully': 0,
        'already_migrated': 0,
        'migration_failed': 0,
        'errors': []
    }
    
    try:
        # Assicurati che le directory esistano
        ensure_storage_directories()
        
        # Ottieni tutti i documenti dal database
        documents = Document.query.filter_by(is_deleted=False).all()
        report['total_documents'] = len(documents)
        
        for doc in documents:
            try:
                # Controlla se il documento è già nel sistema centralizzato
                if doc.file_path and doc.file_path.startswith(ORIGINAL_FILES_DIR):
                    report['already_migrated'] += 1
                    continue
                
                # Migra il documento
                migration_result = migrate_document_to_central_storage(doc)
                
                if migration_result and migration_result.get('status') == 'migrated':
                    report['migrated_successfully'] += 1
                    logging.info(f"Documento ID {doc.id} migrato con successo")
                elif migration_result and migration_result.get('status') == 'already_migrated':
                    report['already_migrated'] += 1
                else:
                    report['migration_failed'] += 1
                    error_msg = f"Documento ID {doc.id}: {migration_result.get('message', 'Errore sconosciuto')}"
                    report['errors'].append(error_msg)
                    logging.warning(error_msg)
            except Exception as e:
                report['migration_failed'] += 1
                error_msg = f"Errore durante la migrazione del documento ID {doc.id}: {str(e)}"
                report['errors'].append(error_msg)
                logging.error(error_msg)
        
        return report
    except Exception as e:
        error_msg = f"Errore durante la migrazione dei file: {str(e)}"
        report['errors'].append(error_msg)
        logging.error(error_msg)
        return report

def get_storage_stats():
    """
    Ottiene statistiche sullo storage centralizzato.
    
    Returns:
        dict: Statistiche sullo storage
    """
    stats = {
        'total_documents': 0,
        'migrated_documents': 0,
        'total_size': 0,
        'original_files': 0,
        'backup_files': 0,
        'files_with_backup': 0,
        'avg_file_size': 0,
        'original_dir': ORIGINAL_FILES_DIR,
        'backup_dir': BACKUP_FILES_DIR
    }
    
    try:
        # Assicurati che le directory esistano
        ensure_storage_directories()
        
        # Conteggio totale documenti
        stats['total_documents'] = Document.query.filter_by(is_deleted=False).count()
        
        # Conteggio documenti migrati
        stats['migrated_documents'] = Document.query.filter(
            Document.is_deleted == False,
            Document.file_path.like(f"{ORIGINAL_FILES_DIR}%")
        ).count()
        
        # Conteggio e dimensione file nel repository principale
        original_files = []
        if os.path.exists(ORIGINAL_FILES_DIR):
            original_files = [f for f in os.listdir(ORIGINAL_FILES_DIR) if os.path.isfile(os.path.join(ORIGINAL_FILES_DIR, f))]
            stats['original_files'] = len(original_files)
            
            # Calcola la dimensione totale
            for filename in original_files:
                file_path = os.path.join(ORIGINAL_FILES_DIR, filename)
                stats['total_size'] += os.path.getsize(file_path)
        
        # Conteggio file nel repository di backup
        backup_files = []
        if os.path.exists(BACKUP_FILES_DIR):
            backup_files = [f for f in os.listdir(BACKUP_FILES_DIR) if os.path.isfile(os.path.join(BACKUP_FILES_DIR, f))]
            stats['backup_files'] = len(backup_files)
        
        # Conteggio file con backup
        for filename in original_files:
            if filename in backup_files:
                stats['files_with_backup'] += 1
        
        # Dimensione media file
        if stats['original_files'] > 0:
            stats['avg_file_size'] = stats['total_size'] / stats['original_files']
        
        return stats
    except Exception as e:
        logging.error(f"Errore durante il recupero delle statistiche dello storage: {str(e)}")
        return stats

def cleanup_orphaned_files(commit=False):
    """
    Pulisce i file orfani che non sono collegati a nessun documento nel database.
    
    Args:
        commit: Se True, elimina effettivamente i file, altrimenti fa solo una simulazione
        
    Returns:
        dict: Report della pulizia
    """
    report = {
        'identified': 0,
        'removed': 0,
        'errors': []
    }
    
    try:
        # Assicurati che le directory esistano
        ensure_storage_directories()
        
        # Ottieni tutti i nomi file registrati nel database
        db_filenames = [doc.filename for doc in Document.query.all() if doc.filename]
        
        # Controlla i file nella directory principale
        orphaned_files = []
        if os.path.exists(ORIGINAL_FILES_DIR):
            for filename in os.listdir(ORIGINAL_FILES_DIR):
                if os.path.isfile(os.path.join(ORIGINAL_FILES_DIR, filename)) and filename not in db_filenames:
                    orphaned_files.append({
                        'filename': filename,
                        'path': os.path.join(ORIGINAL_FILES_DIR, filename),
                        'size': os.path.getsize(os.path.join(ORIGINAL_FILES_DIR, filename)),
                        'directory': 'originals'
                    })
        
        # Controlla i file nella directory di backup
        if os.path.exists(BACKUP_FILES_DIR):
            for filename in os.listdir(BACKUP_FILES_DIR):
                if os.path.isfile(os.path.join(BACKUP_FILES_DIR, filename)) and filename not in db_filenames:
                    orphaned_files.append({
                        'filename': filename,
                        'path': os.path.join(BACKUP_FILES_DIR, filename),
                        'size': os.path.getsize(os.path.join(BACKUP_FILES_DIR, filename)),
                        'directory': 'backup'
                    })
        
        report['identified'] = len(orphaned_files)
        
        # Se richiesto, elimina i file orfani
        if commit and len(orphaned_files) > 0:
            for file_info in orphaned_files:
                try:
                    os.remove(file_info['path'])
                    report['removed'] += 1
                except Exception as e:
                    error_msg = f"Errore durante la rimozione del file {file_info['path']}: {str(e)}"
                    report['errors'].append(error_msg)
                    logging.error(error_msg)
        
        return report
    except Exception as e:
        error_msg = f"Errore durante la pulizia dei file orfani: {str(e)}"
        report['errors'].append(error_msg)
        logging.error(error_msg)
        return report