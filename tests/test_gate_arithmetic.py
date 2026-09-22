"""Focused pin for the README "Verification Gate" confidence arithmetic.

README: "Reports with violations are marked REQUIRES_HUMAN_VERIFICATION with a
confidence penalty of 12 points per violation (minimum 50%)." The canonical
rule lives in the vendored gate (cubiczan-resilience v0.2.1):
PENALTY_PER_VIOLATION = 12, CONFIDENCE_FLOOR = 50.
"""

from market_sentiment_fedgpt._vendored.verification_gate import (
    CONFIDENCE_FLOOR,
    PENALTY_PER_VIOLATION,
    build_gate,
)


def test_penalty_is_twelve_points_per_violation():
    assert PENALTY_PER_VIOLATION == 12
    one = build_gate(["missing indicator"])
    assert one.confidence == 100 - 12 == 88
    two = build_gate(["missing indicator", "missing source_date"])
    assert two.confidence == 100 - 2 * 12 == 76


def test_confidence_floors_at_fifty_percent():
    assert CONFIDENCE_FLOOR == 50
    gate = build_gate([f"violation {i}" for i in range(5)])  # 100 - 60 -> floor
    assert gate.confidence == 50
    assert gate.status == "REQUIRES_HUMAN_VERIFICATION"


def test_clean_input_is_clear_at_full_confidence():
    gate = build_gate([])
    assert gate.status == "CLEAR"
    assert gate.confidence == 100
    assert gate.violations == []


def test_any_violation_requires_human_verification():
    gate = build_gate(["one small gap"])
    assert gate.status == "REQUIRES_HUMAN_VERIFICATION"
    assert gate.violations == ["one small gap"]
