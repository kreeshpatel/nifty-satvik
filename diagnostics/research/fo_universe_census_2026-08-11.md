# F&O universe census — and why "delisted" was the wrong worry

**MEASUREMENT, no trial. No screen-ledger row.** Standing counts: read them from
`diagnostics/research/n_trials.json` and `diagnostics/research/label_screen_ledger.md`.

Built 2026-08-11 from `data/fo_membership.parquet` (owner ran
`pipelines/build/build_fo_universe.py --start 2017-01-01`).

## The census

| | |
|---|--:|
| sessions covered | **2,370** (2017-01-02 .. 2026-08-10) |
| symbols ever in the equity F&O segment | **359** |
| in force on the last session | **208** |
| left the segment before it | **151** |

A universe pinned to today's F&O list would silently drop **42%** of the names that ever traded
there. That is the case for a dated panel, and it is now measured rather than argued.

## But "left the segment" is not "delisted", and that distinction is the whole point

Cross-referencing all 151 leavers against the daily OHLCV pin (which ends 2026-06-29):

| | count | share of leavers |
|---|--:|--:|
| **still trading at the pin end** — F&O exit on exchange liquidity review, company alive | **98** | 64.9% |
| stopped early while still in the store | 0 | 0.0% |
| absent from the daily store under that symbol | 53 | 35.1% |

So roughly two-thirds of the "leavers" are companies that simply fell out of the derivatives
segment — IRCTC, SYNGENE, TORNTPOWER, EXIDEIND, HUDCO, TATATECH, NUVAMA all still print daily bars.
Kite lists them as currently tradable, so an intraday fetch reaches them normally.

**The genuinely-dead tail is at most 53 of 359 — 14.8% of the universe — and is probably far
smaller than that.** Reading the 53 by name, most look like corporate actions rather than deaths:
ANDHRABANK and ALBK into their acquirers, CADILAHC and AMARAJABAT and GMRINFRA renamed, CAIRN and
ABIRLANUVO merged away, CROMPGREAV demerged. DHFL and JETAIRWAYS — the real failures — are two of
the 53, not two of the 151.

**What cannot be claimed, and is not.** `data/delisted_alias_map.json` carries **2 entries**, so it
classifies none of the 53. The rename-versus-death split above is read off the symbol names, which
is domain knowledge and not a measurement made here. The honest statement is a bound: *at most*
14.8%, with strong reason to think the true figure is a fraction of it.

That thin alias map is itself worth noting. The daily store needed a backfill for 103 of 813
members, but only two aliases were ever recorded — so the repo's own rename coverage is far weaker
than its backfill effort implies.

## Consequence for ADR-0015

The owner decided (2026-08-10) that the delisted-name probe should not gate the intraday build, on
the ground that survivorship bias scales with holding period and an intraday book is the short end.
This census supports that decision on a **second, independent** ground the ADR did not rely on:
the F&O universe's attrition is overwhelmingly segment exit rather than corporate death, so the
population Kite cannot serve is a small fraction of the population that leaves.

The earlier framing — which put the five delisted markers at the centre of the question — measured
the wrong thing. −3.69pp on the swing book came from **104 recovered names across the whole Nifty
500**, a different and much broader universe than the 359 that have ever been in F&O.

## Consequence for whether the store is needed at all

Separately, and more importantly: **an intraday store does not certify the current swing book.**

The resolution ceiling is `n_eff = 37` independent 63-day windows with a ±0.59 dSharpe half-width.
That number is **calendar span divided by holding period** — 9.5 years cut into 63-day chunks. Bar
frequency does not enter it. Feeding the existing book 15-minute bars yields the same 9.5 years, the
same 63-day horizon, the same 37 windows and the same ±0.59. It also does not accelerate the
30-closed-trade paper gate, which is set by how often the book trades.

Intraday pays only where the holding period shrinks: a 3-day-hold strategy over the same window has
of order 800 independent 3-day blocks rather than 37. That is a **different strategy family**, with
its own in-sample work, its own pre-registration, its own charge against `n_trials` and its own
forward record starting from zero. It opens a second road; it does not shorten the first.

Finding 0133 is the standing case for opening it — 11 of 22 surveyed positive strategies are
intraday and untested here purely because no store existed. That case is real and unchanged. It is
just not a swing-book argument, and it was previously described as one.

## What was built, and what it costs to leave idle

`nq/data/intraday.py`, `nq/data/fo_universe.py`, `nq/data/nse_bhavcopy.py`,
`pipelines/build/build_fo_universe.py`, `pipelines/build/fetch_intraday_store.py` — all tested, all
hermetic, no credential required except by the fetch driver. Nothing has been fetched.

`data/fo_membership.parquet` is useful on its own terms regardless of the intraday question: it is a
point-in-time liquidity screen maintained by the exchange, dated, with leavers intact. Any book can
read it, including the swing one. Note `data/` is gitignored, so it is a local artifact — rebuild
with the command above.

Reproduce this census: `python pipelines/build/build_fo_universe.py --report`, then cross-reference
`membership_spans` against `nq.data.ohlcv.load_ohlcv_cache`.
