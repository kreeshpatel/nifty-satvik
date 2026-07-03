# 0024 — Bhanushali run as a PRACTITIONER runs it: overtrading solved, drawdown tamed, but the method earns too little per unit of capital

- **Status:** MEASUREMENT / external-strategy analysis per pre-reg `diagnostics/research/preregistry/0024-bhanushali-practitioner.md`
  (params frozen before the run; no retuning). No n_trials cost, no cfg change.
- **Date:** 2026-07-03. Script `scripts/run_bhanushali_practitioner.py`, window 2017–2026, PIT membership,
  tiered real costs. Prompted by the owner's process audit: 0022/0023 tested the *mechanics* but skipped the
  *portfolio process* a real trader runs — the weekly frozen top-50 watchlist, the no-overtrade throttle,
  scaling out (half at 1:2 + swing-low trail), and the index regime check. Owner fixed the four open choices
  (watchlist rank = trend+volatility+volume; half@2R + §12 swing-low trail; NIFTY regime pause; 5 pos / 3
  new-wk / 10d cooldown).

## Result (headline = combined A+B on the weekly watchlist; CORRECTED after amendments 1+2)
> **Amendments (owner-caught).** The first run showed engine A firing 3 trades in 9.5y — an artifact:
> the watchlist demanded a strong DAILY trend, which is near-mutually-exclusive with daily RSI<35 (41 joint
> events in 1.4M ticker-days). Amendment 1 widened eligibility to strong-daily OR sustained-weekly; amendment
> 2 added an engine-A arm on its own weekly-slope-ranked list (only 7% of RSI signals survived the
> daily-slope rank contest). Numbers below are the corrected run.

| arm | tr/yr | win | expR | CAGR | Sharpe | MaxDD |
|---|---|---|---|---|---|---|
| **combined GROSS** | **21** | 40% | +0.17 | **+4.5%** | **+0.48** | **−19.4%** |
| **combined NET** | 21 | 40% | +0.17 | **+1.4%** | **+0.19** | −24.0% |
| B only (pullback), net | 19 | 41% | +0.22 | +2.2% | +0.27 | −23.0% |
| A only (RSI), mixed list, net | 3 | 43% | +0.13 | +0.0% | +0.03 | −6.6% |
| **A only, own weekly-ranked list, net** | **4** | **27%** | **−0.18** | −1.8% | **−0.49** | −19.5% |
| regime OFF, net | 40 | 38% | +0.11 | −1.7% | **−0.05** | −43.8% |
| volume-confirm OFF, net | 44 | 36% | +0.19 | +3.5% | +0.29 | **−38.5%** |
| throttle OFF, net | 21 | 40% | +0.19 | +1.8% | +0.22 | −23.0% (barely binds) |

Sub-periods (net, continuous slice): 2017-18 +0.42 / 2019-21 −0.26 / 2022-26 +0.45. Exit mix: essentially
all exits via (initial or trailed) stop; avg hold 11d — squarely his 3–10d rhythm.

## Root-cause readout (REQUIRED)
1. **The practitioner process WORKS as process.** Trades/yr collapsed 260→21 (the owner's no-overtrade goal),
   and MaxDD collapsed −92%→−19% gross. The watchlist + confluence is itself the throttle: the explicit
   5-pos/3-new cap barely binds (throttle-OFF is nearly identical). Overtrading was a *scanning-the-
   whole-market* artifact, exactly as the owner suspected.
2. **The regime pause is genuinely load-bearing** (his "mahaul", the owner's call): regime OFF flips net
   Sharpe +0.19→−0.05 and deepens DD to −44%. First Bhanushali component that *adds* net Sharpe outright.
3. **But the method cannot deploy capital.** Gross CAGR only +4.5% despite positive expectancy (+0.17R/trade),
   because: tight candle-low stops (~3–4%) want ~57% notional to reach 2% risk → the 30% notional cap and the
   no-leverage cash constraint cut realized risk to ~1%/trade; × 21 trades/yr ≈ a few %/yr. This is the honest
   ceiling of a 5-position tight-stop swing book without leverage. A real trader "earning 20%/yr" on this is
   either concentrated way beyond 30%/name or leveraged.
4. **Costs still eat most of it:** 4.5%→1.4% CAGR (~3%/yr drag on a volatile-midcap watchlist at 0.22%
   slippage). The method selects exactly the names with the highest slippage tier.
5. **Volume nuance (differs from 0023):** removing the HVC gate here raises net CAGR (+3.5%) but deepens DD
   to −38% and doubles the trade count — because the watchlist's volume-*expansion* ranking already
   pre-filters for institutional interest, the per-candle HVC gate acts mostly as drawdown control. In 0023
   (no watchlist) volume was the only institutional filter and removing it collapsed the system. Consistent
   story: *some* volume filter is load-bearing; where you apply it moves return↔DD.
6. **Engine A (RSI-35), correctly watchlisted, fires ~3–4 trades/yr and LOSES.** On its own weekly-ranked
   list (his actual RSI-system watchlist): 37 trades, 27% win, expR −0.18, Sharpe −0.49. A credible human
   cadence (~one trade a quarter from that system), and the same verdict as 0020/0022: the RSI-oversold
   *entry* is the part of his teaching with no edge — buying the dip loses even inside a weekly uptrend
   with green-candle + volume confirmation. Every edge in the arc lives in engine B (momentum pullback).

## Follow-up diagnostics (reviewer checks, `scripts/diag_rsi_recovery.py`, 2,616 engine-A signals)
1. **Weekly-filter lookahead: CLEAN.** Truncation test, 50 random (ticker,date) pairs: weekly trend/slope at
   date d byte-identical whether or not future bars exist. Mon–Thu days read the prior completed W-FRI bar;
   a Friday signal reads the bar completing at its own close — available at decision time.
2. **The weekly filter is SLOWING THE BLEED, not selecting resilience.** From the signal close, forward
   returns trail the universe control at every horizon (−0.4 to −0.8pp at 5–60d). 96% do reclaim the daily
   44-SMA within 60d (median 15d) — but the median path first suffers a **−6.6% MAE within 20d (p10 −17.4%)**,
   which a 2–4% candle-low stop cannot survive. That is the mechanical reason the portfolio arm loses.
3. **The buy-above-high trigger carries the RSI system's ENTIRE edge.** 68% of signals trigger within 3d;
   17% hit the stop level first (knives the trigger correctly refuses). Triggered vs not-triggered forward
   returns: **+4.8 to +6.0pp** separation — and the triggered subset *beats* the universe (+1.0pp/10d),
   while the raw signal underperforms it. His confirmation-entry mechanic is real alpha; the RSI-oversold
   condition itself is anti-alpha. (Consistent with the program-wide lesson: confirmation/momentum works,
   dip-buying does not.)
4. **Capital interaction (explicit decision):** the combined book holds max one position and one pending
   order per ticker across engines, shares the 5-slot capital FCFS, and the cooldown applies across engines
   — a name exiting a B position cannot immediately re-enter via A. Since A is net-negative as a system, the
   practical combined book is B-only (+0.27 net); A stays a documented, excluded arm.

## Verdict
**The practitioner process rescues the strategy's RISK profile, not its RETURN.** Run the way a disciplined
human runs it, Bhanushali's method is a real, low-drawdown (−19%), low-turnover (21/yr) system with positive
per-trade expectancy — and a gross return of ~4.5%/yr that costs cut to ~1.4%/yr net: roughly FD-yield with
equity effort. It is decisively below baseline_v1 (0.667 Sharpe / 15.5% CAGR) on every axis except drawdown. The
durable extracts stand: **regime pause (new, net-positive here), volume as DD-control, watchlist-as-throttle.**
Survivor-only cache (sha f8625a8f, 103 delisted members missing) makes even these numbers optimistic.
Disposition: arc closed for the config; principles feed the forward-only conviction/feature work.
