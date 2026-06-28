# 0068 — Portfolio volatility targeting on the LONG-HORIZON strategy

- **ID** — 0068
- **Registered** — 2026-06-26 (BEFORE the cloud run; question + arms + decision rule fixed first).
- **Why this is NOT a re-tread of 0013** — 0013 (vol-managed exposure, KILL) ran on the **retired
  v1 14-day model**, which already ran `apply_bear_block=True` (entry-level regime gating) — that
  made an exposure overlay redundant ("risk already managed at the ENTRY level"). The **long-horizon
  63-day J-T strategy has NO regime gate and NO bear-block** (STRATEGY_FULL §8): its only risk
  control is the per-name ATR stop, and it carries a real **~−40% drawdown**. Vol targeting has
  **never been tested on this strategy.** The only regime overlay killed *on long-horizon itself*
  (§11) is the **binary** index-200DMA dual-momentum gate; this is a **continuous, realized-vol-keyed**
  mechanism — distinct in kind (vol spikes sharply and mean-reverts in weeks; the index stays below
  its 200DMA for *months* during a recovery, which is why the binary gate sidelined trend rebounds
  and killed CAGR).
- **Hypothesis** — Scaling deployable gross exposure by `min(1, target_vol / trailing_realized_book_vol)`
  (floored) lowers MaxDD and raises Calmar/Sharpe on the walk-forward, concentrated in the crash
  folds (2018 mid-cap, 2020 COVID, 2022), WITHOUT changing stock selection. Predicted: MaxDD
  shallower by ≥4pp, Calmar up, Sharpe flat-to-up, CAGR give-back small (≤ a few pp). Per-trade WR
  and trade count are unchanged by construction (a sizing overlay).
- **Mechanism (wired, flag-gated, default OFF → golden byte-identical)** —
  `long_horizon/backtest/portfolio.simulate`: each day compute realized annualized vol from the
  trailing `vol_window`-day equity curve; `vol_scalar = max(vol_floor, min(1.0, target_vol/realized))`;
  new entries size off `equity * vol_scalar`. Because the 15% position cap is a fraction OF equity,
  scaling the equity scales the **cap-bound** size too — so it de-grosses even though the cap binds
  ~95% of the time (the reason per-name *weighting* overlays are inert here, 0020). Long-only /
  unleveraged → scale DOWN only (cap 1.0). Knobs: `target_vol_annual` (0 = off), `vol_window`,
  `vol_floor`.
- **Evaluation surface** — a single CONTINUOUS multi-year run per arm (frozen live cfg, OFF + 4
  arms over the same panel/window), NOT a per-year-reset walk-forward. RATIONALE: 0068's verdict is
  the MULTI-YEAR MaxDD (the −40.1% headline → target −30%); a per-year-capital-reset harness can
  only see the worst INTRA-year DD and would mis-measure exactly the number that matters. The frozen
  cfg was derived on the pre-2017 slice, so 2017+ is genuinely OOS for it (no re-derivation, no
  peek), and it equals what live trades. MaxDD/Calmar/Sharpe are read off the continuous curve; the
  ≥2-crash-fold check slices that same curve by crash year against the GLOBAL running peak.
- **Overlay is NOT strictly trade-set-invariant** — the earlier "pure sizing overlay, per-trade
  returns unchanged" framing is only approximately true. The cash-affordability cap means de-grossing
  can change marginal fills, and on a CASH-constrained book (15 slots × 15% cap > 100%) de-grossing
  per position can REDISTRIBUTE into more slots (breadth↑, deployment≈flat) instead of holding cash
  — i.e. a diversification effect, not the intended de-gross. This CANNOT be told apart on the
  degenerate local cache (too few eligible names to redistribute into); the harness therefore reports
  `avg_positions_held` + `deploy_pct` per arm AND per crash year, and the `mechanism_note` flags
  "CHECK" if crash-window deployment does not actually fall where DD improves. The unseen-midcap
  split stays N/A (selection is unchanged; only sizing/breadth moves), but the result must be read
  with the de-gross-vs-redistribute distinction in mind.
- **Overfit control** — (i) the small PRE-DECLARED 4-arm grid (selection surface = 4); (ii) the
  paired block-bootstrap dSharpe CI; (iii) the ≥2-crash-fold robustness rule; (iv) the live forward
  wall. (Deflated-Sharpe is REPORTED but NOT a gate — see the 2026-06-26 amendment above.)
- **Decision rule** — pre-declared grid (exactly these 4, no fine-tuning):
  | arm | target_vol_annual | vol_floor | isolates |
  |-----|-------------------|-----------|----------|
  | V1  | 0.12 | 0.40 | aggressive target |
  | V2  | 0.15 | 0.40 | moderate target |
  | V3  | 0.18 | 0.40 | mild target |
  | V4  | 0.15 | 0.50 | moderate target, gentler de-gross floor |

  PROMOTE the single best-**Calmar** arm (ranked among positive-CAGR arms only) iff: (a) **Calmar
  improves** vs the overlay-OFF control (the DD-taming goal is the point); (b) Sharpe not-worse
  (paired block-bootstrap dSharpe CI-low > −0.10); (c) MaxDD ≤ 0.90× the OFF MaxDD; (e) the MaxDD
  improvement is spread across **≥2** of the crash folds (2018/2020/2022), not one. **Judge on SHAPE
  (Calmar / Sharpe / DD), NOT CAGR** — a small CAGR give-back is acceptable if Calmar improves. Else
  KILL (→ "the −40% DD is structural / vol doesn't lead the crash here", itself informative).

  **AMENDMENT 2026-06-26 (pre-run, before any cloud dispatch) — former gate (d) "DSR > 0.95 at
  n_trials=63" is DEMOTED to informational (no longer a hard gate).** A pre-run integrity audit
  showed it is structurally unpassable and therefore pre-rigs the verdict to KILL regardless of the
  overlay's true DD performance: at n_trials=63 the expected-max per-period Sharpe (SR_0) is ~2.36,
  so any Sharpe~1 strategy scores DSR≈0 (verified: DSR=0.0000 for annualized Sharpe up to ~35; it
  only clears 0.95 near Sharpe ~40). This is a property of the repo-wide DSR usage (default
  `sharpe_variance=1.0`), already logged in `diagnostics/audit/QC-STATS.json` as informational
  there too (PBO/CI do the gating, not DSR). More fundamentally, **DSR-on-absolute-Sharpe is the
  wrong overfit instrument for a SIZING OVERLAY**: all 5 arms are the SAME base strategy, so the
  overlay reshapes the drawdown — it cannot lift the Sharpe above an N-trial expected-max. The
  honest overfit controls for a 4-knob sizing grid are exactly (b) the paired CI + the small
  PRE-DECLARED 4-arm grid (selection surface = 4) + (e) the ≥2-crash robustness + the live forward
  wall. DSR is still REPORTED (scaled with the null-SE per-period variance 1/T so the figure is
  sane, not the degenerate zero of the default variance) but carries NO gate weight. n_trials.json
  stays at 63 (the 4 arms remain in the cumulative program count); only the GATE changes.
- **Expected failure mode (honest prior)** — vol-targeting just lowers CAGR ~proportionally with no
  DD benefit (the de-gross trap that killed the binary gate), OR the book's realized vol doesn't
  rise *before* the crash, so the trailing window de-grosses too late. The benign-window local read
  (2017-2019, no crash) is mildly POSITIVE on shape (tv=0.10: Calmar 1.41→1.44, Sharpe 1.464→1.476,
  MaxDD −13.06→−12.04, CAGR −1.2pp) — a weaker skeptical prior than 0013's, but the crash-fold
  walk-forward is decisive.
- **n_trials (cumulative)** — **63** (59 + 4 grid arms, one sweep).
- **Status** — REGISTERED + HARNESS WRITTEN (`diagnostics/run_vol_target_long_horizon.py`) and
  pre-run integrity-audited (lookahead, fill/cost realism, exit-parity, universe-parity, MaxDD
  continuity, DSR scaling — all clean after the gate-(d) amendment). Sanity-tested locally
  (tests/test_vol_target.py, 3 pass). Awaiting the cloud run on the corrected 682-name universe —
  the local features+ohlcv cache is absent, so the multi-year crash-window verdict AND the
  de-gross-vs-redistribute question can only be answered in the cloud (the committed golden fixture
  is a benign 11-name 2017-2019 window: it confirms the overlay de-grosses when breadth isn't
  capped, but shows only the cost side, no crash).

## How to run
```
gh workflow run cpcv-research.yml --ref <branch> -f runner=run_vol_target_long_horizon
```
The runner builds the universe exactly as the live cron / reallocation A/B (PIT membership →
large+mid 5cr → solvent low-debt → cross-sectional rank), loads the FROZEN live cfg, and runs OFF +
the 4 grid arms as continuous single-curve simulations over `LH_TEST_START` (default 2017-01-01;
all 3 crash folds, with 2019+ reported separately for the survivorship-trustworthy window). Output:
`diagnostics/cpcv_vol_target_long_horizon.json` + a printed table (CAGR/Sharpe/MaxDD/Calmar/deploy%/
avgPos/DSR*/trades per arm, the per-crash-year DD+deployment, the paired dSharpe CI, the gates, and
the PROMOTE/KILL verdict).
