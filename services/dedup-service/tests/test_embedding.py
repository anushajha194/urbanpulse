"""
Tests for CLIP Embedding computations.
"""

import math
from app.services.embedding import embedding_service


def test_embedding_dimensions():
    """
    Test that the generated embedding has 512 dimensions.
    """
    image_bytes = b"sample-test-image-12345"
    emb = embedding_service.compute_embedding(image_bytes)

    assert len(emb) == 512
    assert isinstance(emb, list)
    assert all(isinstance(val, float) for val in emb)


def test_embedding_is_normalized():
    """
    Test that the returned embedding is L2-normalized (magnitude == 1.0).
    """
    image_bytes = b"sample-test-image-12345"
    emb = embedding_service.compute_embedding(image_bytes)

    magnitude = math.sqrt(sum(val**2 for val in emb))
    assert abs(magnitude - 1.0) < 1e-5


def test_embedding_is_deterministic():
    """
    Test that the same image input produces the identical mock embedding vector.
    """
    image_bytes = b"same-image-bytes-different-requests"

    emb1 = embedding_service.compute_embedding(image_bytes)
    emb2 = embedding_service.compute_embedding(image_bytes)

    assert emb1 == emb2


def test_different_images_produce_different_embeddings():
    """
    Test that different inputs produce different mock embedding vectors.
    """
    img1 = b"image-alpha"
    img2 = b"image-beta"

    emb1 = embedding_service.compute_embedding(img1)
    emb2 = embedding_service.compute_embedding(img2)

    assert emb1 != emb2
