"""
Dynamic file-based text templates rendering service.
Loads templates from files under templates/ folder to avoid hardcoding strings.
"""

import os
import logging
from typing import Dict

from app.config import settings

logger = logging.getLogger(__name__)


class TemplateService:
    """Manages file-based text templates loading and formatting."""

    def __init__(self):
        self._cache: Dict[str, str] = {}

    def _get_template_path(self, name: str) -> str:
        # Check standard relative templates folder or configured path
        return os.path.join(settings.TEMPLATES_DIR, f"{name}.txt")

    def _load_template_content(self, name: str) -> str:
        """Reads template file from disk, caching the result."""
        if name in self._cache:
            return self._cache[name]

        path = self._get_template_path(name)
        if not os.path.exists(path):
            # Fallback if custom path doesn't align in specific worker runtimes
            fallback_path = os.path.join(
                os.path.dirname(__file__), "..", "templates", f"{name}.txt"
            )
            if os.path.exists(fallback_path):
                path = fallback_path

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self._cache[name] = content
            logger.debug(f"Loaded template '{name}' from {path}")
            return content
        except Exception as e:
            logger.error(f"Failed to load template file '{name}' at {path}: {e}")
            raise FileNotFoundError(f"Template file '{name}' not found.")

    def render(self, template_name: str, context: dict) -> str:
        """
        Loads the template file and substitutes placeholders with context variables.
        """
        content = self._load_template_content(template_name)
        try:
            # Replaces placeholders like {complaint_id} with values from dict
            return content.format(**context)
        except KeyError as ke:
            logger.error(f"Missing context variable {ke} for template {template_name}")
            # Fallback to key-safe formatting or return as-is
            return content


template_service = TemplateService()
