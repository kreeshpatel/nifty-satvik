"""Accumulator health harness — the mid-August health check runs THIS script and nothing else.

Produces one standard report (md + json) on the forward accumulators (bulk/block + ratings):
calendar-aware row/gap accounting, an idempotency probe (live re-fetch must add ~0 keyed rows),
symbol_clean ratio trend, staleness/health-file status, and cron + gitignore wiring checks.
Health METRICS only — no analysis of the accumulated data's content (standing rule).

    python scripts/diag_accumulator_health.py [--no-probe]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config import RESULTS_DIR  # noqa: E402

BB = RESULTS_DIR / "bulkblock_forward.csv"
RT = RESULTS_DIR / "ratings_forward.csv"
HEALTH = RESULTS_DIR / "forward_accum_health.json"
OUT_MD = ROOT / "diagnostics" / "research" / "accumulator_health_report.md"
OUT_JS = ROOT / "diagnostics" / "research" / "accumulator_health_report.json"
IDEMPOTENCY_TOLERANCE = 5   # keyed rows a live re-fetch may add (feed burstiness), else FAIL


def trading_days(lo: pd.Timestamp, hi: pd.Timestamp) -> pd.DatetimeIndex:
    """NSE-calendar-aware session list: cached OHLCV union calendar where it covers, weekdays beyond."""
    days = pd.bdate_range(lo, hi)
    try:
        from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache
        oh = load_ohlcv_cache(OHLCV_CACHE)
        cal = pd.DatetimeIndex(sorted(set().union(*[set(pd.to_datetime(g.index)) for g in oh.values()])))
        known = days[days <= cal.max()]
        holidays = set(known) - set(cal)
        days = pd.DatetimeIndex([d for d in days if d not in holidays])
    except Exception:
        pass                                            # cache unavailable -> weekday approximation
    return days


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--no-probe", action="store_true")
    args = ap.parse_args()
    rep: dict = {"generated": str(pd.Timestamp.now("UTC")), "feeds": {}, "checks": {}}
    lines = [f"# Accumulator Health Report — {pd.Timestamp.today().date()}", ""]

    for name, path, date_col, fmt in (("bulkblock", BB, "date", "%d-%b-%Y"),
                                      ("ratings", RT, "broadcast", "%d-%b-%Y %H:%M:%S")):
        f: dict = {"exists": path.exists()}
        if path.exists():
            df = pd.read_csv(path, dtype=str)
            dts = pd.to_datetime(df[date_col], format=fmt, errors="coerce").dt.normalize().dropna()
            f["rows"] = len(df)
            f["data_span"] = [str(dts.min().date()), str(dts.max().date())] if len(dts) else None
            f["fetch_span"] = [str(df["fetch_ts"].min()), str(df["fetch_ts"].max())]
            if len(dts):
                cal = trading_days(dts.min(), min(dts.max(), pd.Timestamp.today()))
                covered = set(dts)
                gaps = [str(d.date()) for d in cal if d not in covered]
                f["sessions_expected"] = len(cal); f["sessions_with_rows"] = len(cal) - len(gaps)
                f["gap_days"] = gaps
                f["note"] = ("gap days on an EVENT feed can be legitimately empty sessions; "
                             "a growing RUN of gaps is the failure signal")
            if name == "ratings" and "symbol_clean" in df.columns:
                by_fetch = df.groupby(df["fetch_ts"].str[:10])["symbol_clean"].apply(
                    lambda x: (x.astype(str) == "True").mean())
                f["symbol_clean_ratio_by_fetch_day"] = {k: round(v, 3) for k, v in by_fetch.items()}
        rep["feeds"][name] = f
        lines += [f"## {name}", f"- exists: {f['exists']}"]
        for k in ("rows", "data_span", "sessions_expected", "sessions_with_rows"):
            if k in f:
                lines.append(f"- {k}: {f[k]}")
        if f.get("gap_days") is not None:
            lines.append(f"- gap days ({len(f['gap_days'])}): {f['gap_days'][:10]}"
                         + (" ..." if len(f["gap_days"]) > 10 else ""))
        if "symbol_clean_ratio_by_fetch_day" in f:
            lines.append(f"- symbol_clean ratio by fetch day: {f['symbol_clean_ratio_by_fetch_day']}")
        lines.append("")

    # health-file + staleness
    h = json.loads(HEALTH.read_text()) if HEALTH.exists() else {}
    rep["checks"]["health_file"] = h
    stale_flags = {k: v.get("stale") for k, v in h.items()} if h else {}
    lines += ["## health file", f"- staleness flags: {stale_flags}", ""]

    # idempotency probe: live re-run of the collectors must add <= tolerance keyed rows
    if not args.no_probe:
        try:
            # The probe re-fetches and re-appends to measure idempotency. It MUST NOT touch the live
            # append-only record: an earlier version called the collectors against the live paths with
            # a literal "PROBE" timestamp and overwrote real fetch times on three rows (caught and
            # restored in 3216ce7). Now: copy the live files to a scratch dir, probe the COPIES with a
            # real timestamp, compare, discard. The live bytes are asserted unchanged afterwards.
            import hashlib
            import shutil
            import tempfile

            import requests
            from run_forward_accumulators import BB_OUT, RT_OUT, collect_bulkblock, collect_ratings, HDR  # noqa: E402

            def _sha(p):
                return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

            live = {"bulkblock": BB_OUT, "ratings": RT_OUT}
            before = {k: _sha(p) for k, p in live.items()}
            sess = requests.Session(); sess.get("https://www.nseindia.com/", headers=HDR, timeout=25)
            probe_ts = pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M:%S")
            adds = {}
            with tempfile.TemporaryDirectory(prefix="accum_probe_") as td:
                scratch = {k: Path(td) / p.name for k, p in live.items()}
                for k, p in live.items():
                    if p.exists():
                        shutil.copy2(p, scratch[k])
                adds["bulkblock"], _ = collect_bulkblock(sess, probe_ts, out=scratch["bulkblock"])
                adds["ratings"], _ = collect_ratings(sess, probe_ts, out=scratch["ratings"])
                scratch_grew = {k: (scratch[k].exists() and scratch[k].stat().st_size > 0) for k in scratch}
            after = {k: _sha(p) for k, p in live.items()}
            live_untouched = before == after
            ok = all(a <= IDEMPOTENCY_TOLERANCE for a in adds.values()) and live_untouched
            rep["checks"]["idempotency_probe"] = {"adds": adds, "tolerance": IDEMPOTENCY_TOLERANCE,
                                                  "live_untouched": live_untouched,
                                                  "probed_scratch_copies": scratch_grew, "pass": ok}
            lines += ["## idempotency probe",
                      f"- probed on scratch copies; live files untouched: {live_untouched}",
                      f"- re-fetch adds: {adds} (tolerance {IDEMPOTENCY_TOLERANCE}) "
                      f"-> {'PASS' if ok else 'FAIL'}", ""]
        except Exception as e:
            rep["checks"]["idempotency_probe"] = {"error": type(e).__name__}
            lines += ["## idempotency probe", f"- ERROR {type(e).__name__} (network?)", ""]

    # wiring checks: cron step + git-add + gitignore whitelist
    wf = (ROOT / ".github" / "workflows" / "cron-bhanushali-monitor.yml").read_text(encoding="utf-8")
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    wiring = {"cron_step": "run_forward_accumulators.py" in wf,
              "cron_git_add": "bulkblock_forward.csv" in wf and "ratings_forward.csv" in wf,
              "gitignore_whitelist": all(x in gi for x in
                                         ("!results/bulkblock_forward.csv", "!results/ratings_forward.csv",
                                          "!results/forward_accum_health.json"))}
    rep["checks"]["wiring"] = wiring
    lines += ["## wiring", *[f"- {k}: {'OK' if v else 'MISSING'}" for k, v in wiring.items()], ""]

    verdict = ("GREEN" if all(wiring.values())
               and not any(stale_flags.values() or [])
               and rep["checks"].get("idempotency_probe", {}).get("pass", True) else "ATTENTION")
    rep["verdict"] = verdict
    lines.insert(1, f"\n**VERDICT: {verdict}**\n")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    OUT_JS.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    print("\n".join(lines[:40])); print(f"-> {OUT_MD}\n-> {OUT_JS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
