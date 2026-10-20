"""MEASUREMENT (tier 1): live-vs-replay decision diff, as far as it can be done OFFLINE.

A faithful same-week replay is NOT possible here: the pinned price cache ends 2026-06-29 and every
published week is >= 2026-07-04; the 44-week lookback of any 2026-07+ signal also lies in the sealed
2024-07-01..2026-06-30 window, which this work may not read. So this script does what the published record
and the committed corporate-action metadata allow (no price series is read at all):

  A. Arithmetic recompute of every published card's levels from its own published fields (stop rule,
     2R target, extension vs the 44w SMA, buy-zone/no-chase geometry), and cross-archive consistency:
     same (ticker, signal_date) must carry the same entry/stop/target in every later snapshot; rerun
     snapshots must equal the snapshot they re-ran; FRESH published entry vs the modeled fill later held.
  B. Corporate-action exposure of every published card and held position inside its 44-week lookback
     (nse census layer2_passA + corpactions_raw dividends/rights + post-harvest addendum + KNOWN_SEAMS),
     with an analytic estimate of how a user on unadjusted (Kite) prices would see SMA44 / extension / the
     stop differ from the dividend-adjusted engine history. The census ends 2026-07-01, so the live window
     is covered only by a close-to-close break detector on the published record.

    python pipelines/diagnostics/diag_live_decision_diff.py
"""
from __future__ import annotations

import glob
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

LIVE_START = pd.Timestamp("2026-07-04")
LOOKBACK_D = 44 * 7
AUDIT = ROOT / "diagnostics" / "research" / "foundation_audit_2026Q3"
OUT = ROOT / "diagnostics" / "research" / "engine_assumptions" / "live_decision_diff.json"
CENSUS_END = pd.Timestamp("2026-07-01")
BREAK_TOL = 0.25            # week-over-week close ratio break flagged as a possible unregistered corporate action


def load_archives() -> dict:
    out = {}
    for f in sorted(glob.glob(str(ROOT / "results" / "archive" / "*" / "signals_today_weekly.json"))):
        name = Path(f).parent.name
        as_of = pd.Timestamp(name[:10])
        if as_of < LIVE_START:
            continue
        sig = json.load(open(f, encoding="utf-8"))
        pf = Path(f).parent / "paper_portfolio_weekly.json"
        pos = json.load(open(pf, encoding="utf-8")).get("positions", {}) if pf.exists() else {}
        out[name] = {"as_of": as_of, "rerun": "__rerun" in name, "signals": sig["signals"], "positions": pos}
    return out


def sma_from_card(c: dict) -> float | None:
    for t in (c.get("exit_plan") or {}).get("tranches", []):
        if t.get("type") == "runner":
            return t.get("level")
    return None


# ── A. arithmetic + cross-archive ───────────────────────────────────────────────────────────────
def check_card(c: dict) -> dict:
    e, s, tg = c["entry"], c["stop"], c["target"]
    r = e - s
    res = {"ticker": c["ticker"], "status": c["status"], "signal_date": c["signal_date"]}
    res["target_err"] = round(tg - (e + 2 * r), 2)                   # 2R target
    res["stop_pct"] = round(r / e * 100, 2)
    swl = c.get("stop_week_low")
    if swl is not None:
        res["stop_rule_err"] = round(s - max(swl, 0.9 * e), 2)       # stop = max(signal-week low, entry - 10%)
    sma = sma_from_card(c)
    if sma and c.get("ext_pct_over_sma44") is not None:
        res["ext_err_pp"] = round((e / sma - 1) * 100 - c["ext_pct_over_sma44"], 2)
        res["over_cap"] = bool(c["ext_pct_over_sma44"] > (c.get("ext_cap_pct") or 1e9) and not c.get("record_would_skip_as_extended"))
    if c.get("no_chase_above") is not None and c.get("buy_zone_high"):
        res["no_chase_ratio"] = round(c["no_chase_above"] / c["buy_zone_high"], 4)
    return res


def part_a(arch: dict) -> dict:
    checks, tol = [], 0.05            # 2-dp rounding of entry/stop/target
    for name, a in arch.items():
        for c in a["signals"]:
            ch = check_card(c); ch["archive"] = name; checks.append(ch)
    df = pd.DataFrame(checks)
    bad_t = df[df.target_err.abs() > tol]
    bad_s = df[df.get("stop_rule_err", pd.Series(dtype=float)).abs() > tol] if "stop_rule_err" in df else df.iloc[0:0]
    bad_e = df[df.get("ext_err_pp", pd.Series(dtype=float)).abs() > 0.06] if "ext_err_pp" in df else df.iloc[0:0]
    over = df[df.get("over_cap", pd.Series(dtype=object)).eq(True)] if "over_cap" in df else df.iloc[0:0]
    # persistence: same (ticker, signal_date) across non-rerun snapshots must not restate its levels
    seen: dict = defaultdict(dict)
    for name, a in arch.items():
        if a["rerun"]:
            continue
        for c in a["signals"]:
            if c["status"] != "FRESH":          # ACTIVE/HIT_*: signal_date is the modeled FILL date
                seen[(c["ticker"], c["signal_date"])][name] = (c["entry"], c["stop"], c["target"], c["grade"])
    restated = []
    for key, snaps in seen.items():
        vals = list(snaps.items())
        for (n0, t0), (n1, t1) in zip(vals, vals[1:]):
            if t0 != t1:
                restated.append({"key": list(key), "from_snapshot": n0, "to_snapshot": n1, "was": t0, "now": t1,
                                 "entry_delta_pct": round((t1[0] / t0[0] - 1) * 100, 2),
                                 "stop_delta_pct": round((t1[1] / t0[1] - 1) * 100, 2)})
    rs = pd.DataFrame(restated)
    # rerun vs its original: set, levels, grade
    rerun_diff = []
    for name, a in arch.items():
        if not a["rerun"]:
            continue
        base = arch.get(name[:10])
        if base is None:
            continue
        b = {(c["ticker"], c["signal_date"]): c for c in base["signals"]}
        r = {(c["ticker"], c["signal_date"]): c for c in a["signals"]}
        lvl = [k for k in b.keys() & r.keys() if (b[k]["entry"], b[k]["stop"], b[k]["target"], b[k]["grade"]) !=
               (r[k]["entry"], r[k]["stop"], r[k]["target"], r[k]["grade"])]
        rerun_diff.append({"rerun": name, "base": name[:10], "only_in_base": sorted(map(list, b.keys() - r.keys())),
                           "only_in_rerun": sorted(map(list, r.keys() - b.keys())), "level_or_grade_changed": sorted(map(list, lvl))})
    # FRESH published entry vs the modeled fill later carried by the held position
    fills = []
    first_fresh = {}
    for name, a in arch.items():
        if a["rerun"]:
            continue
        for c in a["signals"]:
            if c["status"] == "FRESH":
                first_fresh.setdefault((c["ticker"], c["signal_date"]), c)
    done: set = set()
    for name, a in arch.items():
        if a["rerun"]:
            continue
        for c in a["signals"]:
            if c["status"] == "FRESH" or (c["ticker"], c["signal_date"]) in done:
                continue
            fd = pd.Timestamp(c["signal_date"])
            cand = [f for (t, d), f in first_fresh.items() if t == c["ticker"] and 0 < (fd - pd.Timestamp(d)).days <= 7]
            if not cand:
                continue
            f = cand[0]
            done.add((c["ticker"], c["signal_date"]))
            fills.append({"key": [c["ticker"], f["signal_date"], c["signal_date"]], "pub_entry": f["entry"], "pub_stop": f["stop"],
                          "fill_entry": c["entry"], "fill_stop": c["stop"],
                          "entry_slip_pct": round((c["entry"] / f["entry"] - 1) * 100, 2),
                          "risk_pct_pub": round((f["entry"] - f["stop"]) / f["entry"] * 100, 2),
                          "risk_pct_fill": round((c["entry"] - c["stop"]) / c["entry"] * 100, 2),
                          "above_no_chase": bool(f.get("no_chase_above") and c["entry"] > f["no_chase_above"]),
                          "outside_band": bool(f.get("entry_high") and c["entry"] > f["entry_high"] * 1.0005)})
    fl = pd.DataFrame(fills)
    return {"n_snapshots": len(arch), "n_card_rows": int(len(df)), "n_distinct_cards": int(df[["ticker", "signal_date"]].drop_duplicates().shape[0]),
            "n_fresh_rows": int((df.status == "FRESH").sum()),
            "target_not_2R": {"n": int(len(bad_t)), "rows": bad_t[["archive", "ticker", "target_err"]].head(10).to_dict("records")},
            "stop_rule_mismatch": {"n": int(len(bad_s)), "rows": bad_s[["archive", "ticker", "stop_rule_err"]].head(10).to_dict("records")},
            "ext_pct_mismatch": {"n": int(len(bad_e)), "rows": bad_e[["archive", "ticker", "ext_err_pp"]].head(10).to_dict("records")},
            "fresh_over_ext_cap_not_flagged": {"n": int(len(over)), "rows": over[["archive", "ticker"]].head(10).to_dict("records")},
            "levels_restated_across_snapshots": {
                "n": len(restated), "n_positions": int(len({tuple(r["key"]) for r in restated})),
                "by_snapshot_pair": rs.groupby(["from_snapshot", "to_snapshot"]).size().reset_index(name="n").to_dict("records") if len(rs) else [],
                "entry_delta_pct_abs_max": float(rs.entry_delta_pct.abs().max()) if len(rs) else None,
                "entry_delta_pct_abs_median": float(rs.entry_delta_pct.abs().median()) if len(rs) else None,
                "rows": restated[:12]},
            "rerun_vs_original": rerun_diff,
            "published_vs_fill": {"n": int(len(fl)),
                                  "entry_slip_pct_mean": float(fl.entry_slip_pct.mean()) if len(fl) else None,
                                  "entry_slip_pct_min_max": [float(fl.entry_slip_pct.min()), float(fl.entry_slip_pct.max())] if len(fl) else None,
                                  "risk_pct_pub_mean": float(fl.risk_pct_pub.mean()) if len(fl) else None,
                                  "risk_pct_fill_mean": float(fl.risk_pct_fill.mean()) if len(fl) else None,
                                  "n_fill_above_no_chase": int(fl.above_no_chase.sum()) if len(fl) else 0,
                                  "n_fill_outside_band": int(fl.outside_band.sum()) if len(fl) else 0,
                                  "worst": fl.reindex(fl.entry_slip_pct.abs().sort_values(ascending=False).index).head(8).to_dict("records") if len(fl) else []},
            "stop_pct_distribution": {"min": float(df.stop_pct.min()), "median": float(df.stop_pct.median()), "max": float(df.stop_pct.max())}}


# ── B. corporate-action exposure ─────────────────────────────────────────────────────────────────
def load_events() -> pd.DataFrame:
    rows = []
    pa = pd.read_parquet(AUDIT / "layer2_passA.parquet")
    for r in pa.itertuples():
        f = float(r.implied_factor) if r.resolution in ("CORRECTLY_ADJUSTED", "DEFECT_MISSCALED", "CONVENTION_DEMERGER_BACKADJUSTED") else 1.0
        rows.append(dict(symbol=r.symbol, ex=pd.Timestamp(r.ex_date), kind=r.kind, subject=r.subject, factor=f,
                         exch_factor=float(r.expected_factor), resolution=r.resolution, src="layer2_passA"))
    raw = pd.read_parquet(AUDIT / "corpactions_raw.parquet")
    raw["ex"] = pd.to_datetime(raw["exDate"], errors="coerce")
    for r in raw.dropna(subset=["ex"]).itertuples():
        s = str(r.subject)
        amts = re.findall(r"(?:rs\.?|re\.?|inr)\s*(\d+(?:\.\d+)?)", s, re.I)
        if "dividend" in s.lower() and amts:
            rows.append(dict(symbol=r.symbol, ex=r.ex, kind="dividend", subject=s, factor=np.nan, amount=float(sum(map(float, amts))),
                             resolution="VENDOR_ADJUSTED_ASSUMED", src="corpactions_raw"))
        elif re.search(r"rights", s, re.I):
            rows.append(dict(symbol=r.symbol, ex=r.ex, kind="rights", subject=s, factor=np.nan, resolution="SEE_KNOWN_SEAMS", src="corpactions_raw"))
    ph = pd.read_csv(ROOT / "data" / "corporate_actions_post_harvest.csv", comment="#")
    for r in ph.itertuples():
        rows.append(dict(symbol=r.symbol, ex=pd.Timestamp(r.ex_date), kind=r.kind, subject=r.subject, factor=float(r.implied_factor),
                         resolution=r.resolution, src="post_harvest"))
    return pd.DataFrame(rows)


def exposure(ticker: str, as_of: pd.Timestamp, ref_px: float, ev: pd.DataFrame, seams: dict, since: pd.Timestamp | None = None) -> list[dict]:
    lo = as_of - pd.Timedelta(days=LOOKBACK_D)
    e = ev[(ev.symbol == ticker) & (ev.ex > lo) & (ev.ex <= as_of)].copy()
    out = []
    adj = e[(~e.kind.isin(["dividend", "rights"])) & e.factor.notna()]
    for r in e.itertuples():
        f = r.factor
        if r.kind == "dividend":
            later = float(np.prod([x for x, d in zip(adj.factor, adj.ex) if d > r.ex] or [1.0]))
            f = 1 + r.amount / (ref_px * later) if ref_px else 1.0   # dividend / price AT the ex-date, not today's
        out.append({"ex": str(r.ex.date()), "kind": r.kind, "subject": r.subject[:60], "factor": None if f != f else round(float(f), 5), "resolution": r.resolution})
    for (sym, d), v in seams.items():
        if sym == ticker and pd.Timestamp(d) > lo - pd.Timedelta(days=0) and pd.Timestamp(d) <= as_of and v["provenance"] != "known-erratum":
            out.append({"ex": d, "kind": "KNOWN_SEAM", "subject": v["cause"][:60], "factor": v["factor"], "resolution": v["provenance"]})
    return out


def sma_ratio_raw_over_adj(evs: list[dict], as_of: pd.Timestamp, seams_only: bool = False) -> float:
    """Flat-price estimate of SMA44(raw closes)/SMA44(adjusted closes): a week ending before an adjusting event's
    ex-date has raw = adjusted x (product of the factors of the events still ahead of it)."""
    wk_end = [as_of - pd.Timedelta(days=7 * k) for k in range(43, -1, -1)]
    sc = np.ones(44)
    for ev in evs:
        is_seam = ev["kind"] == "KNOWN_SEAM"
        if seams_only != is_seam:           # seams_only: engine-vs-true distortion bound; else raw-vs-adjusted
            continue
        if ev["factor"] and ev["resolution"] not in ("LEFT_UNADJUSTED_AS_INTENDED", "LEFT_AS_CLIFF"):
            sc *= np.where(np.array(wk_end) < pd.Timestamp(ev["ex"]), ev["factor"], 1.0)
    return float(sc.mean())


def part_b(arch: dict) -> dict:
    from nq.data.adjustment_guard import KNOWN_SEAMS
    ev = load_events()
    rows = []
    # one observation per (ticker, role, snapshot) using non-rerun snapshots
    for name, a in arch.items():
        if a["rerun"]:
            continue
        for c in a["signals"]:
            role = "FRESH" if c["status"] == "FRESH" else "HELD"
            px = c.get("close") or c["entry"]
            evs = exposure(c["ticker"], a["as_of"], px, ev, KNOWN_SEAMS)
            sma = sma_from_card(c)
            row = {"snapshot": name, "ticker": c["ticker"], "role": role, "status": c["status"], "signal_date": c["signal_date"],
                   "n_events": len(evs), "events": evs, "census_blind_weeks": round(max(0, (a["as_of"] - CENSUS_END).days) / 7, 1)}
            if any(e["kind"] == "KNOWN_SEAM" for e in evs):
                row["seam_sma_error_bound"] = round(sma_ratio_raw_over_adj(evs, a["as_of"], seams_only=True), 4)
            if evs:
                rr = sma_ratio_raw_over_adj(evs, a["as_of"])
                row["sma44_raw_over_adj"] = round(rr, 4)
                if role == "FRESH" and sma and c.get("ext_pct_over_sma44") is not None:
                    ext_adj = c["ext_pct_over_sma44"]
                    ext_raw = (c["entry"] / (sma * rr) - 1) * 100
                    row.update(ext_adj=ext_adj, ext_raw_est=round(ext_raw, 2), ext_shift_pp=round(ext_raw - ext_adj, 2),
                               cap_flips=bool((ext_adj <= c.get("ext_cap_pct", 20)) != (ext_raw <= c.get("ext_cap_pct", 20))))
                # ex-date inside the signal week (would move entry/stop levels themselves)
                row["event_in_signal_week"] = any(0 <= (a["as_of"] - pd.Timestamp(e["ex"])).days <= 7 for e in evs)
                # ex-date during the hold (a fixed Kite stop would not be rescaled)
                row["event_during_hold"] = any(pd.Timestamp(e["ex"]) >= pd.Timestamp(c["signal_date"]) for e in evs)
            rows.append(row)
    df = pd.DataFrame(rows)
    exp = df[df.n_events > 0]

    def summ(sub: pd.DataFrame) -> dict:
        d = sub.drop_duplicates(["ticker", "role", "signal_date"])
        return {"observations": int(len(sub)), "distinct_ticker_signals": int(len(d)), "with_ca_in_lookback": int((d.n_events > 0).sum()),
                "share": round(float((d.n_events > 0).mean()), 3) if len(d) else None}

    fresh = df[df.role == "FRESH"]; held = df[df.role == "HELD"]
    by_kind: dict = defaultdict(int)
    for r in exp.drop_duplicates(["ticker", "role", "signal_date"]).itertuples():
        for k in {e["kind"] for e in r.events}:
            by_kind[k] += 1
    fe = fresh[fresh.n_events > 0].drop_duplicates(["ticker", "signal_date"])
    worst_ext = fe.dropna(subset=["ext_shift_pp"]).reindex(fe.dropna(subset=["ext_shift_pp"]).ext_shift_pp.abs().sort_values(ascending=False).index).head(10)
    worst_sma = exp.drop_duplicates(["ticker", "signal_date"]).assign(a=lambda x: (x.sma44_raw_over_adj - 1).abs()).sort_values("a", ascending=False).head(10)
    cols = ["snapshot", "ticker", "role", "sma44_raw_over_adj", "ext_adj", "ext_raw_est", "ext_shift_pp", "cap_flips"]

    # live-window break detector on the published record (covers the census-blind weeks)
    series: dict = defaultdict(dict)
    for name, a in arch.items():
        if a["rerun"]:
            continue
        for c in a["signals"]:
            if c["status"] in ("ACTIVE", "HIT_STOP", "HIT_TARGET") and c.get("close"):
                series[c["ticker"]][a["as_of"]] = c["close"]
    breaks = []
    for t, s in series.items():
        ks = sorted(s)
        for p, q in zip(ks, ks[1:]):
            r = s[q] / s[p]
            if abs(r - 1) > BREAK_TOL:
                breaks.append({"ticker": t, "from": str(p.date()), "to": str(q.date()), "close_from": s[p], "close_to": s[q], "ratio": round(r, 3)})
    pos_status = defaultdict(int)
    for name, a in arch.items():
        if not a["rerun"]:
            for c in a["signals"]:
                pos_status[c["status"]] += 1
    return {"events_loaded": {"layer2_passA_max_ex": str(pd.read_parquet(AUDIT / 'layer2_passA.parquet').ex_date.max()),
                              "n_events": int(len(ev)), "by_kind": ev.kind.value_counts().to_dict(), "census_end": str(CENSUS_END.date())},
            "fresh": summ(fresh), "held": summ(held), "events_by_kind_distinct_signals": dict(by_kind),
            "fresh_event_in_signal_week": int(fresh[fresh.get("event_in_signal_week", False) == True].drop_duplicates(["ticker", "signal_date"]).shape[0]) if "event_in_signal_week" in fresh else 0,
            "held_event_during_hold": int(held[held.get("event_during_hold", False) == True].drop_duplicates(["ticker", "signal_date"]).shape[0]) if "event_during_hold" in held else 0,
            "fresh_cap_flips_if_raw": int(fe["cap_flips"].fillna(False).sum()) if "cap_flips" in fe else 0,
            "fresh_ext_shift_pp_abs_max": float(fe.ext_shift_pp.abs().max()) if "ext_shift_pp" in fe and fe.ext_shift_pp.notna().any() else None,
            "worst_ext_shift": worst_ext[[c for c in cols if c in worst_ext]].to_dict("records"),
            "worst_sma_distortion_any_role": worst_sma[[c for c in cols if c in worst_sma] + ["events"]].to_dict("records"),
            "live_window_close_breaks_gt25pct": breaks,
            "n_rows_with_known_seam_in_lookback": int(df["seam_sma_error_bound"].notna().sum()) if "seam_sma_error_bound" in df else 0,
            "exposure_rows": json.loads(exp.drop(columns=[c for c in ("census_blind_weeks",) if c in exp]).to_json(orient="records")),
            "status_row_counts": dict(pos_status)}


def main() -> int:
    arch = load_archives()
    res = {"label": "MEASUREMENT (tier 1); no price series read", "snapshots": sorted(arch),
           "A_levels_and_consistency": part_a(arch), "B_corporate_action_exposure": part_b(arch)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    a, b = res["A_levels_and_consistency"], res["B_corporate_action_exposure"]
    print("snapshots", len(arch), "rows", a["n_card_rows"], "distinct", a["n_distinct_cards"], "fresh rows", a["n_fresh_rows"])
    for k in ("target_not_2R", "stop_rule_mismatch", "ext_pct_mismatch", "fresh_over_ext_cap_not_flagged", "levels_restated_across_snapshots"):
        print(" ", k, a[k]["n"], a[k]["rows"][:3])
    print("  rerun diffs", [(r["rerun"], len(r["only_in_base"]), len(r["only_in_rerun"]), len(r["level_or_grade_changed"])) for r in a["rerun_vs_original"]])
    print("  published_vs_fill", {k: v for k, v in a["published_vs_fill"].items() if k != "worst"})
    print("B fresh", b["fresh"], "held", b["held"], "kinds", b["events_by_kind_distinct_signals"])
    print("  signal-week events", b["fresh_event_in_signal_week"], "hold events", b["held_event_during_hold"], "cap flips", b["fresh_cap_flips_if_raw"],
          "max |ext shift| pp", b["fresh_ext_shift_pp_abs_max"])
    for w in b["worst_ext_shift"][:6]:
        print("   ext", w)
    for w in b["worst_sma_distortion_any_role"][:6]:
        print("   sma", {k: v for k, v in w.items() if k != "events"}, [(e["ex"], e["kind"], e["factor"]) for e in w["events"]][:4])
    print("  breaks", b["live_window_close_breaks_gt25pct"])
    print("->", OUT.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
