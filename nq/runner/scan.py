"""Live scan entry point — data → ranked panel → signals → ``results/signals_today.json``.

Wires the whole long-horizon pipeline for one scan: load OHLCV (the incremental JSON cache by
default), compute the long-horizon features, compose the ranked eligible panel (membership →
clean → large+mid → PIT D/E → solvency → rank), quarantine demerger-suspect names, then emit the
top-quantile non-held BUY signals for the latest date. Lean: it reuses ``nq.data`` + ``nq.engine``
+ ``nq.strategy`` end-to-end (no logic of its own beyond orchestration + the JSON write).

The reproduction-grade backtest of this same pipeline against baseline_v0 runs on the CLOUD (the
local OHLCV cache is a degenerate survivor subset — inadmissible for headline numbers).
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from config import RESULTS_DIR, load_frozen_cfg
from nq.data.features import compute_all_features
from nq.data.fundamentals import load_fund_store
from nq.data.membership import load_membership
from nq.data.ohlcv import demerger_suspect_names, load_ohlcv_json
from nq.engine.panel import compose_ranked_panel
from nq.strategy.long_horizon import EQUITY, scan

OUT_TODAY = RESULTS_DIR / "signals_today.json"


def run_scan(
    *,
    ohlcv: Mapping[str, pd.DataFrame] | None = None,
    membership: dict | None = None,
    fund_store: Mapping[str, pd.DataFrame] | None = None,
    cfg: Mapping[str, Any] | None = None,
    held: Iterable[str] = (),
    equity: float = EQUITY,
    as_of: Any = None,
    quarantine_demergers: bool = True,
    out_path: Path | None = OUT_TODAY,
    write: bool = True,
) -> dict[str, Any]:
    """Run one long-horizon scan and (optionally) write ``signals_today.json``.

    Defaults load the carried artifacts: the incremental OHLCV JSON cache, the frozen cfg, the
    PIT membership file, and the Screener fundamentals store. Pass explicit objects to scan a
    fixed in-memory universe (tests / a cloud panel). Returns
    ``{as_of, n_signals, held, signals, quarantined}``.
    """
    cfg = dict(load_frozen_cfg() if cfg is None else cfg)
    ohlcv = load_ohlcv_json() if ohlcv is None else dict(ohlcv)
    if not ohlcv:
        result = {"as_of": None, "n_signals": 0, "held": list(held), "signals": [],
                  "quarantined": [], "error": "no OHLCV available"}
        if write and out_path is not None:
            _write(out_path, result)
        return result

    membership = load_membership() if membership is None else membership
    fund_store = load_fund_store() if fund_store is None else fund_store

    features = compute_all_features(ohlcv)
    panel = compose_ranked_panel(features, ohlcv, fund_store=fund_store, membership=membership)
    suspect = sorted(demerger_suspect_names(ohlcv)) if quarantine_demergers else []

    signals = scan(panel, cfg, held=held, suspect=suspect, equity=equity, as_of=as_of)
    as_of_str = signals[0]["signal_date"] if signals else (
        None if panel.empty else pd.to_datetime(panel["date"]).max().strftime("%Y-%m-%d"))

    result = {
        "as_of": as_of_str, "n_signals": len(signals), "held": sorted(str(h) for h in held),
        "signals": signals, "quarantined": suspect,
    }
    if write and out_path is not None:
        _write(out_path, result)
    return result


def _write(out_path: Path, result: dict[str, Any]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")


def main() -> None:  # pragma: no cover - CLI entry
    res = run_scan()
    print(f"signals_today: as_of={res['as_of']} | {res['n_signals']} signal(s) | "
          f"{len(res['quarantined'])} quarantined -> {OUT_TODAY}")


if __name__ == "__main__":  # pragma: no cover
    main()
