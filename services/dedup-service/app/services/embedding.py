"""
CLIP Image Embedding Generation.
Supports production sentence-transformers models and a deterministic stub mode.
"""

import hashlib
import io
import logging
from typing import List
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Computes normalized 512-dimensional image embeddings."""

    def __init__(self):
        self._model = None

    def load_model(self) -> bool:
        """Loads sentence-transformers model if configured."""
        if settings.EMBEDDING_MODE == "stub":
            logger.info("Using stub embedding service (dev mode)")
            return True

        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(settings.CLIP_MODEL_NAME)
            logger.info(f"Loaded CLIP model: {settings.CLIP_MODEL_NAME}")
            return True
        except Exception as e:
            logger.error(f"Failed to load sentence-transformers model: {e}")
            return False

    def compute_embedding(self, image_bytes: bytes) -> List[float]:
        """
        Compute normalized 512-dim CLIP embedding.
        """
        if settings.EMBEDDING_MODE == "stub" or self._model is None:
            return self._compute_stub_embedding(image_bytes)

        try:
            from PIL import Image
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            # SentenceTransformer computes the image embeddings
            emb = self._model.encode(image)
            # L2 Normalize
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            return emb.tolist()
        except Exception as e:
            logger.error(f"Embedding computation failed: {e}. Falling back to stub.")
            return self._compute_stub_embedding(image_bytes)

    def _compute_stub_embedding(self, image_bytes: bytes) -> List[float]:
        """
        Generates a deterministic L2-normalized 512-dim vector from image hash.
        This ensures that identical images produce identical mock embeddings.
        """
        h = hashlib.sha256(image_bytes).digest()
        # Seed numpy generator with the image hash
        seed = int.from_bytes(h[:4], "big")
        rng = np.random.default_rng(seed)

        # Generate 512 numbers, then L2-normalize
        vec = rng.normal(size=512)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()


embedding_service = EmbeddingService()
