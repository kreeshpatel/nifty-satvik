# Execution capture — the self-reported buy/sell popup + the durable per-user ledger (spec)

*Owner decision 2026-07-16: with no broker connection (ADR 0011), the website only INSTRUCTS; the user
executes on their own broker and reports back via a popup that asks for the quantity and execution price
of each buy and sell. This is the concrete input to the Phase-C per-user execution ledger. Spec, not a
brainstorm — this drives the build.*

---

## 0. The loop this closes

```
  website INSTRUCTS  ──►  user executes on THEIR broker  ──►  popup CAPTURES (qty + price)
        ▲                                                              │
        └──────────  reconciliation + next instruction  ◄─────────────┘  append to ledger
```

The website is instruction-only ("Buy KotakBank ≤ ₹1,842"; "Sell 40% at Monday's open"). The popup is the
only way execution state enters the system, and every fill is **self-reported** (`fill_source =
self_reported`, ADR 0011) — never presented as verified.

---

## 1. The subtlety that shapes everything: a SELL is not binary

The live book is config P — exits come in **three tranches (40% @ 2R / 40% pattern / 20% runner)**. So
"mark sold" is almost never "sold the whole position." The sell popup must be **partial-aware**:
- capture **qty sold + execution price** for *this* sell,
- track the **running remaining quantity**,
- and (optionally) tag which tranche it corresponds to, or just infer from remaining.

This turns the existing single-row "I bought this" mark into a **position with a list of execution
events** (one buy — or several — plus one-to-three partial sells), each event carrying qty + price +
timestamp. That list *is* the durable ledger.

---

## 2. The two popups

**BUY popup** (when the user marks a signal bought):
- Fields: **quantity**, **buy execution price**.
- **Pre-filled** with the model's suggestion so confirming is one action: qty from the user's sizer
  (`sizePortfolio`/risk tier), price hinted from the model's entry band. User confirms or edits.
- Allows **multiple buys** on one signal (averaging in) → multiple buy events.

**SELL popup** (when the user marks a sell against a held position):
- Fields: **quantity sold** (default = the tranche the model just flagged, e.g. 40% of current holding),
  **sell execution price** (hinted from the model's exit level — 2R price, or the Monday-open flag).
- Shows **remaining after this sell** live, so partial exits are obvious.
- Fires the reconciliation/discipline update on submit.

Both popups: **pre-fill the disciplined default, make the edit the exception** (the behavioral principle —
discipline as the path of least resistance).

---

## 3. Validation — warn, never block

It is the user's capital and their self-report (solo-user context + ADR 0011). So sanity-check and
**warn**, but never hard-block:
- qty ≤ remaining (on sell); qty > 0; price > 0.
- price within the day's traded range (from owner market-data quotes) → soft warning "that price is
  outside today's range — sure?" (catches fat-finger / wrong-day entries) but let them save.
- The user can always override; the ledger records exactly what they said.

---

## 4. The durable ledger (evolves the existing ephemeral mark)

The current `UserHolding` (`database.py`) is **ephemeral (erased on model completion), buy-only, and
overwritten on re-POST** — all three are wrong for a truth-of-record ledger. The evolution:

- **Append-only execution EVENTS**, not overwrites. Each buy/sell is a row: `(user_id, signal_id, side,
  qty, price, executed_at, fill_source='self_reported', created_at)`. Corrections are **new correcting
  events**, never in-place edits — preserves the audit trail the dispute/integrity thread requires.
- **Durable** — the position and its closed record survive completion (replaces erase-on-completion). The
  user's permanent per-user track record lives here, distinct from the model's shared history.
- Keyed by `signal_id = {ticker}__{signal_date}` (the existing canonical key) so a re-signal is a distinct
  position, and a stale prior-episode hold the user never sold is representable (QUESTIONING §17).
- **Realized R / P&L is computed from the actual events** (quantity-weighted across buys and the three
  sells), never from the model's clean 2R/2.5R/SMA numbers — this is the user's truth (PRODUCT_LAYERS §1).

Keep it OUT of the `NQOrder`/Kite tables (now dead per ADR 0011) so self-reported marks never mix with the
old broker-execution machinery.

---

## 5. What the popup feeds

- **Reconciliation** (the weekly diff, model-plan − user-ledger): the popup is the touchpoint that resolves
  each action item. "Model exited your runner Friday" → user sells → popup → item resolved. A missed action
  stays open until a popup (or an explicit "I didn't sell") closes it.
- **Discipline score** (the behavioral gauge): coverage/timing/exit-adherence all read from these events.
  Placing the sell late, or not at all, is now measurable.
- **The user's NAV / realized P&L**: their own curve, shown as truth; the model's paper NAV stays a
  labeled reference ceiling (never "your expected return").

---

## 6. Delta from what exists (build list)

1. Make `UserHolding` (or a new `execution_events` table) **durable + append-only** (drop erase-on-completion;
   stop overwriting on re-POST).
2. Add the **SELL** side (currently only buy is captured) with **partial-qty + price**.
3. Add **execution price** capture on both sides (buy price beyond the model entry; sell price).
4. Add the two **popup UIs** on the Signals/Research page, pre-filled with the disciplined default.
5. Compute **realized R/P&L from events**; expose the user's durable per-position record.
6. Wire the events into **reconciliation + discipline score** (Phase C/D).

No strategy impact — research plane untouched, golden byte-identical, no trial. This is Phase C/D product
work; it should be built self-report-only from the start (ADR 0011).
