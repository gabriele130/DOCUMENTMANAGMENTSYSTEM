"""
Sistema di storage semplificato per i documenti.

Questo modulo implementa un sistema di storage semplice ma affidabile per tutti i documenti,
con funzioni per salvare, recuperare e verificare i file.
"""

import os
import logging
import datetime
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

# Configurazione della directory di storage principale
UPLOAD_FOLDER = 'uploads'

def save_file(file_obj, original_filename=None):
    """
    Salva un file nella cartella di upload con un nome univoco.
    
    Args:
        file_obj: L'oggetto file da salvare
        original_filename: Nome originale del file (opzionale)
        
    Returns:
        dict: Dizionario con i metadati del file salvato o None in caso di errore
    """
    try:
        if original_filename is None:
            original_filename = secure_filename(file_obj.filename)
        else:
            original_filename = secure_filename(original_filename)
        
        # Crea un nome file univoco con UUID per evitare collisioni
        # Formato: {uuid}_{timestamp}_{original_filename}
        unique_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        unique_filename = f"{unique_id}_{timestamp}_{original_filename}"
        
        # Assicura che la directory di upload esista
        upload_dir = os.path.abspath(UPLOAD_FOLDER)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Percorso completo del file
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Salva il file
        file_obj.save(file_path)
        
        # Ottieni la dimensione del file
        file_size = os.path.getsize(file_path)
        
        logging.info(f"File salvato con successo: {file_path}")
        
        # Restituisci i metadati del file
        return {
            'filename': unique_filename,
            'original_filename': original_filename,
            'file_path': file_path,
            'file_size': file_size
        }
    except Exception as e:
        logging.error(f"Errore durante il salvataggio del file: {str(e)}")
        return None

def get_file_path(filename):
    """
    Ottiene il percorso completo di un file dato il suo nome.
    
    Args:
        filename: Nome del file da cercare
        
    Returns:
        str: Percorso completo del file o None se non trovato
    """
    if not filename:
        return None
    
    file_path = os.path.join(os.path.abspath(UPLOAD_FOLDER), filename)
    
    if os.path.exists(file_path):
        return file_path
    
    return None

def file_exists(filename):
    """
    Verifica se un file esiste.
    
    Args:
        filename: Nome del file da verificare
        
    Returns:
        bool: True se il file esiste, False altrimenti
    """
    if not filename:
        return False
    
    file_path = os.path.join(os.path.abspath(UPLOAD_FOLDER), filename)
    return os.path.exists(file_path)

def delete_file(filename):
    """
    Elimina un file dal sistema di archiviazione.
    
    Args:
        filename: Nome del file da eliminare
        
    Returns:
        bool: True se l'eliminazione è riuscita, False altrimenti
    """
    try:
        if not filename:
            return False
        
        file_path = os.path.join(os.path.abspath(UPLOAD_FOLDER), filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.info(f"File eliminato: {file_path}")
            return True
        
        return False
    except Exception as e:
        logging.error(f"Errore durante l'eliminazione del file: {str(e)}")
        return False