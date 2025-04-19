import json
import logging
import datetime
from app import db
from models import Reminder, Notification, User, Document

logger = logging.getLogger(__name__)

def check_reminders():
    """
    Verifica i promemoria in scadenza e genera notifiche
    Questa funzione dovrebbe essere eseguita periodicamente
    """
    logger.info("Verifica promemoria in corso...")
    today = datetime.datetime.now().date()
    
    # Ottieni tutti i promemoria attivi (non completati)
    reminders = Reminder.query.filter_by(is_completed=False).all()
    notifications_count = 0
    
    for reminder in reminders:
        # Converti la data di scadenza in oggetto date se è datetime
        if isinstance(reminder.due_date, datetime.datetime):
            due_date = reminder.due_date.date()
        else:
            due_date = reminder.due_date
        
        # Calcola i giorni mancanti alla scadenza
        days_until_due = (due_date - today).days
        
        # Verifica promemoria principale
        if days_until_due == reminder.notify_days_before:
            notifications_created = process_reminder_notification(reminder)
            notifications_count += notifications_created
        
        # Verifica notifiche aggiuntive 
        if reminder.extra_notifications:
            try:
                extra_notifications = json.loads(reminder.extra_notifications)
                for extra in extra_notifications:
                    if days_until_due == extra.get('days', 0):
                        notifications_created = process_reminder_notification(
                            reminder, 
                            f"Promemoria aggiuntivo: {extra.get('amount')} {extra.get('unit')}"
                        )
                        notifications_count += notifications_created
            except json.JSONDecodeError:
                logger.error(f"Errore decodifica extra_notifications per reminder {reminder.id}")
        
        # Verifica promemoria scaduti (il giorno stesso della scadenza)
        if days_until_due == 0:
            notifications_created = process_reminder_notification(
                reminder, 
                "Scade oggi!"
            )
            notifications_count += notifications_created
        
        # Verifica promemoria in ritardo (dopo la data di scadenza)
        if days_until_due < 0:
            # Notifica solo se la scadenza è recente (max 7 giorni)
            if days_until_due > -7:
                notifications_created = process_reminder_notification(
                    reminder, 
                    f"In ritardo di {abs(days_until_due)} giorni!"
                )
                notifications_count += notifications_created
    
    logger.info(f"Verifica promemoria completata: generate {notifications_count} notifiche")
    return notifications_count

def process_reminder_notification(reminder, suffix=""):
    """
    Processa un promemoria e genera notifiche
    
    Args:
        reminder (Reminder): Oggetto promemoria
        suffix (str): Suffisso da aggiungere al messaggio di notifica
    
    Returns:
        int: Numero di notifiche generate
    """
    notifications_count = 0
    
    # Ottieni il documento associato (se esiste)
    document = None
    doc_title = "Documento sconosciuto"
    if reminder.document_id:
        document = Document.query.get(reminder.document_id)
        if document:
            doc_title = document.title or document.original_filename
    
    # Determina gli utenti da notificare
    notify_users = []
    
    # Aggiungi utenti specificati nel promemoria
    if reminder.notify_users:
        try:
            user_ids = json.loads(reminder.notify_users)
            for user_id in user_ids:
                user = User.query.get(user_id)
                if user and user not in notify_users:
                    notify_users.append(user)
        except json.JSONDecodeError:
            logger.warning(f"Formato notify_users non valido per reminder {reminder.id}")
    
    # Aggiungi il creatore del promemoria
    creator = User.query.get(reminder.created_by_id)
    if creator and creator not in notify_users:
        notify_users.append(creator)
    
    # Aggiungi il proprietario del documento (se diverso dal creatore)
    if document and document.owner and document.owner not in notify_users:
        notify_users.append(document.owner)
    
    # Genera il messaggio di notifica
    message_base = f"Promemoria: {reminder.title}"
    if document:
        message_base += f" per il documento '{doc_title}'"
        
    message = message_base
    if suffix:
        message += f" - {suffix}"
    
    # Crea una notifica per ogni utente
    for user in notify_users:
        # Determina il tipo di notifica in base al suffisso
        notification_type = "reminder"
        if "scade oggi" in suffix.lower():
            notification_type = "deadline"
        elif "in ritardo" in suffix.lower():
            notification_type = "overdue"
        
        notification = Notification(
            user_id=user.id,
            message=message,
            notification_type=notification_type,
            is_read=False
        )
        
        # Se esiste un documento, aggiungi un link nella notifica
        if document:
            notification.link = f"/documents/{document.id}"
            
        db.session.add(notification)
        notifications_count += 1
    
    db.session.commit()
    return notifications_count