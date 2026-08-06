# Pre-registration 0130 — the sizing-exclusion bound

**Status: PRE-REGISTERED — AWAITING OWNER SIGN-OFF. NOTHING HAS BEEN COMPUTED.**
Written 2026-08-06. **Counts at writing: screens 15 · sealed opens 1 · n_trials 138** — all three
unchanged by this document. No arm has been run; no data has been touched beyond the registry
confrontation below.

**Classification ruling: MEASUREMENT class** (argued in §1). On execution this takes **one
screen-ledger row** (screens 15 → 16) and **does not touch `n_trials`**. §1.4 states the single
condition that would flip it to trial-class, as a binding constraint on the executing session.

---

## 0. The question

The trade-population census (2026-08-06) established that the funded book is not a representative
sample of its own signal population: **0 of the 1,249 tightest-stop signals were funded in 9.5
years**, funding probability varies **48×** by stop width, and **75.7%** of funded trades come from
the widest stop quintile. The mechanism is arithmetic — `shares = sizing_eq × 2% ÷ (entry − stop)`
(`run_bhanushali_weekly_rank.py:868`), so notional is inversely proportional to stop width and the
cash gate is a stop-width filter.

**What that costs, or saves, is unmeasured, and armchair arithmetic flips sign depending on the
framing.** Per trade the excluded quintile dominates (+0.972R vs +0.224R). But roughly six
wide-stop positions fit concurrently where one tight-stop position consumes 70% of the book, and
6 × 0.224 > 0.972. Whether the engine is throwing away its best signals or correctly trading
risk-efficiency for throughput cannot be settled by reasoning. It needs a bound.

---

## 1. Classification gate — run FIRST, before any computation

### 1.1 The precedent that says TRIAL

**`n_trials` 115→116 (2026-07-16)** priced the owner discipline config — the conjunction
`ext_cap=0.20` + `max_risk_pct=0.10` + `max_notional_pct=0.20` — as **one trial**, explicitly noting
it was "a RISK-APPETITE config, not an edge hunt". Risk-appetite framing did **not** exempt it.

**`n_trials` 120→122** priced `FINDING_more_slots` — two arms varying `risk_pct` to change slot
count — as **two trials**. That is a sizing-parameter study on this same book.

Both produced portfolio Sharpe / CAGR / DD against the honest base. Both were adopted or rejected on
that basis. If this bound is the same shape, it is trial-class and this session stops.

### 1.2 The precedent that says MEASUREMENT

Five activation bounds have run at **zero trial cost**, each taking one screen-ledger row:
0117 rotation (row 6), 0119 tiebreak (row 8), 0121 deferral (row 10), 0127 HEG-class (row 14),
**0129 event-proximity SIZING (row 15)**.

**0129 is the closest precedent and it is close.** It evaluated a **position-size multiplier**
`f ∈ {0.50, 0.75}` on activated entries — a sizing change, on this book, with a pre-committed grid —
and was priced as **screens 14 → 15 with `n_trials` unchanged at 138**. A sizing change is therefore
not automatically trial-class.

### 1.3 The distinguishing test, and the ruling

`n_trials.json` defines a trial as *"one independent strategy configuration evaluated for a
PROMOTE/KILL decision against the locked honest base"*, and states that *"pure measurement
diagnostics that make no trade decision are NOT trials."*

The operative question is therefore not "does it change sizing?" but **"does it produce a book
metric comparable to the honest base?"**

| | 115→116 / 120→122 (trials) | 0117 / 0119 / 0121 / 0127 / 0129 (measurements) | **this bound** |
|---|---|---|---|
| Simulates the cash carry path | yes | no | **no** |
| Produces an equity curve | yes | no | **no** |
| Reports Sharpe / CAGR / MaxDD vs base | yes | no | **no** |
| Arm proposed for adoption | yes | no | **no** |
| Output | a book | a ceiling in R/yr | **a ceiling in R/yr and %/yr** |

The design in §3 computes affordability **at full deployment** (`⌊1/cap⌋` concurrent positions)
rather than simulating the cash path. That approximation is not a shortcut — **it is what makes this
a bound rather than a backtest**, and it is why no Sharpe can be produced from it. A quantity that
cannot be compared to 1.132 cannot render a PROMOTE/KILL on the base.

> **RULING: MEASUREMENT class.** One screen-ledger row (screens 15 → 16) on execution;
> `n_trials` stays 138.

### 1.4 The binding constraint that keeps the ruling honest

**The moment any arm is expressed as a portfolio Sharpe, CAGR or MaxDD against the base, this
becomes trial-class and requires an `n_trials` increment before the run.** The executing session may
not compute an equity curve for Arm B, may not simulate its cash path, and may not report a
comparable book metric. If the session concludes that the question cannot be answered without one,
it **stops and returns to the owner** rather than quietly producing it — exactly as the
`max_notional_pct` sweep session correctly did when it priced its own work as a trial.

---

## 2. Gate 0 — registry confrontation

Per [`skills/verdict-machine`](../../../skills/verdict-machine/SKILL.md), every element mapped to its
existing verdict. **Closed elements are excluded from the design.**

| idea element | existing verdict | status | citation |
|---|---|---|---|
| Cap concurrent positions | **REJECTED — knife-edge overfit**, 0.24-Sharpe swing per one-position change | CLOSED | `research/losers_analysis/LOCKED_STRATEGY.md:62-63` |
| Concentration is a cost to be diversified away | **INVERTED — concentration is load-bearing, it IS the edge**; 4–5 names 1.21 > 7 → 0.97 > 10 → 0.81, walking toward the random null 0.74 | CLOSED (trial-priced, `n_trials` 120→122) | `research/substrate/FINDING_more_slots.md` |
| "The book abandons ~19k fills; fix it by fitting more trades" | **CLOSED — the cash-starvation thread is closed**; lower `risk_pct` fits more trades and dilutes monotonically | CLOSED | `FINDING_more_slots.md` |
| Prioritise the fill queue by closeness to the SMA | **REJECT — displaces the CRS leaders that fund the runners, −0.80 Sharpe** | CLOSED | `FORENSIC_FINDINGS.md:200,212`; `SYSTEM.md:82` |
| `max_notional_pct` as an adopted config | **TRIAL-priced** (115→116); the free half of its curve is already computed | CLOSED to re-pricing | `scripts/diag_notional_cap_curve.py`; binder §7 |
| Wide stops make positions small | **already known and written down** — "so a **wide** stop makes positions **small**. Capping R made the book **more** concentrated (14% → 22%)" | KNOWN since 2026-07-16 | `docs/decisions/0009-swing-discipline-config.md:66-68` |
| Lower per-trade risk to fit more signals | **KILL** — 1.0–1.5% → Sharpe 0.79–1.01; "the ~19.7k skipped signals are LOW-CRS-rank noise" | CLOSED | `LOCKED_STRATEGY.md:60-61` |

### 2.1 The collision, named honestly

**This idea collides hard with `FINDING_more_slots`, which is trial-priced and says the adjacent
thing.** That finding measured a monotonic dilution as seats increase and concluded *"there is no
diversification case for widening the book"* and *"the cash-starvation thread is now CLOSED."* Its
mechanism check passed, so its KILL is evidence about the hypothesis rather than about the lever.

Per the collision rule (**cite and narrow, never relitigate**), what this bound brings:

- **New formulation.** `FINDING_more_slots` varied **slot count** by changing `risk_pct` *while
  keeping the stop-width-dependent sizer*. Every arm it ran still sized by `risk ÷ (entry − stop)`,
  so every arm inherited the same stop-width selection — it changed *how many* seats, never *which
  signals could afford one*. This bound holds seats approximately fixed and changes the **sizing
  basis** (stop-width-dependent → stop-width-independent). At a 20% cap it deploys **5 concurrent
  positions**, which is inside more_slots' own best-performing SPEC band (4–5 names, 1.21) — so it
  is explicitly **not** a widening of the book, and the dilution curve is not the thing being
  re-tested.
- **New measurement.** The 6,245-signal population and its engine-validated per-signal simulator
  (0 mismatches against all 3,045 engine rows) did not exist when more_slots ran. The exclusion it
  prices — 0 of 1,249 — was not measurable then.

**What the collision costs this study, stated before it runs:** more_slots bounds the answer from one
side already. If Arm B's advantage requires more seats, it is re-testing a closed question and must
be reported as such rather than as a finding. **The pre-committed reading is therefore asymmetric:**
a FAIL is informative and closes the territory; a CLEAR is *not* evidence for changing the sizer
until it is shown to hold at a seat count inside more_slots' non-diluting band.

### 2.2 What is explicitly NOT being asked

Not asked: whether the book should hold more names (closed); whether `risk_pct` should change
(closed); whether `max_positions` should be tuned (closed); whether fill priority should change
(closed); whether `max_notional_pct` should move (trial-priced, binder §7 owns it). **No arm here is
proposed for adoption.**

---

## 3. Design — frozen before any computation

### 3.1 Arms

- **Arm A — actual.** The 255 funded trades exactly as the record produced them.
- **Arm B — equal-notional comparator.** The same weekly candidate queue and the **same CRS fill
  priority** (`R94:837`), with position size taken from the engine's *existing* stop-width-independent
  term — `sizing_eq × cap ÷ entry` (`R94:873-874`) — instead of `risk ÷ (entry − stop)`. Tight-stop
  signals thereby become affordable. **`cap` is frozen at 0.20**, the live `LIVE_DISCIPLINE` value,
  giving 5 concurrent positions; no sweep, no second value.
- **Clairvoyant leg.** Best-outcome subset among Arm-B-affordable candidates, as a ceiling no real
  rule can reach.

### 3.2 Instrument

The census's **validated per-signal simulator** (`scripts/diag_trade_population_census.py`), re-run
through its existing gate — it must reproduce all 3,045 rows of the engine's uncapped ledger with
**0 mismatches** before any arm is computed, or the study stops.

**Explicitly NOT the engine's `uncapped` mode**, which enforces one-position-per-ticker and is not a
superset of the funded set (81 of the 255 funded trades are absent from it). The census caught this;
it is the trap to avoid.

### 3.3 The stated approximation

Arm B affordability is computed at **full deployment** (`⌊1/cap⌋` concurrent positions), not by
simulating the cash carry path. This is a bound, not a backtest, and the finding must say so in those
words.

### 3.4 Mandatory reporting — all legs required

1. **Both units — R and % of equity — with the sign difference stated.** The arms differ
   systematically in stop-width mix, which is precisely the case binder §8.2 names as where R
   heterogeneity bites. Reporting only R would reproduce the census's own trap.
2. **Concurrency per arm.** Throughput vs risk-efficiency is the entire tension.
3. **Tail leg.** Disaster-class (R ≤ −1.5) exposure per arm. A 20% position with a 2.84% stop and a
   16% position with a 12.62% stop have different gap-through costs; measure it, do not assume it.
4. **Per-year table with signs**, and activation counts.
5. **Seat count actually deployed**, against more_slots' 4–5 / 7 / 10 dose-response.

---

## 4. The gate — one deliberate departure, argued here

**The ±10R/yr floor is invalid for this comparison**, and this is the §8.2 named exception rather
than a convenience: the arms differ systematically in stop-width mix, so 1R does not mean the same
quantity of money in Arm A as in Arm B.

**Restatement, with the derivation shown.** In the record, sizing is pure risk-parity and the engine
*asserts* the invariant on every fill — `rp = shares × (entry − stop) ÷ sizing_eq × 100` must lie in
[1.98, 2.02] (`R94:884, 889`). So **1R ≡ 2% of sizing equity, exactly, in Arm A**. Therefore

    ±10 R/yr  ≡  ±20% of equity per year.

Cross-check against the book's own numbers, which agree three ways: 13.44 R/yr × 2% = **26.9% of
equity per year** arithmetic, against a published CAGR of **24.69%** (the gap is compounding vs
arithmetic). And 20% ÷ 26.9% = **74.4%** — the same figure the power arithmetic gives independently
(the floor is 1.204σ against a book at 1.617σ).

**The gate for this study is therefore ±20% of equity per year**, and it applies to both arms because
% of equity is commensurable where R is not.

**If the executing session judges this restatement unsound, it stops and reports rather than
substituting a number.** A gate invented to fit a result is not a gate.

---

## 5. Pre-committed doors

- **FAIL** (bound below ±20%/yr, or wrong-signed) → record, close. The funding bias is documented as
  a **priced structural property**, not a defect, and SEL-1/2/3 in the Structural Defect Map move
  from **OPEN** to **TRADEOFF**.
- **CLEAR** → **no trial is authorised here.** It becomes an Oct-1 decision item, because changing
  the sizer is a governance-class config change. And per §2.1 it is not evidence for a sizer change
  until shown to hold at a seat count inside more_slots' non-diluting band.
- **UNDERPOWERED / ambiguous** → a first-class outcome. Report and stop; do not retune.

**Given the power finding (map §2 — the floor is 1.204σ against a book at 1.617σ), a FAIL here is
the strongly expected outcome and would carry limited information about the world.** That is stated
in advance so a FAIL is not later read as a strong disconfirmation of the census.

## 6. Do-not-re-test-unless

This bound may be re-opened only by: a **different book shape** whose seat count sits inside
more_slots' non-diluting band while decoupling size from stop width (the breadth-50 equal-weight
structure is the named candidate); or **forward evidence**; or a **corrected-universe re-anchor**
that changes the population's stop-width distribution. Re-running the same comparison with a
different `cap`, a bigger sample, or a different unit is refused relitigation.

---

## 7. What must happen before any arm is computed

1. **Owner sign-off on this pre-registration**, including the §1 classification ruling and the §4
   gate restatement.
2. Screen-ledger row appended **before** the run (screens 15 → 16).
3. `n_trials` untouched at 138 unless §1.4's constraint is breached, in which case the run stops.

**This session computed nothing. Counts are unchanged: screens 15 · sealed opens 1 · n_trials 138.**
