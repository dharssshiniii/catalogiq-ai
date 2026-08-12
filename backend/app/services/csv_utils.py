import csv
import io
import re
from pathlib import Path

import pandas as pd

from app.core.errors import CatalogIQError
from app.services.placeholders import is_placeholder

SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]")
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_filename(filename: str) -> str:
    return SAFE_FILENAME.sub("_", Path(filename).name)[:255] or "upload.csv"


def escape_csv_formula(value: object) -> object:
    return "'" + value if isinstance(value, str) and value.startswith(FORMULA_PREFIXES) else value


def read_csv_bytes(content: bytes) -> pd.DataFrame:
    if not content or not content.strip():
        raise CatalogIQError("EMPTY_CSV", "The uploaded CSV is empty.")
    if b"\x00" in content:
        raise CatalogIQError("INVALID_CSV", "The upload contains binary data.")
    try:
        text = content.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text), strict=True))
        if not rows or not rows[0]:
            raise ValueError("missing header")
        width = len(rows[0])
        if any(len(row) != width for row in rows[1:] if row):
            raise ValueError("inconsistent column count")
        frame = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    except (UnicodeDecodeError, csv.Error, pd.errors.ParserError, ValueError) as exc:
        raise CatalogIQError("INVALID_CSV", "The upload is not a valid UTF-8 CSV.") from exc
    if frame.empty:
        raise CatalogIQError("EMPTY_CSV", "The CSV contains headers but no product rows.")
    return frame


def validate_required_columns(frame: pd.DataFrame, required: tuple[str, ...]) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise CatalogIQError("MISSING_COLUMNS", f"Missing required columns: {', '.join(missing)}")


def profile_frame(frame: pd.DataFrame) -> dict[str, object]:
    missing = {column: int(frame[column].map(is_placeholder).sum()) for column in frame.columns}
    duplicates = int(frame.duplicated().sum())
    mpn = frame["Mfg_Part_Num"].astype(str).str.strip()
    descriptions = frame["Part_Desc"].astype(str).str.strip()
    duplicate_counts = {
        "manufacturer_part_number": int(mpn[mpn != ""].duplicated().sum()),
        "description": int(descriptions[descriptions != ""].duplicated().sum()),
        "full_row": duplicates,
    }
    manufacturers = sorted({str(v).strip() for v in frame["Part_Manuf"] if not is_placeholder(v)})
    total_cells = max(1, frame.shape[0] * frame.shape[1])
    completeness = round(1 - sum(missing.values()) / total_cells, 4)
    return {
        "row_count": len(frame), "columns": list(frame.columns), "missing_placeholder_counts": missing,
        "duplicate_count": duplicates, "duplicate_counts": duplicate_counts, "placeholder_count": sum(missing.values()), "unique_manufacturers": manufacturers,
        "quality_summary": {"completeness_ratio": completeness, "rows_needing_attention": int(frame.apply(lambda row: any(is_placeholder(v) for v in row), axis=1).sum())},
    }
