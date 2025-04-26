import logging
import os
import re

# Semplice sistema di classificazione dei documenti senza API di IA
def classify_document_with_ai(text, file_type):
    """
    Identifica solo il tipo di file senza classificare il contenuto.
    
    Args:
        text: Il testo contenuto nel documento (non utilizzato)
        file_type: L'estensione del file o il tipo MIME
        
    Returns:
        Una stringa che identifica il tipo di file (es. "Documento PDF", "Documento Word", ecc.)
    """
    logging.info(f"Identificazione tipo di file: {file_type}")
    
    # Rimozione delle classificazioni dei documenti per richiesta del cliente
    # Non verranno più mostrate etichette come "Documento PDF" o "Unclassified"
    return ""


def extract_data_from_document(text, document_type):
    """
    Estrae dati strutturati da un documento in base alla sua classificazione.
    Implementazione di base senza API di OpenAI.
    
    Args:
        text: Il testo contenuto nel documento
        document_type: La classificazione del documento (es. "Fattura")
        
    Returns:
        Un dizionario di campi e valori estratti
    """
    if not text:
        return {}
    
    result = {"tipo_documento": document_type}
    
    # Prova ad estrarre date dal testo (formato GG/MM/AAAA o equivalenti)
    date_pattern = r'\b(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})\b'
    dates = re.findall(date_pattern, text)
    if dates:
        result["date"] = dates[:3]  # Limita a 3 date
    
    # Prova ad estrarre importi (€)
    amount_pattern = r'(\d+[,.]\d+)(?:\s*€|\s*[Ee][Uu][Rr][Oo])?'
    amounts = re.findall(amount_pattern, text)
    if amounts:
        result["importi"] = amounts[:5]  # Limita a 5 importi
    
    # Prova ad estrarre email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    if emails:
        result["email"] = emails
    
    # Cerca numeri di telefono
    phone_pattern = r'\b(?:\+\d{1,3}[\s-]?)?\(?\d{3,4}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b'
    phones = re.findall(phone_pattern, text)
    if phones:
        result["telefoni"] = phones
    
    # Estrai ulteriori dati in base al tipo di documento
    if document_type.lower() == "fattura":
        # Cerca numeri di fattura (spesso preceduti da "fattura n." o simili)
        invoice_pattern = r'[Ff]attura\s+(?:[Nn]\.?|[Nn]umero:?)\s*(\w+[-/\d]+)'
        invoice_numbers = re.findall(invoice_pattern, text)
        if invoice_numbers:
            result["numero_fattura"] = invoice_numbers[0]
            
        # Cerca partita IVA
        vat_pattern = r'[Pp]artita\s+IVA\s*:?\s*(\d{11})'
        vat_numbers = re.findall(vat_pattern, text)
        if vat_numbers:
            result["partita_iva"] = vat_numbers[0]
    
    elif document_type.lower() == "curriculum" or "cv" in document_type.lower():
        # Cerca nome e cognome (se appare all'inizio, spesso con caratteri maiuscoli)
        name_pattern = r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
        names = re.findall(name_pattern, text, re.MULTILINE)
        if names:
            result["nome_completo"] = names[0]
    
    return result


def summarize_document(text):
    """
    Genera un riassunto del contenuto del documento.
    Implementazione di base senza API di OpenAI.
    
    Args:
        text: Il testo contenuto nel documento
        
    Returns:
        Un riassunto del testo come stringa
    """
    if not text:
        return "Riassunto non disponibile"
    
    # Trova le frasi più significative
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Prendiamo solo le prime frasi (al massimo 3)
    if len(sentences) > 0:
        summary = ". ".join(sentences[:min(3, len(sentences))])
        return summary + "..."
    
    return "Riassunto non disponibile"