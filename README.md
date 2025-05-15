# Sistema di Gestione Documentale

Sistema avanzato per la gestione documentale con intelligenza artificiale, progettato per aziende che necessitano di organizzazione, classificazione e automazione documentale.

## Caratteristiche principali

- Gestione centralizzata dei documenti aziendali
- Struttura gerarchica di cartelle con permessi personalizzabili
- Conteggio automatico dei file nelle cartelle
- Tag e metadati personalizzati
- Promemoria e scadenze 
- Supporto per correlazioni tra documenti
- Ricerca avanzata
- Audit trail completo delle attività

## Requisiti

- Python 3.10+
- PostgreSQL 12+
- Ambiente virtuale Python (consigliato)

## Installazione

1. Clona il repository:
```
git clone https://github.com/tuonome/gestione-documentale.git
cd gestione-documentale
```

2. Crea un ambiente virtuale e installa le dipendenze:
```
python -m venv venv
source venv/bin/activate  # Su Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Copia il file `.env.example` in `.env` e personalizza i valori:
```
cp .env.example .env
# Modifica i valori nel file .env secondo le tue esigenze
```

4. Crea la struttura delle directory necessarie:
```
mkdir -p uploads document_cache document_storage permanent_storage
```

5. Inizializza il database:
```
flask db upgrade
```

6. Avvia l'applicazione:
```
flask run
```

## Struttura del progetto

- `/app.py`: File principale dell'applicazione
- `/models.py`: Definizioni dei modelli di database
- `/routes.py`: Route principali dell'applicazione
- `/company_routes.py`: Route specifiche per la gestione aziendale
- `/services/`: Servizi e utilità interne
- `/templates/`: Template HTML
- `/static/`: File statici (CSS, JavaScript, immagini)

## Configurazione per l'ambiente di produzione

Per un ambiente di produzione, consigliamo:

1. Utilizzo di un server web come Nginx o Apache con proxy verso Gunicorn
2. Configurazione di SSL/TLS per la connessione sicura
3. Backup regolari del database

## Licenza

Questo software è proprietario e non può essere distribuito senza autorizzazione.

## Contatti

Per assistenza o informazioni, contattare [tuo indirizzo email].