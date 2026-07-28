# Finding 0122 — Ratings tail screen: COVERAGE-KILL (the filing stream has no usable equity linkage); census #4 closes; #5-#7 close on paper preconditions

**Verdict: KILL on coverage grounds — the mechanism was never tested and is NOT adjudicated.** Ledger
row #11 closed (running count 11; sealed opens 1). n_trials untouched at 138. Pre-reg
[0122](../../diagnostics/research/preregistry/0122-ratings-tail-screen.md); scripts
`diag_disaster_census.py`, `harvest_ratings.py`, `diag_ratings_screen_0122.py`.

## Step-0 disaster census (the session's frozen baseline)
Frozen line R ≤ −1.5: **292 train disasters** (2019-01..2024-06), aggregate −696R, present every year
(25-79). Count gate PASSED. Character flag recorded before any harvest: the list is **market-gap
dominated** (KOTAKBANK/INFY/TITAN/ICICIBANK in COVID-2020 and 2022 crash weeks) — the class a ratings
mechanism cannot precede. One artifact noted: FINEORG −39.9R is a tiny-risk inflation (0.27% stop
width), not a data bug.

## The acquisition and why it fails
NSE's structured credit-rating filing archive (regime starts 2023-02; 206k rows harvested → 16,445
after the window-overlap dedup guard). **The Symbol field is free-text junk** — 48% literal
"NOTLISTED", the rest placeholder digits ("222333", "000000"), spelling variants, even dates. This is
a DEBT-INSTRUMENT disclosure stream; issuer-to-equity linkage would require an ISIN→issuer mapping
build. Result: **0% of the era universe's symbols link** → the screen returned 0/57 vs 0/878 — a void
measurement, not evidence. Distinguished honestly: **coverage-KILL, not mechanism-KILL.**

## Why no further route is chased (the campaign's terms)
(a) The Step-0 mechanism flag stands: even with perfect linkage, the covered-era disaster class is
idiosyncratic-thin (~57 events) and the full class is market-gap dominated; (b) an issuer-mapping
build is real work with a hostile prior; (c) this was the pre-declared FINAL ROUND. Census #4 closes.

## Paper preconditions for the remaining census entries (per Step-0's instruction)
- **#5 SAST/insider — CLOSED by precondition.** Its consumer is the per-trade selection margin, and
  the decision-margin law (0119 tiebreak, 0121 deferral: population information cannot be expressed at
  this book's margins) removes the consumer regardless of the data's quality. Citation, not harvest.
- **#6 promoter pledge — CLOSED by precondition.** Its consumer is the same catastrophe-veto as #4:
  the substrate's disaster class is market-gap dominated and the idiosyncratic slice is ~thin-n;
  the same coverage/power wall applies with weaker data (quarterly + event-sparse).
- **#7 quarterly SHP — CLOSED by precondition.** The 0108 staleness failure shape (stale trailing
  fundamentals fight a weekly momentum funnel) plus the closed selection margins leave it no consumer.

## Program consequence
The external-data census is fully resolved: #1 delivery (banked, screen PASS, usage priced out),
#2 earnings calendar (banked, screen PASS, usage priced out), #3 bulk/block (acquisition-blocked,
fallback standing), #4 ratings (coverage-KILL), #5-#7 (paper preconditions). **The campaign pauses.**
