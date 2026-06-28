# MISSION BRIEFING — nifty-satvik: continue the clean long-horizon rebuild

> Paste this as the first message of a new Claude Code session **rooted in
> `C:/nifty-satvik`**. It orients the session; `BUILD_SPEC.md` is the authoritative
> spec and `skills/` is the binding methodology.

## 0 — Working context (verify FIRST)
- Work in **`C:/nifty-satvik`** — a fresh, clean, **long-horizon-ONLY** repo (GitHub
  `kreeshpatel/nifty-satvik`, private, branch `main`). Windows + Git-Bash; shell cwd
  resets between calls → use absolute paths.
- **Do NOT touch** `C:/project` (old `niftyquant` monorepo — ARCHIVE only) or
  `C:/niftyquant-lh` (the superseded intermediate transplant / carry source).
- **STANDING DIRECTIVE — use the skills.** Read the relevant `skills/*/SKILL.md`
  (also registered at `.claude/skills/`; `python scripts/register_skills.py` to
  re-register) BEFORE any research action: `edge-research-pipeline`, `backtest-rigor`,
  `overlay-testing`, `methodology-synthesis`, `leakage-audit`, `portfolio-simulation`.
- **Read `BUILD_SPEC.md`** — the authoritative blueprint (strategy, carry manifest,
  architecture, staged plan, CI). This briefing is orientation; BUILD_SPEC is the spec.
- No `CLAUDE.md` yet — writing a concise one is a good early task.

## 1 — Why this repo exists
The monorepo wove the retired **v1** 14-day model + ensemble + pillar stack into the
validation, sizing, and import graph so tightly that subtracting it cleanly was harder
and riskier than a clean rebuild. There are **NO users** (pre-launch) → no live-deploy
risk. So: **rebuild the code clean; transplant only what can't be regenerated.** The
old repo stays as the archive/provenance.

## 2 — Base theory / the strategy
Long-horizon (3-month) cross-sectional trend-momentum on Nifty-500:
- **Universe:** PIT index-membership-masked Nifty-500 → large+mid (trailing 20d-median
  rupee ADV ≥ ₹5cr) → solvent (`0 ≤ D/E < 1.5`).
- **Signal:** rank by **`sma200_slope_63`** (200-day SMA slope over 63 sessions);
  higher = better. Fill up to **15** slots with top-ranked **non-held** names.
- **Sizing:** risk budget — `risk_per_trade` 3% of equity ÷ per-share risk, capped at
  15% equity & 5% ADV.
- **Exits** (shared live/backtest, decided on the close): ATR stop **3.67×ATR** ·
  target **+22.52%** · trailing activate **+4.0%** / trail **4.27%** below close-peak ·
  **min-hold 10** · **63-day** hard cap (TRADING-day aging).
- **Costs:** brokerage 0.03%/leg + STT 0.10% **both legs** (delivery) + tiered slippage
  + impact >0.5% ADV.
- **Frozen params:** `models/long_horizon/config.json` (derived once pre-2017; never
  re-derived at scan). **Live overlay** (paper sizing only, NOT in frozen cfg/golden):
  0068 vol-target 0.15 / 42 / 0.40.

## 3 — Anchor + end goal
- **Anchor = baseline_v0:** CAGR **26.11%** / Sharpe **1.02** / maxDD −41.9% / Calmar
  0.62 (after-tax 23.13% / 0.83), `research/baseline_v0.json`. **NEVER anchor on the
  superseded 30.26 / 34.67.** *Not live-validated.*
- **End goal:** a clean, legible, defensible LH research+strategy engine that (a)
  reproduces the validated strategy exactly (golden master), (b) runs pre-registered,
  DSR-gated experiments to improve it honestly, and eventually (c) is ready for paper →
  live once the forward wall + discipline justify it.
- **Research path:** the live lever now is the **forward wall** (accumulate live OOS) +
  a few orthogonal candidates — NOT alpha-mining (the model is near its ceiling per the
  §11 KILL log). Entry signal `sma200_slope_63` is **CONFIRMED** (C4 horse-race retired
  the alternatives). The edge is partly **exit-structure-driven** (0071: the ATR stop
  ADDS risk-adj return; the +22.5% target + 4.27% trailing SUBTRACT in-sample — a
  Stage-D candidate, EVIDENCE-ONLY, owner sign-off to promote).

## 4 — Build plan (staged; STOP for owner review between stages)
- **Stage 0 — Foundation: DONE.** Repo + BUILD_SPEC + the 6 carried irreplaceables +
  `nq/` scaffold + lean CI + Stage-0 smoke (5 pass). Commits through `b8cc4ff`.
- **Stage 1 — Data (NEXT).** `nq/data/`: OHLCV acquisition (yfinance + split-heal), the
  PIT membership mask (reads carried CSVs), features (`sma200_slope_63`, `atr_pct`,
  20d-median ADV, the D/E join from the carried Screener pkl), demerger quarantine.
  **Gate:** on a small known universe, `sma200_slope_63` + the eligibility mask
  reproduce expected values; trailing-only (NO lookahead). PORT the LH-clean
  computation so Stage 2's golden can match.
- **Stage 2 — Engine.** `nq/engine/{panel,exits,portfolio}.py`. **Gate (keystone):
  reproduce the carried golden fixture `tests/fixtures/lh_golden_panel.csv`
  byte-for-byte** → proves the rebuilt engine ≡ the validated strategy.
- **Stage 3 — Strategy + runner.** `nq/strategy/long_horizon.py` + `nq/runner/scan.py`.
  **Gate:** frozen-cfg backtest reproduces baseline_v0 ≤1pp on the canonical universe
  (cloud); live scan writes a coherent `signals_today.json`.
- **Stage 4 — Validation + cloud.** `nq/validation/` (cpcv, bootstrap, dsr, metrics) —
  clean, decoupled, no v1 — and the cloud research workflow (`cpcv-research.yml`, port
  from the old repo). **Canonical numbers come ONLY from the cloud** (the local OHLCV
  cache is a degenerate ~20-survivor subset → ~15% CAGR → inadmissible). **Gate:**
  re-derives a known §11 KILL as killed; DSR reads the carried `n_trials.json` (=79).
- **Stage 5 — Tests + CI green.** Port/rewrite the LH tests; CI green on the real runner.

## 5 — The 6 irreplaceables (ALREADY carried — NEVER regenerate naively)
Data corrections (PIT membership / demerger catalog / Screener PIT D/E — `data/`),
empirical history (`research/baseline_v0.json`, `research/overlay_registry.md`,
`diagnostics/research/n_trials.json`=79, the preregistry), the golden fixture, frozen
`config.json`, `skills/`, the STRATEGY/program docs. Re-deriving the data naively
re-introduces survivorship-inflation (CAGR +8–18pp) and the demerger-as-split bug that
fabricates a top-15 BUY on a price series that never existed.

## 6 — Governance (non-negotiable; from the skills)
- Pre-register every trial (`diagnostics/research/preregistry/`) + bump
  `n_trials.json` (=79) **before** running.
- Judge on **paired same-run, same-cache, ≥2019-fold deltas** — NEVER absolute CAGR
  (swings ±~4pp on cache vintage).
- **Promotion bar (ALL):** post-tax post-cost ΔSharpe ≥ +0.10 · ΔCalmar ≥ +0.05 ·
  2022–26 ΔCAGR > 0 · ≥2019 fold-pass ≥ 60% · block-bootstrap CI-low(ΔSharpe) > 0
  (block=63) · turnover Δ ≤ +30% · one-sentence mechanism · DSR at cumulative n_trials.
- **Golden master** = engine-drift guard AND rebuild-equivalence proof.
- **Research produces EVIDENCE only** — never auto-promote a frozen-cfg change; a
  heavy-path PROMOTE needs walk-forward + golden regen + **OWNER SIGN-OFF**.
- **Verify-your-own-code:** run flaw-hunter + backtest-validator on any
  headline-producing code before trusting its numbers.

## 7 — Hard-won learnings (easy to miss)
- **The CI segfault is TOOLCHAIN, not code.** `shap`/`statsmodels`/`lightgbm` +
  OpenMP/BLAS native threading crash the Ubuntu runner at import time — independent of
  coverage (it crashed with `--cov` fully removed). Keep `nq/` **LEAN** (no
  shap/statsmodels/heavy-lightgbm), CI pinned **`OMP_NUM_THREADS=1`**, and **NO `--cov`**
  in the gate. (Baked into the new CI by construction.)
- **Tiered subagents:** mix opus (hard+verify) / sonnet (moderate) / haiku (trivial) by
  task difficulty to save tokens.
- **Commit style:** NO `Co-Authored-By` trailers (git log is investor-facing).
- **Sector is dead weight:** the model is sector-blind and CAGR weakness in
  2018/2019/2025 is single-name + per-stock-regime risk, NOT sector rotation (sector
  IC ≈ 0, repeatedly KILLed). Don't relitigate sector overlays without IC > 0.05 on a
  2022+ sub-period.
- **Vol-carry (parked):** options IV>realized as a 2nd structurally-orthogonal return
  stream — the long-term composition play, gated on the F&O data foundation.

## 8 — Immediate next action
Confirm you are rooted in `C:/nifty-satvik` on `main`; read `BUILD_SPEC.md` + the §0
skills; then **start Stage 1 (the data pipeline)** per §4 — port the LH-clean
OHLCV / membership / feature computation into `nq/data/`, verify `sma200_slope_63` +
eligibility with NO lookahead, small focused commits, and **STOP for review at the
Stage-1 gate.**
