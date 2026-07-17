"""Export a randomised trade list + a rules spec sheet (PDF) for manual TradingView review.

v3 (2026-07-16), owner request: "30 trades for loose and 30 stop trades and 20 good trades and all at
random, and a pdf for rules".

Source = the LIVE BOOK OF RECORD: base 0094 signal + P2 exit, all-grades, Rs10L, 2% risk (Sharpe 1.03 /
168 trades). Not the 4,391-trade substrate — the point is to audit what we would actually trade.

Split-cleaned: trades spanning an unadjusted split are DROPPED (the v1 list was topped by CGCL -17.32R,
which was a 1:4 split, not a loss). See DATA_BUG_unadjusted_splits.md.

Buckets are RANDOM samples (not cherry-picked extremes) so the owner sees the typical case:
  LOSS_RANDOM     30  R < 0
  STOPPED_RANDOM  30  exited via the stop
  GOOD_RANDOM     20  R >= 2
Buckets may overlap (most stops are losses); the overlap is reported.

    python scripts/export_tv_review2.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
from nq.data.membership import load_membership
from nq.data.ohlcv import load_demerger_reference
from run_bhanushali_faithful import EQ0
from run_bhanushali_path1 import corrected_universe
from diag_sleeves import P2_EXIT
from spec_sheet_pdf import build_pdf

OUT = ROOT / "research" / "substrate" / "tv_review"; OUT.mkdir(parents=True, exist_ok=True)
SEED = 20260716

# Which book to export. The spec sheet is RENDERED FROM THIS — a sheet that misdescribes the book is
# worse than no sheet, so every rule the PDF states lives here next to the kwargs that produce it.
BOOKS = {
    "base": dict(
        kw=dict(), label="BASE — live book of record (weekly-swing-0094-rank-p2exit)",
        poscap="<b>None.</b> Size is whatever 2% risk implies (median ~14% of equity per name)",
        ext_rule=None,
        stop_rule="The <b>signal week's LOW</b>. Fixed for the life of the trade (it never moves down; "
                  "see the trail in §5).",
        r_note="1R = entry − stop. Median across the book is <b>14.2% of the entry price</b>.",
        consequence="Notional per name = 2% ÷ R%. At the median R of 14.2%, one name is ~14% of the "
                    "book, so ~7 names fit."),
    "spec": dict(
        kw=dict(ext_cap=0.20, max_risk_pct=0.10, max_notional_pct=0.20),
        label="SPEC — owner discipline config (ext cap 20% + R cap 10% + position cap 20%)",
        poscap="<b>20% of sizing equity per name</b> (max_notional_pct). Load-bearing: capping R forces "
               "notional up to 2%÷R%, so without this cap the book would concentrate further.",
        ext_rule="<b>Extension cap — skip the trade entirely if the fill price is more than 20% above "
                 "the signal-week 44w SMA.</b> A pure selection rule: the stop is untouched. This is the "
                 "rule-faithful half of the config.",
        stop_rule="<b>max(signal-week LOW, entry × 0.90)</b> — R is capped at 10%. NOTE: when the candle "
                  "low is further than 10% away, the stop is <b>lifted off the candle</b> to an arbitrary "
                  "−10% line. This deviates from the taught rule (stop = the week's low) by design, per "
                  "the owner's instruction that R above 10% is distorted.",
        r_note="1R = entry − stop, capped at 10%. Median across the book is <b>9.2% of the entry "
               "price</b> (was 14.2% uncapped).",
        consequence="Notional per name = 2% ÷ R%. At R = 9.2% one name wants ~22% of the book, so only "
                    "~4-5 names fit (the base fits ~7). <b>This concentration is the real cost of the "
                    "R cap</b> — returns were unchanged."),
}
COLS = ["bucket", "tv_symbol", "signal_week", "sig_ctl_pct", "sig_body_frac", "sig_range_pct",
        "entry_date", "entry", "stop", "risk_pct", "ext_vs_sma", "crs_rank",
        "exit_date", "exit_px", "pct_move", "R", "mfe_pct", "mae_pct", "reason", "weeks_held"]


def find_splits(ohlcv, dem):
    """(ticker -> [dates]) of <-45% single-session moves that neither revert nor are known demergers."""
    out = {}
    for t, df in ohlcv.items():
        c = df["Close"]; r = c.pct_change()
        for d, v in r[r < -0.45].items():
            fwd = c.loc[d:].iloc[:6]
            if (fwd.max() / c.loc[d] - 1) > 0.8:
                continue                                     # reverts => bad tick, not a split
            if t in dem and str(pd.Timestamp(d).date()) in dem.get(t, set()):
                continue                                     # genuine demerger — legitimately left
            out.setdefault(t, []).append(pd.Timestamp(d))
    return out


def weekly_meta(P):
    """(ticker, FILL date) -> signal-week date + that candle's geometry + the SMA.

    Keyed on EVERY day of each entry window, not just its first day. The fill is the first daily OPEN
    that prints inside the band, which is frequently Tue/Wed/Thu — keying on the window's Monday alone
    silently dropped ~17% of trades from the review exports (971 -> 809) via the dropna that follows.
    """
    meta = {}
    for t, s in P.items():
        dates = pd.DatetimeIndex(s["dates"])
        c = np.asarray(s["c"], float); h = np.asarray(s["h"], float)
        l = np.asarray(s["l"], float); o = np.asarray(s["o"], float)
        iso = dates.isocalendar(); keys = list(zip(iso["year"].to_numpy(), iso["week"].to_numpy()))
        weeks, cur, prev = [], [], None
        for i, k in enumerate(keys):
            if prev is not None and k != prev:
                weeks.append(cur); cur = []
            cur.append(i); prev = k
        if cur:
            weeks.append(cur)
        wc = np.array([c[d[-1]] for d in weeks]); wh = np.array([h[d].max() for d in weeks])
        wl = np.array([l[d].min() for d in weeks]); wo = np.array([o[d[0]] for d in weeks])
        wsma = pd.Series(wc).rolling(44).mean().to_numpy()
        d2w = {i: wp for wp, d in enumerate(weeks) for i in d}
        for e0, win in s["entry_win"].items():
            k = d2w.get(e0, 0) - 1
            if k < 1:
                continue
            rng = wh[k] - wl[k]
            rec = dict(
                signal_week=dates[weeks[k][-1]],
                sig_ctl_pct=(wc[k] - wl[k]) / wc[k] * 100,
                sig_body_frac=((wc[k] - wo[k]) / rng) if rng > 0 else np.nan,
                sig_range_pct=rng / wl[k] * 100 if wl[k] > 0 else np.nan,
                sma=wsma[k])
            for _d in win[0]:                    # every day of the window — the fill may be any of them
                meta[(t, dates[_d])] = rec
    return meta


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "spec"
    book = BOOKS[which]
    ohlcv = corrected_universe(); mem = load_membership(); dem = load_demerger_reference()
    splits = find_splits(ohlcv, dem)
    P = R94.prep_weekly_rank(ohlcv)

    # R1 — the baseline assertion must hold before we trust any export built on this engine.
    base = R94.backtest(P, mem, start="2017-01-01", eq0=EQ0, **P2_EXIT)
    assert abs(base["sharpe"] - 1.0342) < 0.001 and base["trades"] == 168, "R1 baseline FAILED"

    led = []
    m = R94.backtest(P, mem, ledger=led, start="2017-01-01", eq0=EQ0, **book["kw"], **P2_EXIT)
    print(f"book = {which}: {book['label']}")
    print(f"  Sharpe {m['sharpe']:.4f} / {m['trades']} trades\n")

    t = pd.DataFrame(led)
    t["entry_date"] = pd.to_datetime(t.entry_date); t["exit_date"] = pd.to_datetime(t.exit_date)
    t = t.rename(columns={"tkr": "ticker", "stop0": "stop", "rank": "crs_rank"})

    n0 = len(t)
    t = t[~t.apply(lambda r: any(r.entry_date <= d <= r.exit_date for d in splits.get(r.ticker, [])),
                   axis=1)].copy()
    print(f"split-clean: {n0} -> {len(t)} ({n0-len(t)} dropped)")

    meta = weekly_meta(P)
    for k in ("signal_week", "sig_ctl_pct", "sig_body_frac", "sig_range_pct", "sma"):
        t[k] = [meta.get((r.ticker, r.entry_date), {}).get(k) for r in t.itertuples()]
    t = t.dropna(subset=["signal_week"])

    t["tv_symbol"] = "NSE:" + t.ticker
    t["risk_pct"] = (t.entry - t.stop) / t.entry * 100
    t["ext_vs_sma"] = (t.entry / t.sma - 1) * 100
    t["pct_move"] = (t.exit_px / t.entry - 1) * 100
    t["weeks_held"] = ((t.exit_date - t.entry_date).dt.days / 7).round(1)

    mfe, mae = [], []
    for r in t.itertuples():
        w = ohlcv[r.ticker].loc[r.entry_date:r.exit_date]
        mfe.append((w["High"].max() / r.entry - 1) * 100 if len(w) else np.nan)
        mae.append((w["Low"].min() / r.entry - 1) * 100 if len(w) else np.nan)
    t["mfe_pct"], t["mae_pct"] = mfe, mae

    rng = np.random.RandomState(SEED)
    def take(pool, n, lab):
        pool = pool.copy()
        if len(pool) > n:
            pool = pool.iloc[rng.choice(len(pool), n, replace=False)]
        return pool.assign(bucket=lab)

    # DISJOINT buckets (owner 2026-07-16: "AEGISLOG is written twice in loss random and stopped random").
    # Overlapping buckets waste review time — the same chart opens twice — and they hid a real bucket:
    # losers that did NOT stop out (they bled away via the trail/blow-off/time). Those are a different
    # failure and worth their own eyes. So: STOPPED = stopped out; LOSS = lost WITHOUT stopping.
    stop = t[t.reason.astype(str).str.startswith("stop")]
    loss = t[(t.R < 0) & (~t.index.isin(stop.index))]
    good = t[t.R >= 2]
    # MATCHED CONTROL — mandatory. A loser-only list is defined BY outcome, so every entry in it looks
    # bad and the reader infers the entry style is the cause (EXT_IS_THE_ENGINE.md: this is exactly how
    # the "we buy too high" false inference was manufactured). Ship winners that LOOK like the losers —
    # same extension profile — so entry style can be judged against a real control.
    # The threshold is DERIVED from the losers, never hardcoded: a fixed ">=20%" silently returns an
    # EMPTY control on any book that caps extension (e.g. the spec book's ext_cap=0.20), which would
    # quietly reintroduce the very bias this bucket exists to prevent.
    ext_thr = float(pd.concat([loss, stop]).ext_vs_sma.median())
    print(f"pools -> losses-that-did-NOT-stop {len(loss)} | stopped {len(stop)} | good R>=2 {len(good)}")
    b1 = take(loss, 30, "LOSS_NO_STOP"); b2 = take(stop, 30, "STOPPED_RANDOM")
    b3 = take(good, 20, "GOOD_RANDOM")
    # The matched control is drawn from winners NOT already sampled above, at or beyond the LOSERS' own
    # median extension — a threshold derived from the data, never hardcoded (a fixed ">=20%" silently
    # empties on any book that caps extension, reintroducing the loser-only bias this bucket prevents).
    hi_ext = good[(good.ext_vs_sma >= ext_thr) & (~good.index.isin(b3.index))]
    print(f"matched control: winners at >= the losers' median ext ({ext_thr:.1f}%), not already sampled: {len(hi_ext)}")
    assert len(hi_ext) >= 5, f"matched control too thin ({len(hi_ext)}) — do NOT ship a loser-only list"
    b4 = take(hi_ext, 15, "WINNER_MATCHED")
    allb = pd.concat([b1, b2, b3, b4])
    assert not allb.index.duplicated().any(), "buckets must be DISJOINT — no chart reviewed twice"

    allx = allb
    for c in ("signal_week", "entry_date", "exit_date"):
        allx[c] = pd.to_datetime(allx[c]).dt.strftime("%Y-%m-%d")
    allx = allx[COLS].round(2)
    allx.to_csv(OUT / f"tv_review_{which}.csv", index=False)
    print(f"\nwrote {OUT / f'tv_review_{which}.csv'}  ({len(allx)} rows)")

    print("\n=== bucket profiles ===")
    for b, g in allx.groupby("bucket", sort=False):
        print(f"  {b:16s} n={len(g):2d}  mean %move={g.pct_move.mean():+6.1f}%  meanR={g.R.mean():+5.2f}  "
              f"mean risk%={g.risk_pct.mean():4.1f}  mean ext={g.ext_vs_sma.mean():+5.1f}%  "
              f"mean MFE={g.mfe_pct.mean():+5.1f}%")

    pdf = build_pdf(OUT / f"RULES_SPEC_{which}.pdf", m, len(t), allx, book, ext_thr)
    print(f"wrote {pdf}")


if __name__ == "__main__":
    main()
