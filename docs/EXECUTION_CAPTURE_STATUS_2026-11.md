# Execution capture — spec against what is built (2026-11-13)

Compared: `docs/EXECUTION_CAPTURE_SPEC.md` §6 (the build list) against the code on main. Written for ADR-0020, Part F.

**The app has recorded 0 real fills** (`execution_events`, read-only query on production, 2026-11-13). The gap is use,
not code: every item on the build list exists.

| spec §6 item | status | where |
|---|---|---|
| 1. Durable, append-only ledger | **built** | `execution_events` table with an append-only trigger; `services/execution_ledger.py` |
| 2. SELL side, partial quantity and price | **built** | `POST /api/execution/sell`, with tranche (target / pattern / runner / manual) |
| 3. Execution price on both sides | **built** | `price` on buy and sell events |
| 4. The two popups | **built, on This Week** | `ExecutionCaptureModal.jsx`, opened by "Record buy" and "Record sell". The spec placed them on the Signals/Research page; since the v7 redesign they are on This Week only |
| 5. Realised R and P&L from events | **built** | `position_state`; `GET /api/execution/positions` and `/position/{sig}` |
| 6. Reconciliation and discipline score | **built** | `services/reconciliation.py` (exits due, missed exits), `services/discipline.py` |
| Correcting a wrong entry | **built** | `POST /api/execution/correct` appends a superseding event |

## The one gap that was closed here

The minimum the lifecycle needs is manual entry of a fill with **date**, price and quantity, linked to the model trade.
Price, quantity and the link existed. The **date did not reach the ledger from the popup**: the API accepted
`executed_at`, but the popup never sent it, so every fill would have been stamped with the time it was typed in. Past
fills could not be entered with their real dates.

Changed in this PR (about 40 lines):
- The popup has a **Fill date** field, defaulting to today and not allowing a future date.
- The ledger converts the date string to a datetime and refuses a malformed one.

## Tracking error in the weekly report

`pipelines/lifecycle/core.py::tracking_error` compares each real fill with the model's price for that trade:
- a buy against the model entry, a sell against the model exit;
- in basis points of the model price, and in R (the model's entry minus its stop);
- positive means worse for the trader.

The weekly lifecycle report prints it. Today it reads "no fills".

## What is still needed

1. **Enter fills.** Use "Record buy" / "Record sell" on This Week for each new fill. For the 55 live trades so far, enter
   them once from broker contract notes, with their real dates.
2. **Get the fills to the Saturday scan.** The scan runs on GitHub and cannot read the app's database. Two options, an
   owner decision:
   - give the scan workflow a read-only database URL as a secret, and export `execution_events` to
     `results/execution_fills_export.json` in the lifecycle step; or
   - add an export button in the app and commit the file by hand each quarter.
   Until one exists, the report cannot show tracking error even when fills are recorded.
3. **Partial exits.** The model's exit price for a trade that left in tranches is one blended number in
   `signals_history_weekly.json`. A per-tranche comparison needs the tranche prices from `management_events.jsonl`.
4. **Promotion rule.** PILOT → SCALE needs tracking error under 1% a quarter (ADR-0020). That check becomes automatic
   once item 2 is done.
