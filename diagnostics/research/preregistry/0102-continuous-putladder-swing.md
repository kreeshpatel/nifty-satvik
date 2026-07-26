# Pre-registration 0102 — Always-on deep-OTM put ladder (Universa-style) on the weekly-swing book

**Status:** PRE-REGISTERED (written before any run; params fixed here, not retunable).
**Date:** 2026-07-26. The one hedge construction the 0101 measurement + imported knowledge did NOT refute
(timing is exhausted — 0100 KILL + 0101; the knowledge endorses always-on convexity, never a put-spread,
never signal-armed). **n_trials cost:** +1 (single arm, fixed params) → cumulative 130 → 131, incremented
before the run.

## Overlay
A portfolio-level, ALWAYS-ON **deep-OTM NIFTY put ladder** as a NAV sidecar on the frozen 0094 book
(engine untouched → invariant holds by construction). NOT timed, NOT a put-spread (which truncates the
convex tail — 0100's error). Every month buy a fresh 1-month deep-OTM put; hold for convexity; monetize on
a spike; let the rest lapse. Priced from ACTUAL bhavcopy premiums (`data/_fo_oi_raw.parquet`).

## Params — FIXED (Universa-range; not tuned)
- **Strike:** deep-OTM put, `K = nearest listed strike ≤ 0.90 × spot` (~10% OTM — cheap, convex).
- **Expiry:** front-monthly, rolled EVERY month, always-on (no trigger).
- **Budget:** fixed premium spend = **1.0% of NAV per year**, spent evenly monthly (≈0.083%/mo); units =
  monthly_budget_rupees / put_premium_rupees. A fixed *drag budget* is the Universa discipline (small,
  constant), NOT a notional target — so high-IV months buy fewer puts, not a bigger bill.
- **Monetization:** if the put's intrinsic reaches **≥ 2× its premium** at any point before expiry, realize
  it and stay flat until the next monthly roll (harvest the convex spike — the mechanism that turns drag
  into DD relief). Otherwise settle intrinsic at expiry. (Conservative: intrinsic-only, ignores residual
  time value, so it *understates* monetization.)
- **Structure:** naked long put (full convexity, no upper cap).

Reusing the literature's ~1%/yr spend + ~10% OTM + 2× monetization is deliberate: inventing swing-specific
values would be a hidden tuning trial. If the ladder needs different values to work, that is itself the
finding.

## Hypothesis
A small, constant deep-OTM put spend buys convex crash protection that pays disproportionately in the
market-wide down-legs the book shares (COVID-2020, 2024-25 corrections), cutting the −42% MaxDD by more
than the ~1%/yr premium drag costs in CAGR — the "volatility-tax" argument. Unlike 0100 it is never armed
after a spike (no negative-EV timing) and keeps the full tail (no put-spread cap).

## Predicted direction (before seeing results)
- **ΔMaxDD:** better — the intended effect, concentrated in COVID.
- **ΔCAGR:** negative, ≈ −1%/yr (the fixed drag), partially offset by crash payoffs.
- **ΔSharpe:** ambiguous; positive only if the DD/vol relief outweighs the steady drag.

## Failure modes (≥2, named before running)
1. **Drag > payoff (the AQR prior).** Deep-OTM 1-month puts mostly expire worthless; if the crash payoffs
   (chiefly COVID) don't cover ~9 years of ~1%/yr spend, net CAGR/Sharpe fall with little DD benefit.
2. **Index hedge ≠ the book's idiosyncratic DD (0101's structural read).** If the book's worst drawdowns
   are single-name/concentrated rather than market-wide, an index put ladder can't cover them → DD barely
   moves while drag accrues.
3. **Monetization rarely triggers.** A 10%-OTM 1-month put reaching 2× intrinsic needs a fast >~10-13%
   monthly drop; outside COVID this is rare, so the harvest mechanism may almost never fire → closer to a
   naive hold-to-expiry ladder.

## Pre-committed verdict bar (DD-overlay class — fixed; identical to 0100/0095)
- **SHADOW (forward wall)** iff ALL, continuous-slice: ΔMaxDD ≥ +3.0pp; ΔSharpe ≥ −0.05; 2022-26 slice
  Sharpe not worse by >0.05; ΔCAGR ≥ −2.0pp.
- **PROMOTE:** forward-wall only (book already UNDERPOWERED).
- **KILL / UNDERPOWERED** otherwise. No retune of strike/budget/monetization; a near-miss is a miss (0025).

## Method
- Book leg: frozen 0094 (`run_bhanushali_weekly_rank`) on the corrected universe, 2017-2026; assert
  byte-identical headline reproduction (engine untouched).
- Hedge leg: pure function of the book NAV path + front-monthly deep-OTM put premiums (bhavcopy) + spot
  path; additive sidecar. Report ΔMaxDD/ΔSharpe/ΔCAGR/ΔCalmar + slices + block-bootstrap ΔSharpe CI + DSR
  @131 + a ladder ledger (per-month debit, monetized/expired, payoff, R) + hit-rate.
- Reproducible from the committed pipeline; vibe-trading not used (no PIT-NSE options).

## Registry cross-check (done before writing)
- NOT timed (0100/0101 exhausted timing). NOT a regime gate (0090) or de-gross (0095). NOT a put-spread.
- IS the always-on deep-OTM convexity the imported knowledge endorses (`_ingested/options_oi_tailhedge.md`;
  AQR/Universa) — new construction, new data, judged on drawdown. Clears relitigation on all four axes.
