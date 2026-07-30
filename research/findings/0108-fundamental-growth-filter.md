# Finding 0108 — Fundamental profit+sales growth universe filter KILLs: it removes momentum winners

**Verdict:** **KILL.** Pre-reg [0108](../../diagnostics/research/preregistry/0108-fundamental-growth-filter.md).
Data `data/fundamentals_pit_depth.pkl` (Screener annual P&L, 653 names, PIT-clean: avail=period_end+90d,
strict-before). n_trials 134→135.

## Result (frozen 0094, corrected universe 2017-2026)
| | Sharpe | CAGR | MaxDD | trades | win |
|---|---|---|---|---|---|
| base | 1.132 | 24.7% | −42.4% | 255 | 59% |
| **np_yoy>0 AND rev_yoy>0 filter** | **0.595** | **10.3%** | **−53.9%** | 208 | 48% |
| Δ | −0.537 | −14.4pp | −11.5pp (worse) | −47 | −11pp |

Per-year — mixed, net-catastrophic: HELPED blowup years (2020 +11→+23, 2024 +10→+32) but DESTROYED trend
years (2017 +32→0, 2018 +12→−22, 2019 +31→−8) and worsened 2025 (−13→−21). 4/4 bar FAIL.

## Root cause — the filter fights the momentum edge
Trailing ANNUAL profit growth (lagged up to ~15 months) is **stale and disconnected from price momentum** —
price leads earnings, so many momentum winners are turnaround/recovery names with weak *trailing*
fundamentals (the 2017-2019 winners the filter excluded). Requiring positive trailing growth removes those
winners. Plus coverage shrink (135 no-data names excluded) + the cash-redeploy inversion (255→208 trades,
win 59→48%) — the same wall as ext_cap (0104), O-015, O-022: every "make it safer" filter removes winners
faster than losers. Confirms 0019 (fundamentals-depth is a single weak feature, not an edge).

## PIT / authenticity — clean
The failure is real, not a leak. Eligibility at t uses only the most-recent report with avail (period_end
+ 90d) STRICTLY < t (searchsorted strict-before); growth is Y-vs-Y-1 both past. Screener restatement risk is
negligible for a sign filter. The owner's "can't measure on current" concern is correctly handled.

## The quarterly-Screener question (do NOT build it)
The annual test PRE-REFUTES the direction: quarterly data is fresher (would ease the staleness that hurt
2017-2019) but the structural killers — removing momentum winners + cash-redeploy on a cash-constrained book
— are freshness-independent, and Screener quarterly is only ~3yr deep (untestable on the full window). Days
of scrape+PIT work to sharpen a lever structurally opposed to momentum is not justified.

## The one keeper
The deterioration-screen DID help the blowup years (2020/2024). That is not a universe-entry filter — it is a
narrower RISK-OVERLAY idea (tighten risk on deteriorating-fundamental names you HOLD), a different test worth
noting, not building now.
