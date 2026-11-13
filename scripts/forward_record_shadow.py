"""SHADOW run of the forward record (ADR-0018): what the record would have published this week. It never
commits and never touches the published results.

After the real Saturday scan has committed its record, this:

  1. takes the PREVIOUS week's published record from the immutable archive (`results/archive/<as_of>/`,
     the latest snapshot older than the week the live scan just published) and copies it into a TEMP
     state directory, where the forward record seeds from it exactly as the first live run would;
  2. runs the unmodified weekly cron through `forward_record.py cron` with `--state-dir <temp>`, so
     every file the scan writes lands in the temp directory. Two outputs are kept: the forward record
     (`<temp>/`) and the scan's own unmerged rebuild (`<temp>/raw/`);
  3. diffs both against what the live scan committed, classifies every difference, and writes
     `<temp>/shadow_report.json` and a markdown summary (to `$GITHUB_STEP_SUMMARY` in Actions).

CLEAN — the definition the switch-on decision reads (ADR-0018). A shadow run is CLEAN when BOTH hold:

  (a) PARITY. The shadow's unmerged rebuild is byte-identical to the live commit, in all five published
      files. Then the shadow saw the same data and code as the live scan, and every remaining
      difference is the forward record's doing. A parity failure is UNEXPECTED (data vintage): the
      comparison is not trustworthy, so the run is not clean.
  (b) EVERY difference between the shadow's forward record and the live commit is EXPECTED, meaning it
      is the frozen past standing where the rebuilt past would have been, and the merge's own audit
      names it:
        - a frozen closed trade the rebuild restated, dropped or re-opened (audit: restated,
          restated_rebase, vanished_closed, closed_reopened_in_rebuild);
        - a frozen open trade the rebuild lost, carried by the record (audit: vanished_open,
          pinned_rule_rebuild_missing);
        - a retroactive trade the rebuild added and the record suppressed (audit: suppressed_retroactive);
        - an open trade managed under the exit rule it was opened under (ledger: pinned to a rule that
          is not the current one);
        - an approved amendment applied this week;
        - NAV rows on or before the frozen week (the frozen past), and later rows that equal the live
          rows times the audit's chain-link scale;
        - the derived fields of those: analytics, closed-trade count, open-position count, the NAV
          totals, and row/card order. These are expected only while every item they derive from is
          expected and none is unexpected.
      Anything else is UNEXPECTED: a field of the envelope, the paper book or a fresh buy card that
      differs, a trade or card that differs with no audit finding behind it, or a post-frozen NAV row
      that is not a clean chain-link.

One unexpected difference makes the run NOT CLEAN. Expected differences are not "good"; they are
listed so the owner can see exactly what the frozen record would have held this week.

    python scripts/forward_record_shadow.py --out-dir /tmp/fr_shadow -- --start 2026-07-04
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import forward_record as FR  # noqa: E402

PUBLISHED = FR._PUBLISHED_FILES
ENV, HIST, AN, PF, NAV = PUBLISHED
REPORT_NAME = "shadow_report.json"

# audit finding kinds that explain each shape of difference (see the module docstring)
_KEEPS_FROZEN = {"restated", "restated_rebase", "vanished_closed", "closed_reopened_in_rebuild",
                 "vanished_open", "pinned_rule_rebuild_missing", "open_closed_retroactively"}
_SUPPRESSES = {"suppressed_retroactive"}


class ShadowError(RuntimeError):
    pass


# ── preparing the temp state ───────────────────────────────────────────────────────────────────

def previous_record(archive: Path, live_as_of: str) -> Path:
    """The latest archived snapshot of a week BEFORE `live_as_of` (a re-run of that week wins)."""
    snaps = sorted(d for d in Path(archive).iterdir()
                   if d.is_dir() and d.name.split("__rerun-")[0] < live_as_of
                   and all((d / f).exists() for f in (ENV, HIST)))
    if not snaps:
        raise ShadowError(f"no archived snapshot older than {live_as_of} in {archive}")
    return snaps[-1]


def _guard_out_dir(out_dir: Path, live_dir: Path) -> None:
    out, live, results = Path(out_dir).resolve(), Path(live_dir).resolve(), (ROOT / "results").resolve()
    for protected in (live, results):
        if out == protected or protected in out.parents:
            raise ShadowError(f"--out-dir {out} is inside {protected}: a shadow run never writes the published results")


def prepare(out_dir: Path, prev_dir: Path) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if FR.load_ledger(out_dir) is not None:
        raise ShadowError(f"{out_dir} already holds a ledger: a shadow run must seed fresh")
    for f in PUBLISHED:
        if (Path(prev_dir) / f).exists():
            shutil.copy2(Path(prev_dir) / f, out_dir / f)


def run_shadow(out_dir: Path, cron_args: list[str], *, live_dir: Path | None = None,
               archive: Path | None = None) -> dict:
    live_dir = Path(live_dir or ROOT / "results")
    archive = Path(archive or live_dir / "archive")
    out_dir = Path(out_dir)
    _guard_out_dir(out_dir, live_dir)
    if any(a == "--state-dir" or a.startswith("--state-dir=") for a in cron_args):
        raise ShadowError("the shadow sets --state-dir itself")
    live_as_of = json.loads((live_dir / ENV).read_text(encoding="utf-8"))["generated_at"]
    prev = previous_record(archive, live_as_of)
    prepare(out_dir, prev)
    rc = FR.cron_main(list(cron_args) + ["--state-dir", str(out_dir)], raw_dir=out_dir / "raw",
                      amendments_dir=live_dir)
    if rc != 0:
        raise ShadowError(f"the wrapped cron exited {rc}")
    report = compare(live_dir, out_dir, out_dir / "raw")
    report["seeded_from"] = str(prev.relative_to(archive.parent) if archive.parent in prev.parents else prev)
    (out_dir / REPORT_NAME).write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    return report


# ── the diff classifier ───────────────────────────────────────────────────────────────────────

def _load(d: Path) -> dict:
    d = Path(d)
    out = {"env": json.loads((d / ENV).read_text(encoding="utf-8")),
           "hist": json.loads((d / HIST).read_text(encoding="utf-8")),
           "an": json.loads((d / AN).read_text(encoding="utf-8")) if (d / AN).exists() else {},
           "pf": json.loads((d / PF).read_text(encoding="utf-8")) if (d / PF).exists() else {}}
    nav = pd.read_csv(d / NAV, dtype={"date": str}, float_precision="round_trip") if (d / NAV).exists() else None
    out["nav"] = FR.nav_rows(nav)
    return out


def _item(file: str, item: str, expected: bool, why: str) -> dict:
    return {"file": file, "item": item, "class": "expected" if expected else "unexpected", "why": why}


def _card_key(c: dict) -> str:
    return FR.key_of(c) if c.get("bought_date") else f"fresh:{c.get('ticker')}"


def classify(live: dict, merged: dict, audit: dict, pinned: set[str], amended: set[str]) -> list[dict]:
    """Every difference between the live commit and the shadow's forward record, classified."""
    kinds: dict[str, set] = {}
    for f in audit.get("red", []) + audit.get("amber", []) + audit.get("info", []):
        if f.get("trade"):
            kinds.setdefault(f["trade"], set()).add(f["kind"])
    A = audit.get("base_as_of", "")
    scale = float(audit.get("nav_chain_link_scale", 1.0))
    out: list[dict] = []

    def explain_trade(k: str, where: str) -> tuple[bool, str]:
        ks = kinds.get(k, set())
        if k in amended:
            return True, "amendment applied this week"
        if where == "live_only" and ks & _SUPPRESSES:
            return True, "retroactive trade suppressed by the record (" + ", ".join(sorted(ks)) + ")"
        if where in ("record_only", "differs") and ks & _KEEPS_FROZEN:
            return True, "frozen past kept over the rebuilt past (" + ", ".join(sorted(ks & _KEEPS_FROZEN)) + ")"
        if where == "differs" and k in pinned:
            return True, "managed under the exit rule it was opened under"
        return False, ("no audit finding explains it" if not ks else
                       f"audit says {sorted(ks)}, which does not explain a {where.replace('_', ' ')} difference")

    # trades (signals_history)
    L = {FR.key_of(r): r for r in live["hist"]}
    M = {FR.key_of(r): r for r in merged["hist"]}
    for k in sorted(set(L) | set(M)):
        where = "live_only" if k not in M else "record_only" if k not in L else ("differs" if L[k] != M[k] else None)
        if where:
            ok, why = explain_trade(k, where)
            out.append(_item(HIST, f"{k} ({where.replace('_', ' ')})", ok, why))
    trade_items = [x for x in out if x["file"] == HIST]
    derived_ok = bool(trade_items) and all(x["class"] == "expected" for x in trade_items)
    common = [k for k in (FR.key_of(r) for r in live["hist"]) if k in M]
    if common != [k for k in (FR.key_of(r) for r in merged["hist"]) if k in L]:
        out.append(_item(HIST, "row order", derived_ok, "order follows the frozen record" if derived_ok
                         else "rows reordered with no expected trade difference"))

    # analytics: derived from the trades
    for key in sorted(set(live["an"]) | set(merged["an"])):
        if live["an"].get(key) != merged["an"].get(key):
            out.append(_item(AN, key, derived_ok, "derived from expected trade differences" if derived_ok
                             else "analytics differ while the trades do not (or differ unexpectedly)"))

    # envelope: cards by key, everything else must match
    le, me = live["env"], merged["env"]
    for key in sorted((set(le) | set(me)) - {"signals", "n_positions"}):
        if le.get(key) != me.get(key):
            out.append(_item(ENV, key, False, "envelope field differs; the record only changes cards"))
    if le.get("n_positions") != me.get("n_positions"):
        out.append(_item(ENV, "n_positions", derived_ok, "count of the record's open trades" if derived_ok
                         else "open count differs with no expected trade difference"))
    LC = {_card_key(c): c for c in le.get("signals", [])}
    MC = {_card_key(c): c for c in me.get("signals", [])}
    record_tickers = {k.split("|", 1)[0] for k, r in M.items() if r.get("status") == "ACTIVE"}
    for k in sorted(set(LC) | set(MC)):
        where = "live_only" if k not in MC else "record_only" if k not in LC else ("differs" if LC[k] != MC[k] else None)
        if not where:
            continue
        if k.startswith("fresh:"):
            t = k.split(":", 1)[1]
            ok = where == "live_only" and t in record_tickers and t not in {x.split("|", 1)[0] for x in L
                                                                              if L[x].get("status") == "ACTIVE"}
            out.append(_item(ENV, f"fresh card {t} ({where.replace('_', ' ')})", ok,
                             "the record already holds this name from a prior week" if ok
                             else "fresh buy cards come straight from the rebuild and must match"))
        else:
            ok, why = explain_trade(k, where)
            out.append(_item(ENV, f"card {k} ({where.replace('_', ' ')})", ok, why))
    if [k for k in (_card_key(c) for c in le.get("signals", [])) if k in MC] != \
            [k for k in (_card_key(c) for c in me.get("signals", [])) if k in LC]:
        out.append(_item(ENV, "card order", derived_ok, "order follows the frozen record" if derived_ok
                         else "cards reordered with no expected trade difference"))

    # paper book: only the record's totals may move
    nav_fields = {"total_value", "peak_value", "record_nav_chain_link"}
    for key in sorted(set(live["pf"]) | set(merged["pf"])):
        if live["pf"].get(key) == merged["pf"].get(key):
            continue
        if key in nav_fields:
            ok = scale != 1.0 or _nav_past_differs(live["nav"], merged["nav"], A)
            out.append(_item(PF, key, ok, "the record's frozen / chain-linked NAV" if ok
                             else "NAV total differs with no NAV gap in the audit"))
        elif key == "total_trades":
            out.append(_item(PF, key, derived_ok, "closed-trade count of the record" if derived_ok
                             else "closed count differs with no expected trade difference"))
        else:
            out.append(_item(PF, key, False, "paper-book field differs; the record does not touch the book"))

    # NAV curve
    Ln, Mn = dict((d, v) for d, v in live["nav"]), dict((d, v) for d, v in merged["nav"])
    past = [d for d in sorted(set(Ln) | set(Mn)) if d <= A and Ln.get(d) != Mn.get(d)]
    if past:
        out.append(_item(NAV, f"{len(past)} row(s) on or before {A}", True,
                         "frozen past NAV kept over the rebuilt past"))
    bad_new = [d for d in sorted(set(Ln) | set(Mn)) if d > A and not _chain_ok(Ln.get(d), Mn.get(d), scale)]
    if bad_new:
        out.append(_item(NAV, f"{len(bad_new)} row(s) after {A} (first {bad_new[0]})", False,
                         "a post-frozen NAV row is not the live row times the chain-link scale"))
    elif scale != 1.0 and any(d > A for d in Mn):
        out.append(_item(NAV, f"rows after {A}", True, f"chain-linked onto the frozen level (scale {scale:.6f})"))
    return out


def _chain_ok(live_v, rec_v, scale: float) -> bool:
    if live_v is None or rec_v is None:
        return False
    if scale == 1.0:
        return live_v == rec_v
    return abs(rec_v - live_v * scale) <= 1e-9 * max(1.0, abs(rec_v))


def _nav_past_differs(Ln: list, Mn: list, A: str) -> bool:
    a, b = dict((d, v) for d, v in Ln), dict((d, v) for d, v in Mn)
    return any(a.get(d) != b.get(d) for d in set(a) | set(b) if d <= A)


def parity(live_dir: Path, raw_dir: Path) -> list[dict]:
    """(a) the shadow's own rebuild against the live commit, byte for byte."""
    out = []
    for f in PUBLISHED:
        a, b = Path(live_dir) / f, Path(raw_dir) / f
        if not a.exists() or not b.exists() or a.read_bytes() != b.read_bytes():
            out.append(_item(f, "whole file (parity)", False,
                             "data vintage: the shadow's own rebuild differs from the live scan's, so it did "
                             "not see the same data or code and the comparison cannot be trusted"))
    return out


def compare(live_dir: Path, rec_dir: Path, raw_dir: Path) -> dict:
    audit = json.loads((FR.record_dir(rec_dir) / FR.AUDIT_NAME).read_text(encoding="utf-8"))
    ledger = FR.load_ledger(rec_dir) or {}
    cur = ledger.get("current_rule")
    pinned = {k for k, o in (ledger.get("state", {}).get("open", {}) or {}).items() if o.get("rule") != cur}
    amended = {a["key"] for a in audit.get("amendments_applied", [])}
    par = parity(live_dir, raw_dir)
    diffs = classify(_load(live_dir), _load(rec_dir), audit, pinned, amended)
    items = par + diffs
    n_unexp = sum(1 for x in items if x["class"] == "unexpected")
    return {
        "verdict": "CLEAN" if n_unexp == 0 else "NOT CLEAN",
        "live_as_of": json.loads((Path(live_dir) / ENV).read_text(encoding="utf-8")).get("generated_at"),
        "base_as_of": audit.get("base_as_of"), "audit_level": audit.get("level"),
        "parity": "IDENTICAL" if not par else f"{len(par)} file(s) differ",
        "n_expected": sum(1 for x in items if x["class"] == "expected"), "n_unexpected": n_unexp,
        "differences": items,
        "definition": "CLEAN = parity (shadow rebuild byte-identical to the live commit) AND every record-vs-live "
                      "difference classified expected (frozen past vs rebuilt past, named by the audit). "
                      "See scripts/forward_record_shadow.py and ADR-0018.",
    }


def render_md(r: dict) -> str:
    lines = [f"## Forward-record shadow — {r['verdict']}", "",
             f"- live scan as-of **{r['live_as_of']}**; record seeded from `{r.get('seeded_from')}` "
             f"(frozen through {r['base_as_of']})",
             f"- parity (shadow rebuild vs live commit): **{r['parity']}**",
             f"- audit level: **{r['audit_level']}**; differences: {r['n_expected']} expected, "
             f"**{r['n_unexpected']} unexpected**", ""]
    if r["differences"]:
        lines += ["| class | file | item | why |", "|---|---|---|---|"]
        for x in sorted(r["differences"], key=lambda x: (x["class"] != "unexpected", x["file"], x["item"])):
            lines.append(f"| {x['class']} | {x['file']} | {x['item']} | {x['why']} |")
    else:
        lines.append("No differences: the record would have published exactly what the live scan did.")
    lines += ["", f"_{r['definition']}_", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", required=True, help="temp directory for the shadow state (never results/)")
    ap.add_argument("--live-dir", default=str(ROOT / "results"))
    ap.add_argument("--archive", default=None)
    ap.add_argument("--summary", default=None, help="append the markdown summary here ($GITHUB_STEP_SUMMARY)")
    ap.add_argument("cron_args", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    r = run_shadow(Path(a.out_dir), [x for x in a.cron_args if x != "--"], live_dir=Path(a.live_dir),
                   archive=Path(a.archive) if a.archive else None)
    md = render_md(r)
    (Path(a.out_dir) / "shadow_report.md").write_text(md, encoding="utf-8")
    if a.summary:
        with open(a.summary, "a", encoding="utf-8") as fh:
            fh.write(md)
    print(md)
    if r["verdict"] != "CLEAN":
        print(f"::error::forward-record shadow NOT CLEAN: {r['n_unexpected']} unexpected difference(s)")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
