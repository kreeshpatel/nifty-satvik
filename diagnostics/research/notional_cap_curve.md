# Notional-cap curve — concentration vs collection

**VERIFICATION CLASS — 0 trials, 0 screens. Counts frozen: screens 15 · sealed opens 1 · n_trials 138.** No book re-run. No Sharpe/MaxDD/worst-year. **No arm is recommended.**

**LIMITATION (first, because it binds):** cannot show WHICH TRADES a different cap would fund — the funded set is held fixed at the substrate's; cap->cash-path->selection is inseparable from a book re-run and was declined as trial-class.

**No return column, deliberately:** 0113 PBO 46.2% — within this cfg-lever family the in-sample-best config lands at the OOS median (1.239 -> 0.843 vs 0.835), so a per-cap return ranking carries ~zero OOS decision weight and would deflate every future DSR bar.

Population: uncapped Stage-1 substrate, entry_date >= 2019-01-01, all setups — **3819 trades** (346 with ext<5%, 3473 with ext>=5%).

| cap | risk-sizing under-sized for | **weight ext<5%** | weight ext>=5% | book weight | **realized-R recovery** | positions sized BY the cap | max exposure |
|---|---|---|---|---|---|---|---|
| **0.15** | 100.0% of trades | **0.466** | 0.591 | 0.58 | **0.622** | 100.0% | 15.0% |
| **0.2** | 53.4% of trades | **0.621** | 0.788 | 0.773 | **0.829** | 100.0% | 20.0% |
| **0.25** | 43.3% of trades | **0.713** | 0.851 | 0.838 | **0.884** | 43.3% | 25.0% |
| **0.3** | 34.0% of trades | **0.78** | 0.894 | 0.884 | **0.922** | 34.0% | 30.0% |
| **unbounded** | 0.0% of trades | **1.0** | 1.0 | 1.0 | **1.0** | 0.0% | 2298.9% |

*(`max exposure` and the >30%/>50% tails are the cap itself / zero **by construction** for any bounded cap <= 0.30 — see the JSON. The informative concentration column is `positions sized BY the cap`.)*

**Structural finding.** The notional cap is not a rare guardrail on this book — it is the POSITION SIZER. With the live max_risk_pct=0.10 in force, every stop is at most 10% wide, so risk-sizing always wants at least RISK/0.10 = 20% of equity per name. Any cap at or below 0.20 therefore sets the size of 100% of positions and the 2%-risk rule never binds. Two different quantities are easy to confuse here and both statements are true at cap 0.20: the cap sets NOTIONAL for 100% of trades, while equity RISKED falls below the nominal 2% for the 53.4% whose stop is narrower than 10% (a trade with an exactly-10% stop sits at the cap AND at full risk simultaneously).

**Reading note.** COLLECTION rises and CONCENTRATION rises together — that is the whole tradeoff and it has no interior optimum visible in these columns, by construction. The unbounded arm's max exposure is the sizing rule's IMPLIED notional, not a position the book could ever fund: cash binds first (H5 — cash is the only capacity constraint). It is reported because it is exactly the runaway the 2026-07-16 guardrail was adopted against.

Reproduce: `python scripts/diag_notional_cap_curve.py`
