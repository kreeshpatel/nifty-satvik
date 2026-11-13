"""Append-only FORWARD RECORD for the weekly-swing book (ADR-0018). Off by default.

The Saturday scan rebuilds the whole live record from inception. That makes the past mutable: a
re-adjusted bar re-prices a closed trade (MRPL, 2026-10-24), a name joining the scan signals in a week
that has already been published (ZYDUSWELL and ABDL, ADR-0017), and every exit-rule change needs an
effective-date gate so it does not re-price trades it was never meant to touch.

This module makes closed history immutable WITHOUT touching the engine. The rebuild still runs every
week, and it is used for two things only:

  * NEW information: open positions managed on the new bars, and trades that open after the last frozen
    week;
  * an AUDIT: every difference between the rebuild and the frozen record is classified (green / amber /
    red) and written out, and nothing in the frozen record is changed by it.

Why a merge and not an engine resume. `R94.backtest(return_state=True)` returns the open positions, the
pending orders and the cash, but it cannot be restarted from them: pending orders hold positional
indices into each ticker's bar arrays (a restated or extended series shifts them), demerger views and
the event log are keyed by `id()` of live position objects, and the prepared panel's rolling indicators
are rebuilt from the full history. Resuming would mean new engine code under the golden masters. So the
engine is left exactly as it is, and the merge rules below decide what the rebuild may change.

THE MERGE RULES (base = the frozen state as of the last frozen scan, `A`):

  1. A frozen CLOSED trade is published exactly as frozen. The rebuild's version of it is only compared.
  2. A frozen OPEN trade is taken from the rebuild run under the exit rule it was opened under (its
     "pinned" rule, recorded in the ledger). If that rebuild still holds it, the new state is published.
     If it closed after `A`, the close is new information and is appended. If it closed on or before `A`,
     the close is accepted (a phantom position cannot be managed) and reported RED. If it vanished, the
     frozen row and card are carried and reported RED.
  3. A trade the frozen record has never seen is new only if it entered AFTER `A`. One that entered on or
     before `A` is retroactive (a new universe entrant, a restated signal, a logic change) and is
     suppressed, reported AMBER.
  4. The NAV curve is frozen through `A`. Rows after `A` are the rebuild's, chain-linked so the frozen
     level carries forward: new = rebuild x (frozen at A / rebuild at A).
  5. An explicit amendment (`results/forward_record/amendments.json`, {"TICKER|YYYY-MM-DD": "dated
     reason"}) lets the rebuild's version of one trade win, once. It is the declared route for a
     deliberate correction, and it is recorded in the ledger.

Because each open trade keeps the exit rule it was opened under, an exit-rule change applies only to
trades opened after it. No effective-date constant is needed: the ledger is the gate.

Not pinned (stated, not hidden): the ₹10L capital book's holdings and cash are the current rebuild's (its
NAV curve is frozen and chain-linked, its holdings are not); the base-swing and shadow-exit side records,
the SMA panel and the brain logs are still rebuilt from inception. Discipline and staleness settings are
the current ones for every trade; only the exit rule is pinned.

    python scripts/forward_record.py cron -- --start 2026-07-04       # the weekly scan, forward record ON
    python scripts/forward_record.py verify-seed                 # migration proof on the committed record
    python scripts/forward_record.py replay --archive results/archive   # dry run over the weekly archive
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

RECORD_DIR_NAME = "forward_record"
LEDGER_NAME = "ledger.json"
AUDIT_NAME = "audit.json"
DRIFT_LOG_NAME = "drift.jsonl"
AMENDMENTS_NAME = "amendments.json"
SCHEMA = 1

# the fields a restatement of a closed trade is judged on (the same set the snapshot drift log uses)
NAV_KEY = "NAV"            # amendment key that re-anchors the NAV curve on the rebuild
NAV_GAP_TOL = 0.005        # a chain-link scale moving by more than 0.5% is a NEW NAV gap (amber)
_CLOSED_FIELDS = ("entry", "close_price", "close_date", "r_multiple", "status", "exit_reason")


class ForwardRecordError(RuntimeError):
    """The forward record refuses to publish (e.g. a scan older than the frozen record)."""


# ── published-record helpers ──────────────────────────────────────────────────────────────────

def key_of(row: dict) -> str:
    """Trade identity: ticker + entry date (`signal_date` on a history row, `bought_date` on a card)."""
    return f"{row.get('ticker')}|{str(row.get('signal_date') or row.get('bought_date'))[:10]}"


def exit_rule_fp(rule: dict) -> str:
    return hashlib.sha256(json.dumps(rule, sort_keys=True, default=str).encode()).hexdigest()[:12]


def nav_rows(hist_df: pd.DataFrame | None) -> list[list]:
    if hist_df is None or not len(hist_df):
        return []
    return [[str(d)[:10], float(v)] for d, v in zip(hist_df["date"], hist_df["total_value"])]


def published(envelope: dict, sig_hist: list, analytics: dict, portfolio: dict, hist_df,
              ledger: list | None = None) -> dict:
    """One rebuild's published record, indexed for the merge. `ledger` (the engine's raw trade rows)
    supplies each closed trade's 3-dp R, which the analytics average; without it the 2-dp
    `r_multiple` stands in."""
    closed = [r for r in sig_hist if r.get("status") != "ACTIVE"]
    active = [r for r in sig_hist if r.get("status") == "ACTIVE"]
    r3 = {}
    for r in ledger or []:
        r3[f"{r['tkr']}|{str(r['entry_date'])[:10]}"] = float(r["R"])
    return {
        "envelope": envelope, "analytics": analytics, "portfolio": portfolio,
        "closed": {key_of(r): r for r in closed}, "closed_order": [key_of(r) for r in closed],
        "active": {key_of(r): r for r in active}, "active_order": [key_of(r) for r in active],
        "cards": {key_of(c): c for c in envelope.get("signals", []) if c.get("bought_date")},
        "nav": nav_rows(hist_df if isinstance(hist_df, pd.DataFrame) else pd.DataFrame(hist_df)),
        "r3": r3,
    }


def _hist_df(nav: list[list]) -> pd.DataFrame:
    if not nav:
        return pd.DataFrame({"date": [], "total_value": []})
    return pd.DataFrame({"date": [d for d, _ in nav], "total_value": [v for _, v in nav]})


# ── ledger ────────────────────────────────────────────────────────────────────────────────────

def record_dir(state_dir: Path) -> Path:
    return Path(state_dir) / RECORD_DIR_NAME


def load_ledger(state_dir: Path) -> dict | None:
    p = record_dir(state_dir) / LEDGER_NAME
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save_ledger(ledger: dict, state_dir: Path) -> Path:
    d = record_dir(state_dir)
    d.mkdir(parents=True, exist_ok=True)
    p = d / LEDGER_NAME
    p.write_text(json.dumps(ledger, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return p


def load_amendments(state_dir: Path) -> dict:
    p = record_dir(state_dir) / AMENDMENTS_NAME
    if not p.exists():
        return {}
    raw = json.loads(p.read_text(encoding="utf-8"))
    return {k: str(v) for k, v in raw.items() if str(v).strip()}


def seed(pub: dict, as_of: str, exit_rule: dict, *, seeded_from: str, r3: dict | None = None,
         preapproved: dict | None = None) -> dict:
    """The first frozen state, taken from a PUBLISHED record (the committed files), verbatim.

    Every open trade is pinned to `exit_rule` (the live rule when the record is seeded). `r3` is the
    rebuild's 3-dp R by trade key; it is used only where it agrees with the published 2-dp R, so a seed
    can never import a number the published record does not show."""
    fp = exit_rule_fp(exit_rule)
    r3 = {**pub.get("r3", {}), **(r3 or {})}
    closed = []
    for k in pub["closed_order"]:
        row = pub["closed"][k]
        R = r3.get(k)
        if R is None or round(R, 2) != row.get("r_multiple"):
            R = row.get("r_multiple")
        closed.append({"key": k, "row": row, "R3": R, "rule": fp})
    opens = {k: {"row": pub["active"][k], "card": pub["cards"].get(k), "rule": fp, "opened_as_of": None}
             for k in pub["active_order"]}
    state = {"as_of": as_of, "closed": closed, "open": opens, "open_order": list(pub["active_order"]),
             "nav": pub["nav"]}
    return {"schema": SCHEMA, "seeded_from": seeded_from, "seeded_as_of": as_of,
            "exit_rules": {fp: exit_rule}, "current_rule": fp,
            "state": state, "parent": None,
            # Approvals that exist when the record is seeded were granted to the rebuild that produced the
            # committed record, which already reflects them: they are spent, not pending.
            "amendments_applied": [{"key": k, "reason": v, "as_of": "pre-seed"}
                                   for k, v in sorted((preapproved or {}).items())]}


def pinned_rules(ledger: dict, as_of: str) -> dict[str, dict]:
    """{fp: rule} the merge needs a rebuild for: every exit rule a frozen trade was opened under. Open
    trades are MANAGED by their rule's rebuild; closed ones are only AUDITED against it, so a rule change
    does not read as a restatement of every trade closed before it."""
    base = _base(ledger, as_of)
    fps = {o["rule"] for o in base["open"].values()} | {c.get("rule") for c in base["closed"] if c.get("rule")}
    return {fp: ledger["exit_rules"][fp] for fp in sorted(fps)}


def _base(ledger: dict, as_of: str) -> dict:
    st = ledger["state"]
    if as_of < st["as_of"]:
        raise ForwardRecordError(f"scan as-of {as_of} is OLDER than the frozen record ({st['as_of']}); "
                                 "the forward record never moves backwards")
    if as_of == st["as_of"] and ledger.get("parent") is not None:
        return ledger["parent"]                  # a re-run of the latest week re-merges against its parent
    return st


# ── the merge ─────────────────────────────────────────────────────────────────────────────────

def _changed(old: dict, new: dict) -> dict:
    return {f: [old.get(f), new.get(f)] for f in _CLOSED_FIELDS if old.get(f) != new.get(f)}


def _is_rebase(change: dict) -> bool:
    from check_history_drift import is_rebase
    return is_rebase(change)


def merge(ledger: dict, as_of: str, rebuilds: dict[str, dict], current_rule: dict,
          amendments: dict | None = None) -> tuple[dict, dict, dict]:
    """Merge this scan's rebuild(s) into the frozen record.

    rebuilds: {exit-rule fp: published(...)} — must hold the CURRENT rule's rebuild and one per rule an
    open trade is pinned to (`pinned_rules`). Returns (merged published outputs, new ledger, audit).
    """
    amendments = dict(amendments or {})
    already = {(a["key"], a["reason"]) for a in ledger.get("amendments_applied", [])}
    amend = {k: v for k, v in amendments.items() if (k, v) not in already}
    base = _base(ledger, as_of)
    A = base["as_of"]
    cur_fp = exit_rule_fp(current_rule)
    if cur_fp not in rebuilds:
        raise ForwardRecordError("no rebuild for the current exit rule")
    cur = rebuilds[cur_fp]
    rules = {**ledger["exit_rules"], cur_fp: current_rule}

    findings: list[dict] = []                    # each {"severity": red|amber|info, "kind", ...}
    applied: list[dict] = []

    def _find(severity: str, kind: str, **kw) -> None:
        findings.append({"severity": severity, "kind": kind, **kw})

    # 1. frozen closed trades: published as frozen; the rebuild is only compared.
    closed_out: list[dict] = []
    frozen_closed = set()
    for fz in base["closed"]:
        k = fz["key"]
        frozen_closed.add(k)
        src = rebuilds.get(fz.get("rule") or cur_fp)
        if src is None:
            closed_out.append(fz)
            _find("info", "not_audited_rule_not_rebuilt", trade=k, rule=fz.get("rule"))
            continue
        rb = src["closed"].get(k)
        if k in amend:
            applied.append({"key": k, "reason": amend[k], "as_of": as_of,
                            "from": fz["row"], "to": rb})
            if rb is not None:
                closed_out.append({"key": k, "row": rb, "R3": src["r3"].get(k, rb.get("r_multiple")),
                                   "rule": fz.get("rule") or cur_fp})
            continue
        closed_out.append(fz)
        if rb is None:
            _find("red", "closed_reopened_in_rebuild" if k in src["active"] else "vanished_closed", trade=k)
            continue
        ch = _changed(fz["row"], rb)
        if ch:
            if _is_rebase(ch):                   # dividend-scale re-basing, R unchanged (check_history_drift)
                _find("info", "restated_rebase", trade=k, changed=ch)
            else:
                _find("red", "restated", trade=k, changed=ch)

    # 2. frozen open trades: managed by the rebuild under the rule each was opened under.
    open_out: dict[str, dict] = {}
    new_closed: list[tuple] = []
    for k in base.get("open_order", list(base["open"])):
        fo = base["open"][k]
        src = rebuilds.get(fo["rule"])
        if src is None:
            _find("red", "pinned_rule_rebuild_missing", trade=k, rule=fo["rule"])
            open_out[k] = dict(fo)
            continue
        if k in src["active"]:
            open_out[k] = {"row": src["active"][k], "card": src["cards"].get(k), "rule": fo["rule"],
                           "opened_as_of": fo.get("opened_as_of")}
        elif k in src["closed"]:
            row = src["closed"][k]
            if str(row.get("close_date"))[:10] <= A and k not in amend:
                _find("red", "open_closed_retroactively", trade=k, close_date=row.get("close_date"))
            new_closed.append((k, row, src["r3"].get(k, row.get("r_multiple")), fo["rule"]))
        elif k in amend:
            applied.append({"key": k, "reason": amend[k], "as_of": as_of, "from": fo["row"], "to": None})
        else:
            _find("red", "vanished_open", trade=k)
            open_out[k] = dict(fo)               # carried: a held position is never silently dropped

    # 3. trades the frozen record has never seen: new only if they entered after A.
    seen = frozen_closed | set(base["open"])
    for kind, order, rows in (("closed", cur["closed_order"], cur["closed"]),
                              ("active", cur["active_order"], cur["active"])):
        for k in order:
            if k in seen:
                continue
            entry = k.split("|", 1)[1]
            if entry <= A and k not in amend:
                _find("amber", "suppressed_retroactive", trade=k, entry_date=entry,
                      rebuild_status=rows[k].get("status"))
                continue
            if k in amend:
                applied.append({"key": k, "reason": amend[k], "as_of": as_of, "from": None, "to": rows[k]})
            if kind == "closed":
                new_closed.append((k, rows[k], cur["r3"].get(k, rows[k].get("r_multiple")), cur_fp))
            else:
                open_out[k] = {"row": rows[k], "card": cur["cards"].get(k), "rule": cur_fp,
                               "opened_as_of": as_of}

    # new closes in the current rebuild's order (exit order), pinned-rule closes by close date after it
    pos = {k: i for i, k in enumerate(cur["closed_order"])}
    new_closed.sort(key=lambda x: (pos.get(x[0], len(pos)), str(x[1].get("close_date")), x[0]))
    for k, row, R3, _fp in new_closed:
        closed_out.append({"key": k, "row": row, "R3": R3, "rule": _fp})

    # active order: the current rebuild's, then pinned-only / carried trades in frozen order
    open_order = [k for k in cur["active_order"] if k in open_out]
    open_order += [k for k in base.get("open_order", list(base["open"])) if k in open_out and k not in open_order]
    open_order += [k for k in open_out if k not in open_order]

    # 4. NAV: frozen through A, rebuild after A chain-linked onto the frozen level.
    #    An amendment keyed "NAV" re-anchors the whole curve on the rebuild once (a deliberate correction
    #    such as the B-prime demerger fix, which legitimately moved past NAV by 13%).
    rb_nav = cur["nav"]
    scale = 1.0
    if NAV_KEY in amend:
        applied.append({"key": NAV_KEY, "reason": amend[NAV_KEY], "as_of": as_of, "from": None, "to": None})
        fz_nav = []
        A_nav = "0000-00-00"
    else:
        fz_nav = [r for r in base["nav"] if r[0] <= A]
        A_nav = A
    if fz_nav:
        rb_at = [v for d, v in rb_nav if d <= A]
        if rb_at and rb_at[-1] and rb_at[-1] != fz_nav[-1][1]:
            scale = fz_nav[-1][1] / rb_at[-1]
            moved = abs(scale - float(base.get("nav_scale", 1.0))) > NAV_GAP_TOL
            _find("amber" if moved else "info", "nav_level_gap", as_of=A, frozen=fz_nav[-1][1],
                  rebuild=rb_at[-1], chain_link_scale=scale)
    nav = fz_nav + [[d, (v if scale == 1.0 else v * scale)] for d, v in rb_nav if d > A_nav]

    merged = _publish(cur, closed_out, open_out, open_order, nav, scale)
    # LEVEL. red = something NEW this week rewrote or contradicts the frozen past; amber = a new
    # suppression / NAV gap, or a red finding still unresolved from an earlier week (it stays visible
    # until an amendment resolves it); info = routine re-basing and already-reported ambers.
    prior = set(base.get("audit_ids", []))
    for f in findings:
        f["id"] = f"{f['kind']}:{f.get('trade', '')}"
        f["new"] = f["id"] not in prior or f["kind"] == "nav_level_gap"
        if not f["new"]:
            f["severity"] = {"red": "amber", "amber": "info"}.get(f["severity"], f["severity"])
    red = [f for f in findings if f["severity"] == "red"]
    amber = [f for f in findings if f["severity"] == "amber"]
    info = [f for f in findings if f["severity"] == "info"]
    state = {"as_of": as_of, "closed": closed_out, "open": open_out, "open_order": open_order, "nav": nav,
             "nav_scale": scale,
             "audit_ids": sorted({f["id"] for f in findings if f["kind"] != "nav_level_gap"})}
    new_ledger = copy.deepcopy(ledger)
    if as_of != ledger["state"]["as_of"]:        # a new week: the old head becomes the parent
        new_ledger["parent"] = ledger["state"]   # (a re-run keeps its parent, see `_base`)
    new_ledger["state"] = state
    used = {o["rule"] for o in open_out.values()} | {c["rule"] for c in closed_out if c.get("rule")} | {cur_fp}
    new_ledger["exit_rules"] = {fp: rules[fp] for fp in sorted(used)}
    new_ledger["current_rule"] = cur_fp
    new_ledger["amendments_applied"] = ledger.get("amendments_applied", []) + [
        {"key": a["key"], "reason": a["reason"], "as_of": a["as_of"]} for a in applied]
    audit = {
        "as_of": as_of, "base_as_of": A, "level": "red" if red else ("amber" if amber else "green"),
        "n_red": len(red), "n_amber": len(amber), "n_info": len(info), "red": red, "amber": amber,
        "info": info,
        "amendments_applied": applied,
        "n_closed": len(closed_out), "n_open": len(open_out),
        "n_new_closed": len(new_closed), "n_new_open": sum(1 for o in open_out.values() if o.get("opened_as_of") == as_of),
        "pinned_rules": sorted({o["rule"] for o in open_out.values()}), "current_rule": cur_fp,
        "nav_chain_link_scale": scale,
    }
    return merged, new_ledger, audit


def _publish(cur: dict, closed_out: list, open_out: dict, open_order: list, nav: list, scale: float) -> dict:
    """The merged record in the exact shapes the cron writes (build_envelopes' five outputs)."""
    active_rows = [open_out[k]["row"] for k in open_order]
    sig_hist = [c["row"] for c in closed_out] + active_rows

    env = dict(cur["envelope"])
    # a name the RECORD holds from a prior week that the rebuild does not hold still has its fresh card
    rebuild_held = {k.split("|", 1)[0] for k in cur["cards"]}
    held_tickers = {k.split("|", 1)[0] for k in open_order if open_out[k].get("card") is not None}
    cards, emitted = [], set()
    for c in cur["envelope"].get("signals", []):
        if c.get("bought_date"):
            k = key_of(c)
            if k in open_out and open_out[k].get("card") is not None:
                cards.append(open_out[k]["card"]); emitted.add(k)
        elif c.get("ticker") in held_tickers and c.get("ticker") not in rebuild_held:
            continue                              # the record already holds this name from a prior week
        else:
            cards.append(c)
    for k in open_order:
        if k not in emitted and open_out[k].get("card") is not None:
            cards.append(open_out[k]["card"]); emitted.add(k)
    env["signals"] = cards
    env["n_positions"] = len(active_rows)

    n_closed = len(closed_out)
    Rs = pd.Series([float(c["R3"]) for c in closed_out], dtype=float)
    wins = int((Rs > 0).sum()) if n_closed else 0
    analytics = {
        "total_signals": len(sig_hist), "total_closed": n_closed, "active": len(active_rows),
        "win_rate": round(wins / n_closed * 100, 1) if n_closed else None,
        "avg_return_pct": round(float(pd.Series([c["row"]["return_pct"] for c in closed_out]).mean()), 2)
        if n_closed else None,
        "avg_r": round(float(Rs.mean()), 2) if n_closed else None,
    }
    portfolio = dict(cur["portfolio"])
    portfolio["total_trades"] = n_closed
    if nav:
        vals = [v for _, v in nav]
        portfolio["total_value"] = round(vals[-1], 2)
        portfolio["peak_value"] = round(max(vals), 2)
        if scale != 1.0:
            portfolio["record_nav_chain_link"] = round(scale, 8)
    return {"envelope": env, "sig_hist": sig_hist, "analytics": analytics, "portfolio": portfolio,
            "hist_df": _hist_df(nav)}


# ── orchestration (called by the cron behind its flag) ───────────────────────────────────────

def run(state_dir: Path, as_of: str, current_rule: dict, current: dict, rebuild_for_rule) -> dict:
    """Seed (first run) or load the ledger, rebuild each pinned rule, merge, write ledger + audit.

    current: published(...) of this scan's rebuild under `current_rule`.
    rebuild_for_rule: callable(rule dict) -> published(...) under that exit rule.
    Must be called BEFORE the cron overwrites the published files: the first run seeds from them.
    """
    state_dir = Path(state_dir)
    ledger = load_ledger(state_dir)
    if ledger is None:
        pub = read_published(state_dir)
        if pub is None:                          # nothing published yet: the record starts empty
            pub = published({"signals": []}, [], {}, {}, None)
            seed_as_of = "0000-00-00"
        else:
            seed_as_of = pub["envelope"].get("generated_at")
        ledger = seed(pub, seed_as_of, current_rule, seeded_from=f"committed record as of {seed_as_of}",
                      r3=current["r3"], preapproved=load_amendments(state_dir))
        print(f"forward record: SEEDED from the committed record as of {seed_as_of} "
              f"({len(ledger['state']['closed'])} closed, {len(ledger['state']['open'])} open)", flush=True)
    rebuilds = {exit_rule_fp(current_rule): current}
    for fp, rule in pinned_rules(ledger, as_of).items():
        if fp not in rebuilds:
            rebuilds[fp] = rebuild_for_rule(rule)
    merged, new_ledger, audit = merge(ledger, as_of, rebuilds, current_rule, load_amendments(state_dir))
    save_ledger(new_ledger, state_dir)
    write_audit(audit, state_dir)
    tag = {"red": "::error::", "amber": "::warning::"}.get(audit["level"], "")
    print(f"{tag}forward record [{audit['level'].upper()}]: as-of {as_of} over frozen {audit['base_as_of']} | "
          f"{audit['n_closed']} closed ({audit['n_new_closed']} new) | {audit['n_open']} open | "
          f"red {audit['n_red']} amber {audit['n_amber']}", flush=True)
    for item in audit["red"][:20]:
        print(f"  RED   {item['kind']}: {item.get('trade', '')}", flush=True)
    for item in audit["amber"][:20]:
        print(f"  AMBER {item['kind']}: {item.get('trade', item.get('as_of', ''))}", flush=True)
    return merged


def publish_scan(state_dir: Path, generated_at: str, outputs: tuple, led_all: list, rebuild_for_rule) -> tuple:
    """build_envelopes' five outputs for the LIVE rule in, the forward record's five outputs out.

    `rebuild_for_rule(rule) -> published(...)` rebuilds the uncapped tracker under an earlier exit rule
    that a frozen trade is pinned to. Reads `LIVE_EXIT` at call time."""
    import run_bhanushali_cron as C
    merged = run(state_dir, generated_at, C.LIVE_EXIT, published(*outputs, ledger=led_all), rebuild_for_rule)
    return merged["envelope"], merged["sig_hist"], merged["analytics"], merged["portfolio"], merged["hist_df"]


def tracker_rebuilder(P, mem, tracker_kwargs: dict, out_paper: dict, generated_at: str):
    """A `rebuild_for_rule` for `publish_scan`: re-run the uncapped tracker with exactly the kwargs the
    cron used (same data, discipline, staleness, corporate actions, grade-A set), the exit rule swapped
    for the pinned one. The held cards' exit plan is drawn from the pinned rule too."""
    import run_bhanushali_cron as C
    import run_bhanushali_weekly_rank as R94
    build = getattr(C, "_fr_original_build_envelopes", C.build_envelopes)
    backtest = getattr(R94, "_fr_original_backtest", R94.backtest)

    def _rebuild(rule: dict) -> dict:
        kw = {k: v for k, v in tracker_kwargs.items() if k not in C.LIVE_EXIT and k != "ledger"}
        led: list = []
        out = backtest(P, mem, ledger=led, **kw, **rule)
        live = C.LIVE_EXIT
        C.LIVE_EXIT = rule                       # `_exit_plan` draws a held card's plan from LIVE_EXIT
        try:
            outs = build(P, out, led, out_paper, generated_at, mem)
        finally:
            C.LIVE_EXIT = live
        return published(*outs, ledger=led)
    return _rebuild


def cron_main(argv=None, *, raw_dir: Path | None = None, amendments_dir: Path | None = None) -> int:
    """`run_bhanushali_cron.main` with the forward record ON, without editing the production file.

    The cron is run unmodified. Two seams are observed: the FIRST uncapped grade-A `R94.backtest` call
    (the signal tracker, made before the envelopes are built) has its kwargs captured, and the cron's
    `build_envelopes` call has its outputs passed through `publish_scan` before main() writes them. Both
    patches are removed when the run ends. Switching the live scan on = running this instead of the cron
    (ADR-0018)."""
    import run_bhanushali_cron as C
    import run_bhanushali_weekly_rank as R94
    orig_bt, orig_be = R94.backtest, C.build_envelopes
    cap: dict = {}

    def bt(P, mem, **kw):
        out = orig_bt(P, mem, **kw)
        if kw.get("uncapped") and kw.get("a_grade") is not None and "tracker" not in cap:
            cap["tracker"] = (P, mem, dict(kw), kw.get("ledger"))
        return out

    def be(P, out, ledger, out_paper, generated_at, mem=None):
        outs = orig_be(P, out, ledger, out_paper, generated_at, mem)
        if "published" in cap or "tracker" not in cap or cap["tracker"][3] is not ledger:
            return outs                          # only the tracker's (first) envelope is the record
        _P, _mem, kw, _led = cap["tracker"]
        cap["published"] = True
        sd = Path(cap["state_dir"])
        if raw_dir is not None:              # shadow: keep the unmerged rebuild for the parity check
            e, h, an, pf, hdf = outs
            write_published(dict(envelope=e, sig_hist=h, analytics=an, portfolio=pf, hist_df=hdf), Path(raw_dir))
        if amendments_dir is not None and not (record_dir(sd) / AMENDMENTS_NAME).exists():
            src = record_dir(Path(amendments_dir)) / AMENDMENTS_NAME
            if src.exists():                     # shadow: the committed approvals, copied into the temp state
                record_dir(sd).mkdir(parents=True, exist_ok=True)
                (record_dir(sd) / AMENDMENTS_NAME).write_bytes(src.read_bytes())
        return publish_scan(sd, generated_at, outs, ledger,
                            tracker_rebuilder(_P, _mem, kw, out_paper, generated_at))

    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--state-dir", default=None)
    known, _ = ap.parse_known_args(argv)
    from config import RESULTS_DIR
    cap["state_dir"] = known.state_dir or str(RESULTS_DIR)
    R94._fr_original_backtest, C._fr_original_build_envelopes = orig_bt, orig_be
    R94.backtest, C.build_envelopes = bt, be
    try:
        rc = C.main(argv)
    finally:
        R94.backtest, C.build_envelopes = orig_bt, orig_be
        del R94._fr_original_backtest, C._fr_original_build_envelopes
    if "published" not in cap:
        raise ForwardRecordError("the cron never built the tracker's envelope - forward record not applied")
    return rc


def write_audit(audit: dict, state_dir: Path) -> None:
    d = record_dir(state_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / AUDIT_NAME).write_text(json.dumps(audit, indent=2, default=str) + "\n", encoding="utf-8")
    with open(d / DRIFT_LOG_NAME, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({k: audit[k] for k in ("as_of", "base_as_of", "level", "n_red", "n_amber",
                                                   "red", "amber", "nav_chain_link_scale")},
                            sort_keys=True, default=str) + "\n")


def read_published(d: Path) -> dict | None:
    """A published record from the files the cron writes (results/ or an archive snapshot)."""
    d = Path(d)
    env_p, hist_p = d / "signals_today_weekly.json", d / "signals_history_weekly.json"
    if not env_p.exists() or not hist_p.exists():
        return None
    env = json.loads(env_p.read_text(encoding="utf-8"))
    hist = json.loads(hist_p.read_text(encoding="utf-8"))
    an_p, pf_p, nav_p = (d / "signal_analytics_weekly.json", d / "paper_portfolio_weekly.json",
                         d / "portfolio_history_weekly.csv")
    an = json.loads(an_p.read_text(encoding="utf-8")) if an_p.exists() else {}
    pf = json.loads(pf_p.read_text(encoding="utf-8")) if pf_p.exists() else {}
    nav = pd.read_csv(nav_p, dtype={"date": str}, float_precision="round_trip") if nav_p.exists() else None
    return published(env, hist, an, pf, nav)


def write_published(merged: dict, d: Path) -> None:
    """Write the merged record with the cron's own serialisation (used by the dry-run tools)."""
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    (d / "signals_today_weekly.json").write_text(json.dumps(merged["envelope"], indent=2, default=str), encoding="utf-8")
    (d / "signals_history_weekly.json").write_text(json.dumps(merged["sig_hist"], indent=2, default=str), encoding="utf-8")
    (d / "signal_analytics_weekly.json").write_text(json.dumps(merged["analytics"], indent=2, default=str), encoding="utf-8")
    (d / "paper_portfolio_weekly.json").write_text(json.dumps(merged["portfolio"], indent=2, default=str), encoding="utf-8")
    merged["hist_df"].to_csv(d / "portfolio_history_weekly.csv", index=False)


_PUBLISHED_FILES = ("signals_today_weekly.json", "signals_history_weekly.json", "signal_analytics_weekly.json",
                    "paper_portfolio_weekly.json", "portfolio_history_weekly.csv")


# ── migration proof + dry run ─────────────────────────────────────────────────────────────────

def verify_seed(state_dir: Path, out_dir: Path) -> dict:
    """Seed from the committed record, then publish a same-data scan through the merge, and compare
    every published file byte-for-byte with the committed one.

    The "same-data scan" is the committed record itself: it is exactly what the from-inception rebuild
    produced on that data. Its 3-dp R values are not committed, so the seed falls back to the 2-dp R
    for the analytics; any analytics byte difference that causes is reported, not hidden."""
    from run_bhanushali_cron import LIVE_EXIT
    pub = read_published(state_dir)
    if pub is None:
        raise ForwardRecordError(f"no published record in {state_dir}")
    as_of = pub["envelope"]["generated_at"]
    ledger = seed(pub, as_of, LIVE_EXIT, seeded_from=f"committed record as of {as_of}")
    merged, _, audit = merge(ledger, as_of, {exit_rule_fp(LIVE_EXIT): pub}, LIVE_EXIT)
    write_published(merged, out_dir)
    res = {"as_of": as_of, "audit_level": audit["level"], "files": {}}
    for f in _PUBLISHED_FILES:
        a, b = (Path(state_dir) / f).read_bytes(), (Path(out_dir) / f).read_bytes()
        res["files"][f] = "IDENTICAL" if a == b else f"DIFFERS ({len(a)} vs {len(b)} bytes)"
        if a != b and f.endswith(".json"):
            ja, jb = json.loads(a), json.loads(b)
            if isinstance(ja, dict) and isinstance(jb, dict):
                res.setdefault("field_diffs", {})[f] = {k: [ja.get(k), jb.get(k)] for k in set(ja) | set(jb)
                                                         if ja.get(k) != jb.get(k)}
    if "avg_r" in res.get("field_diffs", {}).get("signal_analytics_weekly.json", {}):
        res["explained"] = ("avg_r is the mean of the engine's 3-dp R, which is not committed; offline the seed "
                            "can only average the published 2-dp r_multiple. The live first run seeds the 3-dp R "
                            "from the same run's rebuild ledger, which closes this gap (tests/test_forward_record.py"
                            "::test_first_run_on_unchanged_data_republishes_the_committed_record_byte_for_byte).")
    return res


def replay(archive: Path) -> list[dict]:
    """Dry run over the weekly archive: seed from the first snapshot, then feed each later snapshot (what
    the from-inception rebuild published that week) through the merge, and report what the forward
    record would have frozen differently from what was actually published."""
    from run_bhanushali_cron import LIVE_EXIT
    fp = exit_rule_fp(LIVE_EXIT)
    snaps = sorted(d for d in Path(archive).iterdir()
                   if d.is_dir() and (d / "signals_history_weekly.json").exists()
                   and (d / "signals_today_weekly.json").exists())
    if not snaps:
        return []
    first = read_published(snaps[0])
    ledger = seed(first, first["envelope"]["generated_at"], LIVE_EXIT, seeded_from=f"archive/{snaps[0].name}")
    rows = [{"snapshot": snaps[0].name, "action": "seed", "closed": len(ledger["state"]["closed"]),
             "open": len(ledger["state"]["open"])}]
    for d in snaps[1:]:
        pub = read_published(d)
        as_of = pub["envelope"]["generated_at"]
        merged, ledger, audit = merge(ledger, as_of, {fp: pub}, LIVE_EXIT)
        pub_closed = set(pub["closed"])
        rec_closed = {key_of(r) for r in merged["sig_hist"] if r.get("status") != "ACTIVE"}
        rows.append({
            "snapshot": d.name, "as_of": as_of, "base_as_of": audit["base_as_of"], "level": audit["level"],
            "red": [f"{x['kind']}:{x.get('trade')}" for x in audit["red"]],
            "amber": [f"{x['kind']}:{x.get('trade', '')}" for x in audit["amber"]],
            "record_closed": len(rec_closed), "published_closed": len(pub_closed),
            "held_back_from_published": sorted(rec_closed - pub_closed),
            "published_not_in_record": sorted(pub_closed - rec_closed),
        })
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify-seed", help="migration proof: seed + same-data publish == committed bytes")
    v.add_argument("--state-dir", default=str(ROOT / "results"))
    v.add_argument("--out-dir", default=None)
    r = sub.add_parser("replay", help="dry run of the merge over the weekly archive snapshots")
    r.add_argument("--archive", default=str(ROOT / "results" / "archive"))
    c = sub.add_parser("cron", help="run the weekly cron with the forward record ON (args pass through)")
    c.add_argument("cron_args", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    if a.cmd == "cron":
        return cron_main([x for x in a.cron_args if x != "--"])
    if a.cmd == "verify-seed":
        import tempfile
        out = Path(a.out_dir) if a.out_dir else Path(tempfile.mkdtemp(prefix="fr_verify_"))
        res = verify_seed(Path(a.state_dir), out)
        print(json.dumps(res, indent=2))
        return 0 if all(v == "IDENTICAL" for v in res["files"].values()) else 1
    for row in replay(Path(a.archive)):
        print(json.dumps(row, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
