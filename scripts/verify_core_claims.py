#!/usr/bin/env python3
"""Execute the core engine claims documented in README.md, without pytest.

Deterministic, stdlib-only, no network — runnable in the pre-install
evidence-matrix CI job (the verifier executes this script with the repo root
as the working directory and requires exit 0).

Covers the claims bound as C001/C002/C003/C004/C014 in evidence/matrix.yaml:
fed-tone keyword scoring, regime thresholds, policy-path shape and direction,
portfolio risk-note rules, gate arithmetic, and the end-to-end example-data run.
"""
from __future__ import annotations

import csv
import io
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from market_sentiment_fedgpt._vendored.verification_gate import build_gate  # noqa: E402
from market_sentiment_fedgpt.core import (  # noqa: E402
    REQUIRED_INDICATORS,
    _fed_score,
    _policy_path,
    _portfolio_notes,
    _regime,
    analyze_market,
    report_json,
)

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS  {label}")
    else:
        failures.append(label)
        print(f"FAIL  {label}" + (f" — {detail}" if detail else ""))


def _portfolio_csv(rows: list[tuple[str, str, str]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ticker", "sector", "weight", "source"])
    for ticker, sector, weight in rows:
        writer.writerow([ticker, sector, weight, "Google Finance"])
    handle = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
    handle.write(buf.getvalue())
    handle.close()
    return handle.name


# --- C001: Fed tone analysis -------------------------------------------------
check("hawkish keyword speech scores positive",
      _fed_score("Inflation is persistent and we need higher rates and tightening.") > 0)
check("dovish keyword speech scores negative",
      _fed_score("The economy is cooling and slowing, with cuts likely as disinflation continues.") < 0)
check("neutral speech scores zero",
      _fed_score("The committee will monitor incoming data carefully.") == 0)

# --- C002: regime classification ---------------------------------------------
check("regime EXUBERANT at composite score >= 4",
      _regime(4) == "EXUBERANT" and _regime(10) == "EXUBERANT")
check("regime FEARFUL at composite score <= -4",
      _regime(-4) == "FEARFUL" and _regime(-10) == "FEARFUL")
check("regime NEUTRAL between the thresholds",
      _regime(0) == "NEUTRAL" and _regime(3) == "NEUTRAL" and _regime(-3) == "NEUTRAL")
check("exactly six required indicators", len(REQUIRED_INDICATORS) == 6)

# --- C003: policy probability path -------------------------------------------
path = _policy_path(0, 0)
check("policy path has 3/6/12-month horizons",
      set(path) == {"3_month_cut_probability", "6_month_cut_probability", "12_month_cut_probability"},
      str(sorted(path)))
check("policy path is monotonic by horizon",
      path["3_month_cut_probability"] <= path["6_month_cut_probability"] <= path["12_month_cut_probability"])
check("policy path stays within [0, 1] at extremes",
      all(0.0 <= p <= 1.0 for p in _policy_path(100, 100).values())
      and all(0.0 <= p <= 1.0 for p in _policy_path(-100, -100).values()))
check("hawkish tone reduces cut probability",
      _policy_path(0, 5)["12_month_cut_probability"] < _policy_path(0, -5)["12_month_cut_probability"])
check("fearful sentiment raises cut probability",
      _policy_path(-5, 0)["12_month_cut_probability"] > _policy_path(5, 0)["12_month_cut_probability"])

# --- C004: portfolio risk notes ----------------------------------------------
notes = _portfolio_notes(
    _portfolio_csv([("PLD", "Real Estate", "0.07"), ("XEL", "Utilities", "0.03")]),
    "NEUTRAL", "HAWKISH",
)
check("hawkish tone flags rate-sensitive sectors (Real Estate, Utilities)",
      len(notes) == 2 and all("rate-sensitive" in note for note in notes), str(notes))
notes = _portfolio_notes(
    _portfolio_csv([("NVDA", "Technology", "0.14"), ("AMZN", "Consumer Discretionary", "0.09")]),
    "EXUBERANT", "BALANCED",
)
check("exuberant regime flags beta-sensitive sectors (Technology, Consumer Discretionary)",
      len(notes) == 2 and all("beta-sensitive" in note for note in notes), str(notes))
notes = _portfolio_notes(
    _portfolio_csv([("BIG", "Industrials", "0.15"), ("SMALL", "Industrials", "0.05")]),
    "FEARFUL", "BALANCED",
)
check("fearful regime flags oversized positions (> 10% weight)",
      len(notes) == 1 and "large position in fearful tape" in notes[0], str(notes))
notes = _portfolio_notes(
    _portfolio_csv([("SMALL", "Industrials", "0.05")]),
    "NEUTRAL", "BALANCED",
)
check("no concentration flags outside the documented conditions",
      notes == ["No material portfolio concentration flags from supplied rows."], str(notes))

# --- Gate arithmetic (C006 companion, executed here for the engine path) ------
check("gate: one violation costs 12 confidence points", build_gate(["v1"]).confidence == 88)
check("gate: confidence floors at 50", build_gate([f"v{i}" for i in range(5)]).confidence == 50)
check("gate: clean run is CLEAR at 100",
      build_gate([]).status == "CLEAR" and build_gate([]).confidence == 100)

# --- C014/C009: end-to-end on the included example data -----------------------
report = analyze_market(
    REPO_ROOT / "examples" / "market_indicators.csv",
    REPO_ROOT / "examples" / "fed_speech.txt",
    REPO_ROOT / "examples" / "portfolio.csv",
)
check("example data classifies a FEARFUL regime", report.regime == "FEARFUL")
check("example data exposes regime/fed_tone/sentiment_score/policy_path/verification fields",
      report.regime == "FEARFUL" and report.fed_tone in {"HAWKISH", "BALANCED"}
      and isinstance(report.sentiment_score, int) and bool(report.policy_path)
      and report.verification is not None)
check("example data scores all six indicators", len(report.indicators) == 6)
check("markdown and JSON render from the same report object",
      "Market Sentiment FedGPT Report" in report.to_markdown() and '"regime"' in report_json(report))

if failures:
    print(f"\ncore engine claims: FAILED ({len(failures)} check(s))")
    raise SystemExit(1)
print("\ncore engine claims: VERIFIED")
raise SystemExit(0)
