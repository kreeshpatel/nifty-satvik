"""MEASUREMENT (part of screen #25): hindsight bound for feature (e), results-meeting stops held to the eventual exit.

Definition and kill rule: diagnostics/research/explore/2026-11-19_stop_conformance_and_fall_discriminator.md, the
"(e) hindsight bound" section (committed before this ran). Train only; prices cut at 2024-06-30. No book backtest.

    python pipelines/diagnostics/explore_results_stop_bound.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
OUT = ROOT / "diagnostics" / "research" / "explore" / "2026-11-19_results_stop_bound.json"
CUT = pd.Timestamp("2024-06-30")
YEARS = 5.5


def main() -> int:
    from run_bhanushali_path1 import corrected_universe
    f = pd.read_csv(ROOT / ".cache" / "fall_discriminator" / "features.csv", parse_dates=["entry_date", "stop_time"])
    ctx = pd.read_parquet(ROOT / "research" / "substrate" / "context_windows.parquet")
    ctx["entry_date"] = pd.to_datetime(ctx["entry_date"])
    f = f.merge(ctx[["ticker", "entry_date", "entry", "stop", "exit_px", "exit_date", "post_ret21"]], on=["ticker", "entry_date"], how="left")
    f["year"] = f["stop_time"].dt.year
    out = {"counts_flagged_by_cohort_year": {}}
    for c, g in f.groupby("cohort"):
        out["counts_flagged_by_cohort_year"][c] = {"flagged": int(g["e_results_5s"].sum()), "total": int(len(g)),
                                                   "by_year": {int(y): int(v) for y, v in g.groupby("year")["e_results_5s"].sum().items()}}
    e = f[f["e_results_5s"] == 1].copy()
    u = corrected_universe()
    rows = []
    for r in e.itertuples():
        df = u[r.ticker]
        ix = pd.DatetimeIndex(df.index).normalize()
        p = pd.DataFrame({"o": (df["open"] if "open" in df else df["Open"]).to_numpy(float),
                          "c": (df["close"] if "close" in df else df["Close"]).to_numpy(float)}, index=ix)
        p = p[~p.index.duplicated(keep="last")].sort_index()
        p = p[p.index <= CUT]
        wk = p["c"].groupby([p.index.isocalendar().year.to_numpy(), p.index.isocalendar().week.to_numpy()])
        wlast = pd.Series({g.index[-1]: g.iloc[-1] for _, g in wk})            # ISO-week last bar -> close
        wsma = wlast.rolling(44).mean()
        stop_wk_end = wlast.index[wlast.index >= r.stop_time][0] if (wlast.index >= r.stop_time).any() else None
        risk = float(r.entry - r.stop)
        hold_px, how, hold_date = np.nan, "", None
        if stop_wk_end is not None:
            cand = wlast.index[(wlast.index >= stop_wk_end)]
            hit = [d for d in cand if wsma.get(d) == wsma.get(d) and wlast[d] < wsma[d]]
            if hit:
                nxt = p.index[p.index > hit[0]]
                if len(nxt):
                    hold_px, hold_date, how = float(p.loc[nxt[0], "o"]), nxt[0], "sma_break" + ("_same_week" if hit[0] == stop_wk_end else "")
                else:
                    hold_px, hold_date, how = float(p["c"].iloc[-1]), p.index[-1], "mark_to_cut"
            else:
                hold_px, hold_date, how = float(p["c"].iloc[-1]), p.index[-1], "mark_to_cut"
        if how.endswith("_same_week"):
            d_r = 0.0
        else:
            d_r = (hold_px - float(r.exit_px)) / risk if risk > 0 else np.nan
        # secondary: banked 21-session path, marked to the cut where it runs past it
        post = p[p.index > r.stop_time]
        if len(post) >= 22 or pd.Timestamp(r.exit_date) + pd.Timedelta(days=35) <= CUT:
            sec = float(r.post_ret21 * r.exit_px / risk) if risk > 0 else np.nan
            sec_how = "banked_post_ret21"
        else:
            sec = (float(p["c"].iloc[-1]) - float(r.exit_px)) / risk if risk > 0 else np.nan
            sec_how = "marked_to_cut"
        rows.append({"ticker": r.ticker, "cohort": r.cohort, "year": int(r.year), "stop_time": r.stop_time, "dR_primary": d_r,
                     "exit_rule": how, "hold_date": hold_date, "dR_secondary_21s": sec, "secondary_basis": sec_how})
    h = pd.DataFrame(rows)

    def summ(col):
        tot = float(h[col].sum())
        by = h.groupby("year")[col].sum()
        flips = int(sum(1 for v in by if np.sign(v) != np.sign(tot) and v != 0))
        w = h.loc[h[col].idxmin()]
        return {"total_R": round(tot, 1), "R_per_year": round(tot / YEARS, 2),
                "by_cohort": {c: round(float(v), 1) for c, v in h.groupby("cohort")[col].sum().items()},
                "by_year": {int(y): round(float(v), 1) for y, v in by.items()},
                "years_with_sign_opposite_to_total": flips,
                "worst_trade": {"ticker": w["ticker"], "cohort": w["cohort"], "stop_time": str(w["stop_time"].date()), "dR": round(float(w[col]), 2)},
                "kill": bool(abs(tot / YEARS) < 10 or flips >= 2)}
    out["n_flagged"] = int(len(h))
    out["exit_rule_mix_primary"] = h["exit_rule"].value_counts().to_dict()
    out["primary_eventual_exit"] = summ("dR_primary")
    out["secondary_banked_21s"] = summ("dR_secondary_21s")
    out["secondary_basis_mix"] = h["secondary_basis"].value_counts().to_dict()
    out["verdict"] = ("KILL RULE MET: the stop domain closes for this book" if out["primary_eventual_exit"]["kill"]
                      else "kill rule not met")
    out["per_trade"] = h.assign(stop_time=h["stop_time"].astype(str), hold_date=h["hold_date"].astype(str)).round(4).to_dict("records")
    OUT.write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "per_trade"}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
