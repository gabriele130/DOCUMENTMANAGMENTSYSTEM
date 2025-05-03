"""
Script per migrare automaticamente tutti i documenti esistenti al nuovo sistema di storage permanente.
Questo script deve essere eseguito una sola volta per trasferire tutti i documenti dal vecchio al nuovo sistema.
"""

import os
import sys
import datetime
import logging
import json
from app import app, db
from models import Document

# Configura il logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

def create_migration_report(report_data):
    """Crea un report di migrazione e lo salva in un file"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"migration_report_{timestamp}.txt"
    
    with open(report_file, 'w') as f:
        f.write(f"== Report di Migrazione allo Storage Permanente ==\n")
        f.write(f"Data: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write(f"Totale documenti: {report_data['total']}\n")
        f.write(f"Documenti migrati con successo: {report_data['migrated']}\n")
        f.write(f"Documenti falliti: {report_data['failed']}\n\n")
        
        if report_data['failed'] > 0:
            f.write("== Dettagli Errori ==\n")
            for error in report_data['errors']:
                if 'document_id' in error:
                    f.write(f"Documento ID {error['document_id']}: {error['reason']}\n")
                else:
                    f.write(f"Errore generale: {error.get('general_error', 'Errore sconosciuto')}\n")
        
        f.write("\n== Fine Report ==\n")
    
    logging.info(f"Report di migrazione salvato in: {report_file}")
    return report_file

def main():
    """Funzione principale per avviare la migrazione"""
    logging.info("Avvio migrazione allo storage permanente...")
    
    with app.app_context():
        # Importa il servizio di storage permanente
        try:
            from services.persistent_storage import (
                ensure_storage_structure, 
                batch_migrate_to_permanent_storage,
                verify_storage_integrity
            )
        except ImportError:
            logging.error("Impossibile importare il modulo persistent_storage. Assicurarsi che esista.")
            sys.exit(1)
        
        # Prepara la struttura di storage
        logging.info("Preparazione della struttura di storage permanente...")
        ensure_storage_structure()
        
        # Conta il numero totale di documenti
        total_documents = Document.query.count()
        logging.info(f"Trovati {total_documents} documenti da migrare")
        
        # Procedi automaticamente con la migrazione
        logging.info(f"Procedo automaticamente con la migrazione di {total_documents} documenti allo storage permanente")
        
        # Esegui la migrazione in batch
        batch_size = 100
        num_batches = (total_documents + batch_size - 1) // batch_size
        
        overall_stats = {
            'total': 0,
            'migrated': 0,
            'failed': 0,
            'errors': []
        }
        
        for i in range(num_batches):
            offset = i * batch_size
            logging.info(f"Elaborazione batch {i+1}/{num_batches} (documenti {offset+1}-{min(offset+batch_size, total_documents)})")
            
            # Migra il batch corrente
            batch_stats = batch_migrate_to_permanent_storage(limit=batch_size)
            
            # Aggiorna le statistiche complessive
            overall_stats['total'] += batch_stats['total']
            overall_stats['migrated'] += batch_stats['migrated']
            overall_stats['failed'] += batch_stats['failed']
            overall_stats['errors'].extend(batch_stats['errors'])
            
            logging.info(f"Batch {i+1} completato: {batch_stats['migrated']}/{batch_stats['total']} documenti migrati")
        
        # Verifica l'integrità dello storage
        logging.info("Verifica dell'integrità dello storage permanente...")
        integrity_stats = verify_storage_integrity()
        
        # Crea il report di migrazione
        report_file = create_migration_report(overall_stats)
        
        # Stampa un riepilogo
        logging.info("==== Riepilogo Migrazione ====")
        logging.info(f"Totale documenti elaborati: {overall_stats['total']}")
        logging.info(f"Documenti migrati con successo: {overall_stats['migrated']}")
        logging.info(f"Documenti falliti: {overall_stats['failed']}")
        logging.info(f"Report salvato in: {report_file}")
        
        if overall_stats['failed'] > 0:
            logging.warning("Alcuni documenti non sono stati migrati. Consulta il report per i dettagli.")
        else:
            logging.info("Migrazione completata con successo!")

if __name__ == "__main__":
    main()