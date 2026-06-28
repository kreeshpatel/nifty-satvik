# NiftyQuant — canonical index

**This is a pointer index only.** The single source of truth for the live strategy reference is below. Do not duplicate content here.

---

## Strategy Reference

| Document | Scope |
|---|---|
| **[`long_horizon/STRATEGY_FULL.md`](../long_horizon/STRATEGY_FULL.md)** | Complete reference: thesis, universe definition, signal mechanics, exit logic, sizing model, costs, robustness tests, caveats, performance metrics (anchor **baseline_v0**: 26.1% gross / 23.1% after-tax CAGR, 1.02 / 0.83 Sharpe, −41.9% / −45.6% DD on the 682-name solvency-corrected universe; the old 30.3% / 1.15 is superseded optimistic-exit provenance). |
| **[`long_horizon/STRATEGY.md`](../long_horizon/STRATEGY.md)** | Terse spec: TL;DR, metrics table, the 5-step universe build, why it works, what was KILLED (no regime gate, no dual-momentum, no sector overlays), audit summary. |
| **[`models/long_horizon/config.json`](../models/long_horizon/config.json)** | Frozen machine-readable parameters: stop_atr_mult 3.67, target_pct 22.52, trailing stops, hold caps (min 10 / max 63 days), risk per trade 3%, position caps, expected win rate 63%, R:R 1.94. Also documents live_overlays (vol-target, shipped 2026-06-26) and derivation provenance. |

---

## Program Documentation

| Directory | Purpose |
|---|---|
| **[`long_horizon/`](../long_horizon/)** | The strategy package — isolated, data-first, rule-based (no ML). Includes charter, research brain, audit ledger. |
| **[`long_horizon/audit/`](../long_horizon/audit/)** | Phase-1 audit (completed 2026-06-25): wiring report, issues found + fixes applied, PHASE1_FIXES.md ledger. Golden master byte-identical; 1814 tests pass. |
| **[`long_horizon/results/`](../long_horizon/results/)** | Research outputs — backtest panels, equity curves, walk-forward folds, pre-registration verdicts. |
| **[`docs/decisions/`](decisions/)** | Ad-hoc decision logs and rationales (decisions/phase1_wiring.md, etc.). |
| **[`diagnostics/research/`](../diagnostics/research/)** | Pre-registration infrastructure: preregistry/ (frozen trial specs), HOLDOUT.md (forward wall), n_trials.json (cumulative count). |

---

## Live Deployment

| Component | Path | Trigger |
|---|---|---|
| **Live scanner** | [`src/runners/long_horizon_cron.py`](../src/runners/long_horizon_cron.py) | GitHub Actions (`.github/workflows/cron-scanner.yml`) — weekdays 4:15 PM IST (10:45 UTC) |
| **Signal output** | `results/signals_today.json` + `signals_history.json` | Auto-committed by the cron; JSON schema in [`results/README.md`](../results/README.md) |
| **Paper portfolio** | `results/portfolio_history.csv` + `paper_portfolio.json` | Tracked daily; equity curve for gate decisions |
| **Cron logs** | GitHub Actions run logs in `.github/workflows/` | Inspect via GitHub UI or via local git history |

**Render was decommissioned 2026-06-25.** The live path is GitHub Actions only.

---

## Configuration & Parameter Changes

| If you want to... | Go to |
|---|---|
| Modify frozen strategy params (stop, target, hold, sizing) | [`models/long_horizon/config.json`](../models/long_horizon/config.json) — requires rebuild + backtest gate before deploy |
| Add/remove live overlays (vol-target, regime, etc.) | `live_overlays` block in [`models/long_horizon/config.json`](../models/long_horizon/config.json) — no backtest re-required, live-only |
| Understand the frozen-param derivation | [`long_horizon/results/`](../long_horizon/results/) (pre-2017 train slice, re-confirmed walk-forward per fold) + [`long_horizon/STRATEGY_FULL.md`](../long_horizon/STRATEGY_FULL.md) §7–9 |
| Pin live to an archived model variant | Render env vars (decommissioned) or GitHub Actions secrets (when multi-strategy live) |

---

## Common Workflows

### Audit / Verify Correctness

1. Read [`long_horizon/audit/PHASE1_FIXES.md`](../long_horizon/audit/PHASE1_FIXES.md) for the latest known issues + resolutions.
2. Run the golden-master test: `pytest tests/integration/test_long_horizon_golden_master.py`
3. Check the live cron logs in GitHub Actions (`.github/workflows/cron-scanner.yml` run history).

### Backtest Changes to the Strategy

1. Clone the frozen config: `python -m long_horizon.backtest --load-frozen-cfg`
2. Modify params in `models/long_horizon/config.json` (or pass via `--cfg-override`)
3. Run walk-forward: `python -m long_horizon.backtest.run_walk_forward --n-folds=9`
4. Check the verdict: walk-forward Sharpe + CAGR vs baseline + per-fold pass rate (≥60% required)
5. If clearing the gate, file a pre-registration in `diagnostics/research/preregistry/` before merge

### Add a New Live Overlay (e.g., Regime Filter, Vol Target)

1. Pre-register the experiment: create `diagnostics/research/preregistry/00XY-<name>.md` with hypothesis + gate
2. Backtest via pre-reg 0068 template (vol-target + sizing overlays, existing example)
3. If PROMOTE-CANDIDATE: add to `live_overlays` in `models/long_horizon/config.json` + ship

### Investigate Live Signal Quality

1. Check `results/signals_today.json` for the latest entry signals
2. Check `results/signals_history.json` for fills, exits, reasons (HIT_TARGET / HIT_STOP / EXPIRED / OVERWRITTEN)
3. Audit against the live cron log + the OHLCV cache in `data/`

---

## Key Files (Quick Reference)

| File | What it holds |
|---|---|
| [`long_horizon/charter.md`](../long_horizon/charter.md) | Program governance: why this exists, methodology, isolation invariants, reuse map |
| [`long_horizon/brain.md`](../long_horizon/brain.md) | Living research state: mission, operating principles, learnings, lever experiments (updating in real time) |
| [`long_horizon/research/DOSSIER.md`](../long_horizon/research/DOSSIER.md) | Measurement results (IC decay, per-factor performance, known findings F0–F8+) — root-cause readouts for each direction tested |
| [`long_horizon/results/README.md`](../long_horizon/results/README.md) | Schema + interpretation for the backtest output files |
| `.github/workflows/cron-scanner.yml` | The live trigger: schedule, env vars, secrets, rollback path |

---

## Pre-Promotion Checklist (Before Any Deployment)

Use this if you're testing a variant strategy or overlay:

- [ ] Pre-registration filed in `diagnostics/research/preregistry/` with hypothesis, gate, mechanism
- [ ] Walk-forward backtest passes: ≥60% of folds clear the Sharpe/Calmar/CI gate
- [ ] Bootstrap CI on ΔSharpe excludes zero (or mechanism-justified exception documented)
- [ ] No sub-period blow-up (2022/2025 lean years stress-tested)
- [ ] Turnover increase ≤30% (capacity check)
- [ ] Mechanism explainable in one sentence
- [ ] Golden master byte-identical after integration
- [ ] Live overlay: shadow tested ≥2 weeks before paper toggle (if applicable)

---

## Operational State

**Strategy:** Long-horizon 3-month trend-momentum. Rule-based (no ML). FROZEN params as of 2026-06-25.

**Live status:** Running paper trading via GitHub Actions (weekdays 4:15 PM IST). Paper gate: ≥30 trades over ~2 months review before any real capital.

**Headline metrics** — anchor: **baseline_v0** (`research/baseline_v0.json`; frozen-cfg arm,
exit-parity-unified engine, corrected-682 universe / 397 solvent names, 2017–2026):
- CAGR: **26.1% gross / 23.1% after-tax (STCG 20%)**
- Sharpe: **1.02 gross / 0.83 after-tax**
- Max drawdown: **−41.9% gross / −45.6% after-tax**
- Calmar: **0.62 gross / 0.51 after-tax**
- Trades/year: ~152 (1445 total) · Win rate: 59.7%

> The previously-quoted 30.3% / 1.15 / −40.1% was the **old optimistic-exit measurement**
> (targets filled at `max(close, target)`). The exit-parity unification (2026-06-26) costs ~4 pp
> CAGR; `baseline_v0` is that re-confirmation (superseded 2026-06-27 — see
> `docs/decisions/0005-headline-correction-baseline-v0.md`). Never anchor on the 34.67% re-derived variant.

**Walk-forward (2019+):** the previously-cited ~32% CAGR / 1.31 Sharpe was measured under the same
optimistic-exit fill and is **pending re-confirmation** on the exit-parity engine — historical
provenance, not a current figure.

**Caveats:**
- Never traded live rupees. Research backtest only.
- -40% drawdown is steep; requires high risk tolerance.
- High-variance, regime-dependent (fat tail, median Sharpe 1.23 vs 5th pct 0.58).
- Concentration in momentum-friendly years.

**Compliance language:** All outputs are model-generated decision-support signals, never advice or guarantees.

---

## Related Documentation (Other Systems)

| System | Where |
|---|---|
| v1 LightGBM 14-day model (RETIRED 2026-06-25) | [`models/`](../models/) (archived; not on live path) |
| General quant safety rules | [`CLAUDE.md`](../CLAUDE.md) (§ Quant Safety Rules) |
| Backend API + frontend | [`README.md`](../README.md) (Architecture & Data Flow section) |
| Testing & CI | [`Makefile`](../Makefile) + `.github/workflows/ci.yml` |

---

**Last updated:** 2026-06-27  
**Strategy status:** Phase 1 audit complete; golden master shipped.  
**Next:** Paper-trading review gate; real-capital decision pending owner discretion.
