"""The map, the fog, and the frontier."""

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

    def test_only_the_home_tile_starts_revealed(self):
        world = a_world()
        self.assertEqual(world.revealed(), [world.home])
        self.assertEqual(world.known_count, 1)
        self.assertEqual(world.unknown_count, 24)

    def test_the_hearth_stands_on_liveable_ground(self):
        # Whatever the terrain draw said, home is never marsh or water.
        for seed in range(20):
            world = a_world(seed)
            self.assertEqual(world.tile(world.home).terrain, Terrain.PLAIN)

    def test_home_is_the_centre(self):
        self.assertEqual(a_world(width=5, height=5).home, (2, 2))


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


class TestFrontier(unittest.TestCase):
    def test_the_frontier_starts_around_the_hearth(self):
        world = a_world()
        self.assertEqual(world.frontier(), [(1, 2), (2, 1), (2, 3), (3, 2)])

    def test_revealing_pushes_the_frontier_outward(self):
        world = a_world()
        world.reveal((2, 1))
        self.assertIn((2, 0), world.frontier())
        self.assertNotIn((2, 1), world.frontier())

    def test_the_frontier_never_includes_a_known_tile(self):
        world = a_world()
        world.reveal((2, 1))
        world.reveal((2, 3))
        for coord in world.frontier():
            self.assertFalse(world.tile(coord).revealed)

    def test_a_fully_revealed_map_has_no_frontier(self):
        world = a_world(width=3, height=3)
        for coord in list(world.tiles):
            world.reveal(coord)
        self.assertEqual(world.frontier(), [])
        self.assertTrue(world.fully_explored)

    def test_counts_track_reveals(self):
        world = a_world()
        world.reveal((2, 1))
        self.assertEqual(world.known_count, 2)
        self.assertEqual(world.unknown_count, 23)


if __name__ == "__main__":
    unittest.main()
