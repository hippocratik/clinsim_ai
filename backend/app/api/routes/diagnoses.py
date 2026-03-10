from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/diagnoses", tags=["diagnoses"])

# Fallback hardcoded set — used only if app.state.icd9_db is unavailable
_ICD9_FALLBACK = [
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
    {"code": "540.9",  "description": "Acute appendicitis without peritonitis"},
    {"code": "285.9",  "description": "Anaemia, unspecified"},
    {"code": "780.60", "description": "Fever, unspecified"},
    {"code": "786.50", "description": "Chest pain, unspecified"},
    {"code": "789.00", "description": "Abdominal pain, unspecified site"},
]


class DiagnosisSearchResult(BaseModel):
    code: str
    description: str


@router.get("/search", response_model=list[DiagnosisSearchResult])
def search_diagnoses(
    request: Request,
    q: str = Query(..., min_length=1, description="Search term for ICD-9 autocomplete"),
    limit: int = Query(10, ge=1, le=50),
):
    """Search ICD-9 codes by code prefix or description substring."""
    q_lower = q.lower().strip()

    # Use dynamic ICD-9 db built from loaded cases, fall back to hardcoded list
    icd9_db = getattr(request.app.state, "icd9_db", None)
    if icd9_db:
        database = [{"code": k, "description": v} for k, v in icd9_db.items()]
    else:
        database = _ICD9_FALLBACK

    results = [
        DiagnosisSearchResult(code=d["code"], description=d["description"])
        for d in database
        if q_lower in d["code"].lower() or q_lower in d["description"].lower()
    ]
    return results[:limit]