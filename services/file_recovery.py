import os
import shutil
import logging
from flask import current_app
from models import Document, db

logger = logging.getLogger(__name__)

# Percorso base assoluto
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Directories to search for missing files (percorsi assoluti)
SEARCH_DIRECTORIES = [
    os.path.join(BASE_DIR, 'uploads'),
    os.path.join(BASE_DIR, 'document_cache'),
    os.path.join(BASE_DIR, 'attached_assets'),
    os.path.join(BASE_DIR, 'exports'),
    os.path.join(BASE_DIR, 'document_storage', 'originals'),
    os.path.join(BASE_DIR, 'document_storage', 'backup')
]

def find_file_alternative_paths(filename):
    """
    Search for a file in multiple directories.
    
    Args:
        filename: The filename to search for
        
    Returns:
        List of full paths where the file was found
    """
    found_paths = []
    
    # Extract the UUID prefix if present
    uuid_part = None
    if '-' in filename:
        parts = filename.split('_', 1)
        if len(parts) > 1 and '-' in parts[0]:
            uuid_part = parts[0]
    
    # Original filename without UUID prefix
    original_name = filename
    if uuid_part and '_' in filename:
        original_name = filename.split('_', 1)[1] if '_' in filename else filename
    
    logger.info(f"Cercando file alternativo per: {filename}")
    logger.info(f"UUID part: {uuid_part}, Nome originale: {original_name}")
    
    for directory in SEARCH_DIRECTORIES:
        # Le directory ora sono già percorsi assoluti
        if not os.path.exists(directory):
            continue
            
        # Look for exact matches
        full_path = os.path.join(directory, filename)
        if os.path.exists(full_path):
            found_paths.append(full_path)
            logger.info(f"Trovato file esatto: {full_path}")
            
        # Look for files with the same original filename (without UUID)
        if uuid_part:
            for file in os.listdir(directory):
                if file.endswith(original_name) or original_name in file:
                    full_path = os.path.join(directory, file)
                    if full_path not in found_paths:
                        found_paths.append(full_path)
                        logger.info(f"Trovato file con nome originale: {full_path}")
                        
        # Look for files with the same UUID prefix
        if uuid_part:
            for file in os.listdir(directory):
                if file.startswith(uuid_part):
                    full_path = os.path.join(directory, file)
                    if full_path not in found_paths:
                        found_paths.append(full_path)
                        logger.info(f"Trovato file con UUID uguale: {full_path}")
    
    return found_paths

def recover_missing_file(document):
    """
    Try to recover a missing file by:
    1. Searching in alternative directories
    2. Restoring from backup
    3. Updating the database with the new path
    
    Args:
        document: The Document object with missing file
        
    Returns:
        bool: True if file was recovered, False otherwise
    """
    if not document:
        return False
        
    # Check if the current path exists
    if os.path.exists(document.file_path):
        return True
    
    logger.warning(f"File mancante: {document.file_path} per documento ID: {document.id}")
    
    # Extract filename from the path
    filename = os.path.basename(document.file_path)
    
    # Search for alternative paths
    alternative_paths = find_file_alternative_paths(filename)
    
    if alternative_paths:
        # If we found alternatives, use the first one
        new_path = alternative_paths[0]
        
        # Ensure the central storage directory exists (è preferibile salvare nel central storage)
        from services.central_storage import ORIGINAL_FILES_DIR, ensure_storage_directories
        
        # Assicurati che le directory esistano
        ensure_storage_directories()
        
        # Copy the file to the central storage directory
        filename = os.path.basename(new_path)
        destination = os.path.join(ORIGINAL_FILES_DIR, filename)
        
        logger.info(f"Copiando file da {new_path} a {destination}")
        try:
            shutil.copy2(new_path, destination)
            new_path = destination
            
            # Crea anche un backup
            from services.central_storage import BACKUP_FILES_DIR
            backup_destination = os.path.join(BACKUP_FILES_DIR, filename)
            shutil.copy2(new_path, backup_destination)
            logger.info(f"Creato backup del file in: {backup_destination}")
        except Exception as e:
            logger.error(f"Errore durante la copia del file: {e}")
        
        # Update the document record
        old_path = document.file_path
        document.file_path = new_path
        db.session.commit()
        
        logger.info(f"Documento ID {document.id} aggiornato con nuovo percorso: {new_path} (vecchio: {old_path})")
        return True
    
    logger.error(f"Non è stato possibile recuperare il file per documento ID: {document.id}")
    return False

def verify_document_file_exists(document_id):
    """
    Verify that a document's file exists, attempt recovery if not
    
    Args:
        document_id: ID of the document to verify
    
    Returns:
        tuple: (found_status, file_path)
            found_status: 
                - 'original': original file exists
                - 'recovered': file was recovered from backup
                - 'not_found': file could not be found
            file_path: path to the file if found, None otherwise
    """
    document = Document.query.get(document_id)
    
    if not document:
        return 'not_found', None
    
    # Check if the original file exists
    if os.path.exists(document.file_path):
        return 'original', document.file_path
    
    # Try to recover the file
    if recover_missing_file(document):
        return 'recovered', document.file_path
    
    return 'not_found', None