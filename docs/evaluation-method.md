# Evaluation method

`python evaluate_golden.py` reads ignored files under `data/raw`, matches by manufacturer part number, and compares only fields populated by both the implementation and expected row. It reports a **two-example prototype benchmark**, never general accuracy. Missing files produce a successful skip.
