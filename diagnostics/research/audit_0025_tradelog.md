# Forensic trade-level audit — 0025 strategy of record (practitioner book, 4×ATR, corrected universe, NET)

**2026-07-03. Tool:** `scripts/audit_trade_ledger.py` (ledger instrumentation is observation-only —
reconciles finding 0025 exactly: net Sharpe +0.397 / CAGR +2.82% / DD −12.1% / 194 trades).
Ledger: `research/exports/bhanushali_0025_tradelog.csv` (194 rows, one per trade, entry-condition
snapshot through exit fill).

## What PASSED (integrity)
- **Timing/lookahead:** entry strictly after signal in 194/194; order life ≤3d respected
  (fills: 156 next-day, 21 day-2, 17 day-3); every fill ≥ trigger; max gap at fill +1.28% (cap 1.5%).
- **Sizing:** median realized risk **exactly 2.00%** (the 0025 deployment fix, verified per-trade);
  median notional 12.4%, median ADV ₹86cr.
- **Costs reconcile:** gross 4.15% − net 2.82% = 1.33%/yr friction ≈ ~531%/yr two-leg notional turnover
  × tiered slippage (37% of trades in the MID tier).
- **Engine mix:** 171 B (pullback) / 23 A (RSI) — matches everything the arc measured.

## What the audit FOUND
1. **A bad-tick erratum in the PINNED cache (new, material to the record).** Cache-wide scan for
   >60%-move-fully-reversed bars: exactly **2 hits, both INDIAMART Diwali-Muhurat sessions**
   (2019-10-27 +104%→−51%; 2020-11-14 +99%→−51%; yfinance doubles that name's Muhurat bar).
   **One 0025 trade transacted on the phantom:** entered 2020-11-09, the engine "sold half at ₹3,092"
   on 2020-11-14 — a price that never traded (real range ~2,330–2,360). Booked R +1.0 is phantom.
   **Sensitivity with the 2 bars dropped: net Sharpe +0.393 / CAGR +2.55% (record: +0.397 / +2.82%).**
   Verdict unchanged (already below the 0.40 bar) but the honest CAGR is ~2.55%.
   **Baseline exposure:** baseline_v1's tradelog holds INDIAMART 2020-09-17→2020-11-17 with a target
   exit — plausibly fired by the phantom high; single small trade, negligible to 0.667, but the anchor's
   dataset carries the same 2 bad bars. **Fix routes to the next dataset pin** (bad-tick reversal screen
   + Muhurat-bar validation in the pin builder), never to the frozen f8625a8f.
2. **Gap-through stop optimism quantified:** 15/192 stop exits (8%) had the exit-day open already below
   the stop; filling those at the open instead costs ~₹28.4k on 10L (~0.3%/yr). Known engine optimism,
   now measured — small.
3. **Concentration (fragility disclosure):** top-3 names = **52% of total P&L** (HINDCOPPER, ADANIGREEN,
   PFC) — above the 30% rigor threshold. Inherent to a 40%-win trail book whose profit is the 3–4R tail
   (median R −0.09, p90 +0.98), but the result is rocket-dependent and jackknife-fragile.
4. **The half-book leg is nearly dead under 4×ATR geometry:** stops sit 15–26% away → +2R = a 30–50%
   move → only **8% of trades ever book half**. The scaling-out design (owner's choice at 0024) is
   effectively inert in the 0025 geometry; the book is a pure trail book in practice.
5. **Watchlist-rank puzzle:** median entry rank 28; 56% of fills come from rank >25. The strongest-trend
   names rarely produce pullback fills (they're extended, not at the MA) — the slope-heavy ranking is
   partially anti-selecting fill-eligible setups.
6. **Weak cells:** 2024 is the worst year (32 trades, −₹59k); 2017-18 flat (+0.01) as recorded.
   Bootstrap CI on net Sharpe [−0.22, +0.94] includes 0 — standalone uncertifiable, as recorded.
7. Backfill/alias-sourced names: 17 trades, net P&L share −7% (the corrected universe names drag, as
   survivorship theory predicts). Zero-volume days inside holds: 4 trades (benign). No other CA suspects.

## Improvement register (discipline-labeled — nothing here was run/tuned)
| # | improvement | evidence | class |
|---|---|---|---|
| 1 | Fill gap-through stops at the OPEN (engine default) | §2, ~0.3%/yr | mechanical realism fix; pre-register as data-honesty change (direction DOWN) |
| 2 | Bad-tick screen + Muhurat validation in the next dataset-pin builder | §1 | data infrastructure (no trial) |
| 3 | Half-book geometry: +2R never fires under 4×ATR — candidates: half at +1R or fixed +12–15% | §4 | NEW TRIAL (n_trials) — owner decision at Oct-1; do NOT run casually |
| 4 | Watchlist rank axis: rank by setup-proximity rather than raw slope | §5 | NEW TRIAL — same discipline |
| 5 | Earnings-calendar avoidance | 0024 limitation, still open | blocked on PIT earnings-date data |
| 6 | Concentration disclosure in any forward-wall/psheet reporting | §3 | reporting rule, no code |

**Bottom line:** the engine is mechanically honest (timing, fills, sizing, costs all verified at trade
level); the dataset had exactly two phantom bars, one of which flattered the book by ~0.27pp CAGR — the
honest headline is **net Sharpe ~+0.39 / CAGR ~+2.6% / DD −12.1%**; and the two real structural findings
(inert half-book leg, rank/fill anti-selection) are logged as pre-registrable trials for the owner, not
tuned in place.
