# PRE-REGISTRATION — the small-candle selection lever + 60/30/10 exit

*Status: **PRE-REGISTERED**. Frozen by the owner 2026-07-16 BEFORE the run. No retuning under any
outcome (R4/R11).*

## Hypothesis

The R problem is a **selection** problem, not a stop problem. The stop *is* the signal-week low, so
`(close − low)/close` at the signal week **is R**. Rather than forcing the stop up to cap R (tested and
killed — `FINDING_owner_6040_poscap.md`), select only trades whose candle is naturally tight. Those
trades have R ≈ 5% by construction, which makes the 2R/3R targets reachable **without truncating the
stop and without concentrating the book**.

## Why this is not a relitigation

`max_risk_pct` (killed) **moved the stop** — it truncated the loss geometry on trades the ranker had
already chosen, which forced notional to 40% of equity and blew the drawdown to −54.5%. This lever
**changes which trades exist** and never touches the stop. Notional stays at `2%/R%` ≈ 40%… — **no.**
See the pre-declared risk below; this is the thing to watch.

New formulation, distinct mechanism. Cited against R-registry rule 1: **new formulation**.

## The frozen spec (one conjunction — owner's standing rule: combined, not lever-by-lever)

| param | value | meaning |
|---|---|---|
| `max_ctl_pct` | **0.05** | signal week `(close − low)/close ≤ 5%` → R ≤ 5% by construction |
| `min_body_frac` | **0.50** | signal week body `(close − open) ≥ 50%` of `(high − low)` — "solid green" |
| `max_notional_pct` | **None** | **no position cap** (owner: "remove the position cap") |
| `max_risk_pct` | **None** | **no R cap** — the candle filter is what solves R |
| `scaled_exit` | `tp1_r=2.0, tp1_frac=0.60, tp2_r=3.0, tp2_frac=0.30` | 60% @ 2R · 30% @ 3R · **residual 10% runs** to the weekly close below the 44w SMA |
| grade | all-grades | as per the baseline of comparison |

Everything else is the live 0094 book (2% risk, Rs10L, in-range fill, CRS rank order).

## Pre-declared arms (K=3 — multiple-testing accounting, R9)

1. **THE SPEC** as frozen above.
2. **Spec, live P2 exit** — isolates whether any gain is the candle filter or the 60/30/10 exit.
3. **Spec + the 3 signal guards** (`slope_min=0.06, prior_above_n=2, prior_above_lookback=4,
   require_progress=True`).

## Pre-declared measurements (recorded whatever the outcome)

- Pool: 8,518 windows → how many survive `max_ctl_pct=0.05 AND min_body_frac=0.50`.
- Trade count, Sharpe, CAGR, MaxDD, **2022-26 continuous slice**, win%, meanR, median R%, exit mix.
- **`meanR × R%`** — the actual price move captured. meanR alone is a denominator illusion when R%
  changes (established twice: `FINDING_R_cap.md`, `FINDING_owner_6040_poscap.md`).
- **Notional per name** = `2% / R%`. At R% = 5 this is **40% of equity with no cap**.

## Pre-declared risks — written down now so no one is surprised

1. **Concentration, uncapped.** This is the big one. Notional = `2%/R%`; at R% ≈ 5 that is **40% of
   equity in one name**, with the position cap explicitly removed. The killed arm reached −54.5% DD at
   20% capped; this arm is unconstrained. **If MaxDD blows out, that is the mechanism, and it was
   predicted here before the run.**
2. **The filter fights the ranker.** Pool median close-to-low is 6.6%, but the traded book's median R is
   14.2% — CRS actively selects fat-candle names. Expect the trade count to fall harder than the raw
   pool share implies.
3. **Fat-tail truncation persists.** 90% of each position is still capped at 3R. Only the 10% residual
   runs. `FINDING_taught_mechanics.md` and `FINDING_owner_6040_poscap.md` both found the fat tail *is*
   the edge. A 10% runner may not carry it.
4. Thin book → an underpowered read. **UNDERPOWERED is a first-class outcome (R11).**

## Gates

Judged on the **2022-26 continuous slice** (R3). Baseline all-grades **1.29** · A-only **1.17** ·
random-selection null **0.74** (sd 0.24). Report the null z too.

**Nothing ships in-sample (R11).** The live config stays FROZEN regardless of outcome.

## Guard

Both levers default `None` ⇒ byte-identical. Verified before the run: golden **1.1319/255** · live P2
**1.0342/168**.
