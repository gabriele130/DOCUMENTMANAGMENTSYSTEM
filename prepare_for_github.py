#!/usr/bin/env python3
"""
Script per preparare il codice per GitHub, rimuovendo o mascherando dati sensibili
e riferimenti a Replit.
"""

import os
import re
import sys
import shutil

def clean_file(file_path):
    """Rimuove o maschera dati sensibili e riferimenti a Replit da un file."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Sostituisci URL di database specifici per Replit con placeholder
    content = re.sub(
        r'postgresql://[a-zA-Z0-9_]+:[a-zA-Z0-9_]+@[a-zA-Z0-9_\.\-]+/[a-zA-Z0-9_]+',
        'postgresql://username:password@localhost/dbname',
        content
    )
    
    # Sostituisci altri riferimenti comuni a Replit
    content = content.replace('.', '.')
    content = re.sub(r'SESSION_SECRET\s*=\s*[\'"][^\'"]+[\'"]', 'SESSION_SECRET = "your_secret_key"', content)
    
    # Rimuovi riferimenti a percorsi specifici di Replit
    content = re.sub(r'\/home\/runner\/[a-zA-Z0-9_\-\/\.]+', '.', content)
    
    # Rimuovi riferimenti a versioni specifiche di Replit
    content = re.sub(r'replit\-[a-zA-Z0-9_\-\.]+', 'generic-host', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Pulito: {file_path}")

def should_exclude(file_path):
    """Determina se un file o una directory deve essere escluso."""
    exclude_patterns = [
        '.git', '__pycache__', '.replit', 'replit.nix',
        '.upm', '.config', '.cache', 'venv', 'node_modules',
        'uploads/', 'document_cache/', 'document_storage/',
        'permanent_storage/', 'attached_assets/'
    ]
    
    for pattern in exclude_patterns:
        if pattern in file_path:
            return True
    
    return False

def process_directory(directory):
    """Processa tutti i file in una directory e nelle sue sottodirectory."""
    for root, dirs, files in os.walk(directory):
        # Modifica dirs in-place per saltare le directory da escludere
        dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d))]
        
        for file in files:
            file_path = os.path.join(root, file)
            
            if should_exclude(file_path):
                continue
            
            # Processa solo file di codice o configurazione
            if file.endswith(('.py', '.js', '.html', '.css', '.json', '.yml', '.yaml', '.ini', '.cfg')):
                try:
                    clean_file(file_path)
                except Exception as e:
                    print(f"Errore durante la pulizia di {file_path}: {e}")

def create_directories():
    """Crea le directory necessarie se non esistono."""
    directories = ['uploads', 'document_cache', 'document_storage', 'permanent_storage']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            # Crea un file .gitkeep per mantenere la directory in git
            with open(os.path.join(directory, '.gitkeep'), 'w') as f:
                f.write('')
            print(f"Creata directory: {directory}")

def main():
    """Funzione principale."""
    print("Preparazione del codice per GitHub...")
    
    # Crea le directory necessarie
    create_directories()
    
    # Processa i file nel progetto
    process_directory('.')
    
    print("Completato! Il codice è pronto per essere caricato su GitHub.")

if __name__ == "__main__":
    main()