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
