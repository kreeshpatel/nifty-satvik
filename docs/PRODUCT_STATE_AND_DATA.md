# Product state & data architecture — the non-obvious foundations

*Design brainstorm, 2026-07-16. Written before building Phase B/C/D, because the traps here are the kind
that silently corrupt a live trading product. Not a decision record — a map of what we must get right.*

---

## 0. The one insight everything hangs on: there are TWO state machines

The current cron is **stateless and idempotent** — its own docstring says *"recomputed from inception each
run."* Every Saturday it throws away everything and re-derives the entire book from price data. That is
correct for a *modeled paper book*. It is a landmine for a *live product*, because it collides with a
second state machine that the cron cannot see:

| | **Model state** | **User state** |
|---|---|---|
| Owner | shared, one per model | private, one per user id |
| Source of truth | **recomputed from price** every Saturday | **the user's actual broker executions** |
| "Did the 40% sell at 2R?" | derived — *did the weekly high cross 2R?* | recorded — *did YOU place the limit, did it fill, at what price?* |
| Mutable? | yes (idempotent recompute) | **no — append-only, it happened** |
| Storage | `results/*.json` (via GitHub) | Postgres, FK `users.id` |

**The product's core job is to reconcile these two, because they diverge.** The model says "40% booked at
2R this week." The user maybe didn't place the order, or it filled at a different price, or they sold 50%
by hand. The model's realized R is fictional for that user; only their execution ledger is real.

---

## 1. Your point 1, answered: "if 40% sold, the system memory should remember"

**Yes — but by the USER state machine, not the model one, and that distinction is the whole ballgame.**

- The **model** already "remembers" the 40% sale by recomputation: next Saturday it re-derives
  `t1_done=True` because the price crossed 2R. That is why Phase A's `exit_stage` shows
  `target_40_booked`. But that is the *model's* memory — it assumes you executed exactly as modeled.
- The **user's** memory must be a **durable, append-only per-user record** of what actually happened,
  because it is *not derivable from price*:
  - Did the user place the 2R limit? (maybe not.)
  - Did it fill? at what price? (slippage.)
  - Did they sell a different fraction? (fat finger, or discretion.)
  - What is their *actual* remaining quantity and realized P&L?

So the answer is: **the model remembers the plan; the user's ledger remembers the truth, and the UI
reconciles the two** ("The model booked the 40% at 2R this week — did you sell? [Yes at ₹X / No / Partial]").
The existing `user_holdings` table is the seed, but it is **ephemeral** (it self-deletes on model
completion) — that is exactly wrong for this. Phase C must add a **durable, append-only execution ledger**.

---

## 2. The deepest structural tension: idempotent recompute vs immutable history

The research engine is *built* to be idempotent (the byte-identical golden master is sacred). The product
needs the **opposite**: a card a user acted on must **never change retroactively.** You cannot let
Tuesday's "BUY at ₹325, stop ₹305" become Saturday's "BUY at ₹340, stop ₹312" because the model
recomputed off revised data. The user bought the Tuesday card; that card is now a contract.

These two requirements are in direct conflict, and the resolution is a **snapshot boundary**:

```
  RESEARCH LAYER (idempotent)            SNAPSHOT BOUNDARY            PRODUCT LAYER (immutable)
  cron recomputes from inception   -->   first time a signal_id  -->  append-only signal_snapshots
  results/*.json (mutable, shared)       is published, freeze it       (never overwritten, per shown card)
```

Rule: **the results/ envelope may change; a published snapshot may not.** Once `signal_id = ILC__2026-07-18`
is shown to a user, its entry band / stop / exit plan are frozen in Postgres. Later model revisions update
the *live* card for *new* viewers, but the user who acted keeps their original terms. This is the single
most important architectural decision in the product and the one a naive build gets wrong.

---

## 3. Runner topology — what each run consumes, produces, its scope, cadence, and store

| run | consumes (input dataset) | scope | produces | cadence | saved where |
|---|---|---|---|---|---|
| **A. Entry scan** (`run_bhanushali_cron`) | full universe: Nifty-500 weekly OHLCV + PIT membership + Nifty-50 (CRS denom) | **~500 stocks** | buy cards + held cards + exit_plan (the envelope) | **Sat 6 PM IST** (weekly close) | `results/signals_today_weekly.json` → GitHub → API |
| **B. Pattern + exit map** (extend monitor) | the **held names only** + fresh daily bars + weekly wk_hlc | **~5 stocks** | intraweek exit events, blow-off watch, structure tags | **weekday 4:15 PM** (post-close) | `results/weekly_monitor.json` (overlay) |
| **C. User execution ledger** (new API, event-driven) | user actions (buy/sell confirmations, broker fills) | **per user** | durable position + realized P&L per user | **on user action / order webhook** | **Postgres** (append-only) |
| Intraday scan | shadow universe | universe | shadow signals | weekday 2:30 PM | scan artifacts |
| Kite refresh | — | — | broker token | weekday 6:15 AM | Postgres session |

**The key realisation you named:** these are *different datasets at different scopes*. The entry scan is
universe-wide and expensive (run rarely, weekly). The pattern/exit map is **position-scoped** — it only
ever looks at the ~5 held names, so it is cheap and can run daily. Do **not** re-scan the universe daily
to check exits; that conflates two jobs and reintroduces the mutable-signal hazard (§2). Entry = weekly,
universe-wide, idempotent. Exit map = daily, position-scoped, observational.

---

## 4. Cadence map — which decision happens *when* (the part that is easy to get wrong)

Each of P's three exit tranches has a **different decision cadence and execution timing**. Getting this
wrong means telling the user to act on the wrong day.

| tranche | trigger | decided | executed | order type the user places |
|---|---|---|---|---|
| 40% @ +2R | price ≥ entry+2R | **any day, intraweek** | when the limit fills | a **resting SELL LIMIT** at ₹(entry+2R), placed upfront |
| 40% pattern | blow-off week (new high, close lower-third) once ≥2.5R | **only at the weekly close (Fri)** | **Monday open** | none upfront — the Saturday scan flags it, user sells Monday |
| 20% runner | weekly close below the 44w SMA | **only at the weekly close (Fri)** | **Monday open** | none upfront — Saturday scan flags it |
| stop | model: weekly close; **real life: intraweek** | model weekly / **real intraweek** | model Monday / **real when hit** | a **resting SELL STOP** at the stop level, placed upfront |

**Two non-obvious consequences:**
1. The **2R target and the stop are resting orders** the user places the day they buy — they fill
   whenever, no monitoring needed. The **pattern and runner exits are weekly decisions** surfaced Saturday,
   acted Monday. The UI must not blur these into one "exit alert."
2. The **model checks the stop only at the weekly close** (that is why backtested losses run past −1R),
   but a real user with a resting stop exits *intraweek*. So the user's realized stop-loss is **better than
   the model's** — another model-vs-user divergence, this one in the user's favour, and it must not be
   "corrected" by the recompute.

---

## 5. The storage plan — what lives where, and how

| data | shared or per-user | mutable? | store | why |
|---|---|---|---|---|
| the live envelope (buy/held cards, exit_plan) | shared (model) | mutable (recomputed) | `results/*.json` via GitHub | idempotent research output |
| model closed-trade history | shared | append-ish | `signals_history_weekly.json` | the model track record |
| **published signal snapshots** | shared, but **frozen per signal_id** | **immutable** | **Postgres (new)** | §2 — the card the user acted on |
| **user execution ledger** (fills, tranches, realized R) | per user | **append-only** | **Postgres (new)** | §1 — the truth of what they did |
| **user journey / memory** (onboarding, notes, tags, dismissed tips) | per user | mutable | **Postgres (new, durable)** | Phase C, not erase-on-completion |
| per-user sizing (capital, risk tier) | per user | mutable | `users` cols (exists) | quantity math |
| broker session | per user | rotating | `kite_sessions` (exists) | auth |

**Hard rule:** nothing per-user goes in `results/` (it is model-global and the Fly image reads it
read-only from GitHub). Everything per-user is Postgres, FK'd to `users.id`, reached through the backend's
REST+JWT layer (no Supabase client on the frontend — follow the existing pattern).

---

## 6. The non-obvious traps — things a normal build misses

1. **signal_id must encode the ENTRY EPISODE, not just the ticker.** A stock exits and re-signals months
   later. `{ticker}__{signal_date}` handles this *only if* signal_date is the entry episode's setup date
   and never reused. A user can hold TWO separate ILC episodes in their history. Every per-user row hangs
   off this key — if it collides, memory corrupts.

2. **Price is universal, quantity is per-user.** The exit levels (2R, 2.5R, the SMA) are the *same* for
   everyone (they are multiples of entry−stop). The *share counts* differ by each user's capital and risk
   tier. "Sell 40%" means 40% of *their* fill, not the model's. The exit_plan is published with prices;
   quantities are computed per user at display time.

3. **A held name can leave the universe mid-trade.** The scan runs on current index members. If a held
   stock is dropped from Nifty-500 or delisted while you hold it, the weekly recompute may stop tracking
   it — but the user still holds it. Need an explicit "orphaned hold" rule: keep managing the exit off raw
   price even after it leaves the scannable universe.

4. **As-of alignment / data lineage.** The CRS rank divides by Nifty-50 *as of the same Friday*. The daily
   monitor overlays Kite LTP. The weekly SMA needs 44 clean weekly closes. If any input is stale or
   misaligned by a day, the rank, the pattern arm level, and the SMA line all shift. Every published card
   should stamp the exact as-of date and data hash it was computed from.

5. **The blow-off pattern is a WEEKLY event — it cannot be confirmed intraweek.** A week that looks like a
   blow-off on Wednesday can close strong on Friday and not be one. So the pattern tranche can only ever be
   flagged Saturday, never mid-week. The daily monitor can show "forming — watch Friday's close," but must
   not tell the user to sell the pattern tranche before the week closes.

6. **Missed / partial action is the normal case, not the exception.** Users will miss the Monday sell, or
   place the limit late, or sell the wrong amount. The ledger must represent "model says tranche booked,
   user did not act" as a first-class state, and the UI must nudge ("you still hold the 40% the model
   exited last Monday"). A boolean `sold=true/false` is not enough; you need per-tranche actual-vs-plan.

7. **Idempotent recompute can resurrect a closed position.** If the data cache changes (a backfilled bar,
   a corrected split), a name the model had *exited* can re-open on recompute, or an *open* one can vanish.
   For research that is fine; for a user who acted, the published snapshot (§2) must shield them from it.
   Watch this specifically around the known split/data bugs (CGCL class).

8. **Two clocks: the model decides Friday, the user acts Monday, the world moves over the weekend.** Every
   "SELL at Monday's open" carries weekend gap risk the backtest models as the Monday open but the user
   experiences as a surprise. The card should say the *decision* (Friday close) and the *action* (Monday
   open) explicitly, so a −15% Monday gap is understood as modeled behaviour, not a system error.

9. **The onboarding "what to keep in mind" list is itself per-user STATE, not static copy.** Where a user
   is in their journey (first login? first buy? first exit? first loss?) determines what guidance to show.
   That is dynamic per-user memory (Phase C), not a static page — e.g., surface "here is how a partial exit
   works" the first time one of their holds hits 2R, not on day one when it is noise.

10. **Reconciliation is a scheduled job, not a moment.** Every Saturday the model produces new tranche
    states; the system must diff them against each user's ledger and generate per-user action items ("the
    model exited your GPIL runner Friday — sell Monday"). This diff — model_state_this_week −
    user_ledger — is a real recurring job we have not built. It is the beating heart of the product and it
    is invisible in a naive "just show the signals" design.

---

## 7. What this implies for the build order

- **Phase B** (pattern + exit map) is *position-scoped and observational* — safe, cheap, no state
  problem. Build next.
- **Phase C** must add THREE Postgres stores, not one: **(a)** immutable published signal snapshots,
  **(b)** the per-user append-only execution ledger, **(c)** durable per-user journey/memory. And the
  **reconciliation job** (§6.10) that diffs model-state against each user's ledger weekly.
- **Phase D** (UI) renders the reconciliation: not "here are signals" but "here is YOUR book vs the
  model's plan, and here is exactly what to do Monday."

The naive version of this product shows the shared model envelope to everyone and calls holdings a
boolean. The correct version treats each user as a separate, durable state machine reconciled weekly
against an immutable snapshot of the model's plan. That difference is the entire foundation.
