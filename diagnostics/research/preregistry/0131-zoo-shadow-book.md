# Pre-registration 0131 — the zoo shadow book (watched, observational)

**Status: CLOSED 2026-08-06 — falsifier fired on both legs; book STOOD DOWN by owner decision.**
Outcome appended at the foot, below the immutable section.
**Counts frozen: screens 16 · sealed opens 1 · n_trials 138. This spends none of them.**

**It is not a trial.** No configuration is evaluated for a PROMOTE/KILL decision against the honest
base; nothing is adopted; the live book, the forward wall and the traded config are untouched. It
stands up a **logger**, exactly as `blend_hybrid_paper.json` is a logger.

**No wall amendment is required yet.** `forward/prereg.md` governs the three books it names; this is
a fourth observational stream outside it. Formalising it as a wall book — or standing it down — is
the **2026-10-01 ask** in §6.

---

## 1. What is elected, and on what evidence

**Elected:** `cup_handle`, `box`, `double_bottom` — added to `touch44` as one combined candidate
pool.

**The evidence, and its exact strength:**

| source | what it shows | what it does NOT show |
|---|---|---|
| [`ZOO_TWO_LENS.md`](../ZOO_TWO_LENS.md) | at population level all three beat `touch44` with CIs excluding zero **in both units** — cup ΔR +0.365 / Δeq +0.758pp, box +0.287 / +0.574, dbl +0.266 / +0.509 | anything about a capped book |
| [`POWER_READJUDICATION.md`](../POWER_READJUDICATION.md) addendum | the standalone rejection (touch 1.29 vs cup 1.02 / box 1.00 / dbl 0.94) **never carried a CI**, and all three gaps sit inside the measured ±0.302 band — widened further by sub-slice and smaller-N | that any of them is *better* |
| STAGE4 configs B/C/D, ROUTER | the zoo does **not** survive the shared cap — and those verdicts are re-adjudicated to NOT PROVEN, not overturned | that the zoo *does* survive it |

**`ascending_base` is NOT elected**: population CIs straddle zero (N=106) *and* it is standalone-worse
by 0.65, outside any plausible band. `trend_pullback`, `vcp`, `flag`, `sr_pivot` are not elected —
null, or N < 60.

## 2. The hypothesis, in the form the evidence supports

> **H: the combined funnel improves the POOL, not the THROUGHPUT.**
>
> Capital binds, not signal supply. The census measured the book funding **255 of 6,245** signals
> (4.08%), with the funded count flat at 15–36 a year while supply swung 280→984. Adding three
> detectors therefore should **not** materially raise trade count; it should raise the *quality of
> what wins the CRS queue*, because there are more candidates competing for the same five-ish seats.

**Falsifier, pre-committed:** if the shadow book's trade count rises materially (>25% over the live
book's) while per-trade quality does not, H is wrong — the funnel is buying throughput, not pool
quality, and the programme's own dilution result (`FINDING_more_slots`) says that is bad.

## 3. Construction — one difference and one only

The shadow book is the **frozen engine** with a wider candidate pool:

| | live/record book | shadow book |
|---|---|---|
| candidate pool | `touch44` | `touch44` + `cup_handle` + `box` + `double_bottom` |
| CRS fill priority | same | **same** |
| exit ladder | frozen default (13-week cap) | **same frozen default** |
| sizing / risk % | same | **same** |
| capital | ₹10L | **same** |
| cash gate | same | **same** |

**Everything except the pool is held identical**, so any divergence is attributable to the pool.
Note this deliberately uses the **frozen ladder, not `P2_EXIT`** — which means it is *not* comparable
to the STAGE1/STAGE4 numbers that motivated it, and that is intentional: those carry confound 1 of
`ZOO_TWO_LENS.md`, and this removes it.

## 4. Evaluation terms — PRE-COMMITTED NOW, before any number is read

**The capped comparison is underpowered by construction and will stay that way.** The measured
resolution band is **±0.302 ΔSharpe** and the book's whole annual return is 1.617σ. A shadow book
running from 2026-08 cannot resolve a Sharpe difference in any horizon the review operates on.
**Therefore:**

- **This will never be read as a Sharpe race, at any review, at any horizon.** A ΔSharpe computed on
  this pair is reported only with the ±0.302 band attached, and never as a verdict. Writing "the
  shadow book beat/lost to the live book on Sharpe" is a violation of this pre-registration.
- **The read is two things, both pre-specified:**
  1. **Population-level per-trade quality** — mean R and mean % of equity per trade, with bootstrap
     CIs, for the elected setups versus `touch44`, on trades the shadow book actually funded. This
     is the lens `ZOO_TWO_LENS.md` established and the only one with power at this sample size.
  2. **Forward divergence** — whether the two books' *selections* diverge, how often, and in which
     direction. Weeks where the shadow book funds a zoo name the live book could not is the
     observable event; there is no such event in the live book's history to compare against.
- **Horizon: the 2026-10-01 review is a status check only, not a decision.** The first substantive
  read is **2027-04-01** (≥2 quarters *and* ≥30 shadow-funded closed trades, mirroring the repo's
  own paper gate). Thresholds may be tightened, never retroactively relaxed.
- **Metric of record:** per-trade **% of equity** is the arbiter, with R reported beside it.
  Rationale: [`UNIT_RESOLUTION.md`](../UNIT_RESOLUTION.md) — the two agree under risk-parity, but the
  arms here differ in half-booking rate and R is biased by the 2.0R notional credit (§4 of the
  definitions caveat added this session).

**What no outcome authorises.** A favourable read does **not** authorise adoption, a config change,
or a trial. It authorises exactly one thing: an owner decision at a review about whether this
becomes a wall book.

## 5. Guards

- **cfg-gated and cold.** Its own output file, its own code path, run beside the existing
  observational loggers. The golden master must stay byte-identical and the determinism guard must
  keep reproducing 1.1319 / 255.
- **It cannot influence the traded book.** A test asserts that running the shadow book leaves the
  live selection and sizing unchanged — no shared mutable state, no ordering effect.
- **Nothing in `forward/prereg.md` is touched.** The three wall books are unaffected.

## 6. The Oct-1 ask

One question, two answers: **formalise the shadow book as a wall book** (which requires a dated
§10 amendment and starts a proper clock), **or stand it down**. Not "is it winning" — it cannot be
winning or losing yet, and §4 forbids reading it that way.

## 7. Do-not-re-test-unless

This pre-registration creates no re-open condition for STAGE4, ROUTER or any E-lever. Those remain
exactly as `POWER_READJUDICATION.md` leaves them: relabelled, not revived.


---

# OUTCOME — appended 2026-08-06, below the immutable section

**Executed exactly as pre-registered, and closed at the first observation.**

**Both pre-committed falsifier legs fired.** Trade count 255 → **491 (+92.6%)** against a 25%
threshold, and per-trade quality **fell** in the pre-committed arbiter: **−1.941pp of equity,
CI [−3.598, −0.264]**, excluding zero (ΔR −0.276, CI [−0.486, −0.067], also excluding zero).
**H — "the pool improves, not the throughput" — is refuted on its own terms, in its own unit.**

**§4 was honoured.** The ΔSharpe of −0.2845 sits inside the ±0.302 band and was **not** read as a
verdict, at any point. What closed the study were three quantities that do not depend on it: an exact
trade count, a CI-excluding-zero quality delta in the arbiter, and a structural displacement
(touch44 fills 255 → 29; 19 shared fills of 255/491).

**The mechanism was measured, not described:** stop width (7.00% → 17–25%) → notional (28.6% → 8–12%
of equity) → seats (5.64 → 12.15 mean concurrent) → dilution (`FINDING_more_slots`' trial-priced
dose-response, where 12.15 seats is past its worst measured point). One correction to the chain as
framed: *"walks the CRS queue down"* is **not** supported — funded `crs_dist` rises, because
`crs_dist` is not comparable across detectors. The fourth link is seat count, not queue depth.

**Both escape routes were already closed before this ran** — idle cash (0104/0108, Law III's
bookend) and equal-notional sizing (0130, −10.83% of equity/yr). That is what makes the result
terminal rather than unresolved.

**§6's ask, answered: STOOD DOWN.** Unwired from the Saturday cron; script, artifact and guard tests
retained so the result stays reproducible. The guard test that asserted the cron wiring has been
**flipped** to assert the stand-down, so re-wiring without re-opening this pre-registration fails the
suite.

Finding: [`research/findings/0131-zoo-shadow-book.md`](../../../research/findings/0131-zoo-shadow-book.md).
