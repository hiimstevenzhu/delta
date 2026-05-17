"""Core probability calculations for TFT shop odds.

This module has no web-framework dependency. The server layer should only
validate request/response shapes and call these functions.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import floor


ProbabilityDistribution = dict[int, float]


@dataclass(frozen=True)
class PoolState:
    """Remaining pool information for the target unit's tier."""

    target_copies_remaining: int
    tier_pool_remaining: int

    def validate(self) -> None:
        if self.target_copies_remaining < 0:
            raise ValueError("target_copies_remaining must be non-negative")
        if self.tier_pool_remaining < 0:
            raise ValueError("tier_pool_remaining must be non-negative")
        if self.target_copies_remaining > self.tier_pool_remaining:
            raise ValueError("target copies cannot exceed total tier pool")


@dataclass(frozen=True)
class SlotOdds:
    """One-slot outcome probabilities for the target tier."""

    target: float
    same_tier_non_target: float
    other_tier: float


def normalize_distribution(distribution: ProbabilityDistribution) -> ProbabilityDistribution:
    """Return a copy without tiny zero entries and with stable key ordering."""

    return {
        key: probability
        for key, probability in sorted(distribution.items())
        if probability > 1e-15
    }


def calculate_slot_odds(
    *,
    tier_odds: float,
    target_copies_remaining: int,
    tier_pool_remaining: int,
) -> SlotOdds:
    """Calculate target, same-tier non-target, and other-tier odds for one slot."""

    PoolState(target_copies_remaining, tier_pool_remaining).validate()
    if not 0 <= tier_odds <= 1:
        raise ValueError("tier_odds must be between 0 and 1")
    if tier_pool_remaining == 0:
        return SlotOdds(target=0.0, same_tier_non_target=0.0, other_tier=1.0)

    # Formula:
    # P(target) = P(slot rolls target tier) * P(target | target tier)
    #           = tier_odds * target_copies_remaining / tier_pool_remaining
    #
    # P(same tier, not target)
    #           = tier_odds * non_target_same_tier_copies / tier_pool_remaining
    #
    # P(other tier) = 1 - tier_odds
    target = tier_odds * (target_copies_remaining / tier_pool_remaining)
    same_tier_non_target = tier_odds * (
        (tier_pool_remaining - target_copies_remaining) / tier_pool_remaining
    )
    other_tier = 1.0 - tier_odds
    return SlotOdds(
        target=target,
        same_tier_non_target=same_tier_non_target,
        other_tier=other_tier,
    )


def calculate_shop_hit_distribution(
    *,
    tier_odds: float,
    target_copies_remaining: int,
    tier_pool_remaining: int,
    shop_slots: int = 5,
) -> ProbabilityDistribution:
    """Calculate exact target-hit distribution for one shop.

    The shop is generated sequentially. Target-tier slots temporarily remove one
    copy from the tier pool for the rest of the shop. Only target hits are
    counted in the returned distribution.
    """

    PoolState(target_copies_remaining, tier_pool_remaining).validate()
    if shop_slots < 0:
        raise ValueError("shop_slots must be non-negative")

    states: dict[tuple[int, int, int], float] = {
        (0, target_copies_remaining, tier_pool_remaining): 1.0
    }

    # Sequential shop DP:
    # state = (hits_so_far, target_left_in_temp_shop_pool, tier_pool_left_in_temp_shop_pool)
    #
    # For each slot:
    # P(next_state) += P(current_state) * P(slot_outcome | current_state)
    #
    # Slot outcomes:
    # - other tier: pool does not change
    # - target: hits + 1, target_left - 1, tier_pool_left - 1
    # - same-tier non-target: tier_pool_left - 1
    for _ in range(shop_slots):
        next_states: dict[tuple[int, int, int], float] = {}
        for (hits, target_left, tier_pool_left), state_probability in states.items():
            slot_odds = calculate_slot_odds(
                tier_odds=tier_odds,
                target_copies_remaining=target_left,
                tier_pool_remaining=tier_pool_left,
            )

            _add_probability(
                next_states,
                (hits, target_left, tier_pool_left),
                state_probability * slot_odds.other_tier,
            )

            if target_left > 0 and tier_pool_left > 0:
                _add_probability(
                    next_states,
                    (hits + 1, target_left - 1, tier_pool_left - 1),
                    state_probability * slot_odds.target,
                )

            same_tier_left = tier_pool_left - target_left
            if same_tier_left > 0 and tier_pool_left > 0:
                _add_probability(
                    next_states,
                    (hits, target_left, tier_pool_left - 1),
                    state_probability * slot_odds.same_tier_non_target,
                )

        states = next_states

    distribution: ProbabilityDistribution = {}
    for (hits, _, _), probability in states.items():
        _add_probability(distribution, hits, probability)

    return normalize_distribution(distribution)


def apply_buy_policy(
    *,
    shop_hits: int,
    copies_needed: int,
    gold_remaining: int,
    unit_cost: int,
) -> int:
    """Return how many target copies are bought from a shop."""

    if min(shop_hits, copies_needed, gold_remaining, unit_cost) < 0:
        raise ValueError("shop_hits, copies_needed, gold_remaining, and unit_cost must be non-negative")
    if unit_cost <= 0:
        raise ValueError("unit_cost must be positive")

    # Formula:
    # affordable = floor(gold_remaining / unit_cost)
    # copies_to_buy = min(shop_hits, copies_needed, affordable)
    affordable = floor(gold_remaining / unit_cost)
    return min(shop_hits, copies_needed, affordable)


def calculate_rolldown_distribution(
    *,
    tier_odds: float,
    target_copies_remaining: int,
    tier_pool_remaining: int,
    copies_needed: int,
    gold: int,
    roll_cost: int,
    unit_cost: int,
    shop_slots: int = 5,
) -> ProbabilityDistribution:
    """Calculate final bought-copy distribution after repeatedly rolling.

    Policy: spend gold to roll, buy every target copy needed and affordable.
    The initial free shop is intentionally not included; this models paid
    refreshes only.
    """

    PoolState(target_copies_remaining, tier_pool_remaining).validate()
    if min(copies_needed, gold, roll_cost, unit_cost) < 0:
        raise ValueError("copies_needed, gold, roll_cost, and unit_cost must be non-negative")
    if roll_cost <= 0:
        raise ValueError("roll_cost must be positive")
    if unit_cost <= 0:
        raise ValueError("unit_cost must be positive")

    states: dict[tuple[int, int, int, int], float] = {
        (0, gold, target_copies_remaining, tier_pool_remaining): 1.0
    }

    # Rolldown DP:
    # state = (copies_bought, gold_left, target_left, tier_pool_left)
    #
    # For each active state:
    # 1. Pay roll_cost.
    # 2. Compute P(shop_hits = h) from the exact shop distribution.
    # 3. Buy min(h, copies still needed, affordable copies).
    # 4. Move probability mass to the updated state.
    #
    # Transition formula:
    # P(next_state) += P(current_state) * P(shop_hits = h)
    while True:
        active_states = [
            state
            for state in states
            if state[1] >= roll_cost and state[0] < copies_needed
        ]
        if not active_states:
            break

        next_states: dict[tuple[int, int, int, int], float] = {}
        for state, state_probability in states.items():
            copies_hit, gold_left, target_left, tier_pool_left = state
            if gold_left < roll_cost or copies_hit >= copies_needed:
                _add_probability(next_states, state, state_probability)
                continue

            gold_after_roll = gold_left - roll_cost
            shop_distribution = calculate_shop_hit_distribution(
                tier_odds=tier_odds,
                target_copies_remaining=target_left,
                tier_pool_remaining=tier_pool_left,
                shop_slots=shop_slots,
            )

            for shop_hits, shop_probability in shop_distribution.items():
                copies_to_buy = apply_buy_policy(
                    shop_hits=shop_hits,
                    copies_needed=copies_needed - copies_hit,
                    gold_remaining=gold_after_roll,
                    unit_cost=unit_cost,
                )
                next_state = (
                    copies_hit + copies_to_buy,
                    gold_after_roll - (copies_to_buy * unit_cost),
                    target_left - copies_to_buy,
                    tier_pool_left - copies_to_buy,
                )
                _add_probability(next_states, next_state, state_probability * shop_probability)

        states = next_states

    distribution: ProbabilityDistribution = {}
    for (copies_hit, _, _, _), probability in states.items():
        _add_probability(distribution, copies_hit, probability)

    return normalize_distribution(distribution)


def chance_at_least(distribution: ProbabilityDistribution, threshold: int) -> float:
    """Return probability of landing at least threshold successes."""

    # Formula: P(X >= threshold) = sum(P(X = x) for all x >= threshold)
    return sum(probability for hits, probability in distribution.items() if hits >= threshold)


def expected_value(distribution: ProbabilityDistribution) -> float:
    """Return expected value for an integer probability distribution."""

    # Formula: E[X] = sum(x * P(X = x))
    return sum(value * probability for value, probability in distribution.items())


def _add_probability(
    target: dict,
    key,
    probability: float,
) -> None:
    if probability <= 0:
        return
    target[key] = target.get(key, 0.0) + probability
