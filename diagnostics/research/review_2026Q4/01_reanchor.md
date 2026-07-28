# §1 Corrected-universe re-anchor

**Pre-committed criterion (CLAUDE.md, the 0025 data-debt clause, verbatim):**
> "Finding 0025 measured the bias: **it scales with holding period** (−0.04 Sharpe tight-stop vs −0.18
> wide-stop swing configs) → the 63d-hold **baseline_v1 0.667 is exposed in the same direction; its
> corrected re-run is unblocked but re-anchors the pin → owner/governance decision (quarterly-review
> class)."

**Machinery:** `scripts/run_corrected_anchor.py` (full window, September). Smoke-proof 2026-07-29:
plumbing runs end-to-end; +104 recovered names; swing book shows the bias direction on the truncated
window; **FLAG carried into September:** the LH base was byte-identical pinned-vs-corrected on the
smoke window — the recovered names may be excluded by the solvency/fundamentals gate (W-04 class),
i.e. the correction may only bite through books whose universe filters admit the recovered names.
September must resolve whether that is a filter artifact or a true no-op.

**EVIDENCE (September fills):**
- [ ] full-window anchor table (pinned vs corrected, both books)
- [ ] trade diff + recovered-name attribution
- [ ] owner decision: re-anchor the pin / keep + caveat
