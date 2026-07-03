# nifty-satvik

## Dependency map maintenance

After editing any `nq/**` module or root `config.py`, regenerate the import map and
commit the result:

```
python scripts/gen_depgraph.py
```

This rewrites [docs/DEPENDENCY_MAP.md](docs/DEPENDENCY_MAP.md) (a Mermaid graph of
first-party `nq/` ↔ `config` wiring). The regenerator is stdlib-only and deterministic,
so re-running produces byte-identical output. A committed pre-commit hook in `.githooks/`
does this automatically when `core.hooksPath` is set — enable once per clone with:

```
git config core.hooksPath .githooks
```

## Output style — ALWAYS use the `caveman` skill

**Always use the [`caveman`](.claude/skills/caveman/SKILL.md) skill: terse, token-efficient
responses** — minimal words, full technical accuracy ("why use many token when few do trick").
Applies to conversational / working output.

Keep FULL prose for artifacts that must stay readable, NOT caveman-terse: commit messages (the
git log is investor-facing), PR summaries, compliance-safe product copy, and committed docs.

## Research program — read this before ANY research / strategy / overlay task

This section is the board. It exists so a session carries the program's state and discipline
instead of re-deriving it or waiting for the owner to paste context. When a task touches the
strategy, its signal, exits, sizing, universe, or a "new idea," start here.

**The strategy + the pinned anchor.** Long-only cross-sectional trend-momentum on NSE Nifty-500
large+mid (ADV ≥ 5cr, solvent D/E < 1.5). Signal `sma200_slope_63`, top-15 by cross-sectional rank,
10–63d hold. Frozen cfg = `models/long_horizon/config.json` (`config.load_frozen_cfg`). The pinned
baseline of record is **`baseline_v1`** (`research/baseline_v1.json`, dataset pin `dataset-pin-20260701`,
ohlcv sha `f8625a8f…`): gross Sharpe **0.667** / Sortino 0.836 / CAGR 15.46% / MaxDD **−46.26%** /
Calmar 0.33 / after-tax CAGR 12.76% / ann vol 27.1%. It is byte-reproducible from the pinned OHLCV
(`gh release download dataset-pin-20260701`, then the `scripts/` harness).

**The in-sample program is CLOSED (2026-07-02, 91 trials).** Every overlay tested landed inside its
noise band; at a moderate edge (~2× random — finding 0008) on ~34 independent 63-day windows, nothing
clears a Deflated-Sharpe gate, and each new in-sample trial deflates the bar further. **Do not run
trial #92 on the single momentum sleeve** without a genuinely new lever. The only remaining source of
unbiased information is the forward wall (`forward/prereg.md`).

**Registry-first — before proposing ANY overlay / signal / exit / sizing / universe idea:**
1. Search `research/overlay_registry.md` (the O-###/S#/R# ledger), `research/findings/NNNN-*.md`, and
   `diagnostics/research/n_trials.json`. Most ideas are already tested. If the id or a near-identical
   hypothesis is `REJECT`/`KILL`, you may **not** relitigate it without stating which of {new data,
   new feature, new sub-period, new formulation} you bring — cite it in the pre-registration.
2. Consult `skills/methodology-synthesis` (borrowed-method index: ADOPTED / CANDIDATE / REFERENCE /
   REJECTED) and the §11 KILL ledger. Already killed (do not re-propose as-is): regime/dual-momentum
   entry gate (O-001), single-beta residual (O-002), sector selection (O-004), RSI/MACD/reversal
   (O-005), low-vol/quality **signal-blend** (O-006/O-007), alt lookbacks 12-1/6-1 (O-010/11/12),
   meta-labeling (0025), conviction sizing (0073/0020), residual-momentum sole-swap (0077) &
   blend/veto (0078), and the **whole technical/chart zoo at 63d** (0079/O-015: RSI/MACD/Stoch/Williams/
   CCI/Bollinger/MFI/OBV have IC≈0; 52-week-high/SMA-dist/ROC have IC but lose as rankers — IC ≠ portfolio
   Sharpe). Vol-target is PROMOTED & shipped to paper (O-009 / pre-reg 0068). Low-vol as a *sole ranker*
   (O-016) is strong-but-uncertifiable → the multi-sleeve fork, not a cfg change. **0081 confirmed the
   momentum×low-vol ERC combination: Sharpe 0.67→0.94, DD −46→−36 at flat CAGR, ρ=0.54 — but UNDERPOWERED**
   → route the low-vol sleeve to the **forward wall** (`forward/prereg.md` §7 swap), the only certifier. The
   operational robot (`nq/paper/wall_cron.py`, wired into `run_paper_cron.py`) logs the 3-book wall daily.
   **The cross-asset / macro branch is CLOSED (2026-07-02, trials 98→100).** The Step-1 PIT gate (finding 0017,
   `nq/data/macro.py` + `tests/test_macro_pit.py` truncation-tested) rebuilt the macro factors clean and split
   real from artifact: **USD/INR-sensitivity is real & PIT-robust** (beta-IC −0.034→−0.0295), **crude was a
   lookahead artifact** of the un-audited `data/macro_data.pkl` (+0.027→+0.002, dropped), VIX dead. But the
   follow-on trial **0082 (O-019) KILLED USD-sensitivity as a rank-component tilt** (`trend_rank + λ·(1−usd_beta_rank)`,
   λ∈{0.15,0.25}): every arm ΔSharpe ≤ 0, the DD relief fails the continuous-slice 2022-26 gate — **IC ≠ portfolio
   Sharpe, again** (like the 52-week-high, 0079). Do NOT re-propose macro/USD/crude as an entry gate (O-001),
   sizing (0073), a sole ranker, or a rank tilt (O-019). The only unspent macro avenue is a *portfolio-level*
   low-USD-beta sleeve via the O-018 ERC mechanism (forward-wall / owner decision), never a single-sleeve blend.

**Reproduce-before-trust.** A number that informs a decision must be reproducible from the committed
pipeline, never a chat transcript (e.g. the veto-0.1 null → `scripts/diag_veto01_cascade.py`). Two
hard-won rules:
- **Sub-period gates use a CONTINUOUS-SLICE of one full run**, never a fresh-capital re-run from the
  sub-window start. Fresh-capital resets the equity peak and reseasons the boundary → a phantom gate
  (base 2022-26 Sharpe 0.762 / DD −40 vs the correct slice **0.570 / −46.3**) that produced false
  KILLs (it wrongly downgraded 0071). Use `nq.runner.research.evaluate_overlay`, which slices.
- Trust ≥2019 folds / the 63d horizon only; old v1 7–14d kills do not transfer.

**Pre-registration + record discipline (`skills/research-log`).** Write the pre-reg
(`diagnostics/research/preregistry/NNNN-*.md`, Status PRE-REGISTERED) **before** running; increment
`n_trials.json` **before** the run (DSR uses the cumulative count). After: a `research/findings/NNNN-*.md`
(with the required root-cause readout + next-setup) **and** an `overlay_registry.md` row. **UNDERPOWERED /
KILL is a first-class outcome — never retune toward a pass; the params are fixed in the pre-reg.**

**Leakage discipline (`skills/leakage-audit`).** Fundamentals join PIT via
`nq.data.fundamentals.value_quality_series` (`merge_asof` backward, `allow_exact_matches=False`,
availability = period_end + 90d). Features are trailing-only. A result WORSE than base is not a leak
(leaks inflate); a too-good one is guilty until cleared.

**Engine invariant.** Any overlay must be cfg-gated so the golden master (`tests/test_stage2_golden.py`)
stays byte-identical when off. After editing `nq/**` or `config.py`: regen the depgraph (above) **and**
run the full suite before pushing.

**Forward wall (`forward/prereg.md`) — the only certifier.** Three books: `base` (PAPER until it clears
the `portfolio-simulation` paper gate — ≥30 closed trades / ~2mo — then small real capital via a dated
amendment), `veto-0.1` + `drift-degross` (WATCHED, logged not traded). The §3 hash-chained 3-book log is
built and tested (`nq/paper/forward_wall.py` + `forward_wall_job.py`). Decisions happen **only** at
quarterly reviews (first trading day Jan/Apr/Jul/Oct); between them, log and **leave it alone** — no
peeking, no config/size changes (except the mechanical −50% halt). The 12-month review resolves the
multi-sleeve fork on forward evidence. Thresholds may be tightened, never retroactively relaxed.

**The Bhanushali external-strategy arc is CLOSED (2026-07-03, findings 0022–0024 + prereg v1.5).** The full
taught system, tested three ways (letter-faithful, method-faithful, practitioner-process), is a low-drawdown
discipline, not a return engine (net ~1.4%/yr vs base 15.5%). Owner decision: **Path C primary** — three new
watched shadow features on the base (`hvc_confirm`, `dip20_depth` — a NEW lever, Jaccard 0.04 vs MA-touch,
60d CI excludes 0 — and `entry_confirm`, a RISK feature; family now 5 with rev_yoy/usd_beta); **Path B** —
the practitioner-B swing sleeve is a registered PROPOSAL for the 2026-10-01 review (promote/kill
pre-committed; spec freeze gated on the delisted backfill); Path A declined. RSI-oversold is triple-killed
(0020/0022/0024 — the indicator *subtracts* from the dip situation); do not relitigate. Regime pause lives
ONLY inside the B-sleeve spec (O-001 stays killed for the base).
**⚠ DATA DEBT — backfill LANDED 2026-07-03, base re-run PENDING.** The pinned `data/ohlcv.pkl` (f8625a8f)
is survivor-only (103/813 PIT members missing). The backfill recovered **103/103 (~100% member-day
coverage)** into `data/ohlcv_backfill.pkl` + `data/delisted_alias_map.json` (pin untouched; see
`diagnostics/research/backfill_readiness.md` + harvest/finalize scripts). Finding 0025 measured the bias:
**it scales with holding period** (−0.04 Sharpe tight-stop vs −0.18 wide-stop swing configs) → the 63d-hold
**baseline_v1 0.667 is exposed in the same direction; its corrected re-run is unblocked** but re-anchors the
pin → owner/governance decision (quarterly-review class). 0025 also settled Path-1: 4×ATR geometry lifts
the swing book to net +0.40 Sharpe / −12% DD on the corrected universe — **0.003 below its pre-committed
bar; recorded, not relitigated; Oct-1 review decides the sleeve.**

**When handed an external research doc, be adversarial.** Cross-reference every recommendation against
the registry (an outside chat can't see it) — most "new" ideas are already tested here. Correct the
doc's premises with our data (e.g. "most residual benefit comes from market residualization" is
contradicted by O-002). Credit only genuinely-new, non-relitigated ideas, and hold them to the same bar.
