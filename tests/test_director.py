import unittest

from hearthfall.engine.agents import Intent, IntentKind
from hearthfall.engine.director import Director
from hearthfall.engine.rng import Rng
from hearthfall.engine.turn import new_game


class TestDirector(unittest.TestCase):
    def test_director_surfaces_raid(self):
        state = new_game(0)
        rng = Rng(0)

        # Override an agent to have a raid intent
        agent_id = next(iter(state.agents.keys()))
        agent = state.agents[agent_id]
        agent.intent = Intent(kind=IntentKind.RAID, target_turn=0)

        director = Director()

        # In a high slack situation, it surfaces
        interrupt = director.evaluate(state, rng)

        assert interrupt is not None
        self.assertEqual(interrupt.cause, f"raid_{agent.id}")
        self.assertIsNone(agent.intent, "Director clears intent after surfacing it")

    def test_director_never_invents_threats(self):
        state = new_game(0)
        rng = Rng(0)

        # Ensure no intents
        for agent in state.agents.values():
            agent.intent = None

        director = Director()
        interrupt = director.evaluate(state, rng)

        self.assertIsNone(
            interrupt,
            "Honesty guarantee: Director cannot invent an interrupt without an intent",
        )
