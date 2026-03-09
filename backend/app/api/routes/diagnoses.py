from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/diagnoses", tags=["diagnoses"])

# Embedded ICD-9 sample set for autocomplete (expand from real ICD-9 data as needed)
_ICD9_DATABASE = [
    {"code": "410.11", "description": "Acute myocardial infarction, STEMI, initial episode"},
    {"code": "410.01", "description": "Acute myocardial infarction, anterolateral wall, initial"},
    {"code": "414.01", "description": "Coronary atherosclerosis of native coronary artery"},
    {"code": "428.0",  "description": "Congestive heart failure, unspecified"},
    {"code": "427.31", "description": "Atrial fibrillation"},
    {"code": "486",    "description": "Pneumonia, organism unspecified"},
    {"code": "491.21", "description": "Obstructive chronic bronchitis with acute exacerbation (COPD)"},
    {"code": "518.81", "description": "Acute respiratory failure"},
    {"code": "584.9",  "description": "Acute renal failure, unspecified"},
    {"code": "585.3",  "description": "Chronic kidney disease, stage III"},
    {"code": "250.00", "description": "Diabetes mellitus type II, uncomplicated"},
    {"code": "250.10", "description": "Diabetes mellitus with ketoacidosis, type II"},
    {"code": "401.9",  "description": "Essential hypertension, unspecified"},
    {"code": "434.11", "description": "Cerebral embolism with cerebral infarction"},
    {"code": "431",    "description": "Intracerebral haemorrhage"},
    {"code": "038.9",  "description": "Unspecified septicaemia"},
    {"code": "995.91", "description": "Sepsis"},
    {"code": "995.92", "description": "Severe sepsis"},
    {"code": "557.9",  "description": "Unspecified vascular insufficiency of intestine"},
    {"code": "574.20", "description": "Calculus of gallbladder without cholecystitis"},
    {"code": "575.10", "description": "Cholecystitis, unspecified"},
    {"code": "540.9",  "description": "Acute appendicitis without peritonitis"},
    {"code": "550.90", "description": "Inguinal hernia, unilateral, without obstruction"},
    {"code": "153.9",  "description": "Malignant neoplasm of colon, unspecified"},
    {"code": "162.9",  "description": "Malignant neoplasm of bronchus and lung, unspecified"},
    {"code": "174.9",  "description": "Malignant neoplasm of breast, unspecified"},
    {"code": "185",    "description": "Malignant neoplasm of prostate"},
    {"code": "203.00", "description": "Multiple myeloma without remission"},
    {"code": "285.9",  "description": "Anaemia, unspecified"},
    {"code": "287.5",  "description": "Thrombocytopenia, unspecified"},
    {"code": "296.22", "description": "Major depressive disorder, single episode, moderate"},
    {"code": "295.30", "description": "Paranoid schizophrenia, unspecified"},
    {"code": "303.90", "description": "Alcohol dependence syndrome, unspecified"},
    {"code": "305.10", "description": "Tobacco use disorder"},
    {"code": "780.60", "description": "Fever, unspecified"},
    {"code": "786.50", "description": "Chest pain, unspecified"},
    {"code": "789.00", "description": "Abdominal pain, unspecified site"},
    {"code": "780.09", "description": "Alteration of consciousness, other"},
]


class DiagnosisSearchResult(BaseModel):
    code: str
    description: str


@router.get("/search", response_model=list[DiagnosisSearchResult])
def search_diagnoses(
    q: str = Query(..., min_length=1, description="Search term for ICD-9 autocomplete"),
    limit: int = Query(10, ge=1, le=50),
):
    """Search ICD-9 codes by code prefix or description substring."""
    q_lower = q.lower().strip()
    results = [
        DiagnosisSearchResult(code=d["code"], description=d["description"])
        for d in _ICD9_DATABASE
        if q_lower in d["code"].lower() or q_lower in d["description"].lower()
    ]
    return results[:limit]