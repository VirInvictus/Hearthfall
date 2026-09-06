import unittest

from hearthfall.engine import balance
from hearthfall.engine.agents import Agent, AgentType, IntentKind
from hearthfall.engine.rng import Rng
from hearthfall.engine.turn import new_game


class TestAgents(unittest.TestCase):
    def test_starving_agent_forms_raid_intent(self):
        agent = Agent(
            id="test", name="Test Clan", type=AgentType.NEIGHBOUR, food=0, mood=1
        )
        rng = Rng(0)

        # Season 1: starts empty. Whatever the band economy is, gathering less
        # than it eats keeps the store at the floor and the mood falls with it.
        # Intent forms the season mood hits zero.
        agent.grow(
            rng,
            forage=balance.BAND_FORAGE,
            consumption=balance.BAND_CONSUMPTION,
        )
        self.assertEqual(agent.food, 0)
        self.assertEqual(agent.mood, 0)
        assert agent.intent is not None
        self.assertEqual(agent.intent.kind, IntentKind.RAID)


class TestBandPlacement(unittest.TestCase):
    def test_a_run_places_bands_within_the_declared_range(self):
        # The count is the loudest lever in the raid economy and its raise
        # was measured and refused (roadmap, SP 6): this pins the wiring so
        # the next attempt really is one constant.
        low, high = balance.BAND_COUNT_RANGE
        for seed in range(15):
            with self.subTest(seed=seed):
                state = new_game(seed)
                self.assertTrue(low <= len(state.agents) <= high)


if __name__ == "__main__":
    unittest.main()
