import json
import numpy as np
import pandas as pd
from pathlib import Path

H = Path(__file__).resolve().parent


def summ(v):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    se = v.std(ddof=1) / np.sqrt(len(v))
    return {"n": int(len(v)), "mean": float(v.mean()), "sd": float(v.std(ddof=1)), "se": float(se),
            "median": float(np.median(v)), "p95": float(np.percentile(v, 95)),
            "abs_mean_le_2se": bool(abs(v.mean()) <= 2 * se), "p95_lt_0.3": bool(np.percentile(v, 95) < 0.3)}


out = {"anchors": {"momentum": json.loads((H / "mom_anchor.json").read_text())}}
for book, f in (("swing", "swing_n1_rows.jsonl"), ("0001", "mom_n1_rows.jsonl")):
    p = H / f
    if not p.exists():
        continue
    df = pd.DataFrame([json.loads(l) for l in p.read_text().splitlines() if l.strip()]).drop_duplicates("seed")
    out[f"N1_{book}"] = {"raw_sharpe": summ(df["sharpe"]), "appraisal": summ(df["appraisal"]),
                         "mean_beta": float(df["beta"].mean())}
    if "no_candidate" in df:
        out[f"N1_{book}"]["shuffle_stats_mean"] = df[["signals", "assigned", "no_candidate", "no_prior_week_bar",
                                                      "sma_fallback", "u_missing_some_entry_days"]].mean().to_dict()
for book, f in (("swing", "swing_s1.json"), ("0001", "mom_s1.json")):
    p = H / f
    if p.exists():
        out[f"S1_{book}"] = json.loads(p.read_text())
(H / "replica_results.json").write_text(json.dumps(out, indent=1, default=float))
print(json.dumps(out, indent=1, default=float))
