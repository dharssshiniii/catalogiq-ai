import pandas as pd
import pytest

from app.core.errors import CatalogIQError
from app.models.schemas import Evidence
from app.services.csv_utils import escape_csv_formula, profile_frame, read_csv_bytes, sanitize_filename, validate_required_columns
from app.services.enrichment import confidence_for, make_field, validate_description
from app.services.placeholders import is_placeholder

REQUIRED = ("Mfg_Part_Num", "Part_Desc", "E1_Brand", "Unilog_Brand", "DIB_Brand", "Part_Manuf")


@pytest.mark.parametrize("value", [None, "", "-", " -- Unbranded -- ", "-- No Unilog Brand --", "-- No DIB Brand --"])
def test_placeholder_detection(value):
    assert is_placeholder(value)


def test_real_value_is_not_placeholder():
    assert not is_placeholder("Aster Works")


def test_required_column_validation():
    with pytest.raises(CatalogIQError, match="Mfg_Part_Num"):
        validate_required_columns(pd.DataFrame({"Part_Desc": ["x"]}), REQUIRED)


@pytest.mark.parametrize("content", [b"", b"Mfg_Part_Num,Part_Desc\n", b"a,b\n1,2,3", b"a,b\x00junk"])
def test_empty_and_corrupted_csv(content):
    with pytest.raises(CatalogIQError):
        read_csv_bytes(content)


def test_duplicate_detection():
    frame = pd.DataFrame([{c: "x" for c in REQUIRED}, {c: "x" for c in REQUIRED}])
    assert profile_frame(frame)["duplicate_count"] == 1


def test_confidence_boundaries_and_conflict():
    assert confidence_for(0) == 0
    assert 0 <= confidence_for(1) <= 1
    assert confidence_for(2) > confidence_for(1)
    assert confidence_for(2, conflicting=True) < 0.7


def test_missing_evidence_requires_review():
    result = make_field("BRAND_NAME", "", None, [])
    assert result.review_status == "NEEDS_REVIEW"
    assert result.confidence == 0


def test_conflicting_evidence_requires_review():
    evidence = [Evidence(excerpt="A", source_identifier="one", extraction_method="demo")]
    result = make_field("BRAND_NAME", "", "A", evidence, conflicting=True)
    assert result.review_status == "CONFLICT"


def test_description_validation():
    assert validate_description("short")[0].code == "DESCRIPTION_TOO_SHORT"
    assert any(i.code == "UNSUPPORTED_CLAIM" for i in validate_description("The best dishwasher with verified dimensions."))
    assert validate_description("Aster 14 place setting stainless steel dishwasher with delay start.") == []


def test_csv_security_utilities():
    assert sanitize_filename("../../evil name.csv") == "evil_name.csv"
    assert escape_csv_formula("=2+2") == "'=2+2"
