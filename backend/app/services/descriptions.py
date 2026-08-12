from dataclasses import dataclass


@dataclass
class DescriptionSet:
    mobile: str
    invoice: str
    short: str
    retail: str
    long: str
    validations: list[dict[str, str]]


ORDER = ["brand", "series", "product_name", "size", "colour", "sound_level"]


def build_descriptions(attributes: dict[str, str]) -> DescriptionSet:
    parts = [attributes[key].strip() for key in ORDER if attributes.get(key)]
    base = " ".join(parts)
    features = [item.strip() for item in attributes.get("features", "").split("|") if item.strip()]
    mobile = base[:80].strip()
    invoice = base[:40].upper().strip()
    short = base[:150].strip()
    retail = ". ".join([base, *features[:2]]).strip(". ")
    long = ". ".join([base, *features]).strip(". ")
    validations = []
    if not attributes.get("product_name"):
        validations.append({"code": "MISSING_PRODUCT_NAME", "status": "INVALID"})
    validations.append({"code": "PROTOTYPE_LENGTH_RULES", "status": "NOT_EVALUATED"})
    return DescriptionSet(mobile, invoice, short, retail, long, validations)
