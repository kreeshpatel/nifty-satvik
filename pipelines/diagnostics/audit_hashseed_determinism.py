"""MEASUREMENT: does any #211 / #212 `explore_*` script's output depend on PYTHONHASHSEED?

Each script is run twice, under PYTHONHASHSEED=0 and =1, OMP_NUM_THREADS=1, and its output files are compared byte for
byte. The committed outputs are backed up first and restored afterwards, so the working tree is unchanged.
Scope limit: inputs cached under .cache/ (navs.pkl, family pickles) are NOT regenerated - this checks each script's own
computation downstream of those caches. Engine-level determinism is the golden master's job (tests/test_stage2_golden.py).
explore_param_sensitivity is checked on ONE nudge family (momentum buffer_mult); a full re-run takes hours.

    python pipelines/diagnostics/audit_hashseed_determinism.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EX = ROOT / "diagnostics" / "research" / "explore"
D = ROOT / "pipelines" / "diagnostics"
WORK = ROOT / ".cache" / "hashseed_audit"

JOBS = [
    ("explore_blend_drawdown_sizing", [str(D / "explore_blend_drawdown_sizing.py")], [EX / "2026-11-18_blend_drawdown_sizing.json"]),
    ("explore_risk_matched_benchmark", [str(D / "explore_risk_matched_benchmark.py")], [EX / "2026-11-18_risk_matched_benchmark.json"]),
    ("explore_after_tax_comparison", [str(D / "explore_after_tax_comparison.py")], [EX / "2026-11-18_after_tax_comparison.json"]),
    ("explore_walkforward_status", [str(D / "explore_walkforward_status.py")], [EX / "2026-11-18_walkforward_status.json"]),
    ("explore_stops_are_requests", [str(D / "explore_stops_are_requests.py")], [EX / "2026-11-18_stops_are_requests.json"]),
    ("explore_circuit_lock_real_bands", [str(D / "explore_circuit_lock_real_bands.py")], [EX / "2026-11-18_circuit_lock_real_bands.json"]),
    ("explore_param_sensitivity (momentum buffer_mult)", [str(D / "explore_param_sensitivity.py"), "momentum", "buffer_mult"],
     sorted((EX / "sensitivity").glob("momentum__buffer_mult__*.json"))),
    ("explore_india_tax_practices", [str(D / "explore_india_tax_practices.py")], [EX / "2026-11-18_india_tax_practices.json"]),
]


def _strip(o):
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items() if k != "seconds"}
    if isinstance(o, list):
        return [_strip(v) for v in o]
    return o


def run(args, seed) -> tuple[int, float]:
    env = {**os.environ, "PYTHONHASHSEED": str(seed), "OMP_NUM_THREADS": "1"}
    t = time.time()
    p = subprocess.run([sys.executable, *args], cwd=ROOT, env=env, capture_output=True, text=True)
    (WORK / f"log_{Path(args[0]).stem}_{seed}.txt").write_text(p.stdout[-5000:] + "\n---\n" + p.stderr[-5000:], encoding="utf-8")
    return p.returncode, time.time() - t


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[1:])
    res = {}
    for name, args, outs in JOBS:
        if only and not any(o in name for o in only):
            continue
        bak = WORK / "backup"
        bak.mkdir(exist_ok=True)
        for f in outs:
            if f.exists():
                shutil.copy2(f, bak / f.name)
        snaps = {}
        for seed in (0, 1):
            if "param_sensitivity" in name:                     # the script skips values whose file already exists
                for f in outs:
                    f.unlink(missing_ok=True)
            rc, sec = run(args, seed)
            snaps[seed] = {f.name: (f.read_bytes() if f.exists() else None) for f in outs}
            res.setdefault(name, {})[f"seed{seed}"] = {"returncode": rc, "seconds": round(sec)}
        same = all(snaps[0][k] == snaps[1][k] and snaps[0][k] is not None for k in snaps[0])
        res[name]["byte_identical"] = bool(same)
        # Some outputs record their own runtime ("seconds"), which can never match between runs. Compare the content
        # with every "seconds" key removed as well (added 2026-11-19 after the first pass flagged
        # explore_param_sensitivity on that field alone).
        res[name]["content_identical_excluding_runtime"] = bool(all(
            snaps[0][k] is not None and snaps[1][k] is not None
            and _strip(json.loads(snaps[0][k])) == _strip(json.loads(snaps[1][k])) for k in snaps[0]))
        res[name]["files"] = list(snaps[0])
        for f in outs:                                           # restore the committed outputs
            if (bak / f.name).exists():
                shutil.copy2(bak / f.name, f)
        print(name, json.dumps(res[name]), flush=True)
    (WORK / "result.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
