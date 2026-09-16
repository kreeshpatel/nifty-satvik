#!/usr/bin/env python3
"""Excursions versus the random-walk null — MEASUREMENT, zero trials.

Implements `diagnostics/research/excursions_null/SPEC.md` with its amendments A1 (sealed slice) and A2
(post-hoc matched-control null, the live weekly-close stop rule, three fixes). The SPEC was committed
before this script existed; A1 and A2 were committed before the run they describe. The constants below
are copied from the SPEC, not chosen here.

    python scripts/diag_excursions_null.py --live-end 2026-09-15          # substrate + live book
    python scripts/diag_excursions_null.py --offline                      # substrate only, no network

Outputs `diagnostics/research/excursions_null/<run-date>/{summary.json, rows.csv.gz}`. Nothing is adopted:
a change to the live `tp1_r` needs a pre-registration, a trial and the quarterly review.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from nq.brain import excursions as X  # noqa: E402
from nq.brain.io import assert_unsealed  # noqa: E402

# ── copied from SPEC.md; changing any of these is a SPEC change, not a tuning knob ─────────────────
K_GRID = (0.5, 1.0, 1.5, 2.0, 3.0)
HORIZON = 260
MU_SENS = 0.15
SIGMA_LOOKBACK, SIGMA_MIN = 63, 40
BAD_DROP, BAD_JUMP = -0.45, 0.90
N_BOOT, SEED = 2000, 20260916
MIN_INFORMATIVE = 30
BANDS = ("r<5%", "5%<=r<10%", "r>=10%")
SUBSTRATE_SPLITS = ("train", "holdout")      # the parquet's labels — NOT a seal-safe filter (SPEC A1)
UNSEALED_END = "2024-06-30"                   # evidence stops here; 2024-07-01.. is the sealed slice
SEALED_OPEN_ID = "S2"                         # the ledger row recording the unplanned 2026-09-16 open
EVIDENCE = ("train", "holdout_unsealed")
PRIMARY_SETUP = "touch44"
INCEPTION = "2026-07-04"
# A2.1 matched control (post-hoc)
N_CONTROLS, CONTROL_SIGMA_TOL, CONTROL_MIN_PRIOR = 20, 0.25, 64
RULES = ("continuous", "weekly_close")        # the SPEC's stop, and the live book's stop (A2.2)

OUT_BASE = ROOT / "diagnostics" / "research" / "excursions_null"


# --------------------------------------------------------------------------- inputs
def demerger_dates() -> dict[str, set[pd.Timestamp]]:
    out: dict[str, set[pd.Timestamp]] = {}
    for path, sym in (("data/corporate_actions_demerger_register.csv", "ticker"),
                      ("data/corporate_actions_post_harvest.csv", "symbol")):
        f = ROOT / path
        if f.exists():
            df = pd.read_csv(f, comment="#")
            if "kind" in df.columns:
                df = df[df["kind"].astype(str).str.lower() == "demerger"]
            for _, r in df.iterrows():
                out.setdefault(str(r[sym]).strip(), set()).add(pd.Timestamp(r["ex_date"]).normalize())
    return out


class Panel:
    """Per-ticker arrays, built once: prices, ISO-week-end mask, pre-entry sigma, integrity counters."""

    def __init__(self, df: pd.DataFrame, demergers: set[pd.Timestamp]):
        self.idx = pd.DatetimeIndex(df.index).normalize()
        self.pos = {d: i for i, d in enumerate(self.idx)}
        self.o = df["Open"].to_numpy(float)
        self.h = df["High"].to_numpy(float)
        self.l = df["Low"].to_numpy(float)
        self.c = df["Close"].to_numpy(float)
        iso = self.idx.isocalendar()
        wk = (iso["year"].astype(int) * 100 + iso["week"].astype(int)).to_numpy()
        self.week_end = np.append(wk[1:] != wk[:-1], True)
        with np.errstate(divide="ignore", invalid="ignore"):
            logret = pd.Series(np.log(np.where(self.c > 0, self.c, np.nan))).diff()
        roll = logret.rolling(SIGMA_LOOKBACK, min_periods=SIGMA_MIN).std() * np.sqrt(252.0)
        self.sigma_at = roll.shift(1).to_numpy()            # uses closes strictly before the bar
        with np.errstate(divide="ignore", invalid="ignore"):
            mv = self.c[1:] / self.c[:-1] - 1.0
        bad = np.concatenate([[0], ((mv <= BAD_DROP) | (mv >= BAD_JUMP)).astype(int)])
        self.bad_cum = np.cumsum(bad)
        self.demergers = sorted(demergers)

    def window_clean(self, i0: int, end: int) -> str | None:
        lo = max(i0, 1)
        if end - 1 >= lo and self.bad_cum[end - 1] - self.bad_cum[lo - 1] > 0:
            return "split-size move in window"
        if any(self.idx[i0] <= d <= self.idx[end - 1] for d in self.demergers):
            return "registered demerger in window"
        return None

    def outcomes(self, i0: int, end: int, entry: float, stop: float, weekly: bool) -> list[str]:
        w = slice(i0, end)
        return X.passage_outcomes(self.h[w], self.l[w], self.c[w], self.week_end[w],
                                  entry=entry, stop=stop, ks=K_GRID, weekly_stop=weekly)


def build_panels(ohlcv: dict, demergers: dict) -> dict[str, Panel]:
    return {t: Panel(df, demergers.get(t, set())) for t, df in ohlcv.items() if df is not None and len(df)}


# --------------------------------------------------------------------------- measurement
def measure(trades: pd.DataFrame, panels: dict[str, Panel]) -> pd.DataFrame:
    """One row per (trade, k): both stop rules, both first-passage nulls, exclusions."""
    rows = []
    labels = [c for c in trades.columns if c not in ("ticker", "entry_date", "entry", "stop")]
    for t in trades.itertuples(index=False):
        base = {"ticker": t.ticker, "entry_date": str(pd.Timestamp(t.entry_date).date()),
                **{c: getattr(t, c) for c in labels}}
        entry, stop = float(t.entry), float(t.stop)
        risk = round((entry - stop) / entry, 6) if entry > 0 else float("nan")
        p = panels.get(t.ticker)
        excl, i0, end = None, None, None
        if not (risk > 0):
            excl = "non-positive risk"
        elif p is None:
            excl = "no price series"
        else:
            i0 = p.pos.get(pd.Timestamp(t.entry_date).normalize())
            if i0 is None:
                excl = "no bar on the entry date"
            else:
                end = min(i0 + HORIZON, len(p.idx))
                excl = p.window_clean(i0, end)
        band = X.risk_band(risk) if risk == risk and risk > 0 else None
        if excl:
            rows += [{**base, "k": k, "risk": risk, "band": band, "excluded": excl} for k in K_GRID]
            continue
        cont = p.outcomes(i0, end, entry, stop, weekly=False)
        wkly = p.outcomes(i0, end, entry, stop, weekly=True)
        sig = p.sigma_at[i0]
        sig = float(sig) if np.isfinite(sig) else None
        first = X.first_passage(p.h[i0:end], p.l[i0:end], entry=entry, stop=stop, target=X.target_at(entry, stop, 3.0))
        for j, k in enumerate(K_GRID):
            tgt = X.target_at(entry, stop, k)
            fp = X.first_passage(p.h[i0:end], p.l[i0:end], entry=entry, stop=stop, target=tgt)
            rows.append({
                **base, "k": k, "risk": risk, "band": band, "excluded": None,
                "outcome": cont[j], "outcome_weekly": wkly[j], "sessions": fp.sessions,
                "mfe_r": first.mfe_r_before_stop, "window_sessions": end - i0,
                "null0": X.null_p_target_first(entry, stop, tgt), "sigma": sig,
                "null_mu": (X.null_p_target_first(entry, stop, tgt, mu=MU_SENS, sigma=sig) if sig else float("nan")),
            })
    return pd.DataFrame(rows)


def matched_controls(trades: pd.DataFrame, panels: dict[str, Panel]) -> pd.DataFrame:
    """A2.1 — per trade, up to N_CONTROLS same-day stocks with sigma within ±25%, at the trade's risk fraction.

    Returns one row per (trade, k) with the control hit rate among resolved controls, for both stop rules.
    Post-hoc: added after the red-team read, labelled as such in the summary."""
    rng = np.random.default_rng(SEED)
    names = sorted(panels)
    out = []
    for t in trades.itertuples(index=False):
        p = panels.get(t.ticker)
        d = pd.Timestamp(t.entry_date).normalize()
        entry, stop = float(t.entry), float(t.stop)
        i_tr = p.pos.get(d) if p is not None else None
        s0 = p.sigma_at[i_tr] if i_tr is not None else np.nan
        if not (entry > stop > 0) or not np.isfinite(s0):
            continue
        rfrac = (entry - stop) / entry
        got = {r: [] for r in RULES}
        n = 0
        for j in rng.permutation(len(names)):
            tk = names[j]
            if tk == t.ticker:
                continue
            q = panels[tk]
            i = q.pos.get(d)
            if i is None or i < CONTROL_MIN_PRIOR:
                continue
            sg = q.sigma_at[i]
            if not np.isfinite(sg) or abs(sg / s0 - 1.0) > CONTROL_SIGMA_TOL:
                continue
            end = min(i + HORIZON, len(q.idx))
            if q.window_clean(i, end):
                continue
            e = q.o[i]
            if not e > 0:
                continue
            st = e * (1.0 - rfrac)
            got["continuous"].append(q.outcomes(i, end, e, st, weekly=False))
            got["weekly_close"].append(q.outcomes(i, end, e, st, weekly=True))
            n += 1
            if n >= N_CONTROLS:
                break
        for jk, k in enumerate(K_GRID):
            row = {"ticker": t.ticker, "entry_date": str(d.date()), "k": k, "n_controls": n}
            for r in RULES:
                res = [o[jk] for o in got[r] if o[jk] != X.UNRESOLVED]
                row[f"ctl_{r}"] = (sum(o == X.HIT for o in res) / len(res)) if res else np.nan
            out.append(row)
    return pd.DataFrame(out)


# --------------------------------------------------------------------------- summaries
def _boot(obs, ref, tick) -> list[float]:
    pt, lo, hi = X.cluster_bootstrap_diff(obs, ref, tick.astype(str), n_boot=N_BOOT, seed=SEED)
    return [round(pt, 4), round(lo, 4), round(hi, 4)]


def _cell(g: pd.DataFrame) -> dict:
    ok = g[g["excluded"].isna()]
    cell: dict = {"n_trades": int(len(g)), "n_excluded": int(g["excluded"].notna().sum())}
    for rule, col in (("continuous", "outcome"), ("weekly_close", "outcome_weekly")):
        if col not in ok.columns:
            continue
        res = ok[ok[col].isin([X.HIT, X.STOPPED])]
        c: dict = {"n_resolved": int(len(res)), "n_unresolved": int((ok[col] == X.UNRESOLVED).sum()),
                   "informative": len(res) >= MIN_INFORMATIVE}
        if len(res):
            hit = (res[col] == X.HIT).astype(float)
            c["hit_rate"] = round(float(hit.mean()), 4)
            if rule == "continuous":                          # the SPEC's nulls are continuous-barrier nulls
                c["null0"] = round(float(res["null0"].mean()), 4)
                c["excess_vs_null0 [pt, lo, hi]"] = _boot(hit, res["null0"], res["ticker"])
                mu = res[res["null_mu"].notna()]
                if len(mu):
                    c["null_mu15"] = round(float(mu["null_mu"].mean()), 4)
                    c["excess_vs_null_mu15 [pt, lo, hi]"] = _boot((mu[col] == X.HIT).astype(float),
                                                                   mu["null_mu"], mu["ticker"])
                hs = res.loc[res[col] == X.HIT, "sessions"]
                if len(hs):
                    c["median_sessions_to_hit"] = float(hs.median())
                ss = res.loc[res[col] == X.STOPPED, "sessions"]
                if len(ss):
                    c["median_sessions_to_stop"] = float(ss.median())
            ctl_col = f"ctl_{rule}"
            if ctl_col in res.columns:
                m = res[res[ctl_col].notna()]
                if len(m):
                    c["matched_control_POSTHOC"] = {
                        "n": int(len(m)), "control_hit_rate": round(float(m[ctl_col].mean()), 4),
                        "trade_hit_rate": round(float((m[col] == X.HIT).mean()), 4),
                        "excess [pt, lo, hi]": _boot((m[col] == X.HIT).astype(float), m[ctl_col], m["ticker"]),
                    }
        cell[rule] = c
    return cell


def summarise(rows: pd.DataFrame) -> dict:
    out: dict = {}
    for k in K_GRID:
        g = rows[rows["k"] == k]
        out[f"k={k}"] = {"all": _cell(g), **{b: _cell(g[g["band"] == b]) for b in BANDS}}
    one = rows[(rows["k"] == K_GRID[0]) & rows["excluded"].isna()]
    if len(one):
        q = one["mfe_r"].quantile([0.25, 0.5, 0.75, 0.9]).round(3)
        out["mfe_r_before_stop_quantiles"] = {str(i): float(v) for i, v in q.items()}
    ex = rows[rows["k"] == K_GRID[0]]["excluded"].value_counts()
    out["exclusions"] = {str(i): int(v) for i, v in ex.items()}
    return out


# --------------------------------------------------------------------------- populations
def substrate_trades() -> pd.DataFrame:
    """SPEC A1 populations. `train` and `holdout_unsealed` are the evidence; `sealed_S2` is disclosure.

    The sealed rows pass `assert_unsealed` only under the recorded S2 row, so a rerun reproduces the
    record of the open and cannot become a new one."""
    d = pd.read_parquet(ROOT / "research" / "substrate" / "trades.parquet")
    d = d[d["split"].isin(SUBSTRATE_SPLITS)].copy()
    unsealed = d["entry_date"] <= pd.Timestamp(UNSEALED_END)
    d["population"] = np.where(d["split"] == "train", "train",
                               np.where(unsealed, "holdout_unsealed", "sealed_S2"))
    assert_unsealed(d.loc[d["population"] != "sealed_S2", "entry_date"])
    assert_unsealed(d.loc[d["population"] == "sealed_S2", "entry_date"], declared_open=SEALED_OPEN_ID)
    return d[["ticker", "entry_date", "entry", "stop", "setup", "population"]].reset_index(drop=True)


def live_trades() -> pd.DataFrame:
    """Each entered trade's entry and stop from the FIRST archived snapshot that shows it held (A2.3)."""
    first: dict = {}
    for f in sorted(glob.glob(str(ROOT / "results" / "archive" / "*" / "signals_today_weekly.json"))):
        for s in json.loads(Path(f).read_text(encoding="utf-8")).get("signals", []):
            if s.get("bought_date") and s.get("entry") and s.get("stop"):
                key = (s["ticker"], str(s["bought_date"])[:10])
                first.setdefault(key, (float(s["entry"]), float(s["stop"])))
    rows = [{"ticker": t, "entry_date": d, "entry": e, "stop": st} for (t, d), (e, st) in sorted(first.items())
            if d >= INCEPTION]
    return pd.DataFrame(rows, columns=["ticker", "entry_date", "entry", "stop"])


def download_raw(tickers: list[str], start: str, end: str) -> dict[str, pd.DataFrame]:
    """UNADJUSTED daily bars (A2.3): the archived entry/stop are raw prices, so the path must be too."""
    import yfinance as yf
    end_excl = str((pd.Timestamp(end) + pd.Timedelta(days=1)).date())
    data = yf.download([f"{t}.NS" for t in tickers], start=start, end=end_excl, auto_adjust=False,
                       progress=False, group_by="ticker", threads=True)
    out = {}
    for t in tickers:
        try:
            df = data[f"{t}.NS"][["Open", "High", "Low", "Close"]].dropna()
        except KeyError:
            continue
        if len(df):
            out[t] = df
    return out


def assert_completed_session(end: str, today: date | None = None) -> None:
    today = today or date.today()
    if date.fromisoformat(end) >= today:
        raise SystemExit(f"--live-end {end} is not a completed session (today is {today}); use the last closed one")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--live-end", help="last COMPLETED session for the live book's prices")
    ap.add_argument("--offline", action="store_true", help="substrate only; no network")
    ap.add_argument("--run-date", default=str(date.today()))
    args = ap.parse_args(argv)
    if not args.offline and not args.live_end:
        ap.error("--live-end is required unless --offline")

    from run_bhanushali_path1 import corrected_universe
    dem = demerger_dates()
    counts = json.loads((ROOT / "diagnostics" / "research" / "n_trials.json").read_text(encoding="utf-8"))
    summary: dict = {
        "spec": "diagnostics/research/excursions_null/SPEC.md (with amendments A1, A2)",
        "class": "MEASUREMENT (zero trials)", "n_trials_at_run": counts["cumulative_n_trials"],
        "run_date": args.run_date,
        "constants": {"k_grid": K_GRID, "horizon": HORIZON, "mu_sensitivity": MU_SENS, "n_boot": N_BOOT,
                      "seed": SEED, "min_informative": MIN_INFORMATIVE, "n_controls": N_CONTROLS,
                      "control_sigma_tol": CONTROL_SIGMA_TOL},
        "reading": ("Selection claims are made ONLY against matched_control_POSTHOC (A2): the first-passage "
                    "nulls cannot separate selection from market drift. sealed_S2 is disclosure, not evidence."),
    }

    sub = substrate_trades()
    panels = build_panels(corrected_universe(), dem)
    rows_a = measure(sub, panels)
    ev = sub[sub["population"].isin(EVIDENCE)]
    ctl = matched_controls(ev, panels)
    rows_a = rows_a.merge(ctl, on=["ticker", "entry_date", "k"], how="left")
    summary["substrate"] = {}
    for pop in ("train", "holdout_unsealed", "sealed_S2"):
        r = rows_a[rows_a["population"] == pop]
        summary["substrate"][pop] = {"touch44 (primary)": summarise(r[r["setup"] == PRIMARY_SETUP]),
                                     "all setups": summarise(r)}
    summary["substrate"]["sealed_S2"]["_status"] = (
        "DISCLOSURE ONLY — unplanned sealed open S2 (label_screen_ledger.md). Not evidence; no interpretation "
        "rule reads it, and no matched control was drawn for it (SPEC A1, A2).")
    all_rows = [rows_a]

    if not args.offline:
        assert_completed_session(args.live_end)
        live = live_trades()
        px = download_raw(sorted(live["ticker"].unique()), start="2026-01-01", end=args.live_end)
        rows_b = measure(live, build_panels(px, dem))
        summary["live"] = {"end": args.live_end, "n_entered_trades": int(len(live)),
                           "_status": "forward-wall description; no matched control (the universe is not downloaded)",
                           **summarise(rows_b)}
        all_rows.append(rows_b.assign(population="live"))

    out = OUT_BASE / args.run_date
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    pd.concat(all_rows, ignore_index=True).to_csv(out / "rows.csv.gz", index=False, compression="gzip")
    print(f"excursions null -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
