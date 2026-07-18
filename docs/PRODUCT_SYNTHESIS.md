# Product synthesis (Part 4) — combining the behavioral, adversarial, and positioning threads

*Synthesis of three parallel subagent explorations + the four foundation docs. Per the guardrails
(C10), subagent output is DATA, not truth: concrete security claims below were spot-verified against the
code (marked ✓); others are flagged "reported — verify." Compliance items stay QUESTIONS, never
conclusions. 2026-07-16.*

---

## 0. The headline: three independent threads converged on the SAME two keystones

The single most useful result is not any one report — it is that three threads that never saw each
other's work arrived at the same two foundations. Convergence from independent priors is the strongest
evidence a design choice is real (the same logic as the research program's adversarial verification).

**Keystone 1 — the immutable, hash-chained, server-authored signal snapshot.** Independently identified by:
- Part 1 §2 (the idempotent-vs-immutable boundary: a card a user acted on must never change).
- The **adversarial** thread: one snapshot artifact closes THREE of its top threats at once — leak
  traceability (per-user watermark + logged served-hash), publish-time integrity/provenance
  (T4.1/T4.4/T4.5), and dispute defensibility (T5.1–T5.3: today there is *no* server-side record of what
  was shown to whom, and the only per-user snapshot is client-written and erased on completion).
- The **positioning** thread (A2): the hash-chained forward record is the product's actual trust moat "in
  a field of screenshot liars."

→ **Build this first.** It is simultaneously a correctness floor, a security control, and the brand.

**Keystone 2 — build against the exit-plan INTERFACE, not against P.** Independently identified by Part 3
§31 and the positioning thread (A4). The three tranches (2R / pattern / runner) are *data*; swapping
P→LIVE→next when the forward wall speaks must be a config change, not a rewrite. Given the cold-start and
gate evidence already lean against P, this hedge is close to certain to pay off.

Everything below hangs off these two.

---

## 1. The reframe that reorganizes the whole product: it is a DISCIPLINE harness, not a signal feed

The behavioral and positioning threads independently reached the same thesis, and it is grounded in our
own `MONTECARLO_null.md`: **a random pick from the ranked pool scores the 0.74 null; the edge lives
entirely in taking the whole ranked book with discipline.** Therefore:

> The signal is nearly free (0.74 by luck). The product sells the **delta** between the disciplined book
> and the cherry-picked null. That delta is a *behavioral* product wearing a signal product's clothes.

This is not a slogan — it changes what "core" means. The discipline mechanisms are the product; the
signal list is the input. Concrete, buildable-on-current-primitives (from the behavioral thread):

- **Make the SET the unit of action, the row the exception.** Promote the existing `sizePortfolio()` (which
  already funds the whole A-book strongest-first) from a right-rail utility to the headline verb: "Take this
  week's book (N names)" = one click; cherry-picking = deliberately opening rows to deselect.
- **Friction on the skip, named by rank.** Deselecting the #1 CRS name gets the hardest costed copy
  ("dropping the top rank is where cherry-picking regresses toward 0.74"); never block (their capital), just
  make the skip effortful and *named*.
- **The discipline score, priced in Sharpe on the null segment.** A geometric per-user score (Coverage ·
  Fidelity · Timing · Exit-adherence · Hold-through · Concentration — geometric so one broken leg tanks it),
  shown as a live position on `[0.67 … 1.03]`: "at 71% you sit at ~0.92; taking the two names you skipped
  moves you to ~1.00." This turns the null finding into a live money gauge instead of a research doc.
- **Default-inversions** so discipline is the path of least resistance: set-take by default; resting 2R
  limit + stop **co-placed at buy** (critical because P is execution-sensitive, §23 — auto-place via Kite for
  in-app users); staggered capital deploy by default (defuse the day-one dump, §29); opt-OUT exits (Saturday
  digest says "confirming: sell the runner Monday" and it executes unless cancelled); "idle is winning"
  between scans (suppress the buy surface so there's nothing to fiddle with).
- **Flatten the familiarity/logo bias** (`TICKER_DOMAINS` gives blue-chips logos, mid-caps monograms) —
  the edge is disproportionately in the boring deep-near-SMA-touch names, so the logo asymmetry is a silent
  thumb on the cherry-pick scale. Label the boring high-edge setup as the *prize*, not the leftover.

The three most valuable book-specific behavioral traps to design against:
1. **Winner-cut / fat-tail decapitation** — cutting a runner early to "lock in gains" doesn't shave return,
   it *removes* the rare 10–40R monster that carries the whole book. The single most expensive user behavior
   and the most natural one. Never allow a runner-cut without the fat-tail interstitial; track winner-cut
   rate as more damaging than a skipped buy.
2. **The pattern-exit "selling after it already dropped" feeling** — the blow-off/runner exits always fire
   Monday after a down-week from the high, so it *feels* like selling the bottom. Reframe at the trigger with
   the R captured ("you're booking a +3.2R winner on schedule; the down-week IS the exhaustion signal"), not
   the drop from peak.
3. **Weekly-cadence boredom → off-model tinkering.** Between Saturdays there is correctly nothing to do;
   make "nothing to do" a satisfying, green, confirmed state and suppress the surfaces that invite fiddling.

---

## 2. Integrity & security — the one artifact + the verified quick-wins

The adversarial thread's structural point matches Keystone 1: today `GET /api/signals` serves a
**byte-identical, un-watermarked, un-gated, un-archived** envelope to every user, which is what makes leaks
untraceable, self-front-running maximal, and disputes indefensible. The snapshot artifact (per-user
watermark variant that does NOT corrupt the tradeable numbers + logged served-hash + publish-time
integrity gate) fixes all three at the serving layer.

**Capacity as an emergent (non-malicious) risk** (confirmed unimplemented in code): no per-name ADV
headroom budget, no user cap tied to capacity, no entry staggering. Many users buying the same top-5 on the
same Monday open degrade their own fills — the invite queue is *exclusivity, not capacity control*. Fix:
compute a per-name ADV budget (universe ADV ≥ 5cr is known), gate invite approvals on remaining headroom,
stagger/ jitter the BUY_OPEN window across cohorts, and track realized-vs-modeled slippage as a live
capacity gauge feeding the review cadence.

**Concrete security findings — spot-verified against the code (✓ = I confirmed it):**
- ✓ **Weaker password path on the live intake route.** `access_requests.py:173` only checks
  `len(password) < 6` and never calls `validate_password_strength` — the admin-facing account-creation path
  (how real subscribers are made) is materially weaker than the self-serve reset path. **Quick, safe fix.**
- ✓ **CORS trusts any `*.vercel.app`.** `main.py:130` `ALLOWED_ORIGIN_REGEX = https://([a-z0-9-]+\.)*vercel\.app`
  — any attacker-deployed Vercel site is a permitted browser origin. Limited today (bearer tokens in
  localStorage, not cookies) but a broad trust surface. **Quick fix: pin to the known deployments.**
- ✓ **Password-reset URL logged.** `auth.py:658` logs the live reset URL (SMTP not wired) — a 30-minute
  account-takeover link sits in host logs. Acceptable only while the owner is the sole log reader; becomes
  real exposure the moment log access widens.
- **Reported — verify:** IP behind Fly proxy is likely the edge address (audit trail + rate-limit keying
  near-useless without parsing `X-Forwarded-For`); WS ticket replay dedupe is single-process (breaks if Fly
  scales >1 worker); `reconcile_drift`/`markBought` accept client-supplied `fill_price`/`qty` feeding the
  P&L/tax pages (fine for solo-user, unverifiable if ever shared — ties to §28 fill_source); email-alias
  non-normalization enables multi-account; access-request endpoint is public with no CAPTCHA/dedicated
  limit. These are plausible and code-consistent but I did not individually confirm each — verify before
  acting.

These are **product/eng hardening**, cleanly separate from the strategy (guardrail: this is not a research
trial, touches no config, no golden). Flagged as a backlog for owner sign-off — security changes to a live,
outward-facing API deserve explicit approval, not a silent autonomous edit.

---

## 3. Positioning & compliance — honest value prop, and questions to verify

**The honest value proposition** (positioning thread, grounded in our findings): NOT "a signal service that
makes 27%." That number is in-sample, start-date-lucky (it caught 2020), attached to P (the research
program's own loser), and DSR-below-gate. The defensible props, in order of real value:
1. **Selection you can't reproduce by hand** — a 99–100th-percentile shortlist vs your own gut (true,
   provable, independent of the disputed CAGR).
2. **Manufactured discipline** — the product's actual job (§1).
3. **A hash-chained, un-editable track record** in a field of screenshot liars — the trust moat.
4. **A restraint engine** — it stays silent most days.

The build already carries most honest caveats (in-sample, not certified, DSR-below-gate, >40% DD). The work
is making that honesty **load-bearing, not fine-print**: put "in-sample, not your expected return" adjacent
to every big number; elevate the live forward NAV to a headline promise; and — the counter-intuitive move —
**publish the §30 divergence tripwire and the ~1-in-4-down-first-year cold-start figure on the marketing
page.** A product that shows you its own kill-switch makes a credibility claim no tip channel can match.
Stop implying the ₹10L→₹81L backtest is the offer; it is a ceiling a disciplined early-joined user
approaches but rarely beats (four leaks, all downward).

**"Which book am I following?"** must be shown honestly while the wall decides: *"Weekly-Swing (config P),
paper/forward-watch, not yet certified, under review vs a steadier-from-cold-start alternative (LIVE)."*
Hiding that a better-from-your-start-date config exists reads as betrayal in hindsight. This is Keystone 2
made user-visible.

**Compliance — QUESTIONS to verify with a SEBI-qualified professional (NOT legal conclusions, NOT advice).**
The positioning thread enumerated 20; the load-bearing clusters:
- **Classification:** does an invite-only systematic *signal* service fall under SEBI Research Analyst /
  Investment Adviser regs — and does the answer change moving from one user (the owner) to inviting others,
  or with/without a fee? Is the FAQ's self-classification ("not a registered RA/IA") sufficient as a matter
  of law, or can conduct (specific entry/stop/target to identified users) re-characterize it?
- **Research-vs-advice line:** does account-scaled position sizing + one-click Kite routing + imperative
  strings ("Buy today", "SELL ON NEXT OPEN") push "research" into regulated "advice"?
- **Performance claims (biggest exposure given P):** rules on showing *backtested* performance
  (in-sample, start-lucky, DSR-below-gate) to prospects; mandatory labeling/separation of hypothetical vs
  live; how self-reported external-broker fills (§28) may or may not be presented.
- **Record-keeping / suitability / risk disclosure:** if deemed RA/IA — rationale retention, KYC/suitability
  for a designed >40%-drawdown strategy, mandatory risk disclosures at prominence, owner conflict-of-interest.

Every one of these is *"verify with a SEBI-qualified professional."* The product should not ship broadening
of the user base without resolving the classification question, since the answer may narrow the conduct
(research-only, no per-user sizing, no imperative buy/sell) required to stay outside the regulated perimeter.

---

## 4. The build order, updated with everything on the table

Unchanged in spine, sharpened by the synthesis:

1. **Snapshot/immutability floor (Keystone 1) — build first.** Server-authored, hash-chained, per-signal
   immutable snapshot with a per-user watermark variant and logged served-hash. It is the correctness floor
   AND the top security control AND the brand's trust moat — three threads, one artifact.
2. **Config-swappable exit-plan interface (Keystone 2).** Make the three tranches data now, so P→LIVE is a
   config flip. Cheap now, decisive when the wall speaks.
3. **Phase B — position-scoped pattern + intraweek exit map.** Safe, observational, no user state. Extends
   the daily monitor; feeds the exit-stage/guidance the behavioral layer renders.
4. **Phase C — the user plane on the snapshot floor:** per-user execution ledger (with `fill_source`:
   broker-confirmed vs self-reported), durable journey memory, and the weekly reconciliation
   (model-state − user-ledger → per-user action items). The discipline-score computation lives here.
5. **Phase D — the discipline-harness UI:** set-take default, rank-named skip friction, the Sharpe-priced
   discipline gauge, co-placed resting orders, staggered deploy, opt-out exits, the cold-start drawdown
   reframe, honest "which book / not-your-expected-return" framing.
- **Parallel hardening backlog (owner sign-off):** the verified security quick-wins (password path, CORS,
  reset-URL) + the capacity/ADV budget. Separate from strategy; no trial, no golden touch.
- **Blocking external step:** the SEBI classification questions must be resolved with a professional before
  broadening the user base.

---

## 5. Reconciliation & rules hygiene (guardrail check)

- **Convergence, not contradiction:** the three threads agreed on the two keystones and the discipline
  thesis; no conflicts to reconcile. Where they overlapped (the snapshot artifact) I merged; where each was
  unique (behavioral mechanics, security specifics, compliance questions) I kept the distinct substance.
- **C10 honored:** verified 3 concrete security claims against code (✓), flagged the rest "verify."
- **C9 honored:** this is one synthesis doc, cross-referencing the four foundation docs, not duplicating
  them.
- **Research plane untouched:** nothing here is a trial; no `n_trials`, no config change, no golden risk.
  The strategy stays exactly as frozen; this is all product/positioning/security thinking in `docs/`.
- Compliance stays **questions to verify**, never conclusions — carried through verbatim.
