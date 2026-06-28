# Ingested digest — `claude-trading-skills`

**Source:** `claude-trading-skills` (GitHub, author "TraderMonty"), local clone at
`/c/Users/krees.KREESHSLAPTOP/lh-skill-sources/claude-trading-skills/`.
**License:** MIT (Copyright (c) 2026 TraderMonty) — adapt + attribute, do not copy verbatim chunks.
**Credibility: HIGH** for methodology/process discipline; **MEDIUM-LOW** for any concrete
signal/setup logic (US-equity swing-trading oriented: CANSLIM/VCP/gap-up/parabolic-short,
US holidays, FMP/FINVIZ APIs, RSP/SPY cross-asset ratios). The crown-jewel skills
(`backtest-expert`, `edge-strategy-reviewer`, `signal-postmortem`) are essentially
strategy-agnostic *validation and research-discipline machinery* and port cleanly to our
long-horizon Indian cross-sectional trend book. The screeners and entry-family logic do NOT.

---

## 1-paragraph summary

A 78-skill library for an LLM-driven US-equity swing-trading research operation. The
genuinely valuable, portable content is its **process scaffolding**, not its alpha: (1) a
"beat-ideas-to-death" backtest-validation methodology with an explicit red-flags checklist and
a deterministic 5-dimension scoring script that emits a Deploy/Refine/Abandon verdict; (2) a
structured **edge-discovery pipeline** (hypothesis-hint → concept → strategy-draft → a
*deterministic* 8-criterion review gate (PASS/REVISE/REJECT) → export, with a full run manifest
and a bounded review-revision loop) — which is a clean blueprint for our Phase-4 harness +
research registry; (3) a **signal-postmortem** loop that classifies each closed signal
(TP/FP/missed/regime-mismatch), enforces a ≥20-sample minimum before adjusting any weight, and
feeds skill-improvement backlog entries — a direct template for our conviction-model feedback
and our hypothesis registry. Most of the rest is US-market-specific setup logic, cross-asset
ratio plumbing, or document-publication QA that does not transfer.

---

## High-value patterns (port these)

| # | Pattern | Source skill | Why relevant to OUR long-horizon engine | Port target |
|---|---------|--------------|------------------------------------------|-------------|
| P1 | "Beat-ideas-to-death" backtest red-flag checklist | `backtest-expert/references/failed_tests.md` | This is the "Backtest-Expert checklist" our Phase-1 audit already referenced — captured precisely below. Codifies survivorship/lookahead/corporate-action/sample-size/plateau checks that map onto our exact failure modes (VEDL demerger-as-split fabricated slope; survivor-only features.pkl). | harness / data-quality / research-discipline |
| P2 | 5-dimension backtest scoring → Deploy/Refine/Abandon verdict | `backtest-expert/scripts/evaluate_backtest.py` | A runnable, deterministic scorer (Sample/Expectancy/Risk/Robustness/ExecRealism, 0-100). We can wrap our own backtest outputs through an adapted version as a *standardized verdict stamp* on every registry entry. Catastrophic-DD override (≥50% → score 0) and "too-good" flag (WR>90% & DD<5%) are cheap lookahead tripwires. | harness |
| P3 | Deterministic 8-criterion strategy-review gate (C1–C8, weighted, PASS/REVISE/REJECT) | `edge-strategy-reviewer` (`SKILL.md` + `references/review_criteria.md`) | Exactly the shape of gate we want in front of any overlay/conviction idea: hard-fail on weak edge thesis (C1) or overfit complexity (C2) → immediate REJECT before scoring anything else. Encodes overfit penalties (precise decimal thresholds, >10/>12 condition count), sample-adequacy estimation, regime-dependency check, exit calibration. Adapts to our promotion bar as a pre-screen. | harness / research-discipline |
| P4 | Overfitting heuristics: round-number thresholds, condition-count caps, ≤5 params | `edge-strategy-reviewer/references/overfitting_checklist.md` + `backtest-expert/references/methodology.md §7` | Directly reinforces our KILL discipline. "Precise threshold (RSI>33.5) = curve-fit" and "param count ≥7 = over-optimized flag" are concrete, mechanical rules we can run against any proposed overlay before it ever touches the harness. Aligns with our frozen-param philosophy. | research-discipline / conviction |
| P5 | Edge-discovery swarm: hint → concept → draft → review → export + run-manifest | `edge-pipeline-orchestrator` + `edge-candidate-agent` (+ hint-extractor/concept-synthesizer/strategy-designer) | Blueprint for our Phase-4 harness orchestration AND our registry: a bounded review-revision loop (max 2 iters; unresolved REVISE → downgraded to `research_probe`, never silently exported), strict-export mode, a `pipeline_run_manifest.json` with full execution trace. Mirrors our pre-registration → test → verdict flow with auditability baked in. | harness / research-discipline |
| P6 | Signal postmortem: outcome classes + ≥20-sample gate + feedback loop | `signal-postmortem` | Direct template for our per-trade conviction feedback. Classifies each closed signal TP/FP/MISSED/REGIME_MISMATCH, records regime-at-signal vs regime-at-exit (separates skill failure from regime shift — matches our "low confidence is INFORMATION not noise" finding), and **refuses weight changes below 20 samples**. Slots onto our forward-wall accumulation + conviction model. | conviction / research-discipline |
| P7 | Position-sizing constraint hygiene: strictest-constraint-wins, round-down, portfolio-heat ≤6-8%, half-Kelly | `position-sizer` (+ `references/sizing_methodologies.md`) | We already have Kelly+ATR+caps; the portable bit is the *checklist framing*: enumerate every constraint (risk%, max-position%, sector%, ADV%), apply the tightest, round shares DOWN, cap total open risk (portfolio "heat") at 6-8%, never full-Kelly. A clean acceptance test for our Phase-6 sizing overlay. | conviction / indian-exec |
| P8 | Regime as weighted composite of orthogonal components (not a single gate) | `macro-regime-detector` | Architecture (not the US ratios): a regime read built from N weighted orthogonal components with explicit weights + a structural(1-2yr) vs tactical(2-8wk) horizon split. Useful framing for a regime *context/sizing modulator* — BUT see distractions: regime-as-entry-gate is a validated KILL for us; only the composite-construction + horizon-separation idea ports. | regime |

---

## Distilled portable content (ready to adapt)

### P1 — Backtest red-flag checklist (the "Backtest-Expert checklist")
Run before trusting ANY backtest. >2-3 unchecked items ⇒ not ready.
- **Data quality:** survivorship addressed? delisted names included? data alignment (no
  lookahead)? corporate actions (splits/dividends) handled? *(this is the exact box our VEDL
  demerger-as-split bug and survivor-only features.pkl failed.)*
- **Sample:** ≥100 trades (200+ ideal); ≥5yr (10+ ideal); full market cycle; multiple regimes.
- **Parameter robustness:** works at nearby param values? a *plateau* of stable performance
  (not a spike)? ≤5 params? params from logic, not pure optimization?
- **Execution realism:** realistic commissions; slippage at 1.5–2× typical; worst-case fills;
  rejections/partial fills.
- **Performance:** positive expectancy in *majority of years*; acceptable in all regimes; no
  >50% DD; edge survives friction.
- **Bias prevention:** rules fixed before testing; economic logic for the edge; results not
  "too good to be true"; OOS performed; no cherry-picking.
- **Process discipline:** spend 20% generating ideas, 80% trying to break them; seek plateaus
  not peaks; a 5% per-trade edge needs 100+ trades to distinguish from luck. Multiple-comparison
  correction required when mining many ideas (they recommend Bonferroni / p<0.01 — we already do
  better with Deflated Sharpe; keep ours).

### P2 — 5-dimension verdict scorer (adapt thresholds to our bar)
Five dims × 20pts = 100; verdict ≥70 Deploy / ≥40 Refine / else Abandon.
- Sample Size (trades), Expectancy (WR×avgWin − lossRate×avgLoss), Risk Mgmt (DD + profit
  factor; **DD≥50% hard-zeros the dimension**), Robustness (years + param count: ≤4 params full
  marks, ≥7 → flag), Execution Realism (was slippage modeled at all).
- Red-flag emitters worth stealing: `negative_expectancy`, `no_slippage_test`,
  `excessive_drawdown(>50%)`, `over_optimized(params≥7)`, `too_good(WR>90% & DD<5%)`.
- *Adaptation note:* the absolute pass thresholds are tuned for US swing trading (WR-centric).
  For us, replace the verdict with our promotion bar (ΔSharpe≥+0.10 ∧ ΔCalmar≥+0.05 ∧
  2022-26 positive ∧ fold-pass≥60% ∧ bootstrap CI excludes 0 ∧ turnover≤+30% ∧ mechanism
  explainable). Keep the *structure* (per-dimension subscore + red-flag list + single verdict
  stamp on each registry entry), discard their numeric cutoffs.

### P3/P4 — Strategy-review gate + overfit heuristics
- **Hard-fail short-circuit:** if edge-thesis is empty/generic (C1 fail) OR condition count >12
  (C2 fail) → REJECT immediately, don't bother scoring the rest. (We should fail fast on
  "no explainable mechanism" — that's already in our bar.)
- **Overfit tripwires (mechanical):** any threshold with a decimal (RSI>33.5, vol>1.73×) = −10
  penalty each; ≥10 conditions = warn, ≥12 = fail; single-regime with no cross-regime validation
  plan = warn; <10 opportunities/yr = fail (too restrictive to validate); stop >15% or
  reward:risk <1.5 = fail; risk_per_trade >2% = fail. Prefer round behavioral levels (RSI 30/70,
  50-DMA) and ≤5 params.
- **Use for us:** a pre-harness lint on any proposed overlay — reject decimal-tuned thresholds
  and high-param-count ideas *before* spending compute, consistent with our frozen-param ethos.

### P5 — Edge pipeline orchestration (for the Phase-4 harness + registry)
- Stages: auto-detect → hints → concepts → drafts → **review/revision loop** → export, each
  writing a YAML artifact.
- **Bounded loop with safe downgrade:** review max 2 iterations; PASS exports, REJECT drops,
  REVISE re-reviewed; *anything still REVISE after the cap is downgraded to `research_probe`, not
  exported.* Nothing silently ships. `--strict-export`: any warn on an export-eligible draft →
  REVISE.
- **Auditability:** every run emits `pipeline_run_manifest.json` with the full execution trace;
  drafts split into `exportable/` vs `research_only/`. Mirror this in our registry: every
  hypothesis run leaves a manifest (params, seed, fold results, verdict, who-passed-what).

### P6 — Signal postmortem loop (for conviction + forward wall)
- Per closed signal: predicted dir vs realized 5d/20d return → {TRUE_POSITIVE, FALSE_POSITIVE,
  MISSED_OPPORTUNITY, REGIME_MISMATCH}; record `regime_at_signal` AND `regime_at_exit`.
- **≥20 samples before any weight/conviction adjustment** (binomial-confidence floor — matches
  our own "WR<45% over 20 trades" rollback math).
- Emits structured weight-adjustment suggestions + a skill-improvement backlog (issue_type,
  severity, evidence, suggested_action). Adapt to feed our conviction model and our KILL/registry
  backlog. Honest attribution: every outcome tagged to its source.

### P7 — Position-sizing acceptance checklist
Survival-first; default 1% risk, never >2%; round shares DOWN; **strictest constraint wins** when
risk% / max-position% / sector% / ADV% collide; total open "portfolio heat" ≤6-8%; half-Kelly
(captures ~75% of growth at far less risk) — never full Kelly. Use as the acceptance test for our
Phase-6 conviction-driven sizing overlay (we already have the mechanics; this is the guardrail
spec).

---

## Distractions / ignore (do NOT port — and what contradicts our validated KILLs)

- **US swing-trading setup skills** — `canslim-screener`, `vcp-screener`,
  `stockbee-momentum-burst-screener`, `breakout-trade-planner`, `parabolic-short-trade-planner`,
  `pead-screener`, `ftd-detector`, `ibd-distribution-day-monitor`, `earnings-trade-analyzer`.
  Different strategy family (short-horizon US single-name breakout/short), not our 63-day
  cross-sectional trend book. The `edge-*` pipeline's exportable entry families are hardwired to
  `pivot_breakout`/`gap_up_continuation` — *we keep the orchestration shell, discard the entry
  families.*
- **`data-quality-checker`** — despite the name, it validates *blog/market-analysis documents*
  (price-scale digit counts, ETF-vs-futures confusion, US-holiday weekday mismatches, allocation
  totals, bp-vs-% units, FRED publication delays). It is NOT OHLCV/PIT/corporate-action
  integrity. Not our data-integrity need. The only transferable scrap: the *idea* of a
  digit-count scale heuristic and a structured error taxonomy — but build our own OHLCV checker
  (split/demerger detection, zero-volume, PIT membership) from scratch.
- **US-specific options/advisory skills** — `options-strategy-advisor`,
  `stanley-druckenmiller-investment`, `us-market-bubble-detector`, `value-dividend-screener`,
  `dividend-growth-pullback-screener`, the `kanchi-dividend-*` US-tax/SOP set. US-options &
  dividend/tax — no transfer to a long-only NSE trend book.
- **CRM/ops/meta skills** — `skill-designer`, `skill-idea-miner`, `trading-skills-navigator`,
  `weekly-performance-digest`, `trade-performance-coach`, `trader-memory-core`. Generic
  meta/journaling; nothing methodological we don't already have.
- **Macro/regime US plumbing** — `macro-regime-detector` (RSP/SPY, HYG/LQD, IWM/SPY, FMP API),
  `market-breadth-analyzer`, `market-environment-analysis`, `sector-analyst`, `theme-detector`.
  Keep ONLY the *architecture* (weighted-orthogonal-component composite; structural-vs-tactical
  horizon split). **Flag / contradiction with our KILLs:** these skills implicitly treat regime
  and sector signals as tradeable edges and several screeners suggest "add a regime filter" as a
  fix. For us that is dangerous: **regime-entry-gate is a validated KILL (§11)**,
  **sector-selection overlays are KILLED** (sector-momentum IC≈0, 6/10 sector feats dead),
  and **RSI/MACD/ROC reversal is KILLED**. Treat any source nudge toward "gate entries by regime"
  or "rotate by sector" as a KNOWN-FALSE prior — regime/sector only survive as a *sizing/context
  modulator hypothesis*, still subject to our full promotion bar.
- **`institutional-flow-tracker`, `market-news-analyst`, `economic-calendar-fetcher`,
  `earnings-calendar`, `finviz-screener`** — US data-source wrappers (FINVIZ/FMP/US earnings).
  Data plumbing, no methodology, wrong market.

---

## Net take for a senior quant maintainer

Three skills are worth genuinely adapting into our stack — `backtest-expert` (P1+P2: the
red-flag checklist + the deterministic verdict scorer, with thresholds swapped for our promotion
bar), `edge-strategy-reviewer` (P3+P4: the fail-fast 8-criterion overfit gate as a pre-harness
lint), and `signal-postmortem` (P6: the ≥20-sample outcome-classification feedback loop for our
conviction model and forward wall). The `edge-pipeline-orchestrator` (P5) is the cleanest
existing blueprint for wiring our Phase-4 harness + registry with auditable run-manifests and a
safe never-silently-ship review loop. Everything else is US-market setup logic, document QA, or
data plumbing — and a few of the regime/sector skills actively nudge toward strategies we have
already KILLed, so they carry a warning label rather than an adoption path.
