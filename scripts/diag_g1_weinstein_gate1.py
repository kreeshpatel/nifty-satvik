"""G1 (Weinstein stage analysis) — GATE-1 census. MEASUREMENT ONLY.

Spends no trial and no screen. No backtest, no exits, no capital, no config change, no
forward-wall read. This script answers the two questions the owner put ahead of any Phase-2
build, and stops:

  (a) ENTRY-COUNT CENSUS — how many stage-2 breakouts per year clear the FULL letter-faithful
      spec (stage-1 base + Mansfield RS >= 0 and rising + volume >= 2x the 10-week average) on
      the corrected universe? If the count is famine-class, we stop and report: underpowering
      is this programme's known killer and it is cheaper to measure it than to discover it.

  (b) EXT-AT-ENTRY — where do those breakouts land against the SLOW weekly line (44w SMA)?
      The load-bearing claim behind the G1 pick is that a stage-1-base breakout fires
      pre-extension. The companion census (`diag_ext_band_census.py`) showed every funnel we
      already own is post-extension on that axis (six-step median 29.5%, box 33.8%). This
      verifies G1's claim empirically BEFORE anything is built.

A leg-by-leg attrition table is included so the famine (if any) is attributed to a named leg
rather than to "the spec" — diagnosis, not tuning. NOTHING here is swept: every parameter is
frozen at a single value chosen once, from the source, and recorded with its interpretation.

================================ FROZEN SPEC + INTERPRETATIONS ================================
Weinstein, "Secrets for Profiting in Bull and Bear Markets" (1988). Weekly bars only.

  LINE          30-week SMA of the weekly close.  *His* line, not our 44w — QUARANTINED
                research-only (the W89 precedent: a foreign grammar may use its own line; our
                base's 44-week line remains an SMA and is untouched).
  STAGE 1       Trailing BASE_LEN weeks in which (i) the 30w SMA is FLAT and (ii) price is
                range-bound.  Weinstein gives no numbers for either; interpretations:
                  BASE_LEN=26 weeks   — his stage-1 bases "last for months"; 6 months is the
                                        span of his worked illustrations.
                  FLAT_TOL=5%         — |sma30 drift across the base| <= 5% == "flat".
                  BASE_RANGE_MAX=35%  — a stage-1 TRADING RANGE, deliberately looser than our
                                        15% flat-base box: Weinstein's bases are wide.
  TRIGGER       Weekly CLOSE above the base ceiling (= the base's high).  He teaches two buys —
                the breakout and the pullback-to-breakout; the census models the BREAKOUT, his
                primary, and records that the pullback buy is not measured here.
  STAGE 2       Close above the 30w SMA AND the 30w SMA no longer declining
                (sma30[k] >= sma30[k-4]) — "the MA has flattened out and is turning up".
  RS            Mansfield Relative Strength: rs = close / index_close;
                mansfield = (rs / SMA_RS(rs) - 1) * 100.  Require >= 0 AND rising over 4 weeks.
                  RS_SMA_LEN=52 weeks — Mansfield's own construction.
                  NOTE (overlap, reported): our incumbent's ranker of record `crs_dist` is the
                  SAME construction at 40 weeks (run_bhanushali_weekly_rank.CRS_LEN=40). We use
                  Weinstein's 52 for letter-faithfulness; the 40w twin is our house lever.
                  INDEX: Nifty-50 (`research/exports/benchmark_nifty50.csv`) — the house index
                  of record for CRS, and the only series covering the full window (the N500 TRI
                  starts 2017-09, which a 52-week RS SMA would push to ~2018-09).
  VOLUME        Breakout-week volume >= 2.0x the mean of the trailing 10 weeks.  He requires a
                "significant" volume increase without a number; 2x/10wk is his charts' rule of
                thumb, recorded as an interpretation.
  ONE PER BASE  A name may not re-signal within COOLDOWN=26 weeks of a prior signal — one
                stage-2 entry per stage-1 base, as taught.
  STOP          Base low (reported for geometry only; no trades are simulated here).

Reproduce:
    python scripts/diag_g1_weinstein_gate1.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from nq.data.membership import load_membership, ticker_in_index_on  # noqa: E402
from nq.data.weekly import build_weekly_panel, _panel_hash  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

# ---- FROZEN PARAMETERS (chosen once, from the source; never swept) ----
SMA_LEN = 30            # weeks — Weinstein's line
BASE_LEN = 26           # weeks of stage-1 base
FLAT_TOL = 0.05         # |30w SMA drift across the base|
BASE_RANGE_MAX = 0.35   # base high/low range
MA_TURN_LOOKBACK = 4    # weeks — sma30[k] >= sma30[k-4]
RS_SMA_LEN = 52         # weeks — Mansfield
RS_RISE_LOOKBACK = 4    # weeks
VOL_MULT = 2.0
VOL_LOOKBACK = 10       # weeks
COOLDOWN = 26           # weeks between signals on one name
ADV_MIN = 5e7           # Rs 5 crore — the house liquidity floor, reported as a variant

START = pd.Timestamp("2017-01-01")
INDEX_CSV = ROOT / "research" / "exports" / "benchmark_nifty50.csv"
OUT_JSON = ROOT / "diagnostics" / "research" / "g1_weinstein_gate1.json"
OUT_MD = ROOT / "diagnostics" / "research" / "g1_weinstein_gate1.md"

BAND_EDGES = [-np.inf, 0.0, 5.0, 10.0, 15.0, 20.0, 25.0, np.inf]
BAND_NAMES = ["<0 (below wk line)", "0-5%", "5-10%", "10-15%", "15-20%", "20-25%", ">25%"]

LEGS = ["universe (weeks with a 30w SMA + a full base window)",
        "+ stage-1 base: 30w SMA flat",
        "+ stage-1 base: price range-bound",
        "+ close > base ceiling (the breakout)",
        "+ close > 30w SMA",
        "+ 30w SMA flattened / turning up",
        "+ Mansfield RS >= 0",
        "+ Mansfield RS rising (4wk)",
        "+ volume >= 2x 10wk avg",
        "+ one-signal-per-base cooldown"]


def _echo(text: str) -> None:
    """Print without dying on a cp1252 console — the artifact on disk is always UTF-8."""
    enc = sys.stdout.encoding or "utf-8"
    sys.stdout.write(text.encode(enc, errors="replace").decode(enc, errors="replace") + "\n")


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in df.iterrows():
        out.append("| " + " | ".join(
            "—" if (isinstance(row[c], float) and np.isnan(row[c])) else str(row[c])
            for c in cols) + " |")
    return "\n".join(out)


def adv20_by_week(ohlcv: dict, panel: pd.DataFrame) -> dict[tuple[str, pd.Timestamp], float]:
    """Rs turnover: 20-day mean of close*volume, sampled on each week_end trading day."""
    wanted = {t: set(g["week_end"]) for t, g in panel.groupby("ticker", sort=False)}
    out: dict[tuple[str, pd.Timestamp], float] = {}
    for tkr, df in ohlcv.items():
        if tkr not in wanted or "Volume" not in df.columns:
            continue
        idx = pd.to_datetime(df.index)
        turn = df["Close"].to_numpy(float) * df["Volume"].to_numpy(float)
        adv = pd.Series(turn, index=idx).rolling(20).mean()
        hit = adv.reindex(pd.DatetimeIndex(sorted(wanted[tkr])))
        for d, v in hit.items():
            out[(tkr, d)] = float(v)
    return out


def detect(panel: pd.DataFrame, idx_weekly: pd.Series) -> tuple[pd.DataFrame, np.ndarray]:
    """Run the frozen Weinstein spec over the weekly panel. Returns (signals, leg-attrition)."""
    legs = np.zeros(len(LEGS), dtype=np.int64)
    rows = []

    for tkr, g in panel.groupby("ticker", sort=True):
        g = g.sort_values("week_end", kind="mergesort")
        we = g["week_end"].to_numpy()
        h, l, c, v = (g[x].to_numpy(float) for x in ("h", "l", "c", "v"))
        sma44 = g["sma44"].to_numpy(float)
        n = len(c)
        if n < BASE_LEN + SMA_LEN + 2:
            continue

        sma30 = pd.Series(c).rolling(SMA_LEN).mean().to_numpy()
        iw = idx_weekly.reindex(pd.DatetimeIndex(we), method="ffill").to_numpy(float)
        rs = np.where(iw > 0, c / iw, np.nan)
        rs_sma = pd.Series(rs).rolling(RS_SMA_LEN).mean().to_numpy()
        mans = 100.0 * (rs / rs_sma - 1.0)
        volavg = pd.Series(v).rolling(VOL_LOOKBACK).mean().shift(1).to_numpy()

        last_sig = -10**9
        for k in range(BASE_LEN + 1, n):
            if pd.Timestamp(we[k]) < START:
                continue
            b0, b1 = k - BASE_LEN, k                      # base window [b0, k)
            if not np.isfinite(sma30[k]) or not np.isfinite(sma30[b0]):
                continue
            legs[0] += 1

            if abs(sma30[k - 1] / sma30[b0] - 1.0) > FLAT_TOL:
                continue
            legs[1] += 1

            base_hi = np.nanmax(h[b0:b1]); base_lo = np.nanmin(l[b0:b1])
            if not (base_lo > 0 and (base_hi - base_lo) / base_lo <= BASE_RANGE_MAX):
                continue
            legs[2] += 1

            if not (c[k] > base_hi):
                continue
            legs[3] += 1
            if not (c[k] > sma30[k]):
                continue
            legs[4] += 1
            if not (k >= MA_TURN_LOOKBACK and sma30[k] >= sma30[k - MA_TURN_LOOKBACK]):
                continue
            legs[5] += 1
            if not (np.isfinite(mans[k]) and mans[k] >= 0.0):
                continue
            legs[6] += 1
            if not (k >= RS_RISE_LOOKBACK and np.isfinite(mans[k - RS_RISE_LOOKBACK])
                    and mans[k] > mans[k - RS_RISE_LOOKBACK]):
                continue
            legs[7] += 1
            if not (np.isfinite(volavg[k]) and volavg[k] > 0 and v[k] >= VOL_MULT * volavg[k]):
                continue
            legs[8] += 1
            if k - last_sig < COOLDOWN:
                continue
            legs[9] += 1
            last_sig = k

            rows.append(dict(
                ticker=tkr, week_end=pd.Timestamp(we[k]), entry=float(c[k]),
                base_hi=float(base_hi), base_lo=float(base_lo),
                stop_pct=round(100.0 * (1.0 - base_lo / c[k]), 2),
                base_range_pct=round(100.0 * (base_hi - base_lo) / base_lo, 2),
                sma30=float(sma30[k]), sma44=float(sma44[k]) if np.isfinite(sma44[k]) else np.nan,
                ext_vs_30w_pct=round(100.0 * (c[k] / sma30[k] - 1.0), 2),
                ext_vs_44w_pct=(round(100.0 * (c[k] / sma44[k] - 1.0), 2)
                                if np.isfinite(sma44[k]) and sma44[k] > 0 else np.nan),
                mansfield=round(float(mans[k]), 2),
                vol_x=round(float(v[k] / volavg[k]), 2),
            ))
    return pd.DataFrame(rows), legs


def main() -> None:
    ohlcv = corrected_universe()
    panel = build_weekly_panel(ohlcv)
    phash = _panel_hash(panel)
    idx = (pd.read_csv(INDEX_CSV, parse_dates=["date"]).set_index("date")["nifty50_close"]
           .sort_index())

    sig, legs = detect(panel, idx)
    mem = load_membership() or {}
    advmap = adv20_by_week(ohlcv, panel)

    sig["year"] = sig["week_end"].dt.year
    sig["is_member"] = [ticker_in_index_on(t, d.date(), mem)
                        for t, d in zip(sig["ticker"], sig["week_end"])]
    sig["adv20"] = [advmap.get((t, d), np.nan) for t, d in zip(sig["ticker"], sig["week_end"])]
    sig["liquid"] = sig["adv20"] >= ADV_MIN
    sig["band"] = pd.cut(sig["ext_vs_44w_pct"], bins=BAND_EDGES, labels=BAND_NAMES, right=False)

    memb = sig[sig["is_member"]]
    both = memb[memb["liquid"]]

    # ---- (a) counts ----
    years = sorted(sig["year"].unique())
    per_year = pd.DataFrame([dict(
        year=int(y),
        all_signals=int((sig["year"] == y).sum()),
        pit_member=int((memb["year"] == y).sum()),
        member_and_ADV5cr=int((both["year"] == y).sum()),
        distinct_names=int(both[both["year"] == y]["ticker"].nunique()),
    ) for y in years])
    per_year.loc[len(per_year)] = dict(
        year="TOTAL", all_signals=len(sig), pit_member=len(memb),
        member_and_ADV5cr=len(both), distinct_names=both["ticker"].nunique())

    span_yrs = (sig["week_end"].max() - sig["week_end"].min()).days / 365.25 if len(sig) else 0.0
    rate = len(both) / span_yrs if span_yrs > 0 else 0.0

    attrition = pd.DataFrame([dict(
        leg=LEGS[i], name_weeks=int(legs[i]),
        pct_of_universe=round(100.0 * legs[i] / max(legs[0], 1), 4),
        survival_vs_prev=(round(100.0 * legs[i] / legs[i - 1], 2) if i and legs[i - 1] else "—"),
    ) for i in range(len(LEGS))])

    # ---- (b) ext at entry ----
    band_rows = []
    for b in BAND_NAMES:
        s = both[both["band"] == b]
        band_rows.append(dict(band=b, N=len(s),
                              share_pct=round(100.0 * len(s) / max(len(both), 1), 1)))
    band_tbl = pd.DataFrame(band_rows)

    ext_stats = dict(
        median_ext_vs_44w=round(float(both["ext_vs_44w_pct"].median()), 2) if len(both) else None,
        mean_ext_vs_44w=round(float(both["ext_vs_44w_pct"].mean()), 2) if len(both) else None,
        share_below_5pct=round(100.0 * float((both["ext_vs_44w_pct"] < 5.0).mean()), 1) if len(both) else None,
        median_ext_vs_30w=round(float(both["ext_vs_30w_pct"].median()), 2) if len(both) else None,
        median_stop_pct=round(float(both["stop_pct"].median()), 2) if len(both) else None,
        median_base_range_pct=round(float(both["base_range_pct"].median()), 2) if len(both) else None,
    )

    # Comparison set from the companion census (committed numbers, quoted not recomputed).
    comparison = {"touch44 (incumbent)": 8.72, "trend_pullback": 22.10, "cup_handle": 28.48,
                  "0084/0085 six-step": 29.53, "double_bottom": 31.64, "vcp (zoo)": 33.24,
                  "box": 33.78, "sr_pivot": 37.87}

    payload = dict(
        _doc="G1 Weinstein Gate-1 census (MEASUREMENT; 0 trials, 0 screens). Entry-count census "
             "+ ext-at-entry. No backtest, no capital, no config change.",
        frozen_params=dict(SMA_LEN=SMA_LEN, BASE_LEN=BASE_LEN, FLAT_TOL=FLAT_TOL,
                           BASE_RANGE_MAX=BASE_RANGE_MAX, MA_TURN_LOOKBACK=MA_TURN_LOOKBACK,
                           RS_SMA_LEN=RS_SMA_LEN, RS_RISE_LOOKBACK=RS_RISE_LOOKBACK,
                           VOL_MULT=VOL_MULT, VOL_LOOKBACK=VOL_LOOKBACK, COOLDOWN=COOLDOWN,
                           ADV_MIN=ADV_MIN, index="nifty50", start=str(START.date())),
        weekly_panel=dict(rows=int(len(panel)), tickers=int(panel["ticker"].nunique()),
                          content_sha256=phash),
        signals_total=int(len(sig)), signals_pit_member=int(len(memb)),
        signals_member_and_liquid=int(len(both)),
        span_years=round(span_yrs, 2), signals_per_year_member_liquid=round(rate, 1),
        per_year=per_year.to_dict(orient="records"),
        leg_attrition=attrition.to_dict(orient="records"),
        ext_at_entry=ext_stats,
        ext_bands=band_tbl.to_dict(orient="records"),
        median_ext_comparison_set=comparison,
    )
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    sig.to_csv(ROOT / "research" / "exports" / "g1_weinstein_signals.csv", index=False)

    md = [
        "# G1 Weinstein — GATE-1 census (entry count + ext-at-entry)",
        "",
        "**MEASUREMENT — 0 trials, 0 screens spent. No backtest, no capital, no config change,**",
        "**no forward-wall read. Standing counts unchanged: screens 12 · sealed opens 1 · n_trials 138.**",
        "",
        f"Weekly panel from `corrected_universe()`: {len(panel)} rows / "
        f"{panel['ticker'].nunique()} tickers, sha256 `{phash[:16]}…`. Window from {START.date()}.",
        "Spec + every ambiguity interpretation frozen in the module docstring; nothing swept.",
        "",
        "Reproduce: `python scripts/diag_g1_weinstein_gate1.py`",
        "",
        "## (a) Entry-count census",
        "",
        f"**{len(both)} signals** clearing the full spec on PIT members with ADV ≥ ₹5cr over "
        f"{span_yrs:.1f} years = **{rate:.1f} signals/year** "
        f"({both['ticker'].nunique()} distinct names).",
        "",
        md_table(per_year),
        "",
        "### Leg-by-leg attrition (which leg costs what)",
        "",
        md_table(attrition),
        "",
        "## (b) Ext-at-entry vs the slow weekly line",
        "",
        f"Median ext vs the 44w SMA at the modelled breakout close: "
        f"**{ext_stats['median_ext_vs_44w']}%** (mean {ext_stats['mean_ext_vs_44w']}%); "
        f"share below 5%: **{ext_stats['share_below_5pct']}%**. "
        f"Median ext vs Weinstein's own 30w line: {ext_stats['median_ext_vs_30w']}%. "
        f"Median modelled stop distance (entry → base low): {ext_stats['median_stop_pct']}%; "
        f"median base range {ext_stats['median_base_range_pct']}%.",
        "",
        md_table(band_tbl),
        "",
        "### Comparison set (median ext vs the 44w SMA, from `ext_band_census.md`)",
        "",
        md_table(pd.DataFrame([dict(funnel=k, median_ext_pct=v) for k, v in comparison.items()])),
        "",
        f"Signal ledger: `research/exports/g1_weinstein_signals.csv` ({len(sig)} rows, all legs passed).",
        "",
    ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    _echo("\n".join(md))


if __name__ == "__main__":
    main()
