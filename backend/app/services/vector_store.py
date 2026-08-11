import os
import logging
from typing import List, Dict, Any, Optional
from app.services.embeddings import get_embedding_service

logger = logging.getLogger(__name__)

class VectorStoreManager:
    _instance = None
    _client = None
    _collection = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(VectorStoreManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, db_path: Optional[str] = None, collection_name: str = "document_chunks"):
        if self._client is None:
            if db_path is None:
                # Default path relative to workspace/backend
                backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                db_path = os.getenv("CHROMA_DB_PATH", os.path.join(backend_dir, "chroma_db"))
            
            logger.info(f"Initializing ChromaDB client at '{db_path}'...")
            try:
                import chromadb
                # Create persistent client
                self._client = chromadb.PersistentClient(path=db_path)
                self._collection = self._client.get_or_create_collection(name=collection_name)
                logger.info(f"ChromaDB collection '{collection_name}' initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB: {e}")
                raise RuntimeError("Unable to initialize the vector database") from e

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        """
        Adds text chunks and their embeddings to the vector database.
        
        Each chunk is expected to be a dictionary:
            - text: str
            - metadata: Dict[str, Any]
        """
        if not chunks:
            return True

        ids = []
        documents = []
        metadatas = []
        texts_to_embed = []

        for chunk in chunks:
            text = chunk["text"]
            meta = chunk["metadata"]
            
            # Generate a unique ID: docID_page_chunkIndex
            doc_id = meta["document_id"]
            page_num = meta["page_number"]
            chunk_idx = meta["chunk_index"]
            chunk_id = f"{doc_id}_{page_num}_{chunk_idx}"
            
            ids.append(chunk_id)
            documents.append(text)
            metadatas.append(meta)
            texts_to_embed.append(text)

        try:
            # Generate embeddings
            embedding_service = get_embedding_service()
            embeddings = embedding_service.get_embeddings(texts_to_embed)
            
            # Upsert into ChromaDB
            self._collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            logger.info(f"Successfully added {len(chunks)} chunks to ChromaDB.")
            return True
        except Exception as e:
            logger.error(f"Failed to add chunks to ChromaDB: {e}")
            return False

    def delete_document(self, document_id: str) -> bool:
        """
        Deletes all chunks associated with a document_id.
        """
        try:
            self._collection.delete(where={"document_id": document_id})
            logger.info(f"Deleted document '{document_id}' chunks from ChromaDB.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document '{document_id}' from ChromaDB: {e}")
            return False

    def query_similarity(
        self, 
        query_text: str, 
        n_results: int = 5, 
        document_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Queries ChromaDB for similar text chunks, optionally filtered by document IDs.
        """
        try:
            if not query_text or not query_text.strip() or n_results < 1:
                return []
            collection_count = self._collection.count()
            if collection_count == 0:
                return []

            # Get embedding for query
            embedding_service = get_embedding_service()
            query_embedding = embedding_service.get_embedding(query_text)
            
            # Setup filter where clause
            where_clause = None
            if document_ids:
                if len(document_ids) == 1:
                    where_clause = {"document_id": document_ids[0]}
                else:
                    where_clause = {"document_id": {"$in": document_ids}}

            # Run query
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, collection_count),
                where=where_clause
            )

            # Re-format output
            formatted_results = []
            if results and results["documents"]:
                # results['documents'] is list of list, retrieve first element
                docs = results["documents"][0]
                metas = results["metadatas"][0]
                distances = results["distances"][0] if "distances" in results else [0.0] * len(docs)
                ids = results["ids"][0]

                for idx in range(len(docs)):
                    formatted_results.append({
                        "id": ids[idx],
                        "text": docs[idx],
                        "metadata": metas[idx],
                        "distance": distances[idx]
                    })
            return formatted_results
        except Exception as e:
            logger.error(f"Error querying similarity in ChromaDB: {e}")
            return []

# Instantiate singleton helper
vector_store_manager = None

def get_vector_store() -> VectorStoreManager:
    global vector_store_manager
    if vector_store_manager is None:
        vector_store_manager = VectorStoreManager()
    return vector_store_manager
