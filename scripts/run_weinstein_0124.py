"""0124 — Weinstein stage analysis as a WHOLE SYSTEM. Phase-2 shadow backtest.

MEASUREMENT class (the 0022/0023/0024 Bhanushali precedent). **No `n_trials` increment, no screen
row, no config change, no forward-wall read.** Standing counts unchanged: screens 12 · sealed
opens 1 · n_trials 138.

Pre-registration: `diagnostics/research/preregistry/0124-weinstein-stage-analysis.md` — the spec,
every ambiguity resolution, the pre-committed bars and the three guards are frozen there and are
NOT restated as tunables here. The entry detector is IMPORTED from the Gate-1 script so the spec
that was censused is byte-identically the spec that is traded.

Two views, in the pre-registered order (diagnostic-first law):
  1. PER-TRADE, UNCAPPED — every signal fills; R is capital-independent.
  2. CAPPED Rs 10L BOOK — cash-gated, 2% risk/fill, RS-strongest-first, marked DAILY so the return
     series is directly comparable to the incumbent sleeves; sub-periods are a CONTINUOUS SLICE of
     the single full run, never a fresh-capital re-run.
Then: correlation to the incumbent swing x lowvol pair, the 3-sleeve ERC blend, and the R anatomy.

Reproduce:
    python scripts/run_weinstein_0124.py
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

import config as CFG  # noqa: E402
from nq.data.membership import load_membership, ticker_in_index_on  # noqa: E402
from nq.data.weekly import build_weekly_panel, _panel_hash  # noqa: E402
from nq.validation.bootstrap import block_bootstrap_metric  # noqa: E402
from nq.validation.metrics import max_drawdown, sharpe  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from diag_g1_weinstein_gate1 import (  # noqa: E402  — the SAME frozen spec Gate-1 censused
    ADV_MIN, INDEX_CSV, MA_TURN_LOOKBACK, RS_SMA_LEN, SMA_LEN, START, adv20_by_week, detect,
)

EQ0 = 10_00_000.0          # Rs 10L, the house book size
RISK = 0.02                # 2% of equity risked per fill
STAGE3_LOOKBACK = 4        # weeks — "close below the prior 4-week low" == the stage-3 warning
TRADING_DAYS = 252

OUT_JSON = ROOT / "diagnostics" / "research" / "weinstein_0124.json"
OUT_MD = ROOT / "research" / "findings" / "0124-weinstein-stage-analysis.md"
LEDGER = ROOT / "research" / "exports" / "weinstein_0124_trades.csv"
SLEEVES = ROOT / "research" / "exports" / "third_sleeve_returns.csv"


def leg_cost(adv: float, notional: float) -> float:
    """Per-leg cost FRACTION: brokerage + STT + ADV-tiered slippage + sqrt impact above 0.5% ADV."""
    base = CFG.BROKERAGE_PCT + CFG.STT_PCT
    a = adv if np.isfinite(adv) and adv > 0 else 0.0
    tier = ("LARGE_CAP" if a >= CFG.ADV_LARGE_CAP_RS
            else "MID_CAP" if a >= CFG.ADV_MID_CAP_RS else "SMALL_CAP")
    slip = CFG.SLIPPAGE[tier]
    impact = 0.0
    if a > 0 and notional > 0.005 * a:
        impact = CFG.IMPACT_ETA * 0.02 * np.sqrt(notional / a)
    return float(base + slip + impact)


# ------------------------------------------------------------------ the grammar's own management
def walk_trade(k, c, o, h, l, sma30, stop0):
    """Weinstein position management from signal week ``k``. Returns exit legs as (idx, px, frac,
    reason, gap) — a half at the first stage-3 warning, the rest at stage-4 / stop / data end."""
    n = len(c)
    stop = stop0
    half_done = False
    legs = []
    remaining = 1.0
    for j in range(k + 1, n):
        # 1. stop first (intra-week). A week opening below the stop fills at the open, not the stop.
        if l[j] <= stop:
            px, gap = (o[j], True) if o[j] < stop else (stop, False)
            legs.append((j, px, remaining, "stop", gap))
            return legs
        # 2. stage-4 confirmation -> out
        if (np.isfinite(sma30[j]) and c[j] < sma30[j]
                and j >= MA_TURN_LOOKBACK and sma30[j] <= sma30[j - MA_TURN_LOOKBACK]):
            legs.append((j, c[j], remaining, "stage4", False))
            return legs
        # 3. stage-3 warning -> sell half into strength, once
        if (not half_done and j - STAGE3_LOOKBACK >= 0
                and np.isfinite(sma30[j]) and c[j] > sma30[j]
                and c[j] < np.nanmin(l[j - STAGE3_LOOKBACK:j])):
            legs.append((j, c[j], 0.5, "stage3_half", False))
            half_done = True
            remaining = 0.5
        # 4. ratchet the stop to each confirmed higher swing low (3-bar pivot)
        if j - 2 >= k and l[j - 1] < l[j - 2] and l[j - 1] < l[j] and l[j - 1] > stop:
            stop = l[j - 1]
    legs.append((n - 1, c[n - 1], remaining, "data_end", False))
    return legs


def build_trades(panel, sig, advmap, idx_ok):
    """Uncapped per-trade simulation: every signal fills at its week close, net of real costs."""
    byname = {t: g.sort_values("week_end", kind="mergesort").reset_index(drop=True)
              for t, g in panel.groupby("ticker", sort=False)}
    rows = []
    for _, s in sig.iterrows():
        g = byname[s["ticker"]]
        we = g["week_end"].to_numpy()
        k = int(np.searchsorted(we, np.datetime64(s["week_end"])))
        if k >= len(we) or pd.Timestamp(we[k]) != s["week_end"]:
            continue
        if not idx_ok.get(pd.Timestamp(we[k]), False):      # the M-rule gates NEW entries
            continue
        c, o, h, l = (g[x].to_numpy(float) for x in ("c", "o", "h", "l"))
        sma30 = pd.Series(c).rolling(SMA_LEN).mean().to_numpy()
        entry, stop0 = float(c[k]), float(s["base_lo"])
        if not (entry > stop0 > 0):
            continue
        adv = advmap.get((s["ticker"], pd.Timestamp(we[k])), np.nan)
        legs = walk_trade(k, c, o, h, l, sma30, stop0)

        cost_in = leg_cost(adv, 0.0)
        gross = sum(frac * px for _, px, frac, _, _ in legs)
        costs = entry * cost_in + sum(frac * px * leg_cost(adv, 0.0) for _, px, frac, _, _ in legs)
        r_net = (gross - entry - costs) / (entry - stop0)
        j_last = legs[-1][0]
        rows.append(dict(
            ticker=s["ticker"], entry_week=s["week_end"], exit_week=pd.Timestamp(we[j_last]),
            entry=round(entry, 2), stop0=round(stop0, 2),
            risk_pct=round(100.0 * (1 - stop0 / entry), 2),
            R=round(float(r_net), 3), held_weeks=int(j_last - k),
            reason=legs[-1][3], gap_through=bool(any(x[4] for x in legs)),
            half_booked=bool(any(x[3] == "stage3_half" for x in legs)),
            ext_vs_44w_pct=s["ext_vs_44w_pct"], mansfield=s["mansfield"], adv20=adv,
            year=int(pd.Timestamp(s["week_end"]).year),
            legs=";".join(f"{x[3]}@{x[1]:.2f}x{x[2]:.2f}" for x in legs),
        ))
    return pd.DataFrame(rows)


def run_capped(panel, sig, advmap, idx_ok, daily_close, all_days):
    """The Rs 10L cash-gated book, marked DAILY. Returns (equity series, fills, cash_skips)."""
    byname = {t: g.sort_values("week_end", kind="mergesort").reset_index(drop=True)
              for t, g in panel.groupby("ticker", sort=False)}
    arrs = {}
    for t, g in byname.items():
        c = g["c"].to_numpy(float)
        arrs[t] = dict(we=g["week_end"].to_numpy(), c=c, o=g["o"].to_numpy(float),
                       h=g["h"].to_numpy(float), l=g["l"].to_numpy(float),
                       sma30=pd.Series(c).rolling(SMA_LEN).mean().to_numpy())

    plan = {}                                   # (ticker, entry_week) -> exit legs, precomputed
    sig = sig.sort_values(["week_end", "mansfield"], ascending=[True, False], kind="mergesort")
    for _, s in sig.iterrows():
        a = arrs[s["ticker"]]
        k = int(np.searchsorted(a["we"], np.datetime64(s["week_end"])))
        if k >= len(a["we"]) or pd.Timestamp(a["we"][k]) != s["week_end"]:
            continue
        plan[(s["ticker"], s["week_end"])] = (k, walk_trade(k, a["c"], a["o"], a["h"], a["l"],
                                                            a["sma30"], float(s["base_lo"])))

    weeks = sorted(set(sig["week_end"]) | {pd.Timestamp(d) for a in arrs.values() for d in a["we"]})
    sig_by_week = {w: g for w, g in sig.groupby("week_end", sort=False)}

    cash, open_pos, fills, skips = EQ0, {}, [], 0
    exits_on = {}                               # week_end -> list of (ticker, px, frac, reason)
    equity_days, eq_vals = [], []

    day_ptr = 0
    for w in weeks:
        # ---- exits scheduled for this week
        for tkr, px, frac, reason in exits_on.pop(w, []):
            p = open_pos.get(tkr)
            if p is None:
                continue
            # full exit takes the whole remaining line; a partial takes its share of what is left
            sh = (p["shares"] if frac >= p["frac_left"] - 1e-9
                  else p["shares"] * (frac / p["frac_left"]))
            cash += sh * px * (1 - leg_cost(p["adv"], sh * px))
            p["shares"] -= sh
            p["frac_left"] -= frac
            if p["frac_left"] <= 1e-9 or p["shares"] <= 1e-9:
                open_pos.pop(tkr, None)

        # ---- mark equity on every trading day up to and including this week_end
        while day_ptr < len(all_days) and all_days[day_ptr] <= w:
            d = all_days[day_ptr]
            mv = 0.0
            for tkr, p in open_pos.items():
                px = daily_close.get((tkr, d))
                mv += p["shares"] * (px if px is not None and np.isfinite(px) else p["last"])
                if px is not None and np.isfinite(px):
                    p["last"] = px
            equity_days.append(d); eq_vals.append(cash + mv)
            day_ptr += 1

        # ---- new entries (M-rule gated, RS-strongest-first, cash-gated)
        if not idx_ok.get(w, False):
            continue
        for _, s in sig_by_week.get(w, pd.DataFrame()).iterrows():
            key = (s["ticker"], s["week_end"])
            if key not in plan or s["ticker"] in open_pos:
                continue
            k, legs = plan[key]
            a = arrs[s["ticker"]]
            entry, stop0 = float(a["c"][k]), float(s["base_lo"])
            if not (entry > stop0 > 0):
                continue
            eq_now = eq_vals[-1] if eq_vals else EQ0
            shares = (RISK * eq_now) / (entry - stop0)
            adv = advmap.get(key, np.nan)
            notional = shares * entry
            need = notional * (1 + leg_cost(adv, notional))
            if need > cash or shares <= 0:
                skips += 1
                continue
            cash -= need
            open_pos[s["ticker"]] = dict(shares=shares, adv=adv, last=entry, frac_left=1.0)
            fills.append(dict(ticker=s["ticker"], week=w, entry=entry, stop0=stop0,
                              shares=shares, notional=notional))
            for j, px, frac, reason, _ in legs:
                exits_on.setdefault(pd.Timestamp(a["we"][j]), []).append(
                    (s["ticker"], float(px), float(frac), reason))
    eq = pd.Series(eq_vals, index=pd.DatetimeIndex(equity_days)).sort_index()
    return eq[~eq.index.duplicated(keep="last")], pd.DataFrame(fills), skips


def perf(ret: pd.Series, eq: pd.Series) -> dict:
    r = ret.to_numpy(float)
    years = max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9)
    return dict(
        Sharpe=round(float(sharpe(r, periods=TRADING_DAYS)), 3),
        CAGR_pct=round(100.0 * ((eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1), 2),
        MaxDD_pct=round(100.0 * float(max_drawdown(eq.to_numpy(float))), 2),
        ann_vol_pct=round(100.0 * float(r.std() * np.sqrt(TRADING_DAYS)), 2),
    )


def slice_perf(ret: pd.Series, eq: pd.Series, lo: str, hi: str) -> dict:
    """CONTINUOUS SLICE of the single full run — never a fresh-capital re-run (the phantom-gate law)."""
    m = (ret.index >= lo) & (ret.index <= hi)
    if m.sum() < 30:
        return dict(Sharpe=None, CAGR_pct=None, MaxDD_pct=None, ann_vol_pct=None, n_days=int(m.sum()))
    r = ret[m]
    e = eq.loc[(eq.index >= r.index[0]) & (eq.index <= r.index[-1])]
    out = perf(r, e)
    out["n_days"] = int(m.sum())
    return out


def rtable(t: pd.DataFrame) -> dict:
    r = t["R"].to_numpy(float)
    g, ls = r[r > 0].sum(), -r[r < 0].sum()
    return dict(N=int(len(r)), win_pct=round(100.0 * float((r > 0).mean()), 1),
                meanR=round(float(r.mean()), 3), medR=round(float(np.median(r)), 3),
                PF=round(float(g / ls), 2) if ls > 0 else None,
                median_risk_pct=round(float(t["risk_pct"].median()), 2),
                stopout_pct=round(100.0 * float((t["reason"] == "stop").mean()), 1),
                median_held_weeks=int(t["held_weeks"].median()))


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in df.iterrows():
        out.append("| " + " | ".join(
            "—" if row[c] is None or (isinstance(row[c], float) and np.isnan(row[c])) else str(row[c])
            for c in cols) + " |")
    return "\n".join(out)


def erc_blend(w: pd.DataFrame, cols: list[str]) -> pd.Series:
    """Quarterly inverse-vol ERC on weekly returns — the 0115 blend mechanism."""
    q = w.index.to_period("Q")
    weights = pd.DataFrame(index=w.index, columns=cols, dtype=float)
    for i, per in enumerate(sorted(q.unique())):
        m = q == per
        prior = w[q < per]
        if len(prior) < 13:
            weights.loc[m, cols] = 1.0 / len(cols)
            continue
        vol = prior[cols].tail(52).std().replace(0, np.nan)
        iv = (1.0 / vol).fillna(0.0)
        weights.loc[m, cols] = (iv / iv.sum()).to_numpy()
    return (w[cols] * weights).sum(axis=1)


def main() -> None:
    ohlcv = corrected_universe()
    panel = build_weekly_panel(ohlcv)
    phash = _panel_hash(panel)
    idx = (pd.read_csv(INDEX_CSV, parse_dates=["date"]).set_index("date")["nifty50_close"]
           .sort_index())

    sig, _ = detect(panel, idx)
    mem = load_membership() or {}
    advmap = adv20_by_week(ohlcv, panel)
    sig["adv20"] = [advmap.get((t, d), np.nan) for t, d in zip(sig["ticker"], sig["week_end"])]
    sig = sig[[ticker_in_index_on(t, d.date(), mem)
               for t, d in zip(sig["ticker"], sig["week_end"])]]
    sig = sig[sig["adv20"] >= ADV_MIN].reset_index(drop=True)

    # ---- the M-rule: Nifty-50 weekly close vs its own 30-week SMA
    iw = idx.resample("W-FRI").last().dropna()
    isma = iw.rolling(SMA_LEN).mean()
    ok_by_week = (iw > isma)
    weeks_all = sorted({pd.Timestamp(d) for d in panel["week_end"].unique()})
    ok_re = ok_by_week.reindex(pd.DatetimeIndex(weeks_all), method="ffill").fillna(False)
    idx_ok = {pd.Timestamp(d): bool(v) for d, v in ok_re.items()}

    # ---- view 1: per-trade uncapped
    tr = build_trades(panel, sig, advmap, idx_ok)
    tr.to_csv(LEDGER, index=False)

    per_year = pd.DataFrame([dict(year=int(y), **{k: v for k, v in rtable(g).items()
                                                  if k in ("N", "win_pct", "meanR", "medR", "PF")})
                             for y, g in tr.groupby("year")])

    # ---- view 2: capped book
    daily_close, all_days = {}, set()
    for t, df in ohlcv.items():
        s = df["Close"]
        for d, v in s.items():
            dd = pd.Timestamp(d)
            if dd >= START:
                daily_close[(t, dd)] = float(v)
                all_days.add(dd)
    all_days = sorted(all_days)

    eq, fills, skips = run_capped(panel, sig, advmap, idx_ok, daily_close, all_days)
    ret = eq.pct_change().dropna()
    full = perf(ret, eq)
    boot = block_bootstrap_metric(ret.to_numpy(float),
                                  lambda x: sharpe(x, periods=TRADING_DAYS))
    slices = {lab: slice_perf(ret, eq, lo, hi) for lab, lo, hi in
              [("2017-21", "2017-01-01", "2021-12-31"), ("2022-26", "2022-01-01", "2026-12-31")]}
    yearly = {}
    for y, g in ret.groupby(ret.index.year):
        yearly[int(y)] = round(100.0 * float((1 + g).prod() - 1), 2)

    # ---- correlation + ERC vs the incumbent pair (weekly, both sides recomputed the same way)
    sl = pd.read_csv(SLEEVES, index_col=0, parse_dates=True)
    wk = pd.DataFrame({
        "weinstein": (1 + ret).resample("W-FRI").prod() - 1,
        "swing": (1 + sl["swing"]).resample("W-FRI").prod() - 1,
        "lowvol": (1 + sl["lowvol"]).resample("W-FRI").prod() - 1,
    }).dropna()
    corr = wk.corr().round(3)
    pair = erc_blend(wk, ["swing", "lowvol"])
    trio = erc_blend(wk, ["swing", "lowvol", "weinstein"])

    def wperf(r: pd.Series) -> dict:
        e = (1 + r).cumprod()
        yr = {int(y): round(100.0 * float((1 + g).prod() - 1), 2) for y, g in r.groupby(r.index.year)}
        return dict(Sharpe=round(float(sharpe(r.to_numpy(float), periods=52)), 3),
                    MaxDD_pct=round(100.0 * float(max_drawdown(e.to_numpy(float))), 2),
                    worst_year_pct=min(yr.values()), losing_years=sum(1 for v in yr.values() if v < 0))

    blend = dict(swing_lowvol=wperf(pair), plus_weinstein=wperf(trio),
                 weinstein_standalone_weekly=wperf(wk["weinstein"]))

    # ---- R anatomy: matched cells (ext band x risk-width tercile), never a one-sided list
    tr["ext_band"] = pd.cut(tr["ext_vs_44w_pct"], [-np.inf, 10, 15, 20, np.inf],
                            labels=["<10%", "10-15%", "15-20%", ">20%"])
    tr["risk_tercile"] = pd.qcut(tr["risk_pct"], 3, labels=["tight", "mid", "wide"])
    anatomy = (tr.groupby(["ext_band", "risk_tercile"], observed=True)
               .agg(N=("R", "size"), meanR=("R", "mean"), win_pct=("R", lambda x: 100 * (x > 0).mean()))
               .round(3).reset_index())
    top_share = (tr.nlargest(max(int(0.1 * len(tr)), 1), "R")["R"].sum()
                 / tr["R"].sum() if tr["R"].sum() != 0 else np.nan)

    payload = dict(
        _doc="0124 Weinstein whole-system shadow backtest (MEASUREMENT; 0 trials, 0 screens).",
        prereg="diagnostics/research/preregistry/0124-weinstein-stage-analysis.md",
        weekly_panel=dict(rows=int(len(panel)), tickers=int(panel["ticker"].nunique()),
                          content_sha256=phash),
        signals_member_liquid=int(len(sig)), trades_uncapped=int(len(tr)),
        per_trade=rtable(tr), per_trade_by_year=per_year.to_dict(orient="records"),
        capped=dict(**full, trades=int(len(fills)), cash_skips=int(skips),
                    Calmar=round(full["CAGR_pct"] / abs(full["MaxDD_pct"]), 2) if full["MaxDD_pct"] else None,
                    boot_ci=[round(float(boot.lower), 3), round(float(boot.upper), 3)],
                    slices=slices, yearly_pct=yearly),
        correlation_weekly=corr.to_dict(),
        erc_blend=blend,
        anatomy=anatomy.to_dict(orient="records"),
        top_decile_share_of_R=round(float(top_share), 3),
    )
    OUT_JSON.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
