"""
Rule engine module mapping issue class and geographic contexts to departments and contacts.
"""

import json
import logging
from typing import Dict, Any, Tuple

from app.config import settings

logger = logging.getLogger(__name__)


class RoutingEngine:
    """Rules engine to map complaints to departments and contacts."""

    def __init__(self):
        self.rules: Dict[str, Any] = {}

    def load_rules(self) -> bool:
        """Load mappings configuration from JSON file."""
        try:
            with open(settings.ROUTING_RULES_PATH, "r", encoding="utf-8") as f:
                self.rules = json.load(f)
            logger.info(f"Loaded routing rules from {settings.ROUTING_RULES_PATH}")
            return True
        except Exception as e:
            logger.error(f"Failed to load routing rules: {e}. Using fallback defaults.")
            self._set_fallback_rules()
            return False

    def _set_fallback_rules(self):
        """Pre-populate mappings if file load fails."""
        self.rules = {
            "department_mappings": {
                "pothole": "Roads & Infrastructure",
                "mud_road": "Roads & Infrastructure",
                "erosion": "Roads & Infrastructure",
                "footpath_damage": "Roads & Infrastructure",
                "streetlight": "Electrical & Streetlights",
                "waterlogging": "Drainage & Water",
                "manhole": "Drainage & Water",
                "dead_animal": "Sanitation",
                "encroachment": "Sanitation",
                "tree": "Parks & Environment",
                "damaged_public_property": "Public Works",
            },
            "sla_tiers_hours": {"high": 24, "medium": 48, "low": 72},
            "supervisor_contacts": {
                "Roads & Infrastructure": {
                    "name": "Supervisor Roads",
                    "phone": "+91-11-2345-1001",
                    "email": "supervisor.roads@urbanpulse.gov",
                }
            },
        }

    def resolve_department(
        self, issue_class: str, ward_id: str, severity_score: float
    ) -> Tuple[str, dict]:
        """
        Maps (issue_class, ward_id, severity_score) to assigned department name and supervisor contact.
        """
        dept_name = self.rules["department_mappings"].get(
            issue_class, "Roads & Infrastructure"
        )
        contact = self.rules["supervisor_contacts"].get(
            dept_name,
            {
                "name": "General Supervisor",
                "phone": "+91-11-2345-1000",
                "email": "supervisor@urbanpulse.gov",
            },
        )

        logger.debug(
            f"Routing engine matched {issue_class} (ward: {ward_id}, severity: {severity_score}) "
            f"-> {dept_name}"
        )
        return dept_name, contact


routing_engine = RoutingEngine()
