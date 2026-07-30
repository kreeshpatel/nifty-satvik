# Pre-registration 0118 — Delivery-quality label screen on the swing substrate

**Status:** PRE-REGISTERED (before any feature-label join). **Date:** 2026-07-27. **Trial accounting:**
this is a MEASUREMENT (label screen) — **0 trials; n_trials stays 138.** Screen-ledger row #7 appended
before the run (`diagnostics/research/label_screen_ledger.md`; running screen count 7). Census basis:
`diagnostics/research/data_census_20260727.md` candidate #1, owner-signed. Registry-first: finding
**0010** (delivery-% INCONCLUSIVE/KILL as a 63d-base ranking signal) is cited — this is a different
horizon (weekly swing), different object (pre-entry-window label screen, not a ranker), different
labels (the banked 0116/0117 classes). **A pass here does NOT authorize a ranking overlay** (the 0010
redux clause).

## Data & PIT
Raw: `data/_delivery_raw.parquet` (harvest_delivery.py — MTO + sec_bhavdata daily archive files,
2019→present, EQ/BE, immutable-at-publication). **Publication assumption (encoded in
`nq/data/delivery.py`):** each file is published the same evening after settlement (~18:00 IST), never
restated → a row dated T is usable after T's close; all joins consume features at dates ≤ the
signal-week Friday, and the entry executes the following week — strictly PIT. Trailing-only derivation
truncation-proven by `tests/test_delivery_pit.py` (3/3). Aliases applied at build
(`data/delisted_alias_map.json`) so delisted members join.

## Audit gate (Step 2 — the screen is INVALID unless these pass, reported first)
1. Per-year coverage of the corrected universe (matched trades / total), incl. delisted-name presence.
2. MTO ↔ sec_bhavdata seam (2020-07): same-day cross-check on overlapping dates; no definition drift
   in deliv_pct.
3. Spot-checks of name-days against the raw published file text.
4. If coverage holes correlate with outcomes (e.g. delisted names systematically missing), STOP.

## Frozen features (pre-entry window ending the SIGNAL-week Friday, inclusive; computed by
`nq.data.delivery.derive_delivery_features`, joined at the last available date ≤ sig-Friday)
| feature | definition |
|---|---|
| dlv_med21 | rolling 21d median delivery-% (min 10 obs) |
| dlv_trend | rolling 5d mean − 21d mean delivery-% |
| dlv_dwn21 | rolling 21d median delivery-% on DOWN days only (who absorbs the selling; min 5 obs) |
| dlv_med21_z | 252d trailing z of dlv_med21 within the name (level-vs-self; drift guard) |
No other features. No window variants. One computation, one join.

## The questions (verbatim from the sign-off)
Q1. Does pre-entry delivery quality separate **false_touch from noise_stop** (the stop's two victim
classes), beyond ext-band × CRS-tercile cells?
Q2. Does it mark **exit_too_early winners** vs ordinary winners?
Q3. (Context) the R-gradient: conditional top-vs-bottom tercile spread on per-trade R.

## Protocol (0116 verbatim)
Train entries 2019-01-01..2024-06-30 ONLY; the sealed 2024-07+ slice is not read by the screen script.
Conditional cells: ext-band (≤10/10-20/>20%) × CRS-tercile; +ADV-tercile conditioning reported for the
liquidity-proxy failure mode. Effect sizes with bootstrap 95% CIs; per-year sign tables. ONE run — no
retunes, no added features, no second pass with different windows.

## Pre-committed pass/kill bar
A feature SURVIVES iff (a) its conditional effect on the Q1 cohort contrast (false_touch-vs-noise_stop
mean difference) or the Q3 R-spread is ≥ 0.15R-equivalent with a CI excluding zero, AND (b) the sign
holds in ≥4 of the 6 train years, AND (c) the effect does not vanish inside ADV terciles (liquidity
proxy check). Anything less → **KILL: delivery-% closes** (finding + registry row; census #2 becomes
the next decision). On a PASS: STOP — present the effect + a one-paragraph mechanism-matched usage
sketch (veto/risk-gate shape, NOT a ranker) and wait for owner sign-off; any usage test is a real
trial (full pre-reg, sealed set, Stage-C capped endpoint, n_trials increments).

## Named failure modes
1. **0010 redux** — delivery carries no swing-horizon information; the screen returns nulls.
2. **Liquidity proxy** — delivery-% tracks size/ADV; the ADV-tercile conditioning exposes it.
3. **The 0116 flip precedent** — a train-clean effect can invert on the sealed set; nothing is
   believed until a (future, separately pre-registered) sealed check — the screen alone never adopts.
4. **Seam artifact** — a spurious "effect" from the MTO↔sec_bhavdata definition change; the audit
   gate's cross-check guards it.
