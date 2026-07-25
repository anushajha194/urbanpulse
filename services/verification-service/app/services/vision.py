"""
Visual change comparison service using pure Python/Pillow.
Computes a similarity index between before and after photos.
"""

import io
import logging
from PIL import Image, ImageChops, ImageStat

logger = logging.getLogger(__name__)


class VisualComparator:
    """Computes a structural similarity index proxy based on pixel metrics."""

    def compute_similarity(self, before_bytes: bytes, after_bytes: bytes) -> float:
        """
        Compare before and after images.
        Returns:
            Float similarity score in [0.0, 1.0] (1.0 = identical).
        """
        try:
            # 1. Open images and convert to Grayscale
            img_before = Image.open(io.BytesIO(before_bytes)).convert("L")
            img_after = Image.open(io.BytesIO(after_bytes)).convert("L")

            # 2. Resize to common resolution to compare structural grids
            img_before = img_before.resize((256, 256))
            img_after = img_after.resize((256, 256))

            # 3. Calculate difference image
            diff = ImageChops.difference(img_before, img_after)

            # 4. Calculate Root Mean Square (RMS) difference
            stat = ImageStat.Stat(diff)
            rms = stat.rms[0]  # root mean square value of pixels

            # Normalize RMS to [0.0, 1.0]
            normalized_rms = rms / 255.0

            # Similarity is inverse of difference
            similarity = 1.0 - normalized_rms

            logger.info(f"Visual similarity calculated: {similarity:.4f}")
            return similarity

        except Exception as e:
            logger.error(f"Failed to calculate visual similarity: {e}")
            # Fallback average
            return 0.5


visual_comparator = VisualComparator()
