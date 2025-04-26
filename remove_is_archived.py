import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db = SQLAlchemy(app)

def remove_is_archived_column():
    """Remove is_archived column from document table"""
    print("Rimozione colonna is_archived dalla tabella document...")
    
    # Verifica se la colonna esiste
    result = db.session.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'document' AND column_name = 'is_archived';"
    )).fetchone()
    
    if result:
        print("Colonna is_archived trovata. Rimozione in corso...")
        # Esegui ALTER TABLE per rimuovere la colonna
        db.session.execute(text("ALTER TABLE document DROP COLUMN is_archived;"))
        db.session.commit()
        print("Colonna is_archived rimossa con successo.")
    else:
        print("Colonna is_archived non trovata. Nessuna azione necessaria.")
    
    print("Operazione completata.")

if __name__ == "__main__":
    with app.app_context():
        remove_is_archived_column()