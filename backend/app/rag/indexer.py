import numpy as np
import faiss
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
from dataclasses import dataclass
from app.models import CaseChunk

@dataclass
class RetrievalResult:
    chunk_id: str
    chunk_type: str
    content: str
    score: float
    case_id: str
    metadata: dict

class RAGIndexBuilder:
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(embedding_model)
        self.dimension = 384  # all-MiniLM-L6-v2 dimension

    def build_index(self, chunks: list[CaseChunk]) -> tuple[faiss.Index, list[CaseChunk]]:
        """Build FAISS index from chunks."""

        # Generate embeddings
        texts = [chunk.content for chunk in chunks]
        embeddings = self.model.encode(texts, show_progress_bar=True)

        # Create FAISS index
        self.dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(self.dimension)
        index.add(embeddings.astype(np.float32))

        return index, chunks

    def search(
        self,
        index: faiss.Index,
        chunks: list[CaseChunk],
        query: str,
        top_k: int = 5,
        case_id: str = None,
        chunk_types: list[str] = None
    ) -> list[RetrievalResult]:
        """Search the index for relevant chunks."""

        # Embed query
        query_embedding = self.model.encode([query])[0].astype(np.float32)

        # Search - get more results if filtering
        search_k = top_k * 10 if (case_id or chunk_types) else top_k
        distances, indices = index.search(query_embedding.reshape(1, -1), search_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue

            chunk = chunks[idx]

            # Apply filters
            if case_id and chunk.case_id != case_id:
                continue
            if chunk_types and chunk.chunk_type not in chunk_types:
                continue

            results.append(RetrievalResult(
                chunk_id=chunk.chunk_id,
                chunk_type=chunk.chunk_type,
                content=chunk.content,
                score=float(1 / (1 + dist)),  # Convert distance to similarity
                case_id=chunk.case_id,
                metadata=chunk.metadata
            ))

            if len(results) >= top_k:
                break

        return results

    def save_index(self, index: faiss.Index, chunks: list[CaseChunk], index_path: str, chunks_path: str):
        """Save index and chunks to disk."""
        faiss.write_index(index, index_path)

        chunks_data = [
            {
                "chunk_id": c.chunk_id,
                "case_id": c.case_id,
                "chunk_type": c.chunk_type,
                "content": c.content,
                "metadata": c.metadata
            }
            for c in chunks
        ]

        with open(chunks_path, "w") as f:
            json.dump(chunks_data, f, indent=2)

    def load_index(self, index_path: str, chunks_path: str) -> tuple[faiss.Index, list[CaseChunk]]:
        """Load index and chunks from disk."""
        index = faiss.read_index(index_path)

        with open(chunks_path, "r") as f:
            chunks_data = json.load(f)

        chunks = [
            CaseChunk(
                chunk_id=c["chunk_id"],
                case_id=c["case_id"],
                chunk_type=c["chunk_type"],
                content=c["content"],
                metadata=c["metadata"]
            )
            for c in chunks_data
        ]

        return index, chunks
