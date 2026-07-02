"""Point-in-time fundamentals — the solvency (D/E) and value/quality join.

The long-horizon universe filter keeps only **solvent low-debt** names (``0 <= D/E < 1.5``).
That gate must be point-in-time: each decision date may use only the most-recently-published
annual report **strictly before** it — otherwise the backtest trades on figures the market
had not yet seen (a P0 leakage; see ``skills/leakage-audit`` §2).

Source: the carried Screener scrape ``data/fundamentals_pit_screener.pkl`` — a
``{ticker -> DataFrame}`` store indexed by ``available_date`` (when the figure became public)
with columns ``period_end, eps_ttm, book_value_ps, roe, debt_equity``.

The join is ``merge_asof(direction="backward", allow_exact_matches=False)`` — strictly
``available_date < decision_date``. ``allow_exact_matches=False`` is load-bearing: it forbids
a same-day filing from leaking in. ``low_debt = -debt_equity`` (higher = less leverage).

Ported verbatim (behaviour-preserving) from the validated source (``long_horizon/data/sheets.py``).
"""
from __future__ import annotations

import pickle
from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd

from config import DATA_DIR

FUND_STORE_PATH = DATA_DIR / "fundamentals_pit_screener.pkl"

# The value/quality factors produced by the PIT join.
VALUE_QUALITY_COLS: tuple[str, ...] = ("ep", "bp", "roe", "low_debt")


def load_fund_store(path: str | Path = FUND_STORE_PATH) -> dict | None:
    """Load the PIT fundamentals store ``{ticker -> frame}`` from disk. Returns ``None`` if
    the file is missing or corrupt (callers then leave the value columns all-NaN)."""
    path = Path(path)
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        print(f"[fundamentals] store not found at {path}; value cols will be NaN")
        return None
    except Exception as exc:
        print(f"[fundamentals] store corrupt or unreadable ({exc}); value cols will be NaN")
        return None


def value_quality_series(
    ticker: str, store: Mapping[str, pd.DataFrame] | None,
    dates: pd.DatetimeIndex, close: np.ndarray,
) -> dict[str, np.ndarray]:
    """Per-date value/quality factor values for one ticker, PIT-safe (strict-before).

    ``dates`` MUST be sorted ascending (the caller sorts the feature frame), so the
    ``merge_asof`` output is row-aligned to ``dates`` with no reordering. Returns a dict with
    arrays for ``ep`` (earnings/price), ``bp`` (book/price), ``roe``, and ``low_debt``
    (= ``-debt_equity``). All-NaN when the store has no row for the ticker.
    """
    n = len(dates)
    out: dict[str, np.ndarray] = {k: np.full(n, np.nan) for k in VALUE_QUALITY_COLS}
    fr = store.get(ticker) if store else None
    if fr is None or len(fr) == 0:
        return out
    right = fr.copy()
    # Normalize both merge keys to ns — the OHLCV index is often [s] while the fundamentals
    # store is [us]; merge_asof requires identical key dtypes.
    right["avail"] = pd.to_datetime(right.index).astype("datetime64[ns]")
    cols = [c for c in ("eps_ttm", "book_value_ps", "roe", "debt_equity") if c in right.columns]
    right = right[["avail", *cols]].sort_values("avail")
    left = pd.DataFrame({"date": pd.to_datetime(dates).astype("datetime64[ns]")})
    merged = pd.merge_asof(
        left, right, left_on="date", right_on="avail",
        direction="backward", allow_exact_matches=False,   # strict: avail < date
    )
    eps = merged["eps_ttm"].to_numpy(dtype=float) if "eps_ttm" in merged else np.full(n, np.nan)
    bvps = merged["book_value_ps"].to_numpy(dtype=float) if "book_value_ps" in merged else np.full(n, np.nan)
    roe = merged["roe"].to_numpy(dtype=float) if "roe" in merged else np.full(n, np.nan)
    de = merged["debt_equity"].to_numpy(dtype=float) if "debt_equity" in merged else np.full(n, np.nan)
    safe = close > 0
    out["ep"] = np.where(safe, eps / np.where(safe, close, 1.0), np.nan)
    out["bp"] = np.where(safe, bvps / np.where(safe, close, 1.0), np.nan)
    out["roe"] = roe
    out["low_debt"] = -de   # higher = less leverage
    return out


# ── Screener.in deep-history PIT-frame builder (Stage-A survivorship fundamentals) ──
# yfinance carries only ~5 recent quarters; Screener company pages carry ~10-12 fiscal years of
# annual P&L + Balance Sheet — the depth needed to give DELISTED / historical index members the
# point-in-time D/E they lack in the carried store (the survivorship blocker). This is the pure,
# testable HTML-table → PIT-frame derivation (the network scrape lives in scripts/scrape_screener.py).
# Ported verbatim from the validated source ``fundamentals_pit.build_pit_frame_from_screener``.

ANNUAL_REPORTING_LAG_DAYS = 90   # filing date unknown → conservative annual lag after period-end


def available_date_from_period_end(period_end, lag_days: int = ANNUAL_REPORTING_LAG_DAYS) -> pd.Timestamp:
    """Conservative public-availability date = period-end + lag (over-estimating the lag is safe)."""
    return pd.Timestamp(period_end) + pd.Timedelta(days=lag_days)


def _ok(v) -> bool:
    try:
        return v is not None and not np.isnan(float(v))
    except (TypeError, ValueError):
        return False


def _screener_num(v) -> float:
    """Parse a Screener cell ('1,234', '12.3%', '', '-') → float or NaN."""
    if v is None:
        return float("nan")
    s = str(v).replace(",", "").replace("%", "").replace("\xa0", "").strip()
    if s in ("", "-", "nan", "NaN"):
        return float("nan")
    try:
        return float(s)
    except (TypeError, ValueError):
        return float("nan")


def _norm_label(s) -> str:
    """Normalise a Screener row label: strip the '+' expander and nbsp/space."""
    return str(s).replace("\xa0", "").replace("+", "").strip()


def _screener_row(table: pd.DataFrame, candidates: tuple[str, ...]) -> pd.Series | None:
    """The period→value Series for the first row whose normalised label matches a candidate
    (case-insensitive). col 0 = line-item labels; remaining cols = period labels ('Mar 2024')."""
    if table is None or table.empty or table.shape[1] < 2:
        return None
    label_col = table.columns[0]
    wanted = {c.lower() for c in candidates}
    for _, row in table.iterrows():
        if _norm_label(row[label_col]).lower() in wanted:
            return row.drop(labels=[label_col])
    return None


def _period_end_from_label(label: str) -> pd.Timestamp | None:
    """'Mar 2024' → 2024-03-31 (fiscal-month end). Non-period labels (TTM, blanks) → None."""
    try:
        ts = pd.to_datetime(str(label).strip(), format="%b %Y")
    except (ValueError, TypeError):
        return None
    return pd.Timestamp(ts) + pd.offsets.MonthEnd(0)


def build_pit_frame_from_screener(
    profit_loss: pd.DataFrame | None, balance_sheet: pd.DataFrame | None,
    *, lag_days: int = ANNUAL_REPORTING_LAG_DAYS,
) -> pd.DataFrame:
    """Build one ticker's PIT frame from Screener annual P&L + Balance Sheet tables. Per fiscal
    year: ``eps_ttm`` = annual EPS; net worth = Equity Capital + Reserves; ``roe`` = Net Profit /
    net worth × 100; ``debt_equity`` = Borrowings / net worth; shares = Net Profit / EPS;
    ``book_value_ps`` = net worth / shares. ``available_date = period_end + lag_days``. Returns a
    **superset** of the carried store's schema (index=available_date; the original
    period_end/eps_ttm/book_value_ps/roe/debt_equity in the same positions, PLUS the Part-1.2 depth
    levels sales/operating_profit/opm_pct/net_profit/total_assets/interest/depreciation — raw annual
    values, growth/ratios derived downstream). Additive: ``value_quality_series`` and every existing
    caller select their columns by name, so they consume it unchanged. Empty frame when nothing parses.
    Lookahead-safe by construction (each value is stamped period_end + lag_days)."""
    eps_row = _screener_row(profit_loss, ("EPS in Rs", "EPS", "Adjusted EPS in Rs"))
    np_row = _screener_row(profit_loss, ("Net Profit", "Profit after tax"))
    sales_row = _screener_row(profit_loss, ("Sales", "Revenue"))
    op_row = _screener_row(profit_loss, ("Operating Profit", "Financing Profit"))
    opm_row = _screener_row(profit_loss, ("OPM %", "Financing Margin %"))
    int_row = _screener_row(profit_loss, ("Interest",))
    dep_row = _screener_row(profit_loss, ("Depreciation",))
    eq_row = _screener_row(balance_sheet, ("Equity Capital", "Share Capital"))
    res_row = _screener_row(balance_sheet, ("Reserves", "Reserves and Surplus"))
    borr_row = _screener_row(balance_sheet, ("Borrowings", "Total Debt"))
    ta_row = _screener_row(balance_sheet, ("Total Assets",))

    labels: list[str] = []
    for r in (eps_row, np_row, sales_row, op_row, opm_row, int_row, dep_row, eq_row, res_row, borr_row, ta_row):
        if r is not None:
            for lbl in r.index:
                if lbl not in labels:
                    labels.append(str(lbl))

    def _cell(row: pd.Series | None, lbl: str) -> float:
        return _screener_num(row[lbl]) if row is not None and lbl in row else float("nan")

    rows: list[dict] = []
    for lbl in labels:
        pe = _period_end_from_label(lbl)
        if pe is None:
            continue
        eps = _cell(eps_row, lbl)
        net_profit = _cell(np_row, lbl)
        eq, res, borr = _cell(eq_row, lbl), _cell(res_row, lbl), _cell(borr_row, lbl)
        net_worth = eq + res if _ok(eq) and _ok(res) else float("nan")
        roe = (net_profit / net_worth * 100.0
               if _ok(net_profit) and _ok(net_worth) and net_worth != 0 else float("nan"))
        de = borr / net_worth if _ok(borr) and _ok(net_worth) and net_worth != 0 else float("nan")
        shares = net_profit / eps if _ok(net_profit) and _ok(eps) and eps != 0 else float("nan")
        bvps = net_worth / shares if _ok(net_worth) and _ok(shares) and shares != 0 else float("nan")
        rows.append({"available_date": available_date_from_period_end(pe, lag_days),
                     "period_end": pe, "eps_ttm": eps, "book_value_ps": bvps,
                     "roe": roe, "debt_equity": de,
                     # ── depth fields (Part 1.2): raw annual levels; growth/ratios derived in features ──
                     "sales": _cell(sales_row, lbl), "operating_profit": _cell(op_row, lbl),
                     "opm_pct": _cell(opm_row, lbl), "net_profit": net_profit,
                     "total_assets": _cell(ta_row, lbl), "interest": _cell(int_row, lbl),
                     "depreciation": _cell(dep_row, lbl)})

    cols = ["period_end", "eps_ttm", "book_value_ps", "roe", "debt_equity",
            "sales", "operating_profit", "opm_pct", "net_profit", "total_assets", "interest", "depreciation"]
    if not rows:
        return pd.DataFrame(columns=cols).set_axis(pd.DatetimeIndex([], name="available_date"))
    frame = pd.DataFrame(rows).set_index("available_date").sort_index()
    return frame[~frame.index.duplicated(keep="last")]
