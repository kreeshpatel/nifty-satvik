# 08 — HEG's demerger convention: the decision packet

**Class: GOVERNANCE — owner decision at the 2026-10-01 review. Nothing here decides it.**
Phase 0 item **A5** of the 2026-09-25 development plan. No trial, no screen row, no sealed open.
Standing counts unchanged: **screens 20 · sealed opens 3 · n_trials 2.** Assembled **2026-09-27**.

**The decision, in one line:** populate the `convention` column for HEG (row 59 of
`data/corporate_actions_demerger_register.csv`), which reads **`UNDECIDED`**, and say whether that
choice is HEG-specific or the register's standing policy.

`§10` of [`oct1_binder_decisions.md`](../oct1_binder_decisions.md) is the authority and its rule stands:
*populating `convention` is the decision, not a data-entry step.* `data/corporate_actions_demergers.csv`
— the file the cleaner actually reads — is **unchanged** and names 4 of the 38 events.

---

## What has changed since the binder's addendum (2026-09-09), and it is substantial

The addendum was written before **B′** became a standing rule (owner decision 2026-09-15, PR #98).
**Three of its statements are now stale, and they are the three that framed the decision.**

| the addendum says | as of 2026-09-27 |
|---|---|
| *"The book models neither — it holds HEG and has no representation for shares received in the demerged entity."* | **No longer true.** B′ *is* that representation: it realises the carved-out slice at the prior close, credits it to cash, and carries the remaining shares re-based. |
| the gap between conventions is *"roughly 6R on one position"*, and *"would also enter `signals_history_weekly.json`"* | **Superseded.** No −6.02R exit was booked. HEG was credited **+0.7216R** and remains **open**; its monitor row reads `r_multiple −0.32`. Nothing entered the closed-trade history. |
| operational fact 1: the monitor *"is currently emitting a false alarm"* — `STOP_BREACH`, severity high, comparing post-event rupees to a ₹585 pre-event stop | **Resolved.** HEG's `flags` are empty and its monitor row reads `entry 242.95`, `stop 218.66`, `stop_breached: false`. |
| operational fact 2: *"no existing guard covers this class"* — `nq.data.adjustment_guard`'s probe reference ends 2026-06-24 | **Stands.** Verified: `data/raw_close_reference.parquet` spans 2017-02-23 … **2026-06-24**, and HEG's own probes end **2026-05-15**. The guard is structurally blind to any event after the reference ends, including this one. |

**So the live question is no longer "which of two errors do we make".** The book already makes a third,
deliberate choice. What the review decides is whether to **write that choice down** as the register's
convention, and whether it is the right one.

---

## The three columns

The binder stated two. B′ is the third, and it is the one in force.

### A · Back-adjust (total-return)

Rebase history so the series is continuous: ÷2.675 for HEG, and the 44-week line falls
**567.64 → 215.85**.

- **Asserts:** the holder kept the spun-off value, so the price series should not show a fall.
- **Against it, in this repo's own words:** `data/corporate_actions_demergers.csv` exists precisely to
  stop the cleaner doing this, because back-adjusting a demerger *"FABRICATES a soaring trend slope
  (e.g. VEDL: raw sma200_slope_63 2.16 → 24.94)"*. The strategy ranks on trend slope.
- **Vendor behaviour on HEG:** the vendor did **not** do this — `vendor_treatment = LEFT_AS_CLIFF`,
  `implied_factor 0.99438` (that residual is the 2026-07-22 ₹3.40 dividend, not the demerger).

### B · Leave the cliff (listed-entity)

History untouched; the listed company genuinely shrank.

- **Asserts:** the value simply left, and smoothing invents trend that never existed.
- **This is the repo's stated convention**, and what an exchange listing applies.
- **Consequence had it been applied to the live position:** 258.60 against a ₹585.00 stop → an exit at
  roughly **−6.02R**. This did not happen, because B′ intervened.

### C · Represent the spun shares — **B′, what the book does today**

Realise the carved-out slice at the prior close, credit it, carry the remainder re-based.
`R94._apply_demerger`; owner decision 2026-09-15; `models/bhanushali_weekly/config.json` block
`live_corporate_actions_change`.

Measured on the live position:

| | value |
|---|---|
| ex-date | 2026-09-07 |
| prior close → post | 728.25 → 272.20 (`series_return_at_ex` −0.626227) |
| retained fraction | 0.373773 |
| spin value per share | ₹456.05 |
| credit to cash | **₹139,521.35** on 305.9344 shares |
| R credited | **+0.7216** |
| entry re-based | 650.00 → **242.95** (monitor) / 244.07 (portfolio) |
| stop re-based | 585.00 → **218.66** |

- **Asserts:** the holder received value as shares of the new entity, and the book should recognise it
  rather than book a phantom loss or pretend the fall never happened.
- **The known weakness, stated:** the credit is taken at the *prior close* as a cash equivalent. The
  owner actually holds **shares in the demerged entity**, whose price moves after the ex-date. B′
  freezes that value at one instant; the book has no position in the new entity and will not track it.
  So B′ is not "correct" either — it is a third, smaller, and **bounded** error, and the direction is
  knowable: if the spun entity rises after listing the book understates, and if it falls the book
  overstates.
- **Two artifacts disagree about the numbers** (finding 0147): `paper_portfolio_weekly.json` records the
  credit as ₹139,521.35 / 305.9344 sh / `r_credited 0.7216`; `results/attribution_ledger.csv` records
  **₹140,323.02 / 307.6923 / 0.7539** — an ₹801.67 gap from a price restatement. Whichever convention
  is adopted, **one of these figures is the one of record and the review should say which.**

---

## A live operational defect found while assembling this, and it is dated

The position is re-based; **one number beside it is not.**

`results/weekly_monitor.json`, HEG, as of 2026-09-24:

| field | value |
|---|---|
| `current_price` | 235.25 |
| `entry` / `stop` | 242.95 / 218.66 — **re-based** ✓ |
| `sma20` | **385.65** |
| `implied_trail_sma20` | **370.22** |

`scripts/run_bhanushali_monitor.py::_last_bar` computes `sma20` as the trailing 20-day mean of the
**raw** Close series. HEG's 20-session window still straddles the cliff, so that mean mixes pre-event
rupees (728) with post-event ones (272) and lands **~57% above the current price**. The trail hint
derived from it cannot fire and is not a meaningful level.

**Scope, stated precisely.** This is the weekday **monitor**, which produces card hints and alerts. The
weekly engine decides on its own weekly series and on B′'s `ca_view`; I did **not** verify the engine's
trail path here, and this packet does not claim the engine is affected. **It self-heals** once the
20-session window clears the ex-date — about **2026-10-05** — which makes it a bounded problem that will
have resolved itself by the review's own date. Recorded so nobody reads that trail level in the meantime.

---

## Proposal carried forward, for the review to accept or refuse

**Halt, not flag, on an unregistered value-leaving event.** A held name that gaps past
`BENIGN_FACTOR_MAX` with nothing registered should freeze rather than be stopped out on a re-based
price. The corporate-action HOLD guard (PR #102, `CA_HOLD_DROP`) already implements this shape for the
**live** path. What this proposal adds is that `adjustment_guard`'s coverage gap is the reason the class
was missed at all: its probe reference ends **2026-06-24** and nothing rebuilds it, so it cannot see a
post-reference event. **Funding that rebuild is the prerequisite**, and it is a review decision because
it is a data-pipeline commitment, not a code fix.

## What must not happen here

- Do **not** populate `convention` as a tidy-up. §10's rule is explicit and it is the whole point.
- Do **not** grow `data/corporate_actions_demergers.csv` without an ADR — `tests/test_demerger_register.py`
  guards it, and that guard stays.
- Nothing in this packet is a proposal to change a backtest number, a gate, or the pinned anchor.

## Verification trail for every number above

- Register row 59: `data/corporate_actions_demerger_register.csv` — `LEFT_AS_CLIFF`, `implied_factor`
  0.99438, `series_return_at_ex` −0.626227, `convention` **UNDECIDED**.
- Probe coverage: `data/raw_close_reference.parquet`, 51,057 rows, 2017-02-23 … 2026-06-24; HEG's 80
  probes end 2026-05-15.
- B′ figures: `results/paper_portfolio_weekly.json` → `positions.HEG.corporate_actions[0]`.
- The artifact disagreement: `results/attribution_ledger.csv`, HEG row, `corporate_actions`.
- Monitor figures: `results/weekly_monitor.json` → `monitors[HEG]`, generated 2026-09-25 16:18;
  `flags` contains no HEG entry.
