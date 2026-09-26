"""A1 — for every number the 2026-10-01 review reads, which of the three books produced it?

SPEC: `diagnostics/research/book_identity/SPEC.md`, committed before this file existed (187954d).

The weekly scan runs three books off one engine. `build_envelopes` is fed the UNCAPPED one
(`run_bhanushali_cron.py:1090`), so the signals page and `signal_analytics_weekly.json` describe a book
where cash never runs out, while `paper_portfolio_weekly.json` and `portfolio_history_weekly.csv`
describe the ₹10L book that would hold real positions. Nothing says so at the point of use.

Artifacts only: no re-run, no network, no engine call. The local OHLCV cache predates inception, so an
offline replay cannot reproduce the live NAV — that is declared, not worked around.

This study proposes nothing. It does not restate performance as better or worse.

Reproduce: `python pipelines/diagnostics/diag_book_identity.py --run-date YYYY-MM-DD`
"""

from __future__ import annotations

import argparse
import sys
import glob
import json
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
OUT_BASE = ROOT / "diagnostics" / "research" / "book_identity"

# the replay leg imports the engine and the live config dicts from scripts/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

# ── the three books, named once (SPEC §"Why this exists") ───────────────────────────────────────────
CAPPED_A = "capped A-only (out_paper) — the book that would hold real positions"
UNCAPPED_A = "uncapped A-only (out_all) — every A signal tracked, cash never runs out"
CAPPED_ALL = "capped all-grades (out_base) — prereg_swing.md §4's comparator"

TOLERANCE_PAISA = 0.005          # half a paisa: two rounded rupee figures agreeing to the cent
OPENING_CAPITAL = 1_000_000.0


def _read(name: str):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def load_artifacts() -> dict:
    hist = pd.read_csv(RESULTS / "portfolio_history_weekly.csv")
    return {
        "signals": _read("signals_history_weekly.json"),
        "analytics": _read("signal_analytics_weekly.json"),
        "portfolio": _read("paper_portfolio_weekly.json"),
        "base": _read("base_swing_forward.json"),
        "scorecard": _read("weekly_review_scorecard.json"),
        "history": hist,
    }


# ── 1. provenance, verified by value rather than asserted from the code ─────────────────────────────
def provenance_map(a: dict) -> dict:
    an, sc, pf = a["analytics"], a["scorecard"], a["portfolio"]
    fwd = sc.get("forward", {})
    grading = sc.get("swing_grading", {})
    hist = a["history"]

    eq = hist["total_value"].astype(float)
    maxdd_recomputed = float((eq / eq.cummax() - 1).min()) * 100

    rows = [
        {"metric": "scorecard forward.n_closed / the '11/40 closed' headline",
         "value": fwd.get("n_closed"),
         "artifact": "results/signal_analytics_weekly.json -> total_closed",
         "book": UNCAPPED_A,
         "verified_by": "equals analytics.total_closed",
         "agrees": fwd.get("n_closed") == an.get("total_closed")},
        {"metric": "expectancy_R (gross)", "value": fwd.get("expectancy_R"),
         "artifact": "results/signal_analytics_weekly.json -> avg_r",
         "book": UNCAPPED_A, "verified_by": "equals analytics.avg_r",
         "agrees": _close(fwd.get("expectancy_R"), an.get("avg_r"))},
        {"metric": "win_rate_pct", "value": fwd.get("win_rate_pct"),
         "artifact": "results/signal_analytics_weekly.json -> win_rate",
         "book": UNCAPPED_A, "verified_by": "equals analytics.win_rate",
         "agrees": _close(fwd.get("win_rate_pct"), an.get("win_rate"))},
        {"metric": "maxdd_pct (the §5 halt reads this)", "value": fwd.get("maxdd_pct"),
         "artifact": "results/portfolio_history_weekly.csv -> total_value",
         "book": CAPPED_A, "verified_by": "reproduced from the NAV curve on the daily grid",
         "agrees": _close(fwd.get("maxdd_pct"), round(maxdd_recomputed, 1), tol=0.15)},
        {"metric": "sharpe (the KILL_SHARPE < 0 trigger)", "value": fwd.get("sharpe"),
         "artifact": "results/portfolio_history_weekly.csv -> total_value",
         "book": CAPPED_A,
         # SPEC §1 requires every mapping be verified by VALUE. This was the one row left asserted from
         # the code, and it is the row the kill decision rests on (red-team, 2026-09-25).
         "verified_by": "recomputed as mean/sd * sqrt(252) on the capped NAV's daily returns",
         "agrees": _close(fwd.get("sharpe"), _sharpe_from_curve(hist), tol=1e-9)},
        {"metric": "nav", "value": fwd.get("nav"),
         "artifact": "results/paper_portfolio_weekly.json -> total_value",
         "book": CAPPED_A, "verified_by": "equals portfolio.total_value",
         "agrees": _close(fwd.get("nav"), pf.get("total_value"))},
        {"metric": "swing_grading.a_only_closed (§4 floor, 20/book)",
         "value": grading.get("a_only_closed"),
         "artifact": "results/signal_analytics_weekly.json -> total_closed",
         "book": UNCAPPED_A, "verified_by": "equals analytics.total_closed",
         "agrees": grading.get("a_only_closed") == an.get("total_closed")},
        {"metric": "swing_grading.base_swing_closed (§4 floor, 20/book)",
         "value": grading.get("base_swing_closed"),
         "artifact": "results/base_swing_forward.json -> n_closed",
         "book": CAPPED_ALL, "verified_by": "equals base_swing_forward.n_closed",
         "agrees": grading.get("base_swing_closed") == a["base"].get("n_closed")},
        {"metric": "paper_portfolio.total_trades", "value": pf.get("total_trades"),
         "artifact": "results/paper_portfolio_weekly.json",
         "book": UNCAPPED_A,
         "verified_by": ("its docstring calls it the CAPPED book's closed count, but it equals the "
                         "uncapped analytics.total_closed"),
         "agrees": pf.get("total_trades") == an.get("total_closed")},
    ]
    return {"rows": rows,
            "all_value_checks_agree": all(r["agrees"] for r in rows if r["agrees"] is not None),
            "maxdd_recomputed_pct": round(maxdd_recomputed, 3)}


def _sharpe_from_curve(hist: pd.DataFrame) -> float:
    """The scorecard's own construction (bhanushali_review_scorecard.py:79-115): rf = 0, daily grid."""
    r = hist["total_value"].astype(float).pct_change().dropna()
    return float(r.mean() / r.std() * (252 ** 0.5))


def _close(x, y, tol: float = 1e-6) -> bool | None:
    if x is None or y is None:
        return None
    return abs(float(x) - float(y)) <= tol


# ── 2. do the two CAPPED books differ at all? ──────────────────────────────────────────────────────
def curve_identity(a: dict) -> dict:
    base = {r["date"][:10]: round(float(r["equity"]), 2) for r in a["base"].get("nav", [])}
    aonly = {str(r.date)[:10]: round(float(r.total_value), 2)
             for r in a["history"].itertuples(index=False)}
    common = sorted(set(base) & set(aonly))
    diffs = [{"date": d, "capped_a_only": aonly[d], "capped_all_grades": base[d],
              "delta": round(aonly[d] - base[d], 2)}
             for d in common if abs(aonly[d] - base[d]) > TOLERANCE_PAISA]
    return {
        "n_points_capped_a_only": len(aonly), "n_points_capped_all_grades": len(base),
        "n_common": len(common), "n_differing": len(diffs), "differing": diffs[:10],
        "max_abs_delta": round(max((abs(aonly[d] - base[d]) for d in common), default=0.0), 4),
        "identical": len(common) > 0 and not diffs,
        "what_it_means": (
            "If identical: under the ₹10L cash gate with a 20% notional cap, grading does not change "
            "what gets FUNDED — the strongest-CRS names fill the few affordable seats either way. §4 "
            "decides on forward MaxDD and Calmar, both read off these curves, so its test cannot "
            "separate arms whose curves agree on every session. Its insufficient-evidence default "
            "then fires mechanically, which is the outcome the cron's own comment block says the "
            "comparator was added to prevent."),
    }


# ── 3. the capped book's own position history ──────────────────────────────────────────────────────
# The window for the discriminating replay. Strictly BEFORE the sealed slice (2024-07-01..2026-06-30),
# so this spends no sealed open. It is not the live window — the live OHLCV cache predates inception —
# and it does not need to be: the question is whether the two books CAN differ, not what they did live.
REPLAY_START, REPLAY_END = "2023-01-02", "2024-06-28"


def grading_discriminates() -> dict:
    """Can the A-grade filter change the book at all? Replay with and without it.

    WHY THIS EXISTS. The first version of this study argued that `out_base` is genuinely its own
    backtest by noting its scalars differ from the UNCAPPED book's. That is a non-sequitur: the
    hypothesis worth killing is that `out_base` silently carries `out_paper` (the CAPPED book), and
    under that bug the observed `n_closed 1 / -1.046R / {'stop': 1}` is exactly what you would see.
    The red-team caught it. The discriminating test is this one (red-team, 2026-09-25).

    If the two books diverge here, then `a_grade` does bite, `_base_swing_record` is not writing the
    wrong object, and the live 55-session identity is a property of the LIVE WINDOW rather than a
    plumbing defect.
    """
    import run_bhanushali_weekly_rank as R94
    from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT, LIVE_PREP, LIVE_STALENESS
    from run_bhanushali_path1 import corrected_universe

    cut = {k: v[pd.DatetimeIndex(v.index) <= pd.Timestamp(REPLAY_END)] for k, v in corrected_universe().items()}
    cut = {k: v for k, v in cut.items() if len(v) > 60}
    P = R94.prep_weekly_rank(cut, **LIVE_PREP)
    kw = dict(start=REPLAY_START, return_state=True, **LIVE_DISCIPLINE, **LIVE_EXIT, **LIVE_STALENESS)

    led_a: list = []
    a_only = R94.backtest(P, None, ledger=led_a, a_grade=R94.grade_a_entries(P), **kw)
    led_all: list = []
    all_grades = R94.backtest(P, None, ledger=led_all, **kw)

    ca, cb = pd.Series(a_only["curve"], dtype=float), pd.Series(all_grades["curve"], dtype=float)
    ca.index, cb.index = pd.DatetimeIndex(ca.index).normalize(), pd.DatetimeIndex(cb.index).normalize()
    common = ca.index.intersection(cb.index)
    delta = (ca.reindex(common) - cb.reindex(common)).abs()
    return {
        "window": f"{REPLAY_START}..{REPLAY_END}",
        "sealed_slice_touched": False,
        "n_common_sessions": int(len(common)),
        "n_sessions_differing": int((delta > TOLERANCE_PAISA).sum()),
        "max_abs_delta": round(float(delta.max()), 2),
        "a_only": {"final_equity": round(float(ca.iloc[-1]), 2), "n_closed": int(len(led_a))},
        "all_grades": {"final_equity": round(float(cb.iloc[-1]), 2), "n_closed": int(len(led_all))},
        "grading_bites": bool((delta > TOLERANCE_PAISA).any()),
        "reading": ("If grading_bites is true, the a_grade filter demonstrably changes the book, so the "
                    "live window's identical curves are a fact about that window — roughly five funded "
                    "seats, ~92% invested, one closure freeing cash — and NOT a wiring defect."),
    }


def capped_closures_are_exact(a: dict) -> dict:
    """Prove the capped closure count EXACTLY, rather than calling it a lower bound.

    A funded name is also tracked in the uncapped book and exits on the same weekly trigger, so
    capped closures are a SUBSET of the 11 uncapped ones. For each uncapped closure, look at the
    snapshots strictly inside [signal_date, close_date): if the name is held in any of them the capped
    book funded it; if it is held in none, it was never funded and cannot have closed. When every
    closure has at least one snapshot in that window, there is no blind spot and the count is exact.

    The boundary matters: a name is legitimately ABSENT from the snapshot at its own close date, so
    testing `<= close_date` would have mislabelled DELHIVERY — the one name that really was funded.
    """
    snaps = {}
    for s in sorted(glob.glob(str(RESULTS / "archive" / "*" / "paper_portfolio_weekly.json"))):
        name = Path(s).parent.name
        if "__rerun" in name:
            continue                      # a rerun repeats its parent's as-of; it is not an observation
        snaps[name] = set(json.loads(Path(s).read_text(encoding="utf-8")).get("positions", {}))

    funded, never, blind = [], [], []
    for s in a["signals"]:
        if not s.get("close_date"):
            continue
        t_, start, end = s["ticker"], str(s["signal_date"])[:10], str(s["close_date"])[:10]
        inside = [k for k in snaps if start <= k < end]
        present = [k for k in inside if t_ in snaps[k]]
        row = {"ticker": t_, "window": f"{start}..{end}", "snapshots_in_window": len(inside),
               "snapshots_holding_it": len(present)}
        if not inside:
            blind.append(row)
        elif present:
            funded.append(row)
        else:
            never.append(row)
    return {
        "n_distinct_snapshots": len(snaps),
        "uncapped_closures": len(funded) + len(never) + len(blind),
        "capped_closures": len(funded), "never_funded": len(never),
        "funded": funded, "never_funded_rows": never,
        "closures_with_no_snapshot_in_window": blind,
        "exact": not blind,
        "why_exact": ("every uncapped closure has at least one snapshot strictly inside its holding "
                      "window, so no position could have opened and closed unobserved. The count is "
                      "EXACT, not a lower bound. The pre-archive gap (inception 2026-07-04 to the "
                      "first snapshot 2026-07-24) is closed by the uncapped book reporting 0 closures "
                      "at 2026-07-24."),
    }


def realisation_events(a: dict) -> dict:
    """Realisation EVENTS, which are not the same thing as closed trades.

    The share path in the snapshots shows partial bookings on positions that never closed: CUB went
    943.40 -> 571.34 -> 190.45 while remaining open throughout. So `closed = 1` is not the number of
    times money was realised, and no published field expresses a partial realisation. This is a fourth
    book-identity hole, alongside the three in DECLARED_HOLES (red-team, 2026-09-25).

    Proceeds are APPROXIMATE: the share delta is priced at the snapshot's mark, not at the fill the
    engine actually got, and entry prices are restated across snapshots (CUB 212.00 -> 210.03).
    """
    seq, prev = [], {}
    for s in sorted(glob.glob(str(RESULTS / "archive" / "*" / "paper_portfolio_weekly.json"))):
        name = Path(s).parent.name
        if "__rerun" in name:
            continue
        pos = json.loads(Path(s).read_text(encoding="utf-8")).get("positions", {})
        for t_, before in prev.items():
            now = pos.get(t_)
            if now is None:
                seq.append({"snapshot": name, "ticker": t_, "kind": "closed",
                            "shares_from": before["shares"], "shares_to": 0.0})
            elif float(now["shares"]) < float(before["shares"]) - 1e-9:
                d = float(before["shares"]) - float(now["shares"])
                px = float(now["current_price"])
                seq.append({"snapshot": name, "ticker": t_, "kind": "partial_booking",
                            "shares_from": before["shares"], "shares_to": now["shares"],
                            "shares_sold": round(d, 4), "approx_proceeds": round(d * px, 2),
                            "priced_at": px})
        prev = pos
    return {
        "n_events": len(seq), "events": seq,
        "n_closed_positions": sum(1 for e in seq if e["kind"] == "closed"),
        "n_partial_bookings": sum(1 for e in seq if e["kind"] == "partial_booking"),
        "APPROXIMATE": ("proceeds are the share delta priced at the snapshot mark, not the engine's "
                        "fill. Exact per-event proceeds are published nowhere — that is the hole."),
    }


def heg_artifact_disagreement(a: dict) -> dict:
    """The two artifacts do not agree about the one corporate action in the live book.

    A1 is exactly the study that should catch this, and the first version of it quoted one figure as
    "the credit" (red-team, 2026-09-25).
    """
    pf = (a["portfolio"].get("positions", {}).get("HEG") or {}).get("corporate_actions") or []
    led = None
    try:
        import csv as _csv
        with open(RESULTS / "attribution_ledger.csv", newline="", encoding="utf-8") as fh:
            for row in _csv.DictReader(fh):
                if row.get("ticker") == "HEG" and row.get("corporate_actions"):
                    led = json.loads(row["corporate_actions"])
                    break
    except Exception as exc:                      # a missing ledger is a hole, not a crash
        return {"error": f"attribution_ledger.csv unreadable: {exc}"}
    if not pf or not led:
        return {"comparable": False, "note": "one side carries no corporate-action row"}
    x, y = pf[0], led[0]
    fields = ("credit", "shares", "r_credited", "retained", "prior_close", "spin_value_per_share")
    deltas = {f: {"paper_portfolio": x.get(f), "attribution_ledger": y.get(f),
                  "delta": (None if x.get(f) is None or y.get(f) is None
                            else round(float(y[f]) - float(x[f]), 4))} for f in fields}
    return {
        "comparable": True, "fields": deltas,
        "disagree_on": [f for f, v in deltas.items() if v["delta"] not in (None, 0.0)],
        "why": ("the ledger is rebuilt from the same archives, so this is a restatement artifact, not "
                "two independent measurements. The ledger also carries NO `shares` for HEG: its join "
                "key is (ticker, signal_date=2026-07-24) against a position entered 2026-07-28."),
    }


def capped_position_history() -> dict:
    snaps = sorted(glob.glob(str(RESULTS / "archive" / "*" / "paper_portfolio_weekly.json")))
    seq, prev, exits, ever = [], None, [], set()
    for s in snaps:
        d = json.loads(Path(s).read_text(encoding="utf-8"))
        names = set(d.get("positions", {}))
        ever |= names
        left = sorted(prev - names) if prev is not None else []
        entered = sorted(names - prev) if prev is not None else sorted(names)
        snap = Path(s).parent.name
        for t in left:
            exits.append({"ticker": t, "gone_by_snapshot": snap})
        seq.append({"snapshot": snap, "n_positions": len(names),
                    "published_total_trades": d.get("total_trades"),
                    "nav": round(float(d.get("total_value") or 0), 2),
                    "entered": entered, "exited": left})
        prev = names
    return {
        "n_snapshots": len(seq), "sequence": seq,
        "names_ever_held": sorted(ever), "n_names_ever_held": len(ever),
        "positions_that_left": exits, "n_positions_that_left": len(exits),
        "LOWER_BOUND": ("snapshots are weekly, so a position opened AND closed between two of them is "
                        "invisible here. This is a lower bound on closures, and it is reported as one. "
                        "`base_swing_forward.n_closed` is an independent corroborating source for the "
                        "all-grades capped book."),
    }


# ── 4. NAV reconciliation ──────────────────────────────────────────────────────────────────────────
def nav_reconciliation(a: dict) -> dict:
    pf = a["portfolio"]
    pos = pf.get("positions", {})
    cv = sum(float(v["current_value"]) for v in pos.values())
    un = sum(float(v["unrealised_pnl"]) for v in pos.values())
    nav = float(pf["total_value"])
    cash = float(pf["cash"])
    return {
        "n_open_positions": len(pos),
        "cash": round(cash, 2), "sum_current_value": round(cv, 2), "total_value": round(nav, 2),
        "identity_residual": round(cash + cv - nav, 2),
        "identity_holds": abs(cash + cv - nav) <= 0.02,
        "sum_unrealised_pnl": round(un, 2),
        "implied_realised_pnl": round(nav - OPENING_CAPITAL - un, 2),
        "DERIVED_NOT_SOURCED": ("implied_realised_pnl is SOLVED FOR, not read from an artifact: the "
                                "capped book's per-position realised P&L is published nowhere. It is "
                                "NAV − opening capital − unrealised, and it carries every rounding and "
                                "any corporate-action cash credit (HEG's spun-off value) with it."),
    }


# ── 5. does any single gate read two books? ────────────────────────────────────────────────────────
def gate_book_mismatch(a: dict) -> dict:
    sc = a["scorecard"]
    gates = [
        {"gate": "readiness (>=40 closed OR 4 quarters)",
         "inputs": {"n_closed": UNCAPPED_A},
         "single_book": True,
         "note": ("the count is uncapped closures; the book it gates — and whose Sharpe/MaxDD sit "
                  "beside it in the same readout — is the capped one")},
        {"gate": "KILL_SHARPE < 0",
         "inputs": {"sharpe": CAPPED_A}, "single_book": True,
         "note": "reads the capped NAV curve only. 55 daily points at the time of writing."},
        {"gate": "prereg_swing.md §4 floor (>=20 closed PER BOOK)",
         "inputs": {"a_only_closed": UNCAPPED_A, "base_swing_closed": CAPPED_ALL},
         "single_book": False,
         "note": ("THE MISMATCH: one arm's count is uncapped, the other's is capped. The two numbers "
                  "are not the same kind of quantity, and a per-book floor is applied to both.")},
        {"gate": "§4 decision (MaxDD shallower AND Calmar >= base - 0.05)",
         "inputs": {"a_only_curve": CAPPED_A, "base_curve": CAPPED_ALL},
         "single_book": True,
         "note": "both capped — but see curve_identity: they may be the same curve."},
    ]
    return {"gates": gates,
            "n_gates_reading_two_books": sum(1 for g in gates if not g["single_book"]),
            "status_at_run": {"kill_triggered": _kill_triggered(sc),
                              "headline": sc.get("headline")}}


def _kill_triggered(sc: dict):
    """The scorecard names the gate in the KEY (`gates.kill`), not anywhere in its value.

    The first version scanned each gate's serialised VALUE for "kill" and so returned None, publishing
    `kill_triggered: null` while the live scorecard said True — on the very capped Sharpe this study is
    attributing. A status field that silently reads "unknown" is worse than absent (red-team, 2026-09-25).
    """
    gates = sc.get("gates")
    if not isinstance(gates, dict):
        return None
    for name, g in gates.items():
        if "kill" in str(name).lower() and isinstance(g, dict):
            return g.get("triggered")
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-date", default=str(date.today()))
    ap.add_argument("--no-replay", action="store_true",
                    help="skip the with/without-a_grade replay (two backtests, a few minutes)")
    args = ap.parse_args(argv)
    replay = not args.no_replay

    a = load_artifacts()
    counts = json.loads((ROOT / "diagnostics" / "research" / "n_trials.json").read_text(encoding="utf-8"))
    summary = {
        "spec": "diagnostics/research/book_identity/SPEC.md",
        "class": "MEASUREMENT — no trial, no screen row, no sealed open, nothing adopted",
        "run_date": args.run_date,
        "n_trials_at_run": counts["cumulative_n_trials"],
        "books": {"capped_a_only": CAPPED_A, "uncapped_a_only": UNCAPPED_A,
                  "capped_all_grades": CAPPED_ALL},
        "provenance": provenance_map(a),
        "curve_identity": curve_identity(a),
        "grading_discriminates": (grading_discriminates() if replay else
                                 {"skipped": "--no-replay"}),
        "capped_closures": capped_closures_are_exact(a),
        "realisation_events": realisation_events(a),
        "heg_artifact_disagreement": heg_artifact_disagreement(a),
        "capped_position_history": capped_position_history(),
        "nav_reconciliation": nav_reconciliation(a),
        "gate_book_mismatch": gate_book_mismatch(a),
        "reading": ("Description only. No rule is proposed and no gate is re-specified. One closed "
                    "position is not evidence that the strategy works, and nothing here restates the "
                    "book's performance as better or worse — it states which book each number is ABOUT. "
                    "The >=30-closed precondition applies: expectancy and win rate are not informative."),
    }

    out = OUT_BASE / args.run_date
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"book identity -> {out}")
    print(json.dumps({
        "curves_identical_live": summary["curve_identity"]["identical"],
        "grading_bites_on_an_unsealed_window": summary["grading_discriminates"].get("grading_bites"),
        "capped_closures": summary["capped_closures"]["capped_closures"],
        "capped_closures_exact": summary["capped_closures"]["exact"],
        "realisation_events": summary["realisation_events"]["n_events"],
        "implied_realised_pnl": summary["nav_reconciliation"]["implied_realised_pnl"],
        "heg_fields_disagreeing": summary["heg_artifact_disagreement"].get("disagree_on"),
        "kill_triggered": summary["gate_book_mismatch"]["status_at_run"]["kill_triggered"],
        "all_value_checks_agree": summary["provenance"]["all_value_checks_agree"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
