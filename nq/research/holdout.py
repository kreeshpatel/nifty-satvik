"""Holdout guard for the company-engine study (pre-registration 0153, section d).

The training window ends 2024-06-30. Every return-based research statistic computed for this study must
pass its return series (or its dates) through :func:`assert_pre_holdout` first. A series reaching
``HOLDOUT_START`` or later raises :class:`HoldoutViolation` unless an explicit unseal token is given. The
token is the id of a signed owner amendment, e.g. ``"AMD-2027-01-0153"``. It must match ``UNSEAL_TOKEN_RE``,
and it is echoed back so the caller can log it next to the result.

Price-free statistics (e.g. L1 forecast accuracy, peer-cluster stability) do not call this guard.
"""
from __future__ import annotations

import re
from datetime import date

import numpy as np
import pandas as pd

HOLDOUT_START = date(2024, 7, 1)
TRAIN_END = date(2024, 6, 30)
UNSEAL_TOKEN_RE = re.compile(r"^AMD-\d{4}-\d{2}-[0-9A-Za-z-]+$")


class HoldoutViolation(RuntimeError):
    pass


def _max_date(obj) -> pd.Timestamp | None:
    if isinstance(obj, (pd.Series, pd.DataFrame)):
        idx = obj.index
        if isinstance(idx, pd.MultiIndex):
            lv = [i for i, n in enumerate(idx.names) if n in ("date", "Date")]
            idx = idx.get_level_values(lv[0] if lv else 0)
        if isinstance(idx, pd.DatetimeIndex):
            return idx.max() if len(idx) else None
        if isinstance(obj, pd.DataFrame):
            for c in ("date", "Date"):
                if c in obj.columns:
                    return pd.to_datetime(obj[c]).max()
        raise TypeError("holdout guard: cannot find a date index or a 'date' column")
    vals = pd.to_datetime(pd.Index(np.atleast_1d(obj)))
    return vals.max() if len(vals) else None


def assert_pre_holdout(obj, *, unseal_token: str | None = None, what: str = "return series") -> str | None:
    """Raise if ``obj`` (Series/DataFrame/dates) extends past TRAIN_END, unless a valid unseal token is given.

    Returns the token (or None) so the caller can record it beside the statistic.
    """
    m = _max_date(obj)
    if m is None or pd.isna(m) or m.date() <= TRAIN_END:
        return unseal_token
    if unseal_token is None:
        raise HoldoutViolation(
            f"{what} extends to {m.date()} (past {TRAIN_END}); the 2024-07-01..2026-06-30 holdout is sealed "
            "for return-based statistics (prereg 0153 d). Pass unseal_token=<signed owner amendment id>.")
    if not UNSEAL_TOKEN_RE.match(unseal_token):
        raise HoldoutViolation(f"unseal token {unseal_token!r} is not a signed owner amendment id (AMD-YYYY-MM-...)")
    return unseal_token


def clip_to_train(obj):
    """Return the part of a date-indexed Series/DataFrame on or before TRAIN_END (for building inputs)."""
    idx = obj.index.get_level_values("date") if isinstance(obj.index, pd.MultiIndex) else obj.index
    return obj[np.asarray(pd.to_datetime(idx) <= pd.Timestamp(TRAIN_END))]
