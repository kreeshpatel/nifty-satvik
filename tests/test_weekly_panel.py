"""`nq/data/weekly.py` had no tests at all, and it makes a parity claim it never checked.

The module exists to stop ~10 swing scripts each re-deriving weekly candles — some by ISO week,
some by `resample("W-FRI")` — and its docstring states the aggregation is "**byte-identical to the
0094 book's** ISO-week grouping in `scripts/run_bhanushali_weekly_rank.prep_weekly_rank`". That
claim is the module's entire reason to exist: it is what lets the Stage-1 research substrate be
reconciled against the book that trades real capital. Nothing enforced it, and no test referenced
`nq.data.weekly` anywhere in the repo.

An unchecked parity claim is worse than no claim. A drift in the ISO-week run grouping, the 44-week
SMA, or the 13-week slope shift would silently re-base every swing diagnostic against a different
weekly panel than the live book uses, and the diagnostics would still look internally consistent.

So: the constants, the aggregation semantics derived by hand, and — the point of the file — a direct
differencing against `prep_weekly_rank` on a shared fixture.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from nq.data.weekly import (  # noqa: E402
    MIN_DAILY_BARS,
    SLOPE_LOOKBACK,
    SMA_LEN,
    _iso_week_groups,
    build_weekly_panel,
)


def _synth(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.001, 0.015, n)))
    return pd.DataFrame(
        {"Open": c * 0.999, "High": c * 1.01, "Low": c * 0.99, "Close": c,
         "Volume": np.full(n, 5e5)},
        index=pd.bdate_range("2018-01-01", periods=n),
    )


@pytest.fixture(scope="module")
def ohlcv() -> dict[str, pd.DataFrame]:
    return {"AAA": _synth(700, 1), "BBB": _synth(700, 2)}


# ------------------------------------------------------------------ constants frozen to the book
def test_constants_match_the_live_book():
    """The 44-week line is owner-mandated as an SMA and the slope lookback is the live
    `SLOPE_LOOKBACK`. Both are pinned in the book; pin them here so the two cannot drift apart
    silently."""
    assert (SMA_LEN, SLOPE_LOOKBACK, MIN_DAILY_BARS) == (44, 13, 300)


# ------------------------------------------------------------------ aggregation, derived by hand
def test_iso_week_grouping_is_sequential_runs_not_calendar_keys():
    """Runs of equal (iso_year, iso_week), in order. A `groupby` on the key would merge two
    non-adjacent stretches that share a week number across a gap; this must not."""
    idx = pd.DatetimeIndex(["2018-01-01", "2018-01-02", "2018-01-08", "2018-01-09", "2018-01-10"])
    assert _iso_week_groups(idx) == [[0, 1], [2, 3, 4]]


def test_iso_week_grouping_handles_the_year_boundary():
    """ISO week 1 of 2019 begins Mon 31 Dec 2018 — a calendar-year grouping would split it."""
    idx = pd.DatetimeIndex(["2018-12-28", "2018-12-31", "2019-01-01"])
    assert _iso_week_groups(idx) == [[0], [1, 2]]


def test_weekly_ohlc_is_first_open_max_high_min_low_last_close(ohlcv):
    panel = build_weekly_panel(ohlcv)
    df = ohlcv["AAA"]
    idx = pd.to_datetime(df.index)
    groups = _iso_week_groups(idx)
    rows = panel[panel.ticker == "AAA"].reset_index(drop=True)

    assert len(rows) == len(groups)
    for i in (0, 5, len(groups) - 1):
        g = groups[i]
        assert rows.loc[i, "o"] == pytest.approx(df["Open"].to_numpy()[g[0]])
        assert rows.loc[i, "h"] == pytest.approx(df["High"].to_numpy()[g].max())
        assert rows.loc[i, "l"] == pytest.approx(df["Low"].to_numpy()[g].min())
        assert rows.loc[i, "c"] == pytest.approx(df["Close"].to_numpy()[g[-1]])
        assert rows.loc[i, "v"] == pytest.approx(df["Volume"].to_numpy()[g].sum())
        assert rows.loc[i, "n_days"] == len(g)
        assert rows.loc[i, "week_end"] == idx[g[-1]]


def test_sma_and_slope_warm_up_exactly_where_they_should(ohlcv):
    panel = build_weekly_panel(ohlcv)
    rows = panel[panel.ticker == "AAA"].reset_index(drop=True)
    assert rows["sma44"].iloc[: SMA_LEN - 1].isna().all()
    assert rows["sma44"].iloc[SMA_LEN - 1 :].notna().all()
    assert rows["sma44"].iloc[SMA_LEN - 1] == pytest.approx(rows["c"].iloc[:SMA_LEN].mean())
    # slope is a ratio over SLOPE_LOOKBACK weeks of the SMA, so it is NaN wherever either end is
    assert rows["slope44"].iloc[:SLOPE_LOOKBACK].isna().all()
    i = SMA_LEN - 1 + SLOPE_LOOKBACK
    expected = rows["sma44"].iloc[i] / rows["sma44"].iloc[i - SLOPE_LOOKBACK] - 1.0
    assert rows["slope44"].iloc[i] == pytest.approx(expected)


def test_names_below_the_daily_floor_are_skipped():
    panel = build_weekly_panel({"THIN": _synth(MIN_DAILY_BARS - 1, 9), "OK": _synth(400, 10)})
    assert set(panel["ticker"]) == {"OK"}


def test_output_is_deterministic_and_independent_of_dict_order():
    a = build_weekly_panel({"AAA": _synth(400, 1), "BBB": _synth(400, 2)})
    b = build_weekly_panel({"BBB": _synth(400, 2), "AAA": _synth(400, 1)})
    pd.testing.assert_frame_equal(a, b)


# ------------------------------------------------------- the parity claim, differenced for real
def test_parity_with_the_live_books_weekly_derivation(ohlcv):
    """The claim in the module docstring, checked against `prep_weekly_rank` itself.

    `prep_weekly_rank` returns per-ticker dicts keyed by the DAILY positional index of each week's
    last bar: `weekend` (the set of those positions), `wk_hlc[pos] = (high, low, close, ...)`, and
    `wsma_at[pos]`. Mapping this module's `week_end` dates back to positions makes the two directly
    comparable.
    """
    import importlib

    book = importlib.import_module("run_bhanushali_weekly_rank")
    prepped = book.prep_weekly_rank(ohlcv)
    panel = build_weekly_panel(ohlcv)

    for tkr, df in ohlcv.items():
        state = prepped[tkr]
        idx = pd.to_datetime(df.index)
        rows = panel[panel.ticker == tkr].reset_index(drop=True)
        positions = [idx.get_loc(d) for d in rows["week_end"]]

        assert set(positions) == set(state["weekend"]), (
            f"{tkr}: the week-end bars disagree between nq.data.weekly and the live book. The "
            f"ISO-week run grouping has drifted, so every swing diagnostic built on this module is "
            f"re-based against a different weekly panel than the book trades."
        )

        for pos, (_, row) in zip(positions, rows.iterrows()):
            h, l, c = state["wk_hlc"][pos][:3]
            assert row["h"] == pytest.approx(h), f"{tkr}@{pos}: weekly high"
            assert row["l"] == pytest.approx(l), f"{tkr}@{pos}: weekly low"
            assert row["c"] == pytest.approx(c), f"{tkr}@{pos}: weekly close"

            want_sma = state["wsma_at"][pos]
            got_sma = row["sma44"]
            if np.isnan(want_sma) or np.isnan(got_sma):
                assert np.isnan(want_sma) and np.isnan(got_sma), (
                    f"{tkr}@{pos}: the 44-week SMA warms up at different weeks in the two "
                    f"implementations"
                )
            else:
                assert got_sma == pytest.approx(want_sma), f"{tkr}@{pos}: 44-week SMA"
