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
from hearthfall.engine.orders import Orders
from hearthfall.engine.state import Season
from hearthfall.engine.world import Terrain, Tile, World

AUTUMN = (
    Season.AUTUMN
)  # base yield 5, the season with the most room to show a difference


def a_world(*terrains: Terrain) -> World:
    """A strip of world matching what `a_ledger` believes, so belief and truth can diverge."""
    tiles = {
        (x, 0): Tile(terrain=terrain)
        for x, terrain in enumerate(terrains or (Terrain.FOREST,))
    }
    return World(width=len(tiles), height=1, home=(0, 0), tiles=tiles)


def a_ledger(*terrains: Terrain, surveyed: bool = True) -> Ledger:
    """A ledger believing one tile of each terrain given, laid left to right along y=0.

    Surveyed by default, because most of these tests are about the greedy fill rather than
    about how well the ground is known, and fully known ground is the case where a tile
    supports what its terrain says it supports. Pass `surveyed=False` for ground the clan has
    only walked past.
    """
    ledger = Ledger(halflives=balance.FACT_HALFLIFE)
    for x, terrain in enumerate(terrains):
        ledger.learn(FactKind.TERRAIN, (x, 0), terrain, turn=0)
        if surveyed:
            ledger.survey((x, 0), balance.TERRAIN_FORAGE[terrain], turn=0)
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


class TestSurveyedGroundSupportsMore(unittest.TestCase):
    """Slice 3. Walking a tile and surveying it are two different amounts of knowing.

    A party that walks past a forest learns it is a forest. A party big enough to stop and
    look learns where the nut trees stand, and only then can the clan put a proper crew on it.
    The yield one forager takes is a property of the ground and does not change; what changes
    is how many hands the clan knows how to use there.
    """

    def test_walked_ground_supports_only_a_token_crew(self):
        take = turn.forage_take(
            a_ledger(Terrain.FOREST, surveyed=False), foragers=4, season=AUTUMN
        )
        self.assertEqual(take.capacity, balance.WALKED_CAPACITY)
        self.assertEqual(take.idle, 4 - balance.WALKED_CAPACITY)

    def test_surveying_unlocks_the_terrain_capacity(self):
        walked = turn.forage_take(
            a_ledger(Terrain.FOREST, surveyed=False), foragers=4, season=AUTUMN
        )
        surveyed = turn.forage_take(a_ledger(Terrain.FOREST), foragers=4, season=AUTUMN)
        self.assertEqual(surveyed.capacity, balance.TERRAIN_CAPACITY[Terrain.FOREST])
        self.assertGreater(surveyed.food, walked.food)

    def test_a_forager_takes_the_same_from_ground_however_well_it_is_known(self):
        walked = turn.forage_take(
            a_ledger(Terrain.FOREST, surveyed=False), foragers=1, season=AUTUMN
        )
        surveyed = turn.forage_take(a_ledger(Terrain.FOREST), foragers=1, season=AUTUMN)
        self.assertEqual(walked.food, surveyed.food)

    def test_surveying_cannot_make_water_workable(self):
        # The `min` against the terrain table is what keeps this true with no special case.
        take = turn.forage_take(
            a_ledger(Terrain.WATER, surveyed=False), foragers=3, season=AUTUMN
        )
        self.assertEqual((take.capacity, take.food), (0, 0))

    def test_a_survey_of_marsh_buys_nothing(self):
        # Marsh supports one either way, which is why the scouts decline to survey it: the
        # engine only spends a survey where it raises the ceiling.
        walked = turn.forage_take(
            a_ledger(Terrain.MARSH, surveyed=False), foragers=3, season=AUTUMN
        )
        surveyed = turn.forage_take(a_ledger(Terrain.MARSH), foragers=3, season=AUTUMN)
        self.assertEqual(walked.capacity, surveyed.capacity)


class TestGroundWearsAndRecovers(unittest.TestCase):
    """Slice 5. The ground does not hold still, which is what lets a survey go out of date.

    Wear takes richness rather than room, and that is the whole reason the mechanic is felt.
    Measured, this clan is hands-limited: a tile losing a forager it never had the people to
    send costs nothing at all, and a clan that stopped scouting entirely ended a run half a
    person behind one that never stopped. Taking food off every hand standing on a tile lands
    the same season.
    """

    def test_a_worked_tile_gives_less_than_an_untouched_one(self):
        tile = Tile(terrain=Terrain.FOREST)
        fresh = turn.true_yield(tile)
        tile.wear = balance.WEAR_PER_TENTH_LOST * 3
        self.assertEqual(turn.true_yield(tile), fresh - 3)

    def test_ground_worked_to_death_still_grows_something(self):
        tile = Tile(terrain=Terrain.FOREST, wear=1_000)
        self.assertEqual(turn.true_yield(tile), balance.WORN_GROUND_FLOOR_TENTHS)

    def test_water_is_not_rescued_by_the_floor(self):
        self.assertEqual(turn.true_yield(Tile(terrain=Terrain.WATER)), 0)

    def test_a_tile_carries_all_but_its_last_hand_forever(self):
        # The allowance scales with the tile, and that is load-bearing rather than tidy: a flat
        # one-hand allowance is exactly what a clan that only walks ground puts on a tile, so
        # wear became a tax on surveying alone and slice 3's gradient flattened.
        world = a_world()
        sustainable = (
            balance.TERRAIN_CAPACITY[Terrain.FOREST] - balance.SUSTAINABLE_MARGIN
        )
        take = turn.ForageTake(
            food=0,
            capacity=0,
            idle=0,
            worked=(
                turn.Worked(
                    coord=(0, 0), terrain=Terrain.FOREST, hands=sustainable, food=0
                ),
            ),
        )
        for _ in range(10):
            turn._wear_ground(world, take)
        # Wear settles at a low, harmless number rather than at zero, and what matters is that
        # it never crosses the threshold where the ground starts giving less.
        self.assertEqual(
            turn.true_yield(world.tile((0, 0))), balance.TERRAIN_FORAGE[Terrain.FOREST]
        )

    def test_leaning_on_a_tile_costs_it(self):
        world = a_world()
        take = turn.ForageTake(
            food=0,
            capacity=0,
            idle=0,
            worked=(
                turn.Worked(
                    coord=(0, 0),
                    terrain=Terrain.FOREST,
                    hands=balance.TERRAIN_CAPACITY[Terrain.FOREST],
                    food=0,
                ),
            ),
        )
        for _ in range(10):
            turn._wear_ground(world, take)
        self.assertGreater(world.tile((0, 0)).wear, 0)

    def test_rested_ground_comes_back(self):
        world = a_world()
        world.tile((0, 0)).wear = 6
        turn._wear_ground(world, turn.ForageTake(food=0, capacity=0, idle=0, worked=()))
        self.assertLess(world.tile((0, 0)).wear, 6)


class TestTheGroundCanDisappoint(unittest.TestCase):
    """The clan plans on what it remembers and gets what is actually there.

    This is the gap slice 2 built the ledger for and slice 5 finally opens: `forage_take` is
    an expectation read off the ledger, `work_ground` is the season that actually happened.
    """

    def test_a_stale_survey_promises_more_than_the_ground_has(self):
        ledger = a_ledger(Terrain.FOREST)
        world = a_world(Terrain.FOREST)
        world.tile((0, 0)).wear = balance.WEAR_PER_TENTH_LOST * 5

        plan = turn.forage_take(ledger, foragers=3, season=AUTUMN)
        actual = turn.work_ground(world, plan, AUTUMN)
        self.assertLess(actual.food, plan.food)
        self.assertEqual(len(actual.short), 1)

    def test_a_fresh_survey_promises_exactly_what_arrives(self):
        world = a_world(Terrain.FOREST)
        ledger = Ledger(halflives=balance.FACT_HALFLIFE)
        ledger.reveal(world, (0, 0), turn=0)
        ledger.survey((0, 0), turn.true_yield(world.tile((0, 0))), turn=0)

        plan = turn.forage_take(ledger, foragers=3, season=AUTUMN)
        actual = turn.work_ground(world, plan, AUTUMN)
        self.assertEqual(actual.food, plan.food)
        self.assertEqual(actual.short, ())

    def test_walked_ground_is_assumed_untouched(self):
        # Optimism is the right default: unworked ground usually is untouched, and a
        # pessimistic guess would make walking pay less than it really does.
        ledger = a_ledger(Terrain.FOREST, surveyed=False)
        plan = turn.forage_take(ledger, foragers=1, season=AUTUMN)
        self.assertEqual(plan.food, per_forager(AUTUMN, Terrain.FOREST))


class TestTheBestGroundIsWorkedFirst(unittest.TestCase):
    def test_foragers_fill_the_richest_tile_before_the_poorest(self):
        # Forest out-yields marsh, so the first three hands belong in the forest whatever
        # order the tiles were learned in.
        take = turn.forage_take(
            a_ledger(Terrain.MARSH, Terrain.FOREST), foragers=3, season=AUTUMN
        )
        self.assertEqual([entry.terrain for entry in take.worked], [Terrain.FOREST])
        self.assertEqual(take.food, 3 * per_forager(AUTUMN, Terrain.FOREST))

    def test_overflow_spills_onto_the_next_best_ground(self):
        take = turn.forage_take(
            a_ledger(Terrain.MARSH, Terrain.FOREST), foragers=4, season=AUTUMN
        )
        self.assertEqual(
            [entry.terrain for entry in take.worked],
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
        ledger.survey((0, 0), balance.TERRAIN_FORAGE[Terrain.FOREST], turn=0)
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
        self.assertEqual(sum(entry.food for entry in take.worked), take.food)

    def test_worked_tiles_are_distinct(self):
        take = turn.forage_take(
            a_ledger(Terrain.FOREST, Terrain.FOREST, Terrain.PLAIN),
            foragers=8,
            season=AUTUMN,
        )
        coords = [entry.coord for entry in take.worked]
        self.assertEqual(len(coords), len(set(coords)))


class TestTheCachedCapacityNeverLies(unittest.TestCase):
    """`GameState.forage_capacity` is a cache, and a cache is a second source of truth.

    It exists only because `snapshot()` lives in `state.py`, computing capacity needs the
    per-terrain tables, and `balance` imports `state`, so `state` importing `balance` would
    close the import loop. That is a real constraint, but the cost is that the number can go
    stale, silently, and content keyed on `forage_capacity` would quietly stop matching.

    So it gets checked against a live count at every step of a real run rather than trusted.
    """

    def test_it_agrees_with_a_live_count_at_every_step_of_a_run(self):
        from hearthfall.engine.rng import Rng

        state = turn.new_game(seed=3)
        rng = Rng(3)
        while not state.is_over:
            live = turn.forage_take(
                state.ledger, foragers=0, season=state.season
            ).capacity
            self.assertEqual(
                state.forage_capacity,
                live,
                f"cache disagreed with a live count on turn {state.turn}",
            )
            self.assertEqual(state.snapshot()["forage_capacity"], live)
            # Scouting whenever the clan can spare two, so the ledger actually grows and the
            # cache is asked to move rather than sitting on its starting value all run.
            adults = state.population.adults
            scout = 2 if adults >= 3 else 0
            turn.resolve(state, Orders(forage=adults - scout, scout=scout), rng)
            if state.pending is not None:
                turn.apply_choice(state, 0)


if __name__ == "__main__":
    unittest.main()
