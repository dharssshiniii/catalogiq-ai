from pathlib import Path
import pandas as pd
import pytest
from app.services.csv_utils import profile_frame

RAW = Path(__file__).parents[2] / "data" / "raw" / "Unihack_ Sample Dataset - Input.csv"

@pytest.mark.skipif(not RAW.exists(), reason="Organizer input is intentionally absent")
def test_local_organizer_profile_matches_observed_counts():
    profile = profile_frame(pd.read_csv(RAW, dtype=str, keep_default_na=False))
    assert profile["row_count"] == 1000
    assert len(profile["columns"]) == 6
    assert profile["missing_placeholder_counts"]["E1_Brand"] == 799
    assert profile["missing_placeholder_counts"]["Unilog_Brand"] == 1000
    assert profile["missing_placeholder_counts"]["DIB_Brand"] == 755
    assert profile["missing_placeholder_counts"]["Part_Manuf"] == 41
    assert profile["duplicate_counts"] == {"manufacturer_part_number": 1, "description": 2, "full_row": 0}
