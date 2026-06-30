# Stage A — Trustworthy Ground (revised 2026-06-30)

> **Status of this doc.** This REVISES and supersedes the Stage A section of `docs/ROADMAP.md`
> (owner-approved 2026-06-30). It also **absorbs the old Stage B corrected-universe data build**
> into Stage A, because a trustworthy baseline is impossible without it. The ROADMAP remains the
> master for Stages C→G; this is the authority for Stage A.
>
> Why revised: the clean rebuild's first cloud runs exposed that the original gate —
> "frozen-cfg backtest reproduces baseline_v0 (26.11% CAGR) within ≤1pp" — is **not achievable as
> written**. The OHLCV cache that produced baseline_v0 is gone, and yfinance **drifts run-to-run**
> (two smokes: 14.20% → 15.57% CAGR on the same command). A literal byte-reproduction of a number
> built on vanished data is impossible. The honest, stronger trust anchor is already in hand: the
> **golden master proves the rebuilt engine ≡ the validated strategy byte-for-byte**, so any
> baseline difference is attributable to *data*, never the engine.

---

## North-star success criterion

Every number Stage A emits must be:

1. **Byte-reproducible** run-to-run (pinned deps + pinned dataset),
2. on a **precisely-defined universe** with documented in/out/survivorship caveats,
3. backed by the **golden equivalence proof** (engine ≡ validated strategy), and
4. produced by a harness **proven to reject a known-§11-dead lever**.

"Trustworthy ground" = we trust the harness and the baseline *before* any overlay research or
trade. A defensible, reproducible, well-caveated baseline beats a flattering, irreproducible one.

---

## Locked owner decisions (2026-06-30)

- **D-A1 — Baseline gate = fresh pinned baseline + explained Δ.** The golden proves the engine;
  Stage A pins a reproducible baseline on the corrected universe and *explains* `|Δ vs baseline_v0
  26.11%|` as data (universe composition + yfinance vintage). ≤1pp ⇒ call it "reproduced"; otherwise
  anchor the fresh pinned number (this becomes **baseline_v1**). No chasing vanished data.
- **D-A2 — Stage A absorbs the corrected-universe build.** A trustworthy baseline requires the
  corrected universe (current ∪ NIFTY_500 + financials policy + delisted rehydration), so that work
  moves into Stage A (A3). `baseline_v1` is the Stage-A anchor.
- **D-A3 — Data source = yfinance** (Kite stays off the backtest path — no credentials + the
  `kite-execution` §0 rule). ~114 hard-bankruptcy delisted names remain unrecoverable = the
  documented survivorship gap.

---

## Sub-stages (each ends with a verifiable gate; STOP for owner review between them)

### A1 — Engine equivalence — ✅ DONE
The rebuilt engine reproduces `tests/fixtures/lh_golden_panel.csv` byte-for-byte via
`nq.engine.portfolio.simulate` (metrics + sha256 trade-ledger). This is the equivalence proof:
engine ≡ validated strategy.
**Gate:** ✅ golden test green (also green in CI on pandas 3.0.4).

### A2 — Reproducibility lockdown — *the missing pillar; do first*
- Pin `pandas`/`numpy` (cap majors) in `pyproject.toml` so the byte-for-byte golden + all numbers
  are stable across resolver drift (CI currently floats to pandas 3.0.x / numpy 2.5.x).
- **Pin the dataset:** commit a frozen, content-hashed OHLCV snapshot for the canonical universe so
  the baseline is identical run-to-run (kills the yfinance 14.2%→15.6% drift).
**Gate:** two back-to-back cloud runs produce **identical** baseline metrics + ledger hash; the
golden still passes under the pinned dep versions.

### A3 — Canonical universe + data integrity — *absorbs old Stage B data*
- Build & pin the corrected universe: `current_members ∪ config.NIFTY_500`; decide the financials
  policy (capital-adequacy proxy vs keep-dropping banks/NBFCs, per data-quality W-04); rehydrate
  ~247 delisted names via yfinance (W-02; ~114 hard bankruptcies unrecoverable).
- Run the data-quality §1-6 checks: split-vs-demerger (the VEDL class), PIT membership extent,
  fundamentals coverage, no-lookahead, zero-vol/holiday.
- Write the universe definition: what's in, what's out (ex-financials reality), the survivorship +
  pre-2018-membership caveats (trust ≥2019 folds).
**Gate:** data-quality checklist green (0 structural issues); solvency coverage ≥ 0.55; a committed
universe-definition doc.

### A4 — The anchored baseline — *gate redefined per D-A1*
- Run the frozen-cfg backtest on the pinned corrected universe → the Stage-A baseline.
- Compare to baseline_v0 (gross 26.11% / Sharpe 1.02). Compute `|Δ CAGR|` and attribute it
  (universe composition, delisted inclusion → expected DOWN move, yfinance vintage).
- Report post-tax (STCG 20%) alongside gross. Block-bootstrap Sharpe CI (block=63) for robustness.
**Gate:** a committed **baseline card** (`research/baseline_v1.json` + a human-readable card):
pinned & reproducible; universe + caveats; `Δ vs baseline_v0` with a one-line mechanism. If ≤1pp,
also tag "baseline_v0 reproduced".

### A5 — Harness can't lie — *the §11 D2 gate*
- Implement ONE known-§11-dead lever as a candidate overlay — the **market-regime entry gate**
  (dual-momentum / breadth threshold), KILLed repeatedly in §11.
- Run `nq.runner.research.evaluate_overlay(base, regime_gated)` on the pinned universe.
**Gate:** the harness returns **KILL** (ΔSharpe CI-low ≤ 0 and/or DSR < 0.95) — proving it won't
false-promote a dead lever. (A second known-dead lever, e.g. a sector-rotation tilt, is a nice-to-have.)

### A6 — Trust record — owner sign-off
- Commit a single "trustworthy ground" record under `research/`: the baseline card, the filled
  `skills/backtest-rigor` checklist, the A5 KILL-re-derivation result, and the reproducibility proof
  (A2 identical-runs evidence).
**Gate:** owner reviews + signs off → Stage A complete → research program (ROADMAP C→G) may begin.

---

## Evaluation / definition-of-done for Stage A

Stage A is done when ALL hold:
- [ ] A1 golden green (engine ≡ strategy) — ✅
- [ ] A2 two cloud runs byte-identical; deps + dataset pinned
- [ ] A3 data-quality checklist green; corrected universe pinned + documented
- [ ] A4 baseline_v1 committed, reproducible, Δ-vs-v0 explained; post-tax reported
- [ ] A5 the regime-gate lever re-derives as KILL through `evaluate_overlay`
- [ ] A6 trust record committed + owner sign-off

## Risks & known limitations (state them, don't hide them)
- **Survivorship residual:** ~114 hard-bankruptcy delistings are unrecoverable from yfinance →
  the baseline stays mildly optimistic. Labelled in the baseline card.
- **Pre-2018 membership** is the 2018 snapshot back-extended (no Wayback) → trust ≥2019 folds.
- **Ex-financials:** the D/E solvency screen drops banks/NBFCs unless the capital-adequacy proxy
  (A3) is adopted; the universe is implicitly "Nifty-500 large+mid ex-financials" until then.
- **Δ vs baseline_v0** is expected (different data vintage + delisted inclusion moves it DOWN);
  this is honest, not a regression — the golden guarantees the engine is unchanged.

## Cross-references
- Equivalence proof: `tests/test_stage2_golden.py`, `tests/fixtures/lh_golden_panel.csv`
- Harness: `nq/runner/research.py` (`evaluate`, `evaluate_overlay`), `nq/validation/`
- Cloud run: `scripts/run_cpcv.py`, `.github/workflows/cpcv-research.yml`
- Discipline: `skills/backtest-rigor`, `skills/leakage-audit`, `skills/data-quality`,
  `skills/overlay-testing`; the §11 KILL log; `diagnostics/research/HOLDOUT.md`
- Anchor: `research/baseline_v0.json` (gross 26.11% / 1.02; after-tax 23.13% / 0.83)
- Master roadmap (Stages C→G): `docs/ROADMAP.md`
