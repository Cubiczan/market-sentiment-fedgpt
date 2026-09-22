"""Offline pins for the README "Airbyte Integration" claims.

No network, no optional SDK: the Airbyte bridge must import cleanly without
airbyte-agent-sdk, fall back to the included CSV examples when no credentials
are configured, and leave the synchronous analyze_market() path untouched.
"""

import asyncio
import inspect
from pathlib import Path

import pytest

import market_sentiment_fedgpt.airbyte_providers as providers
from market_sentiment_fedgpt.core import analyze_market

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = REPO_ROOT / "examples"

REQUIRED_INDICATORS = {
    "aaii_bull_bear",
    "naaim_exposure",
    "vix",
    "put_call",
    "consumer_confidence",
    "umich_sentiment",
}


@pytest.fixture(autouse=True)
def _offline_env(monkeypatch):
    """No credentials anywhere: every path here must be the offline fallback."""
    for var in ("AIRBYTE_CLIENT_ID", "AIRBYTE_CLIENT_SECRET", "FRED_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(REPO_ROOT)  # FALLBACK_* paths are repo-root-relative


def test_module_imports_without_the_optional_sdk():
    assert providers.is_airbyte_available() is False


def test_fetch_live_indicators_falls_back_to_csv_without_credentials():
    indicators = providers.fetch_live_indicators(api_key=None)
    names = {row["indicator"] for row in indicators}
    assert names == REQUIRED_INDICATORS


def test_analyze_via_airbyte_offline_run_passes_the_gate():
    result = asyncio.run(providers.analyze_market_via_airbyte(api_key=None))
    assert result["data_source"] == "csv_fallback"
    assert result["airbyte_available"] is False
    assert result["regime"] in {"EXUBERANT", "NEUTRAL", "FEARFUL"}
    assert result["verification"]["status"] == "CLEAR"
    assert result["verification"]["confidence"] == 100


def test_data_source_vocabulary_is_airbyte_live_or_csv_fallback():
    result = asyncio.run(providers.analyze_market_via_airbyte(api_key=None))
    assert result["data_source"] in {"airbyte_fred_live", "csv_fallback"}


def test_get_mcp_config_exposes_the_documented_server_url():
    config = providers.get_mcp_config()
    assert config["mcp_server_url"] == "https://mcp.airbyte.ai/mcp"


def test_fred_series_map_matches_the_readme_table():
    assert providers.FRED_SERIES_MAP == {
        "aaii_bull_bear": None,  # not in FRED; CSV fallback
        "naaim_exposure": None,  # not in FRED; CSV fallback
        "vix": "VIXCLS",
        "put_call": "CBOE_PC",
        "consumer_confidence": "UMCSENT",
        "umich_sentiment": "UMCSENT",
    }


def test_synchronous_analyze_market_remains_untouched_by_the_bridge():
    # The README's backward-compatibility claim: analyze_market() stays a
    # synchronous, local-file API independent of the Airbyte bridge.
    assert not inspect.iscoroutinefunction(analyze_market)
    report = analyze_market(
        EXAMPLES / "market_indicators.csv",
        EXAMPLES / "fed_speech.txt",
        EXAMPLES / "portfolio.csv",
    )
    assert report.verification.status == "CLEAR"
