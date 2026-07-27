# External-Data Census — the last in-sample axis (2026-07-27; ZERO trials; no acquisitions)

**Premise (proven):** internal information is exhausted — 0117 (price-path funnel information-complete:
any OHLCV transform is DOA), 0115 (a third sleeve needs a genuinely different return source), 0113
(PBO 46%: in-sample selection within the searched family carries no OOS skill). **Standing presumptions:**
IC-based cases must answer the IC≠portfolio graveyard (0079, 0082); PIT-untimestampable data is
disqualified (the 0017 crude lesson); derivatives re-enter only under the 0101 verdict (no OI signal
leads the book's DD; stress signals precede recoveries; term/VRP veto-shaped; timed triggers closed).

**The verdict machine:** the banked 0116/0117 label dataset (4,025 trades: false_touch 15% / noise_stop
17% / exit_too_early 19% / opp_quality_R) prices any candidate in ONE conditional screen — does the
external datum, measured in the PRE-ENTRY window, separate the label classes beyond ext×CRS cells?
Zero trials to use.

## The census (rank order)

### 1. DELIVERY PERCENTAGE (security-wise delivery / MTO) — TOP CANDIDATE
- **Mechanism:** "False-touch losers are disproportionately preceded by LOW/falling delivery-% in the
  pre-entry window (speculative churn carrying the approach), while resolved bases show high/rising
  delivery-% (position-taking). Delivery quality is invisible to OHLCV — the same printed volume can be
  90% intraday churn or 90% taken home."
- **PIT audit:** NSE daily EOD files, timestamped at publication, never restated. VERIFIED live+free
  (availability probes only): `archives.nseindia.com/archives/equities/mto/MTO_DDMMYYYY.DAT` (2019
  confirmed, header intact) and `products/content/sec_bhavdata_full_DDMMYYYY.csv` (2021 + 2025
  confirmed, DELIV_* columns). Archive = as-published files ⇒ survivorship-free (delisted names present
  on their trading days). Truncation test: trivial (daily immutable files; rebuild features from files
  dated ≤ t).
- **Depth/coverage:** ≥2016 across the full universe incl. delisted. Panel-DENSE (every name, every
  day) — unlike every event dataset below, it has per-trade power on all 4,025 labeled trades.
- **Cost:** LOW — the exact `harvest_fo_bhavcopy.py` pattern (~2,400 GETs, restartable, two formats).
  ~1 day build incl. the format seam + PIT tests.
- **Kill-shot screen:** pre-entry 21d delivery-% level/trend vs false_touch/noise_stop/winner labels,
  conditional on ext×CRS, train years only, per-year signs — the 0116 protocol verbatim.
- **Registry:** finding **0010 delivery-% INCONCLUSIVE/KILL** — but that was a 63d-base *ranking
  signal* test; this is a *pre-entry-window label screen on the swing substrate* (new horizon, new
  formulation, new labels). Cited, not relitigated-as-is.

### 2. EARNINGS CALENDAR / RESULTS DATES — the risk-axis candidate (S5 unblocker)
- **Mechanism:** "Stop-outs — especially false_touches — disproportionately contain a results
  announcement inside the trade window; the stop is pricing event risk the entry never sees. Board-
  meeting dates are announced IN ADVANCE, so the event is knowable at entry."
- **PIT:** the datum IS a timestamp (the meeting announcement precedes the meeting) — PIT-trivial, no
  restatement. NSE corporate-announcement archive.
- **Depth:** good 2018+; delisted coverage patchier (use the announcements feed, not company pages —
  company pages die with the listing).
- **Cost:** MEDIUM (scrape + symbol mapping). **Registry: S5 is OPEN** — this unblocks it.
- **Kill-shot:** results-date-inside-window rate: false_touch vs noise_stop vs winners, matched cells.
- **Honest ceiling:** an avoidance/timing rule is an entry veto — the family where every unconditional
  filter died; only an event-specific, label-confirmed effect earns a trial.

### 3. BULK/BLOCK DEALS — clean but sparse
- Mechanism: "Approaches accompanied by bulk-deal accumulation resolve as bases (informed sponsorship);
  blow-off approaches show distribution-side deals." PIT: daily EOD lists, immutable, free (probe
  verified). Depth 2016+. Cost LOW (same harvester family). **Weakness: event-sparse** — most
  pre-entry windows contain zero deals; power concentrated in few trades. Screen: deal-presence /
  direction vs labels.

### 4. CREDIT-RATING ACTIONS — the catastrophe-veto candidate
- Mechanism: "The Yes-Bank/DHFL-class single-name catastrophe (our un-hedgeable tail) is preceded by
  rating downgrades/watch — leverage stress the price has not resolved." PIT: agency press releases are
  timestamped; free via agency sites/exchange filings (scattered). Depth OK, sparse events. Cost
  MEDIUM. Not a return lever — a tail-veto; power limited by (thankfully) few catastrophes in-sample.

### 5. INSIDER / SAST DISCLOSURES — good mechanism, messy acquisition
- Mechanism: "Insider buying in the approach marks real bases; insider selling marks blow-off tops."
  PIT: mandated ≤2-day filing lag, filings timestamped. Depth 2015+. Cost MEDIUM-HIGH (PDF/HTML mess,
  entity normalization, delisted gaps). Screen: insider-net-buy in the pre-entry window vs labels.

### 6. PROMOTER PLEDGE — event + quarterly; veto-shaped
- Mechanism: pledge INCREASES precede leverage-stress collapses (the catastrophe class). PIT: event
  disclosures timestamped; quarterly SHP lag ~21d. Vendor snapshots (Screener/Trendlyne) are
  current-state ⇒ must use exchange filings. Sparse; veto-shaped like #4.

### 7. QUARTERLY SHAREHOLDING (FII/DII/promoter %) — staleness-shaped risk
- Mechanism: institutional sponsorship. But quarterly + ~21d lag = the 0108 staleness failure shape
  (stale trailing data fights a weekly momentum funnel). PIT fine via filing dates. Rank LOW-MED.

### 8. SINGLE-STOCK OPTIONS OI/IV — constrained by 0101
- 0101 verdict stated: index OI leads nothing here; the IC≠portfolio graveyard applies; 0102 closed the
  untimed hedge. Stock-level OI is a different object (per-name positioning) and our F&O harvester
  already fetches the files (we filtered to NIFTY; a re-parse widens it). But: only ~180 F&O names
  (≈half the traded universe, biased large), and the 0101/0102 priors are hostile. Rank LOW-MED; only
  the label kill-shot could earn more.

### CLOSED / DISQUALIFIED (cited, not re-proposed)
- **FII/DII daily flows, macro (USD/crude/VIX):** macro branch CLOSED (0017/0082, O-019); FII/DII
  demoted to regime-context; not per-name ⇒ cannot feed per-trade selection.
- **Analyst estimates/revisions:** vendor PIT-restatement risk (the 0017 class), thin free mid-cap
  coverage in India ⇒ disqualified on PIT+cost at this time.
- **News/sentiment feeds:** sentiment-as-alpha is the rejected thin-evidence class
  (methodology-synthesis); archive PIT questionable; HIGH cost. Out.
- **Short interest / SLB:** Indian SLB is too thin; no reliable panel. Out.
- **Index inclusion/exclusion, buybacks, misc announcements:** PIT-clean but niche/sparse; folded into
  the announcements feed if #2 is ever built; not standalone candidates.

## Ranking (mechanism × orthogonality × PIT × depth)
**1. Delivery % — clear top** (dense panel, PIT-gold, proven-free archive, mechanism aimed exactly at
the false_touch/noise_stop question). 2. Earnings calendar (risk axis, S5-unblocking). 3. Bulk/block
deals. 4. Ratings actions. 5. SAST. 6. Pledge. 7. SHP. 8. Stock options.

## Top-candidate acquisition plan (delivery %) — awaiting sign-off; nothing fetched at scale
1. `scripts/harvest_delivery.py` — clone of the proven `harvest_fo_bhavcopy.py`: MTO_DDMMYYYY.DAT
   (2016..~2020 format) + sec_bhavdata_full (2020+..), restartable, ~2,400 trading days, polite pacing
   → `data/_delivery_raw.parquet` (symbol, date, traded_qty, deliv_qty, deliv_pct).
2. `nq/data/delivery.py` — PIT layer: trailing-only features, truncation-tested like
   `tests/test_options_oi_pit.py`; format-seam continuity check at the MTO→sec_bhavdata boundary
   (the options-cutover audit pattern).
3. Integrity audit: coverage vs the corrected universe (incl. delisted), distribution sanity
   (deliv_pct ∈ [0,100]), seam continuity.

## Screen pre-registration sketch (the kill-shot; MEASUREMENT, 0 trials — params fixed)
> **0118 (draft) — Delivery-quality label screen on the swing substrate**
> **Features (pre-entry 21d window, ending the signal-week Friday, PIT):** `dlv_med21` (median
> delivery-%), `dlv_trend` (last-5d mean − 21d mean), `dlv_on_downdays` (median delivery-% on red days —
> who absorbs the selling), each also as a 252d-trailing z within the name (level-vs-self,
> drift-guarded).
> **Protocol:** 0116 verbatim — train 2019-01..2024-06 only; conditional on ext-band × CRS-tercile
> cells; effects on {R, false_touch, noise_stop, winner} with bootstrap CIs; per-year sign tables;
> sealed 2024-07+ untouched until a frozen-rule amendment (if any feature clears: conditional spread
> ≥ 0.15R AND ≥4/6 year signs — the 0116 bar verbatim).
> **Named failure modes:** (a) 0010 redux — delivery carries no swing-horizon information; (b)
> delivery-% proxies size/liquidity (add ADV to the conditioning cells if flagged); (c) the 0116 lesson
> itself — a train-clean signal can flip on the sealed set; the seal decides; (d) Stage-C cash dynamics
> remain the graveyard (0112) — nothing is adopted from a screen.
> **Trial accounting:** screen = 0 trials; only a Stage-C capped run (if ever reached) increments.

**STOP.** Nothing beyond the availability probes has been fetched; n_trials = 138 untouched.
