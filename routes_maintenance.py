"""
Routes per la manutenzione del sistema e il monitoraggio dello storage centralizzato.
"""

from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app, jsonify, Response, stream_with_context
)
from flask_login import login_required, current_user
from sqlalchemy import func, desc
import os
import logging
import datetime
import json
from functools import wraps
from app import db
from models import Document, ActivityLog, User
from services.central_storage import (
    ensure_storage_directories, 
    get_storage_stats, 
    migrate_files_to_central_storage,
    verify_and_repair_storage,
    validate_document_storage,
    cleanup_orphaned_files,
    get_file_from_storage,
    migrate_document_to_central_storage
)
from services.file_recovery import recover_missing_file
from services.persistent_storage import (
    ensure_storage_structure as ensure_permanent_storage_structure,
    batch_migrate_to_permanent_storage,
    migrate_document_to_permanent_storage,
    verify_storage_integrity as verify_permanent_storage_integrity
)

# Configurazione del blueprint
maintenance_bp = Blueprint('maintenance', __name__, url_prefix='/admin/maintenance')

# Decorator per verificare i permessi di amministratore
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Accesso limitato agli amministratori.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@maintenance_bp.route('/')
@login_required
@admin_required
def index():
    """Dashboard di manutenzione"""
    # Controlla che le directory di storage esistano
    ensure_storage_directories()
    
    # Ottieni statistiche sullo storage
    storage_stats = get_storage_stats()
    
    # Conteggio totale documenti
    doc_count = Document.query.count()
    
    # Conteggio documenti con file mancanti (senza controllo is_deleted)
    missing_files_count = 0
    problem_documents = []
    
    try:
        # La funzione file_exists potrebbe non esistere, utilizziamo un metodo manuale
        for doc in Document.query.all():
            if doc.file_path and not os.path.exists(doc.file_path):
                missing_files_count += 1
                if len(problem_documents) < 10:
                    problem_documents.append(doc)
    except Exception as e:
        logging.error(f"Errore durante il conteggio dei file mancanti: {str(e)}")
    
    # Statistiche attività recenti
    recent_activity = ActivityLog.query.order_by(desc(ActivityLog.timestamp)).limit(20).all()
    
    return render_template(
        'admin/maintenance/index.html',
        storage_stats=storage_stats,
        doc_count=doc_count,
        missing_files_count=missing_files_count,
        problem_documents=problem_documents,
        recent_activity=recent_activity
    )

@maintenance_bp.route('/storage-centralizzato')
@login_required
@admin_required
def central_storage():
    """Gestione dello storage centralizzato"""
    # Controlla che le directory di storage esistano
    ensure_storage_directories()
    
    # Ottieni statistiche sullo storage
    storage_stats = get_storage_stats()
    
    # Query per documenti con problemi (senza controllo is_deleted)
    problem_docs = []
    
    try:
        # La funzione file_exists potrebbe non esistere, utilizziamo un metodo manuale
        for doc in Document.query.all():
            if doc.file_path and not os.path.exists(doc.file_path):
                problem_docs.append(doc)
                if len(problem_docs) >= 50:
                    break
    except Exception as e:
        logging.error(f"Errore durante la ricerca di documenti con problemi: {str(e)}")
    
    # Query per documenti recenti
    recent_docs = Document.query.order_by(desc(Document.created_at)).limit(10).all()
    
    return render_template(
        'admin/maintenance/central_storage.html',
        storage_stats=storage_stats,
        problem_docs=problem_docs,
        recent_docs=recent_docs
    )

@maintenance_bp.route('/avvia-migrazione', methods=['POST'])
@login_required
@admin_required
def start_migration():
    """Avvia la migrazione dei file al sistema di storage centralizzato"""
    try:
        # Avvia la migrazione
        migration_report = migrate_files_to_central_storage(update_database=True)
        
        flash(f"Migrazione completata! {migration_report['migrated_successfully']} documenti migrati con successo, "
              f"{migration_report['migration_failed']} falliti.", 'success')
              
        # Registra l'attività
        log_entry = ActivityLog(
            user_id=current_user.id,
            action_type="migrate",
            target_type="storage",
            target_id=0,
            details=f"Migrazione al sistema di storage centralizzato: {migration_report['migrated_successfully']} successi, "
                   f"{migration_report['migration_failed']} fallimenti",
            result="success" if migration_report['migration_failed'] == 0 else "partial"
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return redirect(url_for('maintenance.central_storage'))
    except Exception as e:
        flash(f"Errore durante la migrazione: {str(e)}", 'danger')
        logging.error(f"Errore durante la migrazione: {str(e)}")
        
        # Registra l'errore
        log_entry = ActivityLog(
            user_id=current_user.id,
            action_type="migrate",
            target_type="storage",
            target_id=0,
            details=f"Errore durante la migrazione: {str(e)}",
            result="failure"
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return redirect(url_for('maintenance.central_storage'))

@maintenance_bp.route('/verifica-ripara-storage', methods=['POST'])
@login_required
@admin_required
def verify_repair_storage():
    """Verifica e ripara eventuali problemi nello storage"""
    try:
        # Esegui la verifica e riparazione
        repair_report = verify_and_repair_storage()
        
        flash(f"Verifica e riparazione completata! {repair_report['verified_ok']} documenti OK, "
              f"{repair_report['files_restored']} file ripristinati.", 'success')
        
        # Registra l'attività
        log_entry = ActivityLog(
            user_id=current_user.id,
            action_type="repair",
            target_type="storage",
            target_id=0,
            details=f"Verifica e riparazione storage: {repair_report['verified_ok']} OK, "
                   f"{repair_report['files_restored']} ripristinati",
            result="success"
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return redirect(url_for('maintenance.central_storage'))
    except Exception as e:
        flash(f"Errore durante la verifica e riparazione: {str(e)}", 'danger')
        logging.error(f"Errore durante la verifica e riparazione: {str(e)}")
        
        # Registra l'errore
        log_entry = ActivityLog(
            user_id=current_user.id,
            action_type="repair",
            target_type="storage",
            target_id=0,
            details=f"Errore durante la verifica e riparazione: {str(e)}",
            result="failure"
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return redirect(url_for('maintenance.central_storage'))

@maintenance_bp.route('/valida-documento/<int:doc_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def validate_document(doc_id):
    """Valida un singolo documento e ne ripristina il file se necessario"""
    try:
        document = Document.query.get_or_404(doc_id)
        
        validation_result = validate_document_storage(document)
        
        if validation_result['status'] == 'ok':
            flash(f"Documento validato con successo: {document.filename}", 'success')
        elif validation_result['status'] == 'restored':
            flash(f"Documento ripristinato con successo: {document.filename}", 'success')
        else:
            flash(f"Il documento non può essere ripristinato: {validation_result['message']}", 'warning')
        
        # Registra l'attività
        log_entry = ActivityLog(
            user_id=current_user.id,
            action_type="validate",
            target_type="document",
            target_id=doc_id,
            details=f"Validazione documento: {validation_result['status']} - {validation_result.get('message', '')}",
            result="success" if validation_result['status'] in ['ok', 'restored'] else "failure"
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return redirect(url_for('maintenance.central_storage'))
    except Exception as e:
        flash(f"Errore durante la validazione del documento: {str(e)}", 'danger')
        logging.error(f"Errore durante la validazione del documento {doc_id}: {str(e)}")
        
        # Registra l'errore
        log_entry = ActivityLog(
            user_id=current_user.id,
            action_type="validate",
            target_type="document",
            target_id=doc_id,
            details=f"Errore durante la validazione: {str(e)}",
            result="failure"
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return redirect(url_for('maintenance.central_storage'))

@maintenance_bp.route('/pulizia-file-orfani', methods=['POST'])
@login_required
@admin_required
def cleanup_orphans():
    """Pulisce i file orfani che non sono collegati a nessun documento nel database"""
    try:
        cleanup_result = cleanup_orphaned_files(commit=request.form.get('commit') == 'true')
        
        if request.form.get('commit') == 'true':
            flash(f"Pulizia completata! Rimossi {cleanup_result['removed']} file orfani.", 'success')
        else:
            flash(f"Simulazione pulizia: trovati {cleanup_result['identified']} file orfani. "
                 "Esegui nuovamente con l'opzione 'Conferma' per rimuoverli.", 'info')
        
        # Registra l'attività
        log_entry = ActivityLog(
            user_id=current_user.id,
            action_type="cleanup",
            target_type="storage",
            target_id=0,
            details=f"Pulizia file orfani: {json.dumps(cleanup_result)}",
            result="success"
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return redirect(url_for('maintenance.central_storage'))
    except Exception as e:
        flash(f"Errore durante la pulizia dei file orfani: {str(e)}", 'danger')
        logging.error(f"Errore durante la pulizia dei file orfani: {str(e)}")
        
        # Registra l'errore
        log_entry = ActivityLog(
            user_id=current_user.id,
            action_type="cleanup",
            target_type="storage",
            target_id=0,
            details=f"Errore durante la pulizia: {str(e)}",
            result="failure"
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return redirect(url_for('maintenance.central_storage'))

@maintenance_bp.route('/storage-permanente')
@login_required
@admin_required
def permanent_storage():
    """Gestione dello storage permanente"""
    # Controlla che le directory di storage permanente esistano
    ensure_permanent_storage_structure()
    
    # Query per documenti con problemi (senza controllo is_deleted)
    problem_docs = []
    
    try:
        # Usa il metodo manuale per trovare documenti con problemi
        for doc in Document.query.all():
            if doc.file_path and not os.path.exists(doc.file_path):
                problem_docs.append(doc)
                if len(problem_docs) >= 50:
                    break
    except Exception as e:
        logging.error(f"Errore durante la ricerca di documenti con problemi: {str(e)}")
    
    # Query per documenti recenti
    recent_docs = Document.query.order_by(desc(Document.created_at)).limit(10).all()
    
    # Conta il numero totale di documenti
    total_documents = Document.query.count()
    
    return render_template(
        'admin/maintenance/permanent_storage.html',
        problem_docs=problem_docs,
        recent_docs=recent_docs,
        total_documents=total_documents
    )

@maintenance_bp.route('/migrazione-storage-permanente', methods=['POST'])
@login_required
@admin_required
def migrate_to_permanent_storage():
    """Avvia la migrazione dei file al sistema di storage permanente"""
    try:
        # Controlla che le directory di storage permanente esistano
        ensure_permanent_storage_structure()
        
        # Conta il numero totale di documenti
        total_documents = Document.query.count()
        
        # Avvia la migrazione in batch
        batch_size = 50  # Dimensione del batch ridotta per evitare problemi di timeout
        migrated = 0
        failed = 0
        errors = []
        
        # Ottieni tutti i documenti
        documents = Document.query.all()
        
        for doc in documents:
            try:
                result = migrate_document_to_permanent_storage(doc)
                
                if result['status'] in ['migrated', 'ok', 'restored']:
                    migrated += 1
                else:
                    failed += 1
                    errors.append({
                        'document_id': doc.id,
                        'reason': result['message']
                    })
            except Exception as e:
                failed += 1
                errors.append({
                    'document_id': doc.id,
                    'reason': str(e)
                })
        
        # Crea un timestamp per il nome del report
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"migration_report_{timestamp}.txt"
        
        # Salva il report
        with open(report_file, 'w') as f:
            f.write(f"== Report di Migrazione allo Storage Permanente ==\n")
            f.write(f"Data: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"Totale documenti: {total_documents}\n")
            f.write(f"Documenti migrati con successo: {migrated}\n")
            f.write(f"Documenti falliti: {failed}\n\n")
            
            if failed > 0:
                f.write("== Dettagli Errori ==\n")
                for error in errors:
                    f.write(f"Documento ID {error['document_id']}: {error['reason']}\n")
            
            f.write("\n== Fine Report ==\n")
        
        # Registra l'attività
        log_entry = ActivityLog(
            user_id=current_user.id,
            action_type="migrate",
            target_type="storage_permanent",
            target_id=0,
            details=f"Migrazione allo storage permanente: {migrated} successi, {failed} fallimenti",
            result="success" if failed == 0 else "partial"
        )
        db.session.add(log_entry)
        db.session.commit()
        
        flash(f"Migrazione allo storage permanente completata! {migrated} documenti migrati con successo, {failed} falliti. Report salvato in {report_file}", 'success')
        return redirect(url_for('maintenance.permanent_storage'))
    except Exception as e:
        flash(f"Errore durante la migrazione allo storage permanente: {str(e)}", 'danger')
        logging.error(f"Errore durante la migrazione allo storage permanente: {str(e)}")
        
        # Registra l'errore
        log_entry = ActivityLog(
            user_id=current_user.id,
            action_type="migrate",
            target_type="storage_permanent",
            target_id=0,
            details=f"Errore durante la migrazione allo storage permanente: {str(e)}",
            result="failure"
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return redirect(url_for('maintenance.permanent_storage'))

@maintenance_bp.route('/verifica-storage-permanente', methods=['POST'])
@login_required
@admin_required
def verify_permanent_storage():
    """Verifica l'integrità dello storage permanente"""
    try:
        # Assicura che le directory di storage esistano
        ensure_permanent_storage_structure()
        
        # Esegui la verifica di integrità
        verification_stats = verify_permanent_storage_integrity()
        
        flash(f"Verifica completata! {verification_stats['ok']} file integri, {verification_stats['repaired']} riparati, {verification_stats['failed']} non ripristinabili.", 'success')
        
        # Registra l'attività
        log_entry = ActivityLog(
            user_id=current_user.id,
            action_type="verify",
            target_type="storage_permanent",
            target_id=0,
            details=f"Verifica storage permanente: {verification_stats['ok']} integri, {verification_stats['repaired']} riparati, {verification_stats['failed']} falliti",
            result="success"
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return redirect(url_for('maintenance.permanent_storage'))
    except Exception as e:
        flash(f"Errore durante la verifica dello storage permanente: {str(e)}", 'danger')
        logging.error(f"Errore durante la verifica dello storage permanente: {str(e)}")
        
        # Registra l'errore
        log_entry = ActivityLog(
            user_id=current_user.id,
            action_type="verify",
            target_type="storage_permanent",
            target_id=0,
            details=f"Errore durante la verifica dello storage permanente: {str(e)}",
            result="failure"
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return redirect(url_for('maintenance.permanent_storage'))

@maintenance_bp.route('/statistiche-documenti')
@login_required
@admin_required
def document_statistics():
    """Visualizza statistiche dettagliate sui documenti"""
    # Statistiche per tipo di file
    file_type_stats = db.session.query(
        Document.file_type, 
        func.count(Document.id).label('count')
    ).group_by(Document.file_type).all()
    
    # Statistiche per mese di creazione
    month_stats = db.session.query(
        func.date_trunc('month', Document.created_at).label('month'),
        func.count(Document.id).label('count')
    ).group_by('month').order_by('month').all()
    
    # Statistiche per utente
    user_stats = db.session.query(
        User.id,
        User.username,
        func.count(Document.id).label('count')
    ).join(Document, Document.owner_id == User.id)\
     .group_by(User.id, User.username)\
     .order_by(desc('count')).all()
    
    return render_template(
        'admin/maintenance/document_statistics.html',
        file_type_stats=file_type_stats,
        month_stats=month_stats,
        user_stats=user_stats
    )

# Flag per tenere traccia della registrazione
_blueprint_registered = False

# Aggiungi il blueprint all'app principale
def register_maintenance_blueprint(app):
    global _blueprint_registered
    if not _blueprint_registered:
        try:
            app.register_blueprint(maintenance_bp)
            _blueprint_registered = True
        except ValueError as e:
            # Il blueprint è già registrato, ignora l'errore
            if "already registered" in str(e):
                _blueprint_registered = True
                pass
            else:
                raise
    
    # Inietta funzioni utili nei template
    @app.template_filter('datetime_format')
    def datetime_format(value, format='%d/%m/%Y %H:%M'):
        if value is None:
            return ""
        return value.strftime(format)
    
    @app.template_filter('filesize_format')
    def filesize_format(bytes, unit='auto'):
        if unit == 'auto':
            if bytes < 1024:
                return f"{bytes} B"
            elif bytes < 1024 * 1024:
                return f"{bytes/1024:.1f} KB"
            elif bytes < 1024 * 1024 * 1024:
                return f"{bytes/(1024*1024):.1f} MB"
            else:
                return f"{bytes/(1024*1024*1024):.2f} GB"
        elif unit == 'kb':
            return f"{bytes/1024:.1f} KB"
        elif unit == 'mb':
            return f"{bytes/(1024*1024):.1f} MB"
        elif unit == 'gb':
            return f"{bytes/(1024*1024*1024):.2f} GB"
        else:
            return f"{bytes} B"