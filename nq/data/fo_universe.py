"""Point-in-time equity F&O membership, derived from the NSE F&O bhavcopies.

Why this exists. The intraday store is scoped to the **F&O universe** rather than all of Nifty 500 —
the reset rationale in `diagnostics/research/n_trials.json` says so, and the reason is that F&O
membership is the liquidity screen the exchange itself maintains. But no such list existed here:
`pipelines/build/harvest_fo_bhavcopy.py` downloads the bhavcopies and keeps ONLY the NIFTY index
option rows, discarding every single-stock row, so the membership was never derivable from what was
already harvested.

Membership is not static and must not be treated as such. Names enter and leave the F&O segment on
exchange review, and a universe pinned to *today's* list is survivorship by another door — the same
error the daily store already paid for. So this produces a dated long frame, and `members_on` reads
it as of a date.

The two vendor schemas mirror `nq.data.options_oi`:
  * OLD  (2017-01 .. 2024-06): ``INSTRUMENT == "FUTSTK"``, symbol in ``SYMBOL``
  * UDiFF (2024-07 ..)       : ``FinInstrmTp == "STF"``, symbol in ``TckrSymb``

Single-stock FUTURES are the membership marker rather than options, because a name in the F&O
segment always has futures while option series can be absent on a given day.
"""
from __future__ import annotations

import pandas as pd

__all__ = ["MEMBER_COLS", "parse_fo_members", "build_membership", "members_on", "membership_spans"]

MEMBER_COLS = ["date", "symbol"]

_OLD_FUTSTK = "FUTSTK"
_UDIFF_STF = "STF"


def parse_fo_members(df: pd.DataFrame, trade_date) -> set[str]:
    """Equity F&O symbols present in ONE bhavcopy. Empty set on a holiday or an unparseable file.

    Auto-detects the schema by column presence, exactly as `options_oi.parse_fo_bhavcopy` does, so
    the two stay consistent when NSE changes format again.
    """
    if df is None or not len(df):
        return set()

    if "FinInstrmTp" in df.columns:                       # ── UDiFF ──
        if "TckrSymb" not in df.columns:
            return set()
        rows = df[df["FinInstrmTp"].astype(str).str.upper() == _UDIFF_STF]
        col = "TckrSymb"
    elif "INSTRUMENT" in df.columns:                      # ── OLD historical ──
        if "SYMBOL" not in df.columns:
            return set()
        rows = df[df["INSTRUMENT"].astype(str).str.upper() == _OLD_FUTSTK]
        col = "SYMBOL"
    else:
        return set()

    if rows.empty:
        return set()
    syms = rows[col].astype(str).str.strip().str.upper()
    return set(syms[syms.str.len() > 0])


def build_membership(raw_by_day: dict) -> pd.DataFrame:
    """``{date -> bhavcopy DataFrame}`` -> a dated long frame of (date, symbol), sorted and unique.

    One row per name per session it was in the segment. Days that parse to nothing contribute no
    rows rather than an empty-set sentinel, so a holiday is indistinguishable from a missing file at
    this layer — `membership_spans` and any coverage audit read gaps, not this function.
    """
    rows: list[tuple[pd.Timestamp, str]] = []
    for d, df in raw_by_day.items():
        stamp = pd.Timestamp(d).normalize()
        for s in parse_fo_members(df, stamp):
            rows.append((stamp, s))
    if not rows:
        return pd.DataFrame({"date": pd.Series(dtype="datetime64[ns]"),
                             "symbol": pd.Series(dtype="object")})
    out = pd.DataFrame(rows, columns=MEMBER_COLS).drop_duplicates()
    return out.sort_values(MEMBER_COLS, kind="mergesort").reset_index(drop=True)


def members_on(panel: pd.DataFrame, date) -> set[str]:
    """The F&O universe as it stood on ``date`` — the most recent session at or before it.

    Carries the last observed session forward rather than requiring an exact match, because a
    decision taken on a holiday or a half-day must still see the universe that was in force. It
    never looks FORWARD: a name that joins the segment tomorrow is not visible today.
    """
    if panel is None or not len(panel):
        return set()
    d = pd.Timestamp(date).normalize()
    dates = pd.to_datetime(panel["date"])
    prior = dates[dates <= d]
    if prior.empty:
        return set()
    return set(panel.loc[dates == prior.max(), "symbol"].astype(str))


def membership_spans(panel: pd.DataFrame) -> pd.DataFrame:
    """First and last session each symbol appears, with its session count.

    The join/leave record. A symbol whose `last` is well before the panel's end left the segment,
    which is exactly the population a universe pinned to today's list would silently drop.
    """
    if panel is None or not len(panel):
        return pd.DataFrame(columns=["symbol", "first", "last", "n_sessions"])
    g = panel.assign(date=pd.to_datetime(panel["date"])).groupby("symbol")["date"]
    out = pd.DataFrame({"first": g.min(), "last": g.max(), "n_sessions": g.nunique()})
    return out.reset_index().sort_values("symbol", kind="mergesort").reset_index(drop=True)
