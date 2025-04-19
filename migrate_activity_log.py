"""
Script per aggiornare la tabella activity_log con nuove colonne
per supportare l'audit trail avanzato.
"""

import os
import sys
from app import app, db
from models import ActivityLog
from sqlalchemy import text

# Definizione delle nuove colonne da aggiungere
NEW_COLUMNS = [
    ("action_category", "VARCHAR(50)"),
    ("context_metadata", "TEXT"),
    ("result", "VARCHAR(20)"),
    ("user_agent", "VARCHAR(256)"),
    ("device_info", "VARCHAR(256)"),
    ("geolocation", "VARCHAR(150)"),
    ("record_hash", "VARCHAR(256)"),
    ("security_level", "VARCHAR(20)"),
    ("verified", "BOOLEAN")
]

def create_column_if_not_exists(column_name, column_type):
    """Aggiunge una colonna se non esiste già nella tabella."""
    # Usa text() per dichiarare esplicitamente le query SQL
    query = text(f"""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name='activity_log' AND column_name='{column_name}';
    """)
    
    result = db.session.execute(query).fetchone()
    
    if not result:
        print(f"Aggiunta colonna {column_name}...")
        alter_query = text(f"ALTER TABLE activity_log ADD COLUMN {column_name} {column_type};")
        db.session.execute(alter_query)
        return True
    else:
        print(f"Colonna {column_name} già esistente.")
        return False

def update_record_hashes():
    """Aggiorna gli hash di integrità per i record esistenti."""
    logs = ActivityLog.query.all()
    updated = 0
    
    for log in logs:
        # Calcola e salva l'hash di integrità
        log.record_hash = log.calculate_hash()
        # Imposta il livello di sicurezza in base all'azione
        if log.action in ['delete', 'share', 'unshare', 'login', 'logout', 'password_change']:
            log.security_level = 'sensitive'
        elif log.action in ['permission_change', 'user_creation', 'user_deletion']:
            log.security_level = 'critical'
        else:
            log.security_level = 'standard'
        
        # Imposta la categoria dell'azione
        if log.action in ['view', 'download', 'print', 'view_content', 'view_folder']:
            log.action_category = 'ACCESS'
        elif log.action in ['upload', 'create', 'update', 'delete', 'archive', 'unarchive', 'create_folder', 'create_reminder']:
            log.action_category = 'CRUD'
        elif log.action in ['share', 'unshare', 'login', 'logout', 'password_change']:
            log.action_category = 'SECURITY'
        elif log.action in ['permission_change', 'user_creation', 'user_deletion', 'user_suspension']:
            log.action_category = 'ADMIN'
        else:
            log.action_category = 'OTHER'
            
        # Imposta il risultato predefinito come successo
        if not log.result:
            log.result = 'success'
            
        # Marca come verificato
        log.verified = True
        
        updated += 1
    
    db.session.commit()
    print(f"Aggiornati {updated} record con hash di integrità e metadati.")

def main():
    """Funzione principale per la migrazione."""
    with app.app_context():
        print("Avvio migrazione della tabella activity_log...")
        
        # Aggiungi le nuove colonne
        columns_added = 0
        for column_name, column_type in NEW_COLUMNS:
            if create_column_if_not_exists(column_name, column_type):
                columns_added += 1
        
        if columns_added > 0:
            print(f"Aggiunte {columns_added} nuove colonne.")
        else:
            print("La tabella è già aggiornata con tutte le colonne necessarie.")
            
        # Aggiorna gli hash e i metadati
        print("Aggiornamento delle categorie e degli hash dei log...")
        update_record_hashes()
        
        print("Migrazione completata con successo!")

if __name__ == "__main__":
    main()