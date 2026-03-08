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
