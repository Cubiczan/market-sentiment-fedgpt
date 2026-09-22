#!/usr/bin/env python3
"""Cross-check evidence/gate_manifest.json against the vendored gate code.

Deterministic, stdlib-only, no network. Every field the manifest documents
must equal the constant or behavior in the code it claims to describe; any
drift exits nonzero (fail-closed). This is the row-25 registry discipline
applied to the VerificationGate: the manifest is the machine-readable record,
and this script proves the record and the code agree.
"""
from __future__ import annotations

import inspect
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from market_sentiment_fedgpt._vendored import verification_gate as gate_module  # noqa: E402

failures: list[str] = []


def check(label: str, expected: object, actual: object) -> None:
    if type(expected) is type(actual) and expected == actual:
        print(f"PASS  {label} = {actual!r}")
    else:
        failures.append(label)
        print(f"FAIL  {label}: manifest {expected!r} != code {actual!r}")


def main() -> int:
    manifest = json.loads(
        (REPO_ROOT / "evidence" / "gate_manifest.json").read_text(encoding="utf-8")
    )
    gate = manifest["gate"]

    check("manifest_version", 1, manifest["manifest_version"])
    check("source_module", "market_sentiment_fedgpt/_vendored/verification_gate.py",
          manifest["source_module"])
    check("upstream_package", "cubiczan-resilience", manifest["upstream_package"])
    check("gate.penalty_per_violation", gate["penalty_per_violation"],
          gate_module.PENALTY_PER_VIOLATION)
    check("gate.confidence_floor", gate["confidence_floor"], gate_module.CONFIDENCE_FLOOR)
    check("gate.severity_floor_hint", gate["severity_floor_hint"], gate_module.SEVERITY_FLOOR)
    check("gate.frozen_dataclass", gate["frozen_dataclass"],
          bool(gate_module.VerificationGate.__dataclass_params__.frozen))
    check("gate.status_vocabulary", gate["status_vocabulary"],
          [gate_module.CLEAR, gate_module.REQUIRES_HUMAN_VERIFICATION])

    match = re.search(r"package version (\d+\.\d+\.\d+)", inspect.getdoc(gate_module) or "")
    check("gate.upstream_version", gate["upstream_version"],
          match.group(1) if match else None)

    # The arithmetic the README documents: 100 - 12 per violation, floored at 50.
    one = gate_module.build_gate(["violation"])
    check("arithmetic: one violation -> 100 - penalty",
          100 - gate_module.PENALTY_PER_VIOLATION, one.confidence)
    five = gate_module.build_gate([f"violation {i}" for i in range(5)])
    check("arithmetic: five violations pin at the floor", gate["confidence_floor"], five.confidence)
    clear = gate_module.build_gate([])
    check("arithmetic: clean input is CLEAR", gate_module.CLEAR, clear.status)
    check("arithmetic: clean input confidence", 100, clear.confidence)

    if failures:
        print(f"\ngate manifest cross-check: FAILED ({len(failures)} mismatch(es))")
        raise SystemExit(1)
    print("\ngate manifest cross-check: VERIFIED (manifest and code agree)")
    raise SystemExit(0)


if __name__ == "__main__":
    raise SystemExit(main())
