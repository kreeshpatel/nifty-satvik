"""Fetch result files from local filesystem first, then GitHub as fallback."""

import io
import logging
import json
import os
import time

import requests

from config import PROJECT_ROOT

_log = logging.getLogger("niftyquant.github_data")

# Re-pointed 2026-07-01: the clean nifty-satvik engine now owns results/* (the
# paper book's cron pushes paper_portfolio.json / portfolio_history.csv /
# paper_ledger_history.csv / paper_trades.json / signals_today.json here).
GITHUB_RAW = "https://raw.githubusercontent.com/kreeshpatel/nifty-satvik/main"
# CORRECTED 2026-08-29: this said the repo is PRIVATE and raw URLs 404 without auth. It is
# PUBLIC and they return 200. The authenticated contents endpoint is still preferred, for rate
# limits (60 req/hour unauthenticated vs 5,000) rather than for access. Same correction as
# routers/signals.py, which carried the identical stale claim.
GITHUB_API_CONTENTS = "https://api.github.com/repos/kreeshpatel/nifty-satvik/contents"


def _local_path(path: str) -> str:
    """Resolve a repo-relative path to an absolute local path."""
    return os.path.join(PROJECT_ROOT, path)


# results/* are cron-pushed to GitHub externally; Render's local copy goes
# stale between cron pushes (the web service only refreshes its filesystem on
# rebuild). So for results/* we PREFER GitHub (with a short cache) and fall
# back to local; for models/* and other deploy-time artifacts local-first is
# correct. Mirrors signals.py::_read_json_with_fallback (F9 fix — overview/
# positions/trades/backtest were silently serving stale local snapshots).
_RESULTS_CACHE_TTL = 30.0
_results_cache: dict[str, tuple[float, str]] = {}


def _read_local(path: str) -> str | None:
    local = _local_path(path)
    if os.path.isfile(local):
        try:
            with open(local, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass
    return None


def _fetch_public_raw(path: str) -> str | None:
    """Read over the PUBLIC raw URL — no token, and not subject to the API's 60/hour limit."""
    try:
        r = requests.get(f"{GITHUB_RAW}/{path}", timeout=10)
        if r.status_code == 200:
            return r.text
        _log.warning("public raw fetch %s -> HTTP %s", path, r.status_code)
    except requests.RequestException as exc:
        _log.warning("public raw fetch %s failed: %s", path, exc)
    return None


def _fetch_remote(path: str) -> str | None:
    """Authenticated contents endpoint, falling back to the public raw URL.

    `results/` is in .dockerignore and so is absent from the image: without a working remote read
    there is no local copy to serve. A single expired token used to take this to zero. The repo is
    public, so it no longer has to. Both fallbacks log — a quiet fallback hides a dead primary.
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        _log.warning("no GITHUB_TOKEN — reading %s over the public raw URL (60/hour per IP)", path)
        return _fetch_public_raw(path)
    try:
        r = requests.get(
            f"{GITHUB_API_CONTENTS}/{path}?ref=main",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.raw",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=10,
        )
        if r.status_code == 200:
            return r.text
        # Expired / revoked / rate-limited token. Recoverable, because the data is public — but
        # never silently, or a dead token is indistinguishable from a healthy one.
        _log.warning("authenticated fetch of %s -> HTTP %s; falling back to the public raw URL. "
                     "Check GITHUB_TOKEN.", path, r.status_code)
    except requests.RequestException as exc:
        _log.warning("authenticated fetch of %s failed (%s); falling back to the public raw URL",
                     path, exc)
    return _fetch_public_raw(path)


def fetch_github_file(path: str) -> str | None:
    """results/* → GitHub-first (30s cache) then local; else local-first then GitHub."""
    if path.startswith("results/"):
        now = time.time()
        hit = _results_cache.get(path)
        if hit and now - hit[0] < _RESULTS_CACHE_TTL:
            return hit[1]
        remote = _fetch_remote(path)
        if remote is not None:
            _results_cache[path] = (now, remote)
            return remote
        return _read_local(path)  # GitHub unreachable — stale local beats a 500
    return _read_local(path) or _fetch_remote(path)


def fetch_github_json(path: str) -> dict | None:
    """Fetch and parse a JSON file."""
    text = fetch_github_file(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def fetch_github_csv(path: str):
    """Fetch a CSV as a DataFrame. Ordering (GitHub-first for results/, else
    local-first) is delegated to fetch_github_file so CSV + JSON stay consistent."""
    import pandas as pd
    text = fetch_github_file(path)
    if text is None:
        return None
    try:
        return pd.read_csv(io.StringIO(text))
    except Exception:
        return None


def fetch_github_jsonl(path: str) -> list[dict] | None:
    """Fetch a newline-delimited JSON file as a list of dicts.

    Same ordering rules as fetch_github_json/csv (GitHub-first for results/), so the append-only
    card archive is read through exactly the same path as every other cron-published artifact.
    A malformed line is skipped rather than failing the whole read — a partial archive is more
    useful than none, and the caller degrades to the current envelope anyway.
    """
    text = fetch_github_file(path)
    if text is None:
        return None
    rows: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows
