"""Optional local-only two-example prototype benchmark."""
import argparse
from pathlib import Path
import pandas as pd
from app.models.schemas import ProductInput
from app.services.enrichment import DemoEnrichmentService

def evaluate(raw_dir: Path) -> int:
    input_path, expected_path = raw_dir / "Unihack_ Sample Dataset - Input.csv", raw_dir / "Unihack_ Expected Output - Delivery Format.csv"
    if not input_path.exists() or not expected_path.exists():
        print("SKIPPED: organizer files are absent from data/raw"); return 0
    inputs, expected = pd.read_csv(input_path, dtype=str, keep_default_na=False), pd.read_csv(expected_path, dtype=str, keep_default_na=False)
    generated = {}; service = DemoEnrichmentService()
    for _, row in inputs.iterrows(): generated[str(row["Mfg_Part_Num"])] = service.enrich(ProductInput(**{key: str(row[key]) for key in ProductInput.model_fields})).commerce_record
    evaluated = ["MANUFACTURER_NAME", "Product Name", "MARKETING_DESCRIPTION"]
    compared = agreements = examples = excluded = 0
    print("two-example prototype benchmark")
    for _, golden in expected.iterrows():
        record = generated.get(str(golden.get("Mfg_Part_Num", "")))
        if record is None: continue
        examples += 1
        for field in evaluated:
            actual, target = str(record.get(field, "")).strip(), str(golden.get(field, "")).strip()
            if not (actual and target): continue
            normalized_actual, normalized_target = " ".join(actual.casefold().split()), " ".join(target.casefold().split())
            supported = field == "Product Name"
            match = normalized_actual == normalized_target if supported else False
            if supported: compared += 1; agreements += match
            else: excluded += 1
            reason = "normalized values agree" if match else "input identifies a dealer, not evidence for actual manufacturer" if field == "MANUFACTURER_NAME" else "expected marketing prose is absent from supplied input evidence"
            print(f"input={golden.get('Mfg_Part_Num','')} | field={field} | generated={actual!r} | expected={target!r} | normalized={normalized_actual!r} vs {normalized_target!r} | status={'MATCH' if match else 'EXCLUDED_UNSUPPORTED'} | reason={reason}")
    print(f"matched_examples={examples}"); print(f"supported_populated_fields_compared={compared}"); print(f"unsupported_comparisons_excluded={excluded}"); print(f"field_agreements={agreements}"); print(f"field_agreement_ratio={agreements / compared:.4f}" if compared else "field_agreement_ratio=NOT_AVAILABLE"); print("This is not general accuracy."); return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--raw-dir", type=Path, default=Path(__file__).parents[1] / "data" / "raw"); raise SystemExit(evaluate(parser.parse_args().raw_dir))
