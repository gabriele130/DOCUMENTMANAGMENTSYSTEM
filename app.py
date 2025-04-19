import os
import logging
import functools
from flask import Flask, render_template, flash, redirect, url_for, g, request, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
import re
from markupsafe import Markup
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Setup SQLAlchemy base class
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()
scheduler = BackgroundScheduler(daemon=True)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///dms.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure file upload settings
app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload size
app.config["ALLOWED_EXTENSIONS"] = {
    "pdf", "docx", "xlsx", "pptx", "txt", "jpg", "jpeg", "png", "gif"
}

# Ensure upload directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Initialize extensions with app
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = "login"
csrf.init_app(app)
CORS(app)

# Create an empty form for CSRF protection
class EmptyForm(FlaskForm):
    pass

# Initialize database
with app.app_context():
    import models
    db.create_all()

# Create a context processor to add form to all templates
@app.context_processor
def inject_csrf_form():
    return {'form': EmptyForm()}

# Import routes after initializing everything
from routes import *
from company_routes import *

# Import e configura il servizio promemoria
with app.app_context():
    from services.reminder_service import check_reminders
    
    # Configura il job scheduler per verificare i promemoria ogni ora
    @scheduler.scheduled_job(IntervalTrigger(minutes=60))
    def scheduled_reminder_check():
        with app.app_context():
            app.logger.info("Esecuzione controllo promemoria schedulato")
            try:
                check_reminders()
            except Exception as e:
                app.logger.error(f"Errore durante il controllo dei promemoria: {str(e)}")
    
    # Avvia lo scheduler
    try:
        scheduler.start()
        app.logger.info("Scheduler avviato con successo")
    except Exception as e:
        app.logger.error(f"Errore avvio scheduler: {str(e)}")

# Filtri personalizzati
@app.template_filter('nl2br')
def nl2br_filter(text):
    if not text:
        return text
    return Markup(text.replace('\n', '<br>'))

# Register error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    # Log error
    app.logger.error(f"500 Error: {str(e)}")
    
    # Rollback any ongoing transactions
    try:
        db.session.rollback()
    except:
        pass
        
    return render_template('500.html'), 500

# Decoratore per gestire le eccezioni SQL e le transazioni
def handle_db_errors(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Database error: {str(e)}")
            flash("Si è verificato un errore nel database. Riprova più tardi.", "danger")
            return redirect(url_for('dashboard'))
    return decorated_function
