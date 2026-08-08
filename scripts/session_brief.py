"""SessionStart hook — put the programme's live state in front of every session.

CLAUDE.md tells each session to recite `screens N · sealed opens N · n_trials N`. Prose cannot
carry a number that changes: on 2026-08-07 every copy of that line in the repo was wrong, and
because the instruction says *recite it*, the stale value was copied into the output of every
session that obeyed. `tests/test_standing_counts.py` stops the prose from disagreeing with the
ledgers; this hook removes the need for the session to read the prose at all — the counts are
computed from their authorities at session start and injected as context.

That, in turn, is what makes it safe for CLAUDE.md to be short. The standing state (counts, the
pinned anchor, the interpreter, what is closed) arrives unconditionally on every session — research
session, code session, or a session that never opens a skill — instead of depending on the model
choosing to load a document.

Contract (https://code.claude.com/docs/en/hooks): stdin is the hook event JSON, stdout is
`hookSpecificOutput.additionalContext`, exit 0. **This hook must never fail a session.** Every
read is individually guarded and a missing authority degrades to a visible `unknown`, never to a
traceback and never to a non-zero exit — a governance brief that blocks work would be removed
within a week, and then there would be no brief at all.

stdlib only, no third-party imports: it runs before the environment is known to be good, and the
interpreter it is checking may be the wrong one.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

N_TRIALS = ROOT / "diagnostics" / "research" / "n_trials.json"
LEDGER = ROOT / "diagnostics" / "research" / "label_screen_ledger.md"
BASELINE = ROOT / "research" / "baseline_v1.json"
PYPROJECT = ROOT / "pyproject.toml"

UNKNOWN = "unknown"


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def n_trials() -> str:
    """Authority: diagnostics/research/n_trials.json. Never a remembered number."""
    try:
        return str(json.loads(_text(N_TRIALS))["cumulative_n_trials"])
    except (ValueError, KeyError, TypeError):
        return UNKNOWN


def screens() -> str:
    """Numbered rows in the screen ledger — `| 17 | 2026-08-06 | ... |`."""
    rows = re.findall(r"^\|\s*(\d+)\s*\|", _text(LEDGER), re.M)
    return str(max(int(r) for r in rows)) if rows else UNKNOWN


def sealed_opens() -> str:
    """S-prefixed rows in the sealed-open table — `| S1 | ... |`."""
    rows = re.findall(r"^\|\s*S(\d+)\s*\|", _text(LEDGER), re.M)
    return str(len(rows)) if rows else UNKNOWN


def anchor() -> str:
    try:
        b = json.loads(_text(BASELINE))
        g, pin = b.get("gross", {}), b.get("pin", {})
        return (
            f"baseline_v1 gross Sharpe {g.get('sharpe', '?')} / CAGR {g.get('cagr_pct', '?')}% / "
            f"MaxDD {g.get('max_drawdown_pct', '?')}% · ohlcv sha {str(pin.get('ohlcv_sha256', '?'))[:8]}"
        )
    except (ValueError, TypeError):
        return UNKNOWN


def interpreter() -> str:
    """Report the running interpreter against the pin, and say plainly when it is outside it.

    A backtest that silently ran on an unpinned interpreter is not reproducible, and the failure is
    invisible at the point it matters — it shows up later as a number that will not reproduce.
    """
    running = f"{sys.version_info.major}.{sys.version_info.minor}"
    m = re.search(r'requires-python\s*=\s*"([^"]+)"', _text(PYPROJECT))
    if not m:
        return f"python {running} (no requires-python pin found)"
    spec = m.group(1)
    lo = re.search(r">=\s*(\d+)\.(\d+)", spec)
    hi = re.search(r"<\s*(\d+)\.(\d+)", spec)
    cur = sys.version_info[:2]
    ok = True
    if lo and cur < (int(lo.group(1)), int(lo.group(2))):
        ok = False
    if hi and cur >= (int(hi.group(1)), int(hi.group(2))):
        ok = False
    if ok:
        return f"python {running} (pin {spec} — ok)"
    return f"python {running} ⚠ OUTSIDE the pin {spec} — do not trust any number produced here"


def branch() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, timeout=5, check=False,
        )
        return out.stdout.strip() or UNKNOWN
    except (OSError, subprocess.SubprocessError):
        return UNKNOWN


def brief() -> str:
    return "\n".join([
        "## nifty-satvik — standing state (generated at session start, from the ledgers)",
        "",
        f"**Standing counts — recite these, not a remembered value: screens {screens()} · "
        f"sealed opens {sealed_opens()} · n_trials {n_trials()}.**",
        f"Authorities: `diagnostics/research/n_trials.json`, "
        f"`diagnostics/research/label_screen_ledger.md`. If any document disagrees, they are right.",
        "",
        f"- Pinned anchor: {anchor()}",
        f"- Interpreter: {interpreter()}",
        f"- Branch: `{branch()}`",
        "",
        "**Route the task before doing it** — `/session-router` classifies it as MEASUREMENT / "
        "RESEARCH / ENGINE / REFACTOR / PRODUCT and names the gate each class must clear. Research "
        "also loads `program-laws` (standing verdicts, cite-and-narrow) and `verdict-machine` (the "
        "method that spends no multiplicity). Rituals: `/pre-register`, `/verdict`, `/seal`, "
        "`/re-anchor`. Adversarial reads: the `red-team`, `flaw-hunter`, `backtest-validator`, "
        "`overfit-skeptic`, and `blind-replica` subagents.",
        "",
        "**Two things a session cannot do from memory:** state a count (read the ledger) and assert "
        "a backtest number is plausible (`/plausibility-check` — the anchors are reproducible, the "
        "model's recollection of them is not).",
    ])


def main() -> int:
    try:
        sys.stdin.read()  # drain the event payload; nothing in it is needed
    except (OSError, ValueError):
        pass
    try:
        payload = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": brief(),
            }
        }
        sys.stdout.write(json.dumps(payload))
    except Exception:  # noqa: BLE001 — a governance brief must never break a session
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
