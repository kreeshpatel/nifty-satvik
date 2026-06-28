# ADR-0002 — Portfolio Volatility-Target Overlay

**Status:** Accepted — shipped to paper 2026-06-26
**Deciders:** Owner
**Pre-registration:** 0068 (arm V2, best-Calmar arm)
**Source of record:** `models/long_horizon/config.json → live_overlays`
**Related:** `long_horizon/STRATEGY_FULL.md §7.1`, §11 (REJECTIONS)

---

## Context

The long-horizon strategy's research headline is **30.26% CAGR / 1.15 Sharpe / −40.1% max
drawdown** (canonical frozen-cfg arm, `cpcv_long_horizon_final_682.json`, 682-name
solvency-corrected universe — all figures are research backtest, never traded a live rupee).
The Calmar ratio is ~0.76.

A ~−40% peak-to-trough drawdown is real portfolio pain. The question was: can it be reduced
without sacrificing the CAGR?

Three routes were tested under pre-registration:

| Approach | Pre-reg | Result |
|---|---|---|
| Market-regime / dual-momentum entry gate (sit out when index is below 200-DMA) | —  | KILLED: cuts DD, but also kills CAGR — the strategy's best years are the strong-trend years the gate would sideline (§11, STRATEGY_FULL.md). Net negative. |
| Pure diversification (more names / looser top-N) | 0069 | KILLED: broadening the book cuts DD but costs CAGR. Selection edge concentrates in the top names. |
| Market-state crash overlays (semivol, drawdown-pct, breadth triggers) | 0070 | Tested; plateau at ~−38% overall floor. A specific crash (e.g. COVID-type) can be cut to −31 with a well-matched signal, but **no single signal generalises across crash characters**. Not a robust lever; a specific crash hedge requires a defined-risk instrument (the deferred vol-carry / options tail-hedge program), not another sizing overlay. |
| **Portfolio vol-target de-gross multiplier** | **0068 V2** | **ADOPTED** (CAGR-neutral, DD −40 → −39 in-backtest; best-Calmar arm). |

The regime gate (the most intuitive fix) was explicitly ruled out because it is in §11 as a
tested and rejected overlay. The vol-target approach is a *non-selection lever*: it leaves
stock ranking, entries, and exits completely unchanged, and only scales the sizing equity
during sustained high-volatility periods.

---

## Decision

Apply a **portfolio-level volatility-target de-gross multiplier** to the live paper book's
sizing equity. The multiplier is:

```
vol_scalar = max(0.40, min(1.0, 0.15 / realized_annualized_book_vol_42d))
```

Where:

- `0.15` is the **annual vol target** (`vol_target_annual`).
- `realized_annualized_book_vol_42d` is the trailing 42-session annualized standard deviation
  of the paper book's daily log-returns, read from `results/portfolio_history.csv` (prior-close
  NAV — lookahead-clean).
- `0.40` is the **floor** (`vol_floor`): the overlay never degrosses below 40% of the nominal
  sizing equity, preventing a complete shutdown during extreme regimes.
- `1.0` is the ceiling: the overlay **only scales down**, never levers up.

The scalar is applied by multiplying the sizing equity before computing `base_risk_qty`:

```python
effective_equity = portfolio_equity * vol_target_scalar(...)
shares = base_risk_qty(entry, stop, adv, cfg, equity=effective_equity)
```

This is the **same formula** executed by both the live scanner and the backtest (via the shared
`portfolio.vol_target_scalar` function). The two paths cannot drift because they call the
identical kernel.

### Configuration

Stored in `models/long_horizon/config.json → live_overlays`, **not** in the frozen `cfg` block:

```json
"live_overlays": {
    "vol_target_annual": 0.15,
    "vol_window":        42,
    "vol_floor":         0.40
}
```

`load_frozen_cfg()` returns only the `cfg` block. The research backtest baselines and the
golden master (`tests/test_long_horizon_golden.py`) are therefore **untouched** — they continue
to operate on the frozen-cfg arm (30.26% / 1.15 / −40.1%) without any vol-target adjustment.

The live scanner reads `live_overlays` explicitly and stamps the applied scalar on each signal
as `vol_target_scalar` plus the resulting `sizing_capital_effective`.

### Disable path

Set `vol_target_annual: 0` in `live_overlays`. The scanner treats a zero or absent value as
"pass-through" (scalar = 1.0 always).

---

## Consequences

### What improves

- **Drawdown** reduces from ~−45% (pre-param-freeze run) / ~−40% (frozen-cfg arm) toward ~−39%
  in-backtest (best-Calmar arm, 0068 V2). The Calmar ratio improves.
- **CAGR is neutral.** The vol-target only de-grosses during sustained high-vol; it does not
  touch the trend-signal ranking, entries, or exits. When volatility is normal (scalar = 1.0),
  the book behaves identically to the unoverlaided frozen-cfg arm.
- **De-grosses automatically during momentum crashes** — the regime where the strategy bleeds —
  without requiring a manual regime-call or a selection gate.

### What does not change

- **Stock selection** — the ranking, universe filter, and entry logic are untouched.
- **Exit rules** — stop, target, trailing, time-cap, min-hold are untouched.
- **Research baselines** — the canonical headline (30.26% / 1.15 / −40.1%) and the golden
  master remain byte-identical.
- **Live-vs-backtest parity** — both paths call the same `portfolio.vol_target_scalar` kernel.

### Known limitations

- The overlay **reduces position sizes during high-vol, not during crash onset**. There is
  an inherent lag (42-day window): it de-grosses *after* vol has been elevated, not at the
  first crash bar. This is by design (avoids false triggers on single-event spikes) but means
  the overlay does not protect against a sharp, short-duration shock.
- **A dependable −30% drawdown floor is not achievable via sizing overlays alone.** Pre-reg
  0070 confirmed that market-state overlays (breadth, semivol, drawdown triggers) plateau at
  ~−38% overall, with individual crash-type matching limited to ~−31% (COVID-specific). A
  structurally lower floor requires a **defined-risk tail hedge** (the deferred vol-carry /
  options-backtester program). This ADR does not claim to solve that.
- The overlay has **never operated in live conditions** — the paper book started 2026-06-25;
  the overlay was wired 2026-06-26. Its realised DD reduction will only be measurable after
  ≥1 drawdown cycle in the paper track record.

### Promotion bar (for reference)

Any future overlay must clear the pre-committed promotion bar (from
`long_horizon/skills/sell-replace-logic/SKILL.md`): post-tax post-cost ΔSharpe ≥ +0.10 /
ΔCalmar ≥ +0.05 / 2022–2026 sub-period positive ΔCAGR / walk-forward fold-pass ≥ 60% /
bootstrap 95% CI on ΔSharpe excludes 0 / turnover increase ≤ 30% / mechanism explainable
in one sentence. The vol-target was assessed against 0068 V2 (best-Calmar) and cleared the
Calmar gate; it was adopted as a **CAGR-neutral** overlay rather than a return-enhancing one.

---

## Alternatives considered

| Alternative | Disposition |
|---|---|
| Market-regime / dual-momentum entry gate | REJECTED — §11 (tested, KILLED: cuts DD, kills CAGR simultaneously) |
| Pure diversification (0069) | REJECTED — costs CAGR; not a free DD lever |
| Market-state crash overlays (0070) | NOT adopted standalone — plateau ~−38%, no single signal generalises; deferred to the tail-hedge program |
| Static de-lever (lower `risk_per_trade_pct`, e.g. 1.5%) | Not pre-registered; reduces both CAGR and DD proportionally (the position cap binds at ~15% for high-priced names so the effect is partial); less targeted than vol-targeting |
| Conditional position-size caps | Not pre-registered; similar logic to vol-target but cruder and harder to backtest |

---

## Implementation notes

- **Shipped commit:** 2026-06-26 (paper path wire-up; part of the Phase-1 hardening program,
  commit `b653f52`).
- **Code location:** `portfolio.vol_target_scalar` (shared kernel); called in
  `src/runners/long_horizon_cron.py` at the per-signal sizing step; identical call in the
  backtest's `portfolio.simulate` (via the same kernel — live-vs-backtest parity enforced at
  the function level, verified in `wiring_report.md`).
- **Config location:** `models/long_horizon/config.json → live_overlays`.
- **Isolation from research baselines:** `load_frozen_cfg()` returns only `cfg`; `live_overlays`
  is never loaded by the backtest harness or the golden master. Verified: golden master
  byte-identical before and after the overlay was wired (3 passed, `PHASE1_FIXES.md`).
- **Signal stamp:** each published signal carries `vol_target_scalar` (the applied scalar, in
  `[0.40, 1.0]`) and `sizing_capital_effective` (= `portfolio_equity × scalar`) so the
  dashboard can surface when the book is running de-grossed.

---

## Open questions

- **Tail-hedge program** (the deferred vol-carry / options-backtester arc): this is the next
  leg of DD reduction. The vol-target overlay reduces sizing during high-vol regimes; a
  defined-risk options position would cap the left tail without the lag. Sequenced after
  ≥30 paper trades and the vol-carry data-foundation work.
- **Vol-window sensitivity** (`vol_window = 42`): was selected as the 0068 V2 best-Calmar arm.
  A shorter window (e.g. 21 days) responds faster but triggers on noise; a longer window (e.g.
  63 days) lags further. No re-evaluation is scheduled unless the paper track record reveals a
  systematic miscalibration.
- **Floor re-evaluation** (`vol_floor = 0.40`): the 40% floor prevents complete shutdown but
  means the book can still take meaningful losses during extreme regimes. Revisit if the paper
  track record shows the floor is too aggressive or too loose.
