"""
Servizio per lo storage persistente dei file.

Questo modulo implementa un sistema di storage che garantisce la persistenza dei file
anche su periodi molto lunghi (mesi, anni). Utilizza molteplici strategie di persistenza
e recupero automatico per assicurare che nessun file venga mai perso.
"""

import os
import logging
import shutil
import datetime
import json
import uuid
import base64
from flask import current_app
from werkzeug.utils import secure_filename
from models import Document, db

# Configurazione dei percorsi assoluti per lo storage
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Directory principale per lo storage permanente
PERMANENT_STORAGE_ROOT = os.path.join(BASE_DIR, 'permanent_storage')
PERMANENT_ORIGINALS_DIR = os.path.join(PERMANENT_STORAGE_ROOT, 'originals')
PERMANENT_BACKUP_DIR = os.path.join(PERMANENT_STORAGE_ROOT, 'backup')

# Directory secondarie (per ridondanza)
SECONDARY_STORAGE_DIRS = [
    os.path.join(BASE_DIR, 'document_storage', 'originals'),
    os.path.join(BASE_DIR, 'document_storage', 'backup'),
    os.path.join(BASE_DIR, 'uploads'),
    os.path.join(BASE_DIR, 'document_cache')
]

# File di indice per il monitoraggio dei file
STORAGE_INDEX_FILE = os.path.join(PERMANENT_STORAGE_ROOT, 'storage_index.json')

def ensure_storage_structure():
    """
    Crea tutte le directory necessarie per lo storage permanente e inizializza l'indice.
    """
    # Crea le directory principali di storage permanente
    os.makedirs(PERMANENT_ORIGINALS_DIR, exist_ok=True)
    os.makedirs(PERMANENT_BACKUP_DIR, exist_ok=True)
    
    # Crea le directory secondarie
    for directory in SECONDARY_STORAGE_DIRS:
        os.makedirs(directory, exist_ok=True)
    
    # Verifica e inizializza il file di indice se non esiste
    if not os.path.exists(STORAGE_INDEX_FILE):
        with open(STORAGE_INDEX_FILE, 'w') as f:
            json.dump({
                'files': {},
                'last_updated': datetime.datetime.now().isoformat(),
                'stats': {
                    'total_files': 0,
                    'total_size': 0
                }
            }, f, indent=2)
    
    logging.info(f"Sistema di storage permanente inizializzato in: {PERMANENT_STORAGE_ROOT}")
    return True

def update_storage_index(filename, file_info):
    """
    Aggiorna l'indice di storage con le informazioni di un file.
    
    Args:
        filename: Il nome del file da aggiornare nell'indice
        file_info: Dizionario con le informazioni sul file
    
    Returns:
        bool: True se l'aggiornamento è riuscito, False altrimenti
    """
    try:
        # Assicurati che l'indice esista
        ensure_storage_structure()
        
        # Leggi l'indice attuale
        with open(STORAGE_INDEX_FILE, 'r') as f:
            index = json.load(f)
        
        # Aggiungi o aggiorna le informazioni sul file
        index['files'][filename] = file_info
        
        # Aggiorna le statistiche
        index['last_updated'] = datetime.datetime.now().isoformat()
        index['stats']['total_files'] = len(index['files'])
        
        # Calcola la dimensione totale
        total_size = 0
        for file_data in index['files'].values():
            total_size += file_data.get('size', 0)
        index['stats']['total_size'] = total_size
        
        # Salva l'indice aggiornato
        with open(STORAGE_INDEX_FILE, 'w') as f:
            json.dump(index, f, indent=2)
        
        return True
    except Exception as e:
        logging.error(f"Errore durante l'aggiornamento dell'indice di storage: {str(e)}")
        return False

def get_file_info_from_index(filename):
    """
    Ottiene le informazioni su un file dall'indice di storage.
    
    Args:
        filename: Il nome del file da cercare
        
    Returns:
        dict: Le informazioni sul file o None se non trovato
    """
    try:
        if not os.path.exists(STORAGE_INDEX_FILE):
            return None
        
        with open(STORAGE_INDEX_FILE, 'r') as f:
            index = json.load(f)
        
        return index['files'].get(filename)
    except Exception as e:
        logging.error(f"Errore durante la lettura dell'indice di storage: {str(e)}")
        return None

def generate_unique_filename(original_filename):
    """
    Genera un nome file unico per lo storage permanente.
    
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

def store_permanent_file(file_obj=None, file_path=None, original_filename=None, document_id=None):
    """
    Archivia un file nel sistema di storage permanente con ridondanza multipla.
    
    Args:
        file_obj: Oggetto file Flask (opzionale)
        file_path: Percorso a un file esistente (opzionale)
        original_filename: Nome originale del file
        document_id: ID del documento associato (opzionale)
        
    Returns:
        dict: Informazioni sul file archiviato o None in caso di errore
    """
    try:
        # Verifica che sia fornito almeno un oggetto file o un percorso
        if file_obj is None and file_path is None:
            raise ValueError("È necessario fornire o un oggetto file o un percorso file")
        
        # Se non è fornito il nome originale, ricavalo dal file
        if original_filename is None:
            if file_path:
                original_filename = os.path.basename(file_path)
            elif hasattr(file_obj, 'filename'):
                original_filename = file_obj.filename
            else:
                original_filename = f"file_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Genera un nome file unico
        unique_filename = generate_unique_filename(original_filename)
        
        # Assicura che la struttura di storage esista
        ensure_storage_structure()
        
        # Percorsi per lo storage del file
        primary_path = os.path.join(PERMANENT_ORIGINALS_DIR, unique_filename)
        backup_path = os.path.join(PERMANENT_BACKUP_DIR, unique_filename)
        
        # Archivia il file nella posizione primaria
        if file_obj:
            file_obj.save(primary_path)
        elif file_path and os.path.exists(file_path):
            shutil.copy2(file_path, primary_path)
        else:
            raise FileNotFoundError(f"Il file {file_path} non esiste")
        
        # Verifica che il file sia stato salvato correttamente
        if not os.path.exists(primary_path):
            raise IOError(f"Il file non è stato salvato correttamente in {primary_path}")
        
        # Ottieni informazioni sul file
        file_size = os.path.getsize(primary_path)
        file_type = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'unknown'
        
        # Crea copie di backup in tutte le posizioni secondarie
        backup_copies = []
        
        # Prima copia nella directory di backup principale
        shutil.copy2(primary_path, backup_path)
        backup_copies.append(backup_path)
        
        # Copie aggiuntive nelle directory secondarie
        for dir_path in SECONDARY_STORAGE_DIRS:
            if os.path.exists(dir_path):
                secondary_path = os.path.join(dir_path, unique_filename)
                try:
                    shutil.copy2(primary_path, secondary_path)
                    backup_copies.append(secondary_path)
                except Exception as e:
                    logging.warning(f"Impossibile creare copia in {dir_path}: {str(e)}")
        
        # Prepara i dettagli del file per l'indice
        file_details = {
            'original_filename': original_filename,
            'storage_filename': unique_filename,
            'primary_path': primary_path,
            'backup_paths': backup_copies,
            'size': file_size,
            'type': file_type,
            'document_id': document_id,
            'created_at': datetime.datetime.now().isoformat(),
            'checksum': calculate_file_checksum(primary_path)
        }
        
        # Aggiorna l'indice di storage
        update_storage_index(unique_filename, file_details)
        
        # Log del salvataggio
        logging.info(f"File archiviato permanentemente: {unique_filename} ({len(backup_copies)} copie di backup)")
        
        return {
            'filename': unique_filename,
            'original_filename': original_filename,
            'file_path': primary_path,
            'file_type': file_type,
            'file_size': file_size,
            'backup_paths': backup_copies
        }
    except Exception as e:
        logging.error(f"Errore durante l'archiviazione permanente del file: {str(e)}")
        return None

def calculate_file_checksum(file_path):
    """
    Calcola un checksum semplice per un file.
    
    Args:
        file_path: Percorso del file
        
    Returns:
        str: Checksum del file
    """
    try:
        import hashlib
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            buf = f.read(65536)  # Leggi in blocchi da 64k
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except Exception as e:
        logging.error(f"Errore durante il calcolo del checksum: {str(e)}")
        return None

def get_permanent_file(filename=None, document_id=None):
    """
    Recupera un file dallo storage permanente, con meccanismi avanzati di recupero automatico.
    
    Args:
        filename: Nome del file nello storage
        document_id: ID del documento (alternativo al filename)
        
    Returns:
        str: Percorso al file recuperato o None se non trovato
    """
    try:
        # Se abbiamo solo l'ID del documento, ottieni il filename dal database
        if filename is None and document_id is not None:
            document = Document.query.get(document_id)
            if document and document.filename:
                filename = document.filename
            else:
                return None
        
        if not filename:
            return None
        
        # Assicurati che la struttura di storage esista
        ensure_storage_structure()
        
        # 1. Prova nel percorso principale
        primary_path = os.path.join(PERMANENT_ORIGINALS_DIR, filename)
        if os.path.exists(primary_path) and os.path.isfile(primary_path):
            logging.debug(f"File trovato nel percorso principale: {primary_path}")
            
            # Verifica integrità tramite checksum
            file_info = get_file_info_from_index(filename)
            if file_info and file_info.get('checksum'):
                current_checksum = calculate_file_checksum(primary_path)
                if current_checksum != file_info['checksum']:
                    logging.warning(f"Checksum non corrispondente per {filename}. Tentativo di ripristino...")
                    # Se il checksum non corrisponde, prova a ripristinare da un backup
                    primary_path = restore_from_backup(filename)
            
            # Se il file esiste e passa i controlli, restituisci il percorso
            if os.path.exists(primary_path):
                return primary_path
        
        # 2. Se non trovato nel percorso principale, prova a ripristinarlo dai backup
        restored_path = restore_from_backup(filename)
        if restored_path:
            logging.info(f"File ripristinato da backup: {restored_path}")
            return restored_path
        
        # 3. Cerca in tutti i percorsi conosciuti nel sistema
        search_result = search_file_in_all_paths(filename)
        if search_result:
            logging.info(f"File trovato in percorso alternativo: {search_result}")
            # Ripristina il file nel percorso principale e aggiorna l'indice
            try:
                shutil.copy2(search_result, primary_path)
                
                # Aggiorna l'indice di storage
                file_details = {
                    'original_filename': os.path.basename(search_result),
                    'storage_filename': filename,
                    'primary_path': primary_path,
                    'backup_paths': [search_result],
                    'size': os.path.getsize(primary_path),
                    'type': filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown',
                    'document_id': document_id,
                    'restored_at': datetime.datetime.now().isoformat(),
                    'restored_from': search_result,
                    'checksum': calculate_file_checksum(primary_path)
                }
                update_storage_index(filename, file_details)
                
                return primary_path
            except Exception as e:
                logging.error(f"Errore durante il ripristino del file: {str(e)}")
                # Se il ripristino fallisce, restituisci comunque il percorso alternativo
                return search_result
        
        # 4. Se il documento esiste nel database, verifica altri percorsi registrati
        if document_id:
            document = Document.query.get(document_id)
            if document and document.file_path and os.path.exists(document.file_path):
                # Trovato nel percorso registrato nel database
                logging.info(f"File trovato nel percorso registrato nel database: {document.file_path}")
                
                # Copialo nel sistema permanente
                try:
                    shutil.copy2(document.file_path, primary_path)
                    file_details = {
                        'original_filename': document.original_filename,
                        'storage_filename': filename,
                        'primary_path': primary_path,
                        'backup_paths': [document.file_path],
                        'size': os.path.getsize(primary_path),
                        'type': document.file_type,
                        'document_id': document_id,
                        'restored_at': datetime.datetime.now().isoformat(),
                        'restored_from': document.file_path,
                        'checksum': calculate_file_checksum(primary_path)
                    }
                    update_storage_index(filename, file_details)
                    
                    # Aggiorna il percorso del documento se necessario
                    if document.file_path != primary_path:
                        document.file_path = primary_path
                        db.session.commit()
                    
                    return primary_path
                except Exception as e:
                    logging.error(f"Errore durante il recupero dal database: {str(e)}")
                    # Se il ripristino fallisce, restituisci comunque il percorso originale
                    return document.file_path
        
        # 5. Se tutte le strategie falliscono, cerca in tutto il filesystem
        find_command = f"find {BASE_DIR} -name '{filename}' 2>/dev/null"
        try:
            import subprocess
            result = subprocess.run(find_command, shell=True, capture_output=True, text=True)
            if result.stdout.strip():
                found_path = result.stdout.strip().split('\n')[0]  # Prendi solo il primo risultato
                logging.info(f"File trovato con ricerca nel filesystem: {found_path}")
                
                # Ripristina il file nel percorso principale
                try:
                    shutil.copy2(found_path, primary_path)
                    file_details = {
                        'original_filename': os.path.basename(found_path),
                        'storage_filename': filename,
                        'primary_path': primary_path,
                        'backup_paths': [found_path],
                        'size': os.path.getsize(primary_path),
                        'type': filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown',
                        'document_id': document_id,
                        'restored_at': datetime.datetime.now().isoformat(),
                        'restored_from': found_path,
                        'checksum': calculate_file_checksum(primary_path)
                    }
                    update_storage_index(filename, file_details)
                    
                    # Aggiorna il documento nel database se esiste
                    if document_id:
                        document = Document.query.get(document_id)
                        if document:
                            document.file_path = primary_path
                            db.session.commit()
                    
                    return primary_path
                except Exception as e:
                    logging.error(f"Errore durante il ripristino del file: {str(e)}")
                    # Se il ripristino fallisce, restituisci comunque il percorso trovato
                    return found_path
        except Exception as e:
            logging.error(f"Errore durante la ricerca nel filesystem: {str(e)}")
        
        # File non trovato con nessun metodo
        logging.warning(f"File non trovato in nessuna posizione: {filename}")
        return None
    except Exception as e:
        logging.error(f"Errore durante il recupero del file: {str(e)}")
        return None

def restore_from_backup(filename):
    """
    Tenta di ripristinare un file dai backup disponibili.
    
    Args:
        filename: Nome del file da ripristinare
        
    Returns:
        str: Percorso al file ripristinato o None se non trovato
    """
    # Percorso nella directory principale
    primary_path = os.path.join(PERMANENT_ORIGINALS_DIR, filename)
    
    # 1. Prima prova nella directory di backup principale
    backup_path = os.path.join(PERMANENT_BACKUP_DIR, filename)
    if os.path.exists(backup_path) and os.path.isfile(backup_path):
        try:
            shutil.copy2(backup_path, primary_path)
            logging.info(f"File ripristinato dalla directory di backup principale: {backup_path}")
            return primary_path
        except Exception as e:
            logging.error(f"Errore durante il ripristino dal backup principale: {str(e)}")
    
    # 2. Prova nelle directory secondarie
    for dir_path in SECONDARY_STORAGE_DIRS:
        secondary_path = os.path.join(dir_path, filename)
        if os.path.exists(secondary_path) and os.path.isfile(secondary_path):
            try:
                shutil.copy2(secondary_path, primary_path)
                logging.info(f"File ripristinato dalla directory secondaria: {secondary_path}")
                return primary_path
            except Exception as e:
                logging.error(f"Errore durante il ripristino dalla directory secondaria: {str(e)}")
    
    # 3. Cerca nell'indice di storage per informazioni sui percorsi di backup
    file_info = get_file_info_from_index(filename)
    if file_info and 'backup_paths' in file_info:
        for backup_path in file_info['backup_paths']:
            if os.path.exists(backup_path) and os.path.isfile(backup_path):
                try:
                    shutil.copy2(backup_path, primary_path)
                    logging.info(f"File ripristinato dal percorso registrato nell'indice: {backup_path}")
                    return primary_path
                except Exception as e:
                    logging.error(f"Errore durante il ripristino dal percorso nell'indice: {str(e)}")
    
    return None

def search_file_in_all_paths(filename):
    """
    Cerca un file in tutti i percorsi noti del sistema.
    
    Args:
        filename: Nome del file da cercare
        
    Returns:
        str: Percorso al file se trovato, altrimenti None
    """
    # Lista di tutti i percorsi da controllare
    all_paths = [
        PERMANENT_ORIGINALS_DIR,
        PERMANENT_BACKUP_DIR
    ] + SECONDARY_STORAGE_DIRS + [
        os.path.join(BASE_DIR, 'uploads'),
        os.path.join(BASE_DIR, 'document_cache'),
        os.path.join(BASE_DIR, 'attached_assets'),
        os.path.join(BASE_DIR, 'exports')
    ]
    
    # Cerca il file esatto
    for dir_path in all_paths:
        if os.path.exists(dir_path):
            full_path = os.path.join(dir_path, filename)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                return full_path
    
    # Cerca file con parti del nome (UUID o nome originale)
    uuid_part = None
    if '_' in filename:
        uuid_part = filename.split('_', 1)[0]
    
    original_name = None
    if '_' in filename:
        original_name = filename.split('_', 1)[1]
    
    if uuid_part or original_name:
        for dir_path in all_paths:
            if os.path.exists(dir_path):
                for file in os.listdir(dir_path):
                    if uuid_part and file.startswith(uuid_part):
                        return os.path.join(dir_path, file)
                    elif original_name and original_name in file:
                        return os.path.join(dir_path, file)
    
    return None

def verify_and_repair_document(document):
    """
    Verifica e ripara il file di un documento, assicurando che sia accessibile.
    
    Args:
        document: Oggetto Document da verificare
        
    Returns:
        dict: Risultato dell'operazione con stato e messaggio
    """
    if not document:
        return {'status': 'error', 'message': 'Documento non valido'}
    
    # Verifica se il file esiste nel percorso registrato
    if document.file_path and os.path.exists(document.file_path):
        return {
            'status': 'ok',
            'message': 'Il file esiste nel percorso registrato',
            'path': document.file_path
        }
    
    # Tenta di recuperare il file dallo storage permanente
    if document.filename:
        permanent_path = get_permanent_file(document.filename, document.id)
        if permanent_path:
            # Aggiorna il percorso nel database
            if document.file_path != permanent_path:
                document.file_path = permanent_path
                db.session.commit()
            
            return {
                'status': 'restored',
                'message': 'File recuperato dallo storage permanente',
                'path': permanent_path
            }
    
    # Se il file non è stato trovato, cerca alternative basate sul nome originale
    if document.original_filename:
        # Cerca in tutte le directory conosciute
        search_result = search_file_in_all_paths(document.original_filename)
        if search_result:
            # Salva il file nello storage permanente
            result = store_permanent_file(
                file_path=search_result,
                original_filename=document.original_filename,
                document_id=document.id
            )
            
            if result:
                # Aggiorna il documento nel database
                document.filename = result['filename']
                document.file_path = result['file_path']
                db.session.commit()
                
                return {
                    'status': 'migrated',
                    'message': 'File migrato allo storage permanente',
                    'path': result['file_path']
                }
    
    # Nessun metodo ha funzionato
    return {
        'status': 'failed',
        'message': 'Impossibile recuperare il file con nessun metodo',
        'path': None
    }

def migrate_document_to_permanent_storage(document):
    """
    Migra un documento esistente al sistema di storage permanente.
    
    Args:
        document: Oggetto Document da migrare
        
    Returns:
        dict: Risultato dell'operazione con stato e messaggio
    """
    try:
        # Verifica che il documento sia valido
        if not document:
            return {'status': 'error', 'message': 'Documento non valido'}
        
        # Se il file esiste, spostalo allo storage permanente
        if document.file_path and os.path.exists(document.file_path):
            result = store_permanent_file(
                file_path=document.file_path,
                original_filename=document.original_filename,
                document_id=document.id
            )
            
            if result:
                # Aggiorna il documento nel database
                old_path = document.file_path
                document.filename = result['filename']
                document.file_path = result['file_path']
                db.session.commit()
                
                logging.info(f"Documento ID {document.id} migrato allo storage permanente: {old_path} -> {result['file_path']}")
                
                return {
                    'status': 'migrated',
                    'message': 'Documento migrato allo storage permanente',
                    'old_path': old_path,
                    'new_path': result['file_path']
                }
        
        # Se il file non esiste nel percorso registrato, cerca alternative
        verification_result = verify_and_repair_document(document)
        if verification_result['status'] in ['ok', 'restored', 'migrated']:
            return verification_result
        
        return {
            'status': 'failed',
            'message': 'Impossibile migrare il documento: file non trovato'
        }
    except Exception as e:
        logging.error(f"Errore durante la migrazione del documento: {str(e)}")
        return {
            'status': 'error',
            'message': f"Errore durante la migrazione: {str(e)}"
        }

def batch_migrate_to_permanent_storage(limit=100):
    """
    Migra in batch tutti i documenti al sistema di storage permanente.
    
    Args:
        limit: Numero massimo di documenti da migrare
        
    Returns:
        dict: Statistiche sull'operazione di migrazione
    """
    stats = {
        'total': 0,
        'migrated': 0,
        'failed': 0,
        'errors': []
    }
    
    try:
        # Recupera tutti i documenti dal database (con limite)
        documents = Document.query.limit(limit).all()
        stats['total'] = len(documents)
        
        for doc in documents:
            try:
                # Tenta di migrare il documento
                result = migrate_document_to_permanent_storage(doc)
                
                if result['status'] in ['migrated', 'ok', 'restored']:
                    stats['migrated'] += 1
                else:
                    stats['failed'] += 1
                    stats['errors'].append({
                        'document_id': doc.id,
                        'reason': result['message']
                    })
            except Exception as e:
                stats['failed'] += 1
                stats['errors'].append({
                    'document_id': doc.id,
                    'reason': str(e)
                })
        
        return stats
    except Exception as e:
        logging.error(f"Errore durante la migrazione batch: {str(e)}")
        stats['errors'].append({'general_error': str(e)})
        return stats

def verify_storage_integrity(limit=100):
    """
    Verifica l'integrità dello storage permanente e ripara eventuali problemi.
    
    Args:
        limit: Numero massimo di file da verificare
        
    Returns:
        dict: Statistiche sulla verifica di integrità
    """
    stats = {
        'total': 0,
        'ok': 0,
        'repaired': 0,
        'failed': 0,
        'errors': []
    }
    
    try:
        # Leggi l'indice di storage
        if not os.path.exists(STORAGE_INDEX_FILE):
            return {'status': 'error', 'message': 'Indice di storage non trovato'}
        
        with open(STORAGE_INDEX_FILE, 'r') as f:
            index = json.load(f)
        
        # Verifica un numero limitato di file
        files_to_check = list(index['files'].keys())[:limit]
        stats['total'] = len(files_to_check)
        
        for filename in files_to_check:
            file_info = index['files'][filename]
            primary_path = file_info.get('primary_path')
            
            # Verifica se il file principale esiste e ha il checksum corretto
            if primary_path and os.path.exists(primary_path):
                if 'checksum' in file_info:
                    current_checksum = calculate_file_checksum(primary_path)
                    if current_checksum == file_info['checksum']:
                        stats['ok'] += 1
                    else:
                        # Checksum non corrispondente, tenta il ripristino
                        restored_path = restore_from_backup(filename)
                        if restored_path:
                            stats['repaired'] += 1
                        else:
                            stats['failed'] += 1
                            stats['errors'].append({
                                'filename': filename,
                                'reason': 'Checksum non corrispondente e impossibile ripristinare'
                            })
                else:
                    # Nessun checksum, considera il file valido
                    stats['ok'] += 1
            else:
                # File principale non trovato, tenta il ripristino
                restored_path = restore_from_backup(filename)
                if restored_path:
                    stats['repaired'] += 1
                else:
                    stats['failed'] += 1
                    stats['errors'].append({
                        'filename': filename,
                        'reason': 'File principale non trovato e impossibile ripristinare'
                    })
        
        return stats
    except Exception as e:
        logging.error(f"Errore durante la verifica dell'integrità: {str(e)}")
        stats['errors'].append({'general_error': str(e)})
        return stats