import logging
from services.openai_service import classify_document_with_ai, extract_data_from_document as extract_data_with_ai, summarize_document

logger = logging.getLogger(__name__)

def classify_document(text, file_type):
    """
    Classify a document using OpenAI's API based on its content and type.
    
    Args:
        text: The text content of the document
        file_type: The file extension or mimetype
        
    Returns:
        A string classification of the document (e.g., "Invoice", "Contract", etc.)
    """
    try:
        return classify_document_with_ai(text, file_type)
    except Exception as e:
        logger.error(f"Document classification failed: {str(e)}")
        return "Unclassified Document"

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
