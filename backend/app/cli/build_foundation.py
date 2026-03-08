#!/usr/bin/env python3
"""
Build the foundation data artifacts for ClinSim AI.

Usage:
    python -m app.cli.build_foundation --num-cases 20
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from app.config import get_settings
from app.core.llm import LLMService
from app.data.loader import load_mimic_dataset, get_case_by_hadm_id
from app.data.parser import parse_discharge_summary, build_case_from_parsed
from app.rag.chunker import chunk_case
from app.rag.indexer import RAGIndexBuilder

async def build_foundation(num_cases: int = 20):
    """Build all foundation data artifacts."""

    print("=" * 60)
    print("ClinSim AI Foundation Builder")
    print("=" * 60)

    settings = get_settings()

    # Step 1: Load dataset
    print("\n[1/5] Loading MIMIC dataset from HuggingFace...")
    dataset = load_mimic_dataset()
    print(f"  Loaded {len(dataset.clinical_cases)} clinical cases")

    # Step 2: Select cases to process
    print(f"\n[2/5] Selecting {num_cases} cases to process...")
    # Get unique hadm_ids
    hadm_ids = dataset.clinical_cases["hadm_id"].unique()[:num_cases]
    print(f"  Selected {len(hadm_ids)} cases")

    # Step 3: Parse discharge summaries
    print("\n[3/5] Parsing discharge summaries with Claude...")
    llm_service = LLMService(api_key=settings.anthropic_api_key, model=settings.llm_model)

    cases = []
    for i, hadm_id in enumerate(hadm_ids):
        print(f"  Processing case {i+1}/{len(hadm_ids)} (hadm_id: {hadm_id})...")

        try:
            case_data = get_case_by_hadm_id(dataset, hadm_id)

            if not case_data["case"]:
                print(f"    Skipping - no case data found")
                continue

            # Get discharge summary text
            discharge_text = case_data["case"].get("text", case_data["case"].get("discharge_summary", ""))

            if not discharge_text:
                print(f"    Skipping - no discharge summary")
                continue

            # Parse with LLM
            parsed = await parse_discharge_summary(llm_service, discharge_text)

            # Build case object
            case = build_case_from_parsed(
                parsed=parsed,
                subject_id=case_data["case"].get("subject_id", 0),
                hadm_id=hadm_id,
                diagnoses=case_data["diagnoses"],
                labs=case_data["labs"],
                age=case_data["case"].get("age", 50),
                gender=case_data["case"].get("gender", "M")
            )

            cases.append(case)
            print(f"    ✓ Parsed: {case.presenting_complaint[:50]}...")

        except Exception as e:
            print(f"    ✗ Error: {e}")
            continue

    print(f"\n  Successfully parsed {len(cases)} cases")

    # Step 4: Build RAG index
    print("\n[4/5] Building RAG index...")
    all_chunks = []
    for case in cases:
        chunks = chunk_case(case)
        all_chunks.extend(chunks)

    print(f"  Created {len(all_chunks)} chunks from {len(cases)} cases")

    builder = RAGIndexBuilder(embedding_model=settings.embedding_model)
    index, indexed_chunks = builder.build_index(all_chunks)
    print(f"  Built FAISS index with {index.ntotal} vectors")

    # Step 5: Save artifacts
    print("\n[5/5] Saving artifacts...")

    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    # Save cases
    cases_data = {case.case_id: case.model_dump() for case in cases}
    with open(data_dir / "cases.json", "w") as f:
        json.dump(cases_data, f, indent=2)
    print(f"  ✓ Saved {settings.cases_path}")

    # Save chunks and index
    builder.save_index(
        index,
        indexed_chunks,
        str(data_dir / "faiss.index"),
        str(data_dir / "chunks.json")
    )
    print(f"  ✓ Saved {settings.chunks_path}")
    print(f"  ✓ Saved {settings.faiss_index_path}")

    # Create mock session for frontend development
    if cases:
        mock_session = {
            "session_id": "mock_001",
            "case_id": cases[0].case_id,
            "case": cases[0].model_dump(),
            "sample_interactions": [
                {
                    "trainee_input": "What brought you to the hospital today?",
                    "patient_response": f"I've been having {cases[0].presenting_complaint.lower()}."
                },
                {
                    "trainee_input": "Can you describe your symptoms?",
                    "patient_response": "It started suddenly and has been getting worse."
                }
            ]
        }
        with open(data_dir / "mock_session.json", "w") as f:
            json.dump(mock_session, f, indent=2)
        print(f"  ✓ Saved data/mock_session.json")

    print("\n" + "=" * 60)
    print("Foundation build complete!")
    print("=" * 60)
    print(f"\nArtifacts created:")
    print(f"  - {len(cases)} cases in data/cases.json")
    print(f"  - {len(all_chunks)} chunks in data/chunks.json")
    print(f"  - FAISS index in data/faiss.index")
    print(f"  - Mock session in data/mock_session.json")


def main():
    parser = argparse.ArgumentParser(description="Build ClinSim AI foundation data")
    parser.add_argument("--num-cases", type=int, default=20, help="Number of cases to process")
    args = parser.parse_args()

    asyncio.run(build_foundation(num_cases=args.num_cases))


if __name__ == "__main__":
    main()
