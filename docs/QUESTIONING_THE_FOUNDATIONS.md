# Questioning the foundations — where the model meets reality (Part 3)

*Continues the two brainstorm docs. This one is different: instead of adding layers, it attacks the
ASSUMPTIONS the whole thing quietly rests on. Each is a place the product can silently fail even if every
line of code is correct, because the *premise* is wrong. Grounded in our own findings. 2026-07-16.*

---

## 21. The assumption that can sink the product: users will cherry-pick, and cherry-picking IS the null

We proved (`MONTECARLO_null.md`) that a **random pick from the CRS-ranked pool scores 0.74** — the null —
while disciplined top-5-CRS scores far higher. The entire edge lives in *respecting the ranking and taking
the whole book.* But a real user will do the opposite: buy the name they've heard of, skip the one that
looks scary, take 2 of the 5 A-grade signals because that's all their gut likes.

> **A user who cherry-picks from the signals gets the random-selection null (~0.74 Sharpe), not the book's
> edge.** The single biggest determinant of a user's outcome is not the strategy — it is *whether they take
> the whole ranked book with discipline.*

This flips the product's #1 job. It is **not** "show good signals" — the signals are already at the
99-100th percentile of selection skill. It is **make discipline the path of least resistance**: surface the
top-5 as a set to be taken together, make skipping one an explicit friction ("you're taking 2 of 5 — the
edge assumes all 5"), and show the user their *own* discipline score (how closely their book tracks the
model's picks). Without this, we ship a 27%-CAGR backtest and users get 0.74 because they bought their
favourites.

---

## 22. The user's results ≠ the paper book — and the paper NAV is an optimistic CEILING

We will be tempted to show the model's paper NAV curve as "what you can expect." It is not. Four
independent leaks each push the user *below* the paper book, none above:

1. **Cherry-picking** (§21) → toward the null.
2. **Fill slippage** — the model fills at the in-range open; the user fills at *their* order's price,
   worse on average.
3. **Timing** — the model acts on the exact bar; the user acts late (missed Monday, placed the limit
   Wednesday).
4. **Cold-start start-date luck** (`COLD_START_DIST.md`) — their join date is a permanent fork, median
   *below* the compounded-from-2017 headline.

So the paper NAV is a **ceiling a disciplined, well-timed, early-joined user approaches but rarely beats.**
The product must show *their* NAV (`nav_history`) as the truth and the model curve as "the reference book,"
never "your expected return." Marketing the paper curve as a forecast is the classic way these products
lose trust when reality underperforms.

---

## 23. P is UNIQUELY execution-sensitive — choosing it raised the bar for non-expert users

This is specific to the config we shipped and easy to miss. The prior LIVE exit (P2) was **all
weekly-close decisions** — a user only ever acted once a week, Monday, off Saturday's flags. Forgiving.

**P is not.** P's 40%@2R tranche is an **intraweek resting limit.** A user who does not place that limit
does not get the 40% booked when price spikes through 2R — they hold the whole position to the weekly
pattern/runner exit, which is a *different, worse-timed book* than the one we backtested. So:

> **P's realized edge for a user depends on them placing a resting 2R limit on day one.** A user who "just
> watches" captures a materially different (and likely worse) version of P than the backtest, because the
> 40% profit-take never happens on schedule.

Consequence: for P, the onboarding *must* teach "place the SELL LIMIT and SELL STOP the moment you buy" as
non-negotiable, and the in-app Kite path should offer to place both automatically. We chose the more
execution-demanding config; the product has to carry that weight, or users get an untested variant of P.

---

## 24. Corporate actions mid-hold — the live CGCL bug, and it's WORSE live

We found the CGCL split as a *research* data bug (a 1:4 split read as a −75% loss). Live it is worse,
because a **real user holds through the corporate action:**
- A **split/bonus** multiplies their share count and divides the price — their broker adjusts, but the
  model's stop/2R/SMA levels (in old-price terms) are suddenly meaningless until the cache adjusts. For one
  weekend the user's card says "stop ₹520" on a stock now trading ₹130.
- A **dividend** drops the price ex-date — could false-trigger a stop or SMA break that isn't a real trend
  break.
- The model's PIT-adjusted series and the user's live broker position **diverge exactly at the corp
  action**, and that is the moment guidance is most dangerous.

Need: a corporate-action calendar gate — around any split/bonus/dividend on a held name, *suspend*
mechanical exit guidance for that name and flag "corporate action — levels adjusting, hold." This is the
CGCL lesson promoted from research hygiene to a live-safety rule.

---

## 25. Capacity & market impact — the strategy has an AUM ceiling we haven't priced

The backtest assumes a price-taker: fills at the open, an ADV-based slippage model. That holds for one
₹10L book. It breaks when **many users buy the same top-5 A-grade names on the same Monday morning:**
- They compete for the same liquidity → they move the price → they degrade *their own* fills.
- The universe is large+mid caps (ADV ≥ 5cr), but the top-5-CRS names each week are a *concentrated*
  target. 100 users × ₹10L into one mid-cap on one open is real impact.
- **The edge has a capacity limit.** Beyond some aggregate AUM the published signal front-runs itself.

Implications we haven't faced: an invite cap is not just exclusivity — it is a *capacity control*. We
should estimate the per-name ADV headroom and cap concurrent users accordingly, and consider staggering
entries or widening the band as AUM grows. Ignoring this means the product degrades its own signal as it
succeeds.

---

## 26. The 44-week-SMA warmup gap — new listings and new index members have no signal

The whole entry/exit rides on a 44-week SMA and a 40-week RS. A stock **newly listed** or **newly added to
the index** does not have 44 weeks of history. The model silently produces NaN and never signals it — fine
for research. But live:
- A user asks "why isn't [hot new listing] ever a signal?" — need an honest "insufficient history"
  answer, not silence.
- A held name that was recently added could have a *just-formed* SMA that is statistically fragile.

Need: an explicit "warming up (needs N more weeks)" state, both to answer users and to avoid trading a
fragile early SMA.

---

## 27. The NSE calendar is not a clean Mon-Fri — the cadence assumes something false

Everything pivots on "Friday weekly close" and "Monday open." Reality:
- **Holidays** shift the weekly close to Thursday and the action day to Tuesday. Muhurat sessions,
  mid-week holidays, and exchange closures all attack the ISO-week boundary (`cur_week_open`).
- **T+1 settlement** means cash from a Monday sell isn't fully available instantly — a user rotating into a
  new name may not have settled funds.
- A **holiday-shortened week** may not print a clean weekly bar.

The `is-this-week-closed` logic (already flagged fragile) must be driven by the **actual NSE trading
calendar**, not the civil week. This is one function that, if wrong, mis-times *every* action for *every*
user.

---

## 28. There are TWO classes of user, and reconciliation differs for each

The product has in-app Kite order placement (`nq_orders`) AND a research-only path (execute on your own
broker). So:
- **In-app executors:** we *know* their fills (Kite order id, WS-filled). Reconciliation is automatic;
  nudges can be assertive ("your 40% sold at ₹X").
- **External executors:** we *cannot* know their fills. Reconciliation is a *conversation* ("did you
  sell? at what price?"); nudges must be interrogative, and their ledger is self-reported (and may be
  wrong).

These are different products stitched together. The user-plane must carry a `fill_source`
(broker-confirmed vs self-reported) on every execution, and never treat self-reported as ground truth for
anything that matters (P&L claims, dispute resolution).

---

## 29. The eager new user OVER-concentrates — worse than the model's ramp

The cold-start we measured assumes the model's *ramp* (it fills ~5 names over 2-3 months as signals fire).
A real new user with cash burning a hole will **deploy all ₹10L on day one into the first 5 signals they
see** — instantly at max concentration, skipping the natural staggering that softened the model's
cold-start drawdown. Their first-quarter risk is *worse* than the ₹10L cold-start distribution, not equal
to it.

Onboarding must actively *slow them down*: "deploy over weeks, not day one; take signals as they fire; the
book is designed to fill gradually." The product's default should stagger, not dump.

---

## 30. When do we tell users to STOP? — the live-vs-expected divergence tripwire

We shipped P knowing it fails the gate and its edge is bull-regime. The forward wall certifies over
quarters. But **users are trading it now**, so "wait for the quarterly review" is not enough. We need a
**pre-committed live tripwire**, decided now (so it can't be rationalized away later):
- If live forward drawdown exceeds the modeled −40% → the −50% kill halts new buys (exists).
- If live forward Sharpe/return diverges from the backtest beyond a pre-set band for N months → surface
  "the live book is underperforming its backtest; here is the honest number" and let users decide.
- The tripwire must be **set before it's needed and shown to users**, or we'll move the goalposts when P
  disappoints (which the research expects).

This is the research program's "thresholds may be tightened, never retroactively relaxed" rule, extended to
the product's duty to the people trading it.

---

## 31. Self-critique — what in THESE brainstorms might itself be wrong

Applying the same skepticism to my own reasoning:
- **I assumed weekly cadence is right for the product.** But P's intraweek 2R limit (§23) means the
  product is *not* purely weekly — it is weekly-decision + intraweek-execution. I under-weighted this in
  Parts 1-2; §23 corrects it.
- **I assumed the reconciliation job is weekly.** For resting-order tranches (2R, stop) it is really
  *event-driven* (fill webhook), not weekly. Reconciliation is a hybrid: event-driven for resting orders,
  weekly-batch for pattern/runner decisions.
- **I may be over-building.** With one live user today (the owner), the three-plane architecture is
  correct *for scale* but heavy *for now*. The honest sequencing: build the snapshot/immutability
  foundation (cheap, prevents corruption) first; defer the full multi-user reconciliation until there is
  more than one user. Don't let "correct at scale" delay "shippable for one."
- **The whole product rests on P, which the research says is inferior.** Every layer I've designed serves
  a config that fails its own gate. The most foundational question remains the one the owner overrode: is
  P the right book to build a product on, or should the product be config-agnostic (swap the config behind
  a stable card/exit interface) so that when the forward wall speaks, the product follows without a
  rebuild? **Design the product against the EXIT-PLAN INTERFACE, not against P specifically** — so the
  three tranches are data, and swapping P→LIVE→(next) is a config change, not a product rewrite. This is
  the single most valuable structural hedge, and it costs almost nothing if done from the start.

---

## The through-line

The strongest base is not more features — it is naming the assumptions that, if wrong, make the features
irrelevant: users cherry-pick into the null; their results are a ceiling not a forecast; P demands
execution most users won't give; corporate actions and the NSE calendar break the clean model; the edge
has a capacity limit; and the product should be built against the *exit-plan interface*, config-agnostic,
so it survives the config being wrong. Build the snapshot/immutability floor first, keep the config
swappable, and make discipline the path of least resistance. Everything else is downstream of these.
