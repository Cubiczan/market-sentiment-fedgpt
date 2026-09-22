"""Focused pin for the README "Key Features" portfolio-risk-notes claim.

The README states the note rules verbatim: rate-sensitive sectors (Real Estate,
Utilities) under a HAWKISH tone, beta-sensitive sectors (Technology, Consumer
Discretionary) in an EXUBERANT regime, and oversized positions in a FEARFUL
regime. Before the evidence matrix these rules had no named test.
"""

from pathlib import Path

from market_sentiment_fedgpt.core import _portfolio_notes


def _portfolio(tmp_path: Path, *rows: tuple[str, str, str]) -> str:
    lines = ["ticker,sector,weight,source"] + [
        f"{ticker},{sector},{weight},Google Finance" for ticker, sector, weight in rows
    ]
    path = tmp_path / "portfolio.csv"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def test_hawkish_tone_flags_rate_sensitive_sectors(tmp_path):
    path = _portfolio(tmp_path, ("PLD", "Real Estate", "0.07"), ("XEL", "Utilities", "0.03"))
    notes = _portfolio_notes(path, "NEUTRAL", "HAWKISH")
    assert len(notes) == 2
    assert all("rate-sensitive" in note for note in notes)


def test_exuberant_regime_flags_beta_sensitive_sectors(tmp_path):
    path = _portfolio(
        tmp_path, ("NVDA", "Technology", "0.14"), ("AMZN", "Consumer Discretionary", "0.09")
    )
    notes = _portfolio_notes(path, "EXUBERANT", "BALANCED")
    assert len(notes) == 2
    assert all("beta-sensitive" in note for note in notes)


def test_fearful_regime_flags_oversized_positions(tmp_path):
    path = _portfolio(tmp_path, ("BIG", "Industrials", "0.15"), ("SMALL", "Industrials", "0.05"))
    notes = _portfolio_notes(path, "FEARFUL", "BALANCED")
    assert len(notes) == 1
    assert "large position in fearful tape" in notes[0]
    assert "BIG" in notes[0]


def test_quiet_book_outside_documented_conditions_gets_no_flags(tmp_path):
    path = _portfolio(tmp_path, ("SMALL", "Industrials", "0.05"))
    notes = _portfolio_notes(path, "NEUTRAL", "BALANCED")
    assert notes == ["No material portfolio concentration flags from supplied rows."]
