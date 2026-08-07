# External literature — **STUB, NOT POPULATED**

> **Status: EMPTY.** This file contains no bands, no ranges, and no published figures. It is a slot,
> not a reference. `tests/test_plausibility_references.py` asserts it stays honest about that: it
> may not claim to be populated while it is empty.

## Why it is empty rather than filled in from memory

A plausibility prior is only useful if it is *sourced*. A remembered range — "Indian midcap momentum
runs mid-teens CAGR with drawdowns in the fifties" — is the right order of magnitude and completely
unciteable, and this programme's central rule is that a number informing a decision must be
reproducible from something committed, never from a transcript. Writing a plausible-looking band
here from recollection would create exactly the artifact the rule forbids, and worse: a band with a
filename, which every future session would then quote as established.

So it stays empty until the owner pastes the real thing.

## What belongs here

The external research compendium held outside this repo — the survey of published results for Indian
equity momentum and midcap strategies. For each entry:

| field | why |
|---|---|
| Claim | the band or figure itself |
| Source | paper, author, year, and where it can be re-read |
| Universe | index, size band, country, and how survivorship was handled |
| Period | the sample window, and whether it includes 2020 |
| Costs | gross or net, and the cost model assumed |
| Horizon | rebalance frequency and holding period |
| Comparability | what in our setup differs, and in which direction it should push |

The last row matters most. A published Sharpe measured gross, on a survivor-biased universe, over a
period ending in 2019, is not a bar our net, corrected, 2017–2026 number has to clear — and treating
it as one produces either false alarm or false comfort.

## Until then

`plausibility_anchors.md` carries the internal anchors, which *are* reproducible, and the
`plausibility-check` skill is written to work from those alone. When asked for an external band, a
session must say this file is unpopulated rather than supply a number from memory.
