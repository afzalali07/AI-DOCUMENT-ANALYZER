import logging
from typing import List

logger = logging.getLogger(__name__)

class EmbeddingService:
    _instance = None
    _model = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(EmbeddingService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Load the model only once
        if self._model is None:
            logger.info(f"Loading SentenceTransformer model '{model_name}'...")
            try:
                # Loading PyTorch is expensive; defer it until embeddings are used.
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(model_name)
                logger.info(f"Model '{model_name}' loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load SentenceTransformer model '{model_name}': {e}")
                raise RuntimeError(f"Unable to load embedding model '{model_name}'") from e

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text strings.
        """
        if not texts:
            return []
        try:
            # sentence-transformers encode returns numpy arrays, we convert to list of floats
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise RuntimeError("Unable to generate document embeddings") from e

    def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.
        """
        return self.get_embeddings([text])[0]

# Instantiate singleton instance
embedding_service = None

def get_embedding_service() -> EmbeddingService:
    global embedding_service
    if embedding_service is None:
        embedding_service = EmbeddingService()
    return embedding_service
