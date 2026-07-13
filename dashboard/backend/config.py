"""
Backend config — imports everything from root config.py if available,
falls back to self-contained constants for standalone deployment.
"""

import os
import sys
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

# Try to import the full root config (has NIFTY_500, ensure_dirs, etc.)
_root_config_loaded = False
try:
    _root = str(Path(PROJECT_ROOT))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    # Force import from root, not self.
    # NB: `import importlib` alone does NOT bind the `importlib.util` submodule —
    # it must be imported explicitly, otherwise the next line raises
    # AttributeError, the bare `except` below swallows it, and the backend
    # silently falls back to the minimal standalone config (missing trading
    # params like BROKERAGE_PCT/STT_PCT). Import the submodule explicitly.
    import importlib.util
    _spec = importlib.util.spec_from_file_location("_root_config", os.path.join(PROJECT_ROOT, "config.py"))
    if _spec and _spec.loader:
        _root_cfg = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_root_cfg)
        # Pull all public names into this module
        for _name in dir(_root_cfg):
            if not _name.startswith("_"):
                globals()[_name] = getattr(_root_cfg, _name)
        _root_config_loaded = True
except Exception:
    pass

# Backfill every name the routers import from `config` that the root config did
# NOT provide. The nifty-satvik mono-repo root config.py is lean: it defines
# NIFTY_500 / NSE_HOLIDAYS / BROKERAGE_PCT / STT_PCT / SECTOR_MAP / get_sector /
# RESULTS_DIR / MODELS_DIR / DATA_DIR / ensure_dirs, but NOT the dashboard-only
# constants (INITIAL_CAPITAL, MAX_POSITIONS, ...). The old all-or-nothing fallback
# (only when the root import FAILED) therefore left INITIAL_CAPITAL undefined on a
# SUCCESSFUL lean import, crashing `from config import INITIAL_CAPITAL` at boot.
# setdefault keeps whatever root DID define and fills only the gaps — robust for
# both the mono-repo (partial) and a fully standalone (no root config) deploy.
from pathlib import Path as _Path

_g = globals()
for _k, _v in {
    "RESULTS_DIR": _Path(os.getenv("RESULTS_DIR", os.path.join(PROJECT_ROOT, "results"))),
    "DATA_DIR": _Path(os.getenv("DATA_DIR", os.path.join(PROJECT_ROOT, "data"))),
    "MODELS_DIR": _Path(os.getenv("MODELS_DIR", os.path.join(PROJECT_ROOT, "models"))),
    "LOGS_DIR": _Path(os.getenv("LOGS_DIR", os.path.join(PROJECT_ROOT, "logs"))),
    "INITIAL_CAPITAL": float(os.getenv("INITIAL_CAPITAL", "1000000")),
    "MAX_POSITIONS": int(os.getenv("MAX_POSITIONS", "15")),        # LH strategy caps at 15
    "BUY_THRESHOLD": float(os.getenv("BUY_THRESHOLD", "0.52")),
    "HOLD_DAYS": int(os.getenv("HOLD_DAYS", "63")),               # LH is a 63-day hold
    "BROKERAGE_PCT": float(os.getenv("BROKERAGE_PCT", "0.0003")),  # 0.03% per leg
    "STT_PCT": float(os.getenv("STT_PCT", "0.001")),              # 0.1% delivery, per leg
    "LOOKBACK_YEARS": 11,
    "NIFTY_500": [],
    "NSE_HOLIDAYS": set(),
    "SECTOR_MAP": {},
}.items():
    _g.setdefault(_k, _v)

_g.setdefault("ALL_DIRS", [_g["DATA_DIR"], _g["LOGS_DIR"], _g["MODELS_DIR"], _g["RESULTS_DIR"]])

if "get_sector" not in _g:
    def get_sector(ticker: str) -> str:
        return SECTOR_MAP.get(ticker, "Others")

if "ensure_dirs" not in _g:
    def ensure_dirs():
        for d in ALL_DIRS:
            _Path(d).mkdir(parents=True, exist_ok=True)


# ── Signals-page position sizer ───────────────────────
# Per-trade risk as a FRACTION of the user's capital, by tier. 'high' 2% would be
# the backtest-of-record's risk/trade; the owner set high=3% ('aggressive') which
# is ABOVE the validated 2% (more drawdown, not backtest-proven — surfaced in the
# UI). POSITION_CAP_PCT caps any single position so a tight stop can't concentrate
# the book (at a 20% cap, medium 2% and high 3% coincide for stops <=10%). Single
# source of truth — served to the frontend via GET /api/sizer/config.
RISK_TIERS = {"medium": 0.02, "high": 0.03}
POSITION_CAP_PCT = 0.20
