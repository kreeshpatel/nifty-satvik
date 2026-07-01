"""
Landing page stats — public endpoint that returns ONLY safe aggregate
data for the marketing landing page. NEVER returns ticker names, entry
prices, or any actionable trading information.

Headline backtest stats (CAGR, total trades, win rate, max DD, etc.) come
from production_strategy.json which the strategy revalidator cron rewrites
quarterly. Equity curve is sampled from portfolio_history.csv. Cached for
1 hour — the underlying data only moves on quarterly revalidation, so a
shorter TTL just heats Render's egress for nothing.
"""

import time
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter

logger = logging.getLogger("landing_stats")
router = APIRouter(tags=["landing-stats"])

# In-memory cache. The underlying signals_history.json + production_strategy.json
# only change on the daily cron (4:15 PM IST) and quarterly revalidation, so a
# 1-hour TTL keeps the landing snappy without serving truly stale data.
_cache = {"data": None, "ts": 0}
CACHE_TTL = 3600  # 1 hour

EQUITY_CURVE_POINTS = 60  # sample portfolio_history.csv down to ~60 points
INITIAL_CAPITAL = 1_000_000.0  # baseline used to compute % return on the curve

# Frozen baseline_v1 anchor — the locked production model (ADR-0006), sourced from
# research/baseline_v1.json on the pinned dataset (dataset-pin-20260701). GROSS backtest,
# in-sample, 2017-2026; `net_cagr_pct` is after Indian transaction costs + 20% STCG. These
# are published, frozen research results that only change when a new baseline is deliberately
# minted (a gated, code-reviewed event), so they live here as constants rather than being
# fetched. SAFETY: none of these reveal the strategy (no signal, factor, hold horizon, or
# parameter) — they are aggregate, non-actionable performance statistics only.
BASELINE_V1 = {
    "version": "baseline_v1",
    "period": "2017–2026",
    "validated_on": "2026-07-01",
    "cagr_pct": 15.46,                     # gross
    "net_cagr_pct": 12.2,                  # after costs + 20% STCG (~12% headline)
    "sharpe": 0.667,
    "sharpe_ci_95": [-0.02, 1.43],         # block-bootstrap 95% CI (straddles 0 — disclosed)
    "win_rate_pct": 60.36,
    "total_trades": 1279,
    "max_drawdown_pct": -46.26,            # raw, unhedged book
    "operational_max_drawdown_pct": -39,   # with the shipped volatility-target overlay
    "psr_gt0_pct": 97.4,                   # Probabilistic Sharpe Ratio, P(Sharpe > 0)
    "min_trl_years": 6.2,                  # Minimum Track Record Length (95%)
    "basis": "gross backtest, in-sample (2017-2026), after costs + 20% STCG for net; "
             "returns are lumpy and bull-concentrated with a deep drawdown",
}


def _live_block() -> dict | None:
    """Live paper-trading forward record (the leak-proof out-of-sample) from the cron-
    published paper book. Aggregate only — never tickers/prices."""
    try:
        from github_data import fetch_github_json
        pf = fetch_github_json("results/paper_portfolio.json") or {}
        an = fetch_github_json("results/signal_analytics.json") or {}
        nav = pf.get("total_value") or pf.get("nav")
        total_ret = round((float(nav) / INITIAL_CAPITAL - 1) * 100, 2) if nav else None
        return {
            "since": "2026-06-30",
            "nav": round(float(nav), 2) if nav else None,
            "starting_nav": INITIAL_CAPITAL,
            "total_return_pct": total_ret,
            "n_positions": pf.get("n_positions") or an.get("active"),
            "n_closed": an.get("total_closed"),
            "win_rate_pct": an.get("win_rate"),
            "note": "Live paper record since inception — the forward wall the model is judged on. "
                    "No real capital has traded; the gate to live capital is >=30 closed paper trades.",
        }
    except Exception as e:
        logger.warning(f"live paper block failed: {e}")
        return None


def _compute_stats() -> dict:
    """
    Read trade_log.csv from GitHub and compute aggregate stats.
    Returns ONLY safe data — no tickers, no prices, no current signals.
    """
    try:
        from github_data import fetch_github_csv
        df = fetch_github_csv("results/trade_log.csv")
    except Exception as e:
        logger.warning(f"Could not load trade_log: {e}")
        df = None

    # Default fallback values if no data
    stats = {
        "total_trades": 0,
        "win_rate_pct": 0,
        "avg_winner_pct": 0,
        "avg_loser_pct": 0,
        "best_streak": 0,
        "yesterday": {
            "trades_closed": 0,
            "avg_pct": 0,
        },
        "last_30_days": {
            "trades_closed": 0,
            "win_rate_pct": 0,
            "total_return_pct": 0,
        },
        "closed_signals_recent": [],
        "sector_heatmap_30d": [],
        "backtest": dict(BASELINE_V1),   # frozen anchor — always present
        "live": None,
        "equity_curve": [],
    }

    # Trade-log section: fills total_trades / win_rate_pct / avg_winner_pct /
    # last_30_days. Skipped cleanly if the file isn't available — every other
    # section below is independent and runs on its own data source.
    if df is not None and not df.empty and "return_pct" in df.columns:
        try:
            total = len(df)
            wins = df[df["return_pct"] > 0]
            losses = df[df["return_pct"] <= 0]

            stats["total_trades"] = int(total)
            stats["win_rate_pct"] = round(len(wins) / total * 100, 1) if total > 0 else 0
            stats["avg_winner_pct"] = round(float(wins["return_pct"].mean()), 2) if len(wins) > 0 else 0
            stats["avg_loser_pct"] = round(float(losses["return_pct"].mean()), 2) if len(losses) > 0 else 0

            # Best winning streak
            try:
                sorted_df = df.sort_values("exit_date") if "exit_date" in df.columns else df
                outcomes = (sorted_df["return_pct"] > 0).tolist()
                best_streak = 0
                current = 0
                for o in outcomes:
                    if o:
                        current += 1
                        best_streak = max(best_streak, current)
                    else:
                        current = 0
                stats["best_streak"] = best_streak
            except Exception:
                pass

            # Last 30 days stats
            if "exit_date" in df.columns:
                try:
                    import pandas as pd
                    df["_exit_dt"] = pd.to_datetime(df["exit_date"], errors="coerce")
                    cutoff = datetime.now() - timedelta(days=30)
                    recent = df[df["_exit_dt"] >= cutoff]
                    if len(recent) > 0:
                        recent_wins = recent[recent["return_pct"] > 0]
                        stats["last_30_days"] = {
                            "trades_closed": int(len(recent)),
                            "win_rate_pct": round(len(recent_wins) / len(recent) * 100, 1),
                            "total_return_pct": round(float(recent["return_pct"].sum()), 2),
                        }

                    # Yesterday's trades only
                    yesterday_start = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                    yesterday_end = yesterday_start + timedelta(days=1)
                    y_df = df[(df["_exit_dt"] >= yesterday_start) & (df["_exit_dt"] < yesterday_end)]
                    if len(y_df) > 0:
                        stats["yesterday"] = {
                            "trades_closed": int(len(y_df)),
                            "avg_pct": round(float(y_df["return_pct"].mean()), 2),
                        }
                except Exception as e:
                    logger.warning(f"Date filtering failed: {e}")
        except Exception as e:
            logger.error(f"Error computing landing stats: {e}")

    # Closed-signal strip + sector heatmap come from signals_history.json so
    # we get sector and status without needing the full trade_log. The strip
    # is anonymized — sector + outcome + return only, never ticker or price.
    try:
        from github_data import fetch_github_json
        history = fetch_github_json("results/signals_history.json")
        if isinstance(history, list) and history:
            closed_states = {"HIT_TARGET", "HIT_STOP", "EXPIRED", "CLOSED"}
            closed = [
                s for s in history
                if isinstance(s, dict)
                and str(s.get("status", "")).upper() in closed_states
            ]

            def _sort_key(s):
                return s.get("last_tracked") or s.get("signal_date") or ""

            closed.sort(key=_sort_key, reverse=True)

            stats["closed_signals_recent"] = [
                {
                    "sector": s.get("sector") or "Other",
                    "status": str(s.get("status", "")).upper(),
                    "pnl_pct": round(float(s.get("pnl_pct") or 0.0), 2),
                    "hold_days": int(s.get("days_since") or s.get("hold_days") or 0),
                    "signal_date": s.get("signal_date"),
                }
                for s in closed[:10]
            ]

            # Sector heatmap — group last 30d closed signals by sector,
            # compute mean pnl_pct + count. Capped at 22 sectors for the grid.
            from collections import defaultdict
            buckets = defaultdict(list)
            cutoff_iso = (datetime.now() - timedelta(days=30)).date().isoformat()
            for s in closed:
                date = s.get("signal_date") or ""
                if date >= cutoff_iso:
                    sector = s.get("sector") or "Other"
                    pnl = s.get("pnl_pct")
                    if pnl is not None:
                        buckets[sector].append(float(pnl))

            heatmap = []
            for sector, pnls in buckets.items():
                if not pnls:
                    continue
                heatmap.append({
                    "sector": sector,
                    "avg_pct": round(sum(pnls) / len(pnls), 2),
                    "trades": len(pnls),
                })
            heatmap.sort(key=lambda x: abs(x["avg_pct"]), reverse=True)
            stats["sector_heatmap_30d"] = heatmap[:22]
    except Exception as e:
        logger.warning(f"signals_history enrichment failed: {e}")

    # Headline backtest stats come from the frozen BASELINE_V1 anchor (set in the default
    # dict above). The legacy production_strategy.json path described the RETIRED v1 model
    # (two-head LightGBM / 14-day horizon) and is not emitted by the clean engine, so it is
    # intentionally NOT read here — the landing headlines the real, locked baseline_v1.

    # Live paper forward record (the leak-proof out-of-sample) — updates daily via the cron.
    stats["live"] = _live_block()

    # Equity curve — sample portfolio_history.csv down to ~60 points so the
    # frontend SVG renders cleanly without shipping 1100 rows of payload.
    # The CSV historically had a schema break (early rows: date,total_value;
    # later rows: 11 columns), so we read with tolerant settings.
    try:
        import pandas as pd
        from github_data import fetch_github_file
        text = fetch_github_file("results/portfolio_history.csv")
        ph = None
        if text:
            from io import StringIO
            try:
                ph = pd.read_csv(
                    StringIO(text),
                    usecols=["date", "total_value"],
                    on_bad_lines="skip",
                    engine="python",
                )
            except Exception:
                ph = None
        if ph is not None and not ph.empty and "date" in ph.columns and "total_value" in ph.columns:
            curve = ph[["date", "total_value"]].dropna().reset_index(drop=True)
            # Trim trailing baseline rows. The paper portfolio sometimes resets
            # to INITIAL_CAPITAL during between-cycle periods, which would make
            # the curve "end at 0%" and misrepresent the actual track record.
            non_baseline = curve.index[curve["total_value"] != INITIAL_CAPITAL]
            if len(non_baseline) > 0:
                curve = curve.iloc[: int(non_baseline.max()) + 1].reset_index(drop=True)
            n = len(curve)
            if n > 0:
                # Sample down to EQUITY_CURVE_POINTS by taking every Nth row.
                step = max(1, n // EQUITY_CURVE_POINTS)
                sampled = curve.iloc[::step].copy()
                # Always include the last row so the curve ends at the real
                # most-recent value, not whatever the sampling stride landed on.
                if sampled.iloc[-1]["date"] != curve.iloc[-1]["date"]:
                    sampled = pd.concat([sampled, curve.iloc[[-1]]], ignore_index=True)
                stats["equity_curve"] = [
                    {
                        "date": str(row["date"]),
                        "return_pct": round(
                            (float(row["total_value"]) - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100, 2
                        ),
                    }
                    for _, row in sampled.iterrows()
                ]
    except Exception as e:
        logger.warning(f"portfolio_history sampling failed: {e}")

    return stats


@router.get("/landing-stats")
async def get_landing_stats():
    """
    Public endpoint — returns aggregate trading stats for the landing page.

    SAFETY: This endpoint NEVER returns:
    - Ticker symbols
    - Entry/exit prices
    - Current open signals
    - Any actionable trading information

    It only returns historical aggregate stats (win rates, counts, percentages)
    so visitors can see proof of performance without being able to copy trades.
    """
    now = time.time()
    if _cache["data"] and (now - _cache["ts"]) < CACHE_TTL:
        return _cache["data"]

    stats = _compute_stats()
    _cache["data"] = stats
    _cache["ts"] = now
    return stats
