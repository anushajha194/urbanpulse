"""
Core weighted scoring engine.
Loads rules from JSON configuration and calculates severity/priority scores.
"""

import json
import logging
from typing import Dict, Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class ScoringEngine:
    """Calculates severity and priority scores using weights configuration."""

    def __init__(self):
        self._set_fallback_rules()

    def load_rules(self) -> bool:
        """Load weights and multipliers config from JSON path."""
        try:
            with open(settings.SCORING_RULES_PATH, "r", encoding="utf-8") as f:
                self.rules = json.load(f)
            logger.info(f"Loaded scoring rules from {settings.SCORING_RULES_PATH}")
            return True
        except Exception as e:
            logger.error(f"Failed to load scoring rules: {e}. Using fallback defaults.")
            self._set_fallback_rules()
            return False

    def _set_fallback_rules(self):
        """Standard backup weights if config load fails."""
        self.rules = {
            "base_severity": {
                "pothole": 45,
                "streetlight": 30,
                "manhole": 60,
                "dead_animal": 40,
                "tree": 50,
                "damaged_public_property": 35,
                "waterlogging": 65,
                "mud_road": 40,
                "erosion": 55,
                "footpath_damage": 35,
                "encroachment": 50,
            },
            "zone_multipliers": {
                "school_zone": 1.5,
                "hospital_zone": 1.5,
                "default": 1.0,
            },
            "traffic_boosts": {
                "low": 0,
                "medium": 10,
                "high": 25,
            },
            "segmentation_area_thresholds": [
                {"threshold_pixels": 100000, "multiplier": 1.3},
                {"threshold_pixels": 50000, "multiplier": 1.15},
            ],
        }

    def calculate_scores(
        self,
        issue_class: str,
        location_context: dict,
        mask_area: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Calculate severity and priority out of 100.

        Formula:
        - Severity = Base Severity * Area Multiplier (capped at 100)
        - Priority = Severity * Zone Multipliers + Traffic Boost (capped at 100)
        """
        # 1. Base Severity
        base_sev = self.rules["base_severity"].get(issue_class, 40.0)

        # 2. Area Multiplier (segmentation classes)
        area_mult = 1.0
        if mask_area is not None:
            # Thresholds are parsed in descending order of size
            thresholds = self.rules.get("segmentation_area_thresholds", [])
            for rule in sorted(thresholds, key=lambda x: x["threshold_pixels"], reverse=True):
                if mask_area >= rule["threshold_pixels"]:
                    area_mult = rule["multiplier"]
                    break

        severity = min(100.0, float(base_sev * area_mult))

        # 3. Zone Multipliers
        zone_mult = 1.0
        if location_context.get("school_zone"):
            zone_mult *= self.rules["zone_multipliers"].get("school_zone", 1.5)
        if location_context.get("hospital_zone"):
            zone_mult *= self.rules["zone_multipliers"].get("hospital_zone", 1.5)

        # 4. Traffic boost
        traffic_tier = location_context.get("traffic_density", "low")
        traffic_boost = self.rules["traffic_boosts"].get(traffic_tier, 0.0)

        # Priority calculation
        priority = min(100.0, float(severity * zone_mult + traffic_boost))

        # Underflow safety check
        severity = max(0.0, severity)
        priority = max(0.0, priority)

        logger.debug(
            f"Scoring: class={issue_class}, mask={mask_area} -> "
            f"Severity={severity:.1f}, Priority={priority:.1f}"
        )

        return {
            "severity": round(severity, 2),
            "priority": round(priority, 2),
        }


scoring_engine = ScoringEngine()
