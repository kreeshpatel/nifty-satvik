# 0024 — Bhanushali run as a PRACTITIONER runs it: overtrading solved, drawdown tamed, but the method earns too little per unit of capital

- **Status:** MEASUREMENT / external-strategy analysis per pre-reg `diagnostics/research/preregistry/0024-bhanushali-practitioner.md`
  (params frozen before the run; no retuning). No n_trials cost, no cfg change.
- **Date:** 2026-07-03. Script `scripts/run_bhanushali_practitioner.py`, window 2017–2026, PIT membership,
  tiered real costs. Prompted by the owner's process audit: 0022/0023 tested the *mechanics* but skipped the
  *portfolio process* a real trader runs — the weekly frozen top-50 watchlist, the no-overtrade throttle,
  scaling out (half at 1:2 + swing-low trail), and the index regime check. Owner fixed the four open choices
  (watchlist rank = trend+volatility+volume; half@2R + §12 swing-low trail; NIFTY regime pause; 5 pos / 3
  new-wk / 10d cooldown).

## Result (headline = combined A+B on the weekly watchlist)
| arm | tr/yr | win | expR | CAGR | Sharpe | MaxDD |
|---|---|---|---|---|---|---|
| **combined GROSS** | **20** | 39% | +0.21 | **+4.0%** | **+0.46** | **−19.5%** |
| **combined NET** | 20 | 39% | +0.21 | **+1.0%** | **+0.15** | −21.8% |
| B only (pullback), net | 20 | 38% | +0.17 | +0.0% | +0.05 | −22.8% |
| A only (RSI), net | **3 trades in 9.5y** | 100% | +1.77 | +0.8% | +0.46 | −2.8% |
| regime OFF, net | 36 | 36% | +0.14 | −1.9% | **−0.08** | −34.3% |
| volume-confirm OFF, net | 45 | 38% | +0.24 | +4.8% | +0.39 | **−36.4%** |
| throttle OFF, net | 20 | — | — | +1.0% | +0.15 | −21.8% (identical — never binds) |

Sub-periods (net, continuous slice): 2017-18 +0.32 / 2019-21 +0.03 / 2022-26 +0.19. Exit mix: essentially
all exits via (initial or trailed) stop; avg hold 11d — squarely his 3–10d rhythm.

## Root-cause readout (REQUIRED)
1. **The practitioner process WORKS as process.** Trades/yr collapsed 260→20 (the owner's no-overtrade goal),
   and MaxDD collapsed −92%→−20% gross. The watchlist + confluence is itself the throttle: the explicit
   5-pos/3-new cap **never binds** (throttle-OFF arm is byte-identical). Overtrading was a *scanning-the-
   whole-market* artifact, exactly as the owner suspected.
2. **The regime pause is genuinely load-bearing** (his "mahaul", the owner's call): regime OFF flips net
   Sharpe +0.15→−0.08 and deepens DD to −34%. First Bhanushali component that *adds* net Sharpe outright.
3. **But the method cannot deploy capital.** Gross CAGR only +4.0% despite positive expectancy (+0.21R/trade),
   because: tight candle-low stops (~3–4%) want ~57% notional to reach 2% risk → the 30% notional cap and the
   no-leverage cash constraint cut realized risk to ~1%/trade; × 20 trades/yr ≈ a few %/yr. This is the honest
   ceiling of a 5-position tight-stop swing book without leverage. A real trader "earning 20%/yr" on this is
   either concentrated way beyond 30%/name or leveraged.
4. **Costs still eat most of it:** 4.0%→1.0% CAGR (~3%/yr drag on a volatile-midcap watchlist at 0.22%
   slippage). The method selects exactly the names with the highest slippage tier.
5. **Volume nuance (differs from 0023):** removing the HVC gate here RAISES net CAGR/Sharpe (+4.8%/+0.39)
   but doubles DD (−36%) — because the watchlist's volume-*expansion* ranking already pre-filters for
   institutional interest, the per-candle HVC gate acts as drawdown control, not return enhancement. In 0023
   (no watchlist) volume was the only institutional filter and removing it collapsed the system. Consistent
   story: *some* volume filter is load-bearing; where you apply it moves return↔DD.
6. **Engine A (RSI-35) is practically untradeable under real confluence** — the weekly-trend + RSI-cross +
   watchlist + quality-green + HVC stack fired 3 times in 9.5 years. His RSI system as taught, with all his
   own confirmations applied, produces ~1 trade every 3 years.

## Verdict
**The practitioner process rescues the strategy's RISK profile, not its RETURN.** Run the way a disciplined
human runs it, Bhanushali's method is a real, low-drawdown (−20%), low-turnover (20/yr) system with positive
per-trade expectancy — and a gross return of ~4%/yr that costs cut to ~1%/yr net: roughly FD-yield with equity
effort. It is decisively below baseline_v1 (0.667 Sharpe / 15.5% CAGR) on every axis except drawdown. The
durable extracts stand: **regime pause (new, net-positive here), volume as DD-control, watchlist-as-throttle.**
Survivor-only cache (sha f8625a8f, 103 delisted members missing) makes even these numbers optimistic.
Disposition: arc closed for the config; principles feed the forward-only conviction/feature work.
