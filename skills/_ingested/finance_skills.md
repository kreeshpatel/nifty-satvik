# Ingested Digest: finance_skills

**Source:** `finance_skills` skill library (MIT license), 7 plugins, 84 skills.
**Ingested:** 2026-06-27
**Curator:** NiftyQuant long-horizon maintainer
**Credibility:** High for operational/institutional process detail; not directly applicable to Indian regulatory context (all examples are US-centric — SEBI/NSE rules govern us).

---

## One-paragraph summary

`finance_skills` is a comprehensive institutional operations skill library aimed at US broker-dealers and RIAs. The majority — advisory-practice, client-onboarding, account-opening-workflow, account-transfers, AML/KYC, fee-disclosure, GIPS, Reg-BI, suitability, sales-practices, wealth-management, billing — is irrelevant to a quant research engine. Four clusters are directly actionable: (1) **corporate-actions** maps precisely onto our open VEDL demerger-as-split bug and provides a rigorous multi-event taxonomy and ex-date/record-date mechanics checklist; (2) **data-quality** gives a six-dimension framework (accuracy, completeness, timeliness, consistency, validity, uniqueness) and concrete validation-rule patterns that port directly into our OHLCV integrity CI; (3) **data-integration/market-data** covers survivorship bias, adjusted-vs-unadjusted price pitfalls, and point-in-time database requirements — all live problems for us; (4) **compliance language** (client-disclosures + investment-suitability) provides the precise safe-language vocabulary ("model-generated signal", "decision-support output", "research recommendation") a paid signal product requires. Nothing contradicts our validated KILLs. Nothing introduces new alpha hypotheses — it is process and data infrastructure, not signal methodology.

---

## High-value patterns

| # | Name | Source skill | Why relevant to NiftyQuant | Port target |
|---|---|---|---|---|
| 1 | Corporate action taxonomy + adjustment checklist | `corporate-actions` | We have an open VEDL demerger-as-split bug; the taxonomy clarifies exactly which events require what OHLCV adjustments and when the ex-date fires under T+1 | data-quality / harness |
| 2 | Ex-date / record-date under T+1 settlement | `corporate-actions` §3 | NSE moved to T+1 settlement in Jan 2023. Under T+1 ex-date = record date (not record-date minus 1 as under T+2). yfinance prices often carry wrong ex-date conventions; this is a lurking data error in slope features | data-quality |
| 3 | Split-adjustment cost-basis invariant | `corporate-actions` §5, §7 | The invariant "total cost basis is unchanged; only per-share price changes" is the same invariant that must hold on adjusted OHLCV: total return must be unchanged across split events. Our split-heal routine in `data/ohlcv_incremental.py` should be validated against this | data-quality / harness |
| 4 | Spin-off basis allocation (Form 8937 ratio) | `corporate-actions` §5 | Demergers (VEDL→Hindustan Zinc spin-off style) require a published parent/child allocation ratio to correctly adjust historical prices. yfinance does NOT automatically apply demerger adjustments — it treats them as splits. We must source the NSE corporate action ratio and apply it manually | data-quality |
| 5 | Six data-quality dimensions with measurement method + target | `data-quality` §1 | Gives a structured rubric (Accuracy/Completeness/Timeliness/Consistency/Validity/Uniqueness) with concrete financial-data targets (>99.5% pricing accuracy, <0.1% duplicate rate). Ports directly as the acceptance criteria for our OHLCV integrity CI gate | data-quality / harness |
| 6 | OHLCV validation-rule taxonomy | `data-quality` §4 | Specific rules: zero-price detection, negative-price detection, stale-price detection (unchanged beyond expected window adjusted for holidays), cross-vendor comparison, settlement-date follows trade-date by correct cycle. All apply directly to our `dv_ohlcv_integrity.py` | data-quality |
| 7 | Variance-threshold price validation | `data-quality` §4 | Flag equity price moves exceeding 15% day-on-day as candidate errors (to be investigated, not auto-dropped). Bonds 5%, high-yield 10%. This is the right calibration: 15% catches most data errors while surviving genuine large-cap circuit-breaker events | data-quality / harness |
| 8 | Survivorship bias and point-in-time database requirement | `market-data` §7, `data-quality` §1 | "Databases including only current listings inflate backtested returns. Point-in-time databases showing the universe as it existed historically are required for unbiased research." This is identical to our open data-foundation problem (PIT membership + delisted OHLCV). Provides authoritative framing for why the fix is mandatory | data-quality |
| 9 | Adjusted vs unadjusted price — when to use which | `market-data` §7 | "Unadjusted for trade-level analysis and regulatory records. Split-adjusted and fully adjusted (splits + dividends) for return calculations." We must ensure slope features use fully-adjusted prices while execution uses unadjusted (close) price for entry/stop computation | data-quality / harness |
| 10 | Data lineage — trace any output to its source transformation | `data-quality` §3 | Lineage enables root-cause analysis when a signal value looks wrong. Applied to us: `sma200_slope_63` for any stock must be traceable to: OHLCV source file → split-heal pass → corporate-action adjustment → SMA computation. This is the diagnostic checklist we need when we see a fabricated slope like VEDL 2.16→24.94 | data-quality / harness |
| 11 | Exception management: severity tiers + MTTR targets | `data-quality` §6 | Critical (block pipeline) / High (same-day) / Medium (3-5d) / Low (maintenance cycle). Applied to our harness: a zero-adjusted-close or demerger-unhandled event is Critical (halt the cron); a >15% single-day move is High (quarantine + inspect); minor rounding is Low | data-quality / harness |
| 12 | Golden-source hierarchy for pricing | `reference-data` §5 | Define preferred source per security type with automatic fallback and documented override log. For us: yfinance close is the primary source; NSE bhavcopy is the fallback/cross-check; manual overrides require documented reason + expiry date | data-quality |
| 13 | Compliance-safe language for a paid signal product | `client-disclosures` §1, `investment-suitability` | "Model-generated signal", "research recommendation", "decision-support output" — never guarantee outcomes. Suitability obligations require disclosing that recommendations may not suit every investor's risk profile. We already follow this (CLAUDE.md line) but the explicit vocabulary from a licensed framework reinforces it | conviction / research-discipline |

---

## Distilled portable content

### Pattern 1 — Corporate action taxonomy for OHLCV adjustment

Events requiring OHLCV price adjustment (backward-adjust historical series):
- **Stock split / bonus share**: multiply historical prices by 1/ratio; multiply historical volumes by ratio; total return unchanged.
- **Reverse split**: multiply historical prices by ratio; divide volumes.
- **Demerger / spin-off**: apply parent/child allocation ratio (published by company, equivalent to Form 8937 in India = NSE circular or BSE filing). Historical parent price drops by the value transferred to the subsidiary; the subsidiary's pre-demerger history is notional. yfinance does NOT apply demerger ratios — it treats the price drop as a split, fabricating the denominator. **Mitigation**: cross-check large single-day price moves (>30%) against NSE corporate action announcements; if a "split" coincides with a known demerger, source the ratio manually and recompute.
- **Cash dividend**: for total-return series, add dividend back to pre-ex-date prices. For price-only series, no adjustment needed (standard for momentum signals — dividends are not part of the price trend).
- **Rights offering**: adjust pre-record-date prices by the theoretical ex-rights price (TERP) ratio if the right has a significant discount.
- **Merger (cash acquisition)**: security delists; remove from universe on effective date; do NOT carry the acquirer's history forward as a replacement.
- **Name/ticker change only**: no price adjustment; update the identifier mapping.

**Ex-date convention under NSE T+1 (effective Jan 2023):**
- ex-date = record date (not record-date − 1 as it was under T+2).
- Trades executed on the ex-date settle the next business day, so the buyer is not a holder of record.
- yfinance ex-dividend dates may still carry T+2 convention for older events — validate against NSE announcements for events after January 2023.

**Validation checklist for each corporate action in OHLCV:**
1. Does the adjusted close on the day before ex-date match close × (1 / adjustment_factor) within 0.1%?
2. Is volume on ex-date within 3× the 20-day average (a 10× spike often signals a data anomaly, not a real trade)?
3. Does the sum of adjusted closes across a 5-day window around the event produce the same total return as the unadjusted closes (adjusted for the known event ratio)?
4. For demergers: does the price drop on ex-date equal the known allocation ratio × subsidiary NAV?

### Pattern 2 — Six-dimension OHLCV data quality framework

Apply these dimensions as acceptance gates in `dv_ohlcv_integrity.py` and CI:

| Dimension | OHLCV application | Hard gate? |
|---|---|---|
| **Accuracy** | Adjusted close within 15% of prior day (flag >15% for CA review); cross-check vs secondary source on 1% random sample | Yes: >15% without CA annotation → quarantine |
| **Completeness** | All 5 OHLCV fields present; no NaN in adjusted_close for tradeable universe; ≥95% of expected trading days covered | Yes: missing adjusted_close → exclude from scan |
| **Timeliness** | OHLCV file arrives within 2h of NSE close (4:00 PM IST); slope features computed from data ≤1 trading day old | Yes: stale data → halt cron |
| **Consistency** | Same ticker's OHLCV from incremental-merge matches full-download recompute within 0.01% on adjusted close | Soft: flag for review |
| **Validity** | Open ≤ High; Low ≤ Close ≤ High; Volume > 0; Price > 0; adjusted_close > 0 | Yes: any violation → quarantine that ticker |
| **Uniqueness** | No duplicate date rows per ticker | Yes: deduplicate, log |

### Pattern 3 — Variance-threshold price validation (calibration)

Reference calibration from institutional practice (adapt for NSE):
- Flag (do not auto-drop) equity adjusted-close moves > **15% day-on-day** for manual CA review.
- Flag (auto-drop after logging) moves > **50% day-on-day** unless a confirmed corporate action annotation exists.
- Zero or negative adjusted-close → always quarantine.
- Unchanged price for > **5 consecutive trading days** for a liquid stock (ADV ≥ 5cr) → flag as stale feed.

NSE-specific: circuit limits are ±20% for most large-caps, ±10% for some, ±5% for some F&O names. A >20% single-day move with no CA annotation is almost certainly a data error.

### Pattern 4 — Data lineage diagnostic for fabricated slope detection

When `sma200_slope_63` for a ticker looks anomalous (e.g., VEDL 2.16→24.94), follow this trace:
1. Pull raw unadjusted OHLCV for the ticker (from the incremental cache).
2. Identify the adjustment events applied (split-heal log).
3. Check each event date against NSE corporate action announcements.
4. Compute the implied adjustment factor from the pre/post price ratio.
5. Cross-check the factor against the announced ratio.
6. If the factor does not match the announcement (demerger treated as split), recompute adjusted_close with the correct ratio.
7. Re-run slope computation on corrected series.

This is the minimum acceptable lineage trace for any ticker flagged as anomalous in CI.

### Pattern 5 — Compliance-safe language for NiftyQuant user-facing copy

Drawn from `client-disclosures` and `investment-suitability`:

**Mandatory language (already in CLAUDE.md, reinforced here):**
- Use: "model-generated signal", "research recommendation", "decision-support output"
- Never use: "guaranteed return", "will outperform", "certain profit"
- Disclose: past backtest performance does not guarantee future results; the strategy has never traded a live rupee (paper-only until explicitly stated otherwise).
- Disclose: signals are generated algorithmically and have not been reviewed by a SEBI-registered investment adviser on a per-user basis.
- Disclose: the service is a research tool; users are responsible for their own investment decisions.

**Suitability framing (apply to onboarding and dashboard copy):**
- The strategy is designed for investors with a 3-month+ investment horizon and tolerance for drawdowns up to −40%.
- Users with short-term liquidity needs, low risk tolerance, or no prior equity market experience should not rely on these signals without independent advice.
- Concentrated positions (top-15 stocks) create single-name risk; diversification across the full portfolio is the user's responsibility.

---

## Distractions — ignore these

| Skill / plugin | Why irrelevant |
|---|---|
| `advisory-practice` (all skills) | CRM, client onboarding, advisor compensation — pure advisory-practice ops, zero quant relevance |
| `account-opening-workflow` | Account opening forms, SIPC disclosure, customer agreement — US brokerage onboarding |
| `account-transfers` | ACAT transfers, DTC — US transfer mechanics; we use Kite |
| `account-maintenance` | Beneficiary updates, address changes, title changes — CRM operations |
| `anti-money-laundering` | FinCEN CIP/CDD rules — US AML; SEBI/FIU governs us instead |
| `know-your-customer` | US KYC framework — irrelevant |
| `fee-disclosure` | ADV Part 2, Form CRS fee schedule disclosure — US RIA; not our model |
| `gips-compliance` | GIPS composite construction — we don't claim GIPS |
| `reg-bi` | SEC Reg BI best-interest standard — US broker-dealer rule |
| `fiduciary-standards` | RIA fiduciary duty under US Advisers Act |
| `regulatory-reporting` | Form PF, 13F, IARD filings — US filings |
| `examination-readiness` | SEC/FINRA exam prep — US regulatory exams |
| `advertising-compliance` | SEC Rule 206(4)-1 marketing rule — US |
| `privacy-data-security` | Reg S-P, CCPA — US privacy law |
| `wealth-management` (all skills) | Tax planning, estate planning, retirement income — advisory, not quant |
| `counterparty-risk` | OTC derivatives, CSAs, SIMM — we are equity-only, long-only |
| `exchange-connectivity` | FIX protocol, co-location, SIP/direct feed architecture — HFT infrastructure we don't operate |
| `post-trade-compliance` | US post-trade reporting (OATS, CAT) — not applicable |
| `settlement-clearing` | DTC/NSCC/FICC mechanics — US settlement; NSE uses NSCCL under T+1 but the specifics differ enough that this skill doesn't port directly |
| `margin-operations` | Reg T, portfolio margin — US margin rules; Kite margin is governed by SEBI |
| `investment-suitability` | FINRA Rule 2111 three-prong suitability — US rule; useful only for the vocabulary and conceptual framing of what "suitability" means, not the specific regulatory obligations |
| `sales-practices` | Churning metrics, breakpoint abuse, FINRA Rule 3280 selling away — US brokerage sales rules |
| `pre-trade-compliance` | US hard/soft block architecture, Reg SHO short-sale rules — US rule framework |

### Specific patterns that contradict our validated KILLs or are out of scope

None of the relevant skills push RSI/MACD/reversal signals, regime-entry-gate overlays, or sector-selection overlays. The data and operations content is methodology-neutral. No conflicts with our kill list.

### What NOT to wire in from this source

- Do not treat the 15%-variance threshold as a hard auto-drop rule — it is a flag-for-review threshold. Our VEDL demerger needed investigation, not auto-drop.
- Do not apply US T+1 ex-date convention without verifying the NSE announcement date — NSE moved to T+1 in Jan 2023 but announcement dates for specific events must be sourced from NSE/BSE circulars, not inferred from the settlement cycle.
- Do not import US compliance regulations (Reg BI, FINRA Rule 2111, Form ADV) as binding obligations — they provide useful vocabulary and conceptual frameworks, but SEBI regulations govern NiftyQuant.

---

## License

`finance_skills` source library: MIT License. Adaptation and attribution required; no large verbatim reproduction.
