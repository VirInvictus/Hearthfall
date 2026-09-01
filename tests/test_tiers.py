import unittest

from hearthfall.engine.people import Ambition
from hearthfall.engine.rng import Rng
from hearthfall.engine.state import ChoiceOption, Effect
from hearthfall.engine.tiers import Tier, get_endorsements
from hearthfall.engine.turn import new_game


class TestTiers(unittest.TestCase):
    def test_ring_emerges_when_tally_set(self):
        state = new_game(0)
        rng = Rng(0)

        self.assertEqual(state.tier, Tier.CLAN)

        # Manually force the conditions
        state.tallies["ring_formed"] = 1

        from hearthfall.engine.turn import TurnReport, _advance

        report = TurnReport(turn=1, season=state.season)
        _advance(state, rng, report)

        self.assertEqual(state.tier, Tier.RING)
        assert state.council is not None
        self.assertGreater(len(state.council.advisors), 0)
        self.assertEqual(len(state.cast), len(state.council.advisors))

    def test_get_endorsements(self):
        state = new_game(0)
        rng = Rng(0)
        state.tallies["ring_formed"] = 1

        from hearthfall.engine.turn import TurnReport, _advance

        _advance(state, rng, TurnReport(turn=1, season=state.season))

        assert state.council is not None
        # Force the first advisor to be cautious
        advisor_id = state.council.advisors[0]
        state.cast[advisor_id].ambition = Ambition.CAUTIOUS

        options = (
            ChoiceOption("Safe", Effect(food=10)),
            ChoiceOption("Risky", Effect(food=-5, morale=10)),
        )

        endorsements = get_endorsements(state, options)
        # Cautious should pick the first option (index 0)
        self.assertIn(state.cast[advisor_id].name, endorsements[0])
        self.assertNotIn(state.cast[advisor_id].name, endorsements[1])
