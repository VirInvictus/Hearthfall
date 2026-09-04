"""Slice 1 of SP 6: the dumb single-roll resolution. If these fail, violence
cannot be balanced or replayed, which is the whole point of the abstract form."""

from __future__ import annotations

import unittest

from hearthfall.engine.combat import Outcome, resolve
from hearthfall.engine.rng import Rng


def _sweep(ours: int, theirs: int, seeds: int = 200) -> tuple[int, float]:
    """Run many seeds; return (wins, mean odds). Wide bounds only — the suite
    guards the arithmetic, not the tuning."""
    wins = 0
    odds_sum = 0.0
    for seed in range(seeds):
        outcome = resolve(ours, theirs, Rng(seed))
        wins += outcome.won
        odds_sum += outcome.odds
    return wins, odds_sum / seeds


class TestResolution(unittest.TestCase):
    def test_same_seed_replays_exactly(self):
        a = resolve(8, 5, Rng(1312))
        b = resolve(8, 5, Rng(1312))
        self.assertEqual(a, b)

    def test_exactly_one_rng_draw_is_consumed(self):
        # The outcome's roll IS the first draw of the stream, and the rng is
        # left exactly one fraction() deep: a second resolve would then be
        # reproducible from the stream's next draw alone.
        fought, fresh = Rng(99), Rng(99)
        outcome = resolve(6, 4, fought)
        self.assertEqual(outcome.roll, fresh.fraction())
        self.assertEqual(fought.fraction(), fresh.fraction())

    def test_equal_strength_is_an_even_coin(self):
        outcome = resolve(5, 5, Rng(1))
        self.assertEqual(outcome.odds, 0.5)
        wins, mean_odds = _sweep(5, 5)
        self.assertGreaterEqual(mean_odds, 0.49)
        self.assertLessEqual(mean_odds, 0.51)
        # 200 seeds at even odds: all-way one side would mean the roll is bent.
        self.assertTrue(60 <= wins <= 140, f"even coin went {wins}/200")

    def test_odds_track_the_strength_ratio(self):
        self.assertGreater(resolve(10, 5, Rng(1)).odds, resolve(5, 5, Rng(1)).odds)
        self.assertGreater(resolve(5, 5, Rng(1)).odds, resolve(5, 10, Rng(1)).odds)
        # Sweep monotonicity, not just the point value.
        weak, _ = _sweep(2, 8)
        strong, _ = _sweep(8, 2)
        self.assertGreater(strong, weak)

    def test_overwhelming_strength_wins_the_sweep(self):
        wins, odds = _sweep(100, 1)
        # Odds 100/101 is about 0.99, so ~2 losses in 200 seeds is the math
        # working, not a bent coin.
        self.assertGreater(odds, 0.95)
        self.assertGreaterEqual(wins, 190)

    def test_zero_strength_loses_without_appeal(self):
        outcome = resolve(0, 5, Rng(1))
        self.assertFalse(outcome.won)
        self.assertEqual(outcome.odds, 0.0)
        self.assertEqual(resolve(0, 0, Rng(1)).odds, 0.0)

    def test_margin_sign_agrees_with_the_outcome(self):
        for seed in range(100):
            outcome = resolve(7, 5, Rng(seed))
            self.assertEqual(outcome.won, outcome.margin > 0)

    def test_outcome_is_a_frozen_value(self):
        outcome = resolve(3, 3, Rng(1))
        self.assertIsInstance(outcome, Outcome)
        with self.assertRaises(AttributeError):
            outcome.won = not outcome.won  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()


class TestTerrainAndMorale(unittest.TestCase):
    """Slice 2: the modifiers scale effective strength before the share, and
    every one of them is optional — defaults must reproduce slice 1 exactly."""

    def test_defaults_reproduce_slice_one(self):
        a = resolve(5, 5, Rng(42))
        b = resolve(5, 5, Rng(42), our_ground=None, their_morale=None)
        self.assertEqual(a, b)

    def test_hills_favor_and_marsh_punishes(self):
        from hearthfall.engine.world import Terrain

        even = resolve(5, 5, Rng(1)).odds
        hills = resolve(5, 5, Rng(1), our_ground=Terrain.HILLS).odds
        marsh = resolve(5, 5, Rng(1), our_ground=Terrain.MARSH).odds
        self.assertGreater(hills, even)
        self.assertLess(marsh, even)
        # Same ground on both sides cancels: the share is back to even.
        both = resolve(
            5, 5, Rng(1), our_ground=Terrain.HILLS, their_ground=Terrain.HILLS
        )
        self.assertAlmostEqual(both.odds, 0.5)

    def test_terrain_weight_comes_from_balance(self):
        from hearthfall.engine.balance import TERRAIN_COMBAT_WEIGHT
        from hearthfall.engine.world import Terrain

        p = resolve(5, 5, Rng(1), our_ground=Terrain.HILLS).odds
        expected = (
            5
            * TERRAIN_COMBAT_WEIGHT[Terrain.HILLS]
            / (5 * TERRAIN_COMBAT_WEIGHT[Terrain.HILLS] + 5)
        )
        self.assertAlmostEqual(p, expected)

    def test_morale_shifts_the_odds_with_parity_at_five(self):
        from hearthfall.engine.balance import (
            MORALE_COMBAT_CEIL,
            MORALE_COMBAT_FLOOR,
        )

        parity = resolve(5, 5, Rng(1), our_morale=5).odds
        self.assertAlmostEqual(parity, 0.5)
        jubilant = resolve(5, 5, Rng(1), our_morale=10).odds
        broken = resolve(5, 5, Rng(1), our_morale=0).odds
        self.assertGreater(jubilant, 0.5)
        self.assertLess(broken, 0.5)
        # The extremes are the balance band itself: 1.2 strength vs 0.8 is
        # odds 0.6, the exact legible number the band promises.
        both = resolve(5, 5, Rng(1), our_morale=10, their_morale=0).odds
        self.assertAlmostEqual(
            both, MORALE_COMBAT_CEIL / (MORALE_COMBAT_CEIL + MORALE_COMBAT_FLOOR)
        )

    def test_modified_fights_stay_deterministic_and_one_draw(self):
        from hearthfall.engine.world import Terrain

        fought, fresh = Rng(7), Rng(7)
        outcome = resolve(6, 4, fought, our_ground=Terrain.HILLS, our_morale=8)
        self.assertEqual(outcome.roll, fresh.fraction())
        self.assertEqual(fought.fraction(), fresh.fraction())
