from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "studylab_core"))

from studylab_core import StudyLabAPI  # noqa: E402


def main() -> int:
    benchmark_path = ROOT / "packages" / "eval" / "benchmarks" / "phase1_solver.json"
    cases = json.loads(benchmark_path.read_text(encoding="utf-8"))
    api = StudyLabAPI()
    failures = []
    false_verified = 0
    for case in cases:
        result = api.solve(content=case["question"], subject=case["subject"])
        if case["must_verify"] and not result["verified"]:
            failures.append(f"{case['id']}: expected verified result")
        if result["verified"] and result["answer"] != case["expected_answer"]:
            false_verified += 1
            failures.append(f"{case['id']}: false verified answer {result['answer']}")
    if false_verified:
        failures.append(f"false_verified_rate must be 0, got {false_verified}/{len(cases)}")
    if failures:
        print("\n".join(failures))
        return 1
    print(f"Phase 1 solver eval passed for {len(cases)} cases; false_verified_rate=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
