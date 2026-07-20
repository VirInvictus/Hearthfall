"""Determinism is invariant 3. If these fail, the project cannot be balanced."""

from __future__ import annotations

import unittest

from hearthfall.engine.rng import Rng


class TestDeterminism(unittest.TestCase):
    def _draws(self, seed: int) -> list[object]:
        rng = Rng(seed)
        return [
            rng.randint(1, 100),
            rng.chance(0.5),
            rng.choice("abcdef"),
            rng.shuffled(range(10)),
            rng.weighted([("a", 1), ("b", 3), ("c", 9)]),
        ]

    def test_same_seed_replays_exactly(self):
        self.assertEqual(self._draws(1312), self._draws(1312))

    def test_different_seeds_diverge(self):
        self.assertNotEqual(self._draws(1), self._draws(2))

    def test_instances_are_independent(self):
        first, second = Rng(7), Rng(7)
        first.randint(1, 100)
        self.assertNotEqual(
            [first.randint(1, 100) for _ in range(5)],
            [second.randint(1, 100) for _ in range(5)],
            "a draw on one instance must not be visible to another",
        )


class TestDraws(unittest.TestCase):
    def test_chance_bounds_are_absolute(self):
        rng = Rng(99)
        self.assertTrue(all(rng.chance(1.0) for _ in range(50)))
        self.assertFalse(any(rng.chance(0.0) for _ in range(50)))

    def test_randint_is_inclusive_at_both_ends(self):
        rng = Rng(4)
        seen = {rng.randint(1, 3) for _ in range(200)}
        self.assertEqual(seen, {1, 2, 3})

    def test_shuffled_leaves_the_input_alone(self):
        rng = Rng(5)
        table = ["a", "b", "c", "d", "e"]
        shuffled = rng.shuffled(table)
        self.assertEqual(table, ["a", "b", "c", "d", "e"])
        self.assertCountEqual(shuffled, table)

    def test_weighted_excludes_zero_weights(self):
        rng = Rng(11)
        picks = {rng.weighted([("live", 1), ("dead", 0)]) for _ in range(200)}
        self.assertEqual(picks, {"live"})

    def test_weighted_respects_the_weights(self):
        rng = Rng(2026)
        picks = [rng.weighted([("rare", 1), ("common", 19)]) for _ in range(2000)]
        self.assertGreater(picks.count("common"), picks.count("rare") * 5)

    def test_weighted_rejects_an_empty_pool(self):
        rng = Rng(1)
        with self.assertRaises(ValueError):
            rng.weighted([("nothing", 0)])


if __name__ == "__main__":
    unittest.main()
