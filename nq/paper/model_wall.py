"""Second-model watched log — an INDEPENDENT hash-chained stream, one per model.

Why not just add a fourth book to the forward wall
--------------------------------------------------
:mod:`nq.paper.forward_wall` carries all three books in ONE atomic row so a partial write cannot
open a silent hole, and its schema is **pinned in** ``forward/prereg.md §3``. Its own docstring says
why that must not be edited::

    changing it (or the hash construction) breaks verification of every prior row against the doc,
    which is the point: the doc is the contract.

Adding a fourth book would change ``DATA_FIELDS`` → change ``_canon_parts`` → change every row hash
→ invalidate the entire existing chain against the registered document. So a second model gets its
**own file and its own chain**, seeded from its own model id. The 3-book wall is left byte-identical
(``tests/test_model_wall.py::test_forward_wall_schema_is_untouched``). This mirrors the precedent set
by the 0131 zoo shadow book: own artifact, own guards, golden byte-identical.

Activation is a governance act, not a code change
-------------------------------------------------
``forward/prereg.md §1`` enumerates the registered books; §10 permits **tightening/clarification
only**, and adding a book is described there as requiring "an explicit cap amendment". Decisions
happen at quarterly reviews (next **2026-10-01**). **This module ships the mechanism, wired to
nothing.** Turning it on is one guarded call in ``scripts/run_paper_cron.py``, after the wall
update::

    if MODEL_WALL_ENABLED:                       # owner flag, default False
        update_model_wall(cand_book.equity_curve, model_id="stpivot-w1",
                          initial_capital=cand_book.initial_capital,
                          state_dir=state_dir, wall_start=wall_start)

Until that line exists and the prereg carries a dated amendment naming the model, nothing is logged.

The recomputed-history hazard, inherited
----------------------------------------
A paper book steps from its own inception, so on a cold start its ``equity_curve`` already holds
months of sessions. Logging those would enter *recomputed* history as forward evidence — every row
would pass the chain (dates strictly increase) and every row would misstate when it was known.
:func:`update_model_wall` therefore takes the same ``wall_start`` bound the 3-book wall uses, and
**refuses to run without one** rather than defaulting to "log everything": for a brand-new stream
there is no legacy caller to preserve, so the safe default is the strict one.
"""
from __future__ import annotations

import csv
import hashlib
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from config import RESULTS_DIR

from .forward_wall import IntegrityError, _chain_hash, _load

__all__ = ["DATA_FIELDS", "FIELDS", "model_genesis", "log_path", "gap_row", "verify_chain",
           "append_row", "read_verified", "update_model_wall"]

DATA_FIELDS: list[str] = ["date", "status", "ret", "equity", "npos"]
FIELDS: list[str] = [*DATA_FIELDS, "row_hash"]

_GENESIS_PREFIX = "nifty-satvik/model-wall/genesis"


def model_genesis(model_id: str) -> str:
    """Chain seed for ``model_id``, bound to the dataset pin.

    Seeding per model is deliberate: two model logs can never be spliced together, and a row cannot
    be lifted from one stream into another and still verify.
    """
    return hashlib.sha256(
        f"{_GENESIS_PREFIX}/{model_id}@dataset-pin-20260701".encode()).hexdigest()


def log_path(model_id: str, state_dir: str | Path = RESULTS_DIR) -> Path:
    return Path(state_dir) / f"model_wall_{model_id}.csv"


def _canon_parts(row: Mapping[str, Any]) -> list[str]:
    """Canonical field strings, fixed order. A ``gap`` row carries empty observation fields."""
    status = str(row.get("status", "ok"))
    parts = [str(row["date"])[:10], status]
    if status == "gap":
        return parts + [""] * (len(DATA_FIELDS) - 2)
    return parts + [f"{float(row['ret']):.8f}", f"{float(row['equity']):.2f}",
                    str(int(row["npos"]))]


def gap_row(date: str) -> dict[str, str]:
    """Missed-trading-day marker — hashed like any row, so a gap is tamper-evident."""
    row = {f: "" for f in DATA_FIELDS}
    row["date"] = str(date)[:10]
    row["status"] = "gap"
    return row


def verify_chain(rows: Sequence[Mapping[str, str]], model_id: str) -> tuple[bool, int]:
    """Recompute from this model's genesis. ``(ok, first_bad_index)``; ``(True, -1)`` when intact."""
    prior = model_genesis(model_id)
    for i, r in enumerate(rows):
        if _chain_hash(prior, [r[f] for f in DATA_FIELDS]) != r["row_hash"]:
            return False, i
        prior = r["row_hash"]
    return True, -1


def append_row(row: Mapping[str, Any], model_id: str,
               path: str | Path | None = None, state_dir: str | Path = RESULTS_DIR) -> str:
    """Verify the whole existing chain, then atomically append ONE row.

    Refuses on a broken chain or a date not strictly after the last logged one — so a double-run is
    refused and a missed day must be an explicit :func:`gap_row`, never a silent back-fill.
    """
    p = Path(path) if path is not None else log_path(model_id, state_dir)
    rows = _load(p)
    ok, bad = verify_chain(rows, model_id)
    if not ok:
        raise IntegrityError(f"{model_id}: chain fails to verify at row {bad}; refusing to append")
    date = str(row["date"])[:10]
    if rows and date <= rows[-1]["date"]:
        raise IntegrityError(
            f"{model_id}: no back-dating / double-run: {date} <= last logged {rows[-1]['date']}")
    parts = _canon_parts(row)
    prior = rows[-1]["row_hash"] if rows else model_genesis(model_id)
    h = _chain_hash(prior, parts)
    new = dict(zip(DATA_FIELDS, parts))
    new["row_hash"] = h
    write_header = not p.exists()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        w.writerow(new)
    return h


def read_verified(model_id: str, path: str | Path | None = None,
                  state_dir: str | Path = RESULTS_DIR) -> list[dict[str, str]]:
    """Load and raise :class:`IntegrityError` if the chain does not verify."""
    p = Path(path) if path is not None else log_path(model_id, state_dir)
    rows = _load(p)
    ok, bad = verify_chain(rows, model_id)
    if not ok:
        raise IntegrityError(f"{model_id}: chain fails to verify at row {bad}")
    return rows


def update_model_wall(
    equity_curve: Sequence[Mapping[str, Any]], *, model_id: str, initial_capital: float,
    wall_start: str, state_dir: str | Path = RESULTS_DIR, path: str | Path | None = None,
    holidays: Iterable[Any] | None = None,
) -> int:
    """Append one row per session in ``equity_curve`` not yet logged. Returns rows written.

    ``wall_start`` is **required**, not optional. The 3-book wall defaults it to ``None`` only to
    preserve pre-existing callers; a new stream has none, so the strict behaviour is the default
    here — no session before the registered start is ever written, because a paper book's
    pre-existing curve is recomputed history rather than forward evidence.

    ``holidays`` is accepted for signature-compatibility with the 3-book writer and is currently
    unused: gap detection needs the session calendar the caller already owns, and inventing a second
    source of truth for trading days is exactly the drift this repo keeps paying for. Callers that
    need gap markers should append :func:`gap_row` explicitly.
    """
    if not equity_curve:
        return 0
    if not wall_start:
        raise ValueError(
            "wall_start is required: without it a cold-start paper curve would enter the log as "
            "forward evidence (forward/prereg.md §3).")
    p = Path(path) if path is not None else log_path(model_id, state_dir)
    existing = _load(p)
    last = existing[-1]["date"] if existing else None
    start = str(wall_start)[:10]

    n = 0
    prev_eq = float(initial_capital)
    for e in equity_curve:
        d = str(e["date"])[:10]
        eq = float(e["equity"])
        ret = (eq / prev_eq - 1.0) if prev_eq > 0 else 0.0
        prev_eq = eq
        if d < start or (last is not None and d <= last):
            continue
        append_row({"date": d, "status": "ok", "ret": ret, "equity": eq,
                    "npos": int(e.get("n_positions", 0))}, model_id, path=p)
        n += 1
    return n
