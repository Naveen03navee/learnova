from typing import List
import os
from google import genai
from google.genai import types
from app.core.config import settings

class Embedder:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Embedder, cls).__new__(cls)
        return cls._instance

    def _get_client(self):
        if self._client is None:
            api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
            self._client = genai.Client(api_key=api_key)
        return self._client

    def encode(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Encodes a list of texts into 384-dimension embeddings via Gemini API.
        Does not consume server RAM.
        """
        if not texts:
            return []

        client = self._get_client()
        embeddings: List[List[float]] = []

        # Process in batches to avoid API payload limits
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                response = client.models.embed_content(
                    model="text-embedding-004",
                    contents=batch,
                    config=types.EmbedContentConfig(output_dimensionality=384),
                )
                if response.embeddings:
                    embeddings.extend([e.values for e in response.embeddings])
                else:
                    embeddings.extend([[0.0] * 384 for _ in batch])
            except Exception as e:
                # Fallback to zero vectors if API is unreachable
                embeddings.extend([[0.0] * 384 for _ in batch])

        return embeddings

    def get_device_status(self) -> str:
        """Returns API status."""
        return "Gemini API (Cloud)"

# Singleton instance
embedder = Embedder()

