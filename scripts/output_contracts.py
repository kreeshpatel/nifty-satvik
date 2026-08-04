"""Output-contract enforcement — the dead-man stops vouching for jobs that persisted nothing.

**Why.** S2-F3 made a job's *firing* provable. It did not make its *output* provable, and the gap
cost real money: the 2026-08-01 scanner run exited 0, judged 17 cards for $4.00, and committed none
of them because `.gitignore` made its `git add` a silent no-op. Every heartbeat stayed green.

**The receipt is the commit diff.** A scheduled job's contract (`results/output_contracts.json`)
names the paths its run MUST update. This module finds the job's most recent cron commit and asserts
the diff actually touched those paths. A job that ran but wrote nothing goes **red by name**.

Two tiers per contract, deliberately:
  * `must_update`            — absent from the diff => **BREACH** (red).
  * `must_update_if_produced` — absent => **WARN**, not red. For genuinely conditional artifacts
                                (the judge log needs an API key; a scan may find nothing).

Pure git + stdlib. No network, no API token — it reads the checkout the monitor already has.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "results" / "output_contracts.json"


def _git(*args: str, cwd: Path | None = None) -> str:
    r = subprocess.run(["git", *args], cwd=str(cwd or ROOT), capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def load_contracts(path: Path | None = None) -> list[dict]:
    p = path or CONTRACTS
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("contracts", [])


def _last_cron_commit(prefix: str) -> tuple[str, str] | None:
    """(sha, iso_date) of the most recent commit whose subject starts with `prefix`."""
    # --fixed-strings, NOT a regex: the prefixes contain "(" and ")" (e.g. "chore(weekly):"),
    # which an ERE would read as a capture group and silently fail to match.
    out = _git("log", "-1", f"--grep={prefix}", "--fixed-strings",
               "--format=%H%x09%cI", "--all")
    line = out.strip().splitlines()[0] if out.strip() else ""
    if not line or "\t" not in line:
        return None
    sha, iso = line.split("\t", 1)
    return sha.strip(), iso.strip()


def _paths_in_commit(sha: str) -> set[str]:
    out = _git("show", "--name-only", "--format=", sha)
    return {ln.strip() for ln in out.splitlines() if ln.strip()}


def _touched(declared: str, changed: set[str]) -> bool:
    """A declared path is satisfied by an exact match or by any file beneath it (directories)."""
    d = declared.rstrip("/")
    return any(c == d or c.startswith(d + "/") for c in changed)


def check_output_contracts(now_utc: datetime | None = None,
                           contracts_path: Path | None = None) -> dict:
    """Per-job: did the last cron commit actually persist what the contract requires?"""
    now = now_utc or datetime.now(timezone.utc)
    rows, breaches, warns = [], [], []

    for c in load_contracts(contracts_path):
        job = c["job"]
        found = _last_cron_commit(c["commit_prefix"])
        if found is None:
            rows.append({"job": job, "status": "NO_COMMIT", "detail":
                         f"no commit matching {c['commit_prefix']!r} in history"})
            # No commit at all is only a breach if the job is supposed to have run by now.
            if c.get("must_update"):
                breaches.append(f"{job}: no cron commit ever found")
            continue

        sha, iso = found
        changed = _paths_in_commit(sha)
        try:
            age_days = (now - datetime.fromisoformat(iso)).total_seconds() / 86400.0
        except ValueError:
            age_days = float("nan")

        missing = [p for p in c.get("must_update", []) if not _touched(p, changed)]
        missing_soft = [p for p in c.get("must_update_if_produced", []) if not _touched(p, changed)]
        stale = age_days == age_days and age_days > c.get("cadence_days", 9)

        status = "OK"
        if missing:
            status = "CONTRACT_BREACH"
            breaches.append(f"{job}: last commit {sha[:8]} did not touch {', '.join(missing)}")
        elif stale:
            status = "STALE"
            breaches.append(f"{job}: last cron commit is {age_days:.1f}d old "
                            f"(cadence {c.get('cadence_days')}d)")
        elif missing_soft:
            status = "OK_WITH_WARN"
        if missing_soft:
            warns.append(f"{job}: conditional artifact(s) not persisted: {', '.join(missing_soft)}")

        rows.append({"job": job, "status": status, "last_commit": sha[:8], "committed_at": iso,
                     "age_days": None if age_days != age_days else round(age_days, 2),
                     "missing_required": missing, "missing_conditional": missing_soft,
                     "n_paths_in_commit": len(changed)})

    return {
        "overall": "RED" if breaches else ("WARN" if warns else "OK"),
        "checked_at": now.isoformat(),
        "jobs": rows, "breaches": breaches, "warnings": warns,
        "_standard": "the commit diff is the receipt — a green workflow that persisted nothing is red here",
    }


def annotations(result: dict) -> list[str]:
    """GitHub Actions annotations, so a breach is loud on the next monitor run."""
    out = [f"::error::output-contract BREACH — {b}" for b in result.get("breaches", [])]
    out += [f"::warning::output-contract — {w}" for w in result.get("warnings", [])]
    return out


def main() -> int:
    res = check_output_contracts()
    for line in annotations(res):
        print(line)
    print(json.dumps(res, indent=2))
    return 1 if res["overall"] == "RED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
