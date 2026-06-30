"""Stage 0 smoke: nq imports + the carried irreplaceables are present and intact.

These pin the frozen strategy params + the empirical anchor as the rebuild's
ground truth — Stage 2's engine must reproduce a golden fixture consistent with
exactly these params.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_nq_imports() -> None:
    import nq

    assert nq.__version__


def test_frozen_config_carried_and_intact() -> None:
    cfg = json.loads((ROOT / "models/long_horizon/config.json").read_text(encoding="utf-8"))["cfg"]
    assert cfg["signal"] == "sma200_slope_63"
    assert cfg["stop_atr_mult"] == 3.67
    assert cfg["target_pct"] == 22.52
    assert cfg["trailing_activate_pct"] == 4.0
    assert cfg["trailing_pct"] == 4.27
    assert cfg["min_hold_days"] == 10
    assert cfg["max_hold_days"] == 63
    assert cfg["max_positions"] == 15
    assert cfg["risk_per_trade_pct"] == 3.0
    assert cfg["max_position_pct"] == 15.0


def test_baseline_v0_anchor_carried() -> None:
    bv0 = json.loads((ROOT / "research/baseline_v0.json").read_text(encoding="utf-8"))
    assert isinstance(bv0, dict) and bv0, "baseline_v0.json must be present and non-empty"


def test_n_trials_carried() -> None:
    nt = json.loads((ROOT / "diagnostics/research/n_trials.json").read_text(encoding="utf-8"))
    assert nt["cumulative_n_trials"] >= 79, "DSR denominator is the governance count (>= the carried 79; grows per trial)"


def test_golden_fixture_carried() -> None:
    assert (ROOT / "tests/fixtures/lh_golden_panel.csv").exists(), "the golden fixture is the equivalence proof"
