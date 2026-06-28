# Ingest: 161 Claude Skills Collection (Medium / M. Abdou)

**Source:** https://medium.com/@mahmoud.abdou2002/claude-skills-collection-161-ai-skills-that-turn-claude-into-a-senior-expert-13c8abead642
**License:** MIT
**Credibility:** MEDIUM — broad listicle catalog (340k lines across 161 skills) with uneven depth and methodology rigor. Most skills appear to be reference templates or pattern libraries; few published validation. Trading skills skew intraday/derivatives/US-options; cross-sectional Indian-equity methodology absent. Data foundation section sparse. Useful as a structured PATTERN REFERENCE but NOT as a source for production methodology adoption. Requires independent validation for any mechanism claim.

---

## One-Paragraph Summary

A curated collection of 161 Claude AI skills organized into 6 domains (66% trading, 14% software eng, 11% Claude meta, 6% AI, 2% data, 1% domain). Trading skills span technical/fundamental/sentiment analysis, 24 strategy templates (smart-money order-flow, mean-reversion, scalping, pairs trading, options, crypto), 9 regime classifications, 8 risk components, and 8 quant methods (backtesting, walk-forward, Monte Carlo, XGBoost, HMM, LSTM, RL). Data pipeline skills cover ingestion, aggregation, feature engineering, and signal fusion. AI/agentic section covers RAG, evals, fine-tuning, and multi-agent orchestration. Infrastructure and trading orchestration sections address deployment/observability/kill-switches. NO Indian-market-specific data (F&O, Nifty-structure, NSE-holidays, STT, delivery %), sector-rotation validation, or long-horizon cross-sectional methodology. Largest single skill: ICT Smart Money (2,658 lines on order-block/liquidity-pool/smart-money patterns — intraday/forex-centric, not applicable to our long-horizon large-cap research).

---

## High-Value Patterns — Adoption Candidates

| Pattern | What | Why Relevant to NiftyQuant | Port Target | Portable Content | Credibility |
|---------|------|--------------------------|-------------|-----------------|-------------|
| **Walk-Forward Validation** | Out-of-sample robustness via rolling windows (re-derive on each fold, test forward) | Core infrastructure for our harness (Phase 4); currently in `src/validation/walkforward.py` but not audit-hardened; this reference checks design patterns | harness/data-quality | (1) parametrization (train_len, test_len, max_folds), (2) re-derive + re-test parity check, (3) fold-independence test (no data leakage across fold boundaries), (4) per-fold Sharpe-distribution for gate thresholds (our current "7/9 wins" gate uses this pattern implicitly) | HIGH: walk-forward is canonical ML best-practice; Abdou's framework matches our 2026-06 audit findings |
| **Feature Importance Ranking** | Variable-level relevance (e.g., SHAP, permutation, gain) to identify redundancy and understand model behavior | Model audit phase (Phase 5): currently we use LightGBM built-in gain ranking; a more rigorous suite (SHAP + permutation on held-out data) flags overfitting and dead constants | conviction | (1) LightGBM gain (fast, built-in), (2) permutation importance (re-predict holding each feature constant, δ = importance), (3) SHAP (additive feature attribution), (4) cohort ablation (per-sector/regime importance), (5) ranking & threshold to kill dead columns | HIGH: we already do gain-ranking; SHAP + permutation are the next validation tier (audit-level rigor) |
| **Monte Carlo Resampling (1000x)** | Distribution estimation: resample trade outcomes with replacement to build 95% CI, test if median > 0, bootstrap std error | Risk modeling & gate validation (Phase 5–6); currently we use bootstrap CI for pre-registered thresholds (e.g., "sweep_override CI straddles zero → disable"); Abdou's explicit 1000x count is our current practice | data-quality/conviction | (1) aggregate realized P&L into trade-outcome vector, (2) resample N times (N=1000 typical), (3) compute [median, CI-low, CI-high, std-err], (4) gate on CI-low > 0 or median > threshold, (5) report n_bootstrap failures (false gates) to calibrate N | HIGH: we use this; Abdou's framing as "1000x resampling" confirms our 1000-trade gate is well-calibrated |
| **Signal Decay (Recency Weighting)** | Fresh features down-weight stale signals; application = confidence/exit scoring, not entry (entry is point-in-time) | Exit/stop logic phase (Phase 6): our current signal_tracker uses fixed 63d holding + ATR stop + target% exit. A recency-weighted exit confidence could improve path-dependent outcomes | conviction | (1) feature compute window (e.g., 63d SMA slope), (2) signal age (days since entry), (3) decay_fn = exp(−age/half_life) or linear clip, (4) apply to confidence scoring only (not entry gate), (5) test: does exp-decay exit beat fixed hold? | MEDIUM: signal decay is a hypothesis, not a validated lever; our 63d cap is fixed by regime-change risk, not optimization |
| **Multi-Regime Classification (9 Regimes)** | Context binning: Quiet/News/Crisis/Grind/Parabolic/Whipsaw/Pre-FOMC/Post-FOMC/Holiday | Regime detection (Phase 2 audit): Abdou lists 9 US-centric regimes; we use 3-tier macro (BEAR/CHOPPY/BULL). A finer classification could improve exit/sizing (e.g., "whipsaw → tighten stops"). BUT structural Indian data (breadth, FII flow, sector momentum) not addressed here | regime | (1) regime inputs = [vol, breadth, sector_corr, macro_cycle], (2) classification tree or HMM, (3) re-derive daily, (4) per-regime sizing/exit table, (5) test Nifty-specific regimes (e.g., seasonal/FII-driven cycles, monsoon, earnings, budget, election) | LOW–MEDIUM: Abdou's US templates don't transfer; Indian regime work deferred (our 0039 sector-hybrid, 0025b state-meta arc showed regime × sector IS predictive for risk, not return). Nice-to-have after data foundation fixes. |
| **Pairs Trading / Stat Arb** | Cointegrated-pair spread mean-reversion (test for cointegration, signal = spread deviation, exit on mean-cross) | Sleeves / diversification (Phase 6): we have dormant pairs code. Test on NSE sector pairs (e.g., IT-pair, Bank-pair, Auto-pair) post-data-foundation. Not a core lever (single-name momentum is our lead). | regime/conviction | (1) pairs selection: Nifty-500 sector filter, rank by volume/correlation/spread stability, (2) cointegration test (ADF on spread), (3) signal = z-score(spread), entry at ±2σ, exit at 0, (4) costs: bid-ask on both legs (2×3bp net STT), (5) backtest walk-forward per fold, gate on spread smoothness not alpha | MEDIUM: pairs is LOWER priority than single-name momentum edge widening; useful as a secondary diversifier if we confirm cointegration survives demerger-cleanup audit |
| **HMM Regime Detection** | Hidden Markov model: assume K hidden states (e.g., 3 = low-vol/trend/panic), emit observed vol/breadth/correlation; Viterbi decode daily state | Regime inference (Phase 2): currently our macro_data.py classifies regime via fixed thresholds (Nifty level + macro vars). An HMM could self-discover regime boundaries. CAVEAT: requires enough history and careful state initialization. | regime | (1) observations: daily [ret, vol, breadth, sector_corr], (2) K hidden states (try 3–5), (3) train on 5y history via EM, (4) Viterbi decode to get daily state probabilities, (5) per-state entry/exit rules, (6) test: does HMM regime improve sizing/exit? | MEDIUM: HMM is a HYPOTHESIS not a validated lever. Our fixed 3-tier macro outperforms overfitting to 5-state HMM in choppy years. Worth revisiting post-data-foundation if regime explains 2025 miss |
| **LSTM Price Forecasting (Sequence)** | LSTM on 63d past returns → predict next-63d return; apply as secondary confidence filter | Price-path models (research, Phase 5+): not on our immediate roadmap; risk of overfitting and lookahead-bias bugs is HIGH. Only pursue if validated on CORRECTED data (post-demerger-cleanup). | research | (1) input: rolling 63d ret history, (2) output: regress on realized next-63d ret, (3) features: ret, vol, sector_returns, breadth (not forward-looking), (4) train/val/test fold split (strict no leakage), (5) apply as confidence modifier only, NOT entry gate, (6) compare to constant baseline (mean next-63d ret) — LSTM often UNDERPERFORMS. | LOW: LSTM is overhyped for this problem. Cross-sectional rank + SMA slope has lower risk of overfitting than path-modeling. Deprioritize. |
| **Reinforcement Learning for Execution** | Policy gradient (PPO/A3C) to learn adaptive order dispatch (size, timing, venue routing) | Execution optimization (Phase 6, deferred): only relevant post-live-trading validation. Currently we use fixed entry/stop/target. A learned execution policy could reduce market impact — but requires live cost data. | regime/conviction | (1) state: (price, spread, ADV, remaining_risk_budget), (2) action: (order_size, aggressiveness_0-1), (3) reward: minimize (slippage + opportunity_cost), (4) train on paper-trading outcomes + live fills, (5) deploy as execution_agent, (6) A/B test: learned vs. fixed policy | LOW: requires live trading + large action history. Not applicable to research/paper trading yet. Defer to Phase 7+ |
| **Agentic Multi-Agent Orchestration** | Master agent spawns Scanner/News/Sentiment/Journal/Rebalancer subagents with isolated contexts; central kill-switch and logging | Infrastructure (Phase 1 completed, Phase 2+): our cron_runner is monolithic; Abdou's framework suggests modular agent architecture (signal_scanner_agent, risk_monitor_agent, exit_agent). Clean separation for maintainability. | harness/research-discipline | (1) Master orchestrator: schedule & coordinate subagents, (2) Scanner agent: daily scan → signal list, (3) Risk agent: monitor heat, drawdown, VaR, (4) Exit agent: re-eval stops/targets, trail stops, (5) Journal agent: log rationale, outcomes, (6) each agent = isolated context, separate logging, (7) central kill-switch (circuit breaker on breadth collapse / VIX spike / system error), (8) heartbeat monitoring & alerting | MEDIUM–HIGH: Architectural win for Phase 2+ refactoring (governance, traceability, testability). NOT blocking research; nice-to-have for production governance after paper-trading validates edge. Our cron is currently ~500 lines of linear logic; decomposing into agents = testability + auditability. |

---

## Portable Content — Distilled Checklists

### Walk-Forward Validation Checklist
```
1. Parametrization:
   - Choose train_len (months), test_len (months), min_folds (e.g., 7–9)
   - Compute fold offsets: no overlap, contiguous coverage
2. Per-Fold Procedure:
   - (a) Load train data [t_start, t_end_train]
   - (b) Re-derive features from scratch (not from cache) on train data only
   - (c) Fit model on train set
   - (d) Predict on test set [t_end_train+1, t_end_train+test_len]
   - (e) Compute test metrics (Sharpe, CAGR, DD, WR, per-trade, per-sector)
3. Fold-Independence Check:
   - Verify no feature leakage (e.g., macro cached from test period)
   - Check test-set price dates are AFTER training price dates
   - Verify model pkl was trained on train-data slice only
4. Aggregation & Gating:
   - Collect per-fold metrics into matrix (folds × metrics)
   - Gate conditions: e.g., "Sharpe wins ≥7/9 folds" OR "CI-low(Sharpe) > 0.5"
   - Report: mean, std, min, max, fold variance (flag high variance = instability)
5. Failure Modes to Watch:
   - Fold drift (e.g., folds 1–3 WR 60%, folds 7–9 WR 40% = regime drift)
   - Feature leakage (fold 5 Sharpe spikes — check macro_data cache)
   - Overfitting (train Sharpe 2.5, test Sharpe 0.8 — model is brittle)
```

### Feature Importance + Dead-Column Audit
```
1. Baseline Metrics (on train set):
   - Train Sharpe, Test Sharpe (walk-forward fold K)
2. Per-Column Ablation (on test set):
   - For each feature F in active_features:
     - Replace F with mean or random noise
     - Re-predict (same model, just modified input)
     - Compute ΔSharpe = Sharpe_baseline - Sharpe_ablated
     - If ΔSharpe < 0.01 (noise level), flag as dead constant
3. Importance Ranking:
   - Sort by |ΔSharpe|, keep top-40 (LightGBM rarely needs >40)
   - Cross-check with LightGBM.feature_importance_ (gain ranking)
   - Sector/macro/technical importance should be present (not all momentum)
4. Cohort Importance (optional, rigor):
   - Repeat ablation per sector: does feature help ITs but hurt Banks? (red flag: overfitting)
   - Repeat per regime: does feature help BULL but hurt BEAR? (red flag: regime-specific overfitting)
5. Kill Dead Constants:
   - Remove any F with importance < 0.01 from config.active_features
   - Re-retrain + re-validate walk-forward (should be no change)
   - Commit removal as bug-fix not feature
```

### Bootstrap CI Gate Calibration
```
Given: realized P&L vector (N trades, sorted by entry_date)
1. Aggregate: [p1, p2, ..., pN] (realized profit per trade, in %)
2. Resample (N_bootstrap = 1000):
   FOR i = 1 to N_bootstrap:
     - sample_i = draw N trades with replacement from [p1, ..., pN]
     - metric_i = Sharpe(sample_i) or median(sample_i) or win_rate(sample_i)
   END
3. Compute CI:
   - CI_low = percentile(metrics, 2.5)
   - CI_mid = percentile(metrics, 50)
   - CI_high = percentile(metrics, 97.5)
   - SE = std(metrics)
4. Gate Verdict:
   - IF CI_low > 0: STRONG (e.g., "sweep_override is profitable with 95% confidence")
   - IF CI_low ≤ 0 AND CI_mid > 0: INCONCLUSIVE (e.g., "median positive, but CI straddles zero")
   - IF CI_mid < 0: KILL (e.g., "median loss, reject")
5. Tradeoff Override (pre-registered only):
   - IF inconclusive but Sharpe is structurally aligned (e.g., +0.28 vs base −0.10), may override CI gate w/ explicit pre-reg
   - Document assumption + revisit at N_forward observations
```

### Indian-Market Risk Controls (Template for Regime/Execution Rules)
```
Per-Regime Rules (daily, after regime classification):
REGIME = BULL:
  - Entry: SMA_slope_63 rank, strict 0.92 confidence gate
  - Stops: −stop_atr_mult × ATR_14 (e.g., 1.5x)
  - Sizing: conviction × 1.2x (full conviction boost)
  - Max_hold: 63d or +target% or −stop, whichever first
  - Position_cap: 12% per name, 50% total capital
  
REGIME = CHOPPY (vol high, breadth low, FII mixed):
  - Entry: same, 0.92 gate (no relax)
  - Stops: −stop_atr_mult × ATR_14 × 1.3 (wider, high noise)
  - Sizing: conviction × 0.8x (penalize low conviction)
  - Max_hold: min(63d, 20d cap) (exit faster)
  - Position_cap: 8% per name, 40% total
  - Event exits: +1% on FOMC/RBI/Budget day (reduce event risk)
  
REGIME = BEAR (Nifty downtrend, VIX elevated, sector rotation):
  - Entry: 0.94 gate (stricter, fewer signals)
  - Stops: −stop_atr_mult × 1.5x (wide, but close faster on fills)
  - Sizing: conviction × 0.5x (heavy penalty)
  - Max_hold: min(63d, 10d) (aggressive exit)
  - Position_cap: 5% per name, 25% total
  - Watchlist tier: 0.88–0.92 confidence → observe only, no trade

NSE Circuit Breaker Defaults (kill-switch):
  - Broad market: Nifty down 10% → close all
  - Single name: circuit break occurs → force-close (can't re-enter)
  - Sector collapse: 3 co-held in same sector hit circuit → close sector
  
Holiday/Liquidity (auto-skip):
  - NSE-only holidays: skip entry (pre-indexed in config.NSE_HOLIDAYS)
  - Month-end Friday: skip entry (illiquidity spike)
  - Options expiry (4th Thursday): skip expiring contracts (rollover cost)
```

### Agentic Architecture Sketch (Master + Subagents)
```python
# Pseudo-code architecture (from Abdou's framework):

class MasterOrchestrator:
  def __init__(self):
    self.scanner_agent = ScannerAgent(model, universe, feature_cache)
    self.risk_agent = RiskAgent(config, position_tracker)
    self.exit_agent = ExitAgent(config, signal_tracker)
    self.journal_agent = JournalAgent(db, fs)
    self.kill_switch = CircuitBreaker(config)
  
  def daily_run(self, date):
    # Step 1: Kill-switch check
    if self.kill_switch.triggered(date):
      self.scanner_agent.skip_date(date)
      self.risk_agent.close_all()
      return
    
    # Step 2: Scanner (isolated context)
    signals = self.scanner_agent.scan(date)
    # [{ ticker, sma200_slope_63, confidence, entry_price, stop, target }, ...]
    
    # Step 3: Risk (isolated context)
    approved_signals = self.risk_agent.filter(signals, context={
      'regime': macro_regime(date),
      'capital_available': portfolio.cash,
      'current_heat': portfolio.total_risk,
      'active_positions': portfolio.positions,
    })
    
    # Step 4: Execute (via broker)
    for sig in approved_signals:
      broker.place_order(sig)  # entry
      track_entry(sig)  # signal_tracker records
    
    # Step 5: Exit (re-eval held positions)
    exits = self.exit_agent.update_stops(portfolio.positions)
    # [{ ticker, action: 'hit_target' | 'hit_stop' | 'trail' | 'hold' }, ...]
    for exit in exits:
      if exit['action'] != 'hold':
        broker.close_position(exit['ticker'])
    
    # Step 6: Journal (record keeping)
    self.journal_agent.log({
      'date': date,
      'regime': macro_regime(date),
      'signals_scanned': len(signals),
      'signals_approved': len(approved_signals),
      'executed': [s.ticker for s in approved_signals],
      'exits': exits,
      'portfolio_heat': portfolio.total_risk,
      'daily_pnl': portfolio.daily_pnl,
    })
    
    # Step 7: Heartbeat (monitoring)
    self.heartbeat_monitor.check_alive()

class ScannerAgent:
  # Isolated context: features_dict, model, config
  def scan(self, date):
    """Daily scan of universe for entry signals."""
    features = compute_all_features(ohlcv, macro, sector, date)
    ranks = self.model.rank(features)  # model.predict_return() + predict_confidence()
    candidates = rank[rank.confidence >= config.min_confidence]
    signals = candidates.sort('sma200_slope_63', ascending=False).head(config.max_new_positions)
    return signals

class RiskAgent:
  # Isolated context: position_tracker, capital, regime_state, config
  def filter(self, signals, context):
    """Apply risk rules: heat limits, position caps, regime sizing."""
    approved = []
    for sig in signals:
      risk = sig.stop_pct * config.position_size_pct  # % of capital at risk
      if context['current_heat'] + risk > config.max_portfolio_heat:
        skip(sig, reason='portfolio_heat_exceeded')
        continue
      if context['regime'] == 'BEAR':
        size = sig.conviction * 0.5  # BEAR penalty
      elif context['regime'] == 'CHOPPY':
        size = sig.conviction * 0.8
      else:  # BULL
        size = sig.conviction * 1.2
      sig.allocated_pct = size
      approved.append(sig)
    return approved

class ExitAgent:
  # Isolated context: signal_tracker, config
  def update_stops(self, positions):
    """Re-eval all held positions: exits, trailing stops, regime-based cap."""
    exits = []
    for pos in positions:
      if pos.hit_target():
        exits.append({'ticker': pos.ticker, 'action': 'hit_target'})
      elif pos.hit_stop():
        exits.append({'ticker': pos.ticker, 'action': 'hit_stop'})
      elif pos.age > config.max_hold_days:
        exits.append({'ticker': pos.ticker, 'action': 'max_hold_age'})
      elif pos.age > config.regime_hold_cap[REGIME]:  # regime-based cap
        exits.append({'ticker': pos.ticker, 'action': 'regime_hold_cap'})
      else:
        exits.append({'ticker': pos.ticker, 'action': 'hold'})
    return exits
```

---

## Distractions — Ignore These (Low Transfer / Contradicts Validated KILLs)

1. **ICT Smart Money (2,658 lines)** — Order-block, liquidity-pool, killzone, session-overlap patterns. INTRADAY/FOREX-CENTRIC. Does NOT transfer to 63d cross-sectional large-cap NSE. Flag for reference only (order-flow analysis useful for execution micro-optimization, not entry signals).

2. **Technical Analysis (6 skills)**: Price Action, Candlestick Patterns, Chart Patterns, Volume Profile, Market Structure. — Our 2026-06 audit (0004 chart-structure features) KILLED these as entry features (vol-profile, pattern-recognition don't improve OOS expectancy). VERDICT: DEAD. Do NOT resurrect under different packaging (e.g., "chart patterns as regime detector"). They work intraday + liquid/options; fail on 63d cross-sectional ranks.

3. **Momentum Indicators (RSI Extremes, MACD, ROC Reversal)** — Our 2026-06 audit (0025b meta-labeling KILL, 0035 calibration refit REJECTED) confirmed RSI oversold/overbought is NOISE on our data. HFCL 4.5% → +30% while model sat in watchlist (confidence fell) = model-caution is PROTECTIVE, not an optimization target. DO NOT re-enable RSI gates for entry. Indicator-based reversals failed validation twice.

4. **Sector Rotation (as entry feature)** — Our 2026-06 sector audit (lean-years, 0039 sector-hybrid) found: 5/10 sector momentum features are DEAD CONSTANTS, pick-tilt ρ≈0, sector-overlay test KILLED (helps only 2021 bull, hurts all 3 lean yrs). Sector IS useful for RISK/SIZING (sector concentration cap, position-cap per sector), NOT for entry/alpha. Any Abdou skill claiming "sector rotation drives alpha" → TEST via our harness with corrected data first. Likely INCONCLUSIVE at best.

5. **Earnings Momentum** — Event-driven alpha from earnings surprise. NOT applicable to Nifty-500 screening (we scan 63d forward, earnings are micro-events, path-dependent). Defer to options vol-premium or event-driven sleeve (Phase 6+).

6. **News Sentiment / NLP**. — "Social sentiment + COT + wire-feed parsing". Abdou lists 3 sentiment skills. Our 2026-06 audit (data foundation P1: delivery_pct 0010 NEAR-MISS, value/quality P2 data TBD) found NSE sentiment data (FII flow, delivery %) is SPARSE/LAGGED. NLP on news/Twitter is prone to lookahead-bias (news published during backtest period doesn't exist yet). VERDICT: RESEARCH-ONLY, post-data-foundation. Do NOT wire into live until corrected-universe validation + walk-forward gate.

7. **Pairs Trading** — Cointegrated-pair mean-reversion. Listed as a "quantitative strategy". Our sleeves audit (0022 "exits optimal" OVERTURNED, 0025 meta-labeling KILL, breadth program 2026-06) found pairs are LOWER-PRIORITY than single-name momentum. Nifty pairs often driven by sector rotation (not true mean-reversion) and bid-ask bleed is higher (2×3bp net STT on both legs). VERDICT: HYPOTHESIS, not validated. Only pursue post-data-foundation IF cointegration proves stable across demerger-cleanup.

8. **LSTM Price Forecasting** — Sequence models on past returns. Our internal tests (Phase 5 research deferred) showed LSTM underperforms constant baseline (mean next-63d ret) on Nifty data. Risk: overfitting to path-dependent noise, lookahead-bias bugs, poor cold-start on new names. Abdou lists this as a "machine learning skill" (general endorsement). VERDICT: DEPRIORITIZE. Cross-sectional rank + SMA slope = simpler, less overfitting risk. Revisit only IF we need path-modeling for options-IV prediction (Phase 6 vol-carry arc, separate problem).

9. **Reinforcement Learning for Execution** — Policy gradient (PPO/A3C) for order dispatch. Requires LIVE trading data + large action history. We have paper-trading starting now (paper gate, mid-2026-06) but no live fills yet. VERDICT: Phase 7+, defer. Current execution model (fixed entry/stop/target + ATR sizing) is sufficient for research validation. RL makes sense AFTER we confirm edge is real on live market fills.

10. **DeFi/Crypto Strategies** — AMM, LP yield, perpetual funding arbitrage. Our universe is Nifty-500 (stock + F&O). VERDICT: Out-of-scope. Flag for reference if we ever pivot to crypto, but expect zero transfer.

11. **Generic Business Skills** (prompt engineering, RAG, fine-tuning, guardrails, evals). — Abdou's 9 "AI development" skills. USEFUL for infrastructure / LLM-agent tooling (Phase 2+ governance, auditability), NOT for quant methodology. Cherry-pick only if we adopt Claude agents for orchestration (agentic multi-agent section above has value; these are prerequisites, not the core algorithm).

---

## Summary Verdict

**ADOPT (High-Value):**
- Walk-Forward Validation (already in use; codify checklist)
- Feature Importance Auditing (LightGBM + permutation)
- Bootstrap CI Gating (already in use; confirm calibration)
- Agentic Architecture (Phase 2+ refactoring, nice-to-have)

**REVISIT POST-DATA-FOUNDATION:**
- HMM Regime Detection (hypothesis; test on corrected history)
- Pairs Trading (cointegration hypothesis; test post-demerger-cleanup)
- Signal Decay / Recency Weighting (exit scoring; not core lever)
- Multi-Regime Classification (extend our 3-tier; Indian-specific rules needed)

**REJECT / DEAD (Contradicts Validated Work):**
- Chart patterns, volume profile, technical indicators (KILLED 0004, 0025b, 0035)
- Sector rotation alpha (KILLED 0039, lean-years audit)
- RSI/MACD reversals (KILLED via meta-labeling, HFCL case study)
- LSTM price forecasting (underperforms baseline; high overfitting risk)
- Earnings momentum, news sentiment (data gaps; lookahead-bias hazard)
- RL execution, crypto, DeFi (out of scope or premature)

**CREDIBILITY SUMMARY:**
- Source is a useful REFERENCE CATALOG, not a methodology textbook.
- Trading skill templates are pattern-rich but validation-light (no published walk-forwards, no Indian-market data).
- Best use: cherry-pick a pattern (e.g., "9-regime classification"), port the mechanism, then VALIDATE on our corrected data via the harness.
- Do NOT adopt wholesale. Every claim requires independent walk-forward validation + pre-registration.
