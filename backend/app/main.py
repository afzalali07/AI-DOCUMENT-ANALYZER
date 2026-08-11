import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routes.upload import router as upload_router
from app.routes.chat import router as chat_router
from app.services.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create uploads directory if not exists
BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))
UPLOADS_DIR = os.getenv("UPLOADS_DIR", os.path.join(BACKEND_DIR, "uploads"))
os.makedirs(UPLOADS_DIR, exist_ok=True)

@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Initializing SQLite database...")
    init_db()
    yield

# Initialize FastAPI App
app = FastAPI(
    title="AI Document Analyzer using RAG API",
    description="Full-stack backend providing PDF parsing, page-level chunking, vector indexing and LLM document interaction.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend web application access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads directory as static route
app.mount("/static/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Include Routers under /api prefix
app.include_router(upload_router, prefix="/api")
app.include_router(chat_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to the AI Document Analyzer API. Visit /docs for documentation."}

@app.get("/api/health")
async def health_check():
    """
    Diagnostic endpoint to verify connection status of ChromaDB and Gemini API.
    """
    from app.services.llm import get_llm_service
    llm_service = get_llm_service()
    gemini_status = llm_service.is_remote_available()
    
    # Try to connect to vector store
    chroma_status = False
    try:
        from app.services.vector_store import get_vector_store
        store = get_vector_store()
        # Run a simple fetch count
        count = store._collection.count()
        chroma_status = True
    except Exception as e:
        logger.error(f"Health check failed to query ChromaDB: {e}")
        count = 0
        
    return {
        "status": "healthy" if (gemini_status and chroma_status) else "degraded",
        "services": {
            "sqlite": "connected",
            "chromadb": "connected" if chroma_status else "failed",
            "gemini_api": "connected" if gemini_status else "disconnected"
        },
        "chroma_chunk_count": count
    }
