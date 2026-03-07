# ClinSim AI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an interactive clinical case simulator using MIMIC data, RAG, and Claude API for medical resident training.

**Architecture:** Foundation Phase (sequential, ~4-6 hrs) → Three Parallel Workstreams → Integration. Foundation must complete before workstreams begin.

**Tech Stack:** Python 3.11+, FastAPI, FAISS, Claude API, Next.js 14, Tailwind CSS, TypeScript

---

## Phase 0: Project Setup

### Task 0.1: Create Project Structure

**Files:**
- Create: `backend/` directory structure
- Create: `frontend/` directory structure
- Create: `data/` directory
- Create: `requirements.txt`
- Create: `backend/.env.example`

**Step 1: Create backend directory structure**

```bash
mkdir -p backend/app/{api/routes,core,prompts,data,generation,cli}
mkdir -p backend/tests
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/api/routes/__init__.py
touch backend/app/core/__init__.py
touch backend/app/prompts/__init__.py
touch backend/app/data/__init__.py
touch backend/app/generation/__init__.py
touch backend/app/cli/__init__.py
touch backend/tests/__init__.py
```

**Step 2: Create data directory**

```bash
mkdir -p data
```

**Step 3: Create requirements.txt**

```
fastapi>=0.109.0
uvicorn>=0.27.0
anthropic>=0.18.0
sentence-transformers>=2.3.0
faiss-cpu>=1.7.4
pandas>=2.2.0
datasets>=2.16.0
pydantic>=2.6.0
pydantic-settings>=2.1.0
python-dotenv>=1.0.0
httpx>=0.26.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
numpy>=1.26.0
```

**Step 4: Create .env.example**

```bash
# backend/.env.example
ANTHROPIC_API_KEY=sk-ant-...
CASES_PATH=data/cases.json
CHUNKS_PATH=data/chunks.json
FAISS_INDEX_PATH=data/faiss.index
LLM_MODEL=claude-sonnet-4-20250514
CORS_ORIGINS=http://localhost:3000
```

**Step 5: Create Python virtual environment**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt
```

**Step 6: Commit**

```bash
git add .
git commit -m "chore: initialize project structure with backend, data directories, and dependencies"
```

---

## Phase 1: Foundation — Data Loading

### Task 1.1: Create Pydantic Models for Case Schema

**Files:**
- Create: `backend/app/models.py`
- Test: `backend/tests/test_models.py`

**Step 1: Write the test**

```python
# backend/tests/test_models.py
import pytest
from app.models import Case, CaseChunk, Demographics, PhysicalExam, Vitals, LabResult, Diagnosis

def test_case_model_validates():
    case = Case(
        case_id="case_001",
        subject_id=12345,
        hadm_id=67890,
        demographics=Demographics(age=55, gender="M", admission_type="EMERGENCY"),
        presenting_complaint="Chest pain for 3 hours",
        hpi="Patient reports sudden onset chest pain while watching TV",
        past_medical_history=["Hypertension", "Diabetes"],
        medications=["Metformin", "Lisinopril"],
        allergies=["Penicillin"],
        physical_exam=PhysicalExam(
            vitals=Vitals(heart_rate=98, blood_pressure="145/92", respiratory_rate=22, temperature=37.2, spo2=94),
            findings="S3 gallop noted, no murmurs"
        ),
        available_labs=[
            LabResult(lab_name="Troponin", value="0.52", unit="ng/mL", flag="critical")
        ],
        diagnoses=[
            Diagnosis(icd9_code="410.11", description="Acute MI, STEMI", is_primary=True)
        ],
        discharge_summary="Patient admitted for STEMI...",
        difficulty="medium",
        specialties=["cardiology"],
        is_generated=False
    )
    assert case.case_id == "case_001"
    assert case.demographics.age == 55

def test_case_chunk_model():
    chunk = CaseChunk(
        chunk_id="case_001_presenting",
        case_id="case_001",
        chunk_type="presenting_complaint",
        content="Chief complaint: Chest pain",
        metadata={"subject_id": 12345, "hadm_id": 67890, "icd9_codes": ["410.11"]}
    )
    assert chunk.chunk_type == "presenting_complaint"
```

**Step 2: Run test to verify it fails**

```bash
cd backend
source venv/bin/activate
pytest tests/test_models.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.models'"

**Step 3: Write the implementation**

```python
# backend/app/models.py
from pydantic import BaseModel
from typing import Optional, Literal
from enum import Enum

class Vitals(BaseModel):
    heart_rate: Optional[int] = None
    blood_pressure: Optional[str] = None
    respiratory_rate: Optional[int] = None
    temperature: Optional[float] = None
    spo2: Optional[int] = None

class PhysicalExam(BaseModel):
    vitals: Vitals
    findings: str

class Demographics(BaseModel):
    age: int
    gender: Literal["M", "F"]
    admission_type: str

class LabResult(BaseModel):
    lab_name: str
    value: str
    unit: str
    flag: Literal["normal", "high", "low", "critical"]

class Diagnosis(BaseModel):
    icd9_code: str
    description: str
    is_primary: bool

class Case(BaseModel):
    case_id: str
    subject_id: int
    hadm_id: int
    demographics: Demographics
    presenting_complaint: str
    hpi: str
    past_medical_history: list[str]
    medications: list[str]
    allergies: list[str]
    physical_exam: PhysicalExam
    available_labs: list[LabResult]
    diagnoses: list[Diagnosis]
    discharge_summary: str
    difficulty: Literal["easy", "medium", "hard"]
    specialties: list[str]
    source_case_id: Optional[str] = None
    is_generated: bool = False

class ChunkType(str, Enum):
    PRESENTING_COMPLAINT = "presenting_complaint"
    HPI = "hpi"
    PMH = "pmh"
    PHYSICAL_EXAM = "physical_exam"
    LABS = "labs"
    MEDICATIONS = "medications"
    HOSPITAL_COURSE = "hospital_course"
    DIAGNOSIS = "diagnosis"

class CaseChunk(BaseModel):
    chunk_id: str
    case_id: str
    chunk_type: str
    content: str
    metadata: dict
    embedding: Optional[list[float]] = None
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_models.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models.py backend/tests/test_models.py
git commit -m "feat: add Pydantic models for Case and CaseChunk schemas"
```

---

### Task 1.2: Create HuggingFace Dataset Loader

**Files:**
- Create: `backend/app/data/loader.py`
- Test: `backend/tests/test_loader.py`

**Step 1: Write the test**

```python
# backend/tests/test_loader.py
import pytest
from app.data.loader import load_mimic_dataset, MIMICDataset

@pytest.mark.integration
def test_load_mimic_dataset():
    """Integration test - requires HuggingFace access."""
    dataset = load_mimic_dataset()

    assert isinstance(dataset, MIMICDataset)
    assert dataset.clinical_cases is not None
    assert len(dataset.clinical_cases) > 0
    assert "text" in dataset.clinical_cases.columns or "discharge_summary" in dataset.clinical_cases.columns

def test_mimic_dataset_dataclass():
    """Unit test for dataclass structure."""
    import pandas as pd
    dataset = MIMICDataset(
        clinical_cases=pd.DataFrame({"id": [1]}),
        diagnoses=pd.DataFrame({"id": [1]}),
        labs=pd.DataFrame({"id": [1]}),
        prescriptions=pd.DataFrame({"id": [1]}),
        d_icd_diagnoses=pd.DataFrame({"id": [1]}),
        d_labitems=pd.DataFrame({"id": [1]})
    )
    assert dataset.clinical_cases is not None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_loader.py::test_mimic_dataset_dataclass -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write the implementation**

```python
# backend/app/data/loader.py
from dataclasses import dataclass
from datasets import load_dataset
import pandas as pd

@dataclass
class MIMICDataset:
    clinical_cases: pd.DataFrame
    diagnoses: pd.DataFrame
    labs: pd.DataFrame
    prescriptions: pd.DataFrame
    d_icd_diagnoses: pd.DataFrame
    d_labitems: pd.DataFrame

def load_mimic_dataset() -> MIMICDataset:
    """Load all tables from the HuggingFace bavehackathon/2026-healthcare-ai dataset."""

    # Load the dataset from HuggingFace
    ds = load_dataset("bavehackathon/2026-healthcare-ai")

    # Convert each split/table to pandas DataFrame
    # Note: Actual table names may vary - adjust based on dataset structure
    clinical_cases = ds["clinical_cases"].to_pandas() if "clinical_cases" in ds else pd.DataFrame()
    diagnoses = ds["diagnoses"].to_pandas() if "diagnoses" in ds else pd.DataFrame()
    labs = ds["labs"].to_pandas() if "labs" in ds else pd.DataFrame()
    prescriptions = ds["prescriptions"].to_pandas() if "prescriptions" in ds else pd.DataFrame()
    d_icd_diagnoses = ds["d_icd_diagnoses"].to_pandas() if "d_icd_diagnoses" in ds else pd.DataFrame()
    d_labitems = ds["d_labitems"].to_pandas() if "d_labitems" in ds else pd.DataFrame()

    return MIMICDataset(
        clinical_cases=clinical_cases,
        diagnoses=diagnoses,
        labs=labs,
        prescriptions=prescriptions,
        d_icd_diagnoses=d_icd_diagnoses,
        d_labitems=d_labitems
    )

def get_case_by_hadm_id(dataset: MIMICDataset, hadm_id: int) -> dict:
    """Retrieve all data for a specific hospital admission."""
    case_data = dataset.clinical_cases[dataset.clinical_cases["hadm_id"] == hadm_id]
    diagnoses = dataset.diagnoses[dataset.diagnoses["hadm_id"] == hadm_id]
    labs = dataset.labs[dataset.labs["hadm_id"] == hadm_id]
    prescriptions = dataset.prescriptions[dataset.prescriptions["hadm_id"] == hadm_id]

    return {
        "case": case_data.to_dict(orient="records")[0] if len(case_data) > 0 else None,
        "diagnoses": diagnoses.to_dict(orient="records"),
        "labs": labs.to_dict(orient="records"),
        "prescriptions": prescriptions.to_dict(orient="records")
    }
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_loader.py::test_mimic_dataset_dataclass -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/data/loader.py backend/tests/test_loader.py
git commit -m "feat: add HuggingFace dataset loader for MIMIC data"
```

---

### Task 1.3: Create Configuration Module

**Files:**
- Create: `backend/app/config.py`
- Test: `backend/tests/test_config.py`

**Step 1: Write the test**

```python
# backend/tests/test_config.py
import pytest
import os

def test_settings_loads_defaults():
    from app.config import Settings

    settings = Settings(anthropic_api_key="test-key")

    assert settings.cases_path == "data/cases.json"
    assert settings.chunks_path == "data/chunks.json"
    assert settings.faiss_index_path == "data/faiss.index"
    assert settings.rag_top_k == 5
    assert settings.embedding_model == "all-MiniLM-L6-v2"
    assert settings.llm_model == "claude-sonnet-4-20250514"
    assert settings.default_resource_budget == 100

def test_settings_requires_api_key():
    from app.config import Settings
    from pydantic import ValidationError

    # Clear any env var
    os.environ.pop("ANTHROPIC_API_KEY", None)

    with pytest.raises(ValidationError):
        Settings()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_config.py -v
```

Expected: FAIL

**Step 3: Write the implementation**

```python
# backend/app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # API Keys
    anthropic_api_key: str

    # Paths
    cases_path: str = "data/cases.json"
    chunks_path: str = "data/chunks.json"
    faiss_index_path: str = "data/faiss.index"

    # RAG Settings
    rag_top_k: int = 5
    embedding_model: str = "all-MiniLM-L6-v2"

    # LLM Settings
    llm_model: str = "claude-sonnet-4-20250514"
    llm_max_tokens: int = 1024

    # Session Settings
    default_resource_budget: int = 100
    session_timeout_minutes: int = 60

    # Server
    cors_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_config.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/config.py backend/tests/test_config.py
git commit -m "feat: add configuration module with environment settings"
```

---

### Task 1.4: Create Discharge Summary Parser Prompts

**Files:**
- Create: `backend/app/prompts/discharge_parser.py`
- Test: `backend/tests/test_discharge_parser.py`

**Step 1: Write the test**

```python
# backend/tests/test_discharge_parser.py
import pytest
from app.prompts.discharge_parser import (
    DISCHARGE_PARSER_SYSTEM_PROMPT,
    DISCHARGE_PARSER_USER_TEMPLATE,
    format_parser_prompt
)

def test_system_prompt_contains_schema():
    assert "presenting_complaint" in DISCHARGE_PARSER_SYSTEM_PROMPT
    assert "past_medical_history" in DISCHARGE_PARSER_SYSTEM_PROMPT
    assert "physical_exam" in DISCHARGE_PARSER_SYSTEM_PROMPT
    assert "JSON" in DISCHARGE_PARSER_SYSTEM_PROMPT

def test_user_template_has_placeholder():
    assert "{discharge_summary}" in DISCHARGE_PARSER_USER_TEMPLATE

def test_format_parser_prompt():
    result = format_parser_prompt("Patient presents with chest pain...")
    assert "Patient presents with chest pain" in result
    assert "<discharge_summary>" in result
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_discharge_parser.py -v
```

Expected: FAIL

**Step 3: Write the implementation**

```python
# backend/app/prompts/discharge_parser.py

DISCHARGE_PARSER_SYSTEM_PROMPT = """You are a clinical data extraction system. Extract structured information from discharge summaries.

You must respond with valid JSON matching this exact schema:
{
  "presenting_complaint": "string - the chief complaint on admission",
  "hpi": "string - history of present illness narrative",
  "past_medical_history": ["array of condition strings"],
  "medications": ["array of medication strings"],
  "allergies": ["array of allergy strings"],
  "physical_exam": {
    "vitals": {
      "heart_rate": number or null,
      "blood_pressure": "string like '120/80' or null",
      "respiratory_rate": number or null,
      "temperature": number or null,
      "spo2": number or null
    },
    "findings": "string - physical exam findings"
  },
  "hospital_course": "string - what happened during hospitalization",
  "discharge_diagnosis": "string - final diagnosis"
}

Rules:
- Extract ONLY information explicitly stated in the text
- Use null for missing values, never invent data
- Keep medication names as written (brand or generic)
- For vitals, extract first recorded values if multiple exist
"""

DISCHARGE_PARSER_USER_TEMPLATE = """Extract structured data from this discharge summary:

<discharge_summary>
{discharge_summary}
</discharge_summary>

Respond with JSON only, no explanation."""


def format_parser_prompt(discharge_summary: str) -> str:
    """Format the user prompt with the discharge summary."""
    return DISCHARGE_PARSER_USER_TEMPLATE.format(discharge_summary=discharge_summary)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_discharge_parser.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/prompts/discharge_parser.py backend/tests/test_discharge_parser.py
git commit -m "feat: add discharge summary parser prompts"
```

---

### Task 1.5: Create LLM Service

**Files:**
- Create: `backend/app/core/llm.py`
- Test: `backend/tests/test_llm.py`

**Step 1: Write the test**

```python
# backend/tests/test_llm.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.core.llm import LLMService

def test_llm_service_init():
    service = LLMService(api_key="test-key", model="claude-sonnet-4-20250514")
    assert service.model == "claude-sonnet-4-20250514"

@pytest.mark.asyncio
async def test_llm_generate_calls_api():
    with patch("app.core.llm.anthropic.AsyncAnthropic") as mock_client:
        mock_response = Mock()
        mock_response.content = [Mock(text='{"test": "response"}')]
        mock_client.return_value.messages.create = AsyncMock(return_value=mock_response)

        service = LLMService(api_key="test-key")
        result = await service.generate(
            system_prompt="You are helpful",
            user_prompt="Hello"
        )

        assert result == '{"test": "response"}'
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_llm.py -v
```

Expected: FAIL

**Step 3: Write the implementation**

```python
# backend/app/core/llm.py
import anthropic
from typing import AsyncIterator

class LLMService:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.async_client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024
    ) -> str:
        """Generate a response (non-streaming)."""
        response = await self.async_client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return response.content[0].text

    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024
    ) -> AsyncIterator[str]:
        """Generate a streaming response."""
        async with self.async_client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        ) as stream:
            async for text in stream.text_stream:
                yield text

    def generate_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024
    ) -> str:
        """Generate a response synchronously."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return response.content[0].text
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_llm.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/core/llm.py backend/tests/test_llm.py
git commit -m "feat: add LLM service wrapper for Claude API"
```

---

### Task 1.6: Create Case Parser Service

**Files:**
- Create: `backend/app/data/parser.py`
- Test: `backend/tests/test_parser.py`

**Step 1: Write the test**

```python
# backend/tests/test_parser.py
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from app.data.parser import parse_discharge_summary, build_case_from_parsed

@pytest.mark.asyncio
async def test_parse_discharge_summary():
    mock_llm_response = json.dumps({
        "presenting_complaint": "Chest pain",
        "hpi": "3 hours of chest pain",
        "past_medical_history": ["HTN", "DM"],
        "medications": ["Metformin"],
        "allergies": [],
        "physical_exam": {
            "vitals": {"heart_rate": 98, "blood_pressure": "140/90", "respiratory_rate": 18, "temperature": 37.0, "spo2": 96},
            "findings": "S3 gallop"
        },
        "hospital_course": "Treated for STEMI",
        "discharge_diagnosis": "Acute MI"
    })

    with patch("app.data.parser.LLMService") as mock_llm:
        mock_llm.return_value.generate = AsyncMock(return_value=mock_llm_response)

        result = await parse_discharge_summary(
            llm_service=mock_llm.return_value,
            discharge_summary="Patient admitted with chest pain..."
        )

        assert result["presenting_complaint"] == "Chest pain"
        assert result["past_medical_history"] == ["HTN", "DM"]

def test_build_case_from_parsed():
    parsed = {
        "presenting_complaint": "Chest pain",
        "hpi": "3 hours of chest pain",
        "past_medical_history": ["HTN"],
        "medications": ["Aspirin"],
        "allergies": [],
        "physical_exam": {
            "vitals": {"heart_rate": 98, "blood_pressure": "140/90", "respiratory_rate": 18, "temperature": 37.0, "spo2": 96},
            "findings": "Normal"
        },
        "hospital_course": "Treated",
        "discharge_diagnosis": "MI"
    }

    diagnoses = [{"icd9_code": "410.11", "description": "Acute MI", "seq_num": 1}]
    labs = [{"label": "Troponin", "value": 0.5, "valueuom": "ng/mL", "flag": "abnormal"}]

    case = build_case_from_parsed(
        parsed=parsed,
        subject_id=123,
        hadm_id=456,
        diagnoses=diagnoses,
        labs=labs,
        age=55,
        gender="M"
    )

    assert case.case_id == "case_456"
    assert case.demographics.age == 55
    assert len(case.diagnoses) == 1
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_parser.py -v
```

Expected: FAIL

**Step 3: Write the implementation**

```python
# backend/app/data/parser.py
import json
from typing import Optional
from app.core.llm import LLMService
from app.models import Case, Demographics, PhysicalExam, Vitals, LabResult, Diagnosis
from app.prompts.discharge_parser import DISCHARGE_PARSER_SYSTEM_PROMPT, format_parser_prompt

async def parse_discharge_summary(
    llm_service: LLMService,
    discharge_summary: str
) -> dict:
    """Parse a discharge summary into structured data using Claude."""

    response = await llm_service.generate(
        system_prompt=DISCHARGE_PARSER_SYSTEM_PROMPT,
        user_prompt=format_parser_prompt(discharge_summary),
        max_tokens=2000
    )

    # Parse JSON response
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        # Try to extract JSON from response if wrapped in markdown
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            parsed = json.loads(json_match.group())
        else:
            raise ValueError(f"Failed to parse LLM response as JSON: {response[:200]}")

    return parsed

def build_case_from_parsed(
    parsed: dict,
    subject_id: int,
    hadm_id: int,
    diagnoses: list[dict],
    labs: list[dict],
    age: int,
    gender: str,
    admission_type: str = "EMERGENCY"
) -> Case:
    """Build a Case object from parsed discharge summary and linked data."""

    # Build vitals
    vitals_data = parsed.get("physical_exam", {}).get("vitals", {})
    vitals = Vitals(
        heart_rate=vitals_data.get("heart_rate"),
        blood_pressure=vitals_data.get("blood_pressure"),
        respiratory_rate=vitals_data.get("respiratory_rate"),
        temperature=vitals_data.get("temperature"),
        spo2=vitals_data.get("spo2")
    )

    # Build physical exam
    physical_exam = PhysicalExam(
        vitals=vitals,
        findings=parsed.get("physical_exam", {}).get("findings", "")
    )

    # Build lab results
    lab_results = []
    for lab in labs:
        flag = "normal"
        if lab.get("flag") == "abnormal":
            # Determine if high or low based on common patterns
            flag = "high"  # Simplified - would need reference ranges

        lab_results.append(LabResult(
            lab_name=lab.get("label", lab.get("lab_name", "Unknown")),
            value=str(lab.get("value", "")),
            unit=lab.get("valueuom", lab.get("unit", "")),
            flag=flag
        ))

    # Build diagnoses
    diagnosis_list = []
    for i, diag in enumerate(diagnoses):
        diagnosis_list.append(Diagnosis(
            icd9_code=diag.get("icd9_code", ""),
            description=diag.get("description", diag.get("long_title", "")),
            is_primary=(diag.get("seq_num", i+1) == 1)
        ))

    # Determine difficulty based on number of diagnoses
    difficulty = "easy" if len(diagnosis_list) <= 2 else "medium" if len(diagnosis_list) <= 4 else "hard"

    # Determine specialties from diagnosis descriptions
    specialties = _infer_specialties(diagnosis_list)

    return Case(
        case_id=f"case_{hadm_id}",
        subject_id=subject_id,
        hadm_id=hadm_id,
        demographics=Demographics(
            age=age,
            gender=gender,
            admission_type=admission_type
        ),
        presenting_complaint=parsed.get("presenting_complaint", ""),
        hpi=parsed.get("hpi", ""),
        past_medical_history=parsed.get("past_medical_history", []),
        medications=parsed.get("medications", []),
        allergies=parsed.get("allergies", []),
        physical_exam=physical_exam,
        available_labs=lab_results,
        diagnoses=diagnosis_list,
        discharge_summary=parsed.get("hospital_course", ""),
        difficulty=difficulty,
        specialties=specialties,
        is_generated=False
    )

def _infer_specialties(diagnoses: list[Diagnosis]) -> list[str]:
    """Infer medical specialties from diagnosis descriptions."""
    specialties = set()

    keywords = {
        "cardiology": ["heart", "cardiac", "infarction", "angina", "arrhythmia", "coronary"],
        "pulmonology": ["lung", "pulmonary", "pneumonia", "copd", "respiratory", "asthma"],
        "infectious": ["sepsis", "infection", "bacterial", "viral", "abscess"],
        "neurology": ["stroke", "seizure", "neurological", "brain", "cva"],
        "gastroenterology": ["liver", "hepatic", "gi", "gastro", "bowel", "intestinal"],
        "nephrology": ["kidney", "renal", "dialysis"],
        "endocrinology": ["diabetes", "thyroid", "endocrine", "diabetic"]
    }

    for diag in diagnoses:
        desc_lower = diag.description.lower()
        for specialty, terms in keywords.items():
            if any(term in desc_lower for term in terms):
                specialties.add(specialty)

    return list(specialties) if specialties else ["general"]
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_parser.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/data/parser.py backend/tests/test_parser.py
git commit -m "feat: add discharge summary parser with case builder"
```

---

### Task 1.7: Create RAG Chunker

**Files:**
- Create: `backend/app/rag/chunker.py`
- Test: `backend/tests/test_chunker.py`

**Step 1: Write the test**

```python
# backend/tests/test_chunker.py
import pytest
from app.rag.chunker import chunk_case
from app.models import Case, Demographics, PhysicalExam, Vitals, LabResult, Diagnosis

@pytest.fixture
def sample_case():
    return Case(
        case_id="case_001",
        subject_id=123,
        hadm_id=456,
        demographics=Demographics(age=55, gender="M", admission_type="EMERGENCY"),
        presenting_complaint="Chest pain for 3 hours",
        hpi="Patient reports sudden onset substernal chest pain",
        past_medical_history=["Hypertension", "Diabetes"],
        medications=["Metformin", "Lisinopril"],
        allergies=["Penicillin"],
        physical_exam=PhysicalExam(
            vitals=Vitals(heart_rate=98, blood_pressure="145/92", respiratory_rate=22, temperature=37.2, spo2=94),
            findings="S3 gallop noted"
        ),
        available_labs=[
            LabResult(lab_name="Troponin", value="0.52", unit="ng/mL", flag="critical")
        ],
        diagnoses=[
            Diagnosis(icd9_code="410.11", description="Acute MI", is_primary=True)
        ],
        discharge_summary="Patient treated for STEMI",
        difficulty="medium",
        specialties=["cardiology"],
        is_generated=False
    )

def test_chunk_case_creates_all_chunk_types(sample_case):
    chunks = chunk_case(sample_case)

    chunk_types = [c.chunk_type for c in chunks]

    assert "presenting_complaint" in chunk_types
    assert "pmh" in chunk_types
    assert "physical_exam" in chunk_types
    assert "labs" in chunk_types
    assert "medications" in chunk_types
    assert "diagnosis" in chunk_types

def test_chunk_case_includes_metadata(sample_case):
    chunks = chunk_case(sample_case)

    for chunk in chunks:
        assert chunk.case_id == "case_001"
        assert chunk.metadata["subject_id"] == 123
        assert chunk.metadata["hadm_id"] == 456

def test_chunk_content_is_meaningful(sample_case):
    chunks = chunk_case(sample_case)

    presenting_chunk = next(c for c in chunks if c.chunk_type == "presenting_complaint")
    assert "Chest pain" in presenting_chunk.content

    pmh_chunk = next(c for c in chunks if c.chunk_type == "pmh")
    assert "Hypertension" in pmh_chunk.content
```

**Step 2: Run test to verify it fails**

```bash
mkdir -p backend/app/rag
touch backend/app/rag/__init__.py
pytest tests/test_chunker.py -v
```

Expected: FAIL

**Step 3: Write the implementation**

```python
# backend/app/rag/chunker.py
from app.models import Case, CaseChunk

def chunk_case(case: Case) -> list[CaseChunk]:
    """Split a case into semantic chunks for RAG retrieval."""
    chunks = []

    base_metadata = {
        "subject_id": case.subject_id,
        "hadm_id": case.hadm_id,
        "icd9_codes": [d.icd9_code for d in case.diagnoses]
    }

    # Chunk 1: Presenting complaint + HPI
    chunks.append(CaseChunk(
        chunk_id=f"{case.case_id}_presenting",
        case_id=case.case_id,
        chunk_type="presenting_complaint",
        content=f"Chief complaint: {case.presenting_complaint}\n\nHistory of present illness: {case.hpi}",
        metadata=base_metadata.copy()
    ))

    # Chunk 2: Past medical history
    pmh_text = ", ".join(case.past_medical_history) if case.past_medical_history else "No significant past medical history"
    chunks.append(CaseChunk(
        chunk_id=f"{case.case_id}_pmh",
        case_id=case.case_id,
        chunk_type="pmh",
        content=f"Past medical history: {pmh_text}",
        metadata=base_metadata.copy()
    ))

    # Chunk 3: Physical exam
    vitals = case.physical_exam.vitals
    vitals_text = f"HR: {vitals.heart_rate}, BP: {vitals.blood_pressure}, RR: {vitals.respiratory_rate}, Temp: {vitals.temperature}°C, SpO2: {vitals.spo2}%"
    chunks.append(CaseChunk(
        chunk_id=f"{case.case_id}_exam",
        case_id=case.case_id,
        chunk_type="physical_exam",
        content=f"Vital signs: {vitals_text}\n\nPhysical exam findings: {case.physical_exam.findings}",
        metadata=base_metadata.copy()
    ))

    # Chunk 4: Labs
    lab_lines = [f"- {lab.lab_name}: {lab.value} {lab.unit} ({lab.flag})" for lab in case.available_labs]
    lab_text = "\n".join(lab_lines) if lab_lines else "No lab results available"
    chunks.append(CaseChunk(
        chunk_id=f"{case.case_id}_labs",
        case_id=case.case_id,
        chunk_type="labs",
        content=f"Laboratory results:\n{lab_text}",
        metadata=base_metadata.copy()
    ))

    # Chunk 5: Medications
    meds_text = ", ".join(case.medications) if case.medications else "No current medications"
    allergies_text = ", ".join(case.allergies) if case.allergies else "No known allergies"
    chunks.append(CaseChunk(
        chunk_id=f"{case.case_id}_meds",
        case_id=case.case_id,
        chunk_type="medications",
        content=f"Current medications: {meds_text}\nAllergies: {allergies_text}",
        metadata=base_metadata.copy()
    ))

    # Chunk 6: Diagnosis
    diag_lines = []
    for d in case.diagnoses:
        prefix = "[PRIMARY] " if d.is_primary else ""
        diag_lines.append(f"{prefix}{d.description} (ICD-9: {d.icd9_code})")
    diag_text = "\n".join(diag_lines)
    chunks.append(CaseChunk(
        chunk_id=f"{case.case_id}_diagnosis",
        case_id=case.case_id,
        chunk_type="diagnosis",
        content=f"Diagnoses:\n{diag_text}",
        metadata=base_metadata.copy()
    ))

    return chunks
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_chunker.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/rag/ backend/tests/test_chunker.py
git commit -m "feat: add RAG chunker for splitting cases into semantic chunks"
```

---

### Task 1.8: Create RAG Index Builder

**Files:**
- Create: `backend/app/rag/indexer.py`
- Test: `backend/tests/test_indexer.py`

**Step 1: Write the test**

```python
# backend/tests/test_indexer.py
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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_indexer.py -v
```

Expected: FAIL

**Step 3: Write the implementation**

```python
# backend/app/rag/indexer.py
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
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_indexer.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/rag/indexer.py backend/tests/test_indexer.py
git commit -m "feat: add RAG index builder with FAISS integration"
```

---

### Task 1.9: Create Foundation Pipeline Script

**Files:**
- Create: `backend/app/cli/build_foundation.py`

**Step 1: Write the script**

```python
# backend/app/cli/build_foundation.py
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
```

**Step 2: Test the script structure**

```bash
python -c "from app.cli.build_foundation import main; print('Import OK')"
```

**Step 3: Commit**

```bash
git add backend/app/cli/build_foundation.py
git commit -m "feat: add foundation pipeline script for data preparation"
```

---

## Phase 2: Workstream 2 — Simulation Engine (Backend API)

> **Note:** This phase can run in parallel with Phase 3 (Frontend) after Foundation is complete.

### Task 2.1: Create RAG Service

**Files:**
- Create: `backend/app/core/rag.py`
- Test: `backend/tests/test_rag_service.py`

**Step 1: Write the test**

```python
# backend/tests/test_rag_service.py
import pytest
from unittest.mock import Mock, patch
from app.core.rag import RAGService

def test_rag_service_retrieve_for_dialogue():
    # Mock FAISS index and chunks
    mock_index = Mock()
    mock_index.search = Mock(return_value=([[0.1, 0.2]], [[0, 1]]))

    mock_chunks = [
        {"chunk_id": "c1", "case_id": "case_001", "chunk_type": "presenting_complaint", "content": "Chest pain", "metadata": {}},
        {"chunk_id": "c2", "case_id": "case_001", "chunk_type": "pmh", "content": "Hypertension", "metadata": {}},
    ]

    with patch("app.core.rag.SentenceTransformer") as mock_st:
        mock_st.return_value.encode = Mock(return_value=[[0.1] * 384])

        service = RAGService(mock_index, mock_chunks, "all-MiniLM-L6-v2")
        results = service.retrieve_for_dialogue("What is your pain?", "case_001", top_k=2)

        assert len(results) <= 2
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_rag_service.py -v
```

**Step 3: Write the implementation**

```python
# backend/app/core/rag.py
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
```

**Step 4: Run test**

```bash
pytest tests/test_rag_service.py -v
```

**Step 5: Commit**

```bash
git add backend/app/core/rag.py backend/tests/test_rag_service.py
git commit -m "feat: add RAG service for semantic retrieval"
```

---

### Task 2.2: Create Patient Dialogue Prompts

**Files:**
- Create: `backend/app/prompts/patient_dialogue.py`
- Test: `backend/tests/test_patient_dialogue.py`

*(Continue pattern for remaining tasks...)*

---

## Phase 3: Workstream 1 — Frontend

> **Note:** This phase can run in parallel with Phase 2 after Foundation is complete.

### Task 3.1: Initialize Next.js Project

**Step 1: Create Next.js app**

```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
```

**Step 2: Commit**

```bash
git add frontend/
git commit -m "feat: initialize Next.js 14 frontend with TypeScript and Tailwind"
```

---

### Task 3.2: Create TypeScript Types

**Files:**
- Create: `frontend/src/lib/types.ts`

*(Continue with frontend tasks...)*

---

## Phase 4: Workstream 3 — Case Generation

> **Note:** This phase can run in parallel after Foundation is complete.

*(Tasks for template extraction, variation generation, validation...)*

---

## Phase 5: Integration

### Task 5.1: Connect Frontend to Backend API

### Task 5.2: End-to-End Testing

### Task 5.3: Demo Preparation

---

## Execution Checklist

### Foundation Phase (Sequential - ~4-6 hours)
- [ ] Task 0.1: Create Project Structure
- [ ] Task 1.1: Create Pydantic Models
- [ ] Task 1.2: Create HuggingFace Dataset Loader
- [ ] Task 1.3: Create Configuration Module
- [ ] Task 1.4: Create Discharge Summary Parser Prompts
- [ ] Task 1.5: Create LLM Service
- [ ] Task 1.6: Create Case Parser Service
- [ ] Task 1.7: Create RAG Chunker
- [ ] Task 1.8: Create RAG Index Builder
- [ ] Task 1.9: Run Foundation Pipeline

### Workstream 2: Backend (Parallel)
- [ ] Task 2.1: Create RAG Service
- [ ] Task 2.2: Create Patient Dialogue Prompts
- [ ] Task 2.3: Create Session Manager
- [ ] Task 2.4: Create Scoring Engine
- [ ] Task 2.5: Create FastAPI App + Routes
- [ ] Task 2.6: Create API Tests

### Workstream 1: Frontend (Parallel)
- [ ] Task 3.1: Initialize Next.js
- [ ] Task 3.2: Create Types
- [ ] Task 3.3: Create Mock API
- [ ] Task 3.4: Create Case Selection Page
- [ ] Task 3.5: Create Patient Chat Component
- [ ] Task 3.6: Create Lab Order Modal
- [ ] Task 3.7: Create Diagnosis Modal
- [ ] Task 3.8: Create Results Page

### Workstream 3: Generation (Parallel)
- [ ] Task 4.1: Create Template Extractor
- [ ] Task 4.2: Create Variation Generator
- [ ] Task 4.3: Create Clinical Validator
- [ ] Task 4.4: Create CLI Tool

### Integration
- [ ] Task 5.1: Connect Frontend to Backend
- [ ] Task 5.2: End-to-End Testing
- [ ] Task 5.3: Demo Preparation
