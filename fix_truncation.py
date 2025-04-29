"""
Script per aggiornare le colonne nella tabella activity_log
per evitare problemi di troncamento con stringhe lunghe.
"""

import os
import sys
from app import app, db
from models import ActivityLog
from sqlalchemy import text

def update_column_type(column_name, new_type):
    """Aggiorna il tipo di una colonna esistente."""
    query = text(f"ALTER TABLE activity_log ALTER COLUMN {column_name} TYPE {new_type};")
    try:
        print(f"Aggiornamento colonna {column_name} a {new_type}...")
        db.session.execute(query)
        db.session.commit()
        print(f"Colonna {column_name} aggiornata con successo.")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Errore nell'aggiornamento della colonna {column_name}: {str(e)}")
        return False

def main():
    """Funzione principale per la migrazione."""
    with app.app_context():
        print("Avvio correzione della tabella activity_log per evitare troncamento...")
        
        # Colonne da aggiornare con i nuovi tipi
        columns_to_update = [
            ("user_agent", "TEXT"),
            ("device_info", "TEXT"),
            ("geolocation", "TEXT")
        ]
        
        # Aggiorna le colonne esistenti
        success_count = 0
        for column_name, new_type in columns_to_update:
            if update_column_type(column_name, new_type):
                success_count += 1
        
        if success_count == len(columns_to_update):
            print("Tutte le colonne sono state aggiornate con successo!")
        else:
            print(f"Aggiornate {success_count}/{len(columns_to_update)} colonne.")
        
        print("Correzione completata!")

if __name__ == "__main__":
    main()