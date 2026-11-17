# Research backlog (research freeze, ADR-0020)

While any strategy is in PAPER or PILOT, new research ideas are logged here and **not run** unless the owner approves them
(`skills/strategy-lifecycle` §8). Append only: add a row, never edit or delete one. To approve an idea, the owner adds the date
in the last column.

| logged | idea | why it might matter | cheapest test | owner approval |
|---|---|---|---|---|
| 2026-11-13 | Widen stops tighter than 8% to 8% (live swing) | +0.37 Sharpe on 20 paths, 20 of 20 better, train window (`diagnostics/research/explore/2026-11-13_stop_floor_and_confirmation.md`) | 9% and 10% on 20 paths, then a pre-registration | |
| 2026-11-13 | Half size when the Nifty is below its 40-week SMA (live swing) | +0.22 Sharpe, inside noise; parked for the January review | already on the 2027-01-01 agenda | |
| 2026-11-13 | Skip signals with results due within 4 weeks (live swing) | drawdown robustly shallower, no Sharpe gain; parked for the January review | already on the 2027-01-01 agenda | |
| 2026-11-13 | Weak-market mean-reversion sleeve | untested; draft amendment unsigned (`forward/drafts/2026-11-13_amendment_mr_sleeve_DRAFT.md`) | owner signature, then paper logging | |
| 2026-11-17 | **News sentiment, market-level only, forward-only** (spec below) — **APPROVED 2026-11-17, first reading the next Saturday scan** | the live losses came in a weak-but-calm market (VIX < 15, midcap breadth > 60%), which no price feature we have separates from a good one; sentiment is the one input the programme has never recorded | start recording; judge at 26 weeks against the pre-committed test below. Needs owner approval under the freeze | |
| 2026-11-17 | **FII / DII net flows as a market-stress signal** (spec below) | foreign and domestic institutional flows are the one market-stress series we can get point-in-time and backtest honestly, unlike sentiment | descriptive run on 2019..2024-06 only, EXPLORE tier, no trial. Needs owner approval under the freeze | |

---

## Spec — news sentiment, market-level only, forward-only (logged 2026-11-17, **approved 2026-11-17**)

**Owner decision 2026-11-17: the market-level reading is approved and starts with the next Saturday scan, frozen with
each scan and changing nothing. The per-signal reading is dropped from the spec** — Law I is the reason (five
instruments have already failed to see entry quality before entry), and dropping it also removes most of the cost and
all of the per-company point-in-time risk.

**Why forward-only.** Sentiment cannot be reconstructed point-in-time: a model reading today's archive of a 2021 article
sees everything that happened afterwards. `long_horizon/charter.md` §4 already fixes the rule — anything that cannot be
rebuilt point-in-time is **forward-only**, excluded from every backtest, judged on the forward record. So this spec
records data and decides nothing. It is not a trial and spends no multiplicity.

**What is recorded, every Saturday scan, after the cards are built — one row a week, market level only:**

| field | definition |
|---|---|
| `sentiment` | one score in −1..+1 for the Indian market over the last 7 days, from headlines only |
| `stress_tags` | zero or more of: policy, rates, currency, global, earnings-season, liquidity, scandal |
| `confidence` | low / medium / high |
| `summary` | one or two sentences, for a human reading the row later |
| `as_of`, `series_id`, `model`, `prompt_sha`, `n_headlines`, `sources` | provenance, so a later change of model or prompt is visible |

**Rules that make it evidence rather than decoration**
1. **It changes nothing.** No signal, rank, size, stop or exit may read these fields.
   `tests/test_market_sentiment.py::test_no_decision_code_reads_the_sentiment_file` pins that.
2. **Frozen at the scan.** The reading is written once, with that week's cards, and never rewritten, like the quality
   axes (`prereg_signal_quality.md` §1).
3. **Headlines only, dated.** Only material published on or before the scan date, and the prompt forbids reasoning
   about anything after `as_of`, forecasts and recommendations.
4. **The prompt and model are frozen** at the start and hashed into every row (`PROMPT_SHA`, `SERIES_ID="market-v1"`).
   Changing either starts a new series rather than continuing this one.
5. Stored append-only in `results/sentiment_forward.jsonl`, whitelisted and listed in the output contract. The step is
   non-blocking: no sentiment failure may ever fail a scan.

**Source.** The reading is produced by the scan itself through the Anthropic web-search tool, the same plumbing the
sealed judge already uses, so no third-party dataset and no external repository is required. The two GitHub
repositories the owner supplied were checked and neither carries Indian news-sentiment data (day-trader-skill is US
tooling over Yahoo / SEC EDGAR / Nasdaq; PKScreener carries FII and mutual-fund *shareholding*, not news).

**Cost per scan.** One call a week with a short search: roughly **₹5–10 a week**, under **₹500 a year**.

**The test, fixed in advance, read at 26 weeks (not before):**
- Split the weeks into sentiment quartiles at the signal Friday. The pass is a **monotone** relation between the
  quartile and the mean R of trades entered in those weeks, **and** a top-minus-bottom quartile gap of at least
  **0.5R per trade** with a bootstrap confidence interval that excludes zero.
- **A result at or below zero, or inside the interval, is a KILL.** No retune, no second prompt.
- **Prior.** Five instruments have already failed to see entry quality before entry (`program-laws` Law I), and two
  real population effects died at the funding margin (0119 delivery −1.29R/yr; 0121 earnings −15.72R/yr). The
  market-level reading is the part with a real prior in its favour, because the live losses sit in a market state
  (weak but calm) that no price feature we have separates from a good one.

**Implementation:** `nq/research/market_sentiment.py`, `scripts/run_market_sentiment.py`, wired into
`.github/workflows/cron-bhanushali-scanner.yml` as a non-blocking step (PR #203).

---
## Spec — FII / DII net flows (logged 2026-11-17, not approved)

**Why this one is different from sentiment:** NSE publishes daily foreign (FII) and domestic (DII) institutional cash
net buy and sell figures, with their dates. It is a genuine point-in-time series, so it can be measured on history
honestly, unlike sentiment.

**Data.** NSE's daily FII/DII cash figures from 2019-01-01 to 2024-06-30 (the train window), stored under
`data/fii_dii_daily.csv` with its source and fetch date. Nothing after 2024-06-30 is loaded: sealed slice B stays shut.

**Features, fixed now, all trailing:**
- `fii_net_20d`, `dii_net_20d`: 20-session net flow in ₹ crore, as of the signal Friday;
- the z-score of each over the trailing 252 sessions;
- `combined_net_20d`: FII plus DII, and its z-score.

**What the study does (EXPLORE, descriptive, no trial, no screen row):** tags every live-configuration trade on
2019-01-01..2024-06-30 with those values at its signal Friday, then reports mean R per closed trade, total R, runner
share and stop-out rate by flow bucket (z below −1, −1 to 0, 0 to +1, above +1), **cross-tabbed with the regime state
from the loss diagnosis** (Nifty against its 40-week SMA × VIX bucket × midcap breadth bucket), and by year so a single
episode is visible. It reports the correlation between the flow z-score and the existing regime variables: if it is
mostly the same information as VIX or breadth, that is the finding.

**It adopts nothing.** Any rule that came out of it would need its own pre-registration and its own trial.

**Honest prior:** macro is largely closed here. Crude was a lookahead artefact and USD sensitivity was killed as a rank
tilt (0082); 0134 pointed nine trailing market-state variables at forward returns and **none** cleared all three bars,
with a power caveat that the null means "not demonstrable", not "absent". FII flows were not among those nine, which is
what makes this worth one descriptive run and nothing more.

