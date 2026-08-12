# The early dip is a loser tell, not a discount — "buy the pullback" selects the losers

**MEASUREMENT, DESCRIPTIVE ONLY. Zero trials. Zero screen-ledger rows** — reads
`research/substrate/trades.parquet` (uncapped touch44), no banked labels. Standing counts: read from
`diagnostics/research/n_trials.json` and `label_screen_ledger.md`.

Prompted by the owner's observation: "the point we buy is always very high, and the stock falls the
next week — we should buy earlier / not so high."

Reproduce: filter `trades.parquet` to `setup=="touch44"`, use `mae_first2wk` (worst low vs entry in
the first ~2 weeks) and `R`.

## The observation is correct

| | |
|---|--:|
| trades that dip below entry within 2 weeks | **98.3%** |
| median first-2wk adverse move | **−4.65%** |
| fell >5% early | 47.1% |
| fell >10% early (near a typical stop) | 15.8% |

Almost every trade pulls back after entry. The eye is not wrong.

## But the pullback is the failing trades, not a cheaper entry

| cohort | N | meanR |
|---|--:|--:|
| dipped >3% in the first 2 weeks | 1091 | **−0.299** |
| went straight up, no early dip | 629 | **+1.425** |

This reverses the proposed remedy. The trades that pull back after entry are the **losers**; the
trades that advance immediately are the **winners**. A limit order placed below the trigger to "buy
cheaper" only fills on names that come back to it — which are the −0.30R cohort — while the +1.43R
cohort runs away unfilled. That is precisely why the live engine enters on a **buy-stop above** the
signal week rather than a limit below: on this funnel the best moves do not look back.

## And entry height does not cause the early fall

`corr(ext_vs_sma, mae_first2wk) = −0.088` — negligible. How far above the 44-week line the entry sat
does **not** predict the early dip. The dip is idiosyncratic post-entry noise, not a consequence of
buying "too high." (By ext band, first-2wk median MAE is −4.44% / −4.07% / −5.06% / −7.16% across
<5% / 5-10% / 10-20% / >20% — flat until the extreme tail.)

## Consequence

"Buy earlier / lower to dodge the fall" is measurably backwards on this book: earliness at *entry
price* selects weakness. The honest version of "find the move early" is a **faster timeframe** (the
intraday store), not a lower entry on the weekly line.

This is consistent with the registry: finding 0088 recorded "buying near the weekly high is a HIGHER
entry" and the entry/exit arc (0098) found "confirmation just delays entry into extended, wide-stop
fills." The buy-stop-above design is the correct side of this trade.

## Caveats

- **Not a full engine test of limit entries.** A clean test of "buy a limit N% below" needs the
  engine (different fills, different stops, and the winners that never fill). The descriptive signal
  is strong enough to answer the owner's question but is not a substitute for that run, which would
  cost a trial.
- MAE and hold are mildly coupled (a fast +2R winner has little time to dip); `mae_first2wk` bounds
  the window to reduce that, and the +1.43 vs −0.30 gap is far too large to be the artifact.
- Uncapped population; Law II — a population gradient need not survive to the funding margin.
