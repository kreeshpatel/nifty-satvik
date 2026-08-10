"""The dual-unit funnel census.

`r_denominator_audit.json:305` flags that the `<5% ext -> +0.717R` core may be a stop-width
DENOMINATOR artifact rather than an edge — a deeper touch has a tighter stop, so 1R is smaller in
rupees and the same move prints a bigger R. A single-unit table cannot tell those apart, and a
single-unit table is what produced the ambiguity. So the binding requirement is that every band
carries BOTH an R figure and a money figure.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "pipelines" / "diagnostics" / "diag_selectivity_census.py"


def _mod():
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("diag_selectivity_census", SRC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _df(n=40, seed=0):
    rng = np.random.default_rng(seed)
    ext = rng.uniform(-2, 40, n)
    stop_w = np.clip(ext * 0.4 + 5, 1, 40)
    R = rng.normal(0.3, 1.5, n)
    return pd.DataFrame({
        "ticker": [f"T{i}" for i in range(n)],
        "entry_date": pd.bdate_range("2019-01-07", periods=n),
        "setup": "touch44", "R": R, "ext_vs_sma": ext, "risk_pct": stop_w,
        "net_pnl": R * 0.02 * 1_000_000, "rank_crs": rng.uniform(0.01, 0.3, n),
    })


# --------------------------------------------------------------------------- the binding rule
def test_every_band_carries_both_an_R_figure_and_a_money_figure():
    m = _mod()
    rows = m._table(m._bands(_df()), 1_000_000.0, 0.02)
    populated = [r for r in rows if r.get("N")]
    assert populated, "the fixture produced no populated band"
    for r in populated:
        assert "meanR" in r and "mean_equity_pct" in r, f"{r['band']} is single-unit"
        assert "med_stop_width_pct" in r, "stop width is the confound; it must be visible"


def test_notional_is_risk_over_stop_width_so_a_tight_stop_buys_a_big_position():
    """The mechanism. Fixed per-trade risk means shares = equity*RISK/(entry-stop), so a 5% stop
    demands ~4x the cash of a 20% stop for the same risk."""
    m = _mod()
    d = _df()
    d.loc[:, "risk_pct"] = 5.0
    tight = m._table(m._bands(d), 1_000_000.0, 0.02)[-1]["med_notional_pct_of_equity"]
    d.loc[:, "risk_pct"] = 20.0
    wide = m._table(m._bands(d), 1_000_000.0, 0.02)[-1]["med_notional_pct_of_equity"]
    assert tight == pytest.approx(40.0, abs=0.01) and wide == pytest.approx(10.0, abs=0.01)
    assert tight == pytest.approx(4 * wide, rel=1e-6)


def test_a_zero_stop_width_does_not_divide_by_zero():
    m = _mod()
    d = _df(); d.loc[0, "risk_pct"] = 0.0
    rows = m._table(m._bands(d), 1_000_000.0, 0.02)
    assert all(np.isfinite(r["med_notional_pct_of_equity"]) for r in rows if r.get("N"))


# --------------------------------------------------------------------------- the audit resolution
def test_the_denominator_check_detects_proportionality_when_risk_is_fixed():
    """net_pnl built as R * RISK * EQ0 is proportional BY CONSTRUCTION, so the check must say so —
    if it cannot detect the clean case it cannot be trusted on the real one."""
    m = _mod()
    c = m._denominator_check(m._bands(_df()), 1_000_000.0, 0.02)
    assert c["corr_R_vs_equity_pct"] == pytest.approx(1.0, abs=1e-6)
    assert c["median_equity_pct_per_R"] == pytest.approx(2.0, abs=1e-6)
    assert c["expected_if_risk_is_fixed"] == pytest.approx(2.0)


def test_the_denominator_check_detects_a_BROKEN_proportionality():
    """Guard the guard: if sizing were not risk-fixed the check must NOT report proportional."""
    m = _mod()
    d = _df()
    d["net_pnl"] = d["net_pnl"] * np.linspace(0.2, 5.0, len(d))   # size varies independently
    c = m._denominator_check(m._bands(d), 1_000_000.0, 0.02)
    assert c["median_equity_pct_per_R"] != pytest.approx(2.0, abs=1e-3)


def test_it_reports_whether_stop_width_is_monotone_below_ten_percent():
    """If stop width rose monotonically with the band, the denominator concern would survive even
    under proportionality. The answer must be stated, not assumed."""
    m = _mod()
    c = m._denominator_check(m._bands(_df()), 1_000_000.0, 0.02)
    assert isinstance(c["stop_width_is_monotone_below_10pct_ext"], bool)
    assert c["stop_width_by_band_sub10pct_ext"]


# --------------------------------------------------------------------------- selection vs cash
def test_the_decomposition_separates_selection_from_cash():
    m = _mod()
    d = m._bands(_df(80, seed=3))
    d["funded"] = False
    out = m._crs_standing(d)
    for v in out["by_band"].values():
        assert "top5_by_crs_pct" in v and "funded_given_top5_pct" in v
    assert "proxy" in out["_proxy_note"].lower(), "the top-5 proxy must be disclosed as one"


def test_bands_are_frozen_to_the_prior_census_so_the_two_are_comparable():
    m = _mod()
    assert m.BAND_EDGES[1:-1] == [0.0, 5.0, 10.0, 15.0, 20.0, 25.0]
    assert len(m.BAND_LABELS) == len(m.BAND_EDGES) - 1
