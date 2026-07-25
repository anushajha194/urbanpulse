"""
Unit tests for the weighted scoring engine formula.
"""

from app.services.engine import ScoringEngine


def test_engine_load_rules():
    """Verify rules are parsed correctly."""
    engine = ScoringEngine()
    loaded = engine.load_rules()
    assert loaded is True
    assert "pothole" in engine.rules["base_severity"]
    assert "school_zone" in engine.rules["zone_multipliers"]


def test_low_severity_in_low_traffic_zone():
    """
    Test low severity issue in a low-traffic, non-safety zone.
    Base streetlight = 30. No multipliers. No boosts.
    Expected: Severity = 30, Priority = 30.
    """
    engine = ScoringEngine()
    engine.load_rules()

    context = {
        "school_zone": False,
        "hospital_zone": False,
        "traffic_density": "low",
    }

    scores = engine.calculate_scores(
        issue_class="streetlight",
        location_context=context,
    )

    assert scores["severity"] == 30.0
    assert scores["priority"] == 30.0


def test_max_priority_in_school_zone():
    """
    Test max severity issue in a school zone with traffic.
    Base waterlogging = 65.
    With large area mask (>100,000 pixels) -> 65 * 1.3 = 84.5 severity.
    School zone multiplier = 1.5 -> 84.5 * 1.5 = 126.75 priority.
    Expected priority capped at 100.
    """
    engine = ScoringEngine()
    engine.load_rules()

    context = {
        "school_zone": True,
        "hospital_zone": False,
        "traffic_density": "high",
    }

    scores = engine.calculate_scores(
        issue_class="waterlogging",
        location_context=context,
        mask_area=120000.0,
    )

    assert scores["severity"] == 84.5
    assert scores["priority"] == 100.0  # Capped at 100


def test_pothole_in_hospital_zone_with_medium_traffic():
    """
    Base pothole = 45.
    Hospital zone multiplier = 1.5 -> 45 * 1.5 = 67.5.
    Medium traffic boost = 10 -> 67.5 + 10 = 77.5.
    """
    engine = ScoringEngine()
    engine.load_rules()

    context = {
        "school_zone": False,
        "hospital_zone": True,
        "traffic_density": "medium",
    }

    scores = engine.calculate_scores(
        issue_class="pothole",
        location_context=context,
    )

    assert scores["severity"] == 45.0
    assert scores["priority"] == 77.5


def test_segmentation_area_scaling():
    """
    Verify different segmentation area levels affect severity correctly.
    Base mud_road = 40.
    Threshold 50,000 pixels -> multiplier 1.15 -> severity = 46.
    Threshold 100,000 pixels -> multiplier 1.30 -> severity = 52.
    """
    engine = ScoringEngine()
    engine.load_rules()

    context = {
        "school_zone": False,
        "hospital_zone": False,
        "traffic_density": "low",
    }

    # Small size
    scores_small = engine.calculate_scores("mud_road", context, mask_area=10000.0)
    assert scores_small["severity"] == 40.0

    # Medium size
    scores_med = engine.calculate_scores("mud_road", context, mask_area=60000.0)
    assert scores_med["severity"] == 46.0

    # Large size
    scores_large = engine.calculate_scores("mud_road", context, mask_area=110000.0)
    assert scores_large["severity"] == 52.0


def test_bounds_capping():
    """Verify values never exceed 100 or drop below 0."""
    engine = ScoringEngine()
    # Force extreme rules
    engine.rules = {
        "base_severity": {"pothole": 150},
        "zone_multipliers": {"school_zone": 5.0},
        "traffic_boosts": {"high": 500},
    }

    context = {
        "school_zone": True,
        "traffic_density": "high",
    }

    scores = engine.calculate_scores("pothole", context)
    assert scores["severity"] == 100.0
    assert scores["priority"] == 100.0
