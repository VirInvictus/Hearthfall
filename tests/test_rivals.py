"""SP 8 slice 1: rivals. The hearth that walks out is a band with a name.

The promise is old (SP 2 slice 4 measured that driving a hearth off is
unpunished and named the fix) and the punishment is not a new mechanic: the
rival is an ordinary band that remembers. If these fail, walkouts are a door
closing instead of a door opening, and the strategy the roadmap said should
be punished still pays.
"""

from __future__ import annotations

import unittest

from hearthfall.engine import balance
from hearthfall.engine.agents import IntentKind
from hearthfall.engine.orders import Orders
from hearthfall.engine.rng import Rng
from hearthfall.engine.turn import new_game
from hearthfall.engine.turn import resolve as turn_resolve
from hearthfall.engine.world import Terrain


def _state_on_the_edge_of_leaving():
    """A clan with one hearth at the door and a store worth taking."""
    state = new_game(seed=42)
    household = state.population.households[0]
    household.resentment = balance.WALKS_OUT_AT
    state.stores.food = 40
    return state, household


class TestTheWalkoutRaisesARival(unittest.TestCase):
    def test_the_leaving_hearth_becomes_an_agent(self):
        state, household = _state_on_the_edge_of_leaving()
        people_before = state.population.total
        turn_resolve(state, Orders(forage=6), Rng(7))

        # The hearth is gone from the clan...
        self.assertNotIn(household, state.population.households)
        self.assertLess(state.population.total, people_before)
        # ...and present on the map, under the name its trait gives it.
        rivals = [a for a in state.agents.values() if a.id.startswith("rival_")]
        self.assertEqual(len(rivals), 1)
        rival = rivals[0]
        self.assertEqual(rival.name, "Hearthkin Clan")

    def test_the_rival_carries_what_it_walked_out_with(self):
        state, household = _state_on_the_edge_of_leaving()
        report = turn_resolve(state, Orders(forage=6), Rng(7))
        rival = next(a for a in state.agents.values() if a.id.startswith("rival_"))
        # One hearth leaving takes the whole walkout share, and holds it. The
        # store the share came out of is the one the season's economy left,
        # which the test reads from the report rather than recomputing.
        self.assertEqual(rival.food, report.food_taken)
        self.assertEqual(rival.mood, household.mood)

    def test_the_camp_is_the_engines_call_and_never_water_or_home(self):
        state, _household = _state_on_the_edge_of_leaving()
        turn_resolve(state, Orders(forage=6), Rng(7))
        rival = next(a for a in state.agents.values() if a.id.startswith("rival_"))
        self.assertIsNotNone(rival.location)
        assert rival.location is not None
        self.assertNotEqual(rival.location, state.world.home)
        tile = state.world.tile(rival.location)
        self.assertIsNot(tile.terrain, Terrain.WATER)

    def test_the_chronicle_says_what_happened(self):
        state, _household = _state_on_the_edge_of_leaving()
        report = turn_resolve(state, Orders(forage=6), Rng(7))
        log = "\n".join(report.log)
        self.assertIn("raising a fire of their own", log)
        self.assertIn("Hearthkin Clan", log)

    def test_the_creation_is_deterministic(self):
        def once() -> tuple[str, tuple[int, int] | None, int, int]:
            state, _ = _state_on_the_edge_of_leaving()
            turn_resolve(state, Orders(forage=6), Rng(7))
            rival = next(a for a in state.agents.values() if a.id.startswith("rival_"))
            return rival.name, rival.location, rival.food, rival.mood

        self.assertEqual(once(), once())


class TestTheRivalRemembers(unittest.TestCase):
    """The punishment is the ordinary band arc: the rival starves, musters,
    massing is announced, and the blow is priced by everything shipped."""

    def test_the_rival_comes_back_in_arms(self):
        state, _household = _state_on_the_edge_of_leaving()
        state.stores.food = 600
        turn_resolve(state, Orders(forage=6), Rng(7))
        rival = next(a for a in state.agents.values() if a.id.startswith("rival_"))
        # Lean and furious: the very next season finds it at the floor, and
        # the floor is where intents form. Orders stay within the smaller
        # clan the walkout left behind.
        rival.food = 0
        rival.mood = 1

        logs = []
        while not state.is_over and not logs:
            adults = state.population.adults
            report = turn_resolve(state, Orders(forage=adults), Rng(7))
            joined = "\n".join(report.log)
            if "massing on the border" in joined:
                logs.append(joined)
        self.assertTrue(logs, "the rival never massed; the punishment is dead")
        self.assertIn("The read says", logs[0])
        assert rival.intent is not None
        self.assertEqual(rival.intent.kind, IntentKind.RAID)


if __name__ == "__main__":
    unittest.main()
