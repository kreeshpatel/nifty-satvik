# Digest: "900+ Hours of Using Claude Code for Trading — What I Learned"

**Source:** https://medium.com/@aiintrading/900-hours-of-using-claude-code-for-trading-what-i-learned-d0a11871b16c
**Author:** AI in Trading (Medium publication)
**Published:** 2026-03-13 | **Read time:** ~5 min
**License:** Public Medium article (no code repo, no explicit license)
**Credibility:** LOW-MEDIUM — practitioner UX tips, no methodology, no performance data, no code shared. Honest lived experience but zero quant rigor. Maps to workflow and process only; zero signal on alpha, data integrity, or Indian-market specifics.

---

## One-Para Summary

A short practitioner piece distilling six UX habits from heavy Claude Code use in a trading context. The core insight is mundane but real: AI-assisted quant work fails at the *workflow* layer before it fails at the *quant* layer — vague prompts, missing context files, no up-front strategy specification, and treating Claude as an oracle rather than a fast junior quant are the repeating failure modes. The article contains no methodology, no backtesting framework, no data-integrity content, and no financial results. Its value to NiftyQuant is entirely in process hygiene: the CLAUDE.md pattern (already in use here), prompt specificity habits, and the "plan before build" discipline map directly onto how we run the harness and research registry.

---

## High-Value Patterns

| # | Pattern | Source Name | Why Relevant to NiftyQuant | Port Target |
|---|---------|-------------|---------------------------|-------------|
| 1 | **Plan-before-build: strategy spec first** | "Plan Before You Build" | We have the pre-registration registry (diagnostics/research/preregistry/) but sessions still drift into coding before the hypothesis and data contract are written down. The article's "ask Claude for clarifying questions first" maps to: open a preregistry file BEFORE touching any src/ file. | research-discipline |
| 2 | **Tight function contracts in prompts** | "Treat AI Like a Junior Quant with ADHD" | When asking Claude to build harness components (Phase 4 overlay tester, Phase 5 conviction model), vague briefs produce plausible-looking but wrong implementations. The pattern: specify the function name, exact input DataFrame schema (columns + dtypes), exact output column name + semantics, and boundary conditions BEFORE asking for code. | harness |
| 3 | **CLAUDE.md as session-persistent context** | "Give Your AI Permanent Memory" | Already in use — but the article calls out the specific items that most reduce session-startup drift: data format spec (what our OHLCV schema looks like, split-heal rules), exact feature contract (feature_enrichment.py is the SSoT), risk rules, known quirks (VEDL demerger bug, PIT membership caveats). Our CLAUDE.md is strong on architecture but thin on these per-session quant invariants. | research-discipline |
| 4 | **Live data via MCP / API instead of manual CSV round-trips** | "Connect Claude to Live Data with MCP Servers" | We use yfinance + GitHub-cache-backed OHLCV. The lesson: when debugging a data-integrity issue (e.g., the demerger-as-split slope fabrication), point a tool directly at the live source rather than re-reading a potentially-stale cached CSV. Concretely: use the yfinance direct fetch in diagnostic scripts rather than loading data/ohlcv_incremental output. | data-quality |
| 5 | **Voice/length discipline: more context = better output** | "Voice Your Prompts" | The mechanism (spoken prompts are 2-3x longer, include conditionals omitted when typing) transfers as a writing discipline: when opening a research session or writing a preregistry entry, write the hypothesis as a paragraph, not a bullet. Longer context = fewer wrong assumptions in the implementation. Not a tool — a writing habit. | research-discipline |

---

## Portable Content (distilled, not verbatim)

### P1 — Strategy Specification Template (pre-build checklist)
Before writing any harness, overlay, or conviction-model code, answer in the preregistry file:
- Exact signal definition (what column, what threshold, what lookback)
- Data contract: input DataFrame schema (columns, dtypes, index)
- Output contract: what the function returns (column name, dtype, semantics)
- Boundary conditions: what happens on NaN, on a stock with < N days history, on a halt day
- Interaction with existing pipeline: where in `long_horizon_cron.py` does this slot?
- Cost of being wrong: what does a silent bug look like in signals_today.json?

### P2 — Tight Prompt Contract for Harness Components
When asking Claude (or writing code yourself) for a new harness component, lead with:
```
Function: `<name>(df: pd.DataFrame, cfg: dict) -> pd.Series`
Input df columns: [date (index), open, high, low, close, volume, sma200_slope_63, atr_pct, adv_cr]
Output: Boolean Series aligned to df.index, True = overlay condition met
Invariants: no lookahead (all windows close-only, no future rows), NaN-safe, PIT-clean
Edge cases: < min_history rows -> all False; zero-volume days -> treat as NaN
```

### P3 — CLAUDE.md Quant Invariants Addendum
Items worth adding or hardening in our CLAUDE.md that the article highlights as session-startup context:
- OHLCV schema: date-indexed, close-adjusted, split-healed, demerger-corrected (VEDL bug documented)
- Feature SSoT: `data/feature_enrichment.py` — never hardcode column lists in callers
- PIT membership: `data/index_membership.py` — filter BEFORE ranking, not after
- Known data landmines: VEDL sma200_slope_63 fabricated 2.16->24.94 pre-fix; ~16 glitch names from F5; survivor-only pre-2015
- Promotion bar: ΔSharpe>=+0.10 AND ΔCalmar>=+0.05 AND 2022-2026 positive AND walk-forward fold-pass>=60% AND bootstrap 95% CI excludes 0

---

## Distractions / Ignore

| Item | Why to Ignore |
|------|---------------|
| WisprFlow voice tool recommendation | Tool-specific, no quant relevance, not relevant to our CI/cron-based workflow |
| "Connect to broker APIs via MCP" framing | We already have the data layer wired; MCP broker integration is a UI concern (Kite), not a research concern |
| "Junior quant with ADHD" framing as novel insight | True but trivial — our CLAUDE.md and preregistry already encode this more rigorously |
| Substack/newsletter CTA | Marketing |
| Generic "bad prompts waste afternoons" warnings | Real but not actionable beyond what P1/P2 above already capture |
| Any implied strategy methodology (mean reversion on SPY) | US equities, wrong asset class, no methodology shared, zero transfer value |
| "200 lines of code that errors repeatedly" as failure archetype | Our failure mode is subtler: code that RUNS but silently violates PIT constraints or lookahead rules — the article doesn't address this at all |

---

## Meta-Assessment for NiftyQuant

The article's value is capped at **process hygiene**, not quant methodology. Nothing here challenges or confirms any of our validated KILLs (regime-entry-gate, sector-selection-overlays, RSI/MACD reversal). Nothing here contributes to Phase 4 harness design, Phase 5 conviction modeling, or Phase 6 sizing/exit overlays.

The one genuinely non-obvious point: the article makes explicit that the practitioners who succeed are not the most experienced coders but the ones who make the AI's guesses reliably correct through *system design* (persistent context, tight contracts, pre-planning). This is exactly what our preregistry + CLAUDE.md + feature SSoT architecture does. The article is weak validation that our discipline framework is on the right track — not a source of new ideas.

**Adoption verdict:** P1 (pre-build checklist) and P2 (tight prompt contract) are worth adding as a one-page addendum to our research discipline notes. P3 (CLAUDE.md hardening) is worth a quick pass against our actual CLAUDE.md. No code to port. No quant methodology to test.
