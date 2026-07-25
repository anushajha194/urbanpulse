"""
Stub detector for local development and testing.

Produces deterministic detection results based on image content hash,
ensuring reproducible test behavior. Cycles through all 11 issue classes
and generates confidence values spanning both above and below the
CONFIDENCE_THRESHOLD (0.4), so both the 'assigned' and 'under_review'
code paths are exercised.
"""

import hashlib
import logging

from app.models.base import BaseDetector, DetectionResult, ALL_CLASSES

logger = logging.getLogger(__name__)


class StubDetector(BaseDetector):
    """
    Deterministic dummy detector for development and testing.

    Uses image content hash to produce reproducible results.
    """

    def __init__(self):
        self._loaded = False

    def load(self) -> bool:
        """Stub always loads successfully."""
        self._loaded = True
        logger.info("Stub detector loaded (no real model)")
        return True

    def detect(self, image_bytes: bytes) -> list[DetectionResult]:
        """
        Generate a deterministic detection based on image hash.

        The hash determines:
        - Which issue class is "detected"
        - The confidence score (spread across [0.15, 0.95])
        """
        if not self._loaded:
            return []

        # Hash the image content for deterministic results
        img_hash = hashlib.md5(image_bytes).hexdigest()
        hash_int = int(img_hash, 16)

        # Select issue class based on hash
        class_index = hash_int % len(ALL_CLASSES)
        issue_class = ALL_CLASSES[class_index]

        # Generate confidence from hash — spread across [0.15, 0.95]
        # This ensures some results are below threshold (0.4) and some above
        confidence_raw = ((hash_int >> 8) % 100) / 100.0
        confidence = 0.15 + (confidence_raw * 0.80)  # Range: [0.15, 0.95]

        # Determine model type based on the class
        from app.models.base import YOLO_CLASSES
        model_type = "yolo" if issue_class in YOLO_CLASSES else "segmentation"

        detection = DetectionResult(
            issue_class=issue_class,
            confidence=round(confidence, 4),
            model_type=model_type,
        )

        logger.info(
            f"Stub detection: {issue_class} ({confidence:.2f}) "
            f"[hash: {img_hash[:8]}]"
        )

        return [detection]

    @property
    def model_name(self) -> str:
        return "Stub-detector"
