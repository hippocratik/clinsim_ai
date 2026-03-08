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
