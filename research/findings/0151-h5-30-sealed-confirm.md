# 0151 — h5-30 on the sealed slice: KILL (current harness, live book)

**Verdict: KILL (2026-11 harness, live weekly-swing book).** One arm; trial counter 2 → 3, raised in its own commit
before the run. Sealed open S4 spent. Pre-registration: `diagnostics/research/preregistry/0151-h5-caps-off-confirm.md`.
Script: `pipelines/diagnostics/confirm_0151_h5_30.py`. Raw output, committed before this write-up:
`diagnostics/research/confirm/0151_h5_30_result.json`. Red-team read: done 2026-11-13, no gate-flipping defect.

## Step 1 — did anything move?

No. The run matches §2 exactly:
- the books: live config vs h5-30, `{"ext_cap": None, "grade_gate": False, "max_notional_pct": 0.30, "max_risk_pct": None}`;
- the 20 standard paired draws (seed `DEFAULT_SEED`);
- continuous slices of full runs from each path's 2019 start;
- the slice 2024-07-01..2026-06-30, with the last sealed bar 2026-06-29.

Every threshold in §5 is as committed in `a49ab91` (sign-off), and the script was committed in `2e57d8d` before the run.

## Step 2 — gate arithmetic

- **Slicing:** every metric comes from `nq.lab.ensemble.slice_metrics` on one continuous NAV per path. There is no
  fresh-capital reseed.
- **Order:** G0 ran on the train context (prices cut 2024-06-30) before any sealed price was loaded.
- **Plausibility:** the live book's own sealed numbers are negative: median Sharpe −0.41, CAGR −10.4%, MaxDD −33.1%.
  The red-team judged this plausible for 2024-07..2026-06, when the Nifty fell from its September 2024 peak. It also
  checked the data: 710 tickers, all ending 2026-06-29; the only bars moving more than 40% are registered demergers,
  which are fed to both books; no split or missing-bar defect was found. A result worse than base is not leak-shaped.

## Step 3 — the outcome table, filled in

| gate | bar (fixed before the run) | actual | pass |
|---|---|---|---|
| G0 | train median paired ΔSharpe in +0.34 ± 0.10 | **+0.335** | ✓ (sealed read allowed) |
| P1 | median ΔSharpe > 0 **and** ≥ 15 of 20 paths > 0 | median **+0.21**, **14 of 20** | ✗ |
| P2 | median ΔMaxDD ≥ −5.0pp | **−3.9pp** [p5 −10.4, p95 +3.4] | ✓ |
| P3 | unperturbed ΔSharpe not negative on both halves | −1.03 (2024H2–25H1), +0.89 (2025H2–26H1) | ✓ |
| P4 | h5-30 sealed net P&L minus its largest winning trade > live sealed net P&L | −₹8.79L − ₹2.01L = −₹10.80L vs −₹3.81L | ✗ |
| P5 | no h5-30 position above 31% of equity at entry | **31.7%** | ✗ |

Any failed bar → **KILL**. It would have been UNDERPOWERED only if P2, P4 and P5 had all held with P1 failing on the
count alone.

Sealed bands (medians over 20 paths): live Sharpe −0.41 / CAGR −10.4% / MaxDD −33.1% / 42 trades; h5-30 −0.14 /
−5.3% / −37.1% / 47.5 trades. Paired ΔCAGR +3.8pp [−4.8, +11.0].

## Disclosures (from the red-team; none changes a gate)

- **P4 is scale-confounded as written.** It compares rupees, and h5-30 enters the slice with a larger NAV after its
  stronger 2019–24. It fails even without subtracting the best trade, and the red-team's estimate in percentage terms
  (about −14% vs −10%) points the same way. The registered rupee form stands. Future pre-registrations should state P&L
  bars in percent of the slice-start NAV.
- **P5 is probably an entry-day mark, not a fill-cap breach.** It is 0.66pp over a bar that already carried a 1pp
  tolerance, and the first `position_log` row is marked at the entry day's close. It fails as written.
- **The 20 paths are not 20 independent observations.** Many are numerically identical (about 6–8 distinct
  trajectories), so "14 of 20" is weaker evidence in either direction than it reads. §4 already stated the read could
  only refute.
- **P3 passed vacuously.** The two halves offset (−1.03 / +0.89).
- **The slice was not clean for the extension-cap leg** (S4's C2 disclosure: the 2026-07-31 ext-band census read
  sealed-slice outcomes). That cuts toward a false pass, not a false fail, so it does not soften the KILL.
- h5-30 lost less than live on the median path's CAGR (−5.3% vs −10.4%), with a deeper drawdown and a failed P4. That
  is not a PROMOTE signal.

## Root cause — why it did what it did

h5-30's train edge came from two channels: more seats (all grades, no extension cap) and bigger positions in
tight-stop names (30% instead of 20%). Both pay in a trending tape and cost in a falling one.
- **In 2024H2–25H1**, the start of the correction, more and larger positions meant more and larger stop-outs. The
  unperturbed run's h5-30 Sharpe was −1.09 against live's −0.06.
- **In 2025H2–26H1** it recovered faster (+0.51 vs −0.37), as a higher-exposure book does.

So the train window's +0.34 was mostly a bet on the regime. That is the same mechanism the S1 throttle exposes from the
other side: removing exposure in weak tape cuts drawdown and costs return. The train 5th percentile (−0.10) already
warned that the edge was not robust, and the sealed 5th percentile is −0.23.

## Transferability

This binds the **live weekly-swing book** under the current harness: PIT membership, the scaled exit (config P), the
continuous-slice method, and the post-#171/#177 data path. It is a KILL of **h5-30 only**. Per the outcome table, no
other h5 variant may be opened on this slice. Uncapped h5 stays a train-window candidate with no sealed evidence for or
against it, and a test of it would need data the program has not seen: the forward record.

## The more important number

On the sealed slice, the **live book itself** lost money: median Sharpe −0.41, CAGR −10.4%, MaxDD −33.1%, consistent
with its negative forward paper record since 2026-07. The h5 question is second-order to that. The next setup is not
another variant on this slice. It is the regime question: what the book does in a falling market, which the S1, half-size
and results-filter work (all drawdown dials) and the weak-market sleeve proposal address.

## Next setup

- No retune and no re-run of h5-30.
- Record in the 2027-01-01 agenda: h5-30 KILL; uncapped h5 untested on unseen data.
- Read the live book's sealed loss against the forward record at the review.

Standing counts: screens 24 · sealed opens 4 · n_trials 3.
