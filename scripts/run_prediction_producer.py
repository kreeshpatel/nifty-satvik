"""Feed the prediction ledger: one forecast per fresh card, resolved from the price path.

The ledger (`nq/brain/predictions.py`, #122) had no producer, so its calibration clock (MIN_RESOLVED =
20) had not started. Each Saturday this:

  1. FORECASTS — for every FRESH card in `results/signals_today_weekly.json`, the claim "price touches
     the +2R target before the stop", with the driftless first-passage null b/(a+b) as the probability
     (`basis = first_passage_null`). Stamped at the card's as-of; the path it predicts starts the next
     session, so the forecast strictly pre-dates its outcome.
  2. RESOLVES — every open forecast whose path has touched either level, using
     `nq.brain.excursions.first_passage` on the cached daily bars after the signal date. A bar touching
     both counts as the stop (the conservative convention). Whether the card was bought does not matter:
     the claim is about the price path, so an unfilled card still resolves.

Idempotent: a subject+claim already forecast is skipped, a resolved forecast is never re-resolved.
The forecasts are an OUTPUT, never a pre-entry feature — nothing may join them into a model's inputs
without purge/embargo (B5).

    python scripts/run_prediction_producer.py [--no-resolve]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nq.brain import predictions as P  # noqa: E402
from nq.brain.excursions import HIT, UNRESOLVED, first_passage, null_p_target_first  # noqa: E402

CARDS = ROOT / "results" / "signals_today_weekly.json"
CLAIM = "touches the +2R target before the stop"
BASIS = "first_passage_null"
RESOLVE_WITHIN_DAYS = 365        # the deadline the ledger requires; the null itself has no horizon
MAX_STALE_DAYS = 3               # Friday as-of -> Saturday run. Older means the stamp would be a backdate.


def forecasts_for(cards: dict) -> list[dict]:
    """The forecast rows a card envelope implies. Pure."""
    as_of = str(cards.get("generated_at") or "")
    out = []
    for c in cards.get("signals", []) or []:
        if c.get("status") != "FRESH":
            continue
        e, s, t = c.get("entry"), c.get("stop"), c.get("target")
        if not (isinstance(e, (int, float)) and isinstance(s, (int, float)) and isinstance(t, (int, float))
                and s < e < t):
            continue
        sig = str(c.get("signal_date") or as_of)
        out.append({"subject": f"{c.get('ticker')}:{sig}", "ticker": c.get("ticker"), "signal_date": sig,
                    "entry": float(e), "stop": float(s), "target": float(t),
                    "probability": null_p_target_first(float(e), float(s), float(t)),
                    "stamped_at": as_of,
                    "resolve_by": (pd.Timestamp(as_of) + pd.Timedelta(days=RESOLVE_WITHIN_DAYS)).date().isoformat()})
    return out


def _open_predictions(rows: list[dict]) -> list[dict]:
    done = {r.get("predicts") for r in rows if r.get("kind") == "resolution"}
    return [r for r in rows if r.get("kind") == "prediction" and r.get("basis") == BASIS
            and r.get("claim") == CLAIM and r.get("row_hash") not in done]


def resolve_one(pred: dict, ohlcv: dict, levels: dict) -> tuple[bool, str] | None:
    """(outcome, resolved_at) once the path has decided; None while it has not. Pure."""
    tkr, sig = pred["subject"].rsplit(":", 1)
    lv = levels.get(pred["subject"])
    df = ohlcv.get(tkr)
    if lv is None or df is None or not len(df):
        return None
    path = df[df.index > pd.Timestamp(sig)]
    if not len(path):
        return None
    ps = first_passage(path["High"].to_numpy(), path["Low"].to_numpy(),
                       entry=lv["entry"], stop=lv["stop"], target=lv["target"])
    if ps.outcome == UNRESOLVED:
        return None
    when = path.index[ps.sessions].date().isoformat()
    return ps.outcome == HIT, when


def _levels_from_archive() -> dict:
    """entry/stop/target per subject, from every archived card envelope — the levels the forecast used."""
    out = {}
    for f in sorted((ROOT / "results" / "archive").glob("*/signals_today_weekly.json")) + [CARDS]:
        try:
            for row in forecasts_for(json.loads(f.read_text(encoding="utf-8"))):
                out.setdefault(row["subject"], row)
        except Exception:        # a malformed old envelope cannot block today's run
            continue
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-resolve", action="store_true", help="forecast only (no price cache needed)")
    ap.add_argument("--ledger", default=str(P.DEFAULT_LOG))
    ap.add_argument("--today", default=str(pd.Timestamp.today().date()), help="run date (tests)")
    args = ap.parse_args(argv)
    ledger = Path(args.ledger)

    rows = P.read_verified(ledger) if ledger.exists() else []
    seen = {(r.get("subject"), r.get("claim")) for r in rows if r.get("kind") == "prediction"}
    n_new = 0
    env = json.loads(CARDS.read_text(encoding="utf-8"))
    age = (pd.Timestamp(args.today) - pd.Timestamp(str(env.get("generated_at")))).days
    fresh = forecasts_for(env) if 0 <= age <= MAX_STALE_DAYS else []
    if age > MAX_STALE_DAYS:
        # A forecast stamped at an as-of written days later is a backdate: its path has already begun.
        print(f"cards are {age} days old (as-of {env.get('generated_at')}) — no forecasts this run; "
              f"stamping them would backdate them")
    for f in fresh:
        if (f["subject"], CLAIM) in seen:
            continue
        P.append_prediction(subject=f["subject"], claim=CLAIM, probability=f["probability"],
                            stamped_at=f["stamped_at"], resolve_by=f["resolve_by"], basis=BASIS, path=ledger)
        n_new += 1

    n_res = 0
    if not args.no_resolve:
        from nq.data.ohlcv import load_ohlcv_cache
        ohlcv = load_ohlcv_cache() or {}
        levels = _levels_from_archive()
        rows = P.read_verified(ledger) if ledger.exists() else []
        for pred in _open_predictions(rows):
            r = resolve_one(pred, ohlcv, levels)
            if r is not None:
                P.append_resolution(predicts=pred["row_hash"], outcome=r[0], resolved_at=r[1],
                                    note="first_passage on cached daily bars", path=ledger)
                n_res += 1

    rows = P.read_verified(ledger) if ledger.exists() else []
    s = P.summarise(rows)
    print(f"prediction ledger: +{n_new} forecast(s), +{n_res} resolution(s) | "
          f"resolved {s.get('n_resolved')}/{s.get('min_resolved')} needed for calibration")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
