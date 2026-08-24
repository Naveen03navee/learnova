from typing import List
import os
from google import genai
from google.genai import types
from app.core.config import settings

import time
import logging

logger = logging.getLogger("app.services.document_processor.embedder")

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

    def _load_model(self):
        """Warm up Gemini client for backwards compatibility."""
        self._get_client()

    def encode(self, texts: List[str], batch_size: int = 64) -> List[List[float]]:
        """
        Encodes a list of texts into 384-dimension embeddings via Gemini API.
        Includes automatic retry with backoff for rate limits.
        """
        if not texts:
            return []

        client = self._get_client()
        embeddings: List[List[float]] = []

        # Process in batches to avoid API payload limits
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            max_retries = 4
            success = False

            for attempt in range(max_retries):
                try:
                    response = client.models.embed_content(
                        model="models/gemini-embedding-001",
                        contents=batch,
                        config=types.EmbedContentConfig(output_dimensionality=384),
                    )
                    if response.embeddings:
                        embeddings.extend([e.values for e in response.embeddings])
                    else:
                        embeddings.extend([[0.0] * 384 for _ in batch])
                    success = True
                    break
                except Exception as e:
                    err_str = str(e)
                    if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt < max_retries - 1:
                        sleep_time = (attempt + 1) * 3
                        logger.warning(f"Rate limit hit during embedding. Retrying in {sleep_time}s... (Attempt {attempt+1}/{max_retries})")
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"Gemini embedding error: {e}")
                        break

            if not success:
                # Fallback to zero vectors if all retries failed
                embeddings.extend([[0.0] * 384 for _ in batch])

            # Small pause between batches if multiple batches exist
            if len(texts) > batch_size:
                time.sleep(0.2)

        return embeddings

    def get_device_status(self) -> str:
        """Returns API status."""
        return "Gemini API (Cloud)"

# Singleton instance
embedder = Embedder()


