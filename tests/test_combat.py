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
