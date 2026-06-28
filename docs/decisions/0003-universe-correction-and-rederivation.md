# ADR-0003 — Fix the Universe Before Live: Stage B Corrected-Universe Re-derivation

**Status:** Accepted  
**Date:** 2026-06-27  
**Deciders:** Owner  
**Related:** `docs/ROADMAP.md` Stage B, `research/overlay_registry.md` U-001/U-002/U-003,
`docs/LIVE_OVERLAY_PROTOCOL.md` §6a (heavy path)

---

## Context

### What the Phase-1 wiring audit found

The Phase-1 audit (`long_horizon/audit/wiring_issues.md`, commits `ab585c3` + `b653f52`)
identified three universe-level defects that are live right now — in both the paper cron
and in the research backtest the headline numbers came from:

**W-01 (HIGH) — Demerger back-adjustment fabricates slopes.**  
`data_store.py::clean_ohlcv_for_features` treats any ≥50% single-session price drop as a
stock split and back-adjusts all pre-event bars. For genuine corporate demergers — where a
subsidiary is spun off at roughly market value, collapsing the parent price — this is wrong:
the pre-event prices are correct and should not be restated. The result is a fabricated soaring
slope. VEDL is the documented instance: pre/post prices back-adjusted from ~2.16 to ~24.94,
producing an `sma200_slope_63` that appears to be a strong uptrend when the stock actually
went sideways. The safe hardening shipped a quarantine guard (skip VEDL for new entries) but
the root cause — the inability to distinguish splits from demergers — is not fixed.

**W-02 (HIGH) — 48 current Nifty-500 members are invisible to the universe.**  
`ds.stocks` is seeded from `fundamentals_pit_screener.pkl` (the Screener fundamentals store).
The 48 names that are current Nifty-500 members but absent from that store are never
downloaded, never scored, and never eligible for the portfolio. They are not small or illiquid
names being filtered — they are simply absent from the data pipeline's starting set. W-02 was
mitigated in Phase 1 by an `AUD-007:` diagnostic print each run, but the universe itself is
not corrected.

**W-04 (HIGH) — The D/E solvency filter silently drops the entire financial sector.**  
Screener reports `D/E = NaN` for deposit-taking banks and lending NBFCs because their balance
sheets are structured around customer deposits, not conventional debt. The filter `0 ≤ D/E <
1.5` interprets `NaN` as a failed test and drops these names — including HDFCBANK, ICICIBANK,
SBIN, BAJFINANCE, and approximately 60 other large-cap and mid-cap financials. This is live
equals backtest (a parity non-issue) but it means the "solvent low-debt" universe excludes the
banking sector for a data reason, not an investment reason. The backtest's 30.3% CAGR / 1.15
Sharpe / −40% DD headline is therefore derived on a universe that never includes any bank or
NBFC — regardless of how creditworthy it is. This is a material misrepresentation of what the
strategy can trade.

### Why this matters before real capital

The headline (30.3% CAGR / 1.15 Sharpe / −40% DD / Calmar 0.76, from
`long_horizon/results/cpcv_long_horizon_final_682.json`, frozen-cfg arm) is the number we
would quote to a user and use to set drawdown expectations. It was derived on a universe that:
- Includes at least one name (VEDL) with a fabricated trend slope.
- Is missing 48 current index members entirely.
- Excludes the entire banking and NBFC sector by a data artefact.

Shipping real capital against this baseline would mean trading a corrected strategy that will
behave differently from the backtest — possibly better, possibly worse — without knowing which.
The frozen cfg (stop 3.67×ATR, target 22.52%, trailing activate 4.0% / give-back 4.27%,
min_hold 10, max_hold 63, risk 3.0%, position cap 15%, ADV cap 5%, max 15 names,
`gate_quantile` 0.5) was derived on the uncorrected universe and is therefore also potentially
mis-calibrated: the stop and target distributions will shift on a universe that includes
financials and properly handles demergers.

Under `docs/LIVE_OVERLAY_PROTOCOL.md` §6a, any change to the frozen cfg is a **heavy path**
re-derivation: it requires a new pre-registration, a full walk-forward re-deriving params per
fold, a golden-master regeneration, and an updated `expected_portfolio_metrics` in config.json.
A universe change is a `cfg`-class change — it changes what the strategy trades, which changes
all calibrated parameters.

---

## Decision

**Fix the universe before committing real capital. Do not ship the frozen base against real
capital on a known-defective universe.**

Stage B of the destination-ordered roadmap (see `docs/ROADMAP.md`) implements the corrected
universe and re-derives the frozen cfg on it. This is the sanctioned heavy path per
`docs/LIVE_OVERLAY_PROTOCOL.md` §6a — not a casual relitigation of the frozen base, but an
acknowledgement that the base was derived on incorrect inputs and must be re-grounded.

Stage B consists of four sequential substages, each gated before the next:

### B1 — CA-type-aware OHLCV cleaner (the W-01 root fix)

Extend `data_store.py::clean_ohlcv_for_features` to cross-reference `yf.Ticker.actions`
when a ≥50% single-session drop is detected. Classify the event as:
- **Split** (Ticker.actions shows a stock split): back-adjust pre-event bars as today (correct).
- **Demerger or special dividend** (no matching split action, or the price-ratio matches a known
  demerger): NaN the `sma200_slope_63` for this name until 263 clean post-event trading sessions
  accumulate (263 = 200 SMA lookback + 63-day slope window). Do not back-adjust.
- **Ambiguous**: treat as demerger (conservative — better to exclude a name for 263 days than
  to fabricate a slope indefinitely).

**Gate:** requires a golden-master regeneration commit in the same PR. A PR that changes this
logic without regenerating the fixture must be rejected on sight.

### B2 — Universe union: 48 invisible current members + PIT fundamentals for new entrants

Expand `ds.stocks` to `sorted(current_members(membership, today) ∪ set(config.NIFTY_500))`
before the download loop. The 48 new entrants will enter the eligible set.

Because W-04 means most financial-sector entrants have no Screener D/E, this substage is
sequenced after B3. Run B2 and B3 together: the union expands the stock list; B3's policy
determines how the new names are filtered. The sequencing is:

```
B2 (union) + B3 (financials policy) → sourced together
→ then baseline panel coverage check (all names in [2019, 2026) must have OHLCV)
→ then B4 re-derivation
```

For any new entrant that lacks a historical fundamentals record, source PIT OHLCV through the
existing incremental downloader and accept the D/E filter outcome per B3's policy (either
included via the capital-adequacy proxy or excluded with a loud diagnostic — not silently
dropped as today).

### B3 — Financials sector: capital-adequacy proxy for D/E

Replace the unconditional `0 ≤ D/E < 1.5` filter with a sector-aware policy:

- **Non-financial names (GICS sector ≠ Financials):** keep `0 ≤ D/E < 1.5` unchanged.
- **Banks and lending NBFCs (GICS Financials, deposit-takers and regulated lenders):**
  substitute a Tier-1 capital adequacy ratio proxy. Candidates (pick one; document in
  `STRATEGY_FULL.md §3`):
  - Screener: `CET1 > 0` or `Capital Adequacy Ratio > 12%` (the RBI minimum is 9%; 12% is
    a conservative buffer).
  - Fallback if the data is absent: exclude the name with an explicit diagnostic (`AUD-007:`
    category `missing_capital_adequacy`) rather than a silent drop.
- **Insurance and asset managers (GICS Financials, non-bank):** treat as non-financial for
  D/E purposes (these companies do not hold customer deposits and their leverage is different
  in kind). Standard `0 ≤ D/E < 1.5` applies.

The policy decision (which proxy, which threshold) is the owner's call and must be documented
in `STRATEGY_FULL.md §3` before B4 begins. This is not a parameter the research session
chooses independently.

### B4 — Re-derive the frozen cfg on the corrected universe; regenerate the golden master; restart the paper book

Once B1–B3 are complete:

1. **New pre-registration** (following `docs/LIVE_OVERLAY_PROTOCOL.md` §2): file a pre-reg
   under `research/preregistry/` naming the corrected universe as the new base and the
   walk-forward verdict criteria.
2. **Full walk-forward re-derivation**: re-derive stop/target/trailing/hold/sizing on the
   pre-2017 train slice using the corrected universe; confirm the derived values are stable
   across expanding-window folds. Accept the new derived values even if they differ from the
   current frozen cfg.
3. **Replace `models/long_horizon/config.json → cfg`** with the newly derived values in a
   single commit that also carries:
   - The regenerated golden-master fixture (the existing `tests/test_long_horizon_golden.py`
     byte-compare will go red on the current fixture; the PR must include a clean regeneration
     via the documented build command).
   - Updated `expected_portfolio_metrics` in config.json (the new CAGR / Sharpe / DD /
     Calmar / trades-per-year from the corrected walk-forward).
   - Updated `long_horizon/results/baseline_v1.json` (committed; the new anchor for all
     subsequent research comparisons).
4. **Restart the paper book**: the existing paper book was seeded on the old cfg and the old
   (defective) universe. The paper-gate clock resets at B4. The pre-committed gate to real
   capital (≥30 paper trades / ~2 months reviewed) runs fresh from the first cron that fires
   under the new cfg.

---

## Consequences

### What improves

- **The headline is honest.** The CAGR / Sharpe / DD figures in `expected_portfolio_metrics`
  will reflect a universe that includes the full Nifty-500 membership (including financials,
  including demerger-safe names). Whatever the new number is, it is the number the live
  strategy actually trades.
- **The frozen cfg is calibrated to the correct data.** Stop multiples, profit targets, and
  trailing bands derived on the corrected universe are not contaminated by fabricated slopes or
  a systematically narrow universe.
- **The financial sector is no longer silently absent.** A universe that can consider HDFCBANK,
  ICICIBANK, and BAJFINANCE when they rank highly is materially different from one that cannot.
  The extent of this effect will be visible in the new baseline metrics.

### What gets harder

1. **Path to first real rupee is materially longer.** Stage B adds: the CA-type cleaner (B1),
   the universe union + PIT sourcing (B2), the financials policy + data work (B3), and then a
   full walk-forward re-derivation + paper-book restart (B4). After B4 the paper-gate clock
   runs for a fresh ~2-month / ≥30-trade window before any real capital. The total delay is
   real and accepted.

2. **The headline will likely move.** Adding financials (momentum-rich in bull years) may lift
   CAGR. Fixing demerger contamination may reduce it. Re-deriving the cfg on the corrected
   universe can shift stop / target / trailing band values; those shifts propagate through
   every downstream number. The correct stance is: **anchor to the honest new number, not the
   30.26% that was quoted before this decision**. The 30.26% / 1.15 Sharpe / −40% DD remains
   the reference for Phase-1 hardening purposes only; baseline_v1 replaces it as the live
   anchor after B4.

3. **The paper-gate clock resets.** The paper book that started 2026-06-25 was seeded on the
   old cfg. Its trade history is not invalidated — it remains a useful observation — but it
   does not count toward the ≥30-trade gate under the new cfg. The gate clock starts at the
   first B4 cron run.

4. **The golden master is intentionally regenerated.** Any session that sees the golden-master
   test go red after B4 without a corresponding golden-master regeneration commit in the same
   PR should treat it as an unintended cfg change, not as a test to fix. The B4 PR is the
   only legitimate place for a golden-master regeneration during Stage B.

---

## Alternatives considered

### A — Defer the universe fix; ship the current frozen base to real capital

The uncorrected base could go live immediately (the paper book exists, the cron runs, the kill
switch is wired). The argument: the 30.26% CAGR is still a defensible research headline even
on the defective universe; the financial-sector exclusion is consistent between live and
backtest (no parity bug); the VEDL demerger guard prevents new position entries.

**Rejected.** The paper gate exists precisely because a strategy that has never traded real
rupees deserves scrutiny before it does. Knowing the universe has three material defects and
choosing to ship anyway is not "paper-gate-cleared" — it is choosing to discover the calibration
error post-trade. The financial sector is 20–25% of the Nifty-500 by weight; a strategy that
cannot consider any of those names when they are ranking first is not the strategy the universe
filter was designed to produce.

### B — Narrow fixes without re-derivation: patch W-01/W-02/W-04, keep the current cfg frozen

Apply the cleaner (B1), expand the universe (B2), add the capital-adequacy proxy (B3), but
treat these as "data fixes" rather than "strategy changes" and keep the current frozen cfg
values (stop 3.67, target 22.52%, etc.) unchanged.

**Rejected.** Under `docs/LIVE_OVERLAY_PROTOCOL.md` §6a, a universe change is a cfg-class
change: the stop-loss multiplier was calibrated to the adverse-excursion distribution of a
universe that excluded financials and included at least one demerger-contaminated slope. A bank
like SBIN has a materially different ATR-relative drawdown profile from the industrials and
IT names that dominate the current universe. Keeping the old cfg after a major universe
expansion is keeping parameters calibrated for a different problem. The walk-forward will show
whether the values happen to be robust — or whether they need adjustment. The correct path is
to let the data answer that, not to declare them frozen for convenience.

### C — Fix W-04 only (financials capital-adequacy proxy) without W-01/W-02

A smaller-scope option: add the capital-adequacy proxy now, keep the other defects deferred,
run a partial re-derivation.

**Rejected.** The three defects are tightly coupled: the 48 invisible names (W-02) include
financial names that W-04 would affect; VEDL's contaminated slope (W-01) affects the
rank-distribution that the cfg stop/target is calibrated against. Fixing them piecemeal and
re-deriving after each fix produces a sequence of partially-corrected baselines rather than
one clean corrected universe. The cleaner path is one Stage B block that fixes all three and
re-derives once.

---

## Cross-references

| Reference | What it specifies |
|---|---|
| `docs/ROADMAP.md` Stage B | The four-substage plan with gates and sequencing |
| `docs/ROADMAP.md` Stage A | The `src/research/` harness that Stage C and beyond depend on; runs in parallel with B1–B3 setup |
| `docs/LIVE_OVERLAY_PROTOCOL.md` §6a | The heavy-path governance for `cfg` changes: pre-reg, walk-forward, golden master, owner approval |
| `research/overlay_registry.md` U-001 | W-01 universe defect record (demerger/split contamination) |
| `research/overlay_registry.md` U-002 | W-02 universe defect record (48 invisible members) |
| `research/overlay_registry.md` U-003 | W-04 universe defect record (D/E filter, financials) |
| `long_horizon/audit/wiring_issues.md` W-01, W-02, W-04 | Original audit findings with severity assessments |
| `long_horizon/audit/PHASE1_FIXES.md` | What was shipped in Phase 1 (safe hardening only; root fixes deferred here) |
| `models/long_horizon/config.json → cfg` | The current frozen parameters (unchanged by this ADR; will change at B4) |
| `tests/test_long_horizon_golden.py` | The byte-compare test that must be regenerated in the B4 PR |

---

## Operating rules derived from this decision

1. **No real capital until B4 is complete and the paper-gate clock (≥30 trades / ~2 months)
   has run under the new cfg.** The current paper book does not satisfy this gate even if it
   accumulates 30 trades before B4 — the gate is tied to the corrected cfg, not the old one.

2. **Do not quote the 30.26% CAGR as the live strategy's headline after B4.** The old number
   was derived on the uncorrected universe. Once `expected_portfolio_metrics` is updated in
   B4, the new numbers in config.json are the canonical reference.

3. **Stage A (harness) and Stage B (universe) run in parallel up to B4.** B1–B3 are data and
   code work; Stage A is statistical harness work (`src/research/`). Both can proceed
   simultaneously. B4 (re-derivation and paper restart) blocks only on B1–B3 being complete —
   it does not require Stage A to be finished, though the harness should be complete before any
   Stage C / D research begins on the corrected baseline.

4. **Any PR that touches `data_store.py::clean_ohlcv_for_features`** (the demerger-fix path)
   must include a golden-master regeneration commit per `docs/LIVE_OVERLAY_PROTOCOL.md` §6a.
   The golden master going red without that regeneration is a signal that something else
   changed unexpectedly — investigate, do not suppress.

5. **The financials capital-adequacy policy** (which proxy, which threshold) is an owner
   decision documented in `STRATEGY_FULL.md §3` before any B4 re-derivation begins. The
   research session does not choose this policy independently.
