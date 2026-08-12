import math
import re
from fractions import Fraction

APPROVED_UNITS = {"v": "V", "a": "A", "in": "in", "dba": "dBA", "kw-hr": "kW-hr"}


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def decimal_to_fraction(value: float) -> str:
    whole = math.floor(value)
    fraction = Fraction(value - whole).limit_denominator(64)
    if fraction.numerator == fraction.denominator:
        whole += 1
        fraction = Fraction(0, 1)
    if not fraction.numerator:
        return str(whole)
    return f"{whole}-{fraction.numerator}/{fraction.denominator}" if whole else f"{fraction.numerator}/{fraction.denominator}"


def normalize_measurement(value: str | float, unit: str) -> str | None:
    normalized_unit = APPROVED_UNITS.get(unit.strip().lower())
    if not normalized_unit:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    rendered = decimal_to_fraction(number) if normalized_unit == "in" else f"{number:g}"
    return f"{rendered} {normalized_unit}"


def normalize_dimensions(width: float, depth: float) -> str:
    return f"{decimal_to_fraction(width)} in W x {decimal_to_fraction(depth)} in D"


def deduplicate_features(features: list[str]) -> list[str]:
    seen: set[str] = set()
    output = []
    for feature in features:
        clean = normalize_whitespace(feature)
        key = clean.casefold()
        if clean and key not in seen:
            seen.add(key)
            output.append(clean)
    return output
