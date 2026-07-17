"""Build the RULES_SPEC.pdf that accompanies the TradingView trade-review CSV.

Every rule here is transcribed from scripts/run_bhanushali_weekly_rank.py as it runs TODAY (the live
book of record: base 0094 signal + P2 exit). If the engine changes, regenerate — do not hand-edit.

Used by scripts/export_tv_review2.py.
"""
from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

ACC = colors.HexColor("#1f4e79")
MUT = colors.HexColor("#666666")
BG = colors.HexColor("#f4f6f8")


def _styles():
    ss = getSampleStyleSheet()
    return dict(
        h1=ParagraphStyle("h1", parent=ss["Heading1"], fontSize=16, textColor=ACC, spaceAfter=2),
        h2=ParagraphStyle("h2", parent=ss["Heading2"], fontSize=11.5, textColor=ACC,
                          spaceBefore=10, spaceAfter=4),
        p=ParagraphStyle("p", parent=ss["BodyText"], fontSize=8.7, leading=11.8, alignment=TA_LEFT),
        small=ParagraphStyle("small", parent=ss["BodyText"], fontSize=7.6, leading=10, textColor=MUT),
        cell=ParagraphStyle("cell", parent=ss["BodyText"], fontSize=7.8, leading=10.2),
    )


def _table(rows, widths, st, header=True):
    data = [[Paragraph(f"<b>{c}</b>" if header and i == 0 else str(c), st["cell"]) for c in r]
            for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), BG))
    t.setStyle(TableStyle(style))
    return t


def build_pdf(path, m, n_trades, sample):
    st = _styles()
    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=14 * mm, bottomMargin=14 * mm,
                            leftMargin=15 * mm, rightMargin=15 * mm,
                            title="Weekly swing book — rules spec sheet")
    W = doc.width
    F = []
    P = lambda s: Paragraph(s, st["p"])          # noqa: E731

    F += [Paragraph("Weekly swing book — rules spec sheet", st["h1"]),
          Paragraph("Model <b>weekly-swing-0094-rank-p2exit</b> · the LIVE book of record · generated for "
                    "manual TradingView review · 2026-07-16", st["small"]),
          Spacer(1, 5)]

    F += [P("<b>Read this first.</b> Every rule below is transcribed from the engine as it runs today. "
            "The trades in <b>tv_review_80.csv</b> were produced by exactly these rules and nothing else. "
            "If a chart looks wrong to you, one of these rules is the reason — the job is to find which. "
            "Rules that <i>sound</i> right but are not implemented are listed in §7 (already tested "
            "and killed), so please check there before proposing one.")]

    # 1 — the book
    F += [Paragraph("1 · The book", st["h2"])]
    F += [_table([
        ["Item", "Value"],
        ["Universe", "NSE equities, point-in-time index membership (a name is only tradable on dates it "
                     "was actually a member — no survivor look-ahead in the membership test)"],
        ["Period", "2017-01-01 to the data cutoff"],
        ["Starting capital", "Rs 10,00,000"],
        ["Risk per trade", "2.0% of sizing equity"],
        ["Position cap", "<b>None.</b> Size is whatever 2% risk implies (median ~14% of equity per name)"],
        ["Costs", "STT 0.1% per leg + an ADV-based impact/slippage model on every leg"],
        ["Result of record", f"Sharpe <b>{m['sharpe']:.4f}</b> · <b>{m['trades']}</b> trades "
                             f"(this CSV samples {n_trades} of them after split-cleaning)"],
    ], [32 * mm, W - 32 * mm], st)]

    # 2 — signal
    F += [Paragraph("2 · Entry signal — weekly bars, all four must be true in the SAME week", st["h2"]),
          P("Weeks are ISO weeks. <b>SMA44</b> = 44-week simple moving average of the weekly close. "
            "Everything is trailing-only (no future data).")]
    F += [_table([
        ["#", "Rule", "Exactly"],
        ["1", "Trend is rising", "SMA44[k] / SMA44[k−13] − 1 <b>&ge; 0.03</b> (i.e. the 44w SMA is up at "
              "least 3% over 13 weeks). This is a low bar — a barely-rising line passes."],
        ["2", "Green candle, closing strong", "close &gt; open <b>AND</b> (close − low) &ge; 0.50 × "
              "(high − low), i.e. the close is in the <b>upper half</b> of the week's range."],
        ["3", "Touch of the 44w SMA", "low &le; SMA44 × <b>1.07</b> (the week dipped to within 7% above the "
              "line) <b>AND</b> close &gt; SMA44 (it closed back above it)."],
        ["4", "Relative strength", "RS &gt; SMA40(RS), where RS = weekly close ÷ Nifty-50 close. "
              "The stock is outperforming its own 40-week average RS."],
    ], [8 * mm, 40 * mm, W - 48 * mm], st)]
    F += [P("<b>Known weakness in rule 3 (already identified, not yet fixed).</b> The touch test cannot "
            "tell a genuine <i>pullback</i> (price above the line, dips to it, bounces) from a "
            "<i>recovery through</i> the line from below (price under the line for weeks, one big candle "
            "crosses up). Both satisfy it, and because the 44w SMA lags, rule 1 still reads “rising” "
            "after weeks of price below it. This is the ZFCVINDIA / RCF case you found.")]

    # 3 — fill
    F += [Paragraph("3 · Fill — the week AFTER the signal", st["h2"])]
    F += [_table([
        ["Step", "Rule"],
        ["Window", "The signal week's <b>low</b> and <b>high</b> define a price band. We look at each daily "
                   "bar of the following week."],
        ["Trigger", "Fill at the <b>first daily OPEN that falls inside [signal-week low, signal-week high]</b>. "
                    "The fill price is that open."],
        ["No fill", "If no daily open lands inside the band all week, the signal <b>expires unfilled</b> — "
                    "no trade."],
        ["Who gets the cash", "When several signals compete for limited cash, candidates are attempted in "
                              "<b>descending CRS distance</b> (CRS = RS ÷ SMA40(RS) − 1, measured at the "
                              "signal week). Strongest first. If cash runs out, the rest are skipped."],
    ], [26 * mm, W - 26 * mm], st)]
    F += [P("<b>Note:</b> this is <i>not</i> a buy-stop. We do not wait for the price to trade through the "
            "signal week's high. That variant was tested (pre-reg 0088) and lost badly, because entering at "
            "the high while the stop sits at the low makes the whole candle the risk.")]

    # 4 — stop and sizing
    F += [Paragraph("4 · Stop and size", st["h2"])]
    F += [_table([
        ["Item", "Rule"],
        ["Stop level", "The <b>signal week's LOW</b>. Fixed for the life of the trade (it never moves down; "
                       "see the trail in §5)."],
        ["R", "1R = entry − stop. Median across the book is <b>14.2% of the entry price</b>."],
        ["Shares", "equity × 2% ÷ (entry − stop). Wider stop ⇒ smaller position."],
        ["Consequence", "Notional per name = 2% ÷ R%. At the median R of 14.2%, one name is ~14% of the "
                        "book, so ~7 names fit."],
    ], [26 * mm, W - 26 * mm], st)]

    # 5 — exits
    F += [Paragraph("5 · Exits — the P2 rule set", st["h2"]),
          P("<b>This is the single most important thing to understand while reviewing charts.</b> Every exit "
            "below is <b>decided at the weekly CLOSE (Friday) and filled at the NEXT MONDAY'S OPEN.</b> "
            "There is <b>no live stop order in the market.</b> Price can trade far below the stop level "
            "mid-week and we do not exit — we exit Monday, at whatever Monday opens at.")]
    F += [_table([
        ["#", "Exit", "Trigger (checked Friday) — fills Monday open"],
        ["1", "Stop", "Weekly close &le; stop. <i>Not</i> the intraweek low — the CLOSE."],
        ["2", "Half at 2R", "Weekly close &ge; entry + 2R ⇒ sell <b>50%</b> of the position (once). "
              "The rest runs."],
        ["3", "20-DAY SMA trail", "<b>Only after the 2R half has booked.</b> trail = max(trail, "
              "SMA20-day × 0.96); exit the rest when the weekly close &lt; trail."],
        ["4", "Blow-off bar", "Armed once MFE &ge; <b>2.5R</b>. Exit if the week makes a <b>new high</b> but "
              "<b>closes in its lower third</b> (long upper wick = exhaustion)."],
        ["5", "20-WEEK SMA trail", "Armed once MFE &ge; <b>2R</b>. Exit if the weekly close &lt; "
              "SMA20-week × 0.96."],
        ["6", "Time backstop", "<b>52 weeks</b> held. (There is no 13-week cap — it was removed.)"],
    ], [8 * mm, 30 * mm, W - 38 * mm], st)]
    F += [KeepTogether([
        Paragraph("Why losses run past −1R", st["h2"]),
        P("Because of the Friday-decide / Monday-fill rule above, a −1R stop is a <b>trigger, not a fill</b>. "
          "Roughly <b>87%</b> of the excess loss is price drifting below the stop level <i>during</i> the "
          "week before Friday; only ~13% is the Monday gap. With a median R of 14%, a −2R exit is a "
          "<b>−28% move</b>. KAYNES booked −2.03R this way; a real standing stop order would have filled "
          "near −1R. <b>The backtest is pessimistic here, not optimistic.</b> A real hard stop was tested "
          "(§7) and it made the drawdown worse, not better.")])]

    F += [PageBreak()]

    # 6 — the CSV
    F += [Paragraph("6 · The trade list (tv_review_80.csv)", st["h2"]),
          P("<b>Random</b> samples — deliberately not the extremes, so you see the typical case. "
            "Buckets can overlap (most stops are losses).")]
    F += [P("<b>Read WINNER_HIGH_EXT alongside the losers — it is there to stop a specific mistake.</b> "
            "A loser list is defined <i>by outcome</i>, so every entry in it looks bad, and it is very easy "
            "to conclude the entry style caused the loss. WINNER_HIGH_EXT holds <b>winners with the same "
            "profile</b> — entered &ge;20% above the 44w SMA, off a big candle. If a loser's chart looks "
            "damning, find the winner that looks identical before concluding anything.")]
    prof = [["Bucket", "n", "Definition", "mean %move", "meanR", "mean MFE"]]
    for b, g in sample.groupby("bucket", sort=False):
        defn = {"LOSS_RANDOM": "R &lt; 0", "STOPPED_RANDOM": "exited via the stop",
                "GOOD_RANDOM": "R &ge; 2",
                "WINNER_HIGH_EXT": "R &ge; 2 <b>and</b> entry &ge;20% above the SMA — the matched control"}.get(b, "")
        prof.append([b, len(g), defn, f"{g.pct_move.mean():+.1f}%", f"{g.R.mean():+.2f}",
                     f"{g.mfe_pct.mean():+.1f}%"])
    F += [_table(prof, [32 * mm, 8 * mm, 34 * mm, 22 * mm, 16 * mm, 20 * mm], st)]
    F += [Spacer(1, 4), _table([
        ["Column", "Meaning"],
        ["signal_week", "The <b>decision bar</b> — the weekly candle that fired the signal. Put your cursor "
                        "here first; this is the candle the rules judged."],
        ["sig_ctl_pct", "(close − low) ÷ close of the signal week, %. <b>This IS R.</b>"],
        ["sig_body_frac", "body (close − open) ÷ range (high − low) of the signal week. 1.0 = no wicks."],
        ["sig_range_pct", "(high − low) ÷ low of the signal week, %."],
        ["entry_date / entry", "The daily open we actually filled at."],
        ["stop", "Signal-week low. <b>Never sent to the market</b> — checked Fridays only."],
        ["risk_pct", "(entry − stop) ÷ entry, %."],
        ["ext_vs_sma", "How far the entry price sat above the 44w SMA, %. <b>Negative = we filled BELOW "
                       "the line</b> (the KENNAMET / NAVA case)."],
        ["crs_rank", "CRS distance at the signal week — the queue position for cash."],
        ["exit_date / exit_px", "Monday open we exited at."],
        ["pct_move", "(exit ÷ entry − 1), %. <b>What the eye sees on the chart.</b>"],
        ["R", "pct_move expressed in R. Beware: R is a ratio — a big R on a tight stop is a small move."],
        ["mfe_pct / mae_pct", "Best / worst excursion vs entry while the trade was open, %."],
        ["reason", "Which §5 rule closed it."],
    ], [30 * mm, W - 30 * mm], st)]

    # 7 — killed
    F += [Paragraph("7 · Already tested and KILLED — please do not re-propose these", st["h2"]),
          P("Each of these was implemented, frozen, run against the 2022-26 slice, and lost. The baseline "
            "to beat is <b>1.29</b>; buying trades <b>at random</b> from the signal pool scores <b>0.74</b>.")]
    F += [_table([
        ["Idea", "Result", "Why it failed"],
        ["Buy-stop entry (wait for the signal high)", "0.22 (pre-reg 0088)", "Entry at the high + stop at "
         "the low = the whole candle is risk (12.8% vs 7%), which halves the size."],
        ["A real hard stop order (live, intraweek)", "worse DD", "Caps every loss at −1R and the drawdown "
         "still got worse — the tight exit cut trades that would have recovered."],
        ["Cap R at 5% (raise the stop)", "0.64 · DD −54.5%", "Forces notional to 2%/5% = 40% of the book "
         "per name. Concentration, not protection."],
        ["Cap capital at 20% per name", "0.64", "The book's natural size is already ~14%. A 20% cap can "
         "only bind <i>upward</i> — it concentrated the book."],
        ["2R / 3R fixed targets, no runners", "0.50–0.82", "Cuts the fat tail. The right tail IS the "
         "entire return; 90% of each position capped at 3R kills it."],
        ["Only small candles (&le;5%, solid body)", "0.37", "Candle size doesn't predict the average "
         "return (&rho;=−0.02) but it strongly predicts the <b>excursion</b> (&rho;=+0.11; MFE 15% vs 27%). "
         "Small candles win more often (60%) and go nowhere. <b>R and reward are the same variable.</b>"],
        ["Cap the entry extension / don't buy far above the SMA", "1.29 &rarr; 0.47", "<b>Extension IS "
         "relative strength</b> — high-RS names are extended <i>because</i> of the strength that makes "
         "them win. On the traded book the 15-25% and &gt;25% extension buckets contribute <b>69% of all "
         "R</b>; Spearman(ext, R) = −0.09. Filtering them pushes CRS below its own pool's random mean. "
         "Killed in 5 forms: near_sma, ext_cap, pool-filter, stratified-CRS, bucket-prior."],
        ["RSI-oversold filter", "killed 3×", "The indicator <i>subtracts</i> from the dip setup."],
        ["Grade-A only (top-5 CRS/week)", "1.17 vs 1.29", "A defensive variant, not a return edge."],
        ["The whole indicator zoo at this horizon", "IC ≈ 0", "RSI / MACD / Stochastic / Williams / CCI / "
         "Bollinger / MFI / OBV all have no rank information here."],
    ], [46 * mm, 26 * mm, W - 72 * mm], st)]

    # 8 — caveats
    F += [Paragraph("8 · Data caveats — real, and they will show up on your charts", st["h2"])]
    F += [_table([
        ["Issue", "Status"],
        ["Unadjusted splits", "<b>Known bug.</b> The price file has ~19 unadjusted splits, so a 1:4 split "
                              "reads as a −75% loss (the CGCL case you caught: entry 763.65 vs "
                              "TradingView ~190). <b>Trades spanning a detected split are EXCLUDED from "
                              "this CSV.</b> If a chart still looks like an impossible cliff, it is likely "
                              "one we failed to detect — flag it."],
        ["Survivor bias", "The pinned price file is survivor-only (103 of 813 point-in-time members are "
                          "missing). A backfill recovering all 103 exists but is not yet the pin — "
                          "re-anchoring it is a governance decision. Measured effect: it makes results "
                          "look <b>better</b> than reality, and it scales with holding period."],
        ["Prices are NSE, unadjusted for dividends", "Expect small cosmetic gaps vs TradingView."],
    ], [30 * mm, W - 30 * mm], st)]

    # 9 — what to look for
    F += [Paragraph("9 · What would actually be useful to find", st["h2"]),
          P("Four independent tests have now said the losers do <b>not</b> fail for a findable entry reason "
            "(prior forensic; ML AUC 0.536; a blind vision review found no grade gap; a learned ranker "
            "scored AUC 0.472, worse than random). So the highest-value thing you can find is <b>not</b> "
            "“this trade looks bad” — it is one of these:")]
    F += [_table([
        ["Look for", "Why it matters"],
        ["A trade that <b>should not exist</b> under §2", "A rule is mis-implemented — that is a bug, and "
         "bugs are free wins. (Your ZFCVINDIA / RCF catch was exactly this.)"],
        ["A price that <b>disagrees with TradingView</b>", "A data bug, like CGCL. Also a free win, and it "
         "affects the live cron, not just the backtest."],
        ["A <b>fill</b> you could not have got in real life", "Execution realism. Check entry_date's open "
         "against the chart."],
        ["A winner we <b>exited too early</b>", "The right tail is the entire edge, so leaks here are worth "
         "more than any loss we could have avoided."],
        ["A <b>setup shape</b> we have no rule for", "Genuinely new information. Note what the chart looks "
         "like, not which indicator you'd add — the indicators are all dead (§7)."],
    ], [52 * mm, W - 52 * mm], st)]

    F += [Spacer(1, 6), Paragraph("Generated by scripts/export_tv_review2.py from "
                                  "scripts/run_bhanushali_weekly_rank.py. Regenerate rather than hand-edit.",
                                  st["small"])]
    doc.build(F)
    return path
