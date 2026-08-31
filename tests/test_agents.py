import unittest
from hearthfall.engine.agents import Agent, AgentType, IntentKind
from hearthfall.engine.rng import Rng

class TestAgents(unittest.TestCase):
    def test_starving_agent_forms_raid_intent(self):
        agent = Agent(id="test", name="Test Clan", type=AgentType.NEIGHBOUR, food=0, mood=1)
        rng = Rng(0)
        
        # Season 1: Starts at 0. Forages 9, consumes 10. Reaches -1. Mood drops to 0. Intent forms.
        agent.grow(rng)
        self.assertEqual(agent.food, 0)
        self.assertEqual(agent.mood, 0)
        assert agent.intent is not None
        self.assertEqual(agent.intent.kind, IntentKind.RAID)
