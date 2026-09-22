#!/usr/bin/env bash
# Executes the README "Quick Start" commands against the included example data.
# No install step, no network: the package runs from src/ via PYTHONPATH.
# Exits nonzero if either invocation fails or loses the documented markers.
set -euo pipefail
cd "$(dirname "$0")/.."

md_out="$(mktemp)"
json_out="$(mktemp)"
trap 'rm -f "$md_out" "$json_out"' EXIT

PYTHONPATH=src python3 -m market_sentiment_fedgpt.cli analyze \
  --indicators examples/market_indicators.csv \
  --speech examples/fed_speech.txt \
  --portfolio examples/portfolio.csv > "$md_out"

grep -q "Market Sentiment FedGPT Report" "$md_out"
grep -q "Verification: CLEAR" "$md_out"
echo "PASS  quick start (markdown) renders the report with a CLEAR gate"

PYTHONPATH=src python3 -m market_sentiment_fedgpt.cli analyze \
  --indicators examples/market_indicators.csv \
  --speech examples/fed_speech.txt \
  --portfolio examples/portfolio.csv \
  --json > "$json_out"

grep -q '"regime"' "$json_out"
grep -q '"verification"' "$json_out"
echo "PASS  quick start (--json) emits machine-readable JSON"

echo "quick start: VERIFIED"
