import numpy as np
from sentence_transformers import SentenceTransformer
from dataclasses import dataclass


@dataclass
class RetrievalResult:
    chunk_id: str
    chunk_type: str
    content: str
    score: float
    case_id: str


class RAGService:
    def __init__(self, faiss_index, chunks: list[dict], embedding_model: str = "all-MiniLM-L6-v2"):
        self.index = faiss_index
        self.chunks = chunks
        self.chunk_lookup = {c["chunk_id"]: c for c in chunks}
        self.model = SentenceTransformer(embedding_model)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        case_id: str = None,
        chunk_types: list[str] = None
    ) -> list[RetrievalResult]:
        """Retrieve relevant chunks for a query."""
        query_embedding = self.model.encode([query])[0].astype(np.float32)

        search_k = top_k * 10 if (case_id or chunk_types) else top_k
        distances, indices = self.index.search(query_embedding.reshape(1, -1), search_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue

            chunk = self.chunks[idx]

            if case_id and chunk["case_id"] != case_id:
                continue
            if chunk_types and chunk["chunk_type"] not in chunk_types:
                continue

            results.append(RetrievalResult(
                chunk_id=chunk["chunk_id"],
                chunk_type=chunk["chunk_type"],
                content=chunk["content"],
                score=float(1 / (1 + dist)),
                case_id=chunk["case_id"]
            ))

            if len(results) >= top_k:
                break

        return results

    def retrieve_for_dialogue(self, question: str, case_id: str, top_k: int = 3) -> list[RetrievalResult]:
        """Retrieve chunks from the active case for patient dialogue."""
        return self.retrieve(query=question, top_k=top_k, case_id=case_id)

    def retrieve_for_generation(self, diagnosis: str, exclude_case_id: str, top_k: int = 10) -> list[RetrievalResult]:
        """Retrieve similar cases for case generation."""
        results = self.retrieve(
            query=diagnosis,
            top_k=top_k * 2,
            chunk_types=["diagnosis", "presenting_complaint"]
        )
        return [r for r in results if r.case_id != exclude_case_id][:top_k]