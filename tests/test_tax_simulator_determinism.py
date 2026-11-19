"""The India after-tax simulator (pipelines/diagnostics/explore_india_tax_practices.py) must not depend on
PYTHONHASHSEED.

Until 2026-11-19 `Taxpayer.retarget` iterated a set of instrument names, and that order fed the lot-insertion order
the harvest walked: the #212 S1->S2 step read +13,460 under seeds 0/2/3 and +11,564 under seed 1 (PR #214,
Correction 3). This test runs simulate() for the static 60/40 book - S1 (no harvest), S2 (harvest), the company S4 -
in four subprocesses with PYTHONHASHSEED 0, 1, 2, 3 and asserts byte-identical output.

The price context is built from the committed TRI file only (no local caches), so it runs in CI.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHILD = r"""
import sys
from pathlib import Path
ROOT = Path(sys.argv[1])
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"),
                str(ROOT / "pipelines" / "diagnostics"), str(ROOT / "pipelines" / "lifecycle")]
import pandas as pd
import explore_india_tax_practices as T
cfg = T.load_cfg()
tri = pd.read_csv(ROOT / "diagnostics/research/benchmarks/tri/nifty_midcap150_momentum_50_tri.csv", parse_dates=["date"])
idx = pd.DatetimeIndex(tri["date"])
idx = idx[(idx >= "2019-03-05") & (idx <= "2024-06-28")]
flat = pd.Series(100.0, index=idx)
ctx = {"idx": idx, "expo": pd.Series(1.0, index=idx), "px_m": flat, "px_s": flat, "gains": {},
       "px_index": {id(cfg): T.index_price(idx, cfg)}, "px_liq": {}, "px_arb": {}}
ctx["px_liq"][id(cfg)], ctx["px_arb"][id(cfg)] = T.cash_prices(idx, cfg)
out = []
for kw in (dict(cash_leg=T.ARB), dict(cash_leg=T.ARB, harvest=True, harvest_day=T.HARVEST_DAY),
           dict(cash_leg=T.LIQ, harvest=True, harvest_day=T.HARVEST_DAY),
           dict(kind="company", cash_leg=T.ARB, harvest=True, harvest_day=T.HARVEST_DAY)):
    r = T.simulate("s60", cfg, ctx, slab=0.30, **kw)
    out.append(repr((r["final"], r["tax"], r["costs"], r["fund_exp"], float(r["mtm"].sum()))))
print("\n".join(out))
"""


def _run(seed: int) -> str:
    env = {**os.environ, "PYTHONHASHSEED": str(seed), "OMP_NUM_THREADS": "1"}
    p = subprocess.run([sys.executable, "-c", CHILD, str(ROOT)], capture_output=True, text=True, env=env, timeout=600)
    assert p.returncode == 0, p.stderr[-2000:]
    return p.stdout


def test_simulate_is_byte_identical_across_hash_seeds():
    outs = {s: _run(s) for s in (0, 1, 2, 3)}
    first = outs[0]
    assert first.strip(), "child produced no output"
    for s, o in outs.items():
        assert o == first, f"PYTHONHASHSEED={s} differs from seed 0:\n{o}\nvs\n{first}"
