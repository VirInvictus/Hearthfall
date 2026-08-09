"""Known ground is workable ground.

`forage_take` is the pure core of slice 2 and the first place the fact ledger pays for
itself: before it, a revealed tile fed nothing but the event table, so exploring was
mechanically pointless and the sub-project's question ("does paying to look pull the player
forward?") could only answer no.

It is pure and it is shared. `_produce` mutates and `forecast` does not, and those two keep
duplicating the *order* of the tick on purpose, but they call one function for the per-tile
arithmetic so a greedy fill cannot be written twice and drift.
"""

from __future__ import annotations

import unittest

from hearthfall.engine import balance, turn
from hearthfall.engine.intel import FactKind, Ledger
from hearthfall.engine.state import Season
from hearthfall.engine.world import Terrain

AUTUMN = (
    Season.AUTUMN
)  # base yield 5, the season with the most room to show a difference


def a_ledger(*terrains: Terrain) -> Ledger:
    """A ledger believing one tile of each terrain given, laid left to right along y=0."""
    ledger = Ledger(halflives=balance.FACT_HALFLIFE)
    for x, terrain in enumerate(terrains):
        ledger.learn(FactKind.TERRAIN, (x, 0), terrain, turn=0)
    return ledger


def per_forager(season: Season, terrain: Terrain) -> int:
    return balance.FORAGE_YIELD[season] * balance.TERRAIN_FORAGE[terrain] // 10


class TestCapacityIsTheCeiling(unittest.TestCase):
    def test_hands_beyond_the_known_ground_bring_back_nothing(self):
        # One plain supports two. The other four walked out and found no ground to work.
        take = turn.forage_take(a_ledger(Terrain.PLAIN), foragers=6, season=AUTUMN)
        self.assertEqual(take.capacity, balance.TERRAIN_CAPACITY[Terrain.PLAIN])
        self.assertEqual(take.idle, 6 - take.capacity)
        self.assertEqual(take.food, take.capacity * per_forager(AUTUMN, Terrain.PLAIN))

    def test_capacity_is_the_sum_over_known_tiles(self):
        take = turn.forage_take(
            a_ledger(Terrain.PLAIN, Terrain.FOREST, Terrain.HILLS),
            foragers=0,
            season=AUTUMN,
        )
        self.assertEqual(
            take.capacity,
            balance.TERRAIN_CAPACITY[Terrain.PLAIN]
            + balance.TERRAIN_CAPACITY[Terrain.FOREST]
            + balance.TERRAIN_CAPACITY[Terrain.HILLS],
        )

    def test_nobody_assigned_takes_nothing_and_idles_nobody(self):
        take = turn.forage_take(a_ledger(Terrain.FOREST), foragers=0, season=AUTUMN)
        self.assertEqual((take.food, take.idle, take.worked), (0, 0, ()))

    def test_knowing_nothing_leaves_every_hand_idle(self):
        take = turn.forage_take(a_ledger(), foragers=4, season=AUTUMN)
        self.assertEqual((take.food, take.capacity, take.idle), (0, 0, 4))


class TestTheBestGroundIsWorkedFirst(unittest.TestCase):
    def test_foragers_fill_the_richest_tile_before_the_poorest(self):
        # Forest out-yields marsh, so the first three hands belong in the forest whatever
        # order the tiles were learned in.
        take = turn.forage_take(
            a_ledger(Terrain.MARSH, Terrain.FOREST), foragers=3, season=AUTUMN
        )
        self.assertEqual([terrain for _, terrain, _ in take.worked], [Terrain.FOREST])
        self.assertEqual(take.food, 3 * per_forager(AUTUMN, Terrain.FOREST))

    def test_overflow_spills_onto_the_next_best_ground(self):
        take = turn.forage_take(
            a_ledger(Terrain.MARSH, Terrain.FOREST), foragers=4, season=AUTUMN
        )
        self.assertEqual(
            [terrain for _, terrain, _ in take.worked],
            [Terrain.FOREST, Terrain.MARSH],
        )
        self.assertEqual(
            take.food,
            3 * per_forager(AUTUMN, Terrain.FOREST)
            + 1 * per_forager(AUTUMN, Terrain.MARSH),
        )
        self.assertEqual(take.idle, 0)

    def test_the_fill_order_does_not_depend_on_the_order_tiles_were_learned(self):
        forwards = turn.forage_take(
            a_ledger(Terrain.HILLS, Terrain.FOREST, Terrain.PLAIN),
            foragers=5,
            season=AUTUMN,
        )
        backwards = turn.forage_take(
            a_ledger(Terrain.PLAIN, Terrain.FOREST, Terrain.HILLS),
            foragers=5,
            season=AUTUMN,
        )
        self.assertEqual(forwards.food, backwards.food)


class TestDeadGround(unittest.TestCase):
    def test_water_supports_nobody_and_yields_nothing(self):
        take = turn.forage_take(a_ledger(Terrain.WATER), foragers=3, season=AUTUMN)
        self.assertEqual((take.food, take.capacity, take.idle), (0, 0, 3))

    def test_water_does_not_swallow_hands_that_better_ground_could_use(self):
        # The bug this guards: filling a zero-capacity tile "first" and consuming a forager.
        take = turn.forage_take(
            a_ledger(Terrain.WATER, Terrain.PLAIN), foragers=2, season=AUTUMN
        )
        self.assertEqual(take.food, 2 * per_forager(AUTUMN, Terrain.PLAIN))
        self.assertEqual(take.idle, 0)


class TestWinterIsStillEmpty(unittest.TestCase):
    """The multiplicative shape exists to keep this true without a special case.

    Winter's base yield is zero, so no terrain can rescue it. An additive terrain bonus
    would have made good ground foragable in winter and quietly deleted the season's whole
    allocation puzzle, which `balance.FORAGE_YIELD` is explicitly tuned around.
    """

    def test_no_terrain_yields_anything_in_winter(self):
        for terrain in Terrain:
            with self.subTest(terrain=terrain):
                take = turn.forage_take(
                    a_ledger(terrain), foragers=4, season=Season.WINTER
                )
                self.assertEqual(take.food, 0)


class TestItReadsBeliefRatherThanTruth(unittest.TestCase):
    """The yield comes from the ledger, never from `world.tile`.

    They agree today, because `reveal` copies the ground faithfully. Slice 5 exists to make
    them disagree, and if the food math reads the world it will ignore staleness forever.
    This test fails the moment someone reaches for the world for convenience.
    """

    def test_a_tile_the_ledger_believes_is_forest_is_foraged_as_forest(self):
        ledger = Ledger(halflives=balance.FACT_HALFLIFE)
        ledger.learn(FactKind.TERRAIN, (0, 0), Terrain.FOREST, turn=0)
        take = turn.forage_take(ledger, foragers=3, season=AUTUMN)
        self.assertEqual(take.food, 3 * per_forager(AUTUMN, Terrain.FOREST))

    def test_a_tile_with_no_terrain_fact_is_not_workable(self):
        # A PRESENCE fact means somebody saw smoke over a ridge. Nobody walked the ground,
        # so there is nothing to forage there.
        ledger = Ledger(halflives=balance.FACT_HALFLIFE)
        ledger.learn(FactKind.PRESENCE, (0, 0), "wolves", turn=0)
        take = turn.forage_take(ledger, foragers=3, season=AUTUMN)
        self.assertEqual((take.food, take.capacity, take.idle), (0, 0, 3))


class TestTheReportedTilesAddUp(unittest.TestCase):
    def test_worked_tiles_account_for_every_unit_of_food(self):
        take = turn.forage_take(
            a_ledger(Terrain.FOREST, Terrain.PLAIN, Terrain.MARSH),
            foragers=5,
            season=AUTUMN,
        )
        self.assertEqual(sum(food for _, _, food in take.worked), take.food)

    def test_worked_tiles_are_distinct(self):
        take = turn.forage_take(
            a_ledger(Terrain.FOREST, Terrain.FOREST, Terrain.PLAIN),
            foragers=8,
            season=AUTUMN,
        )
        coords = [coord for coord, _, _ in take.worked]
        self.assertEqual(len(coords), len(set(coords)))


if __name__ == "__main__":
    unittest.main()
