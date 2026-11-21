# DRAFT — amendment: the exploration lane

**Status: DRAFT for the owner's signature at the January 2027 review. Not in force until signed and dated into
`forward/amendments/`.** Nothing in the repo changes with this draft. Standing counts when drafted: **screens 25 · sealed
opens 4 · n_trials 3** (`diagnostics/research/n_trials.json`, `diagnostics/research/label_screen_ledger.md`,
2026-11-20).

**Goal link.** The mission needs a strategy that beats the index after cost and tax with a forward record. The
evidence to date (`forward/drafts/2027-01/review_dossier.md` §1–3) gives no deflated edge for 0001 or swing. The lane is
a fixed, counted way to keep searching while core capital sits in the fallback, without spending multiplicity off the
books or touching capital.

---

## Amendment 2027-01-__ — exploration lane

### 1. Budget
- **15 trials per calendar quarter.** Every trial is counted in `diagnostics/research/n_trials.json` before it runs,
  in its own commit.
- Unused budget does not carry over.
- Screens are counted in `diagnostics/research/label_screen_ledger.md` as now; a screen is not a trial.
- The deflated hurdle rises with the count (dossier §10: |t| ≥ 3.57 at 141 lifetime trials). Each trial raises the bar
  for every later candidate. That is the price of the lane, and it is accepted here.

### 2. Every experiment is pre-registered
Before any run, a committed pre-registration (`/pre-register`) states:
- the **economic reason**: who is on the other side of the trade, and why the edge should persist;
- the **kill result**: the number, fixed before the run, that ends the candidate;
- the **trial cost**: how many trials it spends against the quarter's 15;
- the metric formulas with `file:line`, the data window, the universe and how overlapping samples are handled
  (CLAUDE.md verification rule 1).

Order, which cannot be recovered once broken: pre-registration committed → counter incremented → run.

### 3. Labels and data
- Every lane result is labelled **EXPLORATORY** in its report and in the registry.
- The **holdout** (strategy data after 2024-06-30) and the **sealed slices** (banked labels with `entry_date` >
  2024-06-30; the sealed judge log) are never read. The holdout guard (`nq.research.holdout`) applies to every return
  statistic.
- UNDERPOWERED and KILL are first-class outcomes.

### 4. Nothing reaches capital from the lane
- A lane result can only nominate a candidate for **paper**.
- Capital needs **26 weeks of forward paper** and a **quarterly review** decision, and the dossier §10 gate (the later
  of the deflated hurdle and 26 weeks).

### 5. Queue order
1. **Company engine 0153, layer L1** (earnings-trend forecast).
2. **0153 L5** (stock-specific crash risk, an exclusion; debt/equity only as an add-on, per the 2026-11-20 note).
3. **0153 L2 / L3** (earnings surprise, earnings seasonality).
4. **0153 L4** (spill-over), only if the earlier layers pass, as 0153 states.

0153 must itself be signed before any of its layers runs. Its own accounting (each layer one screen, the combined book
one trial) applies inside the lane budget.

### 6. The wall rule
When a gate blocks a candidate:
- record the kill, with its number, in the registry;
- take the next candidate in the queue;
- **never relax the gate**, re-tune toward a pass or re-run the same idea with a changed threshold.
A gate changes only by a separate amendment at a quarterly review, never in response to a candidate it blocked.

### 7. Owner time
- **At most 1 hour a week** of owner time for the lane: reading the weekly status and signing pre-registrations.
- If the lane needs more, the queue slows; the budget does not grow.

### 8. Review
- Each quarterly review reports: trials spent / 15, kills with their numbers, candidates on paper and their weeks.

---

## Owner signature

Signed: ______________________  Date: ____________
