"""Regression: the public VerificationGate contract is IMMUTABLE.

The pre-migration dataclass was mutable; the vendored canonical gate
(cubiczan-resilience v0.2.0) is frozen by design. Consumers must derive
modified copies with dataclasses.replace, not field assignment. These
tests pin that contract so an accidental unfreeze fails CI.
"""

from dataclasses import FrozenInstanceError, replace

import pytest

from market_sentiment_fedgpt.core import VerificationGate, build_gate


def _gate() -> VerificationGate:
    return build_gate(["holdings file is empty"])


def test_gate_field_assignment_raises_frozen_instance_error():
    gate = _gate()
    with pytest.raises(FrozenInstanceError):
        gate.status = "CLEAR"


def test_gate_confidence_assignment_also_frozen():
    gate = _gate()
    with pytest.raises(FrozenInstanceError):
        gate.confidence = 100


def test_replace_produces_a_valid_frozen_copy():
    gate = _gate()
    derived = replace(gate, status="REQUIRES_HUMAN_VERIFICATION", confidence=50)
    assert derived is not gate
    assert derived.status == "REQUIRES_HUMAN_VERIFICATION"
    assert derived.confidence == 50
    # original untouched
    assert gate.status == "REQUIRES_HUMAN_VERIFICATION"
    # derived copy obeys the same immutability
    with pytest.raises(FrozenInstanceError):
        derived.violations = []


def test_replace_on_a_clear_gate_downgrades_without_mutation():
    gate = build_gate([])  # healthy path
    assert gate.status == "CLEAR"
    downgraded = replace(gate, status="REQUIRES_HUMAN_VERIFICATION")
    assert gate.status == "CLEAR"
    assert downgraded.status == "REQUIRES_HUMAN_VERIFICATION"
