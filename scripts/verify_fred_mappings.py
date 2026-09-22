#!/usr/bin/env python3
"""Verify FRED_SERIES_MAP matches the README "FRED Series Mappings" table.

Deterministic, stdlib-only, no network: the mapping constant is inspected in
process; no HTTP call is ever made. Any divergence between the documented
table and the code exits nonzero.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from market_sentiment_fedgpt.airbyte_providers import FRED_SERIES_MAP  # noqa: E402

# The README "FRED Series Mappings" table, verbatim.
EXPECTED = {
    "vix": "VIXCLS",
    "put_call": "CBOE_PC",
    "consumer_confidence": "UMCSENT",
    "umich_sentiment": "UMCSENT",
    "aaii_bull_bear": None,  # not in FRED; falls back to CSV
    "naaim_exposure": None,  # not in FRED; falls back to CSV
}

failures: list[str] = []

for name in sorted(EXPECTED):
    expected = EXPECTED[name]
    actual = FRED_SERIES_MAP.get(name, "<absent>")
    if type(actual) is type(expected) and actual == expected:
        print(f"PASS  {name} -> {actual!r}")
    else:
        failures.append(name)
        print(f"FAIL  {name}: expected {expected!r}, found {actual!r}")

undocumented = sorted(set(FRED_SERIES_MAP) - set(EXPECTED))
if undocumented:
    failures.extend(undocumented)
    print(f"FAIL  series in FRED_SERIES_MAP but not in the README table: {undocumented}")

if failures:
    print(f"\nFRED mapping cross-check: FAILED ({len(failures)} mismatch(es))")
    raise SystemExit(1)
print("\nFRED mapping cross-check: VERIFIED (code matches the README table)")
raise SystemExit(0)
