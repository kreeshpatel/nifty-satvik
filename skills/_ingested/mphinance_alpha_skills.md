# Digest: mphinance/alpha-skills

**Source**: https://github.com/mphinance/alpha-skills (formerly antigravity-skills)
**License**: MIT
**Skill count**: 113 directories (per README badge — actual count on disk: ~113 in `skills/`)
**Orientation**: US equities, US options (0DTE), US screener APIs (FMP/Tradier/Alpaca),
Minervini/O'Neil/Druckenmiller methodology, Japanese-market minor coverage.
**Data dependency**: ~18 skills require a paid FMP API key; `ghost-auto-trader` requires
Tradier brokerage API for live execution; `portfolio-manager` requires Alpaca MCP.
**Credibility**: Public open-source, MIT-licensed; code-level quality is solid (structured
Python scripts, JSON schemas, walk-forward references); methodology sources are credible
(Minervini VCP, O'Neil CANSLIM, Engle-Granger cointegration). The quant rigor is
practitioner-grade, not academic-grade — no formal statistical hypothesis testing (e.g., no
t-tests, no bootstrap CIs, no DSR corrections) except in the separate `backtest-expert`
bias checklist. No mention of India/NSE/BSE anywhere in the codebase.

---

## Summary

mphinance/alpha-skills is a 113-skill suite built primarily for US equity traders following
momentum/growth methodologies (Minervini, O'Neil, Druckenmiller). It covers the full
research-to-execution stack: raw observation → edge hypothesis → strategy design → quality
gate → screening → position sizing → portfolio tracking → postmortem. The process-level
skills (hypothesis ideation, backtest methodology, strategy review, signal postmortem,
trader memory state machine) are thoughtfully designed and largely market-agnostic. The
instrument-level skills — screeners, breadth analyzers, FTD/distribution-day detectors,
CANSLIM/VCP/pair-trade — are hardwired to US equities, FMP's US data API, S&P 500/NASDAQ
indices, and US broker APIs. They cannot be applied to NSE directly. One skill
(`ghost-auto-trader`) presents a concrete live-execution DANGER for our paper-first,
manual-confirm discipline. The most transferable content is a cluster of six process/pipeline
skills that would reinforce — not duplicate — our existing project skills.

---

## Skill Transfer Table

| Skill name | What it is | Transfer verdict |
|---|---|---|
| **quant-feature-engineer** | Renaissance-style unified feature engine: break idea → isolate features → test predictive power → score model → Optuna | CANDIDATE — feature ideation process maps directly to our edge-research-pipeline; the scoring model philosophy mirrors our sma200_slope_63 ranking; no India-specific blocker |
| **trade-hypothesis-ideator** | Structured hypothesis cards with falsifiable thesis, kill criteria, experiment design; YAML export for pipeline | ADOPT-PATTERN — almost identical to what our edge-research-pipeline skill does; adds the `kill criteria` field we sometimes skip; the structured YAML schema is worth copying into our pre-registration template |
| **backtest-expert** | "Beat ideas to death" methodology: stress-test stops ±50%, seek plateau not peak, walk-forward, 30-trade minimum, pessimistic fills | ADOPT-PATTERN — the plateau-seeking principle and "punish the strategy" framing are exactly what our backtest-rigor skill enforces; cross-reference only, do not port the script (our harness is different) |
| **edge-strategy-reviewer** | 8-criterion PASS/REVISE/REJECT gate (C1 plausibility, C2 overfit, C3 sample adequacy, C4 regime dependency, C5 exit calibration, C6 concentration, C7 execution realism, C8 invalidation quality) | ADOPT-PATTERN — C3 (sample adequacy continuous score) and C4 (cross-regime validation required) are gaps in our current overlay-testing checklist; the verdict framework maps to our pre-registration gate |
| **edge-pipeline-orchestrator** | 6-stage pipeline: hint-extractor → concept-synthesizer → strategy-designer → reviewer → candidate-agent → orchestrator | REFERENCE-only — our edge-research-pipeline skill already covers this flow; the 6-stage decomposition is useful framing but we have NSE-specific data contracts |
| **signal-postmortem** | Structured postmortem: TRUE_POSITIVE / FALSE_POSITIVE / MISSED / REGIME_MISMATCH; regime-stamping; weight feedback to aggregator | ADOPT-PATTERN — the REGIME_MISMATCH category is one we should formally capture in our signal_analytics.json; the minimum-sample-size rule (20+ for weight adjustments) mirrors our DSR discipline |
| **trader-memory-core** | YAML-based thesis state machine: IDEA → ENTRY_READY → ACTIVE → CLOSED; MAE/MFE postmortem; forward-only transitions; git-tracked state | CANDIDATE — the thesis lifecycle state machine is a useful structure for our paper-trading phase; the MAE/MFE postmortem (maximum favorable/adverse excursion) is not tracked anywhere in our current pipeline |
| **position-sizer** | Fixed-fractional, ATR-based, half-Kelly; portfolio heat cap; binding-constraint logic | REFERENCE-only — we have `trading/position_sizer.py` with Kelly + ATR; the "strictest constraint wins" and "half Kelly" principles are worth reviewing against our sizing_redesign (0036) work |
| **pair-trade-screener** | Cointegration (ADF), z-score entry/exit, beta-neutral pairs; FMP data, statsmodels | CANDIDATE (orthogonal sleeve research) — pairs on NSE are a structurally orthogonal return stream that does not conflict with our trend-momentum primary; this would belong in a new pre-registration entry in overlay_registry. Blocker: script uses FMP API (US data); would need NSE adapter |
| **pead-screener** | Post-Earnings Announcement Drift: weekly candle red-pullback → breakout; FMP calendar; 5-week monitoring window | CANDIDATE (orthogonal sleeve research) — PEAD is documented on NSE (Q results announcements); orthogonal to our sma200_slope_63 signal; needs NSE earnings calendar (not FMP); add to overlay_registry as a hypothesis, not a ready-to-port script |
| **institutional-flow-tracker** | 13F SEC filings → institutional accumulation/distribution; 45d lag; FMP API | REFERENCE-only for methodology; REJECT as a tool — 13F filings are US-SEC specific; Indian equivalent is SEBI bulk deal disclosures + FII/DII aggregate flows (we already have the FII/DII sleeve research in our program) |
| **portfolio-manager** | Alpaca MCP integration for portfolio analysis, rebalancing, risk metrics | REJECT-US-specific — hardwired to Alpaca brokerage; we use Kite/Zerodha |
| **macro-regime-detector** | RSP/SPY, IWM/SPY, HYG/LQD, XLY/XLP cross-asset ratios → 5 regime types (Concentration/Broadening/Contraction/Inflationary/Transitional); monthly frequency | REFERENCE-only — the 5-regime taxonomy and cross-asset approach are intellectually useful for our regime-classification skill; direct use impossible (US ETFs only, no Nifty equivalents wired in) |
| **sector-analyst** | TraderMonty public CSV → sector uptrend ratios → cycle phase; no API key | REJECT-US-specific — data source is US sector ETFs via TraderMonty; we killed price-sector-overlay (Test A, lean years audit) |
| **market-breadth-analyzer** | TraderMonty public CSV → 6-component 0-100 breadth score; no API key | REJECT-US-specific — hardwired to TraderMonty US breadth CSV; analogue for India would need NSE advance-decline data |
| **uptrend-analyzer** | Same TraderMonty CSV, 5 components, ~2800 US stocks | REJECT-US-specific — same as above |
| **market-top-detector** | O'Neil distribution days + Minervini leading-stock deterioration + defensive rotation; FMP API | REJECT-US-specific — FMP US data; but the distribution-day concept is worth knowing for understanding our lean-year patterns |
| **ftd-detector** | O'Neil Follow-Through Day state machine for bottom confirmation; FMP | REJECT-US-specific — FMP, US indices only |
| **ibd-distribution-day-monitor** | IBD distribution day counting; FMP | REJECT-US-specific |
| **stanley-druckenmiller-investment** | Meta-synthesizer: ingests 8 upstream skill JSONs → conviction 0-100 → allocation recommendation | REJECT-US-specific — requires the 5 US-specific upstream skills (breadth/uptrend/top/macro/FTD); the meta-synthesis PATTERN is interesting but already covered by our regime-classification + methodology-synthesis skills |
| **canslim-screener** | O'Neil CANSLIM: Current earnings, Annual growth, New high, Supply/demand, Leadership RS rank, Institutional sponsorship, Market direction; FMP | REJECT-US-specific + REJECT-contradicts-our-KILLs — RSI/momentum filter + chart-pattern entry = we killed these; FMP US data |
| **vcp-screener** | Minervini VCP: Stage 2 uptrend + tight base + volatility contraction breakout; FMP | REJECT-contradicts-our-KILLs — VCP = chart-pattern entry feature, explicitly killed; FMP US data |
| **breakout-trade-planner** | Minervini trade plans from VCP output: entry, stop, target, sizing | REJECT-contradicts-our-KILLs — chart-pattern breakout, killed |
| **finviz-screener** | Natural language → FinViz URL builder | REJECT-US-specific — FinViz is a US screener site |
| **value-dividend-screener** | P/E < 20, yield 3%+, 3yr growth; FMP | REJECT-US-specific — we have our own fundamentals work (Screener.in / 0010 delivery-%) on NSE |
| **dividend-growth-pullback-screener** | 12%+ dividend growers, RSI oversold; FMP | REJECT-US-specific + RSI reversal = REJECT-contradicts-our-KILLs |
| **kanchi-dividend-sop / review / tax** | Japanese dividend investing SOP + US tax accounting | REJECT-US-specific — US tax treatment irrelevant; Indian tax treatment is different |
| **earnings-trade-analyzer** | 5-factor post-earnings scoring; FMP | REJECT-US-specific (FMP, US earnings dates) |
| **earnings-calendar** | Upcoming US earnings; FMP | REJECT-US-specific |
| **pine-to-python** | TradingView PineScript → vectorized Python + Optuna space | REFERENCE-only — we have no Pine scripts to translate; the repaint-risk audit (force `.shift(1)`) is a useful lookahead reminder already in our data-quality skill |
| **us-stock-analysis** | Comprehensive fundamental + technical report for US tickers via web search | REJECT-US-specific |
| **us-market-bubble-detector** | Minsky/Kindleberger bubble scoring: Put/Call, VIX, margin debt, IPO data | REJECT-US-specific |
| **market-environment-analysis** | Global macro overview: US, Europe, Asia, forex, commodities via web search | REFERENCE-only — good framing for macro context in our regime-classification |
| **market-news-analyst** | News impact analysis on equities/commodities; web search | REFERENCE-only — we have our own news_analyzer.py in production |
| **economic-calendar-fetcher** | US/global economic events; FMP | REFERENCE-only — we have NSE holiday + event awareness in config.py |
| **data-quality-checker** | Price scale, notation, date accuracy validation in reports | REFERENCE-only — we have a more complete data-quality skill |
| **options-strategy-advisor** | Black-Scholes, Greeks, P/L simulation; FMP | REFERENCE-only — potentially useful for our vol-carry pivot (Phase-0 underway), but this is a conceptual framework document, not a production tool |
| **ghost-auto-trader** | TradingView webhook → LLM gate → Tradier broker execution, 0DTE options, 30s loop, +50% TP / -40% SL | **DANGER** — see below |
| **portable-memory-core** | `.agent/` folder for cross-harness memory (preferences, history, identity) | REFERENCE-only — we use MEMORY.md + topic files; the structured YAML schema for preferences is worth considering for our research-log skill |
| **skill-warden / skill-designer / write-a-skill / dual-axis-skill-reviewer** | Skill lifecycle infrastructure (health audit, creation template, quality score) | REFERENCE-only — our skills already have their own format; the dual-axis quality score (0-100) is interesting for our own skill-review process |
| **scenario-analyzer** | 18-month scenario from news headlines; multi-agent (analyst + reviewer) | REFERENCE-only |
| **edge-hint-extractor / edge-concept-synthesizer / edge-strategy-designer / edge-candidate-agent / edge-signal-aggregator** | Pipeline stages 1-5 before orchestrator | REFERENCE-only — covered by our edge-research-pipeline skill |
| All creative/productivity skills (blog-post, dashboard, saas-landing, audio-jingle, etc.) | Non-trading content production | NOT APPLICABLE |

---

## TOP TRANSFERABLE PATTERNS

### 1. trade-hypothesis-ideator: Kill Criteria Field (feeds: edge-research-pipeline, pre-registration)

The hypothesis card schema includes an explicit `kill_criteria` array with threshold and measurement source for each criterion. Our pre-registration templates (in `diagnostics/research/preregistry/`) use ad-hoc language for kill conditions. Adopting a structured `kill_criteria` YAML block would make our pre-reg machine-verifiable. Specific addition to the pre-registration template:

```yaml
kill_criteria:
  - metric: per_trade_ci_low
    threshold: 0.0
    source: bootstrap_ci
    verdict_if_below: KILL
  - metric: dsr
    threshold: 0.95
    source: src/validation/overfitting.py
    verdict_if_below: KILL
```

This feeds directly into our `edge-research-pipeline` skill's Step 6 (pre-registration) and `overlay-testing` skill's gate checklist.

### 2. backtest-expert: "Plateau not Peak" Stress-Test Frame (feeds: backtest-rigor)

The skill's core principle — test stop loss at 50%/75%/100%/125%/150% of baseline and look for a plateau of stable performance, not an optimal spike — should be added to our `backtest-rigor` SKILL.md as a named heuristic. We informally do this (parameter sensitivity around stop_atr_mult) but do not frame it as a first-class validation step. The script (`evaluate_backtest.py`) produces a 5-dimension score (Sample Size / Expectancy / Risk Management / Robustness / Execution Realism) that is a useful checklist structure for our backtest-validator agent.

### 3. edge-strategy-reviewer: C3 + C4 Criteria (feeds: overlay-testing)

Two of the eight review criteria are not explicitly in our overlay-testing checklist:

- **C3 Sample Adequacy** (continuous score from estimated annual opportunities): We enforce a minimum trade count per pre-reg but do not score it as a continuous dimension. A sleeve with 15 trades per year should score lower than one with 60, even if both pass the absolute floor.
- **C4 Regime Dependency** (cross-regime validation required for PASS): Our overlay-testing skill requires a walk-forward but does not explicitly require the candidate to be tested in at least two distinct market regimes (BULL/BEAR/CHOPPY). This is already violated by any candidate that only runs in the post-2020 bull regime.

### 4. signal-postmortem: REGIME_MISMATCH Category + Minimum Sample Rule (feeds: research-log, signals)

Our `signal_analytics.json` captures exit reasons (HIT_TARGET, HIT_STOP, EXPIRED, REPLACED) but does not tag whether the outcome was regime-driven. Adding a `regime_at_entry` and `regime_at_exit` field to closed signals would let us distinguish "strategy underperforms in BEAR because it is wrong" from "strategy underperforms in BEAR because it is BEAR." The minimum-sample-size rule (20+ closed signals before adjusting any weight) mirrors our DSR discipline and should be cited in our methodology-synthesis skill.

### 5. trader-memory-core: MAE/MFE Postmortem Fields (feeds: portfolio-simulation, research-log)

Maximum Adverse Excursion and Maximum Favorable Excursion are not computed anywhere in our pipeline. MAE measures "how far against us did the position go before hitting stop/target" — a key input for stop placement calibration. MFE measures "how much upside did we leave on the table" — a key input for target calibration. These are computable from our OHLCV cache for every closed signal in `signals_history.json`. This would strengthen the evidence base for any future stop/target parameter review without requiring a full backtest rerun.

### 6. pair-trade-screener: Cointegration Sleeve Hypothesis (feeds: overlay_registry, edge-research-pipeline)

The ADF cointegration methodology is statistically sound and the pair-trading return stream is structurally orthogonal to trend-momentum (it profits in sideways/choppy markets — exactly our CHOPPY-regime lean years). This is worth a pre-registration entry in `research/overlay_registry.md` as a medium-priority sleeve hypothesis. Key conditions for a valid India-adapted test: (a) universe = Nifty 500 with NSE data (not FMP), (b) minimum ADV filter (≥5cr, matching our large+mid filter), (c) no short-selling for long-only constraint (would need long-only adaptation: only LONG leg of the pair), (d) cointegration must be retested every quarter (NSE sector composition shifts). This is research-worthy but not near-term: we are in paper-trading phase and vol-carry pivot is the prioritized second stream.

### 7. pead-screener: Post-Earnings Drift Hypothesis (feeds: overlay_registry)

PEAD is documented on NSE (Malhotra et al., 2010s studies; Bhattacharya 2018). The mechanism (delayed price adjustment to earnings surprises) is market-structure agnostic. A pre-registration entry is warranted. Key conditions: (a) India earnings calendar (NSE bulk results announcements), (b) minimum market cap for liquidity (Nifty 200 or above to ensure fills), (c) holding period 20-40 trading days (Indian earnings cycle is quarterly, same as US), (d) cannot use FMP — needs Screener.in data or direct NSE filings. Low confidence in transferability without India-specific IC measurement first.

---

## DISTRACTIONS / REJECT LIST

### US-Specific Screeners (REJECT — wrong universe + wrong data API)

- **canslim-screener**: Hardwired to FMP US earnings data, US RS rank, US market direction (S&P 500 M component). Many of the CANSLIM factors (Institutional sponsorship via 13F, earnings growth via FMP) have no NSE equivalent in this implementation. Additionally, the N (new high) and L (leadership RS rank) components overlap our killed chart-pattern and momentum-as-entry features.
- **vcp-screener**: Minervini VCP = volatility contraction breakout pattern = killed feature class per our research log (chart-patterns as entry features: KILL). Doubly irrelevant: FMP + S&P 500 hardcoded universe.
- **breakout-trade-planner**: Downstream of vcp-screener; same kill reason.
- **finviz-screener**: FinViz is a US-only screener. NSE has no equivalent API. Not applicable.
- **value-dividend-screener**: P/E < 20 + 3%+ yield criteria via FMP; India P/E multiples and dividend norms differ materially. Our 0010 delivery-% work and Screener.in scrape cover this hypothesis space for NSE.
- **dividend-growth-pullback-screener**: RSI oversold filter = killed reversal signal class; US dividend data via FMP.
- **earnings-trade-analyzer**: US earnings gap + 5-factor scoring; no NSE earnings calendar source.
- **portfolio-manager**: Alpaca MCP only; we use Kite/Zerodha. Not portable.
- **institutional-flow-tracker**: 13F SEC filings are a US regulatory artifact. India equivalent = SEBI bulk deals + FII/DII disclosures (already explored in our FII/DII sleeve research, demoted to regime-only use).
- **us-stock-analysis, us-market-bubble-detector**: US-ticker-only by design.
- **market-breadth-analyzer, uptrend-analyzer, breadth-chart-analyst**: TraderMonty's public CSV covers US stocks only; the S&P 500 breadth index is the underlying data.
- **market-top-detector, ftd-detector, ibd-distribution-day-monitor**: FMP US data; O'Neil distribution days are defined on US index volume norms; FTD signals use NASDAQ/S&P 500 indices.
- **stanley-druckenmiller-investment**: Meta-synthesizer that requires the five US-specific upstream skills listed above. The individual skill JSONs it consumes are all US data. The synthesis PATTERN is interesting but we already have regime-classification + methodology-synthesis doing this work.
- **kanchi-dividend-sop / review / tax**: Japanese investing methodology + US tax treatment; irrelevant to Indian market and Indian tax law.
- **sector-analyst**: TraderMonty US sector CSV. We killed price-sector-overlay (Test A, 2026-06-14 lean years audit).
- **macro-regime-detector**: RSP/SPY, IWM/SPY, HYG/LQD = US ETFs. The 5-regime taxonomy is intellectually interesting but not operationalizable on NSE without rebuilding the data layer.

### Kills-Overlap (REJECT — contradicts our validated KILLs)

- **vcp-screener / breakout-trade-planner**: Chart pattern as entry feature — KILL per our research log.
- **dividend-growth-pullback-screener**: RSI oversold entry — KILL per our research log (RSI/MACD/ROC reversal).
- **canslim-screener** (N component = new 52-week high breakout): overlaps chart-pattern entry — KILL.
- **technical-analyst** skill (not listed in table above, generic): Weekly chart patterns, MACD, RSI as entry signals — overlaps our KILL list for reversal signals.

### SECURITY / SAFETY FLAG: ghost-auto-trader

**DANGER — DO NOT USE.** This skill automates live broker execution with zero human confirmation: TradingView webhook fires → LLM validates in <1s → Tradier API places 0DTE options order with no manual step. Specific risks in our context:

1. **Contradicts our paper-first gate**: We are in paper/shadow phase before any real capital. Automated execution without human confirmation is a hard violation of our LIVE_OVERLAY_PROTOCOL.md and the gate discipline enforced by our kill-system.
2. **0DTE options**: We do not trade options at all; our strategy is long-only equity trend-momentum.
3. **No circuit breaker**: The 30-second monitor loop with hardcoded +50% TP / -40% SL is a minimum risk guard, not a portfolio-level kill switch. Our own kill-system (portfolio equity curve circuit breaker) would be bypassed entirely.
4. **Tradier API is US broker**: Not applicable to Kite/Zerodha. But the danger is in the pattern: if someone adapts this to Kite, they would be enabling fully automated live trading without the paper gate.

This skill should never be installed in the project workspace. It is flagged here to explicitly rule it out.

---

## HONEST BOTTOM LINE

**Two categories of value; one category of danger.**

**Genuine process patterns worth porting (6):**

| Pattern | Target in our project |
|---|---|
| Kill-criteria structured YAML block | Add to pre-registration template in `diagnostics/research/preregistry/` |
| Plateau-not-peak stress-test framing | Add to `skills/backtest-rigor/SKILL.md` as named heuristic |
| C3 sample adequacy continuous score | Add to `skills/overlay-testing/SKILL.md` checklist |
| C4 cross-regime validation requirement | Add to `skills/overlay-testing/SKILL.md` checklist |
| REGIME_MISMATCH outcome category + min-20 rule | Add `regime_at_entry`/`regime_at_exit` to `signal_analytics.json` schema; cite in `skills/research-log/SKILL.md` |
| MAE/MFE postmortem fields | Add to `signals_history.json` schema; document in `skills/portfolio-simulation/SKILL.md` |

**Hypothesis entries worth adding to overlay_registry (2):**

| Hypothesis | Priority | Blocker before research |
|---|---|---|
| Pair-trading sleeve (cointegration, long-only adapted) | Low | NSE OHLCV adapter; no short-selling constraint; paper-trading gate must pass first |
| PEAD sleeve (post-earnings drift, NSE quarterly results) | Low | India earnings calendar source; min Nifty-200 universe; needs IC measurement before pre-reg |

**Nothing here warrants a new project skill.** Our existing skills (backtest-rigor, overlay-testing, edge-research-pipeline, research-log, methodology-synthesis, portfolio-simulation) already cover all the relevant process territory. The incremental additions are edits to existing skills and schema fields, not new skills.

**All 113 trading tools themselves are US-only or contradict our KILLs.** No script, screener, or data-fetch tool is directly portable to NSE without a full rewrite of the data layer.
