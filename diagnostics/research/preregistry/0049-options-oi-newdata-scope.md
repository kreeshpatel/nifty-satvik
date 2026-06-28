# 0049 — single-stock options-OI: new-data scoping (the orthogonal frontier)

- **ID:** 0049. Registered 2026-06-19, BEFORE any ingestion/model work. **Data-foundation FIRST**
  (feasibility-gated): NO trial is counted and NO model is trained until Step 0 (PIT-clean data)
  passes. Cloud-run.
- **Context:** selection (LTR), exits (0042/0047), and portfolio mechanics (RS-01/0048) are all
  validated/ceilinged on the SAME price/volume data. The engine is at its **data ceiling**. The only
  ceiling-breaker is genuinely NEW, orthogonal information. Per the data-arc review, **single-stock
  options-OI is the promoted candidate** (FII/DII demoted = regime-only, can't rank; fundamentals
  KILLed 0017/0018; LLM-text parked behind a leakage test).

## Hypothesis
Stock-level open-interest dynamics (OI buildup/unwinding, ΔOI×Δprice regime [long/short buildup,
long/short covering], stock-level PCR) carry **smart-money/derivatives positioning** that is
orthogonal to the 79 trailing price/volume features — and may predict where index PCR does not.
Skeptical prior: only ~180–200 F&O names (a subset of Nifty 500), expiry/rollover noise, and the
edge may not survive after-cost on the liquid large-caps where F&O concentrates. Default = KILL.

## Step 0 — DATA FEASIBILITY GATE (must pass before ANY model work)
The data-foundation audit's lesson stands: a leaky/survivor-biased source poisons everything. So:
1. **Source + ingest:** NSE F&O bhavcopy. **Two formats** — legacy (pre-2024-07-08) and **UDiFF**
   (post-2024-07-08); the ingester must handle the format break and reconcile fields.
2. **PIT F&O membership:** reconstruct which stocks were F&O-eligible **on each date** (the list
   changes — adds/exclusions). Using today's F&O list historically = survivorship/lookahead. This is
   the #1 hazard and the gate's hardest requirement.
3. **PIT-clean OI series:** per (date, stock) OI + ΔOI + price, expiry-aware (near-month, roll on
   expiry); align to the as-of timestamp (bhavcopy is EOD → usable T+1, same as the price path).
4. **Coverage + quality report:** % of Nifty-500 trade-days with F&O data; glitch/zero-OI screen;
   manipulation screen on the F&O subset (already large-cap, lower risk).
**Exit Step 0 ONLY IF:** PIT membership reconstructed + ≥N years clean coverage + no look-ahead in the
alignment (a `flaw-hunter` pass clears it). Else → STOP (data not trustworthy; do not model on it).

## Step 1+ (only after Step 0) — pre-register the trial separately
An **orthogonal SLEEVE** (the validated sleeve_contract path; corr<0.30 vs momentum) on the F&O
subset: OI features → rank within F&O names → the standard gate (CPCV + DSR>0.95 at cumulative
n_trials + per-trade after-cost CI-low>0 + matched-permutation IC null + regime stability + skeptic
agents). The trial (and its n_trials bump) is registered in its own pre-reg once Step 0 data exists.

## Frozen decision rule (Step 0)
Step 0 is a MEASUREMENT (not a trial): it produces the PIT-clean OI store + a coverage/leakage report,
or it STOPS. No PROMOTE/KILL of alpha here. The alpha gate lives in the Step-1 pre-reg.

## Parallel standing lever (not part of 0049)
The **forward wall (0003)** runs in parallel as the standing validation/adaptation loop — it accrues
live OOS results, validates the ceilinged edge, and (via the rollback triggers) is the safe answer to
regime change. It is the *safe* lever; options-OI is the *frontier* lever.

## Result
**Status: REGISTERED (scoping) — Step 0 data-feasibility ingester is the next build; no model work
until it passes the PIT/leakage gate.**
