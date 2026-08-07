"""The liquidity cap has to be pinned by something, and until now it was not.

`base_risk_qty` takes the minimum of three constraints: the risk budget, the 15% position cap, and
`max_adv_participation × ADV / fill` — the rule that stops the book from pretending it can buy 5% of
a thin name's daily turnover without moving the price. A mutation probe on 2026-08-08 set
`MAX_ADV_PARTICIPATION` from 0.05 to 0.50 and the entire 664-test suite stayed green: both real-data
goldens produced byte-identical ledger hashes, and all four cases in
`test_stage2_golden::test_base_risk_qty_parity` still passed.

The reason is visible in that table. Its third case carries the comment `# 5% ADV cap binds`, but
with equity 1,000,000 / fill 5,000 / ADV 2e8 the three constraints evaluate to 50, **30**, and 2,000
— the *position* cap binds, and the ADV term is 66× away from mattering. So the one case that
claimed to cover the liquidity cap never touched it.

That matters in the direction that flatters: loosening or deleting the cap inflates the achievable
size on exactly the illiquid names where the fill is least believable, which raises CAGR. It is the
shape of defect this programme's plausibility rule exists to catch, and it would have passed review.
"""

from __future__ import annotations

import pytest

from config import MAX_ADV_PARTICIPATION
from nq.engine.portfolio import base_risk_qty


# (equity, fill, risk_per_share, adv, risk_pct) -> shares, with each constraint's value spelled out
# so a reader can see which one binds without re-deriving it.
#
#   risk budget = risk_pct% * equity / risk_per_share
#   position    = 15% * equity / fill
#   ADV         = MAX_ADV_PARTICIPATION * adv / fill
ADV_BINDING_CASES = [
    # risk 15,000 · position 1,500 · ADV 500  -> ADV binds
    ((1_000_000.0, 100.0, 2.0, 1e6, 3.0), 500),
    # risk 30,000 · position 15,000 · ADV 1,000 -> ADV binds hard on a very thin name
    ((1_000_000.0, 10.0, 1.0, 2e5, 3.0), 1_000),
    # risk 300 · position 1,500 · ADV 500 -> risk budget binds; ADV is present but not binding
    ((1_000_000.0, 100.0, 100.0, 1e6, 3.0), 300),
]


@pytest.mark.parametrize("args,expected", ADV_BINDING_CASES)
def test_adv_participation_cap_binds(args: tuple, expected: int):
    got = base_risk_qty(*args)
    assert got == expected, f"base_risk_qty{args} = {got}, expected {expected}"


def test_the_cap_is_what_makes_the_difference():
    """Guard the guard. If the ADV term were removed entirely the first case would return the
    position cap instead — so this test can actually tell the two apart, which the existing
    parity table could not."""
    args = (1_000_000.0, 100.0, 2.0, 1e6, 3.0)
    with_cap = base_risk_qty(*args)
    # A large finite multiplier, not math.inf: the cap is applied inside an int() cast, so infinity
    # raises OverflowError rather than falling through. Effectively-absent is what we want to model.
    without_cap = base_risk_qty(*args, max_adv_participation=1e9)
    assert with_cap == 500 and without_cap == 1_500, (
        f"expected the cap to bite (500) and its absence to fall through to the position cap "
        f"(1500); got {with_cap} and {without_cap}"
    )


def test_a_loosened_cap_changes_the_answer():
    """The exact mutation that passed 664 tests: 0.05 -> 0.50."""
    args = (1_000_000.0, 100.0, 2.0, 1e6, 3.0)
    assert base_risk_qty(*args, max_adv_participation=0.50) != base_risk_qty(*args), (
        "a 10x looser liquidity cap produced the same share count — the cap is not being applied"
    )


def test_the_default_is_the_config_value():
    """`base_risk_qty` defaults to `config.MAX_ADV_PARTICIPATION`. Pin the constant itself: it is
    an execution-realism assumption, not an implementation detail, and `research/baseline_v1.json`
    was measured under it."""
    assert MAX_ADV_PARTICIPATION == 0.05
    args = (1_000_000.0, 100.0, 2.0, 1e6, 3.0)
    assert base_risk_qty(*args) == base_risk_qty(*args, max_adv_participation=MAX_ADV_PARTICIPATION)


def test_zero_adv_does_not_cap():
    """A name with no ADV data must not size to zero through the liquidity term — the guard is
    `if adv > 0`. Losing it would silently empty the book on any name with a missing ADV."""
    assert base_risk_qty(1_000_000.0, 100.0, 2.0, 0.0, 3.0) == 1_500
