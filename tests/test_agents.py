import unittest

from hearthfall.engine.agents import Agent, AgentType, IntentKind
from hearthfall.engine.rng import Rng


class TestAgents(unittest.TestCase):
    def test_starving_agent_forms_raid_intent(self):
        agent = Agent(
            id="test", name="Test Clan", type=AgentType.NEIGHBOUR, food=0, mood=1
        )
        rng = Rng(0)

        # Season 1: starts empty. Whatever the band economy is, gathering less
        # than it eats keeps the store at the floor and the mood falls with it.
        # Intent forms the season mood hits zero.
        from hearthfall.engine import balance

        agent.grow(
            rng,
            forage=balance.BAND_FORAGE,
            consumption=balance.BAND_CONSUMPTION,
        )
        self.assertEqual(agent.food, 0)
        self.assertEqual(agent.mood, 0)
        assert agent.intent is not None
        self.assertEqual(agent.intent.kind, IntentKind.RAID)
