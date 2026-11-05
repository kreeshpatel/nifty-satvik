# Design Brief v5 — "Ledger"

Owner request (2026-11-05): a completely new, professional website and dashboard at the level
of large financial-technology companies, trading-themed, Robinhood-grade attention to small
details, secure, accessible, comfortable to work in, and no new running cost. This brief is
written **before** the build: what to do, how to do it, and what to keep in mind.

---

## 1. What we are designing

| Surface | Today | v5 goal |
|---|---|---|
| Marketing site (`/`) | Comprehensive, compliance-reviewed copy; glassy navy, glow-heavy | Same substance, rebuilt as a calm, editorial, confident page |
| Sign-in (`/login`, password reset) | Functional | A focused, trustworthy entry with clear security cues |
| App shell (top bar, rail, mobile nav) | Pill nav on glass | Quiet, dense, keyboard-first chrome |
| Dashboard (`/dashboard`) | Card grid, decent | A "command center" whose first screen answers: what to sell, what to buy, how the holds are doing |
| Every other page | Inherit tokens | Inherit v5 tokens automatically; re-skin individually later |

## 2. References and what we take from each

- **Robinhood (2024 identity by Porto Rocha).** One signature colour used with discipline;
  very large, confident numbers; one line chart that *is* the page; generous whitespace;
  the screen's accent follows the state (up or down).
- **Linear.** Dark-first app, near-neutral ground, 1px hairlines instead of glow, a tight 4px
  spacing ramp, keyboard-first navigation (a command palette).
- **Stripe.** Marketing pages that explain with real product pictures; precise typography;
  restraint with gradients.
- **Vercel / Geist.** A purpose-built sans and its matching mono, so prices and percentages
  align in columns without looking like code.
- **Bloomberg / Zerodha Kite.** Density where the operator needs it: tables, tabular figures,
  no decorative motion in data regions.

## 3. The design language

**Idea.** *Satvik* means pure, balanced. The interface should feel like a well-kept ledger:
calm surfaces, exact numbers, colour only where it carries meaning.

**Colour (dark is the default; a light theme is a later phase).**

| Token | Value | Role |
|---|---|---|
| ground | `#0A0C10` | page — near-neutral ink, no navy cast |
| surface 1 / 2 / 3 | `#111419` / `#171B21` / `#1E232B` | cards / hover / inputs |
| hairline 1 / 2 | `#20252D` / `#2A303A` | borders and dividers |
| ink 1 / 2 / 3 | `#F3F5F8` / `#A8B0BC` / `#78818E` | text ramp (3 is AA on ground) |
| brand | `#3D7BFF` | the logo blue; interactive elements only |
| up | `#20C4A0` | gains, buys, take-profit |
| down | `#FF6B4A` | losses, stops, sells |
| warn | `#F5A524` | low conviction, stale data |

Up/down were chosen with the dataviz palette validator against the chart surface
`#111419`: the conventional `#1FCB7A`/`#FF5A5F` pair separates by only ΔE 4.9 for
deuteranopes (fail); `#20C4A0`/`#FF6B4A` separates by ΔE 11.1 (pass, target ≥ 8) and still
reads as gain/loss. Arrows and signs remain mandatory regardless (§4.2).

Gradients and glow are reserved for at most one hero moment per page.

**Type.** Geist for everything, self-hosted and open-licensed. Every price, %, R and count
uses Geist's tabular numerals, so columns align without the "code" look of a monospace
(tested 2026-11-05: Geist Mono made the dashboard read like a terminal log). Geist Mono
is bundled for identifiers only. Display sizes use negative tracking (−0.03em); body text
never goes below 13px in the app or 15px on the marketing site.

**Shape and depth.** Radius 8 (controls), 12 (cards), 16 (panels). Solid surfaces, no
backdrop blur. Depth comes from a 1px hairline and a lighter surface, not from shadow.

**Motion.** 120–200ms, ease-out. Numbers may tick; nothing drifts, parallaxes or loops
inside a data region. Everything honours `prefers-reduced-motion`.

## 4. The small details (the checklist that makes it look expensive)

1. Every number uses tabular figures; currency is `₹` with Indian
   digit grouping (`10,19,489`); negative values use a true minus (`−`), not a hyphen.
2. Gains and losses are never colour-only (WCAG 1.4.1): always a sign and an arrow
   (`▲ +2.4%`, `▼ −1.1%`).
3. Every interactive element has a visible keyboard focus ring, a hover state, a pressed
   state, and a disabled state. Hit targets are at least 40px on touch.
4. Every data region has a designed loading (skeleton), empty, and error state.
5. Freshness is always visible: when the data was produced, and whether it is stale.
6. Alignment: numbers right-aligned in tables; labels and values share a baseline.
7. Copy is sentence case, short, and never overclaims (see §6).
8. Layout works at 390px, 768px and 1440px with no horizontal page scroll.
9. **Phones are for scanning, not reading** (owner, 2026-11-05). On a phone: tighter vertical
   rhythm and smaller display type; any section of three or more cards becomes a swipeable
   row with the next card peeking (the affordance is visible); decorative intros hide, but
   caveat-bearing copy never does; FAQ starts collapsed; the primary action sits in a sticky
   bottom bar inside the thumb zone; tap targets stay ≥ 44px; the sticky header stays ≤ 56px.

## 5. How we will build it

- **Foundations first.** A new token layer (`tokens.css` v5) re-maps the existing variable
  names, so every existing page changes at once and nothing breaks. New fonts are bundled
  with `@fontsource`, so there is no third-party request and no CSP change.
- **Then the four surfaces**, each as a fresh component rather than a patch, in this order:
  marketing site → sign-in → app shell → dashboard. The old page stays in git, not in the
  bundle.
- **Data stays where it is.** The pages read the same endpoints (`/api/signals`,
  `/api/overview`, `/api/landing-stats`, …) through the existing React Query hooks. No new
  backend service; any backend change is limited to security and payload shape.
- **Verification on every surface:** production build, the production CSP served locally
  (zero violations), screenshots at 390 and 1440 with a mocked API, the frontend unit
  tests, and the backend suite.

## 6. What to keep in mind (non-negotiables)

- **Compliance copy is load-bearing.** Not SEBI-registered research; not investment advice;
  invite-only; the user places every order; backtest numbers are in-sample, net of costs,
  and not certified. These sentences are carried over verbatim, not rewritten for style.
- **No invented numbers.** Marketing figures come from the API or the existing,
  reviewed copy; a product picture is labelled illustrative.
- **Security does not regress.** The enforced CSP (`script-src 'self'`) stays; no inline
  scripts, no new third-party origins, no analytics tags.
- **No new running cost.** Static hosting on Vercel's free tier, the existing Fly machine,
  no paid fonts, no paid component kits, no new SaaS.
- **Performance budget.** The marketing page must not load the 3D/particle libraries; the
  first screen should paint from the main bundle plus one route chunk.
- **Owner locks.** The DM Sans lock (2026-04-25) is lifted by the owner's 2026-11-05
  instruction ("permission to change anything related to design").

## 7. Phases

1. Foundations: v5 tokens, fonts, base components. — done 2026-11-05
2. Marketing site (`LandingV3`). — done 2026-11-05
3. Sign-in (`Login`). — done 2026-11-05
4. App shell (top bar re-skin, vector brand mark) and dashboard (`DashboardV5`). — done 2026-11-05
5. Next: re-skin This week, Research, Portfolio, Track record, History, Settings, Admin and the
   info/legal pages as fresh v5 components (they already inherit the v5 tokens); forgot/reset
   password onto `auth-v5.css`; a light theme; a social-share image.

---

## 8. Revision v6 — "Premium fintech" (owner feedback, 2026-11-05)

**Feedback.** v5 read as too sparse ("easy looking", "untidy"). The owner chose a premium
fintech direction (Revolut / Stripe / Groww) over a trading terminal or a corporate bank look,
with the website and dashboard redone together.

**What changes, and how**

| Element | v5 | v6 |
|---|---|---|
| Ground | flat near-black | deep navy-ink with a three-colour mesh glow (blue, violet, cyan) |
| Cards | flat surface + hairline | layered: gradient surface, top highlight, deep two-stage shadow; featured cards get a gradient border |
| Type | 600–640 weight | 700–800 display weight, larger hero (up to 88px) |
| Buttons | white pill | brand-gradient fill with a soft coloured glow; 48px tall |
| Icons | outline in a grey tile | white glyph on a gradient tile, one hue family per meaning |
| Product imagery | a chart card | a 3D-tilted phone showing the app, with floating stat and signal cards |
| Colour blocks | none | full-width gradient band for the closing call to action; gradient stat cards |

**What stays.** Validated up/down colours, arrows and signs on every move, compliance copy
verbatim, no invented numbers (the phone shows labelled sample content), strict CSP, no new
running cost, the mobile density rules (§4.9), `prefers-reduced-motion` stops all floating
motion.

## 9. Revision v6.1 — density and the remaining pages (owner, 2026-11-05)

**Feedback.** "Good — keep going on the detail (spacing, formatting, icons, palette) and make it
a little denser. Not Bloomberg; just a step denser than now."

**Density, as numbers** (app pages; the marketing site tightens by the same ratio):

| Token | v6 | v6.1 |
|---|---|---|
| Card padding | 20–24px | 16px (dense rows 12px) |
| Grid gap | 16px | 12px |
| Section gap | 36px | 24px |
| Body / row text | 14–15px | 13.5px |
| Card radius | 18px | 16px |
| Table row height | ~48px | 40px |
| Page title | 34px | 26px, with a one-line description and an icon tile |

**One page anatomy for every app page.** Page header (gradient icon tile · title · one-line
description · actions on the right) → a summary row of compact stat cards where the page has
numbers → content in layered cards → disclaimer. Tables: sticky uppercase-free header, 40px rows,
right-aligned tabular figures, hover row, no vertical rules. Tabs and segmented controls: one
pill style everywhere. Status always as a chip with a dot.

**Icon system.** Lucide at 16px (inline) / 18px (tiles), 1.75 stroke; a tile's hue encodes its
meaning: blue-violet = product/navigation, cyan = market data, green = gains/targets/success,
amber = caution/time, coral = loss/stop. No emoji, no mixed icon sets.

**Accuracy fix found on the way.** Three more pages (the shared PageShell, Research, Portfolio)
carried the "SEBI Research Analyst … NSE data delayed 15 min" footer; all now read "Not
SEBI-registered · Model-generated research output · Prices are daily closes".
