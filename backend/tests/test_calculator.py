from math import isclose

from backend.tft_odds.calculator import (
    apply_buy_policy,
    calculate_rolldown_distribution,
    calculate_shop_hit_distribution,
    calculate_slot_odds,
    chance_at_least,
)


def test_slot_odds_sum_to_one():
    odds = calculate_slot_odds(
        tier_odds=0.24,
        target_copies_remaining=8,
        tier_pool_remaining=90,
    )

    assert isclose(odds.target + odds.same_tier_non_target + odds.other_tier, 1.0)


def test_shop_distribution_sums_to_one():
    distribution = calculate_shop_hit_distribution(
        tier_odds=0.24,
        target_copies_remaining=8,
        tier_pool_remaining=90,
        shop_slots=5,
    )

    assert isclose(sum(distribution.values()), 1.0)


def test_shop_distribution_respects_finite_target_copies():
    distribution = calculate_shop_hit_distribution(
        tier_odds=1.0,
        target_copies_remaining=1,
        tier_pool_remaining=10,
        shop_slots=5,
    )

    assert max(distribution) == 1


def test_buy_policy_caps_by_need_and_gold():
    assert apply_buy_policy(
        shop_hits=3,
        copies_needed=2,
        gold_remaining=4,
        unit_cost=3,
    ) == 1


def test_rolldown_distribution_can_hit_goal():
    distribution = calculate_rolldown_distribution(
        tier_odds=1.0,
        target_copies_remaining=3,
        tier_pool_remaining=3,
        copies_needed=3,
        gold=15,
        roll_cost=2,
        unit_cost=1,
        shop_slots=5,
    )

    assert isclose(chance_at_least(distribution, 3), 1.0)
