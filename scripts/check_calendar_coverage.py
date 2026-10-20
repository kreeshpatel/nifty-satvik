"""Go red before the NSE holiday calendar runs out, not after.

config.NSE_HOLIDAYS covers through NSE_HOLIDAYS_COVERED_THROUGH (2026-12-31 as of 2026-10-20). NSE publishes
one year at a time, historically in December. Past the bound the weekly engine cannot detect a
holiday-shortened week (scripts/run_bhanushali_weekly_rank.py::week_closed_at warns), so this check turns
the post-commit scan step red from WARN_DAYS before expiry: early enough to load the next year, and
read-only, so it can never cost the week it runs in.

    python scripts/check_calendar_coverage.py [--today YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

WARN_DAYS = 30


def days_left(today: date, through: str) -> int:
    return (date.fromisoformat(through) - today).days


def main(argv: list[str] | None = None) -> int:
    from config import NSE_HOLIDAYS_COVERED_THROUGH as THROUGH
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--today", default=None)
    a = ap.parse_args(argv)
    today = date.fromisoformat(a.today) if a.today else date.today()
    left = days_left(today, THROUGH)
    if left <= WARN_DAYS:
        print(f"::error::NSE holiday calendar ends {THROUGH} ({left} days). Run "
              f"`python scripts/build_nse_holidays.py --emit` once the next year is published and update "
              f"config.py; until then holiday-shortened weeks cannot be detected.")
        return 1
    print(f"calendar coverage: through {THROUGH}, {left} days left (red from {WARN_DAYS} days)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
