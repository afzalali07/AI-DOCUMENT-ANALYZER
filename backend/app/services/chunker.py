import logging
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

def chunk_document_pages(
    pages_data: List[Dict[str, Any]], 
    document_id: str, 
    filename: str,
    chunk_size: int = 1000, 
    chunk_overlap: int = 200
) -> List[Dict[str, Any]]:
    """
    Chunks a list of pages page-by-page to keep page numbers associated with each chunk.
    
    Args:
        pages_data: List of dicts with keys 'page_number' and 'text'.
        document_id: Unique string ID of the document.
        filename: Original filename of the document.
        chunk_size: Maximum size of a chunk in characters.
        chunk_overlap: Overlap between adjacent chunks.
        
    Returns:
        List of dicts representing chunks, containing:
            - text: chunk text content
            - metadata: dict of metadata (document_id, filename, page_number, chunk_index)
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    
    all_chunks = []
    chunk_global_idx = 0
    
    for page in pages_data:
        page_num = page["page_number"]
        page_text = page["text"]
        
        # If the page is empty, we skip or add a small placeholder
        if not page_text.strip():
            continue
            
        # Split the text of this page
        splits = text_splitter.split_text(page_text)
        
        for split_idx, split_text in enumerate(splits):
            chunk_metadata = {
                "document_id": document_id,
                "filename": filename,
                "page_number": page_num,
                "chunk_index": chunk_global_idx
            }
            
            all_chunks.append({
                "text": split_text,
                "metadata": chunk_metadata
            })
            chunk_global_idx += 1
            
    logger.info(f"Split document '{filename}' into {len(all_chunks)} chunks.")
    return all_chunks
