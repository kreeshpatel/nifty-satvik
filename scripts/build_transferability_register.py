"""TRANSFERABILITY REGISTER — does each closed verdict BIND the configuration it is cited against?

Verification class. **Zero trials, zero screens. Counts frozen at screens 16 / sealed opens 1 /
n_trials 138.** No verdict is reversed, revived, or re-adjudicated here. This classifies the corpus
along one axis the registry never recorded: *what was it measured on, and does that still exist?*

## Why a script and not a hand-written table

Reproduce-before-trust. The four headline counts are the deliverable, so they must be recomputable
from a committed classification rather than asserted in prose. Each row below carries its evidence
pointer; the counts fall out of the data. Re-running this regenerates the memo byte-identically.

    python scripts/build_transferability_register.py

## The pivots, sourced not assumed

* **corrected universe — 2026-07-03.** `data/delisted_alias_map.json` + `ohlcv_backfill.pkl` landed
  in d32b29d. Anything measured earlier ran on the survivor-only pin (f8625a8f, 103 of 813 PIT
  members absent). Finding 0025 measured that this bias *scales with holding period*.
* **P2_EXIT — 2026-07-15** (finding 0099); **config P — 2026-07-16**
  (`research/config_CHANGELOG.md`). Before those, the swing exit was the frozen 0094 ladder
  (half@2R, 13-week cap, 20-day trail).
* **the ±0.302 resolution band** — `diagnostics/research/POWER_READJUDICATION.md`.

## The one caveat that applies to the band column itself

±0.302 was derived on the **swing book** (±10R/yr noise floor against a book return of 1.617σ). It
is not a universal constant, and applying it to LH-momentum rows is itself an untested transfer.
Those rows are marked `band_bookmatch=False` and counted separately — the count is reported as a
range, not a point, and that is deliberate.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "diagnostics" / "research" / "TRANSFERABILITY_REGISTER.md"

CORRECTED_UNIVERSE = "2026-07-03"
CONFIG_P = "2026-07-16"
BAND = 0.302

# ── The classification ────────────────────────────────────────────────────────────────────
# (id, date, book, exit_regime, unit, dsharpe_margin | None, binds_swing, binds_frozen,
#  binds_breadth50, note)
#
# book:        LH | SWING | SUBSTRATE | SLEEVE | EXTERNAL | AUDIT
# exit_regime: ladder-LH (frozen 63d cfg) | ladder-0094 | P2 | configP | own (external/standalone)
# unit:        R | Sharpe | eq% | net% | IC   (the unit the VERDICT turned on)
# binds_*:     YES | NO | ARGUED — "ARGUED" means it binds only via an explicitly argued mechanism,
#              which the row's note must state. Never assumed.
ROWS: list[tuple] = [
    # ── The long-horizon registry: O-###. Every one measured on LH-momentum, pinned universe,
    # frozen 63d ladder. These are the rows CLAUDE.md's registry-first rule points every session at,
    # including sessions proposing SWING work.
    ("O-001 regime/dual-momentum gate", "2026-06-25", "LH", "ladder-LH", "net%", None,
     "NO", "YES", "NO",
     "Killed on LH. Re-derived independently on the swing family (0033/0090, ΔSharpe −0.179) and on "
     "the weekly book — so the swing-side kill stands on its OWN evidence, not on O-001. The B-sleeve "
     "spec's regime pause is explicitly carved out. Cite the swing evidence, not this row."),
    ("O-002 residual / beta-stripped momentum", "2026-06-25", "LH", "ladder-LH", "Sharpe", None,
     "NO", "YES", "NO", "Never tested on the swing book. UNTESTED-HERE for swing."),
    ("O-003", "2026-06-25", "LH", "ladder-LH", "Sharpe", None, "NO", "YES", "NO",
     "LH-only. Never re-run on any later vehicle; carried so the ledger stays complete."),
    ("O-004 sector selection", "2026-06-25", "LH", "ladder-LH", "Sharpe", None,
     "ARGUED", "YES", "NO",
     "Binds swing only through 0096 (sector-relative CRS denominator, ΔSharpe −0.672 ON the swing "
     "book) — which is its own verdict with its own evidence. The mechanism argued there "
     "(residualising a trend book destroys the factor it lives on) is shared; the measurement is not."),
    ("O-005 RSI / MACD / reversal", "2026-06-25", "LH", "ladder-LH", "Sharpe", None,
     "NO", "YES", "NO",
     "A REASONED LH reject, later evidenced by 0079 at 63d. RSI-oversold is separately triple-killed "
     "on the swing/Bhanushali side (0020/0022/0024) — that is the binding evidence there."),
    ("O-006 low-vol signal-blend", "2026-06-25", "LH", "ladder-LH", "Sharpe", None,
     "ARGUED", "YES", "NO",
     "0095 argues the mechanism explicitly and re-measures it: 'the O-006/0069 family lesson again — "
     "anything that redistributes this book's risk dilutes quality.' Binds swing via that argued "
     "mechanism plus 0095's own number, not by inheritance."),
    ("O-007 quality signal-blend", "2026-06-25", "LH", "ladder-LH", "Sharpe", None,
     "NO", "YES", "ARGUED",
     "Quality was re-measured as a SLEEVE on the corrected universe by 0115 (Sharpe 0.39, FAIL). "
     "That is the row that binds a breadth-50-style multi-sleeve proposal, not this one."),
    ("O-008", "2026-06-25", "LH", "ladder-LH", "Sharpe", None, "NO", "YES", "NO",
     "LH-only. Never re-run on any later vehicle; carried so the ledger stays complete."),
    ("O-009 vol-target de-gross", "2026-06-26", "LH", "ladder-LH", "Sharpe", None,
     "NO", "YES", "ARGUED",
     "**THE PROVEN NON-TRANSFER.** PROMOTED on LH-momentum and shipped to paper; ported verbatim to "
     "the swing book by 0095 and KILLED there (ΔSharpe −0.398). The mechanism INVERTS on a "
     "cash-constrained book. This row is the register's existence proof."),
    ("O-010/011/012 alt lookbacks 12-1 / 6-1", "2026-06-28", "LH", "ladder-LH", "Sharpe", None,
     "NO", "YES", "NO",
     "Sole-ranker swaps against sma200_slope_63. The swing book does not rank on a momentum lookback "
     "at all — it ranks on crs_dist. Structurally inapplicable, not merely untested."),
    ("O-013 residual momentum sole-swap (0077)", "2026-07-02", "LH", "ladder-LH", "Sharpe", None,
     "NO", "YES", "NO", "LH ranker swap. No swing analogue was ever run."),
    ("O-014 residual blend / veto (0078)", "2026-07-02", "LH", "ladder-LH", "Sharpe", None,
     "NO", "YES", "NO",
     "veto-0.1 survives as a WATCHED forward-wall book on the LH side only."),
    ("O-015 technical zoo at 63d (0079)", "2026-07-02", "LH", "ladder-LH", "IC", None,
     "NO", "YES", "NO",
     "IC screen against a forward-63d label on the LH panel. The swing book's own zoo question was "
     "answered separately and on its own substrate (STAGE1/STAGE4, ZOO_TWO_LENS, 0131) — with the "
     "OPPOSITE population-level sign for cup/box/double_bottom. Citing 0079 at a swing zoo proposal "
     "is a cross-book citation and the two do not agree."),
    ("O-016 low-vol sole ranker", "2026-07-02", "LH", "ladder-LH", "Sharpe", None,
     "NO", "YES", "YES",
     "Binds breadth-50 directly: it is the low-vol sleeve's own measurement, and 0107/0115 carry it "
     "onto the corrected universe against the live swing vehicle."),
    ("O-017 trend x low-vol filter (0080)", "2026-07-02", "LH", "ladder-LH", "Sharpe", 0.222,
     "NO", "YES", "NO", "LH conditional filter; uncertifiable at the LH sample."),
    ("O-018 momentum + low-vol ERC (0081)", "2026-07-02", "SLEEVE", "ladder-LH", "Sharpe", 0.275,
     "ARGUED", "YES", "YES",
     "Portfolio-level, so it is about book SHAPE rather than a lever inside a book — the one class "
     "that survives 0131 §4. 0107 re-ran the identical recipe on the live swing vehicle."),
    ("O-019 USD/INR rank tilt (0082)", "2026-07-02", "LH", "ladder-LH", "Sharpe", -0.065,
     "NO", "YES", "NO", "Rank-component tilt on the LH ranker. No swing analogue."),
    ("O-020 volume-confirmed momentum-pullback", "2026-07-03", "EXTERNAL", "own", "Sharpe", None,
     "NO", "NO", "NO", "Standalone event-driven strategy, rho 0.57 to base. Its own vehicle."),
    ("O-021 volume on the 0094 swing book (0097)", "2026-07-13", "SWING", "ladder-0094", "R", None,
     "YES", "YES", "ARGUED",
     "Measured ON the swing book — but under the frozen 0094 ladder, PRE-config-P."),
    ("O-022 entry/exit research arc (0098)", "2026-07-14", "SWING", "ladder-0094", "Sharpe", None,
     "ARGUED", "YES", "NO",
     "~20 configs, all on the pre-config-P ladder. 'The frozen strategy is the best config found' was "
     "measured against a ladder the live book no longer runs."),
    ("O-023 options-OI tail hedge (0100)", "2026-07-26", "SWING", "ladder-0094", "Sharpe", -0.060,
     "ARGUED", "YES", "ARGUED",
     "Post-config-P by date but explicitly run against the frozen 0094 leg (reproduces 1.132/255 "
     "byte-for-byte). The hedge is external to the exit ladder, so the mechanism argues across."),
    ("O-024 continuous put ladder (0102)", "2026-07-26", "SWING", "ladder-0094", "Sharpe", -0.551,
     "ARGUED", "YES", "ARGUED",
     "Same construction as O-023: a ladder is bought OUTSIDE the book, so the exit regime does not "
     "mediate it and the mechanism argues across. What does not argue across is the number, which "
     "is the frozen leg's."),
    ("SL-001 (open)", "2026-06-28", "SLEEVE", "ladder-LH", "Sharpe", None,
     "NO", "NO", "NO", "OPEN, not a closed verdict — carried for completeness only."),
    ("SL-002 NSE PEAD sleeve", "2026-06-28", "SLEEVE", "ladder-LH", "Sharpe", None,
     "NO", "NO", "ARGUED",
     "Closed by 0128, which measured the drift on the UNIVERSE as an event study, not on any book. "
     "It speaks to a breadth-50 proposal only as a statement about whether the return source exists."),

    # ── LH-momentum findings 0001-0019. All pinned/survivor universe, all frozen 63d ladder.
    ("0001 C4 momentum horse-race", "2026-06-28", "LH", "ladder-LH", "Sharpe", None,
     "NO", "YES", "NO", "Confirms sma200_slope_63 as the LH ranker. The swing book has no such ranker."),
    ("0002 conviction IC within top-15", "2026-07-01", "LH", "ladder-LH", "IC", None,
     "NO", "YES", "NO", "Downgraded to INCONCLUSIVE under the corrected null."),
    ("0003 Kelly sizing", "2026-07-01", "LH", "ladder-LH", "Sharpe", None,
     "ARGUED", "YES", "ARGUED",
     "A theory/ceiling result rather than a book measurement; the quarter-Kelly reasoning is "
     "book-agnostic but its inputs (deployed vol / Sharpe) are LH's."),
    ("0004 conviction sizing C3", "2026-07-01", "LH", "ladder-LH", "Sharpe", -0.057,
     "ARGUED", "YES", "NO",
     "Re-derived on the swing side by 0073-class reasoning and by 0129's explicit family placement "
     "('NOT C3/0073 conviction sizing'). Binds swing only through that argued placement."),
    ("0005 backtest-rigor audit", "2026-07-01", "AUDIT", "ladder-LH", "Sharpe", None,
     "YES", "YES", "YES",
     "Method audit, not a book verdict. Its own classification list is the ancestor of this register."),
    ("0006 let winners run (0071)", "2026-07-01", "LH", "ladder-LH", "Sharpe", 0.114,
     "NO", "YES", "NO",
     "Downgraded to WEAK-SHADOW on regime-selection bias. The swing analogue (no-cap hold) was tested "
     "separately as 0099 and reached the OPPOSITE adoption decision on a different unit."),
    ("0007 quality/value IC", "2026-07-01", "LH", "ladder-LH", "IC", None, "NO", "YES", "NO",
     "IC against a forward-63d label on the LH panel. No swing analogue was ever run; the swing-side "
     "fundamentals question was answered separately, and negatively, by 0108."),
    ("0008 randomized-entry null", "2026-07-01", "LH", "ladder-LH", "Sharpe", None,
     "NO", "YES", "NO",
     "The '~2x random' edge magnitude that sets the LH deflation bar. The swing book has its own "
     "random null (MONTECARLO_null, 0.74) — a DIFFERENT number. Do not cross-cite."),
    ("0009 base return concentration", "2026-07-01", "LH", "ladder-LH", "net%", None,
     "NO", "YES", "NO", "Per-year characterisation of the LH base."),
    ("0010 ATR-scaled trailing (0076)", "2026-07-02", "LH", "ladder-LH", "Sharpe", None,
     "NO", "YES", "NO", "LH exit-block lever."),
    ("0011 residual momentum (0077)", "2026-07-02", "LH", "ladder-LH", "Sharpe", None,
     "NO", "YES", "NO",
     "Sole-ranker swap against sma200_slope_63. The swing book has no momentum ranker to swap."),
    ("0012 residual blend/veto (0078)", "2026-07-02", "LH", "ladder-LH", "Sharpe", None,
     "NO", "YES", "NO",
     "Rank blend / veto on the LH panel. veto-0.1 lives on as an LH-side forward-wall book only."),
    ("0013 technical zoo at 63d (0079)", "2026-07-02", "LH", "ladder-LH", "IC", None,
     "NO", "YES", "NO", "See O-015 — the swing substrate disagrees at population level."),
    ("0014 trend x low-vol filter (0080)", "2026-07-02", "LH", "ladder-LH", "Sharpe", 0.222,
     "NO", "YES", "NO",
     "Conditional pre-ranking filter on the LH panel. Its DD gain is mechanical — a book restricted "
     "to low-vol names has a structurally shallower drawdown — which is why it failed its own bar."),
    ("0015 momentum+low-vol ERC (0081)", "2026-07-02", "SLEEVE", "ladder-LH", "Sharpe", 0.275,
     "ARGUED", "YES", "YES", "Book-shape result; 0107 carries the recipe to the live vehicle."),
    ("0016 macro cross-asset IC", "2026-07-02", "LH", "ladder-LH", "IC", None,
     "NO", "YES", "NO", "Superseded by 0017 on PIT grounds."),
    ("0017 macro PIT reconfirm", "2026-07-02", "LH", "ladder-LH", "IC", None,
     "NO", "YES", "ARGUED", "The USD-sensitivity feature; its sleeve form is closed by 0115."),
    ("0018 USD tilt (0082)", "2026-07-02", "LH", "ladder-LH", "Sharpe", -0.065,
     "NO", "YES", "NO",
     "Rank-component tilt on the LH ranker. Its LESSON (IC does not become portfolio Sharpe) is "
     "programme-wide and is cited as such; its MEASUREMENT is LH-only."),
    ("0019 fundamentals-depth IC", "2026-07-03", "LH", "ladder-LH", "IC", None,
     "ARGUED", "YES", "NO",
     "rev_yoy's IC was measured on the LH panel; its SWING consequence was measured separately by "
     "0108 (growth filter, ΔSharpe −0.537 on the swing book) — which is the binding row there."),

    # ── The external-strategy arc: 0020-0026. Own vehicles, own exits, survivor-pin before 07-03.
    ("0020 Bhanushali 6-step combined", "2026-07-03", "EXTERNAL", "own", "R", None,
     "NO", "NO", "NO", "Standalone; survivor-only pin. RSI-oversold kill originates here."),
    ("0021 hybrid momentum-pullback (0083)", "2026-07-03", "EXTERNAL", "own", "Sharpe", None,
     "NO", "NO", "NO", "Standalone certified vehicle, not a base overlay."),
    ("0022 Bhanushali letter-faithful", "2026-07-03", "EXTERNAL", "own", "Sharpe", None,
     "NO", "NO", "NO", "Survivor-pin, own cost model; verdict itself corrected in-file."),
    ("0023 Bhanushali method-faithful", "2026-07-03", "EXTERNAL", "own", "Sharpe", None,
     "NO", "NO", "NO",
     "Standalone vehicle with its own entry, exit, watchlist and cost model, on the survivor pin."),
    ("0024 Bhanushali practitioner", "2026-07-03", "EXTERNAL", "own", "R", None,
     "NO", "NO", "NO",
     "Explicitly flags its own limit: 'survivor-only cache (sha f8625a8f, 103 delisted members "
     "missing) makes even these numbers optimistic.'"),
    ("0025 Path-1 4xATR geometry", "2026-07-03", "EXTERNAL", "own", "Sharpe", None,
     "ARGUED", "YES", "NO",
     "The FIRST row measured on the corrected universe, and the row that priced the survivorship bias "
     "for everything before it. Its 0.003 miss is recorded, not relitigated."),
    ("0026 six-step owner variant (0084)", "2026-07-03", "EXTERNAL", "own", "Sharpe", None,
     "NO", "NO", "NO", "Corrected universe; ancestor of the swing book but a different exit/entry."),

    # ── The six-step -> weekly arc, 0027-0038. Corrected universe; NOT the live exit.
    ("0027 runner trail (0085)", "2026-07-04", "EXTERNAL", "own", "Sharpe", 0.110, "NO", "NO", "NO",
     "Daily six-step book. Superseded by the weekly line."),
    ("0028 comparative-RS gate (0086)", "2026-07-04", "EXTERNAL", "own", "Sharpe", -0.14,
     "NO", "NO", "NO",
     "**A measured within-family non-transfer.** The SAME CRS lever that lost here (−0.14 on the "
     "daily 0085 book) HELPED on the weekly book (0036). Finding 0036 says so explicitly: 'the CRS "
     "lever behaves differently here than in 0086.'"),
    ("0029 0085 validation dossier", "2026-07-04", "AUDIT", "own", "Sharpe", None, "NO", "NO", "NO",
     "Audit of a book that is no longer the live one."),
    ("0030 trend-death exit (0087)", "2026-07-04", "EXTERNAL", "own", "Sharpe", None,
     "NO", "NO", "NO",
     "Daily six-step book, superseded by the weekly line before the live book existed."),
    ("0031 weekly-confirmation entry (0088)", "2026-07-04", "EXTERNAL", "own", "net%", None,
     "NO", "NO", "NO",
     "Daily six-step exits with a weekly entry grafted on — a hybrid no later book resembles."),
    ("0032 fully-weekly six-step (0089)", "2026-07-04", "EXTERNAL", "own", "Sharpe", None,
     "NO", "NO", "NO",
     "Ancestor of 0091, but still all-EMA — the line the live book uses is an SMA, fixed by 0034."),
    ("0033 weekly regime filter (0090)", "2026-07-04", "SWING", "own", "Sharpe", -0.179,
     "ARGUED", "YES", "NO",
     "Direct weekly-line ancestor of the live book; the regime-gate kill is the swing-side evidence "
     "O-001 is usually (wrongly) cited for."),
    ("0034 all-SMA fully-weekly (0091)", "2026-07-04", "SWING", "own", "Sharpe", None,
     "ARGUED", "YES", "NO",
     "The live book's direct ancestor, and where the 44-WEEK SMA line was fixed (owner-mandated: "
     "always SMA, never EMA). It binds the live book's SIGNAL definition, which config P did not "
     "touch. Its book numbers do not bind: both the ranker (0038) and the exit changed after it."),
    ("0035 tightened pullback (0092)", "2026-07-04", "SWING", "own", "Sharpe", -0.727,
     "ARGUED", "YES", "NO", "Entry-tightening kill on the 0091 ancestor, pre-CRS-rank, pre-config-P."),
    ("0036 slope+qgreen+CRS (0093)", "2026-07-04", "SWING", "own", "Sharpe", -0.192,
     "ARGUED", "YES", "NO",
     "Ancestor config, pre-CRS-rank-fill and pre-config-P. It fixed the slope floor and quality-green "
     "the live book still carries, so the ENTRY definition binds; the book numbers do not."),
    ("0037 CRS on Nifty-50 (0093-N50)", "2026-07-04", "SWING", "own", "Sharpe", None,
     "ARGUED", "YES", "NO", "Ancestor config; fixes the CRS denominator the live book uses."),
    ("0038 CRS-rank fill (0094)", "2026-07-05", "SWING", "ladder-0094", "Sharpe", 0.232,
     "YES", "YES", "ARGUED",
     "THE frozen record: 1.132 / 255. Binds the live book's SELECTION, which config P did not change."),

    # ── The swing book proper, 0095-0115. Split at config P (2026-07-16).
    ("0095 vol-target de-gross", "2026-07-09", "SWING", "ladder-0094", "Sharpe", -0.398,
     "ARGUED", "YES", "ARGUED",
     "The proven non-transfer of O-009. Its own mechanism (cash-constrained books invert de-grossing) "
     "argues across the exit change; the number does not."),
    ("0096 sector-relative CRS", "2026-07-09", "SWING", "ladder-0094", "Sharpe", -0.672,
     "ARGUED", "YES", "NO", "Selection-side, pre-config-P. Exit-independent by construction."),
    ("0097 volume thread nulls", "2026-07-13", "SWING", "ladder-0094", "R", None,
     "ARGUED", "YES", "ARGUED", "Per-trade R nulls; unit survives the exit change better than Sharpe does."),
    ("0098 entry/exit research arc", "2026-07-14", "SWING", "ladder-0094", "Sharpe", None,
     "ARGUED", "YES", "NO",
     "**The largest single transferability exposure in the corpus.** ~20 configs declared 'the frozen "
     "strategy is the best config found' — measured entirely against a ladder replaced ONE DAY later "
     "by 0099. The exit half of this arc is UNTESTED-HERE against config P."),
    ("0099 P2 exit (no-cap + blow-off)", "2026-07-15", "SWING", "P2", "Sharpe", -0.10,
     "YES", "YES", "NO",
     "The regime change itself. ADOPTED by owner-override while FAILING the standard ΔSharpe gate."),
    ("0100 options-OI tail hedge", "2026-07-26", "SWING", "ladder-0094", "Sharpe", -0.060,
     "ARGUED", "YES", "ARGUED",
     "Post-config-P by date, but run against the frozen 0094 leg — it reproduces 1.132/255 "
     "byte-for-byte as its own engine-invariant check. A hedge is bought outside the book, so the "
     "exit regime does not mediate the mechanism; the ΔSharpe is the frozen book's, not the live one's."),
    ("0101 OI lead-lag screen", "2026-07-26", "SWING", "ladder-0094", "IC", None,
     "ARGUED", "YES", "ARGUED",
     "A lead-lag screen of OI signals against forward book drawdowns. Exit-independent by "
     "construction — it asks whether anything ARMS ahead of a drawdown, not how the book exits — so "
     "it argues across config P, though the drawdown series it screened is the frozen book's."),
    ("0102 continuous put ladder", "2026-07-26", "SWING", "ladder-0094", "Sharpe", -0.551,
     "ARGUED", "YES", "ARGUED",
     "Overlay outside the book, so the exit change does not mediate it. What argues across is the "
     "root cause — 111 monthly cycles and exactly one paid — a property of index options on this "
     "universe rather than of the book's exit ladder."),
    ("0103 regime sleeve switch", "2026-07-26", "SLEEVE", "ladder-LH", "Sharpe", None,
     "NO", "YES", "ARGUED",
     "Sleeves reproduced exactly as 0081 — i.e. the LH momentum base, NOT the swing book. Routinely "
     "read as 'the switch is dead for our sleeves'; it was measured on the momentum pair."),
    ("0104 ext_cap tighten", "2026-07-26", "SWING", "configP", "Sharpe", -0.273,
     "YES", "ARGUED", "ARGUED",
     "**Explicitly on the live config P** ('A-only + max_risk 0.10 + max_notional 0.20 + config-P "
     "exit'). One of only three rows in the corpus measured on what is actually running."),
    ("0105 intraday hard stop", "2026-07-26", "SWING", "ladder-0094", "Sharpe", -0.477,
     "ARGUED", "YES", "NO",
     "States 'frozen 0094' — the pre-config-P ladder. The mechanism (whipsaw exceeds recovery) is "
     "about stop TYPE rather than exit ladder, so it argues across; but config P holds positions "
     "roughly twice as long, which changes the whipsaw exposure. Not re-measured."),
    ("0106 widen the stop", "2026-07-26", "SWING", "ladder-0094", "Sharpe", -0.347,
     "ARGUED", "YES", "NO",
     "States 'frozen 0094'. Its mechanism — the signal-week low already sits ~14% below entry, so "
     "widening only pushes the +2R target further away — depends on the target geometry, which "
     "config P changed. Argues across on direction; not on magnitude."),
    ("0107 swing x low-vol blend", "2026-07-26", "SLEEVE", "ladder-0094", "Sharpe", None,
     "ARGUED", "YES", "YES",
     "Book-shape, on the LIVE vehicle's frozen leg. The most breadth-50-relevant positive in the corpus."),
    ("0108 fundamental growth filter", "2026-07-26", "SWING", "ladder-0094", "Sharpe", -0.537,
     "ARGUED", "YES", "NO",
     "States 'frozen 0094'. Its mechanism — trailing annual growth is stale relative to price "
     "momentum, so the filter removes momentum winners — is a property of the universe filter "
     "rather than the exit, so it argues across config P."),
    ("0109 disaster-floor stop", "2026-07-26", "SWING", "ladder-0094", "Sharpe", -0.071,
     "ARGUED", "YES", "NO",
     "States 'frozen 0094'. Its own lesson — micro-edges below ~+-10R cannot be certified on this "
     "book — is the origin of the noise floor this register's band column uses."),
    ("0110 absolute CRS rank floor", "2026-07-26", "SWING", "ladder-0094", "Sharpe", -0.296,
     "ARGUED", "YES", "ARGUED",
     "**The closest call in the corpus: −0.296 against a ±0.302 band.** The KILL rests on 4/4 bar "
     "failure and per-year collapse, not on the Sharpe alone — but the Sharpe margin alone would not "
     "have carried it."),
    ("0111 selection-model phases 0-1", "2026-07-26", "SUBSTRATE", "P2", "R", None,
     "NO", "NO", "ARGUED", "Uncapped 3,045-signal pool. Pool, not book — 0112 is the book row."),
    ("0112 model-selector swap", "2026-07-26", "SWING", "ladder-0094", "Sharpe", -0.097,
     "ARGUED", "YES", "ARGUED",
     "States 'frozen 0094, capped book'. Pool-to-book transfer failure is the mechanism, and it is "
     "about the cash gate rather than the exit — so it argues across config P and toward any "
     "cash-constrained structure. The defensive profile it produced (DD −33.5%, zero losing years) "
     "was never re-measured under config P."),
    ("0113 PBO/CSCV audit", "2026-07-26", "AUDIT", "ladder-0094", "Sharpe", None,
     "YES", "YES", "YES",
     "17 cfg-gated configs on the frozen 0094 engine. Its ~1/3 haircut applies to any in-sample "
     "Sharpe from THAT family — which is most of this register."),
    ("0114 passive-ETF hurdle", "2026-07-27", "SWING", "ladder-0094", "net%", None,
     "ARGUED", "YES", "ARGUED",
     "Reads 'the matrix base col' — i.e. 0113's `pbo_monthly_matrix.csv`, which is the FROZEN 0094 "
     "engine, not config P. The hurdle question survives the exit change by argument (a benchmark "
     "comparison is about the book's return stream), but the number is the frozen book's."),
    ("0115 third-sleeve screen", "2026-07-31", "SLEEVE", "ladder-LH", "Sharpe", 0.017,
     "NO", "YES", "YES",
     "Sole-ranker panels on the FROZEN LH cfg engine, blended against the swing sleeve. Mixed-book "
     "by construction — and the row that most directly binds breadth-50."),

    # ── The substrate era, 0116-0131 + the FINDING_* / STAGE* corpus. Uncapped, P2_EXIT.
    ("0116 context-window selection", "2026-07-31", "SUBSTRATE", "P2", "R", None,
     "NO", "NO", "ARGUED", "Sealed-set KILL on the banked substrate. Pre-entry wall, not a book verdict."),
    ("0117 post-entry Stage 1", "2026-07-31", "SUBSTRATE", "P2", "R", None,
     "NO", "NO", "ARGUED",
     "Train years only, sealed set untouched. An INFORMATION-side result — no in-flight "
     "discriminator exists in this data — which is why it can speak to a differently-shaped book "
     "at all: it constrains what any book could know, not what this one earned."),
    ("0118 delivery-quality screen", "2026-07-27", "SUBSTRATE", "P2", "R", None,
     "NO", "NO", "ARGUED", "SCREEN PASS at the door; usage never designed. Not a book verdict at all."),
    ("0120 earnings-calendar screen", "2026-07-28", "SUBSTRATE", "P2", "R", None,
     "NO", "NO", "ARGUED",
     "SCREEN PASS stopped at the door — usage was never designed, so there is no book verdict here "
     "to transfer. What carries forward is the PIT event layer and the duration-confound caveat."),
    ("0122 ratings tail screen", "2026-07-31", "SUBSTRATE", "P2", "R", None,
     "NO", "NO", "NO", "COVERAGE-KILL — the mechanism was never tested and is explicitly NOT adjudicated."),
    ("0123 vision-graded chart structure", "2026-07-31", "SUBSTRATE", "P2", "R", None,
     "NO", "NO", "ARGUED",
     "Population-level, on charts rendered from the substrate: a reliable blind grader is FLAT "
     "across outcomes. It constrains any book that selects on pre-entry structure, which is why "
     "breadth-50 is ARGUED here rather than NO."),
    ("0124 Weinstein stage analysis", "2026-07-31", "EXTERNAL", "own", "Sharpe", None,
     "NO", "NO", "ARGUED",
     "Letter-faithful foreign vehicle on our universe. Its own text refuses transfer: the rules "
     "'were tested here only in their letter-faithful foreign home.' Lowest sleeve correlation "
     "measured — a breadth-50-shaped observation."),
    ("0126 line-hugger screen", "2026-07-31", "SUBSTRATE", "P2", "R", None,
     "NO", "NO", "NO", "Name-level base rate; null on all three legs."),
    ("0127 HEG-class activation bound", "2026-07-31", "SUBSTRATE", "P2", "R", None,
     "NO", "NO", "ARGUED",
     "Uncapped population chosen BECAUSE it inflates the bound, so the capped book can only be worse "
     "— a rare case where the non-transfer direction is pre-argued and conservative."),
    ("0128 PEAD Gate-1", "2026-07-31", "SUBSTRATE", "P2", "IC", None,
     "NO", "NO", "ARGUED", "Universe-level event study; closed on differentiation, not on the book."),
    ("0129 event-proximity sizing bound", "2026-08-06", "SUBSTRATE", "P2", "R", None,
     "ARGUED", "NO", "ARGUED",
     "Reports BOTH the uncapped substrate and the capped train book, and makes the capped book "
     "PRIMARY. One of the few rows that closes its own transfer gap by construction."),
    ("0130 sizing-exclusion bound", "2026-08-06", "SUBSTRATE", "P2", "eq%", None,
     "ARGUED", "NO", "ARGUED",
     "Book-level in the arbiter unit. Explicitly scopes itself out of breadth-50: 'equal weight in a "
     "wider book is a different question.'"),
    ("0131 zoo shadow book", "2026-08-06", "SWING", "ladder-0094", "eq%", -0.2845,
     "ARGUED", "YES", "NO",
     "Deliberately used the FROZEN ladder, not P2 — stated in its pre-reg §3 as removing a confound, "
     "and stated again as making it non-comparable to STAGE1/STAGE4. Explicitly does NOT close "
     "breadth-50 (§4)."),
    ("STAGE1 uncapped substrate", "2026-07-16", "SUBSTRATE", "P2", "R", None,
     "NO", "NO", "ARGUED",
     "4,391 uncapped trades — a POPULATION, never a book. Its per-setup tables are routinely read "
     "as if they were book results; 0130 and 0131 measured exactly how far apart the two are."),
    ("STAGE2 ML on the substrate", "2026-07-16", "SUBSTRATE", "P2", "R", None,
     "NO", "NO", "ARGUED",
     "LightGBM on the 4,391-trade population with entry-time PIT features only. Population, not "
     "book — and its near-SMA reading was itself corrected in-file on 2026-07-31."),
    ("STAGE3 exit co-optimisation", "2026-07-16", "SUBSTRATE", "P2", "R", None,
     "NO", "NO", "ARGUED",
     "Per-family exit characterisation on the UNCAPPED substrate. Exit results measured where "
     "capital never binds do not transfer to a book where capital always binds."),
    ("STAGE4 sizing sleeves", "2026-07-16", "SUBSTRATE", "P2", "Sharpe", 0.29,
     "NO", "ARGUED", "ARGUED",
     "Bug-corrected in-file. Its STANDALONE family line carried NO CI and its gaps (0.27/0.29/0.35) "
     "sit inside the band — reclassified NOT PROVEN WORSE by POWER_READJUDICATION, then resolved "
     "against the capped book by 0131 in the arbiter unit."),
    ("ROUTER context-router", "2026-07-16", "SUBSTRATE", "P2", "R", None,
     "NO", "NO", "ARGUED",
     "Killed at its own pre-registered gates, on the substrate. Cited beside STAGE4 as closing the "
     "zoo; POWER_READJUDICATION reclassified that pairing and 0131 supplied the missing evidence."),
    ("FINDING_more_slots (seat dilution)", "2026-07-16", "SWING", "P2", "Sharpe", None,
     "ARGUED", "ARGUED", "YES",
     "**The single most breadth-50-relevant trial-priced row in the corpus** (n_trials 120->122): "
     "4-5 seats 1.21 / 7 seats 0.97 / 10 seats 0.81 vs a random null of 0.74. A 50-name book sits far "
     "past its worst measured point — but it was measured by ADDING SEATS TO THIS BOOK, not by "
     "building a different one. Whether it binds a purpose-built breadth-50 structure is the open "
     "question, and this register does not answer it."),
    ("FINDING_pattern_exit / 7030 / 603010 / intraweek / lockin",
     "2026-07-16", "SWING", "P2", "Sharpe", None,
     "ARGUED", "ARGUED", "NO",
     "The R4 exit family, run in the config-P era on the discipline book — so these are among the "
     "few exit results measured near what actually runs. They share one finding: every target "
     "scheme caps the tail at ~2.4R, which is the truncation config P was adopted to avoid."),
    ("FINDING_owner_discipline / R_cap / taught_mechanics / 6040_poscap",
     "2026-07-16", "SWING", "P2", "Sharpe", None, "ARGUED", "ARGUED", "NO",
     "Owner-spec conjunctions tested as single units rather than as separable levers. That makes "
     "them binding as WHOLE SPECS and non-binding as component evidence: a conjunction that loses "
     "does not tell you which conjunct lost."),
    ("FINDING_hard_stop / small_candle / slope5 / decouple / open_progress",
     "2026-07-16", "SWING", "P2", "Sharpe", None, "ARGUED", "ARGUED", "NO",
     "R4-era levers, each guarded byte-identical against the frozen 0094 (1.1319/255). Run in the "
     "config-P era but measured against the frozen baseline, so they bind by argument, not directly."),
    ("MONTECARLO_null / POOL_vs_SELECTION / CRS_DISSECTED / COLD_START",
     "2026-07-16", "SWING", "P2", "R", None,
     "ARGUED", "ARGUED", "ARGUED", "Measurements on the live-era book; the 0.74 random null lives here."),
    ("EXT_IS_THE_ENGINE / ext_band_census", "2026-07-16", "SUBSTRATE", "P2", "R", None,
     "NO", "NO", "ARGUED",
     "Population-level extension census. Its core reading (ext IS the engine, 69% of book R) was "
     "corrected once already on 2026-07-31: the 5-10% band is WEAK, not the trap it was called."),
    ("DATA_BUG_unadjusted_splits", "2026-07-16", "AUDIT", "P2", "net%", None,
     "YES", "YES", "YES", "A data-layer defect, book-independent by construction."),
]

COLS = ("id", "date", "book", "exit_regime", "unit", "margin",
        "swing", "frozen", "breadth50", "note")


def rows() -> list[dict]:
    return [dict(zip(COLS, r)) for r in ROWS]


def universe_of(date: str) -> str:
    return "corrected" if date >= CORRECTED_UNIVERSE else "survivor-pin"


def in_band(r: dict) -> bool | None:
    return None if r["margin"] is None else abs(r["margin"]) < BAND


def band_bookmatch(r: dict) -> bool:
    """Was the ±0.302 band measured on the same book this row was? (Only SWING/SUBSTRATE.)"""
    return r["book"] in ("SWING", "SUBSTRATE")


def counts(rs: list[dict]) -> dict:
    # (1) measured on a book OTHER than the one routinely cited against. Operationally: the row's
    # evidence book is not SWING, yet the row is one the registry-first rule points a swing-side
    # proposer at — i.e. it does not bind the live swing book on its own measurement.
    cross = [r for r in rs if r["book"] != "SWING" and r["swing"] != "YES"]
    predates_universe = [r for r in rs if r["date"] < CORRECTED_UNIVERSE]
    predates_configp = [r for r in rs if r["date"] < CONFIG_P]
    banded = [r for r in rs if in_band(r) is True]
    banded_matched = [r for r in banded if band_bookmatch(r)]
    return {
        "total": len(rs),
        "cross_book": cross,
        "predates_universe": predates_universe,
        "predates_configp": predates_configp,
        "in_band": banded,
        "in_band_bookmatched": banded_matched,
        "margin_known": [r for r in rs if r["margin"] is not None],
        "binds_swing_yes": [r for r in rs if r["swing"] == "YES"],
        "binds_swing_argued": [r for r in rs if r["swing"] == "ARGUED"],
        "binds_swing_no": [r for r in rs if r["swing"] == "NO"],
        "binds_breadth_yes": [r for r in rs if r["breadth50"] == "YES"],
        "untested_here": [r for r in rs if r["swing"] == "NO" and r["breadth50"] == "NO"],
    }


def render(rs: list[dict], c: dict) -> str:
    def pc(n: int) -> str:
        return f"{100 * n / c['total']:.0f}%"
    L: list[str] = []
    A = L.append
    A("# TRANSFERABILITY REGISTER — does each verdict bind what it is cited against?")
    A("")
    A("**Class: VERIFICATION. Zero trials, zero screens. Counts frozen at screens 16 · sealed opens 1 ·")
    A("n_trials 138.** No verdict is reversed, revived, or re-adjudicated. Generated by")
    A("[`scripts/build_transferability_register.py`](../../scripts/build_transferability_register.py)")
    A("— edit the classification there, not this file.")
    A("")
    A("A binder input, and the third audit layer. The first asked whether the *input* was true")
    A("(`FOUNDATION_AUDIT.md`); the second asked whether the *instrument* could resolve what it claimed")
    A("(`POWER_READJUDICATION.md`). This one asks the question both of those leave open: **a verdict can")
    A("be correctly measured on a real book with adequate power and still not apply to the thing someone")
    A("cites it against.**")
    A("")
    A("## The rule this register enforces")
    A("")
    A("> **A verdict measured on the LH momentum book does NOT bind the swing book unless the mechanism")
    A("> is argued explicitly.** Same for substrate→book, sleeve→book, and ancestor-config→live-config.")
    A("")
    A("This is not a theoretical worry. The corpus contains a **measured** instance: `O-009` vol-target")
    A("was **PROMOTED** on LH-momentum and shipped to paper, then ported verbatim to the swing book by")
    A("`0095` and **KILLED** there at ΔSharpe −0.398. The mechanism inverts on a cash-constrained book.")
    A("A second instance is intra-family: the CRS gate lost on the daily six-step book (`0028`, −0.14)")
    A("and helped on the weekly one (`0036`) — finding 0036 says so in its own text.")
    A("")
    A("---")
    A("")
    A("## THE FOUR NUMBERS")
    A("")
    A(f"Over **{c['total']} closed verdicts** classified:")
    A("")
    A("| # | question | count | share |")
    A("|---|---|---:|---:|")
    A(f"| 1 | measured on a book **other** than the live swing book, yet reachable by the "
      f"registry-first rule from a swing proposal | **{len(c['cross_book'])}** | {pc(len(c['cross_book']))} |")
    A(f"| 2 | **predate the corrected universe** (< {CORRECTED_UNIVERSE}) — survivor-only pin, "
      f"103 of 813 PIT members absent | **{len(c['predates_universe'])}** | {pc(len(c['predates_universe']))} |")
    A(f"| 3 | **predate config P** (< {CONFIG_P}) — measured against an exit the live book no longer "
      f"runs | **{len(c['predates_configp'])}** | {pc(len(c['predates_configp']))} |")
    A(f"| 4 | deciding margin **inside the ±{BAND} power band** | "
      f"**{len(c['in_band'])}** of {len(c['margin_known'])} with a published ΔSharpe | "
      f"{100*len(c['in_band'])//max(1,len(c['margin_known']))}% of those |")
    A("")
    A("### Reading #4 honestly")
    A("")
    A(f"Only **{len(c['margin_known'])} of {c['total']}** rows publish a ΔSharpe at all — the rest turned")
    A("on IC, per-trade R, per-year sign counts, or a multi-leg pre-committed bar. So #4 is a statement")
    A("about the subset that CAN be tested against the band, not about the corpus.")
    A("")
    A(f"And the band itself does not transfer cleanly. **±{BAND} was derived on the swing book** "
      f"(±10R/yr noise floor against a 1.617σ book return). Applying it to LH-momentum rows is itself an")
    A(f"untested transfer. Of the {len(c['in_band'])} in-band rows, **{len(c['in_band_bookmatched'])} were")
    A(f"measured on a book the band actually describes**; the remaining "
      f"{len(c['in_band']) - len(c['in_band_bookmatched'])} are flagged, not counted as settled.")
    A(f"**So the defensible reading of #4 is a range: {len(c['in_band_bookmatched'])}–{len(c['in_band'])}.**")
    A("")
    A("---")
    A("")
    A("## What binds the three live objects")
    A("")
    A("`YES` = binds on its own measurement. `ARGUED` = binds only through a mechanism the row's note")
    A("states explicitly. `NO` = does not bind; **UNTESTED-HERE**, which is *not* open-for-retest.")
    A("")
    A("| object | YES | ARGUED | NO |")
    A("|---|---:|---:|---:|")
    A(f"| **the live swing book under config P** | {len(c['binds_swing_yes'])} | "
      f"{len(c['binds_swing_argued'])} | {len(c['binds_swing_no'])} |")
    A(f"| **the frozen record** (baseline_v1 0.667 · frozen 0094 1.132/255) | "
      f"{len([r for r in rs if r['frozen'] == 'YES'])} | "
      f"{len([r for r in rs if r['frozen'] == 'ARGUED'])} | "
      f"{len([r for r in rs if r['frozen'] == 'NO'])} |")
    A(f"| **the proposed breadth-50 structure** | {len(c['binds_breadth_yes'])} | "
      f"{len([r for r in rs if r['breadth50'] == 'ARGUED'])} | "
      f"{len([r for r in rs if r['breadth50'] == 'NO'])} |")
    A("")
    A(f"**Only {len(c['binds_swing_yes'])} of {c['total']} closed verdicts bind the live book on their")
    A("own measurement.** Everything else needs an argument, and the argument is the row's note.")
    A("")
    on_configp = [r["id"] for r in rs if r["exit_regime"] in ("configP", "P2")
                  and r["book"] == "SWING" and not r["id"].startswith("FINDING")]
    A(f"Measured on the live exit regime itself: **{', '.join('`'+i.split()[0]+'`' for i in on_configp)}**")
    A("— and `0099` is the adoption decision rather than a test of it. Everything else that speaks about")
    A("the live book was measured against the ladder it replaced. The `FINDING_*` R4 family also ran in")
    A("the config-P era, which is why it carries `ARGUED` rather than `NO`.")
    A("")
    A("---")
    A("")
    A("## The register")
    A("")
    A("| id | date | book | universe | exit regime | unit | ΔSharpe | in band | → live swing | → frozen "
      "| → breadth-50 |")
    A("|---|---|---|---|---|---|---:|:---:|:---:|:---:|:---:|")
    for r in rs:
        ib = in_band(r)
        ib_s = "—" if ib is None else ("**IN**" if ib else "out")
        if ib and not band_bookmatch(r):
            ib_s = "IN*"
        m = "—" if r["margin"] is None else f"{r['margin']:+.3f}"
        A(f"| {r['id']} | {r['date']} | {r['book']} | {universe_of(r['date'])} | {r['exit_regime']} | "
          f"{r['unit']} | {m} | {ib_s} | {r['swing']} | {r['frozen']} | {r['breadth50']} |")
    A("")
    A("`IN*` = inside the band numerically, but the band was measured on a different book than this row.")
    A("")
    A("---")
    A("")
    A("## Notes — why each row binds or does not")
    A("")
    for r in rs:
        A(f"**{r['id']}** — {r['note']}")
        A("")
    A("---")
    A("")
    A("## Guard — what this register does NOT do")
    A("")
    A("**Nothing is revived.** A verdict that fails transferability becomes **UNTESTED-HERE**, which is a")
    A("statement about the evidence, not an invitation. It is *not* OPEN-FOR-RETEST. Re-testing any of")
    A("these still requires a pre-registration, a declared re-open key from {new data, new feature")
    A("source, new sub-period, new formulation}, and `n_trials` pricing at the trunk. A row moving from")
    A("`YES` to `NO` in the swing column removes a *citation*, not a *cost*.")
    A("")
    A(f"**{len(c['untested_here'])} rows** are UNTESTED-HERE against both the live book and breadth-50.")
    A("That is the register's main product: a list of things the programme knows about a book it no")
    A("longer runs, which have been carrying rhetorical weight they were never measured to carry.")
    A("")
    A("## Root-cause readout")
    A("")
    A("The corpus was built book-by-book as the programme's vehicle changed underneath it — LH momentum,")
    A("then an external swing arc, then the weekly line, then a substrate, then two exit regimes in two")
    A("days. Each verdict was correct where it was measured. The registry recorded *what* was decided and")
    A("*why*, but never *on what* — so a session searching it before proposing gets hits that look")
    A("binding and are not. `O-009` is the proof: the same lever, PROMOTED on one book and KILLED on")
    A("another, sits in the same ledger with no column distinguishing them until now.")
    A("")
    A("## Next setup")
    A("")
    A("None proposed. The register is a lookup layer, not a research agenda. Its intended use is at Gate")
    A("0 of `skills/verdict-machine`: when a registry hit collides with a proposal, this file says")
    A("whether the collision is real.")
    return "\n".join(L) + "\n"


def main() -> int:
    rs = rows()
    ids = [r["id"] for r in rs]
    assert len(ids) == len(set(ids)), "duplicate verdict id"
    c = counts(rs)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(rs, c), encoding="utf-8")
    print(f"{c['total']} verdicts classified -> {OUT.relative_to(ROOT)}")
    print(f"  1. cross-book vs the live swing book : {len(c['cross_book'])}")
    print(f"  2. predate the corrected universe    : {len(c['predates_universe'])}")
    print(f"  3. predate config P                  : {len(c['predates_configp'])}")
    print(f"  4. inside the +-{BAND} band          : {len(c['in_band'])} "
          f"of {len(c['margin_known'])} with a published margin "
          f"({len(c['in_band_bookmatched'])} on a band-matched book)")
    print(f"  binds the live swing book YES/ARGUED/NO : {len(c['binds_swing_yes'])}/"
          f"{len(c['binds_swing_argued'])}/{len(c['binds_swing_no'])}")
    print(f"  UNTESTED-HERE (neither live nor breadth-50): {len(c['untested_here'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
