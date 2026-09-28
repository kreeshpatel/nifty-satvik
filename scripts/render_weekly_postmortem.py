"""The Saturday post-mortem — one page, numbers first, and every number says which book it is about.

Phase 1 item B4 of the 2026-09-25 development plan. PRODUCT, not research: it renders artifacts that
already exist and computes no new statistic, so it spends no trial, no screen row and no sealed open.

DETERMINISTIC BY CHOICE. The Brain plan's Layer 5 sketches an LLM narrating injected numbers. This page
does not call a model: it is generated from committed artifacts by pure formatting, so it costs nothing,
cannot drift between runs, and can be pinned by a golden-file test. A narrated version can be layered on
later — but the numbers-first page has to exist first, and it has to be the thing the review reads.

WHAT IT REFUSES TO DO. It never opens `results/judge_log.jsonl`. That log is SEALED until the first
review read (>= 2 quarters from 2026-08-01 AND >= 100 resolved verdicts), and a reporting page is exactly
the sort of convenience that would breach a seal by accident. `tests/test_weekly_postmortem.py` asserts
the refusal rather than trusting it.

Sources, all committed:
  * results/weekly_review_scorecard.json          — gates, with the conventions ratified 2026-09-27
  * diagnostics/research/book_identity/*/         — which book each number is about (finding 0146)
  * diagnostics/research/trade_forensics/*/       — the loss composition, funded vs never-funded (0147)
  * results/attribution_ledger.csv                — excursions and the index control (A3)
  * results/paper_portfolio_weekly.json           — the capital book's positions and NAV

Reproduce: `python scripts/render_weekly_postmortem.py`
"""

from __future__ import annotations

import argparse
import glob
import json
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT_DIR = RESULTS / "brain"
SEALED = "judge_log.jsonl"          # named so the refusal is greppable, never opened


def _latest(base: Path) -> dict | None:
    """The summary describing the NEWEST DATA under a diagnostics directory, or None.

    Selected on the summary's own `as_of` (the snapshot it describes), NOT on the directory name (the
    date it was RUN). The first version of this page sorted by directory and showed 9 closed trades when
    13 had closed, because `trade_forensics/2026-09-26/` is a re-run about the 2026-09-04 snapshot and
    sorts after `2026-09-25/`, which describes the newer one. A run date is not a data date.
    """
    best, best_key = None, None
    for c in sorted(glob.glob(str(base / "*" / "summary.json"))):
        try:
            payload = json.loads(Path(c).read_text(encoding="utf-8"))
        except Exception:                      # noqa: BLE001 — one bad file must not blank the page
            continue
        # prefer the data date; fall back to the run date, then the directory name
        key = str(payload.get("as_of") or payload.get("run_date") or Path(c).parent.name)
        if best_key is None or key > best_key:
            best, best_key = payload, key
    return best


def _pct(x, nd: int = 2, sign: bool = True) -> str:
    if x is None or (isinstance(x, float) and x != x):
        return "n/a"
    return f"{float(x):{'+' if sign else ''}.{nd}f}%"


def _num(x, nd: int = 2, sign: bool = False) -> str:
    if x is None or (isinstance(x, float) and x != x):
        return "n/a"
    return f"{float(x):{'+' if sign else ''}.{nd}f}"


def _rupees(x) -> str:
    if x is None or (isinstance(x, float) and x != x):
        return "n/a"
    return f"Rs.{float(x):,.2f}"


def _book_short(label: str | None) -> str:
    if not label:
        return "?"
    return "uncapped tracker" if "uncapped" in label.lower() else "capped Rs.10L book"


def render(scorecard: dict, book_identity: dict | None, forensics: dict | None,
           ledger: pd.DataFrame | None, portfolio: dict | None) -> str:
    """The page. Pure: no I/O, no clock, no network — so a golden file can pin it."""
    L: list[str] = []
    as_of = scorecard.get("generated_ist") or scorecard.get("generated_utc") or "?"
    fwd = scorecard.get("forward", {})
    gates = scorecard.get("gates", {})
    grading = scorecard.get("swing_grading", {})

    L += [f"# Saturday post-mortem — {as_of}", "",
          f"**{scorecard.get('headline', '')}**", "",
          "Generated from committed artifacts by `scripts/render_weekly_postmortem.py`. No number here "
          "is new: each one is reproduced from the artifact named beside it. Nothing in this page reads "
          "the sealed judge log.", ""]

    # ── 1. which book ───────────────────────────────────────────────────────────────────────────────
    L += ["## 1. Which book each headline number is about", "",
          "Finding 0146: the weekly scan runs three books off one engine and the readout mixes them. "
          "A number without its book is not interpretable.", "",
          "| number | value | book |", "|---|---|---|"]
    L += [f"| closed trades (the readiness count) | {fwd.get('n_closed')} | uncapped tracker |",
          f"| expectancy | {_num(fwd.get('expectancy_R'), 2, True)}R | uncapped tracker |",
          f"| win rate | {_pct(fwd.get('win_rate_pct'), 1, False)} | uncapped tracker |",
          f"| NAV | {_rupees(fwd.get('nav'))} | capped Rs.10L book |",
          f"| Sharpe (the kill trigger) | {_num(fwd.get('sharpe'), 4, True)} | capped Rs.10L book |",
          f"| MaxDD (the halt trigger) | {_pct(fwd.get('maxdd_pct'), 1)} | capped Rs.10L book |"]
    if book_identity:
        cc = book_identity.get("capped_closures", {})
        re_ = book_identity.get("realisation_events", {})
        nav = book_identity.get("nav_reconciliation", {})
        L += ["",
              f"**The capital book itself:** {cc.get('capped_closures')} closed "
              f"({'exact' if cc.get('exact') else 'lower bound'}), "
              f"{re_.get('n_events')} realisation event(s) — so the closure count is not the number of "
              f"times money was realised. Implied realised {_rupees(nav.get('implied_realised_pnl'))} "
              f"(derived, not sourced), unrealised {_rupees(nav.get('sum_unrealised_pnl'))}.",
              "",
              f"The two capped books' NAV curves are "
              f"{'IDENTICAL' if book_identity.get('curve_identity', {}).get('identical') else 'different'}"
              f" over {book_identity.get('curve_identity', {}).get('n_common')} sessions, so §4's "
              f"MaxDD/Calmar test cannot currently separate the arms."]

    # ── 2. gates ────────────────────────────────────────────────────────────────────────────────────
    L += ["", "## 2. Gates — value, convention, and whether it fired", "",
          "Conventions were ratified in `forward/prereg_swing.md` §11 on 2026-09-27, **before** the "
          "first read, so no reading could be chosen after seeing the data. Between reviews every gate "
          "is **surfaced, not applied** — the only exception is §5's mechanical halt.", "",
          "| gate | reading | fired? | convention | book |", "|---|---|---|---|---|"]
    for name in ("readiness", "promote", "kill", "halt"):
        g = gates.get(name) or {}
        conv = g.get("convention") or {}
        fired = g.get("triggered", g.get("ready", g.get("pass")))
        if name == "readiness":
            reading = f"{g.get('n_closed')} closed / {g.get('quarters_elapsed')} quarters"
            note = "closed-only count"
        elif name == "promote":
            reading = f"exp {_num(g.get('expectancy_R'), 2, True)}R, DD {_pct(g.get('maxdd_pct'), 1)}"
            note = f"{conv.get('cagr_years', '?')} years, {conv.get('maxdd_grid', '?')} grid"
        elif name == "kill":
            reading = _num(g.get("sharpe"), 4, True)
            note = "raw-return, rf = 0 (below cash, not below the risk-free rate)"
        else:
            reading = _pct(g.get("maxdd_pct"), 1)
            note = f"{conv.get('grid', '?')} grid"
        book = _book_short(conv.get("book") or conv.get("maxdd_book"))
        L.append(f"| {name} | {reading} | {'YES' if fired else 'no'} | {note} | {book} |")

    if grading:
        gc = grading.get("convention") or {}
        L += ["", f"**§4 grading (A-only vs base-swing):** {grading.get('verdict', '?')} — "
                  f"A-only {grading.get('a_only_closed')} vs base {grading.get('base_swing_closed')} "
                  f"closed against a floor of {grading.get('floor_per_book')} per book."]
        if gc.get("same_quantity") is False:
            L.append("  **Those two counts are not the same quantity** — the first is the uncapped "
                     "tracker's, the second a capped book's — and this floor short-circuits before the "
                     "MaxDD/Calmar branches, so it is what currently decides §4. Recorded, not repaired: "
                     "repairing it is a live-rule change (0146).")

    # ── 3. loss composition ─────────────────────────────────────────────────────────────────────────
    if forensics:
        d = forensics.get("stop_decomposition", {})
        fs = forensics.get("funded_split", {})
        cv = forensics.get("convention_divergence", {})
        L += ["", "## 3. Where the loss came from", "",
              f"Across {d.get('n')} closed trades in the {forensics.get('as_of')} snapshot: realised "
              f"{_num(d.get('realised_r'), 2, True)}R = designed {_num(d.get('designed_r'), 2, True)}R "
              f"+ beyond-stop {_num(d.get('beyond_stop_r'), 2, True)}R "
              f"({d.get('n_filled_beyond_stop')} of {d.get('n')} filled past the stop).", ""]
        if fs:
            f_, nf = fs.get("funded", {}), fs.get("never_funded", {})
            L += ["| cohort | n | realised | beyond-stop |", "|---|---|---|---|",
                  f"| **funded — the book that holds money** | {f_.get('n')} | "
                  f"{_num(f_.get('realised_r'), 2, True)}R | {_num(f_.get('beyond_stop_r'), 2, True)}R |",
                  f"| never funded — tracker only | {nf.get('n')} | "
                  f"{_num(nf.get('realised_r'), 2, True)}R | {_num(nf.get('beyond_stop_r'), 2, True)}R |",
                  "",
                  "0147: beyond-stop slippage on the funded book is the first row. The second belongs to "
                  "a book no rupee was exposed to, and must not be quoted as the book's."]
        if cv:
            a = cv.get("attribution_nets_favourable_fills", {})
            b = cv.get("ledger_counts_adverse_overshoot_only", {})
            L += ["", f"Two committed conventions disagree by {_num(cv.get('difference_r'), 2, True)}R: "
                      f"netting favourable fills gives {_num(a.get('beyond_stop_r'), 2, True)}R, counting "
                      f"adverse overshoot only gives {_num(b.get('beyond_stop_r'), 2, True)}R. Neither is "
                      f"wrong; a quoted figure should say which."]

    # ── 4. excursions ───────────────────────────────────────────────────────────────────────────────
    if ledger is not None and len(ledger):
        closed = ledger[ledger["exit_reason"].notna()] if "exit_reason" in ledger else ledger.iloc[:0]
        have = closed[closed["mae_r"].notna()] if "mae_r" in closed else closed.iloc[:0]
        L += ["", "## 4. How the trades travelled", "",
              f"{len(have)} of {len(closed)} closed trades carry an excursion measurement. The rest have "
              f"no committed price basis: the capital book never funded them, so no archived mark "
              f"exists (A3)."]
        if len(have):
            L += ["", "| trade | R | MAE | MFE | capture of MFE | basis |", "|---|---|---|---|---|---|"]
            for r in have.itertuples(index=False):
                L.append(f"| {r.ticker} | {_num(getattr(r, 'r_multiple', None), 2, True)} | "
                         f"{_num(getattr(r, 'mae_r', None), 2, True)} | "
                         f"{_num(getattr(r, 'mfe_r', None), 2, True)} | "
                         f"{_num(getattr(r, 'capture_of_mfe', None), 3, True)} | "
                         f"{getattr(r, 'excursion_basis', '?')} |")
            L += ["", "A `weekly_marks` basis cannot see the intra-week extreme, so its MAE and MFE are "
                      "UNDERSTATEMENTS — bounded by the true excursion, never beyond it. A capture near "
                      "-1 means the trade gave back its whole favourable move and then the risk."]

    # ── 5. what is deliberately absent ──────────────────────────────────────────────────────────────
    L += ["", "## 5. What this page does not contain", "",
          f"* **The AI judge stream.** `results/{SEALED}` is sealed until the first review read "
          f"(>= 2 quarters from 2026-08-01 AND >= 100 resolved verdicts). This renderer never opens it.",
          "* **Owner overrides.** No source exists — the engine cannot see a discretionary deviation, "
          "and an empty column would read as 'none happened'. A declared hole, not a zero.",
          "* **Any number computed here.** Every figure is reproduced from a committed artifact; if one "
          "looks wrong, the artifact is wrong, and the diagnostic that wrote it is named above.", ""]
    if portfolio:
        L += [f"*Capital book: {portfolio.get('n_positions')} position(s), cash "
              f"{_rupees(portfolio.get('cash'))}, NAV {_rupees(portfolio.get('total_value'))}.*", ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-date", default=str(date.today()))
    args = ap.parse_args(argv)

    scorecard = json.loads((RESULTS / "weekly_review_scorecard.json").read_text(encoding="utf-8"))
    book_identity = _latest(ROOT / "diagnostics" / "research" / "book_identity")
    forensics = _latest(ROOT / "diagnostics" / "research" / "trade_forensics")
    led_path = RESULTS / "attribution_ledger.csv"
    ledger = pd.read_csv(led_path) if led_path.is_file() else None
    pf_path = RESULTS / "paper_portfolio_weekly.json"
    portfolio = json.loads(pf_path.read_text(encoding="utf-8")) if pf_path.is_file() else None

    page = render(scorecard, book_identity, forensics, ledger, portfolio)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"postmortem_{args.out_date}.md"
    out.write_text(page + "\n", encoding="utf-8")
    try:
        shown = out.relative_to(ROOT).as_posix()
    except ValueError:                        # an out-of-tree --out dir is legitimate (tests, scratch)
        shown = out.as_posix()
    print(f"post-mortem -> {shown} ({len(page.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
