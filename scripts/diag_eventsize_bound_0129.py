"""0129 — Event-proximity SIZING activation bound. ACTIVATION BOUND (ledger row #15). No trial.

Pre-registration: `diagnostics/research/preregistry/0129-eventsize-activation-bound.md`. Every
definition, the size grid, both arms, the gate and both branches are frozen there and are not
re-opened here.

0120 measured the effect (entry with an ANNOUNCED results event inside 14 calendar days costs
-0.383R raw / -0.294 conditional, 5/6 years, ADV-robust, ~10% activation). 0121 killed DEFERRAL via
its bound (94% lapse -> a de-facto skip -> -15.72 R/yr). SIZING is a different mechanism: the trade
still happens, the book stays full, there is no lapse and no idle-cash exposure. The event
definition and N=14cd are IMPORTED VERBATIM from 0120/0121 -- nothing is re-tuned.

Two arms, both reported:
  (a) freed capital LEFT IN CASH   -- the Law III bookend in sizing form
  (b) freed capital REDEPLOYED     -- the honest arm (the book stays full), realistic + clairvoyant

The 2024H2+ sealed slice is not read. The judge log is not read.

Reproduce:
    python scripts/diag_eventsize_bound_0129.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nq.data.delivery import apply_alias_map  # noqa: E402
from nq.data.earnings import EARNINGS_RAW_PATH, build_event_table  # noqa: E402

# ---- FROZEN (pre-reg §1). No sweep anywhere in this file. ----
EVENT_WINDOW_CD = 14                     # imported verbatim from 0120/0121
SIZE_GRID = (0.50, 0.75)                 # position multipliers, both stated in advance
TRAIN_LO, TRAIN_HI = "2019-01-01", "2024-06-30"
YRS = 5.5
FLOOR_R_PER_YR = 10.0                    # 0109 / 0117 path-noise floor
DISASTER_R = -1.5                        # 0109 disaster-floor convention

CAPPED = ROOT / "research" / "exports" / "bhanushali_weekly_rank_0094_trades.csv"
CTX = ROOT / "research" / "substrate" / "context_windows.parquet"
SUBSTRATE = ROOT / "research" / "substrate" / "trades.parquet"
WORKED_EXAMPLES = ("CANFINHOME", "LINDEINDIA", "NATCOPHARM", "GLENMARK")

OUT_JSON = ROOT / "diagnostics" / "research" / "eventsize_bound_0129.json"
OUT_MD = ROOT / "diagnostics" / "research" / "eventsize_bound_0129.md"


# --------------------------------------------------------------------------------------
# frozen activation rule (0120 Q2 / 0121, verbatim logic)
# --------------------------------------------------------------------------------------
def event_index(ev: pd.DataFrame) -> dict:
    return {s: g.sort_values("event_date")[["event_date", "ann_ts"]].to_numpy()
            for s, g in ev.groupby("symbol")}


def sig_friday(entry: pd.Series) -> pd.Series:
    return entry - pd.to_timedelta(entry.dt.weekday + 3, unit="D")


def activation(df: pd.DataFrame, evs: dict, tkr_col: str) -> pd.DataFrame:
    """Adds `activated` and `event_date` (the anchoring known event) — frozen 0120 Q2 rule."""
    out = df.copy()
    out["activated"] = False
    out["event_date"] = pd.NaT
    for i, r in out.iterrows():
        a = evs.get(r[tkr_col])
        if a is None:
            continue
        sf = r["sig_fri"]
        monday = sf + pd.Timedelta(days=3)
        known = a[a[:, 1] <= np.datetime64(sf)]              # announced by the decision moment
        if not len(known):
            continue
        m = known[(known[:, 0] >= np.datetime64(monday)) &
                  (known[:, 0] <= np.datetime64(monday + pd.Timedelta(days=EVENT_WINDOW_CD)))]
        if len(m):
            out.at[i, "activated"] = True
            out.at[i, "event_date"] = pd.Timestamp(m[:, 0].min())
    return out


def trailing_event_share(df: pd.DataFrame, evs: dict, tkr_col: str) -> dict:
    """DESCRIPTIVE ONLY (mechanism note, no outcome contrast, no multiplicity spent).

    The activation rule looks FORWARD 14cd. This measures how often the entry is instead
    immediately DOWNSTREAM of an event — event_date in [monday-14cd, monday). It is reported
    because the worked example showed all four owner-named tickers in that position, and a
    reader is owed the base rate. No R is attached to it anywhere in this file.
    """
    linked = fwd = bwd = 0
    for _, r in df.iterrows():
        a = evs.get(r[tkr_col])
        if a is None:
            continue
        linked += 1
        sf = r["sig_fri"]
        monday = sf + pd.Timedelta(days=3)
        known = a[a[:, 1] <= np.datetime64(sf)]
        if len(known) and len(known[(known[:, 0] >= np.datetime64(monday)) &
                                    (known[:, 0] <= np.datetime64(monday + pd.Timedelta(days=EVENT_WINDOW_CD)))]):
            fwd += 1
        # trailing leg uses TRUE event dates (label layer — the trade lived through them either way)
        if len(a[(a[:, 0] >= np.datetime64(monday - pd.Timedelta(days=EVENT_WINDOW_CD))) &
                 (a[:, 0] < np.datetime64(monday))]):
            bwd += 1
    n = max(linked, 1)
    return {"n_linked_to_calendar": linked, "linkage_pct": round(100.0 * linked / max(len(df), 1), 1),
            "forward_14cd_pct": round(100.0 * fwd / n, 1),
            "trailing_14cd_pct": round(100.0 * bwd / n, 1),
            "note": "descriptive only — no outcome contrast is computed on the trailing leg"}


def per_year_sign(values: np.ndarray, years: pd.Series) -> dict:
    s = pd.Series(values, index=years.index).groupby(years).sum()
    pos = int((s > 0).sum())
    neg = int((s < 0).sum())
    return dict(by_year={int(k): round(float(v), 2) for k, v in s.items()},
                n_years=int(len(s)), n_positive=pos, n_negative=neg,
                majority_sign="+" if pos * 2 > len(s) else ("-" if neg * 2 > len(s) else "tie"),
                majority_share=f"{max(pos, neg)}/{len(s)}")


def arms(d: pd.DataFrame, r_col: str, peer_mean: float, clair_col: str | None) -> dict:
    """Both arms x the frozen size grid. d = ACTIVATED trades only."""
    years = d["entry_date"].dt.year
    r = d[r_col].to_numpy(float)
    res = {}
    for f in SIZE_GRID:
        cash = (f - 1.0) * r                                     # arm (a)
        real = (1.0 - f) * (peer_mean - r)                       # arm (b) realistic
        entry = {
            "a_cash": {"total_R": round(float(cash.sum()), 2),
                       "R_per_yr": round(float(cash.sum()) / YRS, 2),
                       "per_year": per_year_sign(cash, years)},
            "b_redeploy_realistic": {
                "replacement_R_assumed": round(peer_mean, 3),
                "total_R": round(float(real.sum()), 2),
                "R_per_yr": round(float(real.sum()) / YRS, 2),
                "per_year": per_year_sign(real, years)},
        }
        if clair_col is not None:
            rep = d[clair_col].to_numpy(float)
            ok = np.isfinite(rep)
            clair = np.where(ok, (1.0 - f) * (np.nan_to_num(rep) - r), 0.0)
            entry["b_redeploy_clairvoyant"] = {
                "queue_coverage": f"{int(ok.sum())}/{len(d)}",
                "mean_best_alternative_R": round(float(np.nanmean(rep)), 3) if ok.any() else None,
                "total_R": round(float(clair.sum()), 2),
                "R_per_yr": round(float(clair.sum()) / YRS, 2),
                "per_year": per_year_sign(clair, years)}
        res[f"f={f:.2f}"] = entry
    return res


def tail_effect(d: pd.DataFrame, rest: pd.DataFrame, r_col: str) -> dict:
    """Disaster class (R <= -1.5), quantified SEPARATELY from the mean effect (pre-reg §5)."""
    act_dis = d[d[r_col] <= DISASTER_R]
    rest_dis = rest[rest[r_col] <= DISASTER_R]
    out = {
        "disaster_threshold_R": DISASTER_R,
        "activated": {"n": int(len(d)), "n_disaster": int(len(act_dis)),
                      "share_pct": round(100.0 * len(act_dis) / max(len(d), 1), 1),
                      "disaster_total_R": round(float(act_dis[r_col].sum()), 2),
                      "worst_R": round(float(d[r_col].min()), 3) if len(d) else None},
        "non_activated": {"n": int(len(rest)), "n_disaster": int(len(rest_dis)),
                          "share_pct": round(100.0 * len(rest_dis) / max(len(rest), 1), 1),
                          "disaster_total_R": round(float(rest_dis[r_col].sum()), 2)},
    }
    out["enrichment_pp"] = round(out["activated"]["share_pct"] - out["non_activated"]["share_pct"], 1)
    out["relief_by_f"] = {
        f"f={f:.2f}": {
            "tail_R_recovered_per_yr": round((1.0 - f) * float(-act_dis[r_col].sum()) / YRS, 2),
            "note": "book-R the disaster class stops costing; the trades still occur and still lose, "
                    "at reduced size — the R LABEL of each trade is unchanged",
        } for f in SIZE_GRID}
    return out


def population_block(d: pd.DataFrame, r_col: str, label: str, clair_col: str | None = None) -> dict:
    act = d[d["activated"]].copy()
    rest = d[~d["activated"]].copy()
    peer_mean = float(rest[r_col].mean())
    blk = {
        "population": label,
        "n_trades": int(len(d)), "span_years": YRS,
        "book_total_R": round(float(d[r_col].sum()), 2),
        "book_R_per_yr": round(float(d[r_col].sum()) / YRS, 2),
        "activation": {
            "n": int(len(act)), "share_pct": round(100.0 * len(act) / max(len(d), 1), 1),
            "per_yr": round(len(act) / YRS, 1),
            "by_year": {int(k): int(v) for k, v in act["entry_date"].dt.year.value_counts().sort_index().items()},
        },
        "cohort_meanR": round(float(act[r_col].mean()), 3) if len(act) else None,
        "peer_meanR": round(peer_mean, 3),
        "measured_gap_R": round(float(act[r_col].mean()) - peer_mean, 3) if len(act) else None,
        "cohort_total_R": round(float(act[r_col].sum()), 2),
        "cohort_is_positive_EV": bool(len(act) and act[r_col].mean() > 0),
    }
    blk["bounds"] = arms(act, r_col, peer_mean, clair_col) if len(act) else {}
    blk["tail"] = tail_effect(act, rest, r_col)
    return blk


def gate(blk: dict) -> dict:
    """Pre-committed §5 gate: arm (b) net >= +10 R/yr AND majority-year sign consistency."""
    out = {}
    for f, e in blk.get("bounds", {}).items():
        for arm in ("b_redeploy_realistic", "b_redeploy_clairvoyant"):
            if arm not in e:
                continue
            v = e[arm]["R_per_yr"]
            maj = e[arm]["per_year"]["majority_sign"] == "+"
            out[f"{f} :: {arm}"] = dict(
                value_R_per_yr=v, clears_floor=bool(v >= FLOOR_R_PER_YR),
                majority_year_positive=bool(maj), PASS=bool(v >= FLOOR_R_PER_YR and maj))
        v = e["a_cash"]["R_per_yr"]
        out[f"{f} :: a_cash"] = dict(
            value_R_per_yr=v, clears_floor=bool(v >= FLOOR_R_PER_YR),
            majority_year_positive=bool(e["a_cash"]["per_year"]["majority_sign"] == "+"),
            PASS=False,
            note="arm (a) cannot pass alone (pre-reg §5): no redeployment, no route to a positive net")
    return out


def main() -> None:
    print("LEDGER: row #15 (running screen count 15; sealed opens 1; n_trials 138 UNTOUCHED).")
    ev = build_event_table(apply_alias_map(pd.read_parquet(EARNINGS_RAW_PATH)))
    evs = event_index(ev)

    # ---------- uncapped queue (for the clairvoyant replacement + the cross-check) ----------
    sub = pd.read_parquet(SUBSTRATE)
    sub = sub[sub["setup"] == "touch44"].copy()
    sub["entry_date"] = pd.to_datetime(sub["entry_date"])
    queue = sub[(sub["entry_date"] >= TRAIN_LO) & (sub["entry_date"] <= TRAIN_HI)]
    best_alt = queue.groupby("entry_date")["R"].max()            # perfect foresight, same week

    # ---------- PRIMARY: capped train book ----------
    cap = pd.read_csv(CAPPED)
    cap["entry_date"] = pd.to_datetime(cap["entry_date"])
    cap = cap[(cap["entry_date"] >= TRAIN_LO) & (cap["entry_date"] <= TRAIN_HI)].copy()
    cap["sig_fri"] = sig_friday(cap["entry_date"])
    cap = activation(cap, evs, "tkr")
    cap["best_alt_R"] = cap["entry_date"].map(best_alt)
    primary = population_block(cap, "R", "capped train book (0094), 2019-01..2024-06",
                               clair_col="best_alt_R")
    primary["gate"] = gate(primary)

    # ---------- CROSS-CHECK: the identical population 0121 used ----------
    ctx = pd.read_parquet(CTX)
    col = {c.lower(): c for c in ctx.columns}
    ctx["entry_date"] = pd.to_datetime(ctx[col["entry_date"]])
    ctx = ctx[(ctx["entry_date"] >= TRAIN_LO) & (ctx["entry_date"] <= TRAIN_HI)].copy()
    ctx["sig_fri"] = sig_friday(ctx["entry_date"])
    ctx = activation(ctx, evs, col["ticker"])
    cross = population_block(ctx, col["r"], "uncapped 0116/0117 substrate (0121's population)")
    cross["gate"] = gate(cross)
    cross["comparison_0121"] = {
        "pure_skip_R_per_yr": -20.96, "deferral_net_R_per_yr": -15.72,
        "clairvoyant_ceiling_R_per_yr": 36.9,
        "note": "0121's numbers on this identical population — sizing is priced against them here",
    }

    # ---------- mechanism note: forward vs trailing event position (descriptive) ----------
    mech = {"capped": trailing_event_share(cap, evs, "tkr"),
            "uncapped": trailing_event_share(ctx, evs, col["ticker"])}

    # ---------- worked example (ILLUSTRATION, explicitly not evidence) ----------
    worked = []
    for t in WORKED_EXAMPLES:
        for src, df, tc, rc in (("capped 0094", cap, "tkr", "R"),
                                ("uncapped substrate", queue, "ticker", "R")):
            g = df[df[tc] == t]
            for _, r in g.iterrows():
                sf = r["sig_fri"] if "sig_fri" in r and pd.notna(r.get("sig_fri")) else \
                    r["entry_date"] - pd.Timedelta(days=int(r["entry_date"].weekday()) + 3)
                a = evs.get(t)
                known = a[a[:, 1] <= np.datetime64(sf)] if a is not None else np.empty((0, 2))
                monday = sf + pd.Timedelta(days=3)
                m = known[(known[:, 0] >= np.datetime64(monday)) &
                          (known[:, 0] <= np.datetime64(monday + pd.Timedelta(days=EVENT_WINDOW_CD)))] \
                    if len(known) else np.empty((0, 2))
                worked.append(dict(
                    ticker=t, source=src, entry_date=str(r["entry_date"].date()),
                    R=round(float(r[rc]), 3),
                    activated=bool(len(m)),
                    event_date=str(pd.Timestamp(m[:, 0].min()).date()) if len(m) else None,
                    announced_on=str(pd.Timestamp(m[m[:, 0] == m[:, 0].min()][0, 1]).date()) if len(m) else None,
                    days_entry_to_event=int((pd.Timestamp(m[:, 0].min()) - monday).days) if len(m) else None,
                ))

    res = {
        "_doc": "0129 event-proximity SIZING activation bound (ledger #15; 0 trials; sealed slice "
                "not read; judge log not read).",
        "prereg": "diagnostics/research/preregistry/0129-eventsize-activation-bound.md",
        "frozen": {"event_window_cd": EVENT_WINDOW_CD, "size_grid": list(SIZE_GRID),
                   "train": [TRAIN_LO, TRAIN_HI], "floor_R_per_yr": FLOOR_R_PER_YR,
                   "imported_from": "0120 Q2 / 0121 — event definition and N re-tuned NOWHERE"},
        "standing_counts": {"screens": 15, "sealed_opens": 1, "n_trials": 138},
        "PRIMARY_capped": primary,
        "CROSSCHECK_uncapped": cross,
        "mechanism_note_event_position": mech,
        "worked_example": {
            "status": "ILLUSTRATION ONLY — a live example for the finding's prose, NOT evidence; "
                      "reported whatever it shows",
            "rows": worked},
    }
    any_pass = any(v.get("PASS") for v in primary["gate"].values()) or \
        any(v.get("PASS") for v in cross["gate"].values())
    res["VERDICT"] = ("PASS — trial #139 may be pre-registered" if any_pass
                      else "FAIL — no trial; record, bank, close")

    OUT_JSON.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")

    md = [
        "# 0129 — Event-proximity SIZING activation bound (ledger #15)",
        "",
        "**0 trials. Sealed slice not read. Judge log unread. No engine change.**",
        "**Standing counts: screens 15 · sealed opens 1 · n_trials 138.**",
        "",
        "Event definition and N=14cd **imported verbatim from 0120/0121** — nothing re-tuned.",
        "Size grid **f ∈ {0.50, 0.75} stated in advance**, evaluated as a bound, not a search.",
        "",
        "## PRIMARY — capped train book",
        "", "```", json.dumps(primary, indent=2, default=str), "```",
        "",
        "## CROSS-CHECK — the uncapped population 0121 used",
        "", "```", json.dumps(cross, indent=2, default=str), "```",
        "",
        "## Mechanism note — forward vs trailing event position (descriptive only)",
        "", "```", json.dumps(mech, indent=2, default=str), "```",
        "",
        "## Worked example (ILLUSTRATION, not evidence)",
        "", "```", json.dumps(res["worked_example"], indent=2, default=str), "```",
        "", f"## VERDICT: {res['VERDICT']}", "",
        "Reproduce: `python scripts/diag_eventsize_bound_0129.py`", "",
    ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    enc = sys.stdout.encoding or "utf-8"
    sys.stdout.write("\n".join(md).encode(enc, "replace").decode(enc, "replace") + "\n")


if __name__ == "__main__":
    main()
