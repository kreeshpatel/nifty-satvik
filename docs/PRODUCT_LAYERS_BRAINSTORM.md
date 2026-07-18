# Product layers — deep brainstorm (Part 2)

*Continues `PRODUCT_STATE_AND_DATA.md`. Covers the layers above the state/data foundation: the user
journey, nudges, guidance, failure modes, money math, trust, cold-start, audit, and testing — plus the
cross-cutting traps that only show up when you think about the whole thing at once. Design brainstorm, not
a decision record. 2026-07-16.*

---

## 8. The single most dangerous non-obvious trap: a NEW user cannot buy the model's existing holds

The model's paper book started at inception (2026-07-04) and has **ramped over weeks** — it holds ~4-5
names it entered in the past at past prices. A user joining **today** is a **fresh cold start** with zero
positions. Therefore:

> **You must never present the model's current HOLD cards to a new user as "buy these."** Those entries
> happened weeks ago at prices no longer available; their stops and 2R levels are relative to an entry the
> user can't get. A new user may only act on **FRESH buy signals going forward.**

The cron already separates fresh buy cards from held cards, but the *product semantics* must be explicit
and per-user: a held card means "**the model** holds this — informational." Only fresh signals are
"**you** can enter this." This also means **two users who joined on different dates have genuinely
different books forever** — the join date is a permanent fork (this is exactly the cold-start-distribution
result, §16, now made per-user). The "portfolio" a user builds is *their own path from their own start*,
never a copy of the model's mid-flight book.

---

## 9. The user journey is a state machine — and stage is per-user AND per-position

Onboarding "what to keep in mind" is **dynamic per-user state**, not a static page. Milestones:

```
  registered -> funded/sized -> first BUY -> holding -> first 2R (partial exit!) ->
  first PATTERN or RUNNER exit -> first full close -> first LOSS -> steady operator
```

Non-obvious properties:
- **Milestones are irreversible and psychologically loaded.** The *first real loss* is the moment most
  users quit — often at the worst time (the cold-start −11% dip, §16). The system should *detect* "this is
  your first losing close" and respond with the right context ("this is expected; here is the drawdown
  math; the book is judged over years"), not a generic red number.
- **A user is at different stages for different positions simultaneously** — one name at 2R, another
  underwater. Journey stage is per-user *and* per-(user,signal_id). Guidance must be position-aware.
- **Just-in-time teaching beats upfront dumps.** Show "how a partial exit works" the first time one of
  *their* holds hits 2R — not on day one when it is noise. The onboarding list is a *queue of lessons
  unlocked by events*, stored as per-user memory ("has_seen: partial_exit_explainer").

---

## 10. The nudge / action-delivery layer — cadence-locked, idempotent, escalating

Users don't watch screens. The product's job is to deliver the *right action at the right time*, which is
governed by the cadence map (§4):

- **Saturday digest** (after the weekly scan): "Here is Monday's plan — SELL these, the rest hold." This
  is the primary channel; a weekly-swing book is a once-a-week decision.
- **Intraweek alert** (from the daily monitor): "Your 2R limit filled" / "Your stop was hit." Only for the
  *resting-order* tranches (2R, stop) — never for the pattern/runner (those are weekly-close only, §5).
- **Escalation on missed action**: Monday "sell the runner" not confirmed by Tuesday → "You still hold the
  20% runner the model exited Friday." A missed action is a first-class state, not silence.

Non-obvious requirements:
- **Nudges must be idempotent and deduped.** Track `acknowledged` per (user, signal_id, action). Never
  tell a user five times to sell the same tranche. The reconciliation job (§6.10) emits *action items*;
  the nudge layer delivers each *once* until acknowledged.
- **Nudges degrade gracefully.** If we can't confirm a fill (no broker link), the nudge asks ("did you
  sell?") rather than asserting. Never claim an execution we didn't observe.
- **A nudge references its immutable snapshot**, so "why" is always reproducible (§14).

---

## 11. Guidance content model — "specifically tell him what to do" (the owner's ask, made exact)

Every (card state × user-position state) maps to **exactly one unambiguous instruction with a number**.
Ambiguity in trading guidance is a defect. The full enumeration:

| state | the instruction |
|---|---|
| FRESH buy signal | "Buy Mon–Fri inside ₹X–Y. The moment you fill: place a SELL LIMIT for 40% at ₹(2R) and a SELL STOP for all at ₹(stop)." |
| holding, quiet | "Hold. Your 2R limit and stop are resting — nothing to do." |
| 2R filled intraweek | "Your 40% sold at ₹X. 60% remains; stop unchanged; watch Saturday for the pattern/runner." |
| blow-off week (Sat) | "Exhaustion week detected — SELL the 40% pattern tranche at Monday's open. 20% runner remains." |
| runner SMA break (Sat) | "Trend broke below the 44-week SMA — SELL the final 20% at Monday's open. Trade complete." |
| stop hit | "Stopped out at ₹X. Trade complete — do not re-enter unless it signals fresh." |
| missed a Monday sell | "You still hold the [tranche] the model exited [date]. Decide: sell now, or hold off-plan (your call, off-model)." |

Principles: **one number, one verb, one reason (short).** The reason builds trust and teaches; the verb+number is the action. This is the `exit_plan` from Phase A, but *resolved to the user's current state* — i.e. it needs the per-user ledger (§1) to know which tranche they're actually on.

---

## 12. The money-math layer — price is universal, everything else is per-user

- **Quantity** = `min(capital × risk% / (entry − stop), capital × max_notional% ) / entry`, **floored to
  whole shares** (NSE cash — no fractional). Each user's own `default_capital` + `risk_tier`.
- **Tranche rounding is a real decision.** 40% of 17 shares = 6.8. Define it once (e.g. floor the first
  tranches, the runner takes the remainder) so the three tranches always sum to the exact holding.
- **The runner-too-small rule.** After 40% + 40% booked, the 20% runner may be a handful of shares worth
  less than the round-trip brokerage. Define a floor: if the runner is < N shares or < ₹X notional, fold
  it into the pattern tranche (sell 60% at that step). Otherwise you generate dust trades.
- **Capital changes over time.** A user adds/withdraws funds → their per-trade rupee risk changes for
  *new* entries only; open positions keep their original sizing. Sizing always reads *current* capital at
  entry time, snapshotted into the position.
- **Per-user cash contention = per-user cold start.** With their capital tied in 5 names, a new fresh
  signal is skipped *for them* (their own `skipped_cash`). A ₹2L user and a ₹50L user hold a different
  number of names and have different cold-start ramps — the ₹10L cold-start distribution (§16) is *their*
  distribution only at ₹10L. Onboarding sizing must set this expectation per their capital.

---

## 13. Trust, honesty, governance — surfaced, not buried

We are shipping **P**, which the research says is inferior (fails the gate, −40% DD, worse cold-start).
That raises the bar on honesty in the product:

- **Show FORWARD numbers, never the backtest as a forecast.** The Monte-Carlo 27% and the 40R monster are
  in-sample; the MC caveats (`FINDING_pattern_exit`, `mc_year_on_year_P`) say the upside is bull-regime
  luck. The product should display *live forward performance since inception* (N trades, real drawdown),
  and label any backtest chart "historical simulation, not a forecast."
- **The weekly review scorecard already tracks the true gate status** — surface it, don't hide it. A user
  deserves to see the book is FORWARD-WATCH / owner-override, not "certified."
- **The kill-switch is a user-facing state.** The −50% drawdown halt (`forward/prereg.md`) must, if hit,
  tell users STOP — not keep emitting buy cards into a broken book.
- **Compliance copy is centralized** (`frontend/src/lib/signalCopy.js`) — research, not advice; the user
  executes on their own broker. Every action item inherits that framing.

The honest framing is also good product: "here is exactly what the model did and why, forward, warts and
all" builds more trust than a polished backtest curve that reality won't match.

---

## 14. Audit / "why" / per-user reproducibility

A user will ask "**why did you tell me to sell?**" The answer must be reproducible from the **immutable
snapshot + the price data**, not a vanished recompute:

- Every action item stores its cause: "blow-off week of 2026-01-05 — new high 672, closed 574.5 in the
  lower 3% of its range, MFE was 3.2R." Regenerable from the frozen snapshot.
- This is the research program's "reproduce-before-trust" rule (which caught the MC config bug) applied to
  the *user*: no user-facing number that can't be reproduced from committed data + their ledger.
- Disputes ("I sold at ₹X not ₹Y") reconcile the user's actual fill against the model's plan — both are
  stored, so the diff is always answerable.

---

## 15. Failure modes & degraded operation — plan for the unhappy path

| failure | effect | required behaviour |
|---|---|---|
| Saturday scan fails / late | stale envelope | staleness banner ("scan is late — last as-of [date]"); do NOT let users act on last week's plan as if fresh |
| Kite/LTP down | no live price | fall back to Friday close, flag "prices delayed"; never block the weekly decision (it's off the close anyway) |
| missing / late bar for a ticker | 44w SMA / CRS shift → could flip a signal | **data-integrity gate before publish** (the split/bad-tick class, CGCL); don't publish a half-refreshed scan |
| recompute resurrects/vanishes a position | model book jumps | the snapshot boundary (§2) shields users who acted; alert internally |
| GitHub contents API down | envelope unreachable | local-file fallback (exists in `signals.py`) |
| user's broker link expired | can't confirm fills | degrade to "did you sell?" nudges; never assume |
| partial universe refresh | some tickers stale | publish only on a complete, integrity-checked scan; else keep last good |

Principle: **a weekly-swing book fails safe by doing nothing** — the decision is Friday's close, so a
delayed scan or dead LTP does not force an action. The danger is *acting on stale data as if fresh*, so
every card must carry its `as_of` and a freshness state.

---

## 16. Per-user cold start — every new user relives the ramp we measured

`COLD_START_DIST.md` is not just research — it is **each new user's literal first experience**:
- First 2-3 months: ~5-6 concentrated names, biggest ~31% of their book, ~−11% drawdown is *normal*.
- 1-in-4 chance of a down first year purely on *when they joined* (the start-date lottery, made per-user).
- Onboarding must **set this expectation explicitly**, or the first drawdown makes them quit at the worst
  moment. "Do not deploy all your capital on day one; the book fills over weeks as signals fire; expect a
  bumpy first quarter; judge over years."
- A user joining mid-week vs Saturday sees different things — define the first-session experience (probably:
  "the next scan is Saturday; here is how it will work; here is one fresh signal if the window is open").

---

## 17. Cross-cutting traps found while thinking about the whole

1. **Re-entry episodes collide with stale user holds.** A user holds ILC episode-1 (never sold), the model
   exits it and ILC re-signals as episode-2. The user's real book still has episode-1 while the model shows
   episode-2. The ledger keys on `signal_id`-per-episode and must represent "user holds a *prior* episode
   the model has moved on from."
2. **Realized-R attribution is a weighted blend of the user's ACTUAL fills**, across three tranches at three
   times/prices — computed from their executions, never the model's clean 2R/2.5R/SMA numbers.
3. **The "is this week closed?" boundary is fragile and central.** Everything pivots on the ISO-week / Friday
   close (`cur_week_open` in the cron). Holiday-shortened weeks, a mid-week data run, and IST vs UTC all
   attack it. This is a single point of correctness for the entire cadence.
4. **Two clocks + weekend gap.** "Sell at Monday's open" carries weekend-gap risk the backtest prices as the
   Monday open but the user feels as a surprise. State decision-time (Fri close) and action-time (Mon open)
   explicitly so a gap reads as modeled, not a bug.
5. **Idempotency of the reconciliation job.** Running it twice for the same week must produce the same action
   items (no duplicate nudges, no double-counted executions). Reconciliation is `set`-valued, keyed by
   (user, signal_id, tranche, week).
6. **Model paper-NAV ≠ any user's NAV.** The shared paper book's equity curve is one ₹10L path from
   inception; it is *not* what any user experiences. Show the model curve as "the model," each user's real
   NAV (from `nav_history`) as "you," and never conflate them.

---

## 18. Testing a stateful, time-dependent, per-user system

This is the hard part to test and the easy part to get silently wrong:
- **Replay tests:** feed historical weeks through the pipeline, assert the reconciliation emits the correct
  per-user action items for scripted user ledgers (missed a sell, sold early, etc.).
- **Golden per-user journeys:** a fixed synthetic user through a full trade (buy → 2R → pattern → runner)
  with asserted guidance at each step.
- **Idempotency tests:** run the reconciliation twice → identical action set; recompute the envelope twice →
  byte-identical (the existing golden discipline, extended to the product layer).
- **Snapshot-immutability tests:** once published, a signal_id's terms never change even after a model
  recompute with revised data.
- **Cadence tests:** the pattern tranche never fires intraweek; the 2R tranche never waits for Saturday.

---

## 19. Data lineage — one more pass, because it underpins "why"

Every published card should carry: `as_of` (the Friday it was computed off), the OHLCV cache hash, the
membership snapshot date, and the model_version. This makes every card **self-describing and reproducible**
(§14), lets the staleness gate (§15) work, and means a future data correction can be detected as "this card
was built off the pre-correction data" rather than silently overwriting a user's history.

---

## 20. What this all collapses to — the build, made easy by seeing it whole

Three planes, cleanly separated:

- **Research plane** (exists): idempotent, universe-wide, mutable, `results/*.json`. Never touched by user
  state. Keeps its sacred golden.
- **Snapshot plane** (new, Phase C): the immutable boundary. Freezes each published signal_id; the
  reconciliation job diffs model-state vs each user ledger weekly → per-user action items.
- **User plane** (new, Phase C/D): per-user execution ledger + journey memory + NAV; the nudge layer
  delivers action items cadence-locked; the UI renders "your book vs the plan, do this Monday."

With the three planes and the traps above on the table, the build sequence is:
1. **Phase B** — position-scoped pattern + intraweek exit map (safe, observational, no user state).
2. **Phase C** — the snapshot plane + user execution ledger + reconciliation job + journey memory.
3. **Phase D** — the UI: onboarding journey, per-user action items, guidance, honest forward numbers.

Every hard problem (partial fills, missed actions, new-user cold start, "why", re-entry episodes, failure
modes) has a home in this structure. That is the point of writing it all down first.
