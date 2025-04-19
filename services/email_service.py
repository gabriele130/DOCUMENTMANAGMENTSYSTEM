import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

logger = logging.getLogger(__name__)

def send_email(to_email, subject, html_content=None, text_content=None):
    """
    Invia una email utilizzando SendGrid
    
    Args:
        to_email (str): Indirizzo email del destinatario
        subject (str): Oggetto dell'email
        html_content (str, optional): Contenuto HTML dell'email
        text_content (str, optional): Contenuto testuale dell'email
    
    Returns:
        bool: True se l'invio è riuscito, False altrimenti
    """
    # Verifica che sia presente almeno un tipo di contenuto
    if not html_content and not text_content:
        logger.error("Impossibile inviare email: nessun contenuto specificato")
        return False
    
    # Ottiene l'API key da variabile d'ambiente
    api_key = os.environ.get('SENDGRID_API_KEY')
    if not api_key:
        logger.error("SENDGRID_API_KEY non configurata nelle variabili d'ambiente")
        return False
    
    # Configura l'email
    from_email = os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@documentms.com')
    
    # Crea il messaggio
    message = Mail(
        from_email=Email(from_email),
        to_emails=To(to_email),
        subject=subject
    )
    
    # Aggiungi il contenuto appropriato
    if html_content:
        from sendgrid.helpers.mail import HtmlContent
        message.content = HtmlContent(html_content)
    elif text_content:
        from sendgrid.helpers.mail import PlainTextContent
        message.content = PlainTextContent(text_content)
    
    # Tenta l'invio
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        status_code = response.status_code
        
        if status_code >= 200 and status_code < 300:
            logger.info(f"Email inviata con successo a {to_email}")
            return True
        else:
            logger.error(f"Errore invio email: status_code={status_code}")
            return False
    except Exception as e:
        logger.error(f"Errore invio email: {str(e)}")
        return False