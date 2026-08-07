"""Market impact is charged, and the two-pass re-pricing that charges it is exercised.

`simulate` fills an entry twice. The first pass prices at the liquidity-tier rate and sizes the
position off it; the second re-prices at `_slip(adv, notional)`, which adds a flat 0.1% once the
order exceeds 0.5% of the name's daily rupee turnover, and re-checks affordability:

    notional = qty * fill
    slip2    = _slip(adv, notional)
    fill     = o * (1 + slip2)          # re-price with impact for the actual size

A mutation probe on 2026-08-08 found this whole branch to be **dead in every golden master**.
Raising the impact threshold, doubling the impact, or deleting the re-pricing outright left both
`test_stage2_golden` and `test_rebalance_golden` byte-identical. The cause is the fixture, not the
code: `lh_golden_panel.csv` is 11 mega-caps with a minimum ADV around ₹32.9cr, so a 15%-capped
position on ₹10L of equity is roughly 150k against an impact threshold of ~₹16.5L — an order of
magnitude away from ever triggering. The term survived in the suite only through
`test_signal_book.py`'s hard-coded `100.0*1.005`, which reaches `_slip` through a *different* engine.

That matters because impact is the cost that grows precisely where fills are least believable —
thin names, large orders. An engine that silently stopped charging it would report better results on
exactly the trades most likely to be unachievable, and every golden would agree.

So this file pins the boundary arithmetic directly, and then runs `simulate` on a panel thin enough
for the second pass to bite — with a guard-the-guard that fails if the fixture ever stops biting.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from config import ADV_LARGE_CAP_RS, ADV_MID_CAP_RS, SLIPPAGE, load_frozen_cfg
from nq.data.features import compute_all_features
from nq.engine.panel import compose_ranked_panel
from nq.engine.portfolio import _slip, leg_slippage, simulate

CFG = load_frozen_cfg()
IMPACT_ADD = 0.001          # flat impact above the participation threshold
IMPACT_AT = 0.005           # ...of the name's daily rupee turnover


# --------------------------------------------------------------------------- the boundary itself
def test_below_the_threshold_only_the_tier_rate_is_charged():
    adv = 1e8                                        # MID_CAP tier
    assert _slip(adv, IMPACT_AT * adv * 0.99) == SLIPPAGE["MID_CAP"]


def test_above_the_threshold_impact_is_added():
    adv = 1e8
    assert _slip(adv, IMPACT_AT * adv * 1.01) == pytest.approx(SLIPPAGE["MID_CAP"] + IMPACT_ADD)


def test_exactly_at_the_threshold_does_not_charge_impact():
    """The comparison is strict (`notional > 0.005 * adv`). Pinned because a `>` / `>=` flip is a
    one-character change that no golden can see."""
    adv = 1e8
    assert _slip(adv, IMPACT_AT * adv) == SLIPPAGE["MID_CAP"]


def test_zero_adv_never_charges_impact():
    """Guarded by `adv > 0` — without it a missing-ADV name would divide the book's cost model by
    an assumption nobody made."""
    assert _slip(0.0, 1e9) == SLIPPAGE["SMALL_CAP"]


@pytest.mark.parametrize("adv,tier", [
    (ADV_LARGE_CAP_RS, "LARGE_CAP"),
    (ADV_LARGE_CAP_RS - 1, "MID_CAP"),
    (ADV_MID_CAP_RS, "MID_CAP"),
    (ADV_MID_CAP_RS - 1, "SMALL_CAP"),
])
def test_tier_boundaries_are_inclusive_downward(adv: float, tier: str):
    assert _slip(adv, 0.0) == SLIPPAGE[tier]


def test_the_public_wrapper_defaults_to_the_first_pass():
    """`leg_slippage(adv)` with no notional is what the LIVE scan quotes as its indicative entry.
    It must equal the backtest's FIRST pass — tier rate, no impact — or live and backtest diverge
    on cost at the moment of the quote."""
    assert leg_slippage(2e8) == _slip(2e8, 0.0) == SLIPPAGE["MID_CAP"]


# --------------------------------------------------------------- the second pass inside simulate
def _thin_name(n: int, seed: int, drift: float, shares_per_day: float) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(drift, 0.012, n)))
    return pd.DataFrame(
        {"Open": close * (1 + rng.normal(0, 0.003, n)), "High": close * 1.004,
         "Low": close * 0.996, "Close": close,
         "Volume": np.full(n, shares_per_day, dtype=float)},
        index=pd.bdate_range("2015-01-01", periods=n),
    )


def _thin_panel() -> pd.DataFrame:
    """Names liquid enough to stay in the universe, thin enough that a normal position crosses
    0.5% of ADV. At ~₹100 and 60k shares/day the ADV is ~₹60L, so the threshold is ~₹30k — well
    under a 15%-capped position on ₹10L."""
    ohlcv = {"AAA": _thin_name(600, 1, 0.0012, 60_000),
             "BBB": _thin_name(600, 2, 0.0009, 60_000),
             "CCC": _thin_name(600, 3, 0.0006, 60_000)}
    feats = compute_all_features(ohlcv, holidays=set())
    fund = {t: pd.DataFrame({"debt_equity": [0.3], "roe": [15.0]},
                            index=pd.to_datetime(["2014-06-01"])) for t in ohlcv}
    return compose_ranked_panel(feats, ohlcv, fund_store=fund, membership=None, min_adv_rs=0.0)


def test_entries_large_relative_to_turnover_are_repriced_with_impact():
    panel = _thin_panel()
    assert not panel.empty, "fixture produced no eligible names"
    res = simulate(panel, CFG)
    trades = res["trades"]
    assert trades, "fixture produced no trades — it cannot say anything about entry pricing"

    lookup = {(str(r["date"])[:10], r["ticker"]): r for _, r in panel.iterrows()}
    charged = 0
    for t in trades:
        row = lookup.get((str(t["entry_date"])[:10], t["ticker"]))
        if row is None:
            continue
        adv, notional = float(row["adv_rupees_20d"]), float(t["entry"]) * float(t["qty"])
        if notional > IMPACT_AT * adv:
            tier_only = float(row["open"]) * (1.0 + _slip(adv, 0.0))
            assert float(t["entry"]) > tier_only, (
                f"{t['ticker']} on {t['entry_date']}: notional {notional:,.0f} exceeds "
                f"{IMPACT_AT:.1%} of ADV {adv:,.0f}, but the entry filled at the tier-only price. "
                f"The second pass in simulate is not re-pricing."
            )
            charged += 1

    assert charged > 0, (
        "no trade in this fixture crossed the impact threshold, so the test proves nothing about "
        "the second pass. This is the same blindness the goldens have — make the names thinner or "
        "the positions larger until the branch is reached."
    )
