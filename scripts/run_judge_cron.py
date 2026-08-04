"""Run the informed judge over this week's issued cards (pre-reg 0125). FORWARD ONLY.

Called by the Saturday scanner cron AFTER card generation. One independent call per card; every
attempt (success or failure) is appended to the hash-chained `results/judge_log.jsonl`.

**This never blocks the scanner.** Missing API key, missing SDK, model drift, rendering failure, or a
per-card API error all exit 0 with a logged reason. The scanner's state is already committed by the
time this runs; the judge is an observer.

**Sealed** (pre-reg §5): this script writes and never reads back a verdict. Nothing prints a verdict.

    python scripts/run_judge_cron.py --dry-run   # build inputs, make no API call
    python scripts/run_judge_cron.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from nq.paper.judge import (  # noqa: E402
    MODEL, ModelDriftError, assert_model_available, build_card_context, judge_card,
)
from nq.paper.judge_log import DEFAULT_LOG, append_row, logged_keys  # noqa: E402

ENVELOPE = ROOT / "results" / "signals_today_weekly.json"
SMA_PANEL = ROOT / "results" / "weekly_sma_panel.csv"
CHART_DIR = ROOT / "results" / "judge_charts"


def _log(msg: str) -> None:
    print(f"judge: {msg}")


def _ext_band(ext: float | None) -> str | None:
    if ext is None:
        return None
    for hi, name in ((0.0, "<0"), (5.0, "0-5%"), (10.0, "5-10%"),
                     (15.0, "10-15%"), (20.0, "15-20%"), (25.0, "20-25%")):
        if ext < hi:
            return name
    return ">25%"


def _sma_lookup() -> dict[str, float]:
    """Signal-week 44w SMA per ticker, from the panel the cards themselves were built from."""
    if not SMA_PANEL.exists():
        return {}
    import csv
    out: dict[str, float] = {}
    with open(SMA_PANEL, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            try:
                out[str(r.get("ticker", "")).upper()] = float(r.get("sma44") or r.get("sma") or "nan")
            except (TypeError, ValueError):
                continue
    return out


def _event_status(ticker: str, as_of: str) -> dict:
    """PIT earnings-calendar status from the 0120 module. Absent data is reported, never guessed."""
    try:
        import pandas as pd

        from nq.data.earnings import EARNINGS_RAW_PATH, build_event_table, known_events_features
        if not Path(EARNINGS_RAW_PATH).exists():
            return {"available": False, "reason": "no earnings source on this runner"}
        events = build_event_table(pd.read_parquet(EARNINGS_RAW_PATH))
        pairs = pd.DataFrame([{"symbol": ticker, "asof": pd.Timestamp(as_of)}])
        feat = known_events_features(events, pairs).iloc[0]
        days = feat.get("days_to_known_event")
        days = None if days != days else float(days)            # NaN -> None
        return {"available": True, "days_to_known_event": days,
                "known_event_within_14cd": bool(days is not None and 0 <= days <= 14)}
    except Exception as exc:                                    # noqa: BLE001 — never block
        return {"available": False, "reason": f"{type(exc).__name__}: {exc}"}


_PANEL: dict[str, object] = {}


def _panel():
    """Build the weekly panel ONCE per run, from the LIVE cache.

    Deliberately NOT `render_chart.render()`: that helper reloads the universe on every call (a full
    load per card) and reads `corrected_universe()` — the backtest universe with the delisted
    backfill, which is not committed and which the live cron explicitly does not use. The judge is a
    live-forward instrument, so it sees exactly the bars the cards were built from.
    """
    if not _PANEL:
        import pandas as pd

        import run_bhanushali_weekly_crs as CRS
        import run_bhanushali_weekly_rank as R94
        from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache

        _PANEL["P"] = R94.prep_weekly_rank(dict(load_ohlcv_cache(OHLCV_CACHE)))
        _PANEL["n50"] = (pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"])
                         .set_index("date")["nifty50_close"].sort_index())
    return _PANEL["P"], _PANEL["n50"]


def _render_chart(ticker: str) -> bytes | None:
    """Weekly candles + 44w/20w SMA for one card, as PNG bytes.

    Returns None on failure — a card with no chart is NOT judged with fewer inputs (that would
    silently change the frozen instrument mid-cohort); it is skipped and logged as a failure row.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        import render_chart                                   # for its committed weekly() builder

        P, n50 = _panel()
        if ticker not in P:
            return None
        w = render_chart.weekly(ticker, P, n50)
        n = min(len(w["wc"]), 160)                            # ~3 years of weekly context
        wd, wo, wh, wl, wc = (w["wd"][-n:], w["wo"][-n:], w["wh"][-n:], w["wl"][-n:], w["wc"][-n:])
        ws, w20 = w["ws"][-n:], w["w20"][-n:]

        fig, ax = plt.subplots(figsize=(12, 6))
        for i in range(n):
            up = wc[i] >= wo[i]
            ax.plot([i, i], [wl[i], wh[i]], color="#333", lw=0.7, zorder=1)
            ax.add_patch(plt.Rectangle((i - 0.3, min(wo[i], wc[i])), 0.6,
                                       max(abs(wc[i] - wo[i]), 1e-9),
                                       color="#1a7f37" if up else "#b3261e", zorder=2))
        ax.plot(range(n), ws, color="#1f77b4", lw=1.6, label="44w SMA")
        ax.plot(range(n), w20, color="#ff7f0e", lw=1.0, label="20w SMA")
        ax.set_title(f"{ticker} — weekly, {wd[0].date()}..{wd[-1].date()}", fontsize=11)
        ax.legend(loc="upper left"); ax.grid(alpha=0.15)
        step = max(n // 12, 1)
        ax.set_xticks(range(0, n, step))
        ax.set_xticklabels([wd[i].strftime("%b-%y") for i in range(0, n, step)],
                           rotation=45, fontsize=8)

        CHART_DIR.mkdir(parents=True, exist_ok=True)
        out = CHART_DIR / f"{ticker}.png"
        fig.tight_layout(); fig.savefig(out, dpi=90); plt.close(fig)
        return out.read_bytes()
    except Exception:                                           # noqa: BLE001 — never block
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="informed-judge forward stream (pre-reg 0125)")
    ap.add_argument("--dry-run", action="store_true", help="build inputs, make no API call")
    ap.add_argument("--log", default=str(DEFAULT_LOG))
    args = ap.parse_args(argv)

    if not ENVELOPE.exists():
        _log(f"no envelope at {ENVELOPE} — nothing to judge")
        return 0
    envelope = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    as_of = str(envelope.get("generated_at") or datetime.now(timezone.utc).date())
    cards = [s for s in (envelope.get("signals") or [])
             if isinstance(s, dict) and s.get("tier") == "signal" and s.get("entry") is not None]
    if not cards:
        _log(f"as-of {as_of}: no buy cards this week")
        return 0

    already = logged_keys(args.log)
    todo = [c for c in cards if (as_of, str(c.get("ticker"))) not in already]
    _log(f"as-of {as_of}: {len(cards)} cards, {len(todo)} not yet logged")
    if not todo:
        return 0

    smas = _sma_lookup()
    client = None
    if not args.dry_run:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            _log("ANTHROPIC_API_KEY not set on this runner — judge SKIPPED (scanner unaffected). "
                 "Add it as a repository secret to enable the stream.")
            return 0
        try:
            import anthropic
        except ImportError:
            _log("anthropic SDK not installed — judge SKIPPED. Install the '[judge]' extra.")
            return 0
        client = anthropic.Anthropic()
        try:
            assert_model_available(client)
        except ModelDriftError as exc:
            _log(f"::error::MODEL DRIFT — {exc}. No substitution made; judge SKIPPED this run.")
            return 0

    n_ok = n_fail = 0
    cost = 0.0
    for card in todo:
        tkr = str(card.get("ticker"))
        # Dry run proves input assembly and that no call is made; it does not build the panel (a full
        # universe load) — chart rendering is exercised by the live run.
        png = b"" if args.dry_run else _render_chart(tkr)
        if png is None:
            append_row({"as_of": as_of, "ticker": tkr, "signal_date": str(card.get("signal_date")),
                        "model": MODEL, "ok": False, "error": "chart render failed"}, args.log)
            n_fail += 1
            _log(f"{tkr}: chart render failed — logged, not judged")
            continue

        ext = None
        sma = smas.get(tkr.upper())
        try:
            if sma and card.get("entry"):
                ext = round(100.0 * (float(card["entry"]) / sma - 1.0), 2)
        except (TypeError, ValueError, ZeroDivisionError):
            ext = None
        ctx = build_card_context(card, sma44=sma, ext_vs_sma_pct=ext, ext_band=_ext_band(ext),
                                 event_status=_event_status(tkr, as_of))

        if args.dry_run:
            _log(f"{tkr}: DRY RUN — chart {len(png)}B, context {len(ctx)}B, no call made")
            continue

        row = judge_card(client, card=card, chart_png=png, context_json=ctx, as_of=as_of,
                         fetched_at=datetime.now(timezone.utc).isoformat())
        append_row(row, args.log)
        cost += float(row.get("cost_usd") or 0.0)
        if row.get("ok"):
            n_ok += 1
            _log(f"{tkr}: logged (sealed)")            # never prints the verdict — pre-reg §5
        else:
            n_fail += 1
            _log(f"{tkr}: call failed — {row.get('error')}")

    if not args.dry_run:
        _log(f"run complete: {n_ok} logged, {n_fail} failed, cost ${cost:.4f} -> {args.log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
