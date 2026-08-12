from typing import List
import os

class Embedder:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Embedder, cls).__new__(cls)
        return cls._instance

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            # HF caching works automatically in the background (default ~/.cache/huggingface)
            self._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            
    def encode(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Encodes a list of texts into embeddings.
        Loads the model lazily if not already loaded.
        """
        if not texts:
            return []
            
        self._load_model()
        
        # encode() returns a numpy array, we convert to list of floats for pgvector
        embeddings = self._model.encode(texts, batch_size=batch_size, show_progress_bar=False)
        return embeddings.tolist()

# Singleton instance
embedder = Embedder()
