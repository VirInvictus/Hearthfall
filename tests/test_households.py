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
from hearthfall.engine.people import Household, Rationing, first_claim, share_out
from hearthfall.engine.rng import Rng
from hearthfall.engine.state import Effect, Orders, Population, Season

PER_ADULT, PER_CHILD = 2, 1


_test_hh_id = 1
def hh(adults: int, children: int = 0, mood: int = 5) -> Household:
    global _test_hh_id
    id_ = _test_hh_id
    _test_hh_id += 1
    return Household(id=id_, adults=adults, children=[4] * children, mood=mood)


def a_state(*, food: int, households: list[tuple[int, int]]):
    """A real run, dealt into the hearths a test wants to watch."""
    state = turn.new_game(1)
    state.stores.food = food
    state.population.households = [
        hh(adults, children) for adults, children in households
    ]
    return state


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

    def test_the_three_policies_are_three_different_functions(self):
        # A regression guard for a real bug. The founding clan starts with the same number of
        # adults in every household, so WORKERS ordered by `-adults` tied everywhere and fell
        # back to index order, which is exactly what CHILDREN produced. Measured over 150
        # seeds the two were indistinguishable, and they were indistinguishable because they
        # were the same function wearing two names. Each now carries a dependent-count
        # tiebreak, so "feed the workers" means where food buys the most labour.
        households = [hh(2, 1), hh(2, 1), hh(2)]
        shares = {
            policy: tuple(share_out(households, 7, policy, PER_ADULT, PER_CHILD))
            for policy in Rationing
        }
        self.assertEqual(
            len(set(shares.values())),
            len(Rationing),
            f"two policies divide a short store identically: {shares}",
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

    def test_the_hearths_do_not_bear_in_lockstep(self):
        # Found level, all three reached the bond target on the same season and the chronicle
        # read "3 children were born to the clan", which is a batch job rather than three
        # things that happened. Staggering the founding bond spreads them across seasons.
        bonds = {h.bond for h in turn.new_game(1).population.households}
        self.assertGreater(len(bonds), 1, "every hearth starts on the same schedule")

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


class TestResentmentHasTeeth(unittest.TestCase):
    """Slice 4. A grudge that only ever sat in a condition key now does three things.

    It accrues where it could not before (burying somebody while another fire ate), it changes
    how food is divided, and past the last rung the hearth stops being part of this clan.
    """

    def test_burying_someone_while_another_fire_eats_is_its_own_grievance(self):
        # Eight food against twelve of demand: enough for the two hearths of hands and nothing
        # for the third. An empty store would wrong nobody, because nobody ate.
        state = a_state(food=8, households=[(2, 0), (2, 0), (1, 2)])
        turn.resolve(state, Orders(rationing=Rationing.WORKERS), Rng(1))
        passed_over = state.population.households[-1]
        self.assertGreater(
            passed_over.resentment,
            balance.RESENTMENT_PER_SHORT_SHARE,
            "a hearth that buried somebody while another ate resents it no more than one "
            "that merely went short; the accrual slice 4 exists for is missing",
        )

    def test_an_even_split_still_wrongs_nobody(self):
        # The invariant the accrual is charged against. A first attempt added resentment on any
        # death, which quietly made EQUAL breed grudges and stopped it being a real option.
        state = a_state(food=8, households=[(2, 0), (2, 0), (1, 2)])
        turn.resolve(state, Orders(rationing=Rationing.EQUAL), Rng(1))
        self.assertEqual(
            [h.resentment for h in state.population.households],
            [0, 0, 0],
            "an even split produced resentment even though nobody was passed over",
        )

    def test_a_hearth_past_the_line_takes_its_share_first(self):
        angry = Household(id=1, adults=2, mood=5, resentment=balance.HOARDS_AT)
        patient = Household(id=2, adults=2, mood=5)
        claims = first_claim(
            [patient, angry],
            food=4,
            hoards_at=balance.HOARDS_AT,
            per_adult=2,
            per_child=1,
        )
        self.assertEqual(claims, [0, 4], "the angry hearth did not take first")

    def test_the_angriest_takes_first_when_two_have_stopped_waiting(self):
        angrier = Household(id=1, adults=1, mood=5, resentment=balance.HOARDS_AT + 3)
        angry = Household(id=2, adults=1, mood=5, resentment=balance.HOARDS_AT)
        claims = first_claim(
            [angry, angrier],
            food=2,
            hoards_at=balance.HOARDS_AT,
            per_adult=2,
            per_child=1,
        )
        self.assertEqual(claims, [0, 2])

    def test_a_patient_hearth_divides_only_what_is_left(self):
        state = a_state(food=6, households=[(2, 0), (2, 0)])
        state.population.households[0].resentment = balance.HOARDS_AT
        report = turn.resolve(state, Orders(), Rng(1))
        # Four food to the hearth that took first, two left for the other, which needed four.
        self.assertEqual(report.households_hoarding, 1)
        self.assertGreater(report.starved, 0)

    def test_a_hearth_that_has_had_enough_walks_out(self):
        state = a_state(food=100, households=[(2, 0), (2, 0)])
        state.population.households[0].resentment = balance.WALKS_OUT_AT
        report = turn.resolve(state, Orders(), Rng(1))
        self.assertEqual(report.households_left, 1)
        self.assertEqual(report.people_left, 2)
        self.assertGreater(
            report.food_taken, 0, "they left without their share of the store"
        )
        self.assertEqual(state.population.living_households, 1)
        self.assertEqual(state.hearths_walked_out, 1)

    def test_the_grudge_has_to_be_a_season_old_before_they_go(self):
        """The player gets one season to answer it, which is what makes it a decision.

        A hearth that crosses the line and leaves inside the same tick is a mechanic the player
        only ever learns about from its own aftermath.
        """
        state = a_state(food=8, households=[(2, 0), (2, 0), (1, 2)])
        for _ in range(3):
            if state.is_over:
                break
            report = turn.resolve(state, Orders(rationing=Rationing.WORKERS), Rng(1))
            worst = state.population.worst_resentment
            if worst >= balance.WALKS_OUT_AT:
                self.assertEqual(
                    report.households_left,
                    0,
                    "a hearth crossed the line and left in the same season",
                )
                break

    def test_an_event_can_mend_the_longest_grudge(self):
        state = a_state(food=50, households=[(2, 0), (2, 0)])
        state.population.households[1].resentment = 5
        turn.apply_effect(state, Effect(household=(("mood", 1), ("resentment", -3))))
        self.assertEqual(state.population.households[1].resentment, 2)
        self.assertEqual(
            state.population.households[0].resentment, 0, "it hit the wrong hearth"
        )

    def test_mending_cannot_drive_a_grudge_below_nothing(self):
        state = a_state(food=50, households=[(2, 0)])
        turn.apply_effect(state, Effect(household=(("resentment", -9),)))
        self.assertEqual(state.population.households[0].resentment, 0)


if __name__ == "__main__":
    unittest.main()
