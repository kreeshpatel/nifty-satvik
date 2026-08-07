"""0123 Phase-1.5 — DETECTOR-INTEGRITY audit + the pre-registered agreement/disagreement split.

For each graded chart, evaluate the COMMITTED detectors (nq/research/setups.py zoo + the box and
S/R-pivot logic used in the chart-validation work) at the SAME decision week the model saw, then:
 1. agreement rate per detector vs the model's setup_type / box_region annotation,
 2. the disagreement cohort (ids listed for eyeballing),
 3. THE DECISIVE CROSS-CHECK: re-run the Phase-2 separation test SEPARATELY on the agreement and
    disagreement cohorts (pre-registered; adds no ledger row).
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from render_blind_chart import load_panel, _weekly_volume
from render_chart import weekly
from nq.research import setups as S
sys.path.insert(0, str(ROOT / "scripts"))
from screen_0123 import _merged, _celladj, _boot_ci

OUT = ROOT / "research" / "substrate" / "grades_0123" / "phase15_detectors.csv"


def detectors_at(ticker, entry_date, P, n50, ohlcv):
    """Fire-state of every committed detector at the decision week (last completed week < entry)."""
    w = weekly(ticker, P, n50)
    wv = _weekly_volume(ticker, P, ohlcv)
    wd = w["wd"]
    ed = pd.Timestamp(entry_date)
    idxs = [i for i, x in enumerate(wd) if x < ed]
    if not idxs:
        return None
    k = idxs[-1]
    wo, wh, wl, wc = w["wo"], w["wh"], w["wl"], w["wc"]
    wsma, slope = w["ws"], w["slope"]
    rs = w["rsok"].astype(float)
    n = min(len(wc), len(wv))
    args = (wo[:n], wh[:n], wl[:n], wc[:n], wv[:n], wsma[:n], slope[:n], rs[:n])
    if k >= n:
        return None
    out = {}
    for name, fn in [("vcp", S.vcp_signal), ("flag", S.flag_signal), ("cup_handle", S.cup_handle_signal),
                     ("ascending_base", S.ascending_base_signal), ("double_bottom", S.double_bottom_signal)]:
        try:
            sig, _ = fn(*args)
            out[name] = bool(sig[k])
        except Exception:
            out[name] = False

    # box (flat-base) detector — the TIGHT keeper version from the chart-validation work
    box_len, box_tight = 8, 0.15
    box = False; box_lo = box_hi = np.nan
    if k >= box_len and np.nan_to_num(slope[k], nan=-9) >= S.SLOPE_MIN:
        bh = wh[k - box_len:k].max(); bl = wl[k - box_len:k].min()
        if bl > 0 and (bh - bl) / bl <= box_tight and wsma[k] == wsma[k] and wc[k - box_len:k].min() > wsma[k]:
            box = True; box_lo, box_hi = bl, bh
    out["box_breakout"] = box; out["box_lo"] = box_lo; out["box_hi"] = box_hi

    # S/R pivot level detector (>=2 pivot highs clustered, price breaking it)
    piv = np.zeros(len(wh), bool)
    for i in range(2, len(wh) - 2):
        if wh[i] >= wh[i - 2:i + 3].max():
            piv[i] = True
    sr = False; sr_lvl = np.nan
    if k >= 14:
        pv = [wh[i] for i in range(k - 14, k - 1) if piv[i]]
        if len(pv) >= 2:
            lvl = float(np.median(pv))
            near = [p for p in pv if abs(p / lvl - 1) <= 0.03]
            if len(near) >= 2 and wc[k - 1] <= lvl < wc[k]:
                sr = True; sr_lvl = lvl
    out["sr_breakout"] = sr; out["sr_level"] = sr_lvl
    out["any_zoo"] = any(out[x] for x in ["vcp", "flag", "cup_handle", "ascending_base", "double_bottom"])
    out["any_detector"] = out["any_zoo"] or box or sr
    return out


MODEL_TO_DET = {   # model setup_type -> the committed detector that claims the same concept
    "flat_base_box": "box_breakout", "sr_breakout": "sr_breakout", "cup_handle": "cup_handle",
    "ascending_base": "ascending_base", "double_bottom": "double_bottom",
}


def main():
    df = _merged()
    P, n50, ohlcv = load_panel()
    rows = []
    for _, r in df.iterrows():
        d = detectors_at(r["ticker"], r["entry_date"], P, n50, ohlcv)
        if d is None:
            continue
        rows.append({"id": r["id"], **{k: v for k, v in d.items()}})
    det = pd.DataFrame(rows)
    m = df.merge(det, on="id", how="inner")
    m.to_csv(OUT, index=False)
    print(f"detector states computed for {len(m)}/{len(df)} charts -> {OUT}")

    # --- 1. agreement rates ---
    print("\n--- 1. DETECTOR INTEGRITY: model annotation vs committed formula detectors ---")
    m["model_says_setup"] = m["setup_type"] != "no_clear_setup"
    m["model_box"] = m["box_region"].notna() & (m["box_region"].astype(str) != "None")
    print(f"  model sees SOME setup: {m['model_says_setup'].mean()*100:.1f}%   "
          f"formulas fire ANY detector: {m['any_detector'].mean()*100:.1f}%")
    agree_any = (m["model_says_setup"] == m["any_detector"]).mean()
    print(f"  presence agreement (any setup): {agree_any*100:.1f}%")
    print(f"  model box_region present: {m['model_box'].mean()*100:.1f}%  vs box detector: {m['box_breakout'].mean()*100:.1f}%  "
          f"agreement {(m['model_box']==m['box_breakout']).mean()*100:.1f}%")
    # class-level match
    m["class_match"] = [MODEL_TO_DET.get(st) is not None and bool(row.get(MODEL_TO_DET.get(st), False))
                        for st, row in zip(m["setup_type"], m.to_dict("records"))]
    print(f"  setup-CLASS match (model's named type also fires in formulas): {m['class_match'].mean()*100:.1f}%")
    print("\n  model setup_type distribution:")
    for k, v in m["setup_type"].value_counts().items():
        print(f"    {k:18s} {v}")
    print("  committed detector fire-rates:")
    for c in ["box_breakout", "sr_breakout", "cup_handle", "double_bottom", "ascending_base", "vcp", "flag"]:
        print(f"    {c:18s} {m[c].mean()*100:5.1f}%")

    # --- 2. disagreement cohort ---
    m["agree"] = m["model_says_setup"] == m["any_detector"]
    dis = m[~m["agree"]]
    print(f"\n--- 2. DISAGREEMENT COHORT: n={len(dis)} ({len(dis)/len(m)*100:.1f}%) ---")
    print(f"  model-sees-setup but formulas silent: {((m['model_says_setup']) & (~m['any_detector'])).sum()}")
    print(f"  formulas fire but model sees none:    {((~m['model_says_setup']) & (m['any_detector'])).sum()}")
    dis[["id", "ticker", "entry_date", "cohort", "setup_type", "any_detector", "grade", "R"]].to_csv(
        OUT.parent / "phase15_disagreement_cohort.csv", index=False)
    print(f"  committed -> {OUT.parent / 'phase15_disagreement_cohort.csv'}")

    # --- 3. THE DECISIVE CROSS-CHECK ---
    print("\n--- 3. DECISIVE CROSS-CHECK: separation re-run on each cohort ---")
    for label, sub in [("AGREEMENT", m[m["agree"]]), ("DISAGREEMENT", m[~m["agree"]])]:
        if len(sub) < 40:
            print(f"  {label}: n={len(sub)} too small to test"); continue
        sub = sub.copy(); sub["g_adj"] = _celladj(sub, "grade")
        sw = sub[sub["cohort"] == "strong_winner"]["g_adj"].values
        st = sub[sub["cohort"].isin(["false_touch", "noise_stop"])]["g_adj"].values
        if len(sw) < 10 or len(st) < 10:
            print(f"  {label}: thin cohorts"); continue
        d, lo, hi = _boot_ci(sw, st)
        print(f"  {label:13s} n={len(sub):3d}  celladj grade (winner - stopout) = {d:+.3f}  "
              f"CI[{lo:+.3f},{hi:+.3f}]  {'SEPARATES' if (lo>0 or hi<0) else 'CI straddles 0 -> NULL'}")


if __name__ == "__main__":
    main()
