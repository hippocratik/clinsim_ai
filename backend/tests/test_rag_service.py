import pytest
from unittest.mock import Mock, patch
import numpy as np
from app.core.rag import RAGService, RetrievalResult


def make_mock_rag(chunks=None):
    if chunks is None:
        chunks = [
            {"chunk_id": "c1", "case_id": "case_001", "chunk_type": "presenting_complaint", "content": "Chest pain", "metadata": {}},
            {"chunk_id": "c2", "case_id": "case_001", "chunk_type": "pmh", "content": "Hypertension", "metadata": {}},
            {"chunk_id": "c3", "case_id": "case_002", "chunk_type": "presenting_complaint", "content": "Shortness of breath", "metadata": {}},
        ]

    mock_index = Mock()
    mock_index.search = Mock(return_value=(
        np.array([[0.1, 0.2, 0.3]]),
        np.array([[0, 1, 2]])
    ))

    with patch("app.core.rag.SentenceTransformer") as mock_st:
        mock_st.return_value.encode = Mock(return_value=np.array([[0.1] * 384]))
        service = RAGService(mock_index, chunks, "all-MiniLM-L6-v2")

    return service, mock_index


def test_retrieve_returns_results():
    service, _ = make_mock_rag()
    results = service.retrieve("chest pain", top_k=3)
    assert isinstance(results, list)
    assert all(isinstance(r, RetrievalResult) for r in results)


def test_retrieve_filters_by_case_id():
    service, _ = make_mock_rag()
    results = service.retrieve("chest", top_k=5, case_id="case_001")
    assert all(r.case_id == "case_001" for r in results)


def test_retrieve_filters_by_chunk_type():
    service, _ = make_mock_rag()
    results = service.retrieve("chest", top_k=5, chunk_types=["presenting_complaint"])
    assert all(r.chunk_type == "presenting_complaint" for r in results)


def test_retrieve_for_dialogue():
    service, _ = make_mock_rag()
    results = service.retrieve_for_dialogue("What is your pain?", "case_001", top_k=2)
    assert isinstance(results, list)
    assert len(results) <= 2


def test_retrieve_for_generation_excludes_case():
    service, _ = make_mock_rag()
    results = service.retrieve_for_generation("STEMI", exclude_case_id="case_001", top_k=5)
    assert all(r.case_id != "case_001" for r in results)


def test_score_is_between_0_and_1():
    service, _ = make_mock_rag()
    results = service.retrieve("chest", top_k=3)
    for r in results:
        assert 0.0 <= r.score <= 1.0