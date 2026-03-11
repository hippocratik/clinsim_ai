"""
Tests for GET /labs endpoint.
Returns all labs from d_labitems grouped by category.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient

SAMPLE_LAB_DICTIONARY = [
    {"itemid": 50012, "lab_name": "Albumin", "fluid": "Blood", "category": "Chemistry"},
    {"itemid": 50813, "lab_name": "Sodium", "fluid": "Blood", "category": "Chemistry"},
    {"itemid": 51221, "lab_name": "Hematocrit", "fluid": "Blood", "category": "Hematology"},
    {"itemid": 51279, "lab_name": "Red Blood Cells", "fluid": "Blood", "category": "Hematology"},
    {"itemid": 51301, "lab_name": "White Blood Cells", "fluid": "Blood", "category": "Hematology"},
]


@pytest.fixture
def test_client():
    from app.core.session_manager import SessionManager
    from app.core.scoring import ScoringEngine
    from app.main import create_app

    mock_llm = Mock()
    mock_llm.stream = AsyncMock(return_value=iter([]))

    app = create_app()

    with TestClient(app) as client:
        # Override after lifespan has run so our fixture data wins
        app.state.cases = []
        app.state.case_index = {}
        app.state.icd9_db = {}
        app.state.generation_jobs = {}
        app.state.rag_service = None
        app.state.session_manager = SessionManager()
        app.state.scoring_engine = ScoringEngine()
        app.state.llm_service = mock_llm
        app.state.lab_dictionary = SAMPLE_LAB_DICTIONARY
        yield client


def test_labs_endpoint_returns_200(test_client):
    response = test_client.get("/api/labs")
    assert response.status_code == 200


def test_labs_grouped_by_category(test_client):
    response = test_client.get("/api/labs")
    data = response.json()

    assert "Chemistry" in data
    assert "Hematology" in data


def test_labs_each_item_has_required_fields(test_client):
    response = test_client.get("/api/labs")
    data = response.json()

    for category, labs in data.items():
        for lab in labs:
            assert "itemid" in lab, f"Missing itemid in {category} lab"
            assert "lab_name" in lab, f"Missing lab_name in {category} lab"
            assert "fluid" in lab, f"Missing fluid in {category} lab"


def test_labs_correct_items_per_category(test_client):
    response = test_client.get("/api/labs")
    data = response.json()

    assert len(data["Chemistry"]) == 2
    assert len(data["Hematology"]) == 3


def test_labs_category_not_included_in_each_item(test_client):
    """Category is the grouping key — should not be duplicated inside each item."""
    response = test_client.get("/api/labs")
    data = response.json()

    for category, labs in data.items():
        for lab in labs:
            assert "category" not in lab
