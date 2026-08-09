"""Households, and the decision that makes them bite.

`spec.md` §5: a household is what starves, what resents, what marries, and what feuds. The
arithmetic here is what turns a famine from a number into somebody, and the rationing choice is
what makes the player responsible for which somebody.

Two things are worth guarding hardest. First, no policy may waste food, because a policy that
quietly fed fewer mouths off the same store would be strictly worse and the choice would
collapse into a right answer. Second, being wronged is not the same as being hungry: everyone
going equally short must breed no resentment at all, or EQUAL stops being a real option.
"""

from __future__ import annotations

import unittest

from hearthfall.engine import balance, turn
from hearthfall.engine.people import Household, Rationing, share_out
from hearthfall.engine.rng import Rng
from hearthfall.engine.state import Effect, Orders, Population, Season

PER_ADULT, PER_CHILD = 2, 1


def hh(adults: int, children: int = 0, mood: int = 5) -> Household:
    return Household(adults=adults, children=[4] * children, mood=mood)


class TestSharingOut(unittest.TestCase):
    def test_a_full_store_feeds_everyone_whatever_the_policy(self):
        households = [hh(2), hh(1, 2), hh(3)]
        demand = sum(h.demand(PER_ADULT, PER_CHILD) for h in households)
        for policy in Rationing:
            with self.subTest(policy=policy):
                shares = share_out(households, demand, policy, PER_ADULT, PER_CHILD)
                self.assertEqual(
                    shares, [h.demand(PER_ADULT, PER_CHILD) for h in households]
                )

    def test_no_policy_wastes_food(self):
        # The invariant that keeps the choice a choice. If one policy left food undealt it
        # would kill more people off the same store and nobody would ever pick it.
        households = [hh(2), hh(1, 2), hh(3)]
        demand = sum(h.demand(PER_ADULT, PER_CHILD) for h in households)
        for policy in Rationing:
            for food in range(20):
                with self.subTest(policy=policy, food=food):
                    shares = share_out(households, food, policy, PER_ADULT, PER_CHILD)
                    # Everything available is dealt, up to the point where nobody is hungry.
                    # Surplus stays in the store rather than being handed out and lost.
                    self.assertEqual(sum(shares), min(food, demand))

    def test_nobody_is_handed_more_than_they_can_eat(self):
        households = [hh(1), hh(1)]
        shares = share_out(households, 100, Rationing.WORKERS, PER_ADULT, PER_CHILD)
        self.assertEqual(shares, [2, 2])

    def test_equal_spreads_the_shortfall_rather_than_concentrating_it(self):
        households = [hh(2), hh(2), hh(2)]
        shares = share_out(households, 6, Rationing.EQUAL, PER_ADULT, PER_CHILD)
        self.assertEqual(shares, [2, 2, 2])

    def test_workers_feeds_the_household_with_the_most_hands_first(self):
        households = [hh(1, 3), hh(4)]
        shares = share_out(households, 8, Rationing.WORKERS, PER_ADULT, PER_CHILD)
        self.assertEqual(shares, [0, 8], "the four-adult household should eat first")

    def test_children_feeds_the_household_with_the_most_young_first(self):
        households = [hh(1, 3), hh(4)]
        shares = share_out(households, 5, Rationing.CHILDREN, PER_ADULT, PER_CHILD)
        self.assertEqual(
            shares, [5, 0], "the household full of children should eat first"
        )

    def test_an_empty_clan_divides_nothing(self):
        self.assertEqual(share_out([], 10, Rationing.EQUAL, PER_ADULT, PER_CHILD), [])


class TestTheFamineLandsOnSomebody(unittest.TestCase):
    def a_clan(self, food: int, rationing: Rationing):
        state = turn.new_game(1)
        state.stores.food = food
        turn.resolve(state, Orders(rationing=rationing), Rng(1))
        return state

    def test_an_even_split_wrongs_nobody(self):
        # Everyone hungry together is a hardship. Watching another hearth eat is a grievance.
        state = self.a_clan(food=4, rationing=Rationing.EQUAL)
        self.assertEqual(
            sum(h.resentment for h in state.population.households),
            0,
            "an even split produced resentment; EQUAL has stopped being a real option",
        )

    def test_favouring_the_workers_creates_a_household_that_remembers(self):
        state = self.a_clan(food=4, rationing=Rationing.WORKERS)
        self.assertGreater(
            sum(h.resentment for h in state.population.households),
            0,
            "somebody was fed last and nobody minded",
        )

    def test_the_report_says_who_went_without(self):
        state = turn.new_game(1)
        state.stores.food = 4
        report = turn.resolve(state, Orders(rationing=Rationing.WORKERS), Rng(1))
        self.assertGreater(report.households_wronged, 0)
        self.assertTrue(any("went without" in line for line in report.log), report.log)

    def test_a_plentiful_store_makes_the_policy_irrelevant(self):
        # Rationing is a decision about scarcity. With enough to go round it must not be a
        # lever at all, or the player is being asked a question with no stakes every season.
        outcomes = set()
        for policy in Rationing:
            state = turn.new_game(1)
            state.stores.food = 500
            turn.resolve(state, Orders(rationing=policy), Rng(1))
            outcomes.add(
                (
                    state.population.total,
                    sum(h.resentment for h in state.population.households),
                )
            )
        self.assertEqual(len(outcomes), 1, "policy mattered when nobody was short")


class TestThePoolIsDerivedFromTheHouseholds(unittest.TestCase):
    """One source of truth. The aggregates must never be able to disagree with the kin groups."""

    def test_totals_are_the_sum_of_the_households(self):
        population = Population(households=[hh(2, 1), hh(3), hh(0, 2)])
        self.assertEqual(population.adults, 5)
        self.assertEqual(population.child_count, 3)
        self.assertEqual(population.total, 8)

    def test_morale_is_the_average_of_the_living(self):
        population = Population(households=[hh(1, mood=2), hh(1, mood=8)])
        self.assertEqual(population.morale, 5)

    def test_an_emptied_household_stops_counting_toward_morale(self):
        population = Population(households=[hh(1, mood=8), hh(0, mood=0)])
        self.assertEqual(population.morale, 8)
        self.assertEqual(population.living_households, 1)

    def test_worst_mood_finds_the_household_the_average_hides(self):
        # The whole reason the household layer exists: two clans averaging five are not the
        # same clan if one of them has a hearth at zero.
        even = Population(households=[hh(1, mood=5), hh(1, mood=5)])
        lopsided = Population(households=[hh(1, mood=10), hh(1, mood=0)])
        self.assertEqual(even.morale, lopsided.morale)
        self.assertNotEqual(even.worst_mood, lopsided.worst_mood)

    def test_losing_people_takes_children_before_adults(self):
        population = Population(households=[hh(2, 2)])
        population.take_people(2)
        self.assertEqual((population.adults, population.child_count), (2, 0))

    def test_losing_people_cannot_take_more_than_exist(self):
        population = Population(households=[hh(1)])
        self.assertEqual(population.take_people(5), 1)
        self.assertEqual(population.total, 0)

    def test_a_death_lands_on_the_household_that_is_worst_off(self):
        population = Population(households=[hh(2, mood=9), hh(2, mood=1)])
        population.take_people(1)
        self.assertEqual(population.households[0].adults, 2)
        self.assertEqual(population.households[1].adults, 1)


class TestTheForecastKnowsAboutRationing(unittest.TestCase):
    def test_the_projected_deaths_follow_the_policy(self):
        # The forecast exists to show the consequence of a decision before it is made. If it
        # averaged the rationing away it would be silent about the one thing being chosen.
        state = turn.new_game(1)
        state.stores.food = 4
        projected = {
            policy: turn.forecast(state, Orders(rationing=policy)).would_starve
            for policy in Rationing
        }
        self.assertGreater(
            len(set(projected.values())),
            1,
            f"every policy forecast the same: {projected}",
        )

    def test_the_forecast_still_matches_resolution_for_every_policy(self):
        for policy in Rationing:
            for food in (0, 3, 9, 40):
                with self.subTest(policy=policy, food=food):
                    orders = Orders(rationing=policy)
                    a, b = turn.new_game(1), turn.new_game(1)
                    a.stores.food = b.stores.food = food
                    projected = turn.forecast(a, orders)
                    report = turn.resolve(b, orders, Rng(1))
                    self.assertEqual(projected.would_starve, report.starved)
                    self.assertEqual(projected.eaten, report.consumed)


class TestContentCanSeeTheHouseholds(unittest.TestCase):
    def test_the_aggregate_keys_are_in_the_snapshot(self):
        snapshot = turn.new_game(1).snapshot()
        for key in ("households", "worst_household_mood", "households_resentful"):
            self.assertIn(key, snapshot)

    def test_resentful_households_are_counted_once_they_pass_the_line(self):
        state = turn.new_game(1)
        self.assertEqual(state.snapshot()["households_resentful"], 0)
        state.population.households[0].resentment = balance.RESENTFUL_AT
        self.assertEqual(state.snapshot()["households_resentful"], 1)

    def test_morale_still_answers_for_the_thirty_events_that_read_it(self):
        # The compatibility guarantee. Households arrived without touching the corpus.
        state = turn.new_game(1)
        self.assertEqual(state.snapshot()["morale"], balance.STARTING_MORALE)
        turn.apply_effect(state, Effect(morale=-2))
        self.assertEqual(state.snapshot()["morale"], balance.STARTING_MORALE - 2)


class TestTheFoundingClan(unittest.TestCase):
    def test_the_clan_starts_split_into_kin_groups(self):
        population = turn.new_game(1).population
        self.assertEqual(len(population.households), balance.STARTING_HOUSEHOLDS)
        self.assertEqual(population.adults, balance.STARTING_ADULTS)
        self.assertEqual(population.child_count, balance.STARTING_CHILDREN)

    def test_the_split_does_not_depend_on_the_seed(self):
        # Who is in which household at turn zero is not something a run should differ on.
        shapes = {
            tuple(
                (h.adults, h.child_count)
                for h in turn.new_game(s).population.households
            )
            for s in range(5)
        }
        self.assertEqual(len(shapes), 1)


class TestWinterStillCostsEveryone(unittest.TestCase):
    def test_the_winter_ration_is_larger(self):
        self.assertGreater(turn.rations(Season.WINTER), turn.rations(Season.SPRING))


if __name__ == "__main__":
    unittest.main()
