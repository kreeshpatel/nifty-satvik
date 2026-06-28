# NiftyQuant Long-Horizon — Skills Library

The reusable procedures for building, testing, and operating the long-horizon strategy.
Each skill is a `SKILL.md` with frontmatter (`name`, `description` with trigger words).

> **ALWAYS USE THESE WHILE WORKING.** Before any data change, backtest, overlay test,
> conviction-feature, exit/sizing rule, or regime/execution decision, consult the relevant
> skill below — they encode the discipline that keeps this a trustworthy paid engine. When
> in doubt about *which* method applies, start at [`methodology-synthesis`](methodology-synthesis/SKILL.md).

## Working procedures (use these)

| Skill | Use when… | Borrowed from |
|---|---|---|
| [skills-first](skills-first/SKILL.md) | **at the START of every task** — check what skills/agents already exist before any command or plan (don't reinvent) | project (owner meta-rule) |
| [repo-map](repo-map/SKILL.md) | **before changing any value/formula/file** — find its single source, blast radius, and live-vs-backtest parity points | project (Phase-1 audit) |
| [methodology-synthesis](methodology-synthesis/SKILL.md) | you need to know *which* borrowed method applies / what we adopted vs rejected | all 6 sources (master index) |
| [backtest-rigor](backtest-rigor/SKILL.md) | before trusting **any** harness/backtest number — the red-flag checklist | claude-trading-skills `backtest-expert` (MIT) |
| [data-quality](data-quality/SKILL.md) | any OHLCV / PIT / corporate-action change (split vs demerger — the VEDL lesson) | `data-quality-checker` (MIT) + finance_skills `corporate-actions` (MIT) |
| [leakage-audit](leakage-audit/SKILL.md) | before trusting a backtest — lookahead / train-serve skew / survivorship / purge-embargo integrity gate | project (flaw-hunter + PIT) |
| [overlay-testing](overlay-testing/SKILL.md) | testing any candidate overlay through the Phase-4 harness vs baseline_v0 | project (Phase 4) |
| [edge-research-pipeline](edge-research-pipeline/SKILL.md) | generating + structuring a new edge/overlay idea (hypothesis→design→test→review→log) | claude-trading-skills `edge-*` pipeline (MIT) |
| [sell-replace-logic](sell-replace-logic/SKILL.md) | adding/evaluating a sell-beyond-mechanical or capital-rotation rule (S1–S7 / R1–R4) | project (owner-authored) |
| [conviction-features](conviction-features/SKILL.md) | adding a PIT-safe feature to the Phase-5 conviction model | project (Phase 5) |
| [regime-classification](regime-classification/SKILL.md) | detecting/labelling market regime (breadth/state) — and what it may/may-not gate | project (§11-aware) |
| [indian-market-execution](indian-market-execution/SKILL.md) | NSE mechanics — STT, circuit limits, F&O, T+1, settlement, SEBI language | algo_ai_skill `indian-algo-trading` (Apache-2.0) |
| [kite-execution](kite-execution/SKILL.md) | Kite (Zerodha) auth, fills, session expiry, order edge cases | project (audit-grounded) |
| [portfolio-simulation](portfolio-simulation/SKILL.md) | paper gate, fill realism, kill-switch triggers, live-vs-backtest divergences — before any real rupee | project (Stage E→F) |
| [research-log](research-log/SKILL.md) | recording a finding — where it goes (registry / changelog / ADR / findings) | project |

## Source digests (reference only — `_ingested/`)

Critical, project-grounded digests of what each external source offered and what we ignored.
Not procedures — provenance + the adopt/reject reasoning.

| Digest | Credibility | Net value |
|---|---|---|
| [_ingested/claude-trading-skills.md](_ingested/claude-trading-skills.md) | high | the goldmine — backtest-expert, data-quality, edge-* pipeline |
| [_ingested/algo_ai_skill.md](_ingested/algo_ai_skill.md) | high | Indian-market realism + backtest→live lifecycle |
| [_ingested/finance_skills.md](_ingested/finance_skills.md) | high (selective) | corporate-actions + compliance language; rest = advisory noise |
| [_ingested/scientiacapital_skills.md](_ingested/scientiacapital_skills.md) | medium | agent-swarm/debug patterns; rest = GTM/eng noise |
| [_ingested/medium_161skills.md](_ingested/medium_161skills.md) | medium | walk-forward / feature-importance / bootstrap / agentic arch (ADOPT); HMM-regime / pairs (REVISIT); chart-patterns / RSI / LSTM (REJECT — contradict our KILLs) |
| [_ingested/medium_900hours.md](_ingested/medium_900hours.md) | low | process hygiene (plan-first, tight specs, CLAUDE.md) — validates what we already do |
| [_ingested/mphinance_alpha_skills.md](_ingested/mphinance_alpha_skills.md) | medium (US-oriented) | 6 process patterns to fold in (kill-criteria block, plateau-not-peak, sample-adequacy, cross-regime, MAE/MFE + regime-mismatch postmortem) + 2 sleeve hypotheses (NSE pair / PEAD); REJECT the US screeners; DANGER: ghost-auto-trader (never install) |

## How the skills connect (graph)

```
  repo-map  (before changing any value/formula/file — blast radius + parity)
       │
       ▼
                       methodology-synthesis  (entry point — which method applies)
                                 │
  data-quality ──► backtest-rigor ──► overlay-testing ──► research-log
       ▲                                   ▲    ▲              │
       │                                   │    │              ▼
  (every data change)        edge-research-pipeline   research/overlay_registry.md
                                   │        │                  research/findings/
                              conviction-features              docs/decisions/ (ADRs)
                                   │
                       sell-replace-logic · regime-classification
                                   │
              indian-market-execution · kite-execution  (live realism)
```

## Provenance & licenses

External patterns are **adapted + attributed, never raw-copied**. Source licenses:
`algo_ai_skill` Apache-2.0 · `claude-trading-skills` MIT (© 2026 TraderMonty) ·
`finance_skills` MIT · `scientiacapital/skills` (see repo). The Medium articles are
public posts (the 161-skills repo is MIT). Original clones live **outside** this repo
(`~/lh-skill-sources/`) and are not committed.

## The bar every borrowed idea must clear

A borrowed method is a **hypothesis**, never an instant adoption. To go live it must pass the
promotion bar in [`../docs/LIVE_OVERLAY_PROTOCOL.md`](../docs/LIVE_OVERLAY_PROTOCOL.md):
post-tax post-cost ΔSharpe ≥ +0.10, ΔCalmar ≥ +0.05, 2022–2026 positive, walk-forward
fold-pass ≥ 60%, bootstrap 95% CI excludes 0, turnover ≤ +30%, mechanism explainable — and
it must not contradict a validated §11 KILL without genuinely new evidence.
