# Blind replica notes: risk features (C) and 60/40 week (D)

Source: `diagnostics/replica/phase0/risk_features_spec.md` only. Implementation:
`risk_replica.py` -> `risk_replica.csv`; `benchmark_week_replica.py` -> `benchmark_week_replica.json`
(NAV JSONs as fetched 2026-11-20 ~17:15 IST pinned in `nav_20261120/`).

Each item: the ambiguity, then the choice made. "Material on sample?" says whether the alternative reading
would change any of the 20 sample values, where that was checked.

## C. Calendar / prices

1. **Close panel columns.** Spec says sessions are the dates of the close panel but not which symbols build it.
   Choice: union of dates across every symbol in backfill+cache (after clean), from 2016-01-01, not just members.
2. **Returns across gaps.** "No forward-fill" is stated for `rs`; for `r` (log) nothing is said. Choice: both are
   computed row-to-row on the union panel with no fill, so a missing close makes that day and the next day NaN.
3. **`mk` membership source.** Members per day from `load_membership()` intervals, ends inclusive; a member with
   no price that day is simply skipped by the mean (skipna). Symbols in the membership file with no price frame
   contribute nothing.
4. **Beta variance sample.** "Sample variance of mk over the same 126 sessions": choice is all non-missing `mk`
   in the window (not restricted to days where `rs` is also present). Same for `dbeta126`: variance over all
   `mk<0` days in the window; covariance over `mk<0` days with both values.
5. **`dvol126` mean denominator.** Mean of min(r,0)^2 over the non-missing `r` values (not divided by 126).
6. **`n_down5_252` / NaN `rs`.** Count over the window; NaN never counts as a down day.
7. **`mdd252`.** Rolling windows over the full session index (NaN close -> NaN dd that day; min_periods
   counts non-NaN values).
8. **Label `mk` missing.** Spec fills only missing `rs` with 0; a missing `mk` in the forward window would
   propagate NaN. Not hit on the sample (mk is defined every session).
9. **Label when p+63 does not exist** (data ends) -> NaN. Label cutoff test uses session p+63 <= 2024-06-30.

## C. Bands

10. **Hit counting.** Count of hitter rows (EQ, symbol, side) whose date is one of the window's sessions; hitter
    dates that are not panel sessions are ignored. Duplicate (symbol,date,side) rows would count twice
    (the run prints the duplicate count; see stdout).
11. **First hitter date** taken from the whole hitters file (all series), = 2019-01-01. Window NaN if its first
    session is before it.
12. **Band "No Band"** (non-numeric) -> NaN band_pct (symbol present, so gsm still parsed).
13. **Series EQ only for the band file.** A member trading in BE that day (e.g. SUZLON on some dates) is absent
    from the EQ rows -> band_pct NaN, gsm_stage 0. Literal reading; arguably wrong for a T2T-moved stock.
14. **GSM stage text case.** Files carry both "GSM STAGE - 0" and "GSM Stage - 0"; parsed case-insensitively.
15. **Band file date** = date in the filename `sec_list_YYYYMMDD.csv`, on or before the Friday (inclusive).

## C. ASM

16. **ST detection on subject is case-sensitive?** Spec: subject contains "SHORT" or "ST-ASM" (spaces removed).
    Subjects are mixed case ("Short-Term"). Choice: upper-case the subject, remove spaces, then test.
17. **File-name tests** (`_ST`, IBC, ICA) case-sensitive, as written.
18. **Sheet test "CONSOL"**: sheet title upper-cased first (titles are "Consolidated - ST ASM").
19. **Header cell "exactly Symbol"**: compared after stripping whitespace.
20. **Stage parsing**: first Roman (I..VI) or Arabic token in the Stage cell; empty/unparseable stage cell -> 1
    (spec gives 1 only for a missing column). First column whose header contains "Stage" (case-sensitive).
21. **Rows**: every row after the header with a non-blank Symbol cell is a listed security (no end-of-table
    detection). Duplicate symbol in one sheet -> max stage.
22. **File with no CONSOL sheet / no header row**: no snapshot (frameworks unchanged). An empty CONSOL table
    (header but no rows) is a snapshot that empties the framework.
23. **eff_date**: first w.e.f. match scanning sheets in workbook order, rows then cells; month matched on its
    first three letters; spaces and comma optional.
24. **Ordering**: (pub_date, circNumber as integer). Multiple xlsx in one folder: filename order (never occurs).
25. **Events** include changes back to 0 (an exit); the initial state is 0 for everyone.
26. **"NaN for Fridays on or before the first event's pub_date"**: read as the first event over all symbols,
    not per symbol.
27. **Restriction**: only circulars with cirDate <= 2025-09-05 (latest sample key) parsed, per task note; this
    cannot change any sample value because only pub_date < Friday is used.
28. **asm_days_in_stage** uses eff_date of the last event even when eff_date > Friday (can be negative).

## C. Pledge

29. **Which list rows belong to the symbol**: list `symbol` field equals the key symbol exactly (no ISIN
    matching, so renamed symbols lose earlier filings).
30. **Previous filing** for `pledge_chg_1q` = the filing immediately before in known-time order (ties broken by
    recordId), whatever quarter it covers. The lists contain only one version per recordId.
31. **Multiple promoter contexts / repeated facts**: first fact per local name across promoter contexts.
32. **held = 0** treated as missing for the ratio branches.
33. **New-format percent fallback** multiplied by 100 (spec: filed as a fraction).
34. **pledge_declared_none flags**: all tags starting with either prefix, excluding those ending
    ForNonPromoterNonPublic / ForPublicShareHolder / ForPublicShareholder, in any context. Values compared as
    the string "false" (case-insensitive). **A filing with no flag at all is NOT declared-none** (vacuous truth
    rejected). No filing known yet -> all three pledge columns NaN. "Before 2021" = Friday < 2021-01-01.
35. **XML missing** for a recordId -> value NaN, no flags.

## C. Fundamentals

36. **Company key source**: `company_key(isin, symbol)` applied to the whole `results_xbrl` table; the key of
    the first row with that symbol. (Checked: equals the view's `company` for all 20 sample symbols.)
37. **As-of view row**: literally the latest view row for the company with broadcast_ts <= Friday 15:30, over
    ALL rows (both bases, primary or not); ties keep file order (last). Checked: for all 20 keys the latest row
    is unique and `is_primary`, so restricting to the primary basis would not change the sample.
38. **Primary basis for balance sheets**: the company's `primary_basis` (constant per company in the view).
    `results_xbrl.consolidated` True <-> "consolidated".
39. **Balance-sheet ties**: same broadcast_ts -> latest period_end.
40. **de_ratio validity window, "that month"**: read as the month of (period_end + 6 month-ends), i.e. the next
    expected balance-sheet period (Sep period_end -> Mar -> +60d; Mar -> Sep -> +45d). The other reading
    (month of period_end) swaps 45/60. **Coin-flip; any match/mismatch on de_ratio near the boundary is not
    evidence.** `MonthEnd(6)` from pandas (a non-month-end period_end rolls to the next month end first).
41. **de with equity <= 0** -> NaN; borrowings missing part = 0.

## D. 60/40 week

42. **NAV vintage**: mfapi fetched 2026-11-20 ~17:15; the 2026-11-20 NAV was already published for both funds.
    A fetch earlier in the day would have returned 2026-11-19 NAVs (still status OK). Pinned copies saved.
43. **Cost basis** of a lot = traded value (stamp duty not capitalised). Either way tax is 0 in week 1.
44. **ST loss set-off**: ST loss offsets LT gains (Indian rule); irrelevant in week 1.
45. **index_weight denominator** = pre-tax NAV including (negative) cash -> 0.6000300; ex-cash it is exactly 0.6.
46. **Cash** = 20,00,000 − (12,00,000 + 8,00,000) × 1.00005 = −100.
47. **Both funds taxed at equity rates** (spec gives one rate set; the arbitrage fund is equity-oriented).

## Observations from the run (not ambiguities, but worth checking in the difference)

48. **dbeta126 is NaN on 8 of 20 keys** because the 126-session window has fewer than 40 `mk<0` days in strong
    up-markets (e.g. 32 down days to 2023-10-20, 34 to 2024-02-23). Follows the spec as written.
49. Hitter file has 0 duplicate (symbol, date, side) EQ rows, so item 10 does not matter.
50. AWL 2023-01-20 mdd252 NaN (listed 2022, fewer than 200 closes). JSWHL label NaN (after the 2024-06-30 cut).
51. Runtime: 1,491 s total, of which ~1,480 s is a cold parse of the ASM workbooks (cirDate <= 2025-09-05);
    the parse is cached to the session scratchpad on `--asm-cache`.

## Spec change 2026-11-20 (owner decision): declared-none pledge = 0

Change applied: a filing with no pledge number whose promoter pledge/encumbrance yes/no flags are all false now
has value 0 (and `pledge_declared_none` = 1 when it is the latest filing). The previous filing uses the same rule,
so `pledge_chg_1q` can be 0 − 0. Re-run with
`python risk_replica.py --pledge-only <keys> <out> [--update-in-place]` (no price/ASM load, ~3 s).
Outputs: `risk_replica_declared_none.csv` (10 new keys); the 3 pledge columns of `risk_replica.csv` overwritten
in place. On the 20 original keys only BSE 2024-01-19 and JSWHL 2025-09-05 changed (pledge_pct NaN -> 0,
pledge_chg_1q NaN -> 0); declared_none unchanged. The in-place rewrite also re-serialised MAXHEALTH adv60_cr
with a 3e-14 float round-trip difference (no real change).

New or sharpened ambiguities:

52. **"Has no number"** in the declared-none test now means *no number filed* (all four numeric routes NaN),
    evaluated before the 0 is substituted; otherwise the rule would be circular. Choice: test on the raw value.
53. **Declared 0 before 2021.** The spec makes the value 0 regardless of date but keeps `pledge_declared_none`
    NaN before 2021-01-01. Choice: value 0 is applied at any date (moot here, since the list files contain no
    filing known before Oct 2021; see 55).
54. **No flags at all** is still NOT a declaration (item 34 unchanged): value stays NaN, declared_none 0.
    Flags with a mix of true/false, or any value other than "false", also leave NaN.
55. **Coverage observation**: the lists start at 2021-01.json but the earliest filings for TORNTPHARM and M&MFIN
    are for the Sep-2021 quarter (known Oct-2021), so their 2021-01-29 and 2021-06-04 keys have no known filing
    and all three pledge columns are NaN, under the spec's "NaN while no filing is known" rule.
