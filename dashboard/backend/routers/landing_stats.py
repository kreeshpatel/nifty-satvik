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
        "backtest": None,
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

    # Headline backtest stats — production_strategy.json is rewritten on the
    # quarterly revalidation cron and is the authoritative source for the
    # CAGR / total-trades / win-rate / max-DD numbers shown in the hero +
    # KPI row. Frontend uses these in preference to the live-cron numbers
    # above for the headline display.
    try:
        from github_data import fetch_github_json
        strategy = fetch_github_json("results/production_strategy.json")
        if isinstance(strategy, dict):
            br = strategy.get("backtest_results") or {}
            stats["backtest"] = {
                "version": strategy.get("version"),
                "validated_on": strategy.get("validated_on"),
                "next_revalidation": strategy.get("next_revalidation"),
                "period": strategy.get("backtest_period"),
                "cagr_pct": br.get("cagr"),
                "total_return_pct": br.get("total_return"),
                "total_trades": br.get("total_trades"),
                "win_rate_pct": br.get("win_rate"),
                "avg_return_per_trade_pct": br.get("avg_return_per_trade"),
                "sharpe": br.get("sharpe_2024"),
                "max_drawdown_pct": br.get("max_drawdown"),
                "profit_factor": br.get("profit_factor_2024"),
            }
    except Exception as e:
        logger.warning(f"production_strategy enrichment failed: {e}")

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
