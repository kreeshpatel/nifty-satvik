# §3 Forward-wall audit

**Pre-committed criteria (forward/prereg.md, verbatim):**
> "**All three books begin in PAPER (Phase A).** The base transitions to small real capital only in
> Phase B, and only via a dated §10 amendment once the repo's **pre-committed paper gate is met**
> (`skills/portfolio-simulation`: **≥ 30 closed trades AND ~2 months** of paper)."
> "Thresholds are the backtest's own rolling-12-month distribution"
> "Red is a *review* trigger, not an auto-halt"

**Machinery:** `scripts/audit_forward_wall.py` — fixture-tested 5/5 (tamper detection, halt breach,
gate counts, sleeve completeness, config drift). **The live wall logs were NOT read during the build**
(no-peeking held); September runs it against the live logs for the first time.

**EVIDENCE (September fills):**
- [ ] chain verification result (live)
- [ ] paper-gate counts per book
- [ ] halt events + sleeve completeness
- [ ] config-drift result vs prereg.md frozen keys

---

## Update 2026-08-11 — why 0001's forward record is still empty, diagnosed

Prompted by the owner asking to run 0001 momentum live beside the swing book. The momentum forward
wall is **already wired** — `cron-forward-wall.yml` → `scripts/run_paper_cron.py` →
`nq.paper.wall_cron.update_wall` — and it is **not** an unwired-producer problem.

It is blocked, correctly, by its own liveness guard. `data/ff_india_factors.parquet` ends
**2026-06-29** (2,162 rows). The wall would log sessions after that, and
`_assert_veto_arm_live` refuses because the veto-0.1 arm has **no residual ranks** past the factor
data's coverage — it will not log a veto book byte-identical to base. Confirmed: calling the guard
with `covered_through=2026-06-29` and dates `2026-07-02..09` raises `VetoArmUnavailable`. This is the
same data-freeze class as the swing OHLCV top-up bug fixed 2026-08-11; the guard fails closed, which
is right.

**So the wall cannot accrue until one of two owner decisions is taken**, both already on this review:

1. **Retire the veto-0.1 arm** (the §6 decision on this agenda). With no veto arm, the wall logs base
   + drift-degross and starts accruing 0001's forward record immediately. Cheapest unblock.
2. **Refresh `ff_india_factors`** past 2026-06-29 so the veto arm has residuals. This is a
   factor-data acquisition, not a config change, and funds the arm rather than retiring it.

Neither is taken unilaterally: (1) amends a registered pre-reg arm, (2) sources external factor data.
Both are the owner's call, and this diagnosis is why the "veto arm — retire or fund" item is now also
the gate on whether 0001 gets a live forward record at all.

---

## Update 2026-08-12 — the wall cron now fails RED every weekday; the concrete runner cause

The forward-wall cron (`cron-forward-wall.yml`, `0 13 * * 1-5`) has failed every trading day (08-10,
08-11, 08-12 confirmed). Exact chain, from run 31605608695:

```
forward-wall: SKIPPED (FileNotFoundError: .../data/ff_india_factors.parquet)
→ results/forward_wall.csv never produced
→ commit step `need results/forward_wall.csv` → "::error:: the wall produced no log" → exit 1
```

This is a **sharper** cause than the 2026-08-11 note above (which described the factor data as *stale*
locally). On the CI runner the factor panel is not stale — it is **absent**: `data/ff_india_factors.parquet`
is gitignored (`/data/*`), and **no workflow builds it.** A builder exists —
`pipelines/build/build_ff_india_factors.py` — and its inputs are present on the runner
(`data/fundamentals_pit_screener.pkl` is committed/whitelisted; OHLCV is downloaded by the cron), so
the panel *could* be built there. The workflow simply never calls the builder; it runs only
`run_paper_cron.py`. The output contract failing red is the guard working, not the bug.

So the daily red is the veto-arm strand of §6 made concrete, and there are three responses, all owner
calls because they touch a registered pre-reg arm:

1. **Fund it — add a build step.** Insert `python pipelines/build/build_ff_india_factors.py` before
   `run_paper_cron.py` in the workflow. Lowest-effort, and it lets the wall accrue the forward
   evidence the Oct-1 decision needs (accruing ≠ promoting). **Caveat, unverified:** the HML factor
   depends on `bp` from the committed fundamentals scrape; if that scrape ends ~2026-06-29, HML — and
   therefore the residual ranks the veto arm needs — may still not extend to recent weeks even after
   a build. Confirm the built panel's date range on the runner before trusting this as a full fix.
2. **Retire the veto arm** (the §6 "retire" branch). Then the wall logs base-swing + drift-degross,
   which need no factor data, and starts accruing immediately. This pre-empts the Oct-1 promote/kill
   in the "kill" direction, so it is an owner decision, not a cron fix.
3. **Stop the daily red without deciding** — e.g. demote `forward_wall.csv` from `need` to `opt`, or
   pause the schedule until Oct-1. Silences a real "wall not producing" signal the contract author
   made loud on purpose; a stopgap, not a fix.

Note the base-swing forward record is blocked by this too: `_assert_veto_arm_live` refuses to log the
WHOLE wall when the veto arm cannot fire, so the certifier book is not accruing either. That raises the
priority of resolving the veto-arm question above "wait until Oct-1".
