import datetime
from sqlalchemy import or_, and_
from flask import current_app
from models import Document, Tag, User

def search_documents(query, user_id, doc_type=None, from_date=None, to_date=None, tags=None):
    """
    Search for documents based on various criteria.
    
    Args:
        query: The search query string
        user_id: The user performing the search
        doc_type: Filter by document type/classification
        from_date: Filter documents created after this date
        to_date: Filter documents created before this date
        tags: List of tag IDs to filter by
        
    Returns:
        List of Document objects matching the search criteria
    """
    # Start with base query for documents the user has access to
    base_query = Document.query.filter(
        or_(
            Document.owner_id == user_id,
            Document.shared_with.any(User.id == user_id)
        )
    )
    
    # Filter by document type/classification if specified
    if doc_type:
        base_query = base_query.filter(Document.classification == doc_type)
    
    # Filter by creation date range if specified
    if from_date:
        base_query = base_query.filter(Document.created_at >= from_date)
    
    if to_date:
        # Add one day to include the end date
        end_date = to_date + datetime.timedelta(days=1)
        base_query = base_query.filter(Document.created_at < end_date)
    
    # Filter by tags if specified
    if tags and len(tags) > 0:
        for tag_id in tags:
            base_query = base_query.filter(Document.tags.any(Tag.id == tag_id))
    
    # Apply text search if query string is provided
    if query:
        search_query = f"%{query}%"
        base_query = base_query.filter(
            or_(
                Document.title.ilike(search_query),
                Document.description.ilike(search_query),
                Document.content_text.ilike(search_query),
                Document.original_filename.ilike(search_query)
            )
        )
    
    # Exclude archived documents by default
    base_query = base_query.filter(Document.is_archived == False)
    
    # Order by relevance (if search query) or recency
    if query:
        # Ordering by relevance would depend on database capabilities
        # For simple cases, we just order by recency
        return base_query.order_by(Document.updated_at.desc()).all()
    else:
        return base_query.order_by(Document.updated_at.desc()).all()

def search_document_content(text_query):
    """
    Perform a full-text search on document content.
    
    Args:
        text_query: The text to search for in document content
        
    Returns:
        List of Document objects with matching content
    """
    # This is a simple implementation; in a production system,
    # you might use a dedicated search engine like Elasticsearch
    search_query = f"%{text_query}%"
    
    results = Document.query.filter(
        Document.content_text.ilike(search_query)
    ).order_by(Document.updated_at.desc()).all()
    
    return results

def advanced_search(criteria):
    """
    Perform an advanced search with multiple criteria.
    
    Args:
        criteria: Dictionary of search criteria
        
    Returns:
        List of Document objects matching all criteria
    """
    query = Document.query
    
    # Handle each search criterion
    if 'text' in criteria and criteria['text']:
        search_text = f"%{criteria['text']}%"
        query = query.filter(
            or_(
                Document.title.ilike(search_text),
                Document.description.ilike(search_text),
                Document.content_text.ilike(search_text),
                Document.original_filename.ilike(search_text)
            )
        )
    
    if 'owner_id' in criteria and criteria['owner_id']:
        query = query.filter(Document.owner_id == criteria['owner_id'])
    
    if 'classification' in criteria and criteria['classification']:
        query = query.filter(Document.classification == criteria['classification'])
    
    if 'file_type' in criteria and criteria['file_type']:
        query = query.filter(Document.file_type == criteria['file_type'])
    
    if 'created_after' in criteria and criteria['created_after']:
        query = query.filter(Document.created_at >= criteria['created_after'])
    
    if 'created_before' in criteria and criteria['created_before']:
        query = query.filter(Document.created_at <= criteria['created_before'])
    
    if 'tags' in criteria and criteria['tags']:
        for tag_id in criteria['tags']:
            query = query.filter(Document.tags.any(Tag.id == tag_id))
    
    if 'exclude_archived' in criteria and criteria['exclude_archived']:
        query = query.filter(Document.is_archived == False)
    
    # Order results by specified field or default to recency
    order_by = criteria.get('order_by', 'updated_at')
    order_dir = criteria.get('order_dir', 'desc')
    
    if order_dir.lower() == 'desc':
        query = query.order_by(getattr(Document, order_by).desc())
    else:
        query = query.order_by(getattr(Document, order_by))
    
    return query.all()
