"""The §3 wall read of forward/prereg_signal_quality.md — frozen procedure, no new axis, no new cut.

For each of the four pre-registered axes: mean forward r_multiple in the hypothesised-strong bucket
minus the weak bucket, a bootstrap CI, the per-year sign, and a Holm bar across the family of four.
FORWARD rows (signal on/after the 2026-08-17 inception) are the confirmatory set; SEED rows are
reported beside them and never pooled into it (§2).

Measurement only: no trial, no screen, no sealed-slice read (every row is >= 2026-07-04). The
result is EVIDENCE, never authorization (§4) — a positive axis earns a separate pre-registered trial.

    python pipelines/diagnostics/read_signal_quality_wall.py   # -> diagnostics/research/signal_quality_wall/<as_of>.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "results" / "signal_quality_forward.csv"
OUT = ROOT / "diagnostics" / "research" / "signal_quality_wall"

MIN_PER_BUCKET = 5           # below this a bucket mean is not reported as a contrast (backtest-rigor §E1)
N_BOOT = 10_000
SEED = 20260817              # the pre-registration date, fixed so the CI reproduces


def _buckets(df: pd.DataFrame) -> dict[str, tuple[pd.Series, pd.Series, str]]:
    """The frozen strong/weak split for each axis, exactly as §1 defines it."""
    out = {}
    out["Q1 body_ratio"] = (df["body_ratio"] >= 0.50, df["body_ratio"] < 0.50, "solid (>=0.50) vs doji (<0.50)")
    td = df["touch_depth_min_ext"]
    out["Q2 touch_depth"] = (td < 5.0, (td >= 5.0) & (td < 10.0), "deep (<5%) vs shallow (5-10%)")
    conv = df["signal_conviction"].astype(str).str.lower()
    out["Q3 signal_conviction"] = (conv == "normal", conv == "low", "normal vs low")
    cr = df["crs_rank"]
    if cr.notna().sum() >= 3:
        lo, hi = cr.quantile([1 / 3, 2 / 3])
        out["Q4 crs_rank"] = (cr >= hi, cr <= lo, f"top tercile (>={hi:.3g}) vs bottom (<={lo:.3g})")
    else:
        out["Q4 crs_rank"] = (cr.notna() & False, cr.notna() & False, "terciles undefined (n<3)")
    return out


def _boot_ci(a: np.ndarray, b: np.ndarray, rng) -> tuple[float, float]:
    d = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(N_BOOT)]
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def read(df: pd.DataFrame) -> list[dict]:
    rng = np.random.default_rng(SEED)
    rows = []
    for name, (strong, weak, rule) in _buckets(df).items():
        s, w = df.loc[strong.fillna(False), "r_multiple"].to_numpy(), df.loc[weak.fillna(False), "r_multiple"].to_numpy()
        r = {"axis": name, "rule": rule, "n_strong": int(len(s)), "n_weak": int(len(w)),
             "mean_strong": float(s.mean()) if len(s) else None, "mean_weak": float(w.mean()) if len(w) else None}
        if len(s) >= MIN_PER_BUCKET and len(w) >= MIN_PER_BUCKET:
            r["diff"] = r["mean_strong"] - r["mean_weak"]
            r["ci95"] = _boot_ci(s, w, rng)
            # Family of four, Bonferroni bar (Holm's strictest step): a two-sided 1 - 0.05/4 interval,
            # i.e. the 0.625th..99.375th bootstrap percentiles, must exclude zero.
            lo, hi = np.percentile([rng.choice(s, len(s)).mean() - rng.choice(w, len(w)).mean()
                                    for _ in range(N_BOOT)], [0.625, 99.375])
            r["ci_holm_strict"] = (float(lo), float(hi))
            r["survives_family"] = bool(lo > 0 or hi < 0)
            r["status"] = "INFORMATIVE" if r["survives_family"] else "UNDERPOWERED"
        else:
            r["status"] = f"UNDERPOWERED (a bucket below {MIN_PER_BUCKET})"
        r["years"] = sorted({str(d)[:4] for d in df.loc[strong.fillna(False) | weak.fillna(False), "signal_date"]})
        rows.append(r)
    return rows


def main() -> int:
    df = pd.read_csv(SRC)
    closed = df[df["r_multiple"].notna()].copy()
    as_of = str(df["signal_date"].max())
    res = {"source": SRC.relative_to(ROOT).as_posix(), "as_of_max_signal": as_of,
           "n_rows": int(len(df)), "n_closed": int(len(closed)),
           "closed_by_phase": closed["phase"].value_counts().to_dict(),
           "exit_reasons_closed": closed["exit_reason"].fillna("?").value_counts().to_dict(),
           "n_open": int((df["status"] == "ACTIVE").sum()),
           "censoring": ("every closed signal is a stop; winners hold longer and are still open, so a "
                         "closed-only contrast compares losers with losers and is biased toward zero"
                         if (closed["status"] == "HIT_STOP").all() else "mixed exits"),
           "forward": read(closed[closed["phase"] == "forward"]),
           "seed": read(closed[closed["phase"] == "seed"]),
           "verdict_rule": "§3: an axis carries information only if it survives the family correction; "
                           "§4: UNDERPOWERED carries the wall another quarter. Nothing here changes the book."}
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{as_of}.json"
    path.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"closed {res['n_closed']} {res['closed_by_phase']} | exits {res['exit_reasons_closed']} | open {res['n_open']}")
    for phase in ("forward", "seed"):
        for r in res[phase]:
            print(f"  [{phase}] {r['axis']:<22} n {r['n_strong']}/{r['n_weak']} "
                  f"strong {r['mean_strong'] if r['mean_strong'] is None else round(r['mean_strong'], 2)} "
                  f"weak {r['mean_weak'] if r['mean_weak'] is None else round(r['mean_weak'], 2)} -> {r['status']}"
                  + (f" diff {r['diff']:+.2f} CI95 [{r['ci95'][0]:+.2f}, {r['ci95'][1]:+.2f}]" if "diff" in r else ""))
    print(f"-> {path.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
