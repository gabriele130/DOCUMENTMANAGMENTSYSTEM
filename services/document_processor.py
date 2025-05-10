"""
Servizio di elaborazione documenti.
Questa è una versione semplificata che utilizza il nuovo sistema di storage.
"""

import os
import datetime
import logging
from flask import current_app
from werkzeug.utils import secure_filename

# Funzioni importate dal sistema di storage semplificato
from services.simple_document_storage import save_document as simple_save_document
from services.simple_document_storage import allowed_file, get_file_path, verify_document_file
from services.simple_document_storage import extract_document_metadata, get_document_preview

def save_document(file, owner_id):
    """
    Salva un documento utilizzando il sistema di storage semplificato
    e restituisce i metadati del file salvato.
    
    Args:
        file: L'oggetto file da salvare
        owner_id: ID dell'utente proprietario
        
    Returns:
        dict: Dizionario con i metadati del file salvato
    """
    try:
        # Utilizza il sistema di storage semplificato
        result = simple_save_document(file, owner_id)
        if result:
            logging.info(f"Documento salvato con successo: {result['file_path']}")
        else:
            logging.error("Errore durante il salvataggio del documento")
        return result
    except Exception as e:
        logging.error(f"Errore durante il salvataggio del documento: {str(e)}")
        return None