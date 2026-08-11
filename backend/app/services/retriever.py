import logging
from typing import List, Dict, Any, Optional
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)

def retrieve_relevant_chunks(
    query: str, 
    document_ids: Optional[List[str]] = None, 
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Retrieves the top N most similar chunks for a given query.
    
    Args:
        query: User question string.
        document_ids: List of document IDs to restrict search to. If None/empty, searches all.
        limit: Number of documents to retrieve.
        
    Returns:
        List of dictionaries containing matching chunks and their metadata.
    """
    logger.info(f"Retrieving relevant chunks for query: '{query[:50]}...' Filter docs: {document_ids}")
    
    vector_store = get_vector_store()
    results = vector_store.query_similarity(
        query_text=query,
        n_results=limit,
        document_ids=document_ids
    )
    
    logger.info(f"Retrieved {len(results)} chunks from vector store.")
    return results
