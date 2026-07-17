# ADR 0011 — Drop the per-user broker (Kite) trading connection; users execute on their own broker

**Date:** 2026-07-16
**Status:** ACCEPTED (owner decision)
**Affects:** the product planes designed in `docs/PRODUCT_*` and `docs/QUESTIONING_THE_FOUNDATIONS.md`.

## Decision

The app will **not** connect to a user's trading account. Users see the model's actions (buy cards, exit
instructions) on the website and **execute everything themselves on their own broker.** The one-click
in-app order placement and the per-user Kite login are dropped.

## Scope — what is dropped vs what stays

**Dropped (per-user trading integration):**
- Per-user Kite OAuth login / `kite_sessions` table + `KiteSession` model (per-user encrypted token).
- In-app order placement: `routers/nq_orders.py`, `routers/kite.py` (per-user Kite proxy), `reconcile_drift`.
- The order-push side of the WebSocket, the Kite `/auth/callback` trading flow, and any frontend
  "connect broker / Buy / Sell" controls.

**Unchanged (owner-side, centralized):**
- The **owner's market-data Kite app** for quotes/LTP (centralized + cached — memory `kite-market-data-owner-app`).
  Live prices on cards still work.
- `cron-kite-refresh` (refreshes the **owner** market-data session, not per-user).

## Why this matters — the design consequences

### 1. The "two classes of user" distinction collapses to ONE (supersedes PRODUCT_LAYERS §28)
There are no longer in-app executors with broker-confirmed fills. **Every user is a self-reported
executor.** Therefore:
- **Fills are never broker-confirmed** — `fill_source` is always `self_reported`. The product must never
  present a self-reported number as verified (performance claims, disputes, the discipline-score
  fill-slippage metric all inherit this).
- **Reconciliation is always a conversation**, never automatic: "the model exited your runner Friday — did
  you sell? at what price?" The user execution ledger (Phase C) is entirely user-authored.
- This *simplifies* the build (no per-user Kite auth, no order state machine) but *hardens* the ledger's
  trust model (self-report only).

### 2. P's execution-sensitivity is now FULLY the user's manual burden (sharpens QUESTIONING §23)
We shipped P, whose 40%@2R tranche is an **intraweek resting limit.** The earlier recommendation was to
*auto-place* that limit + stop via Kite for in-app users. **That option is gone.** The product can only
**instruct**, not place. So:
- Onboarding must make "place a SELL LIMIT for 40% at ₹X and a SELL STOP for all at ₹Y on your broker the
  moment you fill" a hard, checkbox-confirmed step — not a suggestion.
- The behavioral "co-place at buy" default becomes "**co-instruct at buy** + confirm you placed both."
- The risk that a user "just watches" and gets an untested worse variant of P is now higher, because we
  cannot backstop it with automation. This is a real cost of pairing the execution-sensitive config (P)
  with the no-automation product — worth keeping visible.

### 3. The monitor/nudge still adds value — but confirms nothing
We still see the market price (owner quotes), so the daily monitor can detect "price crossed 2R" and nudge
**"your 2R target was reached — confirm your limit filled,"** and "the runner's SMA broke — sell Monday."
It just cannot observe the user's actual execution. Nudges are interrogative, never assertive.

### 4. Compliance posture IMPROVES (relevant to the QUESTIONING §B questions — still verify)
The positioning/compliance thread flagged that one-click Kite routing + per-account sizing pushed the
product toward regulated **execution/advice**. Dropping the trading connection moves it firmly toward
"**research tool — you execute on your own broker**," the safer side of the RA/IA line. This removes one
factor, but does **not** resolve the open questions: per-user position sizing and imperative "buy/sell"
strings remain items to verify with a SEBI-qualified professional. Not legal advice — the classification
questions in QUESTIONING §B still stand.

## Consequences / follow-ups

- **Dead/dormant code** (audit before removal): `routers/kite.py`, `routers/nq_orders.py`, `kite_sessions`
  table + `KiteSession`, the Kite trading `/auth/callback`, the order WebSocket path, `reconcile_drift`,
  and the frontend broker-connect/Buy/Sell UI. **Not removed in this ADR** — flagged for a decision on
  prune-now vs leave-dormant (precedent: the HDFC market-data swap was left dormant, memory
  `hdfc-market-data-swap`).
- **No strategy impact:** research plane untouched, golden byte-identical, no trial.
- **Phase C ledger design** should be built self-report-only from the start (single `fill_source`), which
  is simpler than the two-path design in PRODUCT_LAYERS §28.
- **Guidance layer** (PRODUCT_LAYERS §11) is unchanged in spirit but every "sell / buy" instruction is now
  strictly "do this on your broker," reinforcing the research-not-advice framing.

## Supersedes / amends
- `PRODUCT_LAYERS_BRAINSTORM.md` §28 (two user classes → one self-reported class).
- `QUESTIONING_THE_FOUNDATIONS.md` §23 (auto-place-via-Kite mitigation removed; manual-only) and the §B
  compliance context (one factor removed, questions still open).
- `PRODUCT_SYNTHESIS.md` §1 ("co-place resting orders … auto-place via Kite" → co-instruct + confirm).
