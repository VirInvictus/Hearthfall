"""The fact ledger: what we know, when we learned it, and how much to trust it.

`spec.md` §1 makes this the spine module. Fog stops being a property of a tile and becomes a
property of a fact, so the same machinery answers "have we walked there" and, later, "how
many spears did Stonefold have when we last looked".
"""

from __future__ import annotations

import unittest

from hearthfall.engine.intel import FactKind, Ledger, Staleness
from hearthfall.engine.rng import Rng
from hearthfall.engine.world import Terrain, World

WEIGHTS = {Terrain.PLAIN: 8, Terrain.FOREST: 6, Terrain.HILLS: 4, Terrain.MARSH: 3}

# Terrain never goes stale; ground does not move. Presence goes stale fastest, because a
# band that camped somewhere last spring tells you very little this autumn.
HALFLIVES = {
    FactKind.TERRAIN: None,
    FactKind.FORAGE: 8,
    FactKind.PRESENCE: 2,
}


def a_world(seed: int = 1, width: int = 5, height: int = 5) -> World:
    return World.generate(width, height, Rng(seed), WEIGHTS)


def a_ledger() -> Ledger:
    return Ledger(halflives=HALFLIVES)


class TestLearning(unittest.TestCase):
    def test_a_fact_we_have_never_looked_at_is_unknown(self):
        ledger = a_ledger()
        self.assertFalse(ledger.knows(FactKind.TERRAIN, (1, 1)))
        self.assertIsNone(ledger.fact(FactKind.TERRAIN, (1, 1)))
        self.assertIsNone(ledger.age(FactKind.TERRAIN, (1, 1), now=5))

    def test_learning_records_the_value_and_the_turn(self):
        ledger = a_ledger()
        ledger.learn(FactKind.TERRAIN, (1, 1), Terrain.FOREST, turn=3)
        fact = ledger.fact(FactKind.TERRAIN, (1, 1))
        assert fact is not None
        self.assertEqual(fact.value, Terrain.FOREST)
        self.assertEqual(fact.learned_turn, 3)
        self.assertTrue(ledger.knows(FactKind.TERRAIN, (1, 1)))

    def test_age_counts_seasons_since_we_looked(self):
        ledger = a_ledger()
        ledger.learn(FactKind.PRESENCE, (1, 1), "wolves", turn=3)
        self.assertEqual(ledger.age(FactKind.PRESENCE, (1, 1), now=3), 0)
        self.assertEqual(ledger.age(FactKind.PRESENCE, (1, 1), now=9), 6)

    def test_looking_again_resets_the_age(self):
        ledger = a_ledger()
        ledger.learn(FactKind.PRESENCE, (1, 1), "wolves", turn=1)
        ledger.learn(FactKind.PRESENCE, (1, 1), "nobody", turn=9)
        self.assertEqual(ledger.age(FactKind.PRESENCE, (1, 1), now=9), 0)
        self.assertEqual(ledger.value(FactKind.PRESENCE, (1, 1)), "nobody")

    def test_facts_can_hang_off_a_named_subject_not_just_a_tile(self):
        # Sub-project 4 needs "stonefold's spears"; the key shape must already allow it.
        ledger = a_ledger()
        ledger.learn(FactKind.PRESENCE, "stonefold", 40, turn=2)
        self.assertEqual(ledger.value(FactKind.PRESENCE, "stonefold"), 40)
        self.assertFalse(ledger.knows(FactKind.PRESENCE, (0, 0)))

    def test_a_tile_and_a_name_do_not_collide(self):
        ledger = a_ledger()
        ledger.learn(FactKind.PRESENCE, (1, 2), "wolves", turn=1)
        ledger.learn(FactKind.PRESENCE, "1,2", "a lie", turn=1)
        self.assertEqual(ledger.value(FactKind.PRESENCE, (1, 2)), "wolves")


class TestStaleness(unittest.TestCase):
    def test_never_looked_reads_as_never(self):
        self.assertIs(
            a_ledger().staleness(FactKind.FORAGE, (1, 1), now=4), Staleness.NEVER
        )

    def test_terrain_never_goes_stale(self):
        # A None half-life means the ground does not move. This is the case that keeps the
        # old boolean fog working unchanged underneath the new machinery.
        ledger = a_ledger()
        ledger.learn(FactKind.TERRAIN, (1, 1), Terrain.HILLS, turn=0)
        for now in (0, 10, 1_000):
            self.assertIs(
                ledger.staleness(FactKind.TERRAIN, (1, 1), now), Staleness.FRESH
            )

    def test_a_fact_within_its_halflife_is_fresh(self):
        ledger = a_ledger()
        ledger.learn(FactKind.PRESENCE, (1, 1), "wolves", turn=0)
        self.assertIs(ledger.staleness(FactKind.PRESENCE, (1, 1), 2), Staleness.FRESH)

    def test_a_fact_past_its_halflife_is_aging(self):
        ledger = a_ledger()
        ledger.learn(FactKind.PRESENCE, (1, 1), "wolves", turn=0)
        self.assertIs(ledger.staleness(FactKind.PRESENCE, (1, 1), 3), Staleness.AGING)
        self.assertIs(ledger.staleness(FactKind.PRESENCE, (1, 1), 4), Staleness.AGING)

    def test_a_fact_past_twice_its_halflife_is_stale(self):
        ledger = a_ledger()
        ledger.learn(FactKind.PRESENCE, (1, 1), "wolves", turn=0)
        self.assertIs(ledger.staleness(FactKind.PRESENCE, (1, 1), 5), Staleness.STALE)

    def test_kinds_age_at_their_own_rates(self):
        ledger = a_ledger()
        ledger.learn(FactKind.PRESENCE, (1, 1), "wolves", turn=0)
        ledger.learn(FactKind.FORAGE, (1, 1), 4, turn=0)
        self.assertIs(ledger.staleness(FactKind.PRESENCE, (1, 1), 5), Staleness.STALE)
        self.assertIs(ledger.staleness(FactKind.FORAGE, (1, 1), 5), Staleness.FRESH)


class TestTheMapAsFacts(unittest.TestCase):
    """The fog is the ledger's first client, not a parallel system."""

    def test_a_fresh_ledger_knows_nothing(self):
        self.assertEqual(a_ledger().revealed(), [])
        self.assertEqual(a_ledger().known_count, 0)

    def test_revealing_is_learning_the_terrain(self):
        world, ledger = a_world(), a_ledger()
        ledger.reveal(world, world.home, turn=0)
        self.assertEqual(ledger.revealed(), [world.home])
        self.assertEqual(ledger.known_count, 1)
        self.assertEqual(ledger.unknown_count(world), 24)
        self.assertEqual(
            ledger.value(FactKind.TERRAIN, world.home),
            world.tile(world.home).terrain,
        )

    def test_the_frontier_starts_around_the_hearth(self):
        world, ledger = a_world(), a_ledger()
        ledger.reveal(world, world.home, turn=0)
        self.assertEqual(ledger.frontier(world), [(1, 2), (2, 1), (2, 3), (3, 2)])

    def test_revealing_pushes_the_frontier_outward(self):
        world, ledger = a_world(), a_ledger()
        ledger.reveal(world, world.home, turn=0)
        ledger.reveal(world, (2, 1), turn=1)
        self.assertIn((2, 0), ledger.frontier(world))
        self.assertNotIn((2, 1), ledger.frontier(world))

    def test_the_frontier_never_includes_a_known_tile(self):
        world, ledger = a_world(), a_ledger()
        for coord in (world.home, (2, 1), (2, 3)):
            ledger.reveal(world, coord, turn=0)
        for coord in ledger.frontier(world):
            self.assertFalse(ledger.knows(FactKind.TERRAIN, coord))

    def test_a_fully_revealed_map_has_no_frontier(self):
        world, ledger = a_world(width=3, height=3), a_ledger()
        for coord in list(world.tiles):
            ledger.reveal(world, coord, turn=0)
        self.assertEqual(ledger.frontier(world), [])
        self.assertTrue(ledger.fully_explored(world))

    def test_the_frontier_comes_back_sorted(self):
        world, ledger = a_world(), a_ledger()
        ledger.reveal(world, world.home, turn=0)
        self.assertEqual(ledger.frontier(world), sorted(ledger.frontier(world)))

    def test_presence_facts_do_not_count_as_map_knowledge(self):
        # Seeing smoke from a distance is not the same as having walked the ground.
        world, ledger = a_world(), a_ledger()
        ledger.learn(FactKind.PRESENCE, (0, 0), "smoke", turn=0)
        self.assertEqual(ledger.revealed(), [])
        self.assertIn((0, 0), [c for c in world.tiles if c not in ledger.revealed()])


if __name__ == "__main__":
    unittest.main()
