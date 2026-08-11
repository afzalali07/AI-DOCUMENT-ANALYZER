import os
import uuid
import shutil
import logging
from typing import List
from fastapi import APIRouter, File, UploadFile, Query, HTTPException

from app.models.schemas import DocumentResponse, DocumentSummaryResponse
from app.services.database import (
    add_document, 
    get_documents, 
    get_document, 
    delete_document as db_delete_document
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
UPLOADS_DIR = os.getenv("UPLOADS_DIR", os.path.join(BACKEND_DIR, "uploads"))
os.makedirs(UPLOADS_DIR, exist_ok=True)

def process_and_index_pdf(file_path: str, filename: str, doc_id: str, use_ocr: bool):
    """
    Background or helper task to parse, chunk, embed, and summarize a PDF document.
    """
    from app.services.chunker import chunk_document_pages
    from app.services.llm import get_llm_service
    from app.services.pdf_parser import extract_text_from_pdf
    from app.services.vector_store import get_vector_store

    try:
        logger.info(f"Starting text extraction for {filename}...")
        # 1. Parse PDF
        pages_data = extract_text_from_pdf(file_path, use_ocr=use_ocr)
        page_count = len(pages_data)
        
        # Collect full text for summarization
        full_text = "\n".join([page["text"] for page in pages_data if page["text"]])
        if not full_text.strip():
            raise ValueError("The PDF contains no extractable text. Enable OCR for scanned documents.")
        
        # 2. Chunk text
        logger.info(f"Chunking {filename}...")
        chunks = chunk_document_pages(
            pages_data=pages_data,
            document_id=doc_id,
            filename=filename
        )
        
        # 3. Embed and store chunks in ChromaDB
        logger.info(f"Indexing chunks for {filename} into vector store...")
        vector_store = get_vector_store()
        vector_success = vector_store.add_chunks(chunks)
        
        if not vector_success:
            raise RuntimeError("Failed to write document embeddings")
            
        # 4. Generate Summaries via LLM
        logger.info(f"Generating LLM summary for {filename}...")
        llm_service = get_llm_service()
        summary_data = llm_service.generate_summary(full_text)
        
        # 5. Save to SQLite database
        file_size = os.path.getsize(file_path)
        db_success = add_document(
            doc_id=doc_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            page_count=page_count,
            summary=summary_data.get("summary"),
            key_findings=summary_data.get("key_findings"),
            important_dates=summary_data.get("important_dates")
        )
        
        if db_success:
            logger.info(f"Successfully processed and indexed document: {filename} ({doc_id})")
        else:
            raise RuntimeError("Failed to save document metadata")
            
    except Exception as e:
        logger.exception(f"Unhandled error processing document {filename}: {e}")
        raise

@router.post("/upload", response_model=List[DocumentResponse])
async def upload_documents(
    files: List[UploadFile] = File(...),
    use_ocr: bool = Query(default=False, description="Enable OCR fallback for scanned pages")
):
    """
    Accepts PDF files, saves them, and starts text extraction, embedding, indexing and summarization.
    """
    processed_docs = []
    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF file is required.")
    
    for file in files:
        safe_name = os.path.basename(file.filename or "")
        if not safe_name.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF.")
            
        # Generate unique ID for this document
        doc_id = str(uuid.uuid4())
        
        # Define storage path
        file_ext = os.path.splitext(safe_name)[1].lower()
        stored_filename = f"{doc_id}{file_ext}"
        file_path = os.path.join(UPLOADS_DIR, stored_filename)
        
        # Save file to disk
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            logger.error(f"Failed to save file {file.filename} to disk: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save {file.filename}")
            
        file_size = os.path.getsize(file_path)
        
        # Process and index synchronously for upload response (or background tasks)
        # We'll do it inline so we can return the summaries/page counts directly,
        # but catch exceptions.
        try:
            process_and_index_pdf(file_path, safe_name, doc_id, use_ocr)
        except Exception as exc:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=422, detail=f"Failed to process {safe_name}: {exc}") from exc
        
        # Fetch newly added doc from DB to get actual page count
        doc_meta = get_document(doc_id)
        page_count = doc_meta["page_count"] if doc_meta else 0
        
        processed_docs.append(DocumentResponse(
            id=doc_id,
            filename=safe_name,
            file_size=file_size,
            page_count=page_count,
            uploaded_at=doc_meta["uploaded_at"] if doc_meta else ""
        ))
        
    return processed_docs

@router.get("/", response_model=List[DocumentResponse])
async def list_documents():
    """
    Returns a list of all uploaded and indexed documents.
    """
    docs = get_documents()
    return docs

@router.get("/{doc_id}/summary", response_model=DocumentSummaryResponse)
async def get_document_summary(doc_id: str):
    """
    Returns the generated executive summary, findings, and dates for a specific document.
    """
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    return DocumentSummaryResponse(
        id=doc["id"],
        filename=doc["filename"],
        summary=doc["summary"],
        key_findings=doc["key_findings"],
        important_dates=doc["important_dates"]
    )

@router.delete("/{doc_id}")
async def delete_document_endpoint(doc_id: str):
    """
    Deletes a document from the system (disk, SQLite, and vector database).
    """
    from app.services.vector_store import get_vector_store

    # 1. Delete from SQLite and get file path
    file_path = db_delete_document(doc_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    # 2. Delete file from disk
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            logger.error(f"Failed to delete file {file_path} from disk: {e}")
            
    # 3. Delete chunks from ChromaDB
    try:
        get_vector_store().delete_document(doc_id)
    except Exception as exc:
        logger.warning("Document metadata was deleted, but vector cleanup failed: %s", exc)
    
    return {"status": "success", "message": f"Document {doc_id} successfully deleted."}

@router.post("/{doc_id}/regenerate", response_model=DocumentSummaryResponse)
async def regenerate_document_summary(doc_id: str):
    """
    Regenerates the AI summary dashboard (executive summary, findings, and dates)
    for a document that has already been uploaded, useful if Ollama was offline.
    """
    from app.services.llm import get_llm_service
    from app.services.pdf_parser import extract_text_from_pdf

    # 1. Fetch document metadata from SQLite
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    # 2. Check if the AI service is available
    llm_service = get_llm_service()
    if not llm_service.is_available():
        raise HTTPException(status_code=503, detail="The AI summarization service is currently offline. Please try again later.")
        
    file_path = doc["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Source PDF file not found on disk.")
        
    try:
        logger.info(f"Regenerating summary for {doc['filename']}...")
        # 3. Extract text from the PDF
        pages_data = extract_text_from_pdf(file_path, use_ocr=False)
        full_text = "\n".join([page["text"] for page in pages_data if page["text"]])
        
        # 4. Generate summary
        summary_data = llm_service.generate_summary(full_text)
        
        # 5. Update SQLite
        db_success = add_document(
            doc_id=doc_id,
            filename=doc["filename"],
            file_path=doc["file_path"],
            file_size=doc["file_size"],
            page_count=doc["page_count"],
            summary=summary_data.get("summary"),
            key_findings=summary_data.get("key_findings"),
            important_dates=summary_data.get("important_dates")
        )
        
        if not db_success:
            raise HTTPException(status_code=500, detail="Failed to save regenerated summary to database.")
            
        return DocumentSummaryResponse(
            id=doc_id,
            filename=doc["filename"],
            summary=summary_data.get("summary"),
            key_findings=summary_data.get("key_findings"),
            important_dates=summary_data.get("important_dates")
        )
    except Exception as e:
        logger.exception(f"Failed to regenerate summary for {doc['filename']}: {e}")
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {str(e)}")
