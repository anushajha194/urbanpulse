"""
Face and license plate blurring pipeline.

Applies Gaussian blur to detected faces and license plates before
images are stored. Two modes are available:

  - 'stub': Returns the image unchanged (for dev/testing without model weights)
  - 'model': Runs a YOLO-based face/plate detector and blurs detections

The blur mode is controlled by the BLUR_MODE setting.
"""

import io
import logging
from abc import ABC, abstractmethod

from PIL import Image, ImageFilter

from app.config import settings

logger = logging.getLogger(__name__)


class BaseBlurService(ABC):
    """Abstract base class for blur services."""

    @abstractmethod
    def blur_image(self, image_bytes: bytes) -> bytes:
        """
        Apply privacy blur to an image.

        Args:
            image_bytes: Raw image data

        Returns:
            Image bytes with faces/plates blurred
        """
        pass


class StubBlurService(BaseBlurService):
    """
    No-op blur service for development and testing.

    Returns the image unchanged. This allows the full pipeline
    to run without requiring model weights.
    """

    def blur_image(self, image_bytes: bytes) -> bytes:
        logger.debug("Stub blur: returning image unchanged")
        return image_bytes


class ModelBlurService(BaseBlurService):
    """
    Production blur service using YOLO-based detection.

    Detects faces and license plates, then applies heavy
    Gaussian blur to those regions. Assumes pretrained
    weights are available at the configured paths.
    """

    def __init__(self):
        self._face_model = None
        self._plate_model = None

    def load_models(self):
        """Load face and plate detection models."""
        try:
            from ultralytics import YOLO

            # These paths would be configured in production
            # Using YOLOv8n-face for face detection
            self._face_model = YOLO("yolov8n-face.pt")
            self._plate_model = YOLO("yolov8n-plate.pt")
            logger.info("Blur models loaded successfully")
        except Exception as e:
            logger.warning(
                f"Failed to load blur models, falling back to stub: {e}"
            )
            return False
        return True

    def blur_image(self, image_bytes: bytes) -> bytes:
        """Detect faces/plates and apply Gaussian blur."""
        image = Image.open(io.BytesIO(image_bytes))

        # Detect and blur faces
        if self._face_model:
            image = self._apply_detections(image, self._face_model)

        # Detect and blur license plates
        if self._plate_model:
            image = self._apply_detections(image, self._plate_model)

        # Convert back to bytes
        output = io.BytesIO()
        img_format = image.format or "JPEG"
        image.save(output, format=img_format, quality=90)
        output.seek(0)
        return output.read()

    def _apply_detections(self, image: Image.Image, model) -> Image.Image:
        """Run detection model and blur detected regions."""
        import numpy as np

        img_array = np.array(image)
        results = model(img_array, verbose=False)

        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                # Crop the detected region
                region = image.crop((x1, y1, x2, y2))
                # Apply heavy Gaussian blur (radius 30 for strong anonymization)
                blurred_region = region.filter(ImageFilter.GaussianBlur(radius=30))
                # Paste back
                image.paste(blurred_region, (x1, y1, x2, y2))

        return image


def create_blur_service() -> BaseBlurService:
    """
    Factory function to create the appropriate blur service.

    Returns StubBlurService for dev/testing, ModelBlurService for production.
    Falls back to StubBlurService if model loading fails.
    """
    if not settings.BLUR_ENABLED:
        logger.info("Blur disabled by configuration")
        return StubBlurService()

    if settings.BLUR_MODE == "model":
        service = ModelBlurService()
        if service.load_models():
            return service
        logger.warning("Model blur failed to load, falling back to stub")

    return StubBlurService()


# Singleton instance — created on first import
blur_service = create_blur_service()
