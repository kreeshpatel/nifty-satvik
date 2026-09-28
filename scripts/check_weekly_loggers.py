"""The watched-book loggers must have actually logged THIS week — checked after the commit, in RED.

## Why this exists

`run_blend_paper.py` crashed on every Saturday from inception and its step is non-fatal, so the cron
stayed green while `blend_hybrid_paper.json` sat at `n_points: 0` for about seven weeks. Nothing was
wrong with the alerting: there was no alert. The file existed, the job exited 0, and the only artifact
that would have shown the problem was the file's own contents.

Three loggers write forward evidence that cannot be backfilled — a week they miss is a week of the
watched books' history permanently gone:

  * `results/blend_hybrid_paper.json`   — the swing x low-vol blend (0107), the forward evidence for the
                                          multi-sleeve fork and the strongest drawdown lever on the board
  * `results/breadth50_forward.json`    — the breadth-50 watched book (§4's second-book question)
  * `results/signal_quality_forward.csv` — the 4-axis family, read at the quarterly wall

## Why it runs AFTER the commit, and why the producers stay non-fatal

Every producer step runs BEFORE the commit. Making one hard-fail would abort the job before the weekly
state is committed, so a side-book logger's defect would withhold the LIVE book's own record — trading a
silent miss for a lost week. The cron already learned this: the signal-quality `--validate` step sits
after the publish for exactly that reason, and its comment says so.

So the producers keep their `|| echo ::warning::` and this runs after the push, where a failure is loud
and costs nothing that has not already been saved.

## What "logged this week" means

The scan's own `generated_at` is the reference. A logger whose `asof` is older than that ran against
stale inputs or did not run at all — which is the `n_points: 0` failure mode, stated as a date rather
than inferred from a count.

    python scripts/check_weekly_loggers.py            # RED on a stale logger
    python scripts/check_weekly_loggers.py --warn-only # report without failing (local use)
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

# Loggers that must advance every scan, with the field that proves they did.
JSON_LOGGERS = {
    "blend_hybrid_paper.json": "the swing x low-vol blend (0107) — forward evidence for the sleeve fork",
    "breadth50_forward.json": "the breadth-50 watched book (§4's second-book question)",
}
CSV_LOGGER = "signal_quality_forward.csv"
# The capital book's own streams, rebuilt from inception every run (wired 2026-09-28). Their `as_of`
# column must carry THIS scan, for the same reason as the JSON loggers: a file that is rewritten with a
# stale payload still "updates", so the contract alone cannot see the miss.
AS_OF_COLUMN_LOGGERS = {
    "brain/position_log.csv.gz": "the capital book's daily holdings",
    "brain/management_events.jsonl": "what was DONE to each position — tranches, ratchets, halts",
}


def scan_as_of() -> str | None:
    p = RESULTS / "signals_today_weekly.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("generated_at")


def check(as_of: str | None = None) -> list[str]:
    """One message per stale or missing logger. Empty means every watched book advanced."""
    as_of = as_of or scan_as_of()
    problems: list[str] = []
    if not as_of:
        return ["no results/signals_today_weekly.json — cannot tell which week this is"]

    for name, why in JSON_LOGGERS.items():
        p = RESULTS / name
        if not p.is_file():
            problems.append(f"{name} is MISSING — {why}")
            continue
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:                        # noqa: BLE001 — unreadable is a failure too
            problems.append(f"{name} is unreadable ({exc}) — {why}")
            continue
        logged = str(payload.get("asof") or "")
        if logged < str(as_of):
            problems.append(
                f"{name} last logged {logged or 'never'} but the scan is {as_of} — this week is missing "
                f"from {why}. n_points={payload.get('n_points')}")

    for name, why in AS_OF_COLUMN_LOGGERS.items():
        q = RESULTS / name
        if not q.is_file():
            problems.append(f"{name} is MISSING — {why}")
            continue
        try:
            if name.endswith(".jsonl"):
                lines = [ln for ln in q.read_text(encoding="utf-8").splitlines() if ln.strip()]
                stamps = {json.loads(ln).get("as_of") for ln in lines}
            else:
                import gzip
                with gzip.open(q, "rt", encoding="utf-8") as fh:
                    stamps = {r.get("as_of") for r in csv.DictReader(fh)}
        except Exception as exc:                        # noqa: BLE001
            problems.append(f"{name} is unreadable ({exc}) — {why}")
            continue
        stamps.discard(None)
        # EMPTY IS LEGITIMATE and must not be a failure: a week with no management event is a real
        # week. What is not legitimate is a file whose newest stamp is older than this scan.
        if stamps and max(stamps) < str(as_of):
            problems.append(f"{name} last stamped {max(stamps)} but the scan is {as_of} — {why}")

    p = RESULTS / CSV_LOGGER
    if not p.is_file():
        problems.append(f"{CSV_LOGGER} is MISSING — the 4-axis family read at the quarterly wall")
    else:
        with open(p, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        if not rows:
            problems.append(f"{CSV_LOGGER} has no rows — the collector produced an empty table")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--warn-only", action="store_true", help="report without failing the job")
    args = ap.parse_args(argv)

    as_of = scan_as_of()
    problems = check(as_of)
    if not problems:
        print(f"weekly loggers: all advanced to {as_of}")
        return 0
    for p in problems:
        print(f"{'::warning::' if args.warn_only else '::error::'}{p}")
    print(f"{len(problems)} watched-book logger(s) did not record this week. A missed week cannot be "
          f"backfilled: these books are forward evidence and §3 forbids reconstructed history.")
    return 0 if args.warn_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
