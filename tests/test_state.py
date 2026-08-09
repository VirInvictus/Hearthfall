"""State shape, and the snapshot the content layer reads.

`snapshot()` is the only seam between the simulation and the event corpus. If a key
disappears from it, every event condition naming that key silently stops matching, so the
key set is pinned here on purpose.
"""

from __future__ import annotations

import unittest

from support import an_int

from hearthfall.engine import turn
from hearthfall.engine.state import Orders, Population, Season

SNAPSHOT_KEYS = {
    "turn",
    "year",
    "season",
    "adults",
    "children",
    "people",
    "food",
    "morale",
    "tiles_known",
    "tiles_unknown",
    "forage_capacity",
    "hands_without_ground",
    "households",
    "worst_household_mood",
    "households_resentful",
    "terrain_home",
    "terrain_revealed",
}


class TestSnapshot(unittest.TestCase):
    def test_the_key_set_is_exactly_what_content_may_test(self):
        # Two halves, pinned separately. The simulation's own keys are a fixed contract and
        # are listed above; the `tally_` keys are declared by content in `data/tallies.toml`
        # and would make this list a second place to maintain the registry. What must hold is
        # that nothing else sneaks in, because an unlisted key is one no event author knows
        # exists and one no test is defending.
        keys = set(turn.new_game(1).snapshot())
        self.assertEqual({k for k in keys if not k.startswith("tally_")}, SNAPSHOT_KEYS)

    def test_every_declared_tally_is_present_from_the_first_turn(self):
        # If a tally only appeared once written, a condition naming it would fail to load
        # until some other event had already fired, which is a load order dependency nobody
        # would ever debug. They all start at zero and they are all always there.
        from hearthfall.engine.events.loader import load_tallies

        snapshot = turn.new_game(1).snapshot()
        for name in load_tallies():
            self.assertEqual(
                snapshot[f"tally_{name}"], 0, f"tally_{name} missing or set"
            )

    def test_values_are_primitives_the_evaluator_can_compare(self):
        for key, value in turn.new_game(1).snapshot().items():
            self.assertIsInstance(value, (int, str), f"{key} is not comparable")

    def test_people_is_adults_plus_children(self):
        snapshot = turn.new_game(1).snapshot()
        self.assertEqual(
            snapshot["people"],
            an_int(snapshot["adults"]) + an_int(snapshot["children"]),
        )

    def test_tile_counts_cover_the_whole_map(self):
        state = turn.new_game(1)
        snapshot = state.snapshot()
        self.assertEqual(
            an_int(snapshot["tiles_known"]) + an_int(snapshot["tiles_unknown"]),
            len(state.world.tiles),
        )

    def test_the_snapshot_tracks_the_state(self):
        state = turn.new_game(1)
        before = state.snapshot()
        state.stores.food += 7
        self.assertEqual(state.snapshot()["food"], an_int(before["food"]) + 7)


class TestTheCalendar(unittest.TestCase):
    def test_seasons_cycle_in_order(self):
        state = turn.new_game(1)
        seen = []
        for offset in range(8):
            state.turn = offset
            seen.append(state.season)
        self.assertEqual(
            seen,
            [
                Season.SPRING,
                Season.SUMMER,
                Season.AUTUMN,
                Season.WINTER,
                Season.SPRING,
                Season.SUMMER,
                Season.AUTUMN,
                Season.WINTER,
            ],
        )

    def test_the_year_advances_every_fourth_turn(self):
        state = turn.new_game(1)
        for offset, expected in [(0, 1), (3, 1), (4, 2), (7, 2), (8, 3)]:
            state.turn = offset
            self.assertEqual(state.year, expected)


class TestPopulation(unittest.TestCase):
    def test_totals(self):
        population = Population.of(4, [1, 2, 3])
        self.assertEqual(population.child_count, 3)
        self.assertEqual(population.total, 7)


class TestOrders(unittest.TestCase):
    def test_assigned_counts_every_job(self):
        self.assertEqual(Orders(forage=2, explore=1, tend=3).assigned, 6)

    def test_an_exact_allocation_is_legal(self):
        Orders(forage=2, explore=1, tend=3).validate(adults=6)

    def test_leaving_hands_idle_is_legal(self):
        Orders(forage=1).validate(adults=6)


if __name__ == "__main__":
    unittest.main()
