---
name: methodology-synthesis
description: >
  The "always use" index of what we learned from external trading-skill sources and which of
  OUR skills/phases each borrowed method feeds. Consult this BEFORE building a harness component,
  a conviction feature, a sizing/exit overlay, a data-quality check, a regime classifier, or an
  Indian-execution guard — to know which borrowed method applies and whether it is ADOPTED,
  a CANDIDATE hypothesis to test, REFERENCE-only, or a REJECTED distraction. Trigger words:
  "what did we learn from external sources", "borrowed methodology", "which skill applies",
  "best practice from", "did someone already do this", "is there a pattern for", "external source",
  "ingested skills", "borrowed pattern".
---

# Methodology Synthesis — the borrowed-knowledge index for NiftyQuant Long-Horizon

This is the master index over six external skill libraries we ingested to make ourselves smarter
at building **NiftyQuant Long-Horizon** — a rule-based, long-only, cross-sectional 63-trading-day
trend-momentum strategy on NSE Nifty-500 large+mid caps (signal = `sma200_slope_63` top-15, frozen
params, baseline_v0 = **26.1% gross CAGR / 1.02 Sharpe / −41.9% DD / 0.62 Calmar; after-tax 23.1% / 0.83**
(supersedes the optimistic-exit 30.26%/1.15 measurement, 2026-06-27); never traded a live rupee, paper-first).

**How to use this file.** When you start work in a phase below, read the row(s) that feed it, then
open the named target skill (`skills/overlay-testing`, `skills/conviction-features`,
`skills/kite-execution`, `skills/regime-classification`, `skills/research-log`,
`skills/sell-replace-logic`) for the operational detail. A borrowed idea is a **HYPOTHESIS**, never
an instant adoption — anything marked CANDIDATE must clear the full promotion bar
(`skills/overlay-testing` Step 6) before it is wired in.

**The promotion bar (the one gate everything answers to).** Post-tax post-cost ΔSharpe ≥ +0.10
AND ΔCalmar ≥ +0.05 AND 2022–2026 sub-period positive AND walk-forward fold-pass ≥ 60% AND
block-bootstrap (block=63) 95% CI on ΔSharpe excludes zero AND turnover increase ≤ 30% AND
mechanism explainable in one sentence. No borrowed method is exempt.

---

## 1. Credibility verdict per source (one line each)

| Source | License | Verdict |
|---|---|---|
| **algo_ai_skill** — `indian-algo-trading` (Apache-2.0, v1.1.14) | Apache-2.0 | **HIGH** — the only source authored for the Indian market; its FY25-26 cost/friction tables, tick/circuit clamps, and 7-gate robustness battery are directly load-bearing. Hard-filter its sentiment "edges" and HMM-regime-gate (collide with our KILLs). |
| **claude-trading-skills** (TraderMonty, MIT, ©2026) | MIT | **HIGH** — best-in-class on backtest-trust discipline: the red-flag checklist, the 5-dimension verdict scorer, the C1–C8 review gate, the bounded review-loop + run-manifest, and the ≥20-sample postmortem loop are the cleanest external analogues to our harness + registry. Entry-logic skills are US-swing and discarded. |
| **finance_skills** (MIT, 84 skills) | MIT | **HIGH for data-quality only** — its corporate-action taxonomy, six-dimension data-quality framework, golden-source hierarchy, and adjusted-vs-unadjusted discipline are the spec for our VEDL-demerger bug class. ~70 of its 84 skills are US advisory/compliance/CRM and irrelevant; mine the data-integration plugin and the compliance vocabulary, ignore the rest. |
| **scientiacapital/skills** (67 skills) | (per repo) | **MEDIUM** — a handful of genuinely useful architecture/discipline patterns (three-component backtest separation, half-Kelly rationale, Builder+Observer audit, "skeptical of your own code", relative-strength as a cross-sectional alt-signal) buried in 38+ CRM/GTM and crypto/options skills. High signal-to-noise cost; the patterns we keep are real. |
| **Medium — "900+ Hours of Using Claude Code for Trading"** (AI in Trading, 2026-03-13) | article | **LOW** — anecdotal; its only durable contribution is the plan-before-build / tight-function-contract / CLAUDE.md-invariants discipline, which we partly already have. Its failure archetype ("code that errors repeatedly") is NOT our failure mode (ours is code that RUNS but silently violates PIT/lookahead). Treat as reinforcement, not new knowledge. |
| **medium_161skills.md** (Abdou-style 161-skill catalogue) | article | **MEDIUM** — walk-forward parametrization, feature-importance auditing (gain + permutation + SHAP), bootstrap-CI gating, and NSE-specific regime templates are useful and align with our existing practice. Its long tail (ICT/TA/momentum-indicator/sector-rotation entry signals) directly re-pitches our KILLs and must be refused. |

---

## 2. Mapping table — borrowed pattern → our phase/skill → adoption status

Status legend: **ADOPTED-as-skill** (already in one of our SKILL.md files or about to be wired into
one) · **CANDIDATE** (a pre-registerable hypothesis, must clear the promotion bar) · **REFERENCE**
(consult when relevant; not a trial) · **REJECTED** (distraction or collides with a §11 KILL).

| # | Borrowed pattern | Source | Feeds (phase / skill) | Status |
|---|---|---|---|---|
| 1 | **Indian cost & friction table (FY25-26)** — delivery STT "paid on both buy and sell", exchange txn + SEBI + stamp line items, slippage tiers | algo_ai_skill | data-quality / indian-exec (`kite-execution`, `overlay-testing` cost columns) | **CANDIDATE (audit)** — see §3.1; potentially changes our post-tax headline |
| 2 | **Tick-rounding + DPR/circuit clamp** on entry/stop/target | algo_ai_skill | indian-exec (`kite-execution`) | **ADOPTED** — formalizes the F2 penny-stock stop bug + merged circuit-breaker (#109) |
| 3 | **7-gate robustness battery** (walk-forward, trade-order MC reshuffle, price-permutation, holdout, regime-conditional, ±10% param sweep, ≥50-trade gate) | algo_ai_skill | harness (`overlay-testing`) / research-discipline (`research-log`) | **CANDIDATE** — adopt trade-order MC reshuffle + ±10% sensitivity sweep; keep our matched-permutation IC null over their price-permutation |
| 4 | **Sharpe-weighted allocation w/ correlation penalty + true portfolio heat** (`√(wᵀΣw)`) | algo_ai_skill | conviction (`conviction-features`) / harness | **CANDIDATE** — for the 2nd-return-stream/vol-carry composition; must beat the "weighting inert under caps" (0020) prior |
| 5 | **Layered drawdown / strategy-decay guardrails** (rolling-Sharpe decay detector) | algo_ai_skill | indian-exec / regime (`regime-classification`) | **CANDIDATE** — generalizes our 30d-Sharpe rollback into a continuous paper monitor; MUST re-derive thresholds for a 63d-hold/−40%-DD book |
| 6 | **Calmar-ratio optimization & ranking** | algo_ai_skill | harness (`overlay-testing` Step 4) | **ADOPTED** — our bar already requires ΔCalmar ≥ +0.05; standard helper |
| 7 | **STCG/LTCG holding-period arbitrage + after-tax checks** (20.8% STCG incl 4% cess) | algo_ai_skill | indian-exec / conviction | **CANDIDATE (audit)** — confirm backtester applies STCG incl cess (see §3.1); a "let winners run past 365d" exit-overlay is a registerable hypothesis (flag, don't build) |
| 8 | **AST linter** (no hardcoded token/lot-size, no NSE-scrape, IST tz present, structured logging) | algo_ai_skill | indian-exec / research-discipline | **CANDIDATE** — cheap CI lint over `long_horizon_cron` + Kite code |
| 9 | **Backtest red-flag checklist** (survivorship / delisted / data-alignment / corporate-actions / sample / param-robustness / execution-realism / bias-prevention) | claude-trading-skills | harness / data-quality / research-discipline | **ADOPTED** — pre-harness lint; its corporate-actions + survivorship boxes are exactly the boxes we failed (VEDL, survivor-only features.pkl) |
| 10 | **5-dimension verdict scorer** (per-dim subscore + red-flag list + single stamp; DD≥50%→0 override; too-good WR>90%&DD<5% flag) | claude-trading-skills | harness (`overlay-testing` Step 4/7) | **ADOPTED (structure)** — keep skeleton + DD-override + too-good flag; **replace their US-swing cutoffs with OUR promotion bar** |
| 11 | **C1–C8 deterministic review gate + overfit tripwires** (decimal-precision threshold = −10 each; ≥12 conditions = fail; no-mechanism = instant REJECT) | claude-trading-skills | harness / research-discipline / conviction | **ADOPTED** — fail-fast lint on every hypothesis BEFORE harness compute; C1/C2 short-circuit operationalizes our "mechanism explainable" gate |
| 12 | **Edge-discovery pipeline: stage → artifact → bounded-review → run-manifest, never-silently-ship** | claude-trading-skills | harness / research-discipline (`research-log`) | **ADOPTED (shell)** — mirror in our registry; unresolved candidates auto-downgrade to `research_probe`; discard their hardwired entry families |
| 13 | **Signal postmortem feedback loop** (TRUE_POS/FALSE_POS/MISSED/REGIME_MISMATCH; regime-at-signal vs regime-at-exit; ≥20-sample floor before any weight change) | claude-trading-skills | conviction (`conviction-features`) / research-discipline | **ADOPTED** — spec for the Phase-5 conviction feedback loop; ≥20-floor matches our WR<45%-over-20 binomial math |
| 14 | **Position-sizing constraint hygiene** (strictest-constraint-wins across risk%/max-pos%/sector%/ADV%; round DOWN; portfolio heat ≤6-8%; half-Kelly never full) | claude-trading-skills | conviction / indian-exec | **ADOPTED (acceptance test)** — the Phase-6 sizing overlay must pass this checklist |
| 15 | **Corporate-action taxonomy + OHLCV adjustment mechanics** (split = multiply hist prices; spin-off/demerger = NSE-published parent/child ratio, NOT inferred from price drop; cash-merger = delist) | finance_skills | data-quality | **ADOPTED** — this is the **VEDL demerger-as-split bug fix spec** (slope fabricated 2.16→24.94) |
| 16 | **Ex-date mechanics under T+1** (post-2023 ex-date = record-date, not −1; yfinance may carry T+2) | finance_skills | data-quality | **CANDIDATE** — add as a flag (not auto-correct) to `dv_ohlcv_integrity.py` |
| 17 | **Six-dimension data-quality framework** (Accuracy/Completeness/Timeliness/Consistency/Validity/Uniqueness with numeric targets) | finance_skills | data-quality | **ADOPTED (scaffold)** — maps directly to OHLCV CI gates; hard-gate Accuracy+Validity, soft-gate Consistency |
| 18 | **Variance-threshold price validation** (flag >15% DoD, quarantine >50% w/o CA, quarantine ≤0 price, flag >5-day-unchanged liquid) | finance_skills | data-quality | **ADOPTED** — concrete `dv_ohlcv_integrity.py` rules; NSE circuit limits (20/10/5%) frame the thresholds |
| 19 | **Data-lineage trace for anomalous slope** (raw → split-heal → CA → SMA; cross-check implied vs announced ratio) | finance_skills | data-quality | **ADOPTED** — turns the ad-hoc VEDL catch into a repeatable diagnostic protocol |
| 20 | **Survivorship / PIT-database requirement** (current-listings-only inflates returns; PIT mandatory for price AND fundamentals) | finance_skills | data-quality | **REFERENCE (mandatory framing)** — authoritative backing for our open PIT-membership/delisted-OHLCV fix; absolute CAGR stays caveated until fixed |
| 21 | **Adjusted vs unadjusted price discipline** (features use close_adj; execution uses close_raw) | finance_skills | data-quality | **ADOPTED** — assert entry/stop/target source from raw (live) price, slope from adjusted |
| 22 | **Exception severity tiers** (Critical/High/Medium/Low; quarantine one ticker, don't abort the scan) | finance_skills | data-quality | **CANDIDATE** — per-ticker exception handling in `long_horizon_cron` so the scan completes on a partial universe |
| 23 | **Golden-source hierarchy + CA events register** (yfinance primary → NSE bhavcopy → manual override w/ expiry; CA ratios from NSE/BSE circulars not yfinance) | finance_skills | data-quality | **CANDIDATE** — the structural fix that would have caught VEDL via a second source |
| 24 | **Compliance-safe language vocabulary** ("model-generated signal", required disclosures incl. "never traded real capital", "~40% historical DD") | finance_skills | conviction / operating-model | **ADOPTED** — reinforces existing CLAUDE.md Security rule with exact product copy |
| 25 | **Three-component backtest separation** (SignalGenerator → PortfolioManager → PerformanceAnalyzer; swappable SizingPolicy) | scientiacapital | harness (`overlay-testing` Step 2) | **ADOPTED (refactor target)** — names the right boundary for the Phase-4 `SizingPolicy` interface |
| 26 | **Walk-forward as the only trustworthy mode** (100-trade/fold underpowered flag; "if it only works in-sample, walk-forward exposes it") | scientiacapital | harness | **ADOPTED** — already enforced; adopt the framing + underpowered-flag for harness docs |
| 27 | **Drawdown-escalation ladder** (graduated 3/5/8% breaker + 25/50/75/100% recovery ramp) | scientiacapital | conviction / regime | **CANDIDATE** — graduated MAX_POSITIONS reduction fits the 63d hold better than a binary halt; re-calibrate for −40% book |
| 28 | **Half-Kelly with hard cap — documented rationale** (~75% growth at ~50% DD; estimation error justifies it) | scientiacapital | conviction (`conviction-features`) | **ADOPTED** — document in `position_sizer.py` so nobody "fixes" it to full Kelly |
| 29 | **Regime-aware backtesting** (test WITHIN each regime separately; report per-regime Sharpe per fold) | scientiacapital | regime (`regime-classification`) / harness | **ADOPTED** — per-regime fold reporting; this is a measurement, NOT a regime entry gate (see §4) |
| 30 | **India VIX size-scaling** (^INDIAVIX > pctile → size multiplier 1.0/0.5/0.0) | scientiacapital | regime | **CANDIDATE** — pre-registerable; size-scaling (not entry gate); calibrate on India-VIX percentile, not US-35 |
| 31 | **Contract-first feature definition** (IN/OUT scope, success checkboxes, observer checkpoints) | scientiacapital | research-discipline (`research-log`) | **ADOPTED** — extends our pre-reg template with explicit OUT-OF-SCOPE + observer checkpoints |
| 32 | **Builder + Observer dual-agent for harness PRs** (adversarial observer checks lookahead + live/backtest parity; BLOCKER findings block merge) | scientiacapital | harness / research-discipline | **CANDIDATE** — would have caught AUD-002/AUD-020/ensemble-order bugs; spin a 2nd worktree agent on complex harness PRs |
| 33 | **Treat code YOU wrote with more skepticism** (4-question reproducibility checklist before any KILL/ADOPT verdict) | scientiacapital | research-discipline | **ADOPTED** — add to the verdict protocol; our best catches (AUD-023, 0011 gate) came from exactly this |
| 34 | **Relative-strength rank as alt cross-sectional signal** (stock 63d return / Nifty-500 63d return) | scientiacapital | conviction | **CANDIDATE (robustness check)** — does RS-rank produce walk-forward Sharpe within 0.10 of `sma200_slope_63`? validates mechanism or upgrades it |
| 35 | **Plan-before-build: strategy spec + clarifying questions FIRST** | Medium 900h | research-discipline (`research-log`) | **ADOPTED** — open a preregistry file BEFORE touching any `src/` file |
| 36 | **Tight function contracts in prompts** (name, input schema, output column+semantics, boundary conditions = the test assertion) | Medium 900h | harness (`overlay-testing` Step 2) | **ADOPTED** — standard harness contract block; the contract becomes the invariant test |
| 37 | **CLAUDE.md quant invariants** (data quirks + promotion bar as a per-session section) | Medium 900h | data-quality / operating-model | **CANDIDATE** — add known landmines (VEDL, ~16 F5 glitch names, survivor-only pre-2015, PIT-filter-before-rank) + the bar to CLAUDE.md |
| 38 | **Live-source debugging over cached-CSV** (fetch suspect ticker fresh from yfinance, cross-check around CA date) | Medium 900h | data-quality | **ADOPTED** — required step in any data-integrity diagnostic (VEDL was a cache artifact) |
| 39 | **Walk-forward fold parametrization & independence check** (train_len/test_len/no-overlap; re-derive from scratch on train slice; leakage spike check) | medium_161skills | harness / data-quality | **ADOPTED** — codifies best-practice parametrization; matches AUD-021/AUD-003 audit findings |
| 40 | **Feature-importance auditing** (LightGBM gain + permutation ablation ΔSharpe + SHAP + per-cohort) | medium_161skills | conviction (`conviction-features`) | **ADOPTED (Phase-5)** — permutation+SHAP is the next rigor tier; would have caught the 5/10 dead-constant sector features |
| 41 | **Bootstrap-CI gating** (1000× resample; CI-low>0 STRONG / straddle INCONCLUSIVE / mid<0 KILL) | medium_161skills | data-quality / conviction / harness | **ADOPTED** — confirms our current practice (0026 sweep-override CI verdict) is well-calibrated |
| 42 | **Agentic architecture** (Master orchestrator + isolated Scanner/Risk/Exit/Journal subagents + kill-switch + heartbeat) | medium_161skills | harness / research-discipline | **REFERENCE** — nice-to-have production governance AFTER paper validation; not blocking research |
| 43 | **Finer NSE regime classification** (Quiet/GrindUp/Whipsaw/Pre-RBI/Monsoon/FII-flow → per-regime SIZE/EXIT rules) | medium_161skills | regime | **CANDIDATE (sizing/exit only)** — regime×state is predictive for RISK not return-alpha (0025b/0039); modulate size/stops, NOT entry |

### REJECTED — distractions and KILL-colliders (do not port)

| Rejected item | Source(s) | Why rejected |
|---|---|---|
| All intraday execution alpha (TWAP/VWAP/iceberg, NSE intraday seasonality, stop-hunt, expiry-day slicing) | algo_ai_skill, claude-ts | We are EOD daily-rebalanced delivery — no intraday slicing. The sqrt impact-cost fragment we already have via capacity-aware execution. |
| All F&O / options machinery (greeks, calendar spreads, max-pain, PCR, gamma, rollover/OI) | algo_ai_skill, scientiacapital, claude-ts | Cash-delivery equity only. Revisit ONLY if the vol-carry sleeve arc resumes. |
| Sentiment "data-edge" as alpha (FII/DII buy-sell, PCR-contrarian, delivery-%, bulk-deals, GIFT-Nifty gap) | algo_ai_skill | **Collides with KILLs:** FII/DII DEMOTED to regime-only; delivery-% (0010) INCONCLUSIVE/KILL. Presented as edge with zero validation = the thin-evidence hype our filter rejects. Keep only as a "what data exists" catalogue. |
| **HMM / regime as a LIVE ENTRY GATE** (gate if regime-prob<0.7, switch momentum/MR/flat) | algo_ai_skill, claude-ts, medium_161 | **§11 KILL: market-regime / dual-momentum gate** — cuts CAGR, sidelines the best bull years (India bull momentum *is* beta). Regime-CONDITIONAL backtesting (#29) is fine; regime-as-entry-gate is a known KILL. |
| **RSI / MACD / ROC / mean-reversion reversal signals** | algo_ai_skill, claude-ts, scientiacapital, medium_161 | **§11 KILL:** all short-term reversal/RSI/MACD/ROC/acceleration signals (Sharpe <0.5, DD −60 to −81%). Any source pitching these as edge is a red flag. |
| **Sector rotation / sector-selection as entry feature** | claude-ts, medium_161 | **§11 KILL:** sector-residual / sector-selection overlays hurt lean years; sector IC ≈ 0; 6/10 sector feats are dead constants. Sector is useful for RISK/SIZING context only, never alpha (re-opens only at sector IC > 0.05 on a 2022+ sub-period). |
| TA family (price-action, candlesticks, chart patterns, volume profile, Elliott/Fib/Wyckoff) | claude-ts, scientiacapital, medium_161 | **KILLed by 0004** chart-structure feature validation (don't improve OOS). Do not resurrect under different packaging. |
| Their weak promotion thresholds (Sharpe>1.0, DD<20%, >50 trades, CAGR>30% as a pass) | algo_ai_skill, claude-ts | Strictly weaker than our bar. Use the checklist STRUCTURE, never their numeric bars. |
| US advisory/compliance/CRM/broker-dealer skills (Reg-BI, GIPS, Form-ADV/PF/13F, KYC/AML, ACAT, FIX/co-lo, Reg-T margin, settlement) | finance_skills | US regulatory context; SEBI/FIU/DPDP govern us. Only the suitability *vocabulary* (#24) transfers. |
| CRM / GTM / sales automation (38+ skills) + crypto/Bitcoin Markov + LLM-infra (NautilusTrader/LangGraph/Unsloth) + IBKR/forex/COT | scientiacapital, claude-ts | Wrong domain entirely; zero quant-methodology transfer. |
| `data-quality-checker` (validates BLOG documents, not OHLCV) | claude-ts | Despite the name, it checks market-analysis prose (digit counts, US-holiday mismatches), NOT OHLCV/PIT/corporate-action integrity. Build ours from scratch (#15–23); only the digit-scale heuristic is a scrap. |
| Broker-specific SDK details (Rupeezy/Vortex enum-typecheck, OrderTracker postback, loopback OAuth) | algo_ai_skill | Broker-specific; we use Kite, concepts already covered. |
| LSTM/RL/swarm-LLM-voting for signals; pairs/cointegration; earnings-momentum | scientiacapital, medium_161 | Underperform our simpler rank+slope, add lookahead-bug surface, or are separate-strategy questions with skeptical priors — defer, do not import. |

---

## 3. The TOP borrowed methods we actually adopt — and why

These are the highest-value imports. Each is grounded in a specific failure or gap we have.

### 3.1 Indian cost/tax audit of our backtester (algo_ai_skill #1, #7) — **highest-stakes**
The source's FY25-26 table states delivery **STT 0.1% is "paid on both buy and sell"**
(`indian-market.md:149`, verified). Our config applies `STT_PCT = 0.1%` **sell-side only**. If the
source is right, every backtest understates round-trip friction by ~0.1% per trade — and our
promotion bar is **post-tax post-cost**, so this directly moves the load-bearing delta. The table
also lists exchange-txn (0.002-0.006%), SEBI (0.0001-0.0002%), and stamp-duty items we may omit.
**Action:** an audit (a measurement, 0 trials) to reconcile our cost model against this table and
to confirm the backtester applies STCG at 20.8% incl 4% cess. Do this BEFORE trusting any new
overlay's post-tax delta. This is not an overlay — it is a correctness check on the yardstick.

### 3.2 Corporate-action taxonomy = the VEDL bug-fix spec (finance_skills #15, #19, #21, #23)
We have a confirmed bug where yfinance treated VEDL's **demerger as a split**, fabricating
`sma200_slope_63` from 2.16 → 24.94. The taxonomy says exactly why: a spin-off requires the
**NSE-published parent/child allocation ratio**; yfinance instead infers an adjustment factor from
the price drop, which is wrong for spin-offs. The fix spec is concrete: cross-check large single-day
moves (>30%) against NSE corporate-action announcements, maintain a CA events register
(ticker/date/type/factor/source), enforce features-use-adjusted / execution-uses-raw, and run the
data-lineage trace (raw → split-heal → CA → SMA, compare implied vs announced ratio) on any slope
flagged >2 SD from the cross-sectional distribution. This is the single highest-leverage data-quality
import because it both fixed a live bug class and gives us the recurring diagnostic for a 500-stock book.

### 3.3 The pre-harness trust gate (claude-trading-skills #9, #10, #11)
Three layers, run in order, BEFORE spending harness compute on a hypothesis: (a) the **red-flag
checklist** (>2-3 unchecked boxes = not ready — its survivorship + corporate-action boxes are the
ones we failed); (b) the **C1–C8 review gate** with overfit tripwires (any decimal-precision
threshold = penalty, ≥12 conditions = fail, no explainable mechanism = instant REJECT); (c) the
**5-dimension verdict scorer** structure (per-dim subscore + red-flag list + single stamp), keeping
its DD≥50%→0 override and too-good (WR>90% & DD<5%) flag but **replacing its US-swing numeric
cutoffs with our promotion bar**. This operationalizes "mechanism explainable in one sentence" as a
hard short-circuit and saves harness runs on ideas that were never going to pass.

### 3.4 The conviction feedback loop (claude-trading-skills #13 + medium_161 #40)
The Phase-5 conviction model needs honestly-attributed labels. Adopt the postmortem taxonomy
(TRUE_POS / FALSE_POS / MISSED / REGIME_MISMATCH), record **regime-at-signal vs regime-at-exit** to
separate skill failure from regime shift, and refuse any weight change below **20 samples** (matches
our own WR<45%-over-20-trades binomial rollback math). Pair it with feature-importance auditing
(gain → permutation-ΔSharpe → SHAP → per-cohort) as the next rigor tier — the same audit that would
have flagged the 5/10 dead-constant sector features earlier.

### 3.5 Harness architecture + provenance (scientiacapital #25, #31, #33 + claude-ts #12)
The Phase-4 harness boundary is named for us: **SignalGenerator → PortfolioManager →
PerformanceAnalyzer with a swappable SizingPolicy** — so conviction-driven sizing can be tested
without rewriting portfolio logic. Wrap it in the bounded review-loop + **run-manifest** discipline
(every hypothesis leaves a manifest; unresolved candidates auto-downgrade to `research_probe`, never
silently shipped) and the contract-first pre-reg (explicit OUT-OF-SCOPE + observer checkpoints). Gate
every verdict behind the 4-question self-skepticism checklist (reproducible? harness unchanged between
control/candidate? read the metric code? simpler explanation ruled out?) — our best catches all came
from exactly that posture.

### 3.6 Sizing discipline, documented (claude-ts #14 + scientiacapital #28)
The Phase-6 sizing overlay's acceptance test: strictest-constraint-wins across
risk%/max-position%/sector%/5%-ADV, round shares DOWN, cap total open portfolio heat at 6-8%, default
1% risk never >2%, **half-Kelly never full** — and document the half-Kelly rationale in
`position_sizer.py` (~75% growth at ~50% DD; estimation error makes full Kelly overbet) so nobody
"fixes" it later. Note: our −40% baseline DD means sizing alone can't cut the drawdown much (the cap
binds, per STRATEGY.md caveat 1) — the sizing overlay must prove it adds on top of the already-shipped
vol-target overlay, not compete on the same axis.

---

## 4. What we explicitly REJECT — and why (the KILL-colliders)

Three families of borrowed "edges" recur across the sources and **directly contradict our
pre-registered, validated KILLs** (`long_horizon/STRATEGY_FULL.md §11`,
`skills/overlay-testing` Step "what NOT to test"). Treat any nudge toward them as a **known-false
prior** — they do not get a fresh trial without extraordinary new evidence.

1. **Regime as a live entry gate** (algo_ai_skill HMM-gate, claude-ts macro-regime-detector,
   medium_161 kill-switch-on-regime). **§11 KILL:** the market-regime / dual-momentum gate cuts CAGR
   and sidelines the best bull years — *India bull momentum is beta*, and the regime gate that would
   cut the −40% DD also kills the return. Regime-**conditional backtesting** (#29) and regime-driven
   **sizing/exit modulation** (#30, #43) are allowed; regime-as-entry-gate is not.

2. **Sector rotation / sector-selection as an entry feature** (claude-ts sector-analyst/theme-detector,
   medium_161 sector-rotation). **§11 KILL:** sector-residual and sector-selection overlays hurt lean
   years, sector IC ≈ 0, and 6/10 sector features are dead constants with pick-tilt ρ≈0. The lean-years
   overlay test HURT all three lean years. Sector is a RISK/SIZING context input only. Re-opens only on
   sustained sector IC > 0.05 on a 2022+ sub-period.

3. **RSI / MACD / ROC / mean-reversion reversal signals** (every source ships these; medium_161 and
   scientiacapital pitch them as edge). **§11 KILL:** all short-term reversal/RSI/MACD/ROC/acceleration
   signals scored Sharpe <0.5 with −60 to −81% DD. **0004** also KILLed chart-structure features
   (don't improve OOS) and **0025b** confirmed model-caution is protective. A source recommending these
   as edge is a credibility red flag for that source's quant judgment, not a hypothesis to test.

We also reject all weaker promotion bars (use the checklist structure, never the numbers), the entire
US-advisory/CRM/options/crypto/LLM-infra long tail, and `data-quality-checker` (it validates blog prose,
not OHLCV). The PIT-survivorship caveat (#20) is kept as mandatory framing, not a trial: absolute CAGR
numbers stay caveated until PIT membership + delisted OHLCV are fixed.

---

## 5. Cross-references

- **Promotion bar + full overlay protocol:** `skills/overlay-testing/SKILL.md`
- **Exit / rotate overlays + the exact bar source:** `skills/sell-replace-logic/SKILL.md`
- **Conviction model + feedback loop + feature audit:** `skills/conviction-features/SKILL.md`
- **Regime classification (conditional/sizing, NOT entry gate):** `skills/regime-classification/SKILL.md`
- **Kite / Indian execution realism (tick, circuit, costs):** `skills/kite-execution/SKILL.md`
- **Pre-registration + verdict discipline:** `skills/research-log/SKILL.md`
- **The KILL ledger (the §11 we do not relitigate):** `long_horizon/STRATEGY_FULL.md §11`,
  summarized in `long_horizon/STRATEGY.md`
- **Baseline_v0 of record:** `research/baseline_v0.json`
  (26.1% gross CAGR / 1.02 Sharpe / −41.9% DD / 0.62 Calmar; after-tax 23.1% / 0.83 —
  supersedes the optimistic-exit 30.26%/1.15 measurement, 2026-06-27; never anchor on the 34.67% re-derived variant)
- **Ingested source digests (provenance):** `skills/_ingested/`

**Attribution.** Borrowed methods above are adapted (not copied) from: `algo_ai_skill`
(indian-algo-trading, Apache-2.0, v1.1.14); `claude-trading-skills` (TraderMonty, MIT ©2026);
`finance_skills` (MIT); `scientiacapital/skills`; and two Medium articles
("900+ Hours of Using Claude Code for Trading", AI in Trading, 2026-03-13; and the 161-skill
catalogue, `medium_161skills.md`). We ported concepts and checklists, not verbatim code or text,
in keeping with each source's license.
