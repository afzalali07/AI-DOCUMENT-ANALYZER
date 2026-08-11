from pydantic import BaseModel, Field
from typing import List, Optional

class SourceCitation(BaseModel):
    document_id: str
    filename: str
    page: int
    text: str

class MessageModel(BaseModel):
    id: Optional[int] = None
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str
    sources: Optional[List[SourceCitation]] = None

class ChatSessionModel(BaseModel):
    id: str
    title: str
    created_at: str

class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10000)
    session_id: Optional[str] = None
    document_ids: Optional[List[str]] = Field(default=None, description="List of document IDs to query. If empty, queries all documents.")

class ChatResponse(BaseModel):
    answer: str
    session_id: str
    sources: List[SourceCitation]

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    page_count: int
    uploaded_at: str

class DocumentSummaryResponse(BaseModel):
    id: str
    filename: str
    summary: Optional[str] = None
    key_findings: Optional[List[str]] = None
    important_dates: Optional[List[str]] = None
