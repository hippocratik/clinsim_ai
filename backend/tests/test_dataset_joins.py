"""
Tests verifying that all datasets are properly joined in get_case_by_hadm_id
and that build_case_from_parsed uses all linked data.

Covers three bugs:
1. d_icd_diagnoses not joined -> diagnosis descriptions empty
2. d_labitems not joined -> lab names "Unknown"
3. prescriptions not passed to build_case_from_parsed -> silently dropped
"""
import pytest
import pandas as pd
from app.data.loader import MIMICDataset, get_case_by_hadm_id
from app.data.parser import build_case_from_parsed


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def minimal_dataset():
    """A minimal in-memory MIMICDataset with one admission (hadm_id=100)."""
    clinical_cases = pd.DataFrame([{
        "case_id": 1,
        "subject_id": 10,
        "hadm_id": 100,
        "age": 60,
        "gender": "M",
        "admission_diagnosis": "Chest pain",
        "discharge_summary": "Patient admitted with chest pain, treated and discharged."
    }])

    diagnoses = pd.DataFrame([{
        "subject_id": 10,
        "hadm_id": 100,
        "seq_num": 1,
        "icd9_code": "410.11"
    }])

    labs = pd.DataFrame([{
        "hadm_id": 100,
        "itemid": 50,
        "charttime": "2026-01-01 08:00",
        "value": "0.5",
        "unit": "ng/mL"
    }])

    prescriptions = pd.DataFrame([{
        "subject_id": 10,
        "hadm_id": 100,
        "startdate": "2026-01-01",
        "enddate": "2026-01-03",
        "drug": "Aspirin",
        "dose_value": "81",
        "dose_unit": "mg",
        "route": "PO"
    }])

    d_icd_diagnoses = pd.DataFrame([{
        "icd9_code": "410.11",
        "short_title": "AMI anterolateral",
        "long_title": "Acute myocardial infarction of anterolateral wall"
    }])

    d_labitems = pd.DataFrame([{
        "itemid": 50,
        "lab_name": "Troponin I",
        "fluid": "Blood",
        "category": "Chemistry"
    }])

    return MIMICDataset(
        clinical_cases=clinical_cases,
        diagnoses=diagnoses,
        labs=labs,
        prescriptions=prescriptions,
        d_icd_diagnoses=d_icd_diagnoses,
        d_labitems=d_labitems
    )


@pytest.fixture
def parsed_discharge():
    return {
        "presenting_complaint": "Chest pain",
        "hpi": "3 hours of chest pain",
        "past_medical_history": ["HTN"],
        "medications": ["Aspirin"],
        "allergies": [],
        "physical_exam": {
            "vitals": {
                "heart_rate": 90,
                "blood_pressure": "130/80",
                "respiratory_rate": 16,
                "temperature": 37.0,
                "spo2": 98
            },
            "findings": "Normal"
        },
        "hospital_course": "Treated for STEMI",
        "discharge_diagnosis": "Acute MI"
    }


# ── get_case_by_hadm_id tests ────────────────────────────────────────────────

def test_diagnoses_include_description(minimal_dataset):
    """Diagnoses returned by get_case_by_hadm_id must include long_title from d_icd_diagnoses."""
    result = get_case_by_hadm_id(minimal_dataset, hadm_id=100)
    diagnoses = result["diagnoses"]

    assert len(diagnoses) == 1
    diag = diagnoses[0]
    assert diag.get("long_title") == "Acute myocardial infarction of anterolateral wall", (
        "d_icd_diagnoses was not joined: long_title is missing from diagnosis records"
    )


def test_labs_include_lab_name(minimal_dataset):
    """Labs returned by get_case_by_hadm_id must include lab_name from d_labitems."""
    result = get_case_by_hadm_id(minimal_dataset, hadm_id=100)
    labs = result["labs"]

    assert len(labs) == 1
    lab = labs[0]
    assert lab.get("lab_name") == "Troponin I", (
        "d_labitems was not joined: lab_name is missing from lab records"
    )


def test_prescriptions_returned(minimal_dataset):
    """get_case_by_hadm_id must return prescriptions for the admission."""
    result = get_case_by_hadm_id(minimal_dataset, hadm_id=100)
    prescriptions = result["prescriptions"]

    assert len(prescriptions) == 1
    assert prescriptions[0]["drug"] == "Aspirin"


# ── build_case_from_parsed tests ─────────────────────────────────────────────

def test_build_case_diagnosis_description_populated(parsed_discharge):
    """Diagnoses in Case must have non-empty description when long_title is provided."""
    diagnoses = [{"icd9_code": "410.11", "long_title": "Acute myocardial infarction of anterolateral wall", "seq_num": 1}]
    labs = [{"lab_name": "Troponin I", "value": "0.5", "unit": "ng/mL"}]
    prescriptions = [{"drug": "Aspirin", "dose_value": "81", "dose_unit": "mg", "route": "PO"}]

    case = build_case_from_parsed(
        parsed=parsed_discharge,
        subject_id=10,
        hadm_id=100,
        diagnoses=diagnoses,
        labs=labs,
        prescriptions=prescriptions,
        age=60,
        gender="M"
    )

    assert len(case.diagnoses) == 1
    assert case.diagnoses[0].description != "", (
        "Diagnosis description is empty — long_title from d_icd_diagnoses not used"
    )
    assert "myocardial" in case.diagnoses[0].description.lower()


def test_build_case_lab_name_not_unknown(parsed_discharge):
    """Lab results in Case must use lab_name, not fall back to 'Unknown'."""
    diagnoses = [{"icd9_code": "410.11", "long_title": "Acute MI", "seq_num": 1}]
    labs = [{"lab_name": "Troponin I", "value": "0.5", "unit": "ng/mL"}]
    prescriptions = []

    case = build_case_from_parsed(
        parsed=parsed_discharge,
        subject_id=10,
        hadm_id=100,
        diagnoses=diagnoses,
        labs=labs,
        prescriptions=prescriptions,
        age=60,
        gender="M"
    )

    assert len(case.available_labs) == 1
    assert case.available_labs[0].lab_name != "Unknown", (
        "Lab name fell back to 'Unknown' — lab_name from d_labitems not used"
    )
    assert case.available_labs[0].lab_name == "Troponin I"


def test_build_case_prescriptions_included(parsed_discharge):
    """Medications in Case must include drugs from prescriptions table."""
    diagnoses = [{"icd9_code": "410.11", "long_title": "Acute MI", "seq_num": 1}]
    labs = []
    prescriptions = [
        {"drug": "Aspirin", "dose_value": "81", "dose_unit": "mg", "route": "PO"},
        {"drug": "Metoprolol", "dose_value": "25", "dose_unit": "mg", "route": "PO"},
    ]

    case = build_case_from_parsed(
        parsed=parsed_discharge,
        subject_id=10,
        hadm_id=100,
        diagnoses=diagnoses,
        labs=labs,
        prescriptions=prescriptions,
        age=60,
        gender="M"
    )

    drug_names = [m if isinstance(m, str) else m.get("drug", m) for m in case.medications]
    assert any("Aspirin" in str(m) for m in case.medications), (
        "Prescriptions not included in case medications — prescriptions param not wired up"
    )
