from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
import json
from pathlib import Path

router = APIRouter(prefix="/api/diagnoses", tags=["diagnoses"])

# ── Description lookup for raw MIMIC codes ────────────────────────────────────
ICD9_DESCRIPTIONS: dict[str, str] = {
    "4241":  "Mitral valve disorders",
    "4240":  "Mitral valve stenosis",
    "41401": "Coronary atherosclerosis of native coronary artery",
    "41071": "Subendocardial infarction, initial episode",
    "41011": "Acute MI, anterolateral wall, initial",
    "42731": "Atrial fibrillation",
    "42732": "Atrial flutter",
    "4275":  "Cardiac arrest",
    "4280":  "Congestive heart failure, unspecified",
    "42821": "Systolic heart failure, acute",
    "42823": "Systolic heart failure, acute on chronic",
    "4019":  "Essential hypertension, unspecified",
    "4011":  "Benign essential hypertension",
    "40390": "Hypertensive chronic kidney disease, unspecified",
    "44020": "Atherosclerosis of native arteries of extremities, unspecified",
    "44023": "Atherosclerosis of native arteries with ulceration",
    "44024": "Atherosclerosis of native arteries with gangrene",
    "44103": "Atherosclerosis of renal artery",
    "5845":  "Acute kidney failure, tubular necrosis",
    "5849":  "Acute renal failure, unspecified",
    "5856":  "End stage renal disease",
    "51881": "Acute respiratory failure",
    "49121": "Obstructive chronic bronchitis with acute exacerbation",
    "4789":  "Other disease of upper respiratory tract",
    "4860":  "Pneumonia, organism unspecified",
    "486":   "Pneumonia, organism unspecified",
    "25000": "Diabetes mellitus type II, uncomplicated",
    "25010": "Diabetes with ketoacidosis, type II",
    "25060": "Diabetes with neurological manifestations, type II",
    "2724":  "Other and unspecified hyperlipidemia",
    "2761":  "Hyposmolality and hyponatremia",
    "2762":  "Acidosis",
    "2939":  "Unspecified transient mental disorder",
    "43491": "Cerebral artery occlusion with cerebral infarction",
    "56211": "Diverticulosis of colon, without hemorrhage",
    "5695":  "Other specified disorders of intestine",
    "5780":  "Hematemesis",
    "5961":  "Bladder neck obstruction",
    "60001": "Benign prostatic hyperplasia without urinary obstruction",
    "78821": "Retention of urine, unspecified",
    "99591": "Sepsis",
    "99592": "Severe sepsis",
    "99859": "Other postoperative infection",
    "0389":  "Unspecified septicaemia",
    "V4365": "Coronary angioplasty status",
    "V4581": "Aortocoronary bypass status",
    "V5867": "Long-term use of insulin",
}


def _build_icd9_db() -> dict[str, str]:
    """
    Load raw ICD-9 codes directly from cases.json.
    Returns {raw_code: description} — no dot formatting applied.
    """
    candidates = [
        Path(__file__).parent.parent.parent.parent / "data" / "cases.json",
        Path(__file__).parent.parent.parent / "data" / "cases.json",
        Path("data/cases.json"),
        Path("backend/data/cases.json"),
    ]
    cases_path = next((p for p in candidates if p.exists()), None)

    if cases_path is None:
        # No cases.json found — use description map only
        return dict(ICD9_DESCRIPTIONS)

    try:
        raw = json.loads(cases_path.read_text())
    except Exception:
        return dict(ICD9_DESCRIPTIONS)

    # Handle different JSON shapes
    if isinstance(raw, dict):
        cases = raw.get("cases", raw.get("data", list(raw.values())))
    elif isinstance(raw, list):
        cases = raw
    else:
        cases = []

    db: dict[str, str] = {}
    for case in cases:
        if not isinstance(case, dict):
            continue
        for dx in case.get("diagnoses", []):
            if not isinstance(dx, dict):
                continue
            code = dx.get("icd9_code", "").strip()
            if not code:
                continue
            # Keep raw code exactly as stored — no dot insertion
            desc = (
                dx.get("description", "").strip()
                or ICD9_DESCRIPTIONS.get(code, "")
                or code  # fallback: show code itself as label
            )
            db[code] = desc

    # If nothing loaded from cases, fall back to description map
    if not db:
        return dict(ICD9_DESCRIPTIONS)

    return db


# Built once at import time — no app.state dependency
_ICD9_DB: dict[str, str] = _build_icd9_db()


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

    results = [
        DiagnosisSearchResult(code=code, description=desc)
        for code, desc in _ICD9_DB.items()
        if q_lower in code.lower() or q_lower in desc.lower()
    ]
    return results[:limit]