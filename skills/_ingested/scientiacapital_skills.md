# Ingest: scientiacapital/skills

**Source:** `/c/Users/krees.KREESHSLAPTOP/lh-skill-sources/skills/`
**License:** MIT (per repo readme pattern; confirm before copying any verbatim code)
**Ingested:** 2026-06-27
**Credibility:** Medium — well-structured engineering skillset for US options/IBKR trading; quant
methodology is practitioner-grade but US-centric and not empirically validated for Indian
cross-sectional equity. Research-discipline content is thin; workflow-engineering content is solid.

---

## One-paragraph summary

ScientiaCapital/skills is a 67-skill library built around a BDR (sales development) operator who
also actively trades US options via IBKR. The majority of skills (40+) are pure GTM/CRM/sales
automation — completely irrelevant to NiftyQuant. The trading-relevant content lives in
`trading-signals-skill` (18 reference files: backtesting patterns, Markov regime, risk management,
equities scanner, Turtle/Elliott/Fibonacci/Wyckoff/options strategies) and the workflow-engineering
layer (agent-teams, subagent-teams, dual-team architecture, debug-like-expert, workflow-orchestrator).
The backtesting patterns file is the highest-value artifact for us: it articulates clean separation
of signal generation / portfolio management / performance analysis, identifies the core look-ahead and
survivorship-bias failure modes, and correctly names walk-forward as the only trustworthy validation
mode. The Markov-regime file is US/crypto-centric (7-state BTC model) — not portable as-is but the
4-state general model and VIX-override circuit-breaker pattern transfer conceptually. Risk management
is options-Greeks-centric (delta/gamma/theta gates) — inapplicable to our long-only equity strategy,
but the drawdown-escalation ladder and Kelly half-sizing rationale are portable. The agent-orchestration
skills document a real dual-team (Builder + Observer) pattern and context-engineering discipline that
directly maps to how we should structure multi-agent research workflows.

---

## High-value patterns

| # | Name | Source file | Why relevant to NiftyQuant | Port target |
|---|------|-------------|----------------------------|-------------|
| 1 | Walk-forward as the only trustworthy mode | `backtesting-patterns.md` | Matches our existing gate philosophy; the specific articulation of "train on N, test on N+1, slide" with minimum 100 trades is quotable in our harness docs | harness |
| 2 | Signal / Portfolio / Analyzer separation | `backtesting-patterns.md` | Our `backtest_engine.py` conflates signal generation and portfolio logic. The three-component split (SignalGenerator → PortfolioManager → PerformanceAnalyzer) maps cleanly to how we should refactor to accept injected strategies and support combinatorial sleeve testing | harness |
| 3 | Drawdown-escalation ladder | `risk-management.md` | The 0–3% / 3–5% / 5% half-size / 8% halt protocol is a clean model for how we structure the circuit-breaker in `signal_tracker.py`. Our current `KILL_CRITERIA` is binary; a graduated ladder is better for a strategy with 63d hold periods | conviction / regime |
| 4 | Half-Kelly with hard per-trade cap | `risk-management.md` + `equities.md` | We already use Kelly in `position_sizer.py`; the explicit reasoning for Half-Kelly (cut drawdown ~50% for ~25% CAGR sacrifice) and the "cap at 5–10% regardless" override is cleaner than our current config | conviction |
| 5 | Survivorship bias — explicit checklist item | `backtesting-patterns.md` | Our data foundation audit (MEMORY.md project_data_foundation_audit.md) already identified this as P1; this source confirms the canonical framing: "historical data only includes stocks that still exist today = missing all that went to zero" — useful as harness gate language | data-quality |
| 6 | Look-ahead bias — "using today's close to make today's decision" | `backtesting-patterns.md` | Direct framing for our harness PIT (point-in-time) checklist; useful for documenting why `persist=False` in `DataStore.compute_all_features` is mandatory | data-quality |
| 7 | Regime-aware backtesting: test within each regime separately | `backtesting-patterns.md` | Directly applicable to our lean-years / sector-blindness finding. The prescription "test within each regime separately to understand when the strategy works vs when it should be turned off" is the right framing for our `post0028_gonogo.md` regime-conditional analysis | regime |
| 8 | 4-state general Markov model (ADX + DI cross + ATR expansion) | `markov-regime.md` | Simplified version of what we already implement (3-tier BEAR/CHOPPY/BULL); the ADX>25 + DI cross formulation is a clean implementation reference if we ever revisit regime detector construction | regime |
| 9 | VIX-override circuit breaker at threshold | `markov-regime.md` | Pattern: "when VIX > 35, override model → cut size to minimum + hedging only." We have `KILL_CRITERIA` but no VIX-anchored override. For Indian markets this maps to India VIX (NSE). Mechanism is implementable via yfinance `^INDIAVIX`; threshold needs India-specific calibration | regime |
| 10 | Contract-first feature definition before coding | `dual-team-architecture.md` | Maps to our pre-registration discipline (`diagnostics/research/preregistry/`). The contract template (interfaces + scope boundaries + success criteria + observer checkpoints) is a cleaner format than our current markdown files | research-discipline |
| 11 | Builder + Observer dual-team: Observer is always non-negotiable | `dual-team-architecture.md` | For our multi-agent research workflows (Phase 4 harness build): a dedicated adversarial observer agent watching for lookahead / survivorship / parity bugs while the builder implements is exactly how we should structure complex harness PRs | harness / research-discipline |
| 12 | Context engineering: narrow file boundaries per agent | `context-engineering.md` | When we spawn subagents for sweep runs or feature experiments, giving each agent exactly the files it needs (not the whole repo) prevents drift and confusion. The WORKTREE_TASK.md < 1000-token rule is a useful forcing function | harness |
| 13 | Debug-like-expert: treat code you wrote with MORE skepticism | `debug-like-expert/SKILL.md` | Directly applicable to our audit bugs (e.g. AUD-023 reversal, 0011 label method walk-forward gate catching our own mistake). Formalizes: "your intent doesn't matter — only the code's actual behavior matters." | research-discipline |
| 14 | Relative-strength scan: stock_return_3m / spy_return_3m > 1.5 | `equities.md` | We already use `sma200_slope_63` as our cross-sectional rank signal. The RS formulation here (3m return vs index) is a simpler alternative worth comparing in a pre-registered trial as a robustness check on the ranking signal | conviction |
| 15 | Minimum 100 trades before drawing conclusions | `backtesting-patterns.md` | Validates our bootstrap CI requirement. The stated threshold is 100+ trades; below that "Monte Carlo simulation helps." We already enforce this but the framing is useful for harness documentation | harness |

---

## Distilled portable content

### 1. Backtest harness component separation

```
BacktestEngine (orchestrator)
├── SignalGenerator    — produces signals from strategy rules (injectable)
├── PortfolioManager   — tracks trades, capital, position limits, costs
└── PerformanceAnalyzer — computes metrics from completed trade history
```

The value: swapping signal generators without touching portfolio logic. Our current
`backtest_engine.py` already has injected-model design (post-v1 cleanup); the next
step is making `PortfolioManager` accept a `SizingPolicy` interface so that
conviction-driven sizing (Phase 6) can be tested without rewriting the engine.

### 2. Walk-forward articulation (harness docs language)

> "Train on window N, test on window N+1, slide. If a strategy only works in-sample,
> walk-forward exposes it. In-sample-only backtests are worthless for predicting future
> performance."

Minimum parameters we enforce: 252-day train, 63-day test (one quarter), slide by 63.
Below 100 trades per fold: flag the fold as underpowered.

### 3. Drawdown-escalation ladder (circuit breaker design)

| Drawdown from peak | Action |
|--------------------|--------|
| 0–3% | Normal; no change |
| 3–5% | Review all positions; tighten ATR stops by 20% |
| 5% | Reduce new-position size by 50%; hold existing |
| 8% | Halt new entries; review every open position |
| Recovery | Re-enter at 25% → 50% → 75% → 100% over 4 weeks, each week must be profitable |

For NiftyQuant's 63d hold: the 8% halt would mean no new signals until portfolio recovers.
India-specific calibration needed (our realized DD is higher, -40% research backtest).

### 4. Half-Kelly justification (for position_sizer.py docs)

Full Kelly maximizes geometric growth but produces 50–70% drawdowns. Half Kelly gives
~75% of growth rate with ~50% of the drawdown. In practice, cap at 10–15% per position
regardless of Kelly output because win-rate/payoff estimates are imprecise. We already
implement this; the explicit rationale should be documented in `position_sizer.py`.

### 5. India VIX circuit-breaker hypothesis

Source pattern: VIX > 35 → override model → cut size to minimum.
India VIX (`^INDIAVIX` via yfinance) is the NSE's equivalent. Historical threshold
needs calibration (Indian markets are structurally more volatile; threshold may need
to be 25–30 for equivalent signal quality). This is a pre-registered trial candidate
(not an instant adoption): does an India VIX gate improve Calmar ratio without
degrading Sharpe on the long-horizon walk-forward folds?

### 6. Dual-team research discipline (adapted to NiftyQuant)

For complex harness or overlay PRs:
- Builder agent: implements the harness change, writes tests
- Observer agent: independently checks for lookahead bias, PIT violations,
  cost omissions, parity with live cron path
- Observer is never optional; runs in a separate worktree

Context engineering rule: each agent's WORKTREE_TASK.md must be under 1000 tokens
and name exactly which files it can touch. No agent reads the full repo.

### 7. Debug-as-science protocol (adapted for quant bugs)

When a backtest produces suspicious results:
1. Document exact behavior (metric values, fold, n_trades)
2. Map execution path (which code computed this)
3. Form 2–3 falsifiable hypotheses
4. Test each with minimal interventions (one change at a time)
5. Never call it fixed until the reproduction test passes
6. Apply extra skepticism to code you yourself wrote

This is what caught our AUD-023 reversal and the ensemble component-order bug.
Formalizing it as a checklist reduces the chance of false KILLs/ADOPTs.

---

## Distractions / ignore list

| Skill / content area | Why irrelevant |
|----------------------|----------------|
| CRM / sales / BDR automation (38 skills) | GTM for a SaaS company, zero quant content |
| Options strategies (25+ strategies, Greeks gates, theta/vega/gamma) | We are long-only equity; no options |
| Zero-DTE / Wheel / Iron Condor / Credit spreads | US options specific |
| Elliott Wave / Fibonacci / Wyckoff (as entry signals) | Discretionary TA — contradicts our rule-based cross-sectional approach; also regime-entry-gate is a KILLED pattern for us |
| 7-state Bitcoin Markov model | Crypto-specific; on-chain metrics inapplicable |
| Swarm-consensus LLM voting for trade signals | We are rule-based, not LLM-signal driven; LLM used only for news sentiment and optimizer prompts |
| IBKR API / ib_async / execution routing | We use Kite/Zerodha; IBKR is irrelevant |
| forex / commodities / VIX term structure | Asset classes outside scope |
| NautilusTrader / LangGraph / Unsloth / GROQ | Infrastructure for LLM systems, not quant engine |
| Stripe / Supabase SQL / Docker Compose skills | Web-app engineering; backend team handles separately |
| RSI/MACD/ROC as entry signals | KILLED in our validated research (reversal signals underperform on NSE large+mid) |
| Fundamental P/E screening | We use liquidity + D/E + PIT membership filters; adding P/E valuation screen is a separate pre-registered trial, not an instant import |
| AGENT_SWARM_GUIDE.md rotation system | Designed for a 40-project portfolio rotating autonomously; our research is sequential/gated, not a rotation queue |
