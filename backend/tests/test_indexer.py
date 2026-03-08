import pytest
import numpy as np
from app.rag.indexer import RAGIndexBuilder
from app.models import CaseChunk

@pytest.fixture
def sample_chunks():
    return [
        CaseChunk(
            chunk_id="case_001_presenting",
            case_id="case_001",
            chunk_type="presenting_complaint",
            content="Chief complaint: Chest pain for 3 hours",
            metadata={"subject_id": 123, "hadm_id": 456, "icd9_codes": ["410.11"]}
        ),
        CaseChunk(
            chunk_id="case_001_pmh",
            case_id="case_001",
            chunk_type="pmh",
            content="Past medical history: Hypertension, Diabetes",
            metadata={"subject_id": 123, "hadm_id": 456, "icd9_codes": ["410.11"]}
        ),
    ]

def test_index_builder_creates_embeddings(sample_chunks):
    builder = RAGIndexBuilder(embedding_model="all-MiniLM-L6-v2")
    index, chunks_with_embeddings = builder.build_index(sample_chunks)

    assert index is not None
    assert index.ntotal == 2  # Two chunks indexed

def test_index_builder_search_returns_results(sample_chunks):
    builder = RAGIndexBuilder(embedding_model="all-MiniLM-L6-v2")
    index, chunks = builder.build_index(sample_chunks)

    # Search for something similar to chest pain
    results = builder.search(index, chunks, "heart pain", top_k=2)

    assert len(results) > 0
    assert results[0].chunk_id == "case_001_presenting"  # Should match chest pain
