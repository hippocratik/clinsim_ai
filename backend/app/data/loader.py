from dataclasses import dataclass
from huggingface_hub import snapshot_download
import pandas as pd
from pathlib import Path

DATASET_REPO = "bavehackathon/2026-healthcare-ai"

@dataclass
class MIMICDataset:
    clinical_cases: pd.DataFrame
    diagnoses: pd.DataFrame
    labs: pd.DataFrame
    prescriptions: pd.DataFrame
    d_icd_diagnoses: pd.DataFrame
    d_labitems: pd.DataFrame

def load_mimic_dataset() -> MIMICDataset:
    """Load all tables from the HuggingFace bavehackathon/2026-healthcare-ai dataset.

    Downloads the dataset snapshot once and caches it locally. Each CSV file
    is loaded separately since they have different schemas.
    """
    # Download (or use cached) snapshot of the dataset repo
    snapshot_path = Path(snapshot_download(repo_id=DATASET_REPO, repo_type="dataset"))

    clinical_cases = pd.read_csv(snapshot_path / "clinical_cases.csv.gz")
    diagnoses = pd.read_csv(snapshot_path / "diagnoses_subset.csv.gz")
    labs = pd.read_csv(snapshot_path / "labs_subset.csv.gz")
    prescriptions = pd.read_csv(snapshot_path / "prescriptions_subset.csv.gz")
    d_icd_diagnoses = pd.read_csv(snapshot_path / "diagnosis_dictionary.csv.gz")
    d_labitems = pd.read_csv(snapshot_path / "lab_dictionary.csv.gz")

    return MIMICDataset(
        clinical_cases=clinical_cases,
        diagnoses=diagnoses,
        labs=labs,
        prescriptions=prescriptions,
        d_icd_diagnoses=d_icd_diagnoses,
        d_labitems=d_labitems
    )

def get_case_by_hadm_id(dataset: MIMICDataset, hadm_id: int) -> dict:
    """Retrieve all data for a specific hospital admission.

    Joins diagnoses with d_icd_diagnoses (via icd9_code) so each diagnosis
    record includes long_title and short_title.

    Joins labs with d_labitems (via itemid) so each lab record includes
    lab_name, fluid, and category.
    """
    case_data = dataset.clinical_cases[dataset.clinical_cases["hadm_id"] == hadm_id]

    diagnoses = (
        dataset.diagnoses[dataset.diagnoses["hadm_id"] == hadm_id]
        .merge(dataset.d_icd_diagnoses, on="icd9_code", how="left")
    )

    labs = (
        dataset.labs[dataset.labs["hadm_id"] == hadm_id]
        .merge(dataset.d_labitems, on="itemid", how="left")
    )

    prescriptions = dataset.prescriptions[dataset.prescriptions["hadm_id"] == hadm_id]

    return {
        "case": case_data.to_dict(orient="records")[0] if len(case_data) > 0 else None,
        "diagnoses": diagnoses.to_dict(orient="records"),
        "labs": labs.to_dict(orient="records"),
        "prescriptions": prescriptions.to_dict(orient="records")
    }
