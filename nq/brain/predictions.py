"""A prediction ledger: forecasts stamped BEFORE their outcome, resolved later, and Brier-scored.

Phase 1 item B5 of the 2026-09-25 development plan (Brain plan Layer 6). The point is calibration, and
calibration is only measurable when the forecast provably pre-dates the outcome — otherwise it is
recollection, which this programme already refuses for counts and for backtest numbers.

WHY IT IS HASH-CHAINED. The same reason `nq/paper/judge_log.py` is: a claim that can be edited after the
fact is not a claim. Each row binds its predecessor, so a reordered, altered or removed row breaks the
chain at that position. The chain is verified before every append, so the ledger cannot be extended from
a corrupted state.

WHY RESOLUTION IS A SECOND ROW. Append-only and "record the outcome" are in tension: writing the outcome
into the prediction row would mean rewriting it. So a resolution is its OWN row naming the prediction's
`row_hash`. The forecast as it was made survives verbatim, forever, next to what happened.

THE RULE THAT MAKES IT EVIDENCE. `stamped_at` must be strictly before `resolve_by`. A "prediction" logged
on or after the moment it resolves is not a prediction, and `append_prediction` refuses it rather than
storing it with a caveat. `06_habit_ledger_spec.md` §1.5's hard rule also applies downstream: these rows
are never joined into a pre-entry feature set without purge and embargo, because a forecast about a trade
is a function of that trade's own future.

A Brier score is the squared error of a probability against a 0/1 outcome, so lower is better, 0.25 is
what you get by always saying 50%, and it is only interpretable in bulk — `summarise` refuses to
pronounce below `MIN_RESOLVED`.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG: Path = ROOT / "results" / "brain" / "prediction_ledger.jsonl"
GENESIS: str = hashlib.sha256(b"nifty-satvik/prediction-ledger/genesis@plan-B5").hexdigest()

KINDS = ("prediction", "resolution")
# A Brier score over a handful of forecasts says nothing. The programme's own habit — state the floor and
# refuse to read below it — applied here (cf. the >=30-closed precondition, prereg_swing §11.4).
MIN_RESOLVED = 20


class IntegrityError(RuntimeError):
    """The ledger refuses an append that would make it unreadable as evidence."""


def _canon(payload: Mapping[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "row_hash"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _chain_hash(prior: str, canon: str) -> str:
    return hashlib.sha256(f"{prior}|{canon}".encode()).hexdigest()


def _load(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def verify_chain(rows: Sequence[Mapping[str, Any]]) -> tuple[bool, int]:
    """``(True, -1)`` if intact, else ``(False, first_bad_index)``. Position-sensitive by construction."""
    prior = GENESIS
    for i, r in enumerate(rows):
        if _chain_hash(prior, _canon(r)) != r.get("row_hash"):
            return False, i
        prior = r["row_hash"]
    return True, -1


def _append(row: dict[str, Any], path: Path) -> str:
    rows = _load(path)
    ok, bad = verify_chain(rows)
    if not ok:
        raise IntegrityError(f"existing chain fails to verify at row {bad}; refusing to append")
    row["seq"] = (int(rows[-1]["seq"]) + 1) if rows else 0
    prior = rows[-1]["row_hash"] if rows else GENESIS
    row["row_hash"] = _chain_hash(prior, _canon(row))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, sort_keys=True, ensure_ascii=False, default=str) + "\n")
    return row["row_hash"]


def append_prediction(*, subject: str, claim: str, probability: float, stamped_at: str,
                      resolve_by: str, basis: str, path: str | Path = DEFAULT_LOG) -> str:
    """Record a forecast. Returns its ``row_hash``, which a later resolution must name.

    `subject` is what the claim is about — a `trade_id`, a ticker, or the literal ``"self"`` for a claim
    about the system's own behaviour ("HEG carries after the scan"). `basis` says where the number came
    from, e.g. ``first_passage_null`` or ``owner``, so a model can later be scored against the null
    rather than against nothing.
    """
    if not 0.0 <= float(probability) <= 1.0:
        raise IntegrityError(f"probability {probability} is not in [0, 1]")
    if not str(stamped_at) < str(resolve_by):
        # THE RULE. A forecast stamped at or after the moment it resolves is not a forecast, and storing
        # it with a caveat would let it into a calibration number later.
        raise IntegrityError(
            f"stamped_at {stamped_at!r} is not strictly before resolve_by {resolve_by!r} — a prediction "
            f"must pre-date its own outcome")
    if not claim.strip():
        raise IntegrityError("a prediction with no claim cannot be resolved")
    return _append({"kind": "prediction", "subject": subject, "claim": claim,
                    "probability": round(float(probability), 6), "stamped_at": str(stamped_at),
                    "resolve_by": str(resolve_by), "basis": basis}, Path(path))


def append_resolution(*, predicts: str, outcome: bool, resolved_at: str, note: str | None = None,
                      path: str | Path = DEFAULT_LOG) -> str:
    """Record what happened. `predicts` is the prediction row's ``row_hash``.

    A resolution is a separate row so the forecast is never rewritten. It refuses an unknown target, a
    double resolution, and a resolution stamped before the forecast it resolves.
    """
    p = Path(path)
    rows = _load(p)
    target = next((r for r in rows if r.get("row_hash") == predicts and r.get("kind") == "prediction"),
                  None)
    if target is None:
        raise IntegrityError(f"no prediction with row_hash {predicts!r} to resolve")
    if any(r.get("kind") == "resolution" and r.get("predicts") == predicts for r in rows):
        raise IntegrityError(f"prediction {predicts[:12]}… is already resolved; a correction is a new "
                             f"prediction, not a second resolution")
    if str(resolved_at) < str(target["stamped_at"]):
        raise IntegrityError(f"resolved_at {resolved_at!r} precedes the prediction's stamp "
                             f"{target['stamped_at']!r}")
    return _append({"kind": "resolution", "predicts": predicts, "outcome": bool(outcome),
                    "resolved_at": str(resolved_at), "note": note}, p)


def brier(probability: float, outcome: bool) -> float:
    """Squared error of a probability against a 0/1 outcome. Lower is better; 0.25 is always-50%."""
    return round((float(probability) - (1.0 if outcome else 0.0)) ** 2, 6)


def resolved_pairs(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Predictions joined to their resolutions, oldest first. Unresolved forecasts are excluded."""
    rows = list(rows)
    preds = {r["row_hash"]: r for r in rows if r.get("kind") == "prediction"}
    out = []
    for r in rows:
        if r.get("kind") != "resolution":
            continue
        p = preds.get(r.get("predicts"))
        if p is None:
            continue
        out.append({"subject": p["subject"], "claim": p["claim"], "basis": p["basis"],
                    "probability": p["probability"], "stamped_at": p["stamped_at"],
                    "resolve_by": p["resolve_by"], "outcome": r["outcome"],
                    "resolved_at": r["resolved_at"], "brier": brier(p["probability"], r["outcome"])})
    return out


def summarise(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Calibration so far — and a refusal to pronounce on too few.

    `mean_brier` is reported alongside the always-50% reference (0.25) and the base rate, because a
    Brier score on its own is not interpretable: a model that always says 5% scores well on rare events
    while knowing nothing.
    """
    pairs = resolved_pairs(rows)
    n = len(pairs)
    out: dict[str, Any] = {"n_resolved": n, "min_resolved": MIN_RESOLVED,
                           "informative": n >= MIN_RESOLVED}
    if not n:
        out["reading"] = "nothing resolved yet"
        return out
    base = sum(1 for p in pairs if p["outcome"]) / n
    out |= {
        "mean_brier": round(sum(p["brier"] for p in pairs) / n, 6),
        "always_50pct_reference": 0.25,
        "base_rate": round(base, 4),
        "always_base_rate_reference": round(base * (1 - base), 6),
        "mean_probability": round(sum(p["probability"] for p in pairs) / n, 4),
        "by_basis": {},
    }
    for b in sorted({p["basis"] for p in pairs}):
        sub = [p for p in pairs if p["basis"] == b]
        out["by_basis"][b] = {"n": len(sub),
                              "mean_brier": round(sum(p["brier"] for p in sub) / len(sub), 6)}
    out["reading"] = (
        f"{n} resolved: mean Brier {out['mean_brier']:.4f} against {0.25} for always-50% and "
        f"{out['always_base_rate_reference']:.4f} for always-the-base-rate ({base:.0%})."
        + ("" if out["informative"] else
           f" BELOW THE FLOOR of {MIN_RESOLVED} — not to be read as calibration."))
    return out


def read_verified(path: str | Path = DEFAULT_LOG) -> list[dict[str, Any]]:
    """Every row, after checking the chain. Raises rather than returning a silently-corrupt ledger."""
    rows = _load(Path(path))
    ok, bad = verify_chain(rows)
    if not ok:
        raise IntegrityError(f"prediction ledger fails to verify at row {bad}")
    return rows
