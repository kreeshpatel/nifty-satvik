# Owner "taught mechanics" spec — tested as ONE conjunction: LOSES (2026-07-16)

Owner spec: signal guards (slope_min 0.06 · prior_above 2/4 · require_progress) + **entry buy-stop at
signal-high x 1.02** (fill max(open, trigger)) + **stop = candle low** + **scaled exit 60% @2R (resting
limit) / 20% @3R (resting limit) / 20% runner until a weekly close below the 44w SMA** + ext_floor 0.
Tested as a single conjunction per the owner's instruction ("only trade exists if all the requirement
fulfills"). Live config untouched. R11: a FINDING, no retune.

## Result

| config | trades | Sharpe | CAGR | DD | Calmar | 17-21 | **22-26** | win | meanR |
|---|---|---|---|---|---|---|---|---|---|
| BASE (live rule) | 168 | 1.03 | 21.2% | −34.8% | 0.61 | 0.79 | **1.29** | 54% | +0.616 |
| **OWNER SPEC** | 172 | 0.86 | 15.0% | −34.1% | 0.44 | **0.93** | **0.79** | 44% | +0.517 |
| scaled exit ONLY (live signal+fill) | 197 | 0.90 | 18.0% | **−43.8%** | 0.41 | 0.98 | 0.80 | 44% | +0.615 |

**0.79 vs 1.29 (−0.50), and only +0.2 sigma above the random-selection null (0.74) — i.e. at chance.**
Exit mix ran as designed: `sma_break 76% · stop 17% · eos 6% · stop_part 1%`.

## Root cause — the exit, and the reason is subtle

The scaled exit alone costs −0.49 (1.29 → 0.80) on the unchanged live signal. But **meanR is essentially
identical (+0.615 vs +0.616)** — the taught exit earns the *same average R* with a *much worse shape*
(Sharpe 0.90 vs 1.03, DD −43.8% vs −34.8%).

1. **Capping 80% at 2R/3R truncates the fat tail.** This book's edge IS the tail — 27% of touch trades are
   R>=2 runners carrying the whole result. Booking 60%+20% early removes exactly that. It is why finding
   0099 (no time cap) was adopted, why 0071/0084/0085 all pointed the same way, and why the exit forensic
   concluded "capturing more MFE truncates the runners".
2. **The 44w-SMA runner exit is far too slow.** The residual 20% rides deep into givebacks; drawdown blows
   out to −43.8% versus the P2 exit's −34.8%. The 44-week line is a lagging reference — by the time a
   weekly close breaks it, the giveback has happened.

## The one real signal in this result

The owner spec **BEATS the live book in 2017-21 (0.93 vs 0.79)** and loses badly in 2022-26 (0.79 vs 1.29).
**The taught mechanics worked in the trending era and stopped working in the chop.** That is a coherent,
economically-sensible split — fixed 2R/3R targets pay in a market that trends cleanly off support, and bleed
in one that whipsaws. It also mirrors the CRS finding in reverse (CRS is skilful in 2022-26, not 2017-21).

## Standing law, 5th sighting

Pool filter → broke CRS. 14-EMA gate on B → deleted the deep pullbacks. G1/G2 → chaotic cascade. 0094-RF →
the ATR stop halved the width. Now the taught 2R/3R exit → caps the tail. **Every attempt to impose
structure on this book removes the fat tail or perturbs the fills, and regresses toward the null.**

## Note on the stop convention (unchanged, and it matters)

The stop is evaluated at the **weekly close** and filled at the **Monday open**, so losses routinely exceed
1R (KAYNES −2.03R). The 2R/3R target arithmetic assumes R is a clean unit on both sides; on the downside it
is not. A true intra-week stop order would cap losses near −1R and would change this spec's economics — it
is untested and would be a separate pre-registration.
