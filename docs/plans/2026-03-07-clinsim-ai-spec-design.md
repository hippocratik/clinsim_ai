# ClinSim AI — Spec-Driven Design Document

**Version:** 1.0
**Date:** 2026-03-07
**Status:** Approved for Implementation
**Target:** Healthcare AI Hackathon MVP + Extension Points

---

## Executive Summary

ClinSim AI is an interactive clinical case simulator that transforms real MIMIC patient data into training scenarios for medical residents. This spec-driven design document provides exact schemas, prompts, and acceptance criteria that enable parallel development by three engineers.

**Architecture:** Foundation Phase (sequential) → Three Parallel Workstreams → Integration

**Dataset:** [bavehackathon/2026-healthcare-ai](https://huggingface.co/datasets/bavehackathon/2026-healthcare-ai)

---

## Table of Contents

1. [Shared Data Schemas](#1-shared-data-schemas)
2. [Foundation Phase](#2-foundation-phase)
3. [Workstream 1: Frontend](#3-workstream-1--frontend)
4. [Workstream 2: Simulation Engine](#4-workstream-2--simulation-engine)
5. [Workstream 3: Case Generation](#5-workstream-3--case-generation)
6. [Integration & Extension Points](#6-integration--extension-points)

---

## 1. Shared Data Schemas

These schemas are the contract between all three workstreams. They must be agreed upon before parallel work begins.

### 1.1 Case Schema

```typescript
interface Case {
  case_id: string;                    // e.g., "case_001"
  subject_id: number;                 // MIMIC subject_id
  hadm_id: number;                    // MIMIC hospital admission id

  // Demographics
  demographics: {
    age: number;
    gender: "M" | "F";
    admission_type: string;           // e.g., "EMERGENCY", "ELECTIVE"
  };

  // Progressive reveal layers
  presenting_complaint: string;
  hpi: string;
  past_medical_history: string[];
  medications: string[];
  allergies: string[];

  physical_exam: {
    vitals: {
      heart_rate: number;
      blood_pressure: string;
      respiratory_rate: number;
      temperature: number;
      spo2: number;
    };
    findings: string;
  };

  available_labs: {
    lab_name: string;
    value: string;
    unit: string;
    flag: "normal" | "high" | "low" | "critical";
  }[];

  diagnoses: {
    icd9_code: string;
    description: string;
    is_primary: boolean;
  }[];

  discharge_summary: string;
  difficulty: "easy" | "medium" | "hard";
  specialties: string[];
  source_case_id?: string;
  is_generated: boolean;
}
```

### 1.2 RAG Chunk Schema

```typescript
interface CaseChunk {
  chunk_id: string;
  case_id: string;
  chunk_type: "presenting_complaint" | "hpi" | "pmh" | "physical_exam" |
              "labs" | "medications" | "hospital_course" | "diagnosis";
  content: string;
  metadata: {
    subject_id: number;
    hadm_id: number;
    icd9_codes: string[];
  };
  embedding?: number[];
}
```

### 1.3 Session Schema

```typescript
interface SimulationSession {
  session_id: string;
  case_id: string;
  trainee_id: string;
  started_at: string;
  status: "active" | "completed" | "abandoned";
  revealed_info: string[];
  ordered_labs: string[];
  actions_taken: TraineeAction[];
  current_score: number;
}

interface TraineeAction {
  action_type: "ask_question" | "order_lab" | "perform_exam" | "submit_diagnosis";
  content: string;
  timestamp: string;
  cost: number;
}
```

### 1.4 Response Schemas

```typescript
interface PatientResponse {
  response: string;
  revealed_chunks: string[];
  confidence: number;
}

interface CaseScore {
  session_id: string;
  diagnostic_accuracy: number;
  primary_diagnosis_correct: boolean;
  differential_score: number;
  efficiency_score: number;
  time_to_diagnosis_seconds: number;
  labs_ordered: number;
  optimal_labs: number;
}
```

---

## 2. Foundation Phase

**Duration:** ~4-6 hours
**Owner:** 1 engineer (or pair)
**Prerequisite for:** All three workstreams

### 2.1 HuggingFace Dataset Loader

**File:** `src/data/loader.py`

```python
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
    """Load all tables from HuggingFace dataset."""
    ds = load_dataset("bavehackathon/2026-healthcare-ai")
    # Convert to DataFrames and return
    ...
```

**Acceptance Criteria:**
- [ ] Dataset loads without authentication issues
- [ ] All expected tables are present
- [ ] Can query by `subject_id` and `hadm_id`

### 2.2 Discharge Summary Parser

**File:** `src/data/parser.py`

**System Prompt:**

```python
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
```

**User Template:**

```python
DISCHARGE_PARSER_USER_TEMPLATE = """Extract structured data from this discharge summary:

<discharge_summary>
{discharge_summary}
</discharge_summary>

Respond with JSON only, no explanation."""
```

**Acceptance Criteria:**
- [ ] Parses 20 discharge summaries successfully
- [ ] JSON output validates against Case schema
- [ ] No hallucinated data (null for missing fields)
- [ ] Handles malformed summaries gracefully

### 2.3 Structured Data Linker

**File:** `src/data/linker.py`

```python
def link_structured_data(
    parsed_case: dict,
    subject_id: int,
    hadm_id: int,
    dataset: MIMICDataset
) -> Case:
    """Enrich parsed case with structured data from MIMIC tables."""
    # Join diagnoses, labs, prescriptions by hadm_id
    ...
```

**Acceptance Criteria:**
- [ ] All ICD-9 codes mapped to readable descriptions
- [ ] Labs include name, value, unit, and abnormal flag
- [ ] Primary diagnosis identified (seq_num = 1)

### 2.4 RAG Index Builder

**File:** `src/rag/indexer.py`

**Chunking Strategy:**

```python
def chunk_case(case: Case) -> list[CaseChunk]:
    """Split a case into semantic chunks for RAG retrieval."""
    chunks = []

    # Chunk 1: Presenting complaint + HPI
    chunks.append(CaseChunk(
        chunk_id=f"{case.case_id}_presenting",
        chunk_type="presenting_complaint",
        content=f"Chief complaint: {case.presenting_complaint}\n\nHistory: {case.hpi}",
        ...
    ))

    # Chunk 2: Past medical history
    # Chunk 3: Physical exam
    # Chunk 4: Labs
    # Chunk 5: Medications
    # Chunk 6: Diagnosis

    return chunks
```

**Index Building:**

```python
from sentence_transformers import SentenceTransformer
import faiss

def build_rag_index(cases: list[Case]) -> tuple[faiss.Index, list[CaseChunk]]:
    model = SentenceTransformer('all-MiniLM-L6-v2')

    all_chunks = []
    for case in cases:
        all_chunks.extend(chunk_case(case))

    texts = [chunk.content for chunk in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True)

    dimension = embeddings.shape[1]  # 384
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings.astype(np.float32))

    faiss.write_index(index, "data/faiss.index")
    return index, all_chunks
```

**Acceptance Criteria:**
- [ ] Minimum 20 cases chunked (120+ chunks)
- [ ] FAISS index builds in under 60 seconds
- [ ] Retrieval returns relevant chunks
- [ ] Index persists and reloads correctly

### 2.5 Foundation Phase Output

```
data/
├── cases.json          # 20+ structured cases
├── chunks.json         # 120+ RAG chunks with metadata
├── faiss.index         # Vector index
└── mock_session.json   # Sample session for frontend
```

---

## 3. Workstream 1 — Frontend

**Tech Stack:** Next.js 14, Tailwind CSS, TypeScript
**Owner:** Engineer 1
**Dependencies:** `data/mock_session.json` from Foundation Phase

### 3.1 Project Structure

```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                   # Case selection
│   ├── session/[sessionId]/page.tsx
│   └── results/[sessionId]/page.tsx
├── components/
│   ├── patient/
│   │   ├── PatientChat.tsx
│   │   └── MessageBubble.tsx
│   ├── clinical/
│   │   ├── VitalsPanel.tsx
│   │   ├── LabsPanel.tsx
│   │   └── LabOrderModal.tsx
│   ├── actions/
│   │   ├── ActionBar.tsx
│   │   └── DiagnosisModal.tsx
│   └── results/
│       ├── ScoreCard.tsx
│       └── PathComparison.tsx
├── lib/
│   ├── api.ts
│   ├── types.ts
│   └── mock-api.ts
└── hooks/
    ├── useSession.ts
    └── usePatientChat.ts
```

### 3.2 Case Selection Page

**File:** `app/page.tsx`

**UI Layout:**
- Grid of case cards grouped by specialty
- Difficulty filter (Easy/Medium/Hard/Random)
- "Start Case" button creates session and redirects

**API Calls:**
- `GET /api/cases` → List available cases
- `POST /api/sessions` → Create new session

### 3.3 Patient Encounter Screen

**File:** `app/session/[sessionId]/page.tsx`

**Layout:** Split panel
- Left: Patient chat interface
- Right: Clinical data (vitals, labs, exam findings)
- Bottom: Action bar (Ask History, Physical Exam, Order Labs, Diagnosis)

**State Management:**

```typescript
interface SessionState {
  session: SimulationSession;
  case: Case;
  messages: ChatMessage[];
  revealedVitals: boolean;
  revealedExamSections: string[];
  orderedLabs: OrderedLab[];
  resourcesUsed: number;
  maxResources: number;
}
```

### 3.4 Patient Chat Component

**File:** `components/patient/PatientChat.tsx`

```typescript
interface PatientChatProps {
  sessionId: string;
  messages: ChatMessage[];
  onSendMessage: (message: string) => Promise<void>;
  isLoading: boolean;
}

const SUGGESTED_QUESTIONS = [
  "What brought you to the hospital today?",
  "When did your symptoms start?",
  "Have you experienced this before?",
  "Do you have any allergies?",
  "What medications are you taking?",
];
```

**Streaming Support:** Use SSE for patient responses.

### 3.5 Lab Order Modal

**File:** `components/clinical/LabOrderModal.tsx`

**Lab Categories:**

```typescript
const LAB_CATEGORIES = {
  panels: [
    { id: "cbc", name: "Complete Blood Count", cost: 2 },
    { id: "bmp", name: "Basic Metabolic Panel", cost: 3 },
    { id: "cmp", name: "Comprehensive Metabolic Panel", cost: 4 },
    { id: "cardiac", name: "Cardiac Enzymes", cost: 3 },
    { id: "coags", name: "Coagulation Panel", cost: 2 },
  ],
  individual: [
    { id: "troponin", name: "Troponin", cost: 2 },
    { id: "bnp", name: "BNP", cost: 2 },
    { id: "ddimer", name: "D-Dimer", cost: 2 },
    { id: "lactate", name: "Lactate", cost: 1 },
    // ...
  ],
};
```

### 3.6 Diagnosis Modal

**File:** `components/actions/DiagnosisModal.tsx`

- ICD-9 autocomplete search
- Primary diagnosis (required)
- Differential diagnoses (optional, up to 3)
- Clinical reasoning textarea (optional)
- Confirmation warning before submission

### 3.7 Results Page

**File:** `app/results/[sessionId]/page.tsx`

**Display:**
- Score breakdown (diagnostic accuracy, efficiency, time)
- Side-by-side path comparison (trainee vs optimal)
- Learning points (RAG-powered explanations)
- "Try Another Case" button

### 3.8 Mock API

**File:** `lib/mock-api.ts`

```typescript
export const mockApi = {
  async getCases(): Promise<Case[]> { ... },
  async createSession(caseId: string): Promise<{ session_id: string }> { ... },
  async getSession(sessionId: string): Promise<SessionState> { ... },
  async sendChat(sessionId: string, message: string): Promise<ChatResponse> { ... },
  async orderLabs(sessionId: string, labIds: string[]): Promise<OrderLabsResponse> { ... },
  async submitDiagnosis(sessionId: string, diagnosis: DiagnoseRequest): Promise<DiagnoseResponse> { ... },
};
```

### 3.9 Acceptance Criteria

| Component | Criteria |
|-----------|----------|
| Case Selection | Cases load, filter works, creates session |
| Patient Chat | Messages stream, suggested questions work |
| Vitals Panel | Displays on session load |
| Labs Panel | Orders labs, shows results, tracks cost |
| Diagnosis Modal | ICD-9 search, submits, redirects |
| Results Page | Score breakdown, path comparison |
| Mock API | All endpoints mocked with realistic delays |

---

## 4. Workstream 2 — Simulation Engine

**Tech Stack:** Python 3.11+, FastAPI, FAISS, Claude API
**Owner:** Engineer 2
**Dependencies:** `data/cases.json`, `data/chunks.json`, `data/faiss.index`

### 4.1 Project Structure

```
backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   ├── api/routes/
│   │   ├── cases.py
│   │   ├── sessions.py
│   │   ├── diagnoses.py
│   │   └── health.py
│   ├── core/
│   │   ├── rag.py
│   │   ├── llm.py
│   │   ├── session_manager.py
│   │   └── scoring.py
│   └── prompts/
│       ├── patient_dialogue.py
│       ├── exam_findings.py
│       └── debrief.py
├── tests/
└── requirements.txt
```

### 4.2 Configuration

**File:** `app/config.py`

```python
class Settings(BaseSettings):
    anthropic_api_key: str
    cases_path: str = "data/cases.json"
    chunks_path: str = "data/chunks.json"
    faiss_index_path: str = "data/faiss.index"
    rag_top_k: int = 5
    embedding_model: str = "all-MiniLM-L6-v2"
    llm_model: str = "claude-sonnet-4-20250514"
    llm_max_tokens: int = 1024
    default_resource_budget: int = 100
    cors_origins: list[str] = ["http://localhost:3000"]
```

### 4.3 RAG Service

**File:** `app/core/rag.py`

```python
class RAGService:
    def __init__(self, faiss_index, chunks, embedding_model):
        self.index = faiss_index
        self.chunks = chunks
        self.model = SentenceTransformer(embedding_model)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        case_id: str | None = None,
        chunk_types: list[str] | None = None
    ) -> list[RetrievalResult]:
        """Retrieve relevant chunks with optional filtering."""
        ...

    def retrieve_for_dialogue(self, question: str, case_id: str) -> list[RetrievalResult]:
        """Retrieve from active case for patient dialogue."""
        ...

    def retrieve_for_generation(self, diagnosis: str, exclude_case_id: str) -> list[RetrievalResult]:
        """Retrieve similar cases for generation."""
        ...
```

### 4.4 Patient Dialogue Prompts

**File:** `app/prompts/patient_dialogue.py`

```python
PATIENT_SYSTEM_PROMPT = """You are a simulated patient in a medical training scenario. You are being interviewed by a medical trainee who is trying to diagnose your condition.

CRITICAL RULES:
1. You can ONLY answer based on the clinical information provided in the <context> tags
2. You must NEVER invent symptoms, history, or details not in the context
3. If asked about something not covered in the context, say "I'm not sure" or "I don't think so"
4. Speak naturally as a patient would - use layman's terms, not medical jargon
5. Show appropriate emotion based on condition severity
6. Keep responses concise - 1-3 sentences typically

CONTEXT INTERPRETATION:
- "Chief complaint" = why you came to the hospital today
- "HPI" = the story of how your symptoms developed
- "PMH" = your medical history if asked about previous conditions
- "Medications" = pills you take regularly if asked
- "Physical exam findings" = you don't directly state these; they're for the trainee to discover"""

PATIENT_USER_TEMPLATE = """<context>
{retrieved_context}
</context>

The medical trainee asks: "{question}"

Respond as the patient would. Remember:
- Only use information from the context above
- Speak naturally, not clinically
- Keep it brief (1-3 sentences)
- If the context doesn't cover this topic, express uncertainty"""
```

**Question Classification:**

```python
QUESTION_CHUNK_MAPPING = {
    "symptom": ["presenting_complaint", "hpi"],
    "history": ["pmh"],
    "medication": ["medications"],
    "allergy": ["medications"],
    "default": ["presenting_complaint", "hpi", "pmh"]
}

def classify_question(question: str) -> list[str]:
    """Determine which chunk types are relevant."""
    # Keyword matching to route to appropriate chunks
    ...
```

### 4.5 Session Manager

**File:** `app/core/session_manager.py`

```python
@dataclass
class Session:
    session_id: str
    case_id: str
    trainee_id: str
    started_at: datetime
    status: str = "active"
    revealed_info: list[str] = field(default_factory=list)
    ordered_labs: list[str] = field(default_factory=list)
    performed_exams: list[str] = field(default_factory=list)
    actions: list[TraineeAction] = field(default_factory=list)
    resources_used: int = 0
    max_resources: int = 100
    chat_history: list[dict] = field(default_factory=list)
    submitted_diagnosis: Optional[dict] = None
    score: Optional[dict] = None

class SessionManager:
    def create_session(self, case_id: str, trainee_id: str) -> Session: ...
    def get_session(self, session_id: str) -> Session: ...
    def record_action(self, session_id: str, action_type: str, content: str, cost: int): ...
    def order_labs(self, session_id: str, lab_ids: list[str]) -> list[dict]: ...
    def perform_exam(self, session_id: str, exam_type: str) -> dict: ...
    def submit_diagnosis(self, session_id: str, diagnosis: dict) -> dict: ...
```

### 4.6 Scoring Engine

**File:** `app/core/scoring.py`

```python
class ScoringEngine:
    OPTIMAL_LABS = {
        "cardiac": ["troponin", "bnp", "ecg"],
        "respiratory": ["abg", "chest_xray", "cbc"],
        "infectious": ["cbc", "blood_culture", "lactate", "procalcitonin"],
    }

    TIME_THRESHOLDS = {
        "excellent": 300,   # < 5 min  → 20 pts
        "good": 600,        # < 10 min → 15 pts
        "adequate": 900,    # < 15 min → 10 pts
    }

    def score_session(self, session) -> CaseScore:
        # Primary diagnosis: 40 pts if correct
        # Differential: up to 30 pts (10 per match)
        # Efficiency: up to 30 pts (penalty for over-ordering)
        # Time: up to 20 pts
        ...
```

### 4.7 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/sessions` | Create session | `{case_id}` → `{session_id}` |
| `GET /api/sessions/{id}` | Get session state | Full session object |
| `POST /api/sessions/{id}/chat` | Chat with patient | SSE streaming response |
| `POST /api/sessions/{id}/labs` | Order labs | `{lab_ids}` → `{results}` |
| `POST /api/sessions/{id}/exam` | Perform exam | `{exam_type}` → `{findings}` |
| `POST /api/sessions/{id}/diagnose` | Submit diagnosis | `{diagnosis}` → `{score}` |
| `GET /api/sessions/{id}/results` | Get results | Full debrief data |
| `GET /api/cases` | List cases | With filters |
| `GET /api/diagnoses/search` | Search ICD-9 | Autocomplete |

### 4.8 Acceptance Criteria

| Component | Criteria |
|-----------|----------|
| RAG Service | Retrieves relevant chunks, filters work |
| LLM Service | Streams responses, handles errors |
| Session Manager | Tracks state, enforces resource limits |
| Scoring Engine | Correct scoring for all components |
| Patient Chat | Grounded in RAG, no hallucinations |
| All Endpoints | Return documented schemas |

---

## 5. Workstream 3 — Case Generation

**Tech Stack:** Python 3.11+, Claude API, FAISS
**Owner:** Engineer 3
**Dependencies:** `data/cases.json`, `data/chunks.json`, `data/faiss.index`

### 5.1 Project Structure

```
backend/
├── app/
│   ├── generation/
│   │   ├── template_extractor.py
│   │   ├── variation_generator.py
│   │   ├── clinical_validator.py
│   │   └── prompts.py
│   ├── api/routes/
│   │   └── generation.py
│   └── cli/
│       └── generate_cases.py
└── tests/
```

### 5.2 Template Extractor

**File:** `app/generation/template_extractor.py`

```python
@dataclass
class ClinicalTemplate:
    source_case_id: str
    primary_diagnosis: str
    icd9_code: str
    diagnosis_category: str
    cardinal_symptoms: list[str]      # Must-have symptoms
    supporting_symptoms: list[str]    # Common but optional
    critical_lab_patterns: list[dict]
    critical_exam_findings: list[str]
    symptom_timeline: str
    risk_factors: list[str]
    age_range: tuple[int, int]
    valid_genders: list[str]
    common_differentials: list[str]
    distinguishing_features: list[str]
```

**System Prompt:**

```python
TEMPLATE_EXTRACTION_SYSTEM_PROMPT = """You are a clinical pattern extraction system. Given a complete patient case, extract the reusable clinical template — the essential pattern that defines this diagnosis independent of the specific patient.

Your output must be valid JSON matching this schema:
{
  "primary_diagnosis": "string",
  "icd9_code": "string",
  "diagnosis_category": "cardiac|respiratory|infectious|neurological|gastrointestinal|renal|endocrine|other",
  "cardinal_symptoms": ["symptoms that MUST be present"],
  "supporting_symptoms": ["commonly present but not required"],
  "critical_lab_patterns": [{"lab_name": "string", "pattern": "elevated|decreased|normal", "typical_range": "string"}],
  "critical_exam_findings": ["typical physical exam findings"],
  "symptom_timeline": "hyperacute|acute|subacute|chronic",
  "risk_factors": ["demographics, comorbidities, exposures"],
  "age_range": [min, max],
  "valid_genders": ["M", "F"],
  "common_differentials": ["similar diagnoses"],
  "distinguishing_features": ["what makes this diagnosis unique"]
}

Rules:
- Extract the PATTERN, not the specific patient details
- Cardinal symptoms are definitional
- Lab patterns indicate direction, not exact values
- Be conservative — only include truly essential elements"""
```

### 5.3 Variation Generator

**File:** `app/generation/variation_generator.py`

```python
@dataclass
class VariationParameters:
    age: Optional[int] = None
    gender: Optional[str] = None
    add_comorbidities: list[str] = None
    symptom_severity: str = "typical"  # mild, typical, severe
    atypical_presentation: bool = False
    add_red_herrings: bool = False
    lab_variation: str = "normal"      # normal, borderline, extreme

class VariationGenerator:
    def __init__(self, llm_service, rag_service):
        self.llm = llm_service
        self.rag = rag_service

    async def generate_variation(
        self,
        template: ClinicalTemplate,
        params: VariationParameters = None
    ) -> dict:
        # 1. Retrieve similar real cases for grounding
        # 2. Generate variation with Claude
        # 3. Return complete Case dict
        ...

    async def generate_batch(
        self,
        template: ClinicalTemplate,
        count: int = 3
    ) -> list[dict]:
        ...
```

**System Prompt:**

```python
VARIATION_GENERATION_SYSTEM_PROMPT = """You are a clinical case generator for medical education. Given a clinical template and reference cases, generate a novel but clinically plausible patient case.

CRITICAL RULES:
1. The generated case MUST have the same underlying diagnosis as the template
2. All symptoms, labs, and findings must be clinically plausible
3. Use reference cases for realistic lab values and presentations
4. The case should be DIFFERENT from the source
5. Never invent lab values outside realistic ranges
6. Maintain internal consistency

OUTPUT FORMAT: Valid JSON matching the Case schema."""
```

### 5.4 Clinical Validator

**File:** `app/generation/clinical_validator.py`

```python
class ValidationSeverity(Enum):
    ERROR = "error"     # Reject case
    WARNING = "warning" # Usable but flagged
    INFO = "info"       # Minor observation

@dataclass
class ValidationResult:
    is_valid: bool
    issues: list[ValidationIssue]
    confidence_score: float

class ClinicalValidator:
    # Reference ranges for rule-based validation
    LAB_REFERENCE_RANGES = {
        "troponin": {"low": 0, "high": 0.04, "critical_high": 2.0},
        "bnp": {"low": 0, "high": 100, "critical_high": 5000},
        # ...
    }

    VITAL_RANGES = {
        "heart_rate": {"low": 60, "high": 100, "critical_low": 30, "critical_high": 200},
        # ...
    }

    async def validate(self, generated_case: dict, template: ClinicalTemplate) -> ValidationResult:
        issues = []
        issues.extend(self._validate_vitals(generated_case))
        issues.extend(self._validate_labs(generated_case))
        issues.extend(self._validate_demographics(generated_case, template))
        issues.extend(await self._llm_validate(generated_case, template))

        return ValidationResult(
            is_valid=not any(i.severity == ValidationSeverity.ERROR for i in issues),
            issues=issues,
            confidence_score=...
        )
```

### 5.5 CLI Tool

**File:** `app/cli/generate_cases.py`

```bash
# Generate 3 variations from a specific case
python -m app.cli.generate_cases --source-case case_001 --count 3

# Generate from all cardiac cases
python -m app.cli.generate_cases --diagnosis "myocardial infarction" --count 2

# Append to main case store
python -m app.cli.generate_cases --all-cases --count 1 --append

# Skip validation for speed
python -m app.cli.generate_cases --source-case case_001 --count 5 --no-validate
```

### 5.6 API Endpoint

```python
@router.post("/generate")
async def generate_case_variation(request: GenerateRequest, background_tasks: BackgroundTasks):
    """Async generation with job tracking."""
    job_id = str(uuid.uuid4())
    generation_jobs[job_id] = {"status": "pending", "generated_case_ids": []}
    background_tasks.add_task(run_generation, job_id, request, ...)
    return {"job_id": job_id, "status": "pending"}

@router.get("/generate/{job_id}")
async def get_generation_status(job_id: str):
    """Poll for generation status."""
    return generation_jobs.get(job_id)
```

### 5.7 Acceptance Criteria

| Component | Criteria |
|-----------|----------|
| Template Extractor | Extracts cardinal symptoms, lab patterns |
| Variation Generator | Creates novel cases with same diagnosis |
| Clinical Validator | Catches implausible cases (>80% pass rate) |
| CLI Tool | Batch generation, valid JSON output |
| API Endpoint | Async generation, status polling |

---

## 6. Integration & Extension Points

### 6.1 API Contract Summary

**Base URL:** `http://localhost:8000/api`

| Endpoint | Method | Owner |
|----------|--------|-------|
| `/cases` | GET | WS2 |
| `/cases/{id}` | GET | WS2 |
| `/sessions` | POST | WS2 |
| `/sessions/{id}` | GET | WS2 |
| `/sessions/{id}/chat` | POST (SSE) | WS2 |
| `/sessions/{id}/labs` | POST | WS2 |
| `/sessions/{id}/exam` | POST | WS2 |
| `/sessions/{id}/diagnose` | POST | WS2 |
| `/sessions/{id}/results` | GET | WS2 |
| `/diagnoses/search` | GET | WS2 |
| `/generate` | POST | WS3 |
| `/generate/{job_id}` | GET | WS3 |

### 6.2 Local Development Setup

```bash
# Terminal 1: Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm install && npm run dev

# Terminal 3: Case Generation
cd backend && source venv/bin/activate
python -m app.cli.generate_cases --source-case case_001 --count 3
```

### 6.3 Integration Tests

**File:** `tests/integration/test_full_flow.py`

```python
class TestCompleteSimulationFlow:
    async def test_case_selection_to_diagnosis(self, client):
        # 1. List cases
        # 2. Create session
        # 3. Chat with patient
        # 4. Order labs
        # 5. Perform exam
        # 6. Submit diagnosis
        # 7. View results
        ...

class TestRAGGrounding:
    async def test_no_hallucination(self, client):
        # Verify patient doesn't invent symptoms
        ...

class TestResourceManagement:
    async def test_resource_limit_enforced(self, client):
        # Cannot exceed budget
        ...
```

### 6.4 Extension Points (Phase 2)

#### Challenge Mode

```python
# Add to Session dataclass
mode: str = "standard"  # "standard", "challenge", "timed"
time_limit_seconds: Optional[int] = None
test_budget: Optional[int] = None
```

#### Program Director Dashboard

```python
# New endpoints
GET /api/trainees/{id}/performance
GET /api/cohort/{id}/analytics
```

#### Authentication

```python
# Add Clerk/Auth0 integration
# JWT validation middleware
# Role-based access (trainee vs admin)
```

#### Database Migration

```python
# Replace in-memory stores with PostgreSQL
# Session persistence across restarts
# Trainee performance history
```

#### Imaging Support

```python
# Add to Case schema
available_imaging: list[ImagingStudy] = []
```

### 6.5 Deployment (Post-Hackathon)

| Component | MVP | Production |
|-----------|-----|------------|
| Frontend | localhost:3000 | Vercel |
| Backend | localhost:8000 | Railway/Render |
| Database | In-memory | PostgreSQL |
| Sessions | In-memory | Redis |
| Vector DB | FAISS | Pinecone/pgvector |
| Auth | None | Clerk/Auth0 |

### 6.6 Demo Script (3 minutes)

1. Open case selection (10s)
2. Start cardiology case (10s)
3. Chat with patient — 2-3 questions (45s)
4. Order cardiac enzymes (20s)
5. Perform cardiac exam (15s)
6. Submit diagnosis (20s)
7. View results and score breakdown (30s)
8. Show generated case variation (30s)

---

## Appendix A: File Checklist

### Foundation Phase Output
- [ ] `data/cases.json`
- [ ] `data/chunks.json`
- [ ] `data/faiss.index`
- [ ] `data/mock_session.json`

### Workstream 1 (Frontend)
- [ ] `frontend/app/page.tsx`
- [ ] `frontend/app/session/[sessionId]/page.tsx`
- [ ] `frontend/app/results/[sessionId]/page.tsx`
- [ ] `frontend/components/patient/PatientChat.tsx`
- [ ] `frontend/components/clinical/LabOrderModal.tsx`
- [ ] `frontend/components/actions/DiagnosisModal.tsx`
- [ ] `frontend/lib/api.ts`
- [ ] `frontend/lib/mock-api.ts`

### Workstream 2 (Backend)
- [ ] `backend/app/main.py`
- [ ] `backend/app/config.py`
- [ ] `backend/app/core/rag.py`
- [ ] `backend/app/core/llm.py`
- [ ] `backend/app/core/session_manager.py`
- [ ] `backend/app/core/scoring.py`
- [ ] `backend/app/prompts/patient_dialogue.py`
- [ ] `backend/app/api/routes/sessions.py`
- [ ] `backend/app/api/routes/cases.py`

### Workstream 3 (Generation)
- [ ] `backend/app/generation/template_extractor.py`
- [ ] `backend/app/generation/variation_generator.py`
- [ ] `backend/app/generation/clinical_validator.py`
- [ ] `backend/app/cli/generate_cases.py`
- [ ] `backend/app/api/routes/generation.py`

---

## Appendix B: Environment Variables

```bash
# Backend (.env)
ANTHROPIC_API_KEY=sk-ant-...
CASES_PATH=data/cases.json
CHUNKS_PATH=data/chunks.json
FAISS_INDEX_PATH=data/faiss.index
LLM_MODEL=claude-sonnet-4-20250514
CORS_ORIGINS=http://localhost:3000

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

---

## Appendix C: Dependencies

### Backend (requirements.txt)
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
```

### Frontend (package.json dependencies)
```json
{
  "next": "^14.1.0",
  "react": "^18.2.0",
  "tailwindcss": "^3.4.0",
  "typescript": "^5.3.0"
}
```
