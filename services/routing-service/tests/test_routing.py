"""
Unit tests for the routing engine classification mappings.
"""

from app.services.engine import routing_engine


def test_load_routing_rules():
    """Verify routing weights are parsed correctly."""
    routing_engine.load_rules()
    assert "pothole" in routing_engine.rules["department_mappings"]
    assert "Roads & Infrastructure" in routing_engine.rules["supervisor_contacts"]


def test_routing_mappings():
    """
    Test routing of specific issue categories to correct department tags.
    """
    routing_engine.load_rules()

    # pothole -> Roads
    dept, contact = routing_engine.resolve_department("pothole", "ward_east", 8.0)
    assert dept == "Roads & Infrastructure"
    assert contact["name"] == "Supervisor Roads"

    # streetlight -> Electrical
    dept, contact = routing_engine.resolve_department("streetlight", "ward_east", 3.0)
    assert dept == "Electrical & Streetlights"

    # waterlogging -> Drainage
    dept, contact = routing_engine.resolve_department("waterlogging", "ward_west", 5.0)
    assert dept == "Drainage & Water"

    # tree -> Parks
    dept, contact = routing_engine.resolve_department("tree", "ward_east", 6.0)
    assert dept == "Parks & Environment"


def test_unknown_class_routing():
    """
    Verify unknown classes route to a fallback general department.
    """
    routing_engine.load_rules()
    dept, contact = routing_engine.resolve_department("unknown_class", "ward_east", 5.0)
    assert dept == "Roads & Infrastructure"  # fallback default
