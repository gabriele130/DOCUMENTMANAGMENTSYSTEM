# Guida alla migrazione da Replit

Questo documento fornisce istruzioni per migrare l'applicazione dall'ambiente Replit a un server locale o a un altro provider cloud.

## Prerequisiti

- Python 3.10 o superiore
- PostgreSQL 12 o superiore
- pip e virtualenv

## Passaggi per la migrazione

### 1. Preparazione del codice

Prima di clonare il repository da GitHub, è importante preparare il codice rimuovendo i riferimenti a Replit e i dati sensibili:

```bash
# Esegui lo script di preparazione
python prepare_for_github.py
```

### 2. Configurazione dell'ambiente

Dopo aver clonato il repository:

```bash
# Crea un ambiente virtuale
python -m venv venv
source venv/bin/activate  # Su Windows: venv\Scripts\activate

# Installa le dipendenze
pip install -r dependencies.txt
```

### 3. Configurazione del database

```bash
# Crea un database PostgreSQL
createdb nome_database

# Configura le variabili d'ambiente nel file .env
cp .env.example .env
# Modifica il file .env con i dati di connessione al tuo database
```

### 4. Modifica dei percorsi dei file

I percorsi dei file potrebbero dover essere adattati all'ambiente locale:

- In Replit, il percorso base è `/home/runner/workspace/`
- Nel tuo ambiente sarà la directory in cui hai clonato il repository

Controlla i seguenti file per eventuali percorsi assoluti:
- `app.py`
- `services/simple_document_storage.py`
- `services/file_recovery.py`

### 5. Inizializza il database

```bash
# Esegui le migrazioni del database (se usi Flask-Migrate)
flask db upgrade

# Oppure inizializza direttamente il database (se non usi migrazioni)
# L'app lo farà automaticamente al primo avvio
```

### 6. Creazione delle directory di storage

```bash
mkdir -p uploads document_cache document_storage permanent_storage
```

### 7. Avvio dell'applicazione

```bash
# Avvio in modalità sviluppo
flask run

# Avvio in produzione con gunicorn
gunicorn --bind 0.0.0.0:5000 main:app
```

## Considerazioni per la produzione

1. **Sicurezza**:
   - Usa HTTPS in produzione
   - Configura un proxy come Nginx o Apache davanti a Gunicorn
   - Imposta SECRET_KEY univoci e complessi

2. **Performance**:
   - Configura adeguatamente il pool di connessioni al database
   - Valuta l'uso di un sistema di cache come Redis

3. **Storage**:
   - Per ambienti di produzione, valuta l'utilizzo di storage object come S3, MinIO, etc.
   - Modifica `services/simple_document_storage.py` per supportare lo storage object

4. **Backup**:
   - Configura backup regolari del database e dei file caricati