# 0017 — Point-in-time fundamentals → orthogonal value/quality alpha

- **ID:** 0017 (Stage C of the institutional rebuild; see [[0016]])
- **Registered:** 2026-06-08
- **Holdout:** embargo-45 walk-forward (dev/measurement) → unseen-universe →
  forward-wall (confirmation). Reproducible-only verdicts. DSR-gated.
- **n_trials (cumulative):** ~63 at start (continues the 0012/0016 ledger;
  +1 per walk-forward candidate evaluated).
- **Status:** Step 1 DONE (2026-06-08) — INCONCLUSIVE (coverage floor not met on
  yfinance; see Result). Disposition (kill / deep scrape / other free source)
  escalated to owner. Step 2 gated on a credible signal that Step 1 did not produce.

## Context

Stage A (the optimizer + risk model) was fairly KILLed (0016): portfolio
construction can't rescue the momentum signal (it smooths Sharpe but costs −15.7%
CAGR, DSR 0.26). Every PRICE-based / construction lever in the 0012/0016 record
has now been killed. The one genuinely **untested, orthogonal** lever is
**non-price information**: value + quality from fundamentals. The price-momentum
model structurally cannot see "is this company cheap / high-quality" — that is
the breadth the Fundamental Law says we lack.

## Hypothesis

Point-in-time value (E/P, B/P) and quality (ROE, low debt/equity, accruals)
factors carry **cross-sectional IC that is orthogonal to the momentum signal**,
and adding them (as features via retrain, or as a cross-sectional tilt) improves
out-of-sample risk-adjusted expectancy on the balanced scorecard — WITHOUT a
lookahead bias.

## Critical correctness guard — LOOKAHEAD

`src/data/fundamentals_pit.py` (built, tested, gate-clean) accesses fundamentals
**strictly** as-of: `point_in_time_value(frame, field, as_of)` returns only rows
whose `available_date < as_of` (strict — same-day results aren't tradeable, T+1
convention). `available_date = period_end + 60d` (conservative SEBI-LODR lag)
when the true filing date is unknown (yfinance gives period-end only).
Over-lagging is safe; under-lagging leaks. The existing `data/fundamentals.py`
(current-snapshot yfinance `.info`) is NOT used — it has no time dimension and
would leak catastrophically.

## Design (two steps — cheap KILL first)

**Step 1 — MEASURE (descriptive, no DSR trial).** Build the PIT store from
yfinance quarterly financials; compute the value/quality factor **IC / IC-IR**
(reusing Stage-0 `factor_metrics`) vs forward returns at the 14-day horizon AND a
longer horizon (e.g. 60–90d — value/quality are multi-month signals; the
**horizon mismatch** vs the 14-day model is the central risk). Report under the
**coverage floor**: a date/fold with <70% of the universe carrying real PIT data
does NOT count (pre-2018 yfinance coverage is thin). **Early KILL:** if no factor
clears |IC-IR| materially above zero at any tested horizon on covered names →
KILL cheaply, before any retrain.

**Step 2 — INTEGRATE (gated, only if Step 1 shows orthogonal IC).** Either (a)
add the factors to `V1_FEATURES` and retrain the ensemble (atomic 3-sibling,
feature-count parity), or (b) apply them as a cross-sectional tilt/gate on the
existing signal. Test at a horizon-appropriate rebalance/hold. Decision rule =
the standard 0012/0016 gate: balanced composite > 0, DSR > 0.95, no floor breach
(WR/CAGR/trade-count/drawdown), holdout doesn't contradict. Any breach → KILL.

## Source

yfinance quarterly financials first (free, already used by the repo, least
fragile) — coverage ~2018+ for quarterly statements. A Screener.in / NSE-XBRL
deeper-history scrape is a **later augment ONLY if the coverage floor isn't met**
(it is outward-facing + ToS-relevant → surfaced to the owner before running at
scale). Neutral-fill (rank 0.5) means thin coverage is a non-bet, not a bias.

## Honest prior (~40–50%)

Value/quality is the best-prior orthogonal lever, BUT: (1) the horizon mismatch
(slow factors vs a 14-day model) may mean they only help at a longer hold; (2)
the universe is large-cap-tilted Nifty 500 where value/quality are well-arbitraged;
(3) the whole 0012/0016 record is kills. Skeptical priors; cheap Step-1 KILL gate
before any retrain spend.

## Result

### Step 1 — MEASURE (2026-06-08, cloud run 27104586479, `pit_factor_ic.json`)

**Verdict: INCONCLUSIVE on coverage grounds → the yfinance data source is KILLed
as inadequate. The factor hypothesis is NOT tested (neither supported nor cleanly
killed). Disposition (kill Stage C vs deep scrape) escalated to the owner — the
deep scrape is outward-facing/ToS-relevant per this pre-reg's Source clause.**

The cheap test did its job: it told us cheaply that the cheap data source cannot
test the hypothesis, before any retrain spend.

**Coverage (the headline):** yfinance quarterly statements carry only ~5 recent
quarters, so PIT availability (period_end + 60d) effectively starts in 2024. Mean
universe coverage by year: 2017–2023 = **0%**, 2024 = 4%, 2025 = 44%, 2026 = 21%.
Of **111** monthly sample dates, the count clearing the 70% floor was ep **3**,
bp **6**, roe **3**, low_debt **6** — all clustered in late 2025. The pre-registered
coverage floor was therefore **not met**; per design this is exactly the trigger
for the deeper-history decision, not a signal claim.

**The above-floor IC (single-regime artifact, NOT credible factor evidence):**

| factor | 14d IC | 63d IC | 126d IC | dates | read |
|---|---|---|---|---|---|
| bp (value) | +0.071 | +0.102 | +0.143 | 6 | monotone-positive, hit 1.0 |
| ep (value) | +0.035 | +0.048 | +0.155 | 3 | only 126d notable, n=3 |
| roe (quality) | −0.032 | −0.058 | +0.024 | 3 | noisy / null |
| low_debt (quality) | −0.074 | −0.100 | −0.089 | 6 | **negative** (high debt won) |

The t-stats (bp 126d t=6.27) are inflated by overlapping 126d windows on
monthly-spaced dates from one ~12-month window → ~1–2 independent observations.
The coherent story is a **late-2025 cheap/leveraged-cyclical rally** (value-positive
AND low-debt-negative = junk rally), a single-regime fingerprint — not multi-regime
factor IC. We cannot distinguish "value works" from "value rallied in 2025" on this
data.

**Decision fork (owner-gated):**
- **(A) KILL Stage C** — without deep fundamental history the one orthogonal lever
  is untestable; given the 0012/0016 kill-record and that the validated lever is the
  existing edge + the forward wall ([[0003]]), don't invest in a scrape. Record as
  KILL (data-infeasible).
- **(B) Deep scrape** — Screener.in / NSE-XBRL announcement-dated history (multi-year,
  multi-regime). The only way to actually run Step 1 as designed. Outward-facing +
  ToS-relevant + a real data-engineering project → owner authorizes.
- **(C) One more free deep source** — try a bulk India-fundamentals dataset before
  committing to a scrape (cheaper path to multi-year history).

_(Step 2 remains gated on a credible Step-1 signal, which this run did not produce.)_

### Step 1b — DEEP-history augment (owner authorized 2026-06-08)

Owner chose **(B) deep scrape**. Built `diagnostics/scrape_screener_fundamentals.py`
(Screener.in annual P&L + Balance Sheet, ~10-12 fiscal years/name; cached,
rate-limited, one-time research build — not a cron) + the pure, lookahead-safe
`fundamentals_pit.build_pit_frame_from_screener` (annual EPS → eps_ttm; net worth =
Equity Capital + Reserves; ROE, debt/equity, BVPS derived; **available_date =
period_end + 90-day** conservative annual lag; 9 unit tests, mypy-strict clean).
Spike confirmed reachability + 12yr depth on RELIANCE; 5-ticker smoke = full
2018+ coverage. Re-runs Step-1 IC on the deep store via the SAME harness
(workflow `scrape-pit-factor-ic.yml`). This time the coverage floor CAN be met
across 2017+ and multiple regimes (2018 bear / 2020 COVID / 2021 bull / 2022 / 2025),
so a positive value IC could no longer be dismissed as a single-regime artifact —
making the Step-1 verdict (and any KILL) finally credible.

### Step 1 FINAL — HONEST base (2026-06-08, run 27118748147, `pit_factor_ic_honest.json`)

**Verdict: KILL for the 14-day model. The credible measurement is finally in** —
deep Screener store + survivorship-corrected universe gives **88-91% coverage every
year 2017-2026** (all 111 monthly dates clear the 0.70 floor; vs yfinance's 0% pre-2024).

| factor | 14d IC-IR | 63d | 126d |
|---|---|---|---|
| **ep (earnings yield)** | 0.10 (t=1.0) | 0.20 (t=2.0) | **0.25 (t=2.6)** |
| bp (book/price) | 0.01 | 0.11 | 0.15 (t=1.5) |
| roe | 0.02 | −0.05 | −0.11 |
| low_debt | −0.11 | −0.18 | −0.19 |

At the model's **14-day horizon, value/quality carries essentially NO usable IC** (the
strongest, ep, is t=1.0 = noise). The one real signal is **earnings-yield at 126 days**
(IC-IR 0.25, t=2.6) — a genuine but **modest 6-month value effect**, a horizon mismatch
9× the 14-day model. ROE is null; **low_debt is NEGATIVE** (the Indian leverage/junk
premium — high-debt names outperformed). → **Do NOT add value/quality features to the
14-day ensemble** (no IC at the relevant horizon). The 126d ep signal is noted as a
SEPARATE longer-horizon strategy possibility (out of scope per the 2026-06-08 "honesty +
live-proof first, stop chasing alpha" decision). Stage C is CLOSED. This is the credible
KILL the deep+honest data enabled — not the earlier yfinance INCONCLUSIVE.
