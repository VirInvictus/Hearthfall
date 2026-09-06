"""SP 8 slice 3: the works. Surplus hands become permanent, modest things.

The brief's invariants, as tests: a work order is a labour line like any
other (hands against the same adults), what gets raised is the engine's
call, each work is spent once and modest forever, and the forecast cannot
drift from the rules the smokehouse touches.
"""

from __future__ import annotations

import unittest

from hearthfall.engine import balance
from hearthfall.engine.agents import Intent, IntentKind
from hearthfall.engine.orders import Orders
from hearthfall.engine.rng import Rng
from hearthfall.engine.state import Season
from hearthfall.engine.turn import forecast, new_game
from hearthfall.engine.turn import resolve as turn_resolve


def _run_seasons(orders_count: int, seasons: int, seed: int = 42):
    """A quiet clan (no events) with `orders_count` hands on the works, and
    a store deep enough that the test is about the works, not about bread."""
    state = new_game(seed)
    state.stores.food = 400
    logs: list[str] = []
    for _ in range(seasons):
        adults = state.population.adults
        report = turn_resolve(
            state, Orders(forage=adults - orders_count, work=orders_count), Rng(7)
        )
        logs.append("\n".join(report.log))
    return state, logs


class TestRaisingTheWorks(unittest.TestCase):
    def test_hands_raise_the_ladder_in_order(self):
        # Two hands put six hand-seasons in over three seasons: the
        # palisade closes, and the note is the chronicle's business.
        state, logs = _run_seasons(2, 3)
        self.assertEqual(state.improvements.get("palisade"), 1)
        self.assertTrue(
            any("The palisade is closed" in log for log in logs),
            "a finished work went unannounced",
        )

    def test_progress_left_over_from_the_last_work_does_not_carry(self):
        state, _logs = _run_seasons(2, 3)
        self.assertEqual(state.work_progress, 0)
        # And the next work starts from nothing: four more seasons raises
        # the smokehouse with two hands, not sooner.
        for _ in range(2):
            adults = state.population.adults
            turn_resolve(state, Orders(forage=adults - 2, work=2), Rng(7))
        self.assertNotIn("smokehouse", state.improvements)
        for _ in range(1):
            adults = state.population.adults
            turn_resolve(state, Orders(forage=adults - 2, work=2), Rng(7))
        self.assertEqual(state.improvements.get("smokehouse"), 1)

    def test_work_hands_compete_for_the_same_adults(self):
        state = new_game(seed=42)
        over = Orders(forage=4, work=3)
        with self.assertRaises(ValueError):
            turn_resolve(state, over, Rng(7))

    def test_a_finished_ladder_says_so(self):
        state = new_game(seed=42)
        state.improvements = {"palisade": 1, "smokehouse": 1, "shrine": 1}
        report = turn_resolve(state, Orders(forage=4, work=2), Rng(7))
        self.assertIn("nothing left to raise", "\n".join(report.log))


class TestWhatTheWorksAreWorth(unittest.TestCase):
    def test_the_palisade_keeps_grain_when_a_raid_lands(self):
        from hearthfall.engine.turn import resolve as turn_resolve

        def run(palisade: bool):
            state = new_game(seed=42)
            if palisade:
                state.improvements["palisade"] = 1
            band = state.agents[next(iter(state.agents))]
            band.intent = Intent(kind=IntentKind.RAID, target_turn=state.turn)
            band.mood = 0
            state.stores.food = 60
            turn_resolve(state, Orders(forage=6, militia=0), Rng(7))
            return state.stores.food

        walled, open_store = run(True), run(False)
        # Same seed, same season, same band: the walled granary kept exactly
        # the guard more, and the wall never turns the raid into a profit.
        self.assertEqual(walled - open_store, balance.PALISADE_GRANARY_GUARD)
        self.assertGreater(walled, 0)

    def test_the_smokehouse_trims_spoilage(self):
        from hearthfall.engine.turn import _spoil_rate

        state = new_game(seed=42)
        orders = Orders(forage=6)
        plain = _spoil_rate(state, orders, Season.SUMMER)
        state.improvements["smokehouse"] = 1
        trimmed = _spoil_rate(state, orders, Season.SUMMER)
        self.assertLess(trimmed, plain)
        self.assertEqual(
            trimmed,
            max(
                balance.SPOIL_RATE_FLOOR,
                balance.SPOIL_RATE[Season.SUMMER] - balance.SMOKEHOUSE_SPOIL_TRIM,
            ),
        )

    def test_the_smokehouse_keeps_food_in_a_real_season(self):
        def run(with_smokehouse: bool) -> int:
            state = new_game(seed=42)
            if with_smokehouse:
                state.improvements["smokehouse"] = 1
            state.stores.food = 100
            turn_resolve(state, Orders(forage=6), Rng(7))
            return state.stores.food

        self.assertGreater(run(True), run(False))

    def test_the_shrine_steadies_the_drift(self):

        state = new_game(seed=42)
        state.improvements["shrine"] = 1
        state.stores.food = 600
        for household in state.population.households:
            household.mood = 3
        for _ in range(4):
            turn_resolve(state, Orders(forage=6), Rng(7))
        # Drift pulls toward the shrine's target, past the plain middle.
        self.assertEqual(state.population.morale, balance.SHRINE_DRIFT_TARGET)


class TestTheForecastStaysHonest(unittest.TestCase):
    def test_the_forecast_agrees_with_a_smokehouse_clan(self):
        state = new_game(seed=42)
        state.improvements["smokehouse"] = 1
        state.stores.food = 80
        orders = Orders(forage=5, tend=1)
        projection = forecast(state, orders)
        report = turn_resolve(state, orders, Rng(7))
        # The season's economy is otherwise deterministic: produced and
        # eaten match, so closing food matches iff the spoil rate matches.
        self.assertEqual(projection.produced, report.produced)
        self.assertEqual(projection.eaten, report.consumed)
        self.assertEqual(projection.closing_food, state.stores.food)


if __name__ == "__main__":
    unittest.main()
