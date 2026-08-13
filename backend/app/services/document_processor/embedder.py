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

    def get_device_status(self) -> str:
        """Safely returns the device type without raising exceptions."""
        try:
            if self._model and hasattr(self._model, "device"):
                return "GPU" if "cuda" in str(self._model.device).lower() else "CPU"
            
            # If model isn't loaded yet, try to safely check torch
            import torch
            return "GPU" if torch.cuda.is_available() else "CPU"
        except Exception:
            return "CPU"

# Singleton instance
embedder = Embedder()
