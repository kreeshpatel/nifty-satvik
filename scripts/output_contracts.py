"""Output-contract enforcement — the dead-man stops vouching for jobs that persisted nothing.

**Why.** S2-F3 made a job's *firing* provable. It did not make its *output* provable, and the gap
cost real money: the 2026-08-01 scanner run exited 0, judged 17 cards for $4.00, and committed none
of them because `.gitignore` made its `git add` a silent no-op. Every heartbeat stayed green.

**The receipt is the commit.** A scheduled job's contract (`results/output_contracts.json`) names
the paths its runs must persist. This module finds the job's most recent cron commit and checks
those paths against it. A job that ran but never persists an artifact goes **red by name**.

Two tiers per contract, deliberately:
  * `must_update`            — never persisted, or stopped updating => **BREACH** (red).
  * `must_update_if_produced` — absent from this run's diff => **WARN**, not red. For genuinely
                                conditional artifacts (the judge log needs an API key; a scan may
                                find nothing).

**What "persisted" means, and what it deliberately does not.** The first draft asked whether each
path appeared in the last cron commit's *diff*, and that was wrong. On 2026-08-04 the scanner was
re-dispatched over the same as-of-2026-07-31 book; it produced byte-identical weekly files, so git
correctly recorded no diff for them, and the checker convicted a healthy job. A cron whose output is
unchanged is working. **A false positive in an alarm is as damaging as a missed defect** — it is how
alarms stop being read. So a required path breaches only when it is absent from the tree at the
job's last cron commit (never persisted at all — the silent-`git add` signature), or when no commit
of that job has written it inside the staleness bound (it has stopped updating entirely).

**Two states, not one, when the answer is unknown.** `NO_COMMIT` means the history was searched and
the job's commits are not in it. `INDETERMINATE` means the history could not be searched — a shallow
checkout, or one that does not reach back past the cadence window. The first CI run of this module
confused the two and went RED against commits that plainly existed on `main`, because
`actions/checkout` defaults to `fetch-depth: 1`. Absent evidence is not negative evidence; that rule
is S2.14's, and it applies to this checker's own reasoning first.

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


def history_adequacy(cadence_days: float, now: datetime, repo: Path | None = None) -> dict:
    """Can this checkout answer "did job X commit recently?" at all?

    ABSENT EVIDENCE IS NOT NEGATIVE EVIDENCE — the lesson S2.14 records about the intraday scans,
    applied here to the checker's own reasoning. A shallow clone contains no cron commits, and a
    naive search reports that as "no cron commit ever found": a confident RED derived from a repo
    that was never asked to hold the answer. That is precisely how the first CI run of this module
    failed, against commits that plainly existed on main.

    Two ways the evidence base can be missing:
      * the clone is SHALLOW (`actions/checkout` defaults to fetch-depth 1);
      * the history is complete-as-fetched but does not REACH BACK past the job's cadence window,
        so an absence inside that window is unobservable rather than false.
    """
    shallow = _git("rev-parse", "--is-shallow-repository", cwd=repo).strip() == "true"
    n = _git("rev-list", "--count", "--all", cwd=repo).strip()
    n_commits = int(n) if n.isdigit() else 0
    oldest_iso = (_git("log", "--all", "--reverse", "--format=%cI", cwd=repo).splitlines() or [""])[0].strip()
    reaches_back = None
    if oldest_iso and not shallow:
        try:
            span_days = (now - datetime.fromisoformat(oldest_iso)).total_seconds() / 86400.0
            reaches_back = span_days >= cadence_days
        except ValueError:
            reaches_back = None
    # A TRUNCATED history is inadequate; a merely YOUNG one is not. `git clone --depth`/
    # `--shallow-since` always set the shallow flag, so that flag is the reliable truncation
    # signal; a complete repo that happens to be two days old is hiding nothing.
    #
    # `reaches_back_past_cadence` is therefore reported but does not by itself condemn the
    # checkout. It is applied per-job instead, and only to the one verdict it can invalidate:
    # "this job never committed" is unsupportable if the history is shorter than the window the
    # claim covers. (An early draft folded it into `adequate` and made a legitimately young repo
    # unanswerable — the same over-reach in the opposite direction.)
    adequate = (not shallow) and n_commits > 1
    return {"adequate": adequate, "shallow": shallow, "n_commits": n_commits,
            "oldest_commit": oldest_iso or None, "reaches_back_past_cadence": reaches_back}


def load_contracts(path: Path | None = None) -> list[dict]:
    p = path or CONTRACTS
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("contracts", [])


def _last_cron_commit(prefix: str, repo: Path | None = None) -> tuple[str, str] | None:
    """(sha, iso_date) of the most recent commit whose subject starts with `prefix`."""
    # --fixed-strings, NOT a regex: the prefixes contain "(" and ")" (e.g. "chore(weekly):"),
    # which an ERE would read as a capture group and silently fail to match.
    out = _git("log", "-1", f"--grep={prefix}", "--fixed-strings",
               "--format=%H%x09%cI", "--all", cwd=repo)
    line = out.strip().splitlines()[0] if out.strip() else ""
    if not line or "\t" not in line:
        return None
    sha, iso = line.split("\t", 1)
    return sha.strip(), iso.strip()


def _paths_in_commit(sha: str, repo: Path | None = None) -> set[str]:
    out = _git("show", "--name-only", "--format=", sha, cwd=repo)
    return {ln.strip() for ln in out.splitlines() if ln.strip()}


def _exists_at(sha: str, path: str, repo: Path | None = None) -> bool:
    """Is `path` present in the tree at `sha`? (A directory counts if it holds anything.)"""
    d = path.rstrip("/")
    return bool(_git("ls-tree", "-r", "--name-only", sha, "--", d, cwd=repo).strip())


def _last_touched_by_job(prefix: str, path: str, repo: Path | None = None) -> str | None:
    """ISO date this job's commits last MODIFIED `path`, or None if none ever did.

    Scoped to the job's own commits on purpose: an artifact kept alive only by hand edits is not
    evidence that the cron is persisting it.
    """
    out = _git("log", "-1", f"--grep={prefix}", "--fixed-strings", "--format=%cI", "--all",
               "--", path.rstrip("/"), cwd=repo).strip()
    return out.splitlines()[0].strip() if out else None


def _touched(declared: str, changed: set[str]) -> bool:
    """A declared path is satisfied by an exact match or by any file beneath it (directories)."""
    d = declared.rstrip("/")
    return any(c == d or c.startswith(d + "/") for c in changed)


def check_output_contracts(now_utc: datetime | None = None,
                           contracts_path: Path | None = None,
                           repo: Path | None = None) -> dict:
    """Per-job: did the last cron commit actually persist what the contract requires?"""
    now = now_utc or datetime.now(timezone.utc)
    rows, breaches, warns, indeterminate = [], [], [], []
    contracts = load_contracts(contracts_path)

    # One adequacy probe, sized by the LONGEST cadence any contract needs to see back through.
    widest = max((c.get("cadence_days", 9) for c in contracts), default=9)
    hist = history_adequacy(widest, now, repo=repo)

    for c in contracts:
        job = c["job"]
        if not hist["adequate"]:
            # The checkout cannot answer the question. Say so; do NOT convict.
            rows.append({"job": job, "status": "INDETERMINATE", "history": hist, "detail":
                         "insufficient git history to search for this job's commits — "
                         "absent evidence, not a breach"})
            indeterminate.append(job)
            continue

        found = _last_cron_commit(c["commit_prefix"], repo=repo)
        if found is None:
            # Per-job adequacy: "this job never committed" is unsupportable when the history is
            # shorter than the cadence window the claim covers.
            job_hist = history_adequacy(c.get("cadence_days", 9), now, repo=repo)
            if job_hist["reaches_back_past_cadence"] is False:
                rows.append({"job": job, "status": "INDETERMINATE", "history": job_hist, "detail":
                             f"history spans less than this job's {c.get('cadence_days')}d cadence "
                             "window — an absence inside it is unobservable, not false"})
                indeterminate.append(job)
                continue
            rows.append({"job": job, "status": "NO_COMMIT", "detail":
                         f"no commit matching {c['commit_prefix']!r} in history"})
            # No commit at all is only a breach if the job is supposed to have run by now.
            if c.get("must_update"):
                breaches.append(f"{job}: no cron commit ever found")
            continue

        sha, iso = found
        changed = _paths_in_commit(sha, repo=repo)
        try:
            age_days = (now - datetime.fromisoformat(iso)).total_seconds() / 86400.0
        except ValueError:
            age_days = float("nan")

        # The predicate is NOT "appeared in the last commit's diff". That was the first draft and it
        # was wrong: the 2026-08-04 dispatch re-ran the same as-of-2026-07-31 book, produced
        # byte-identical weekly files, and git — correctly — recorded no diff for them. A cron whose
        # output is unchanged is healthy, and calling it a breach is a false alarm. A false positive
        # in an alarm is as damaging as a missed defect: it is how alarms stop being read.
        #
        # The defect class is an artifact that NEVER LANDS, not one that did not change this week.
        # So a required path breaches only if it is absent from the tree at the job's last cron
        # commit (never persisted at all), or no commit of this job has touched it within the
        # staleness bound (it has stopped updating entirely).
        stale_bound = c.get("staleness_days") or 4 * c.get("cadence_days", 9)
        missing, gone_stale = [], []
        for p in c.get("must_update", []):
            if not _exists_at(sha, p, repo=repo):
                missing.append(p)
                continue
            if _touched(p, changed):
                continue                       # updated by this very run — nothing to check
            last_iso = _last_touched_by_job(c["commit_prefix"], p, repo=repo)
            if last_iso is None:
                missing.append(p)              # in the tree, but no run of this job ever wrote it
                continue
            try:
                age = (now - datetime.fromisoformat(last_iso)).total_seconds() / 86400.0
            except ValueError:
                continue
            if age > stale_bound:
                gone_stale.append(f"{p} (last written {age:.0f}d ago, bound {stale_bound:.0f}d)")

        missing_soft = [p for p in c.get("must_update_if_produced", []) if not _touched(p, changed)]
        stale = age_days == age_days and age_days > c.get("cadence_days", 9)

        status = "OK"
        if missing or gone_stale:
            status = "CONTRACT_BREACH"
            if missing:
                breaches.append(f"{job}: {', '.join(missing)} NEVER PERSISTED by this job "
                                f"(absent from the tree at {sha[:8]}, or never written by any of "
                                f"its commits) — the silent-`git add` signature")
            if gone_stale:
                breaches.append(f"{job}: has stopped updating {', '.join(gone_stale)}")
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

    if breaches:
        overall = "RED"
    elif indeterminate:
        # Not OK (nothing was verified) and not RED (nothing was disproved).
        overall = "INDETERMINATE"
    elif warns:
        overall = "WARN"
    else:
        overall = "OK"

    return {
        "overall": overall,
        "checked_at": now.isoformat(),
        "history": hist,
        "jobs": rows, "breaches": breaches, "warnings": warns,
        "indeterminate": indeterminate,
        "_standard": "the commit diff is the receipt — a green workflow that persisted nothing is red here",
    }


# Severity ladder for the fold below. A job that fired but published nothing is exactly as bad as
# a job that never fired — both mean the system produced no evidence — so CONTRACT_BREACH sits with
# MISSING at the top. INDETERMINATE ranks above OK because a deaf alarm is not a healthy one.
_SEVERITY = {"OK": 0, "WARN": 1, "INDETERMINATE": 2, "OVERDUE": 3, "CONTRACT_BREACH": 4,
             "MISSING": 4, "ERROR": 5}


def fold_into_health(health: dict, contracts: dict) -> dict:
    """Attach the contract result to `scheduler_health` AND let it move the top-level `overall`.

    An alarm subsection nobody has to remember to read is half an alarm. Before this fold, a
    contract breach was recorded in a nested key while `overall` still said OK — the same shape of
    defect the contracts exist to catch, one level up.

    Mutates and returns `health`.
    """
    health["output_contracts"] = contracts
    mapped = {"RED": "CONTRACT_BREACH", "INDETERMINATE": "INDETERMINATE",
              "WARN": "WARN", "OK": "OK", "ERROR": "ERROR"}.get(contracts.get("overall"), "ERROR")
    current = health.get("overall", "OK")
    if _SEVERITY.get(mapped, 5) > _SEVERITY.get(current, 0):
        health["overall"] = mapped
        health["overall_driver"] = "output_contracts"
    return health


def annotations(result: dict) -> list[str]:
    """GitHub Actions annotations, so a breach is loud on the next monitor run."""
    out = [f"::error::output-contract BREACH — {b}" for b in result.get("breaches", [])]
    if result.get("indeterminate"):
        h = result.get("history", {})
        out.append(
            "::warning::output-contract INDETERMINATE for "
            f"{', '.join(result['indeterminate'])} — this checkout cannot answer the question "
            f"(shallow={h.get('shallow')}, commits={h.get('n_commits')}). "
            "Set `fetch-depth: 0` on the job's actions/checkout. NOT a breach.")
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
