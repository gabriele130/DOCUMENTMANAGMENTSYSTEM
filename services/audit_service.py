"""
Audit Trail Service per la gestione degli audit log in conformità con ISO 27001, GDPR ed eIDAS.
Questo servizio fornisce funzionalità per la registrazione di tutte le attività degli utenti
nel sistema in modo dettagliato, sicuro e conforme alle normative.
"""

import json
import datetime
import hashlib
import uuid
import os
from flask import request, current_app
from app import db
from models import ActivityLog, User, Document

class AuditTrailService:
    """Servizio per la gestione degli audit log in conformità con le normative."""
    
    # Categorie di azioni per classificazione
    ACTION_CATEGORIES = {
        'view': 'ACCESS',
        'download': 'ACCESS',
        'print': 'ACCESS',
        'upload': 'CRUD',
        'create': 'CRUD',
        'update': 'CRUD',
        'delete': 'CRUD',
        'archive': 'CRUD',
        'unarchive': 'CRUD',
        'share': 'SECURITY',
        'unshare': 'SECURITY',
        'login': 'SECURITY',
        'logout': 'SECURITY',
        'password_change': 'SECURITY',
        'permission_change': 'ADMIN',
        'user_creation': 'ADMIN',
        'user_deletion': 'ADMIN',
        'user_suspension': 'ADMIN',
    }
    
    # Livelli di sicurezza per le diverse azioni
    SECURITY_LEVELS = {
        'view': 'standard',
        'download': 'standard',
        'print': 'standard',
        'upload': 'standard',
        'create': 'standard',
        'update': 'standard',
        'delete': 'sensitive',
        'archive': 'standard',
        'unarchive': 'standard',
        'share': 'sensitive',
        'unshare': 'sensitive',
        'login': 'sensitive',
        'logout': 'standard',
        'password_change': 'critical',
        'permission_change': 'critical',
        'user_creation': 'critical',
        'user_deletion': 'critical',
        'user_suspension': 'critical',
    }
    
    @staticmethod
    def log_activity(user_id, action, document_id=None, details=None, result="success", 
                     ip_address=None, user_agent=None, device_info=None, geolocation=None):
        """
        Registra una attività nel sistema con audit trail completo.
        
        Args:
            user_id: ID dell'utente che ha eseguito l'azione
            action: Tipo di azione (view, download, create, update, delete, etc.)
            document_id: ID del documento coinvolto (opzionale)
            details: Dettagli specifici dell'azione in formato dict/JSON
            result: Risultato dell'operazione (success, failure, denied)
            ip_address: Indirizzo IP dell'utente (automatico se non specificato)
            user_agent: User agent del browser dell'utente (automatico se non specificato)
            device_info: Informazioni sul dispositivo dell'utente (opzionale)
            geolocation: Informazioni sulla posizione geografica (opzionale)
        
        Returns:
            ActivityLog: L'oggetto ActivityLog creato
        """
        try:
            # Ottieni informazioni dall'ambiente se non specificate
            if not ip_address and request:
                ip_address = request.remote_addr
            
            if not user_agent and request:
                user_agent = request.headers.get('User-Agent', '')
            
            # Determina categoria e livello di sicurezza
            action_category = AuditTrailService.ACTION_CATEGORIES.get(action, 'GENERAL')
            security_level = AuditTrailService.SECURITY_LEVELS.get(action, 'standard')
            
            # Prepara i metadati contestuali
            context_meta = {}
            
            # Aggiungi metadati del documento se applicabile
            if document_id:
                document = Document.query.get(document_id)
                if document:
                    context_meta = {
                        'document_title': document.title,
                        'filename': document.original_filename,
                        'file_type': document.file_type,
                        'file_size': document.file_size,
                        'version': document.version if hasattr(document, 'version') else 1,
                        'created_at': document.created_at.isoformat() if document.created_at else None,
                        'owner': document.owner.username if document.owner else None
                    }
            
            # Converti i dettagli in JSON se necessario
            if isinstance(details, dict):
                details_json = json.dumps(details)
            else:
                details_json = details
                
            # Converti i metadati in JSON
            context_metadata_json = json.dumps(context_meta)
            
            # Crea il record di log
            activity_log = ActivityLog(
                user_id=user_id,
                document_id=document_id,
                action=action,
                action_category=action_category,
                details=details_json,
                context_metadata=context_metadata_json,
                result=result,
                ip_address=ip_address,
                user_agent=user_agent,
                device_info=device_info,
                geolocation=geolocation,
                security_level=security_level
            )
            
            # Calcola e imposta l'hash per la verifica di integrità
            activity_log.record_hash = activity_log.calculate_hash()
            activity_log.verified = True
            
            # Salva il log
            db.session.add(activity_log)
            db.session.commit()
            
            # Logging per debug
            current_app.logger.info(f"Audit log: {user_id} {action} {document_id} {result}")
            
            return activity_log
        except Exception as e:
            current_app.logger.error(f"Errore nella registrazione audit: {str(e)}")
            # Gestione degli errori, evita crash
            db.session.rollback()
            return None
    
    @staticmethod
    def log_document_view(user_id, document_id, ip_address=None):
        """Log specifico per la visualizzazione di un documento"""
        return AuditTrailService.log_activity(
            user_id=user_id,
            action="view",
            document_id=document_id,
            details={"action": "document_view"},
            ip_address=ip_address
        )
    
    @staticmethod
    def log_document_download(user_id, document_id, ip_address=None):
        """Log specifico per il download di un documento"""
        return AuditTrailService.log_activity(
            user_id=user_id,
            action="download",
            document_id=document_id,
            details={"action": "document_download"},
            ip_address=ip_address
        )
    
    @staticmethod
    def log_document_print(user_id, document_id, ip_address=None):
        """Log specifico per la stampa di un documento"""
        return AuditTrailService.log_activity(
            user_id=user_id,
            action="print",
            document_id=document_id,
            details={"action": "document_print"},
            ip_address=ip_address
        )
    
    @staticmethod
    def log_login(user_id, success=True, ip_address=None, user_agent=None):
        """Log specifico per i tentativi di login"""
        result = "success" if success else "failure"
        return AuditTrailService.log_activity(
            user_id=user_id,
            action="login",
            details={"success": success},
            result=result,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_logout(user_id, ip_address=None):
        """Log specifico per il logout"""
        return AuditTrailService.log_activity(
            user_id=user_id,
            action="logout",
            details={"action": "user_logout"},
            ip_address=ip_address
        )
    
    @staticmethod
    def export_logs_to_file(start_date=None, end_date=None, user_id=None, action=None, format="json"):
        """
        Esporta i log in un file per conservazione a norma.
        
        Args:
            start_date: Data di inizio per l'esportazione
            end_date: Data di fine per l'esportazione
            user_id: Filtra per utente specifico
            action: Filtra per azione specifica
            format: Formato di esportazione (json, csv)
            
        Returns:
            String: Percorso del file esportato
        """
        query = ActivityLog.query
        
        # Applica i filtri
        if start_date:
            query = query.filter(ActivityLog.created_at >= start_date)
        if end_date:
            query = query.filter(ActivityLog.created_at <= end_date)
        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
        if action:
            query = query.filter(ActivityLog.action == action)
            
        # Ordina per data
        logs = query.order_by(ActivityLog.created_at).all()
        
        # Crea directory se non esiste
        export_dir = "exports/audit_logs"
        os.makedirs(export_dir, exist_ok=True)
        
        # Genera nome file unico
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{export_dir}/audit_log_{timestamp}.{format}"
        
        # Esporta in base al formato richiesto
        if format == "json":
            log_data = []
            for log in logs:
                # Crea un dizionario con tutti i dati del log
                log_entry = {
                    "id": log.id,
                    "timestamp": log.created_at.isoformat(),
                    "user_id": log.user_id,
                    "user": log.user.username if log.user else None,
                    "action": log.action,
                    "action_category": log.action_category,
                    "document_id": log.document_id,
                    "document": log.document.title if log.document else None,
                    "details": log.details,
                    "result": log.result,
                    "ip_address": log.ip_address,
                    "security_level": log.security_level,
                    "integrity_verified": log.verify_integrity()
                }
                log_data.append(log_entry)
                
            # Scrivi sul file
            with open(filename, 'w') as f:
                json.dump(log_data, f, indent=2)
        
        elif format == "csv":
            import csv
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                # Scrivi intestazione
                writer.writerow([
                    "ID", "Timestamp", "User ID", "Username", "Action", 
                    "Category", "Document ID", "Document", "Details", 
                    "Result", "IP Address", "Security Level", "Integrity"
                ])
                
                # Scrivi dati
                for log in logs:
                    writer.writerow([
                        log.id,
                        log.created_at.isoformat(),
                        log.user_id,
                        log.user.username if log.user else None,
                        log.action,
                        log.action_category,
                        log.document_id,
                        log.document.title if log.document else None,
                        log.details,
                        log.result,
                        log.ip_address,
                        log.security_level,
                        log.verify_integrity()
                    ])
        
        return filename
    
    @staticmethod
    def verify_log_integrity(log_id=None):
        """
        Verifica l'integrità di uno o tutti i log.
        
        Args:
            log_id: ID specifico del log da verificare, o None per verificare tutti
            
        Returns:
            dict: Risultati della verifica
        """
        results = {
            "verified": 0,
            "tampered": 0,
            "total": 0,
            "tampered_logs": []
        }
        
        if log_id:
            logs = [ActivityLog.query.get(log_id)]
        else:
            logs = ActivityLog.query.all()
        
        for log in logs:
            results["total"] += 1
            if log.verify_integrity():
                results["verified"] += 1
            else:
                results["tampered"] += 1
                results["tampered_logs"].append({
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                    "document_id": log.document_id
                })
        
        return results