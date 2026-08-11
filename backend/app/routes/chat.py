import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import ChatRequest, ChatResponse, SourceCitation, MessageModel, ChatSessionModel
from app.services.database import (
    create_chat_session,
    get_chat_sessions,
    delete_chat_session,
    add_chat_message,
    get_chat_messages,
    update_session_title
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

@router.get("/sessions", response_model=List[ChatSessionModel])
async def list_sessions():
    """
    Returns a list of all active chat sessions.
    """
    return get_chat_sessions()

@router.post("/sessions", response_model=ChatSessionModel)
async def create_session(title: Optional[str] = Query(default="New Chat")):
    """
    Creates a new chat session.
    """
    session_id = str(uuid.uuid4())
    success = create_chat_session(session_id, title)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create chat session.")
    
    # Retrieve newly created session
    sessions = get_chat_sessions()
    for s in sessions:
        if s["id"] == session_id:
            return ChatSessionModel(**s)
            
    raise HTTPException(status_code=500, detail="Failed to retrieve created session.")

@router.get("/sessions/{session_id}/history", response_model=List[MessageModel])
async def get_session_history(session_id: str):
    """
    Returns all message history for a specific session.
    """
    messages = get_chat_messages(session_id)
    return messages

@router.delete("/sessions/{session_id}")
async def delete_session_endpoint(session_id: str):
    """
    Deletes a chat session and all its messages.
    """
    success = delete_chat_session(session_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete chat session.")
    return {"status": "success", "message": f"Session {session_id} successfully deleted."}

@router.post("/", response_model=ChatResponse)
async def ask_question(request: ChatRequest):
    """
    Submits a question to the RAG pipeline.
    """
    from app.services.llm import get_llm_service
    from app.services.retriever import retrieve_relevant_chunks

    session_id = request.session_id
    
    # 1. Create session if it doesn't exist
    if not session_id:
        session_id = str(uuid.uuid4())
        create_chat_session(session_id, "New Chat")
        logger.info(f"Created new implicit session {session_id} for query.")
        
    # 2. Check if this is the first message (to update title later)
    existing_messages = get_chat_messages(session_id)
    is_first_message = len(existing_messages) == 0
    
    # 3. Retrieve relevant chunks from ChromaDB
    # Limit to 4-5 chunks depending on chunk size to avoid context limit issues
    chunks = retrieve_relevant_chunks(
        query=request.query,
        document_ids=request.document_ids,
        limit=5
    )
    
    # 4. Generate answer using Ollama/Llama3
    llm_service = get_llm_service()
    answer, citations = llm_service.generate_answer(
        query=request.query,
        context_chunks=chunks,
        chat_history=existing_messages
    )
    
    # 5. Log messages to SQLite history
    add_chat_message(session_id=session_id, role="user", content=request.query, sources=None)
    add_chat_message(session_id=session_id, role="assistant", content=answer, sources=citations)
    
    # 6. Update session title if first message
    if is_first_message:
        # Generate title from first few words of the user query
        words = request.query.split()
        title = " ".join(words[:5]) + ("..." if len(words) > 5 else "")
        update_session_title(session_id, title)
        logger.info(f"Updated session title to: '{title}'")
        
    # 7. Map citations to SourceCitation Pydantic schema
    formatted_citations = []
    for cit in citations:
        formatted_citations.append(SourceCitation(
            document_id=cit["document_id"],
            filename=cit["filename"],
            page=cit["page"],
            text=cit["text"]
        ))
        
    return ChatResponse(
        answer=answer,
        session_id=session_id,
        sources=formatted_citations
    )
