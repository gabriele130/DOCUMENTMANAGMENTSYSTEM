"""
Script per migrare automaticamente tutti i documenti esistenti al nuovo sistema di storage centralizzato.
Questo script deve essere eseguito una sola volta per trasferire tutti i documenti dal vecchio al nuovo sistema.
"""

import os
import sys
import logging
import datetime
from app import app, db
from models import Document
from services.central_storage import (
    ensure_storage_directories,
    migrate_files_to_central_storage,
    verify_and_repair_storage
)

# Configura il logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_migration_report(report_data):
    """Crea un report di migrazione e lo salva in un file"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"migration_report_{timestamp}.txt"
    
    with open(report_filename, 'w') as f:
        f.write("=== REPORT DI MIGRAZIONE AL SISTEMA DI STORAGE CENTRALIZZATO ===\n")
        f.write(f"Data: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Scrivi i dati principali
        f.write(f"Documenti totali: {report_data['total_documents']}\n")
        f.write(f"Migrati con successo: {report_data['migrated_successfully']}\n")
        f.write(f"Già migrati: {report_data['already_migrated']}\n")
        f.write(f"Migrazione fallita: {report_data['migration_failed']}\n\n")
        
        # Scrivi eventuali errori
        if report_data['errors'] and len(report_data['errors']) > 0:
            f.write("ERRORI DURANTE LA MIGRAZIONE:\n")
            for i, error in enumerate(report_data['errors'], 1):
                f.write(f"{i}. {error}\n")
        else:
            f.write("Nessun errore durante la migrazione.\n")
            
        f.write("\n=== FINE REPORT ===\n")
    
    logger.info(f"Report di migrazione creato: {report_filename}")
    return report_filename

def main():
    """Funzione principale per avviare la migrazione"""
    try:
        logger.info("Avvio della migrazione al sistema di storage centralizzato...")
        
        # Creazione delle directory di storage
        logger.info("Creazione delle directory di storage centralizzato...")
        ensure_storage_directories()

        # Utilizziamo il contesto dell'applicazione
        with app.app_context():
            # Contiamo i documenti nel database
            doc_count = Document.query.count()
            logger.info(f"Trovati {doc_count} documenti nel database")
            
            # Avvia la migrazione
            logger.info("Migrazione dei file al sistema di storage centralizzato...")
            migration_report = migrate_files_to_central_storage(update_database=True)
            
            # Crea un report di migrazione
            report_file = create_migration_report(migration_report)
            
            # Verifica e ripara lo storage
            logger.info("Verifica e riparazione dello storage...")
            repair_report = verify_and_repair_storage()
            
            logger.info(f"Verifica completata: {repair_report['verified_ok']} documenti OK, " +
                      f"{repair_report['files_restored']} file ripristinati")
            
            logger.info("Migrazione completata con successo!")
            logger.info(f"Report di migrazione salvato in: {report_file}")
            
            if migration_report['migration_failed'] > 0:
                logger.warning(f"ATTENZIONE: {migration_report['migration_failed']} documenti non sono stati migrati correttamente!")
                logger.warning("Controlla il report per i dettagli")
                return 1
            
            return 0
    except Exception as e:
        logger.error(f"Errore durante la migrazione: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())