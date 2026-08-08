"""The map: terrain generation and geometry.

Fog, the frontier, and reveal used to live here. They moved to `test_intel.py` when knowledge
became a property of a fact rather than of a tile (`spec.md` §1). What is left is the part of
the world that is true whether or not anybody has looked at it.
"""

from __future__ import annotations

import unittest

from hearthfall.engine.rng import Rng
from hearthfall.engine.world import Terrain, World

WEIGHTS = {Terrain.PLAIN: 8, Terrain.FOREST: 6, Terrain.HILLS: 4, Terrain.MARSH: 3}


def a_world(seed: int = 1, width: int = 5, height: int = 5) -> World:
    return World.generate(width, height, Rng(seed), WEIGHTS)


class TestGeneration(unittest.TestCase):
    def test_the_same_seed_lays_down_the_same_map(self):
        first, second = a_world(42), a_world(42)
        self.assertEqual(
            {coord: tile.terrain for coord, tile in first.tiles.items()},
            {coord: tile.terrain for coord, tile in second.tiles.items()},
        )

    def test_different_seeds_lay_down_different_maps(self):
        first, second = a_world(1), a_world(2)
        self.assertNotEqual(
            {coord: tile.terrain for coord, tile in first.tiles.items()},
            {coord: tile.terrain for coord, tile in second.tiles.items()},
        )

    def test_every_tile_is_generated(self):
        world = a_world(width=4, height=6)
        self.assertEqual(len(world.tiles), 24)

    def test_the_hearth_stands_on_liveable_ground(self):
        # Whatever the terrain draw said, home is never marsh or water.
        for seed in range(20):
            world = a_world(seed)
            self.assertEqual(world.tile(world.home).terrain, Terrain.PLAIN)

    def test_home_is_the_centre(self):
        self.assertEqual(a_world(width=5, height=5).home, (2, 2))

    def test_the_world_holds_no_opinion_about_what_is_known(self):
        # The whole point of the migration: geography carries no knowledge. If a `revealed`
        # flag ever comes back here, there are two answers to "do we know this ground".
        world = a_world()
        self.assertFalse(hasattr(world.tile(world.home), "revealed"))
        for attribute in ("reveal", "frontier", "revealed", "known_count"):
            self.assertFalse(
                hasattr(world, attribute),
                f"World.{attribute} belongs to the ledger now",
            )


class TestNeighbours(unittest.TestCase):
    def test_neighbours_are_orthogonal_only(self):
        world = a_world()
        self.assertEqual(world.neighbours((2, 2)), [(1, 2), (2, 1), (2, 3), (3, 2)])

    def test_neighbours_are_clipped_to_the_map(self):
        world = a_world()
        self.assertEqual(world.neighbours((0, 0)), [(0, 1), (1, 0)])

    def test_neighbours_come_back_sorted(self):
        world = a_world()
        for coord in [(0, 0), (2, 2), (4, 4), (1, 3)]:
            self.assertEqual(world.neighbours(coord), sorted(world.neighbours(coord)))

    def test_in_bounds(self):
        world = a_world(width=3, height=3)
        self.assertTrue(world.in_bounds((0, 0)))
        self.assertTrue(world.in_bounds((2, 2)))
        self.assertFalse(world.in_bounds((3, 0)))
        self.assertFalse(world.in_bounds((-1, 0)))


if __name__ == "__main__":
    unittest.main()
