"""Ext-band census — where do our funnels' fills actually land against the SLOW weekly line?

MEASUREMENT ONLY. Spends no trial and no screen; reads no forward-wall log; changes no config.

Two questions, both settled from committed ledgers (reproduce-before-trust):

  PART A — the daily-vs-weekly band question.
    The six-step funnel (findings 0026/0084, 0027/0085) anchors its pullback and its trigger on the
    DAILY 44-SMA. E11's "deep near-SMA" edge (meanR +1.004 at ext < 5%) is measured against the
    WEEKLY 44-week SMA. A name can sit on its daily line while far above its weekly line, so the
    claim "a daily-44-SMA-anchored entry lands in the E11 band" is an assumption, not a fact.
    This part tabulates ext-vs-weekly-44w-SMA at fill for every 0084 / 0085 trade and bands it.

  PART B — the E11 20-25% number, cross-checked from the ledger side.
    E11 reported (ad hoc) that the box / S-R entries concentrate their edge at 20-25% ext. The
    committed Stage-1 substrate already carries a per-trade ``ext_vs_sma``; this part re-derives
    the per-setup band profile from that artifact so the census's pre-/post-extension axis rests
    on a committed number rather than a chat transcript.

PIT discipline: the weekly SMA joined to a fill is the SMA of the last COMPLETED week strictly
before the entry date (``merge_asof`` backward, ``allow_exact_matches=False``) — the current week
is not closed at fill time and may not be read.

Reproduce:
    python scripts/diag_ext_band_census.py
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

from nq.data.weekly import build_weekly_panel, _panel_hash  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

OUT_JSON = ROOT / "diagnostics" / "research" / "ext_band_census.json"
OUT_MD = ROOT / "diagnostics" / "research" / "ext_band_census.md"

# E11's own bands, kept verbatim so the two studies are comparable. The <0 band is NEW and
# necessary: a daily-44-SMA reclaim can fill BELOW the weekly line, which E11 never had to model.
BAND_EDGES = [-np.inf, 0.0, 5.0, 10.0, 15.0, 20.0, 25.0, np.inf]
BAND_NAMES = ["<0 (below wk line)", "0-5%", "5-10%", "10-15%", "15-20%", "20-25%", ">25%"]

LEDGERS = {
    "0084 six-step (target-capped exits)": "bhanushali_sixstep_0084_trades.csv",
    "0085 six-step (runner trail)": "bhanushali_sixstep_runner_0085_trades.csv",
}


def _echo(text: str) -> None:
    """Print without dying on a cp1252 console — the artifact on disk is always UTF-8."""
    enc = sys.stdout.encoding or "utf-8"
    sys.stdout.write(text.encode(enc, errors="replace").decode(enc, errors="replace") + "\n")


def band(series_pct: pd.Series) -> pd.Series:
    return pd.cut(series_pct, bins=BAND_EDGES, labels=BAND_NAMES, right=False)


def profile(df: pd.DataFrame, rcol: str = "R") -> dict:
    """N / win% / meanR / medR / profit-factor for one cohort."""
    r = df[rcol].to_numpy(float)
    r = r[~np.isnan(r)]
    if r.size == 0:
        return dict(N=0, win_pct=np.nan, meanR=np.nan, medR=np.nan, PF=np.nan)
    gains, losses = r[r > 0].sum(), -r[r < 0].sum()
    return dict(
        N=int(r.size),
        win_pct=round(100.0 * float((r > 0).mean()), 1),
        meanR=round(float(r.mean()), 3),
        medR=round(float(np.median(r)), 3),
        PF=round(float(gains / losses), 2) if losses > 0 else np.inf,
    )


def band_table(df: pd.DataFrame, bandcol: str = "band", rcol: str = "R") -> pd.DataFrame:
    rows = []
    for b in BAND_NAMES:
        sub = df[df[bandcol] == b]
        rows.append(dict(band=b, share_pct=round(100.0 * len(sub) / max(len(df), 1), 1),
                         **profile(sub, rcol)))
    tot = profile(df, rcol)
    rows.append(dict(band="ALL", share_pct=100.0, **tot))
    return pd.DataFrame(rows)


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in df.iterrows():
        cells = []
        for c in cols:
            v = row[c]
            cells.append("—" if (isinstance(v, float) and np.isnan(v)) else str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


# --------------------------------------------------------------------------- PART A
def part_a(panel: pd.DataFrame) -> tuple[dict, list[str]]:
    wk = panel[["ticker", "week_end", "sma44"]].dropna(subset=["sma44"]).copy()
    wk = wk.sort_values("week_end", kind="mergesort")

    results, md = {}, []
    for label, fname in LEDGERS.items():
        path = ROOT / "research" / "exports" / fname
        led = pd.read_csv(path, parse_dates=["entry_date"])
        if "ticker" not in led.columns:          # the six-step ledgers name the column `tkr`
            led = led.rename(columns={"tkr": "ticker"})
        led = led.sort_values("entry_date", kind="mergesort")

        # PIT join: last COMPLETED week strictly before the fill.
        joined = pd.merge_asof(
            led, wk, left_on="entry_date", right_on="week_end", by="ticker",
            direction="backward", allow_exact_matches=False,
        )
        joined["ext_wk_pct"] = 100.0 * (joined["entry"] / joined["sma44"] - 1.0)
        unmatched = int(joined["sma44"].isna().sum())
        j = joined.dropna(subset=["ext_wk_pct"]).copy()
        j["band"] = band(j["ext_wk_pct"])

        tbl = band_table(j)
        results[label] = dict(
            ledger=fname, trades_in_ledger=int(len(led)), joined=int(len(j)),
            unmatched_no_weekly_sma=unmatched,
            ext_wk_pct_median=round(float(j["ext_wk_pct"].median()), 2),
            ext_wk_pct_mean=round(float(j["ext_wk_pct"].mean()), 2),
            share_below_5pct=round(100.0 * float((j["ext_wk_pct"] < 5.0).mean()), 1),
            bands=tbl.to_dict(orient="records"),
        )
        md += [f"\n### {label}",
               f"\n`{fname}` — {len(led)} trades, {len(j)} joined to a completed weekly SMA "
               f"({unmatched} unmatched). Median ext-vs-weekly-44w-SMA at fill: "
               f"**{results[label]['ext_wk_pct_median']}%**; share below 5%: "
               f"**{results[label]['share_below_5pct']}%**.\n",
               md_table(tbl)]
    return results, md


# --------------------------------------------------------------------------- PART B
def part_b() -> tuple[dict, list[str]]:
    sub = pd.read_parquet(ROOT / "research" / "substrate" / "trades.parquet")
    sub = sub.copy()
    sub["band"] = band(sub["ext_vs_sma"])

    results, md = {}, []
    md.append(f"\nSubstrate: `research/substrate/trades.parquet` — {len(sub)} uncapped trades, "
              f"{sub['setup'].nunique()} setups. `ext_vs_sma` is the committed per-trade column "
              "(percent, vs the weekly 44w SMA).\n")

    order = (sub.groupby("setup").size().sort_values(ascending=False).index.tolist())
    for setup in order:
        s = sub[sub["setup"] == setup]
        tbl = band_table(s)
        results[setup] = dict(
            N=int(len(s)),
            ext_median=round(float(s["ext_vs_sma"].median()), 2),
            share_below_5pct=round(100.0 * float((s["ext_vs_sma"] < 5.0).mean()), 1),
            share_20_to_25=round(100.0 * float(s["ext_vs_sma"].between(20.0, 25.0).mean()), 1),
            bands=tbl.to_dict(orient="records"),
        )
        md += [f"\n### {setup} (N={len(s)}, median ext {results[setup]['ext_median']}%)\n",
               md_table(tbl)]
    return results, md


def main() -> None:
    ohlcv = corrected_universe()
    panel = build_weekly_panel(ohlcv)
    phash = _panel_hash(panel)

    a_res, a_md = part_a(panel)
    b_res, b_md = part_b()

    payload = dict(
        _doc="Ext-band census (MEASUREMENT; 0 trials, 0 screens). Part A = ext-vs-weekly-44w-SMA "
             "at fill for the daily-anchored six-step ledgers. Part B = the same banding on the "
             "committed Stage-1 substrate, per setup.",
        weekly_panel=dict(rows=int(len(panel)), tickers=int(panel["ticker"].nunique()),
                          content_sha256=phash, built_from="corrected_universe()"),
        band_edges_pct=[None if np.isinf(x) else x for x in BAND_EDGES],
        part_a_sixstep_ledgers=a_res,
        part_b_substrate_by_setup=b_res,
    )
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    head = [
        "# Ext-band census — where our fills land against the slow weekly line",
        "",
        "**MEASUREMENT — 0 trials, 0 screens spent. No config change. No forward-wall read.**",
        "Standing counts unchanged: **screens 12 · sealed opens 1 · n_trials 138.**",
        "",
        f"Weekly panel built from `corrected_universe()`: {len(panel)} rows / "
        f"{panel['ticker'].nunique()} tickers, content sha256 `{phash[:16]}…`.",
        "PIT join: the SMA of the last **completed** week strictly before the fill "
        "(`merge_asof` backward, `allow_exact_matches=False`).",
        "",
        "Reproduce: `python scripts/diag_ext_band_census.py`",
        "",
        "## Part A — the daily-vs-weekly band question (six-step ledgers)",
    ]
    body = head + a_md + ["", "## Part B — E11's per-setup band profile, from the committed substrate"] + b_md + [""]
    OUT_MD.write_text("\n".join(body), encoding="utf-8")

    _echo("\n".join(body))


if __name__ == "__main__":
    main()
