import logging
from services.openai_service import classify_document_with_ai, extract_data_from_document as extract_data_with_ai, summarize_document

logger = logging.getLogger(__name__)

def classify_document(text, file_type):
    """
    Identifica solo il tipo di file senza classificare il contenuto.
    
    Args:
        text: Il testo contenuto nel documento (non utilizzato)
        file_type: L'estensione del file o il tipo MIME
        
    Returns:
        Una stringa che identifica il tipo di file (es. "Documento PDF", "Documento Word", ecc.)
    """
    try:
        return classify_document_with_ai(text, file_type)
    except Exception as e:
        logger.error(f"Identificazione tipo di file fallita: {str(e)}")
        return "Documento Generico"

def extract_data_from_document(text, document_type):
    """
    Extract structured data from a document based on its classification.
    
    Args:
        text: The text content of the document
        document_type: The classification of the document (e.g., "Invoice")
        
    Returns:
        A dictionary of extracted fields and values
    """
    try:
        return extract_data_with_ai(text, document_type)
    except Exception as e:
        logger.error(f"Data extraction failed: {str(e)}")
        return {"error": f"Data extraction failed: {str(e)}"}

def generate_document_summary(text):
    """
    Generate a summary of the document content.
    
    Args:
        text: The text content of the document
        
    Returns:
        A string summary of the document
    """
    try:
        return summarize_document(text)
    except Exception as e:
        logger.error(f"Document summarization failed: {str(e)}")
        return "Summary not available"
