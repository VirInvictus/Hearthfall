"""Turn resolution: the food math, the dying, and the clock.

Most tests set morale to the drift target and below the birth threshold, which pins the
population steady so a single step can be observed without births or drift moving it.
"""

from __future__ import annotations

import unittest

from support import not_none

from hearthfall.engine import balance, turn
from hearthfall.engine.events.loader import Event
from hearthfall.engine.intel import FactKind, Ledger
from hearthfall.engine.rng import Rng
from hearthfall.engine.state import (
    ChoiceOption,
    Effect,
    GameState,
    Orders,
    Outcome,
    Population,
    Season,
    Stores,
)
from hearthfall.engine.world import Terrain, World

WEIGHTS = {Terrain.PLAIN: 1}


def a_state(
    *,
    adults: int = 6,
    children: list[int] | None = None,
    food: int = 100,
    morale: int = 5,
    turn_number: int = 0,
    seed: int = 1,
) -> GameState:
    world = World.generate(5, 5, Rng(seed), WEIGHTS)
    # Mirrors `turn.new_game`: the clan starts knowing the ground under its own feet, walked
    # and surveyed both, and nothing else. Building the ledger here rather than letting it
    # default keeps the half-lives explicit in the fixture.
    ledger = Ledger(halflives=balance.FACT_HALFLIFE)
    ledger.reveal(world, world.home, turn=0)
    ledger.survey(
        world.home, balance.TERRAIN_CAPACITY[world.tile(world.home).terrain], turn=0
    )
    return GameState(
        seed=seed,
        world=world,
        ledger=ledger,
        population=Population.of(adults, list(children or []), morale),
        stores=Stores(food=food),
        turn=turn_number,
    )


class TestProduction(unittest.TestCase):
    def test_foragers_yield_by_season(self):
        # Exactly as many hands as one plain supports, so this isolates the season from the
        # capacity ceiling slice 2 added. Over-assign and you measure the ceiling instead.
        hands = balance.TERRAIN_CAPACITY[Terrain.PLAIN]
        for offset, season in enumerate(
            [Season.SPRING, Season.SUMMER, Season.AUTUMN, Season.WINTER]
        ):
            state = a_state(turn_number=offset)
            self.assertEqual(state.season, season)
            report = turn.resolve(state, Orders(forage=hands), Rng(1))
            per_forager = (
                balance.FORAGE_YIELD[season]
                * balance.TERRAIN_FORAGE[Terrain.PLAIN]
                // 10
            )
            self.assertEqual(report.produced, hands * per_forager)

    def test_the_known_ground_caps_what_hands_can_bring_in(self):
        # Slice 2's central rule: five hands on one known plain is still one plain's worth.
        # Before this, a forager was worth the same wherever the clan had or had not walked,
        # so exploring bought nothing and the fog was scenery.
        capacity = balance.TERRAIN_CAPACITY[Terrain.PLAIN]
        state = a_state(turn_number=2)  # autumn, the season with the most to lose
        report = turn.resolve(state, Orders(forage=5), Rng(1))
        self.assertEqual(report.forage_capacity, capacity)
        self.assertEqual(report.foragers_idle, 5 - capacity)
        self.assertEqual(
            report.produced, capacity * balance.FORAGE_YIELD[Season.AUTUMN]
        )

    def test_idle_hands_are_said_out_loud(self):
        # If the ceiling is invisible the player cannot learn that scouting is the answer.
        report = turn.resolve(a_state(), Orders(forage=6), Rng(1))
        self.assertTrue(
            any("no ground to work" in line for line in report.log),
            f"nothing in the report told the player why: {report.log}",
        )

    def test_no_foragers_produce_nothing(self):
        report = turn.resolve(a_state(), Orders(), Rng(1))
        self.assertEqual(report.produced, 0)

    def test_winter_hands_cannot_solve_the_problem(self):
        # The whole reason an autumn stockpile is a decision.
        self.assertLess(balance.FORAGE_YIELD[Season.WINTER], balance.FOOD_PER_ADULT)


class TestConsumption(unittest.TestCase):
    def test_adults_and_children_eat_at_different_rates(self):
        state = a_state(adults=4, children=[3, 3])
        report = turn.resolve(state, Orders(), Rng(1))
        self.assertEqual(
            report.consumed, 4 * balance.FOOD_PER_ADULT + 2 * balance.FOOD_PER_CHILD
        )

    def test_production_feeds_the_same_turn_it_arrives(self):
        # Produce runs before consume, so foraging can cover this turn's mouths.
        state = a_state(adults=2, food=0, turn_number=2)  # autumn, yield 5
        report = turn.resolve(state, Orders(forage=1), Rng(1))
        self.assertEqual(report.shortfall, 0)
        self.assertEqual(report.starved, 0)

    def test_the_store_is_never_driven_negative(self):
        state = a_state(adults=6, food=3)
        turn.resolve(state, Orders(), Rng(1))
        self.assertGreaterEqual(state.stores.food, 0)


class TestStarvation(unittest.TestCase):
    def test_a_shortfall_kills(self):
        state = a_state(adults=4, children=[3, 3], food=0)
        report = turn.resolve(state, Orders(), Rng(1))
        self.assertEqual(report.shortfall, 10)
        self.assertEqual(report.starved, 4)

    def test_children_die_before_adults(self):
        state = a_state(adults=4, children=[3, 3], food=0)
        turn.resolve(state, Orders(), Rng(1))
        self.assertEqual(state.population.children, [])
        self.assertEqual(state.population.adults, 2)

    def test_the_child_furthest_from_maturity_is_taken_first(self):
        state = a_state(adults=1, children=[1, 4], food=1, morale=10)
        turn.resolve(state, Orders(), Rng(1))
        # Demand 3, one food, shortfall 2, one death. The nearly-grown one remains and
        # then ages a turn.
        self.assertEqual(state.population.children, [])
        self.assertEqual(state.population.adults, 2, "the survivor came of age")

    def test_starvation_cannot_kill_more_than_exist(self):
        state = a_state(adults=2, children=[], food=0)
        report = turn.resolve(state, Orders(), Rng(1))
        self.assertEqual(report.starved, 2)
        self.assertEqual(state.population.adults, 0)

    def test_starvation_costs_morale(self):
        fed = a_state(adults=2, food=100, morale=8)
        starving = a_state(adults=2, food=0, morale=8)
        turn.resolve(fed, Orders(), Rng(1))
        turn.resolve(starving, Orders(), Rng(1))
        self.assertLess(starving.population.morale, fed.population.morale)

    def test_morale_never_falls_below_the_floor(self):
        state = a_state(adults=8, food=0, morale=1)
        turn.resolve(state, Orders(), Rng(1))
        self.assertGreaterEqual(state.population.morale, balance.MORALE_MIN)


class TestSpoilage(unittest.TestCase):
    def test_stores_rot_by_season(self):
        state = a_state(adults=0, food=100, turn_number=1)  # summer
        report = turn.resolve(state, Orders(), Rng(1))
        self.assertEqual(report.spoiled, int(100 * balance.SPOIL_RATE[Season.SUMMER]))

    def test_tending_slows_the_rot(self):
        untended = a_state(adults=4, food=100, turn_number=1)
        tended = a_state(adults=4, food=100, turn_number=1)
        loose = turn.resolve(untended, Orders(), Rng(1))
        kept = turn.resolve(tended, Orders(tend=3), Rng(1))
        self.assertLess(kept.spoiled, loose.spoiled)

    def test_tending_can_never_fully_defeat_rot(self):
        state = a_state(
            adults=20, food=1000, turn_number=3
        )  # winter, the kindest season
        report = turn.resolve(state, Orders(tend=20), Rng(1))
        self.assertGreater(report.spoiled, 0)

    def test_rot_takes_only_what_survived_the_eating(self):
        # Spoil runs after consume, so food someone just ate is never rotted first.
        state = a_state(adults=5, food=100, turn_number=1)
        report = turn.resolve(state, Orders(), Rng(1))
        remaining = 100 - report.consumed
        self.assertEqual(
            report.spoiled, int(remaining * balance.SPOIL_RATE[Season.SUMMER])
        )


class TestExploration(unittest.TestCase):
    def test_too_few_scouts_reveal_nothing(self):
        state = a_state()
        report = turn.resolve(state, Orders(scout=balance.SCOUTS_TO_WALK - 1), Rng(1))
        self.assertIsNone(report.revealed)
        self.assertEqual(state.ledger.known_count, 1)

    def test_enough_scouts_reveal_a_frontier_tile(self):
        state = a_state()
        report = turn.resolve(state, Orders(scout=balance.SCOUTS_TO_WALK), Rng(1))
        self.assertIsNotNone(report.revealed)
        self.assertEqual(state.ledger.known_count, 2)
        self.assertTrue(state.ledger.knows(FactKind.TERRAIN, not_none(report.revealed)))

    def test_a_named_target_is_honoured(self):
        state = a_state()
        target = state.ledger.frontier(state.world)[0]
        report = turn.resolve(state, Orders(scout=2, scout_target=target), Rng(1))
        self.assertEqual(report.revealed, target)

    def test_exploring_off_the_frontier_is_refused(self):
        state = a_state()
        with self.assertRaises(ValueError):
            turn.resolve(state, Orders(scout=2, scout_target=(0, 0)), Rng(1))

    def test_an_unnamed_target_is_drawn_reproducibly(self):
        first, second = a_state(), a_state()
        self.assertEqual(
            turn.resolve(first, Orders(scout=2), Rng(7)).revealed,
            turn.resolve(second, Orders(scout=2), Rng(7)).revealed,
        )

    def test_exploring_a_finished_map_is_survivable(self):
        state = a_state()
        for coord in list(state.world.tiles):
            state.ledger.reveal(state.world, coord, state.turn)
        report = turn.resolve(state, Orders(scout=4), Rng(1))
        self.assertIsNone(report.revealed)


class TestScoutingIsAGradient(unittest.TestCase):
    """Slice 3: party size decides how well the ground gets known, not whether it does.

    Two walk it and learn what it is. A third stops and looks properly, and the tile becomes
    ground the clan knows how to work. The cliff at `SCOUTS_TO_WALK` is still there, because a
    lone scout genuinely cannot cover ground, but past it the return is a slope.
    """

    def test_a_walking_party_learns_the_terrain_and_no_more(self):
        state = a_state()
        report = turn.resolve(state, Orders(scout=balance.SCOUTS_TO_WALK), Rng(1))
        walked = not_none(report.revealed)
        self.assertTrue(state.ledger.knows(FactKind.TERRAIN, walked))
        self.assertFalse(state.ledger.knows(FactKind.FORAGE, walked))
        self.assertIsNone(report.surveyed)

    def test_a_bigger_party_also_surveys_what_it_walked_into(self):
        state = a_state()
        report = turn.resolve(state, Orders(scout=balance.SCOUTS_TO_SURVEY), Rng(1))
        self.assertEqual(report.surveyed, report.revealed)
        self.assertTrue(state.ledger.knows(FactKind.FORAGE, not_none(report.surveyed)))

    def test_a_survey_raises_the_forage_ceiling(self):
        walking, surveying = a_state(), a_state()
        target = walking.ledger.frontier(walking.world)[0]
        turn.resolve(
            walking, Orders(scout=balance.SCOUTS_TO_WALK, scout_target=target), Rng(1)
        )
        turn.resolve(
            surveying,
            Orders(scout=balance.SCOUTS_TO_SURVEY, scout_target=target),
            Rng(1),
        )
        self.assertGreater(surveying.forage_capacity, walking.forage_capacity)

    def test_the_party_surveys_the_best_ground_it_knows_of(self):
        """Not necessarily the tile it just walked into.

        Orders stay scalar and the engine places the work, exactly as it places foragers.
        A party that walks into thin ground gives the good ground it already knows about the
        proper look instead, which is what keeps scouting worth doing after the frontier has
        stopped being interesting.
        """
        state = a_state()
        forest = (state.world.home[0], state.world.home[1] - 1)
        state.world.tiles[forest].terrain = Terrain.FOREST
        state.ledger.reveal(state.world, forest, turn=0)  # walked, never surveyed
        target = next(
            coord for coord in state.ledger.frontier(state.world) if coord != forest
        )

        report = turn.resolve(
            state,
            Orders(scout=balance.SCOUTS_TO_SURVEY, scout_target=target),
            Rng(1),
        )
        self.assertEqual(report.revealed, target)
        self.assertEqual(report.surveyed, forest)

    def test_a_survey_that_would_buy_nothing_is_not_made(self):
        # Nothing left to walk into and nothing left to look harder at. The hands are wasted,
        # and the report says so rather than quietly re-surveying known ground.
        state = a_state()
        for coord in list(state.world.tiles):
            state.ledger.reveal(state.world, coord, state.turn)
            state.ledger.survey(
                coord, balance.TERRAIN_CAPACITY[state.world.tile(coord).terrain], turn=0
            )
        report = turn.resolve(state, Orders(scout=balance.SCOUTS_TO_SURVEY), Rng(1))
        self.assertIsNone(report.revealed)
        self.assertIsNone(report.surveyed)

    def test_surveying_still_pays_once_the_map_is_walked_out(self):
        """The property that keeps scouting from switching itself off halfway through a run.

        A clan that has walked every tile it can reach has run out of ground to find, but not
        out of ground to learn.
        """
        state = a_state()
        for coord in list(state.world.tiles):
            state.ledger.reveal(state.world, coord, state.turn)
        before = turn.forage_take(
            state.ledger, foragers=0, season=state.season
        ).capacity
        report = turn.resolve(state, Orders(scout=balance.SCOUTS_TO_SURVEY), Rng(1))
        self.assertIsNone(report.revealed)
        self.assertIsNotNone(report.surveyed)
        self.assertGreater(state.forage_capacity, before)


class TestPopulationGrowth(unittest.TestCase):
    def test_children_age_toward_maturity(self):
        state = a_state(children=[4, 3])
        turn.resolve(state, Orders(), Rng(1))
        self.assertEqual(state.population.children, [3, 2])

    def test_a_child_matures_into_an_adult(self):
        state = a_state(adults=6, children=[1, 3])
        report = turn.resolve(state, Orders(), Rng(1))
        self.assertEqual(report.matured, 1)
        self.assertEqual(state.population.adults, 7)
        self.assertEqual(state.population.children, [2])

    def test_a_starving_clan_never_births(self):
        for seed in range(20):
            state = a_state(food=0, morale=10, seed=seed)
            self.assertEqual(turn.resolve(state, Orders(), Rng(seed)).born, 0)

    def test_a_miserable_clan_never_births(self):
        for seed in range(20):
            state = a_state(
                food=1000, morale=balance.BOND_MOOD_THRESHOLD - 1, seed=seed
            )
            self.assertEqual(turn.resolve(state, Orders(), Rng(seed)).born, 0)

    def test_a_fed_and_willing_household_bears_on_a_schedule(self):
        # Growth is deterministic now, and the schedule is the point: a hearth kept fed and
        # content bears after BOND_TO_BEAR seasons, every time. The old gate rolled dice
        # against clan-wide food and morale, which is a question about nobody, and it came
        # back yes so rarely that the clan simply never grew.
        state = a_state(food=1000, morale=balance.MORALE_MAX)
        births = 0
        for _ in range(balance.BOND_TO_BEAR):
            births += turn.resolve(state, Orders(), Rng(1)).born
        self.assertGreater(births, 0, "a fed, content clan never grew")

    def test_a_hungry_season_sets_a_household_back(self):
        # Famine costs years of growth, not a turn of it, which is what makes rationing a
        # decision with a tail rather than a decision about this season only.
        state = a_state(food=1000, morale=balance.MORALE_MAX)
        turn.resolve(state, Orders(), Rng(1))
        earned = state.population.households[0].bond
        self.assertGreater(earned, 0)

        state.stores.food = 0
        turn.resolve(state, Orders(), Rng(1))
        self.assertLess(state.population.households[0].bond, earned)


class TestMoraleDrift(unittest.TestCase):
    def test_low_morale_recovers_toward_the_middle(self):
        state = a_state(morale=1)
        turn.resolve(state, Orders(), Rng(1))
        self.assertEqual(state.population.morale, 2)

    def test_high_morale_settles_toward_the_middle(self):
        # One fed adult, and a store deliberately under BIRTH_FOOD_THRESHOLD, so neither
        # starvation nor a birth moves anything and the drift is the only thing acting. This
        # used to use a clan of nobody; since morale became the average of the *living*
        # households, an empty clan reports 0 rather than whatever it felt before it died.
        state = a_state(morale=balance.MORALE_MAX, food=39, adults=1, children=[])
        turn.resolve(state, Orders(), Rng(1))
        self.assertEqual(state.population.morale, balance.MORALE_MAX - 1)

    def test_morale_at_the_target_does_not_drift(self):
        state = a_state(morale=balance.MORALE_DRIFT_TARGET)
        turn.resolve(state, Orders(), Rng(1))
        self.assertEqual(state.population.morale, balance.MORALE_DRIFT_TARGET)


class TestTheClock(unittest.TestCase):
    def test_a_turn_advances_the_season(self):
        state = a_state()
        self.assertEqual(state.season, Season.SPRING)
        turn.resolve(state, Orders(), Rng(1))
        self.assertEqual(state.season, Season.SUMMER)

    def test_four_turns_make_a_year(self):
        state = a_state()
        self.assertEqual(state.year, 1)
        for _ in range(4):
            turn.resolve(state, Orders(), Rng(1))
        self.assertEqual(state.year, 2)
        self.assertEqual(state.season, Season.SPRING)

    def test_surviving_the_full_run_endures(self):
        state = a_state(adults=4, food=10_000)
        for _ in range(balance.TURNS_PER_RUN):
            self.assertIsNone(state.outcome)
            turn.resolve(state, Orders(), Rng(1))
        self.assertIs(state.outcome, Outcome.ENDURED)

    def test_losing_every_adult_buries_the_clan(self):
        state = a_state(adults=1, children=[], food=0)
        report = turn.resolve(state, Orders(), Rng(1))
        self.assertIs(report.outcome, Outcome.BURIED)
        self.assertIs(state.outcome, Outcome.BURIED)

    def test_dying_on_the_last_turn_is_still_dying(self):
        state = a_state(
            adults=1, children=[], food=0, turn_number=balance.TURNS_PER_RUN - 1
        )
        turn.resolve(state, Orders(), Rng(1))
        self.assertIs(state.outcome, Outcome.BURIED)

    def test_a_finished_run_resolves_no_further(self):
        state = a_state(adults=1, food=0)
        turn.resolve(state, Orders(), Rng(1))
        with self.assertRaises(RuntimeError):
            turn.resolve(state, Orders(), Rng(1))


class TestOrders(unittest.TestCase):
    def test_orders_cannot_assign_more_people_than_exist(self):
        state = a_state(adults=3)
        with self.assertRaises(ValueError):
            turn.resolve(state, Orders(forage=2, scout=2), Rng(1))

    def test_orders_cannot_be_negative(self):
        state = a_state(adults=3)
        with self.assertRaises(ValueError):
            turn.resolve(state, Orders(forage=-1), Rng(1))

    def test_children_are_not_hands(self):
        state = a_state(adults=2, children=[3, 3, 3])
        with self.assertRaises(ValueError):
            turn.resolve(state, Orders(forage=3), Rng(1))


class TestEffects(unittest.TestCase):
    def test_an_effect_moves_the_numbers(self):
        state = a_state(adults=4, food=50, morale=5)
        turn.apply_effect(state, Effect(food=-10, morale=2, adults=-1))
        self.assertEqual(state.stores.food, 40)
        self.assertEqual(state.population.morale, 7)
        self.assertEqual(state.population.adults, 3)

    def test_effects_are_clamped_to_a_legal_state(self):
        state = a_state(adults=1, food=5, morale=1)
        turn.apply_effect(state, Effect(food=-100, morale=-100, adults=-100))
        self.assertEqual(state.stores.food, 0)
        self.assertEqual(state.population.morale, balance.MORALE_MIN)
        self.assertEqual(state.population.adults, 0)

    def test_an_effect_can_add_and_remove_children(self):
        state = a_state(children=[2])
        turn.apply_effect(state, Effect(children=2))
        self.assertEqual(len(state.population.children), 3)
        turn.apply_effect(state, Effect(children=-3))
        self.assertEqual(state.population.children, [])


class TestEventsInATurn(unittest.TestCase):
    def flavor(self, **effect_kwargs) -> Event:
        return Event(
            id="flavor",
            title="A Quiet Thing",
            body="...",
            effect=Effect(**effect_kwargs),
        )

    def fork(self) -> Event:
        return Event(
            id="fork",
            title="A Hard Thing",
            body="...",
            options=(
                ChoiceOption(text="Bear it", effect=Effect(food=-10, morale=1)),
                ChoiceOption(text="Refuse it", effect=Effect(morale=-3)),
            ),
        )

    def test_no_corpus_means_no_events(self):
        report = turn.resolve(a_state(), Orders(), Rng(1))
        self.assertIsNone(report.event_id)

    def test_a_flavor_event_applies_itself(self):
        state = a_state(food=100)
        report = turn.resolve(state, Orders(), Rng(1), [self.flavor(food=-20)])
        self.assertEqual(report.event_id, "flavor")
        self.assertIsNone(report.pending)
        # Consumed 12, rotted, then the event took its 20.
        self.assertLess(state.stores.food, 100 - 12 - 20 + 1)

    def test_a_fork_waits_for_an_answer(self):
        state = a_state()
        report = turn.resolve(state, Orders(), Rng(1), [self.fork()])
        self.assertIsNotNone(report.pending)
        self.assertEqual(report.pending, state.pending)
        self.assertEqual(not_none(report.pending).event_id, "fork")
        self.assertEqual(len(not_none(report.pending).options), 2)

    def test_the_next_turn_is_blocked_until_the_answer_comes(self):
        state = a_state()
        turn.resolve(state, Orders(), Rng(1), [self.fork()])
        with self.assertRaises(RuntimeError):
            turn.resolve(state, Orders(), Rng(1))

    def test_answering_applies_the_chosen_effect_and_unblocks(self):
        state = a_state(food=100, morale=5)
        turn.resolve(state, Orders(), Rng(1), [self.fork()])
        food_before = state.stores.food
        turn.apply_choice(state, 0)
        self.assertIsNone(state.pending)
        self.assertEqual(state.stores.food, food_before - 10)
        self.assertEqual(state.population.morale, 6)
        turn.resolve(state, Orders(), Rng(1))  # no longer blocked

    def test_the_other_option_has_the_other_effect(self):
        state = a_state(morale=5)
        turn.resolve(state, Orders(), Rng(1), [self.fork()])
        turn.apply_choice(state, 1)
        self.assertEqual(state.population.morale, 2)

    def test_answering_nothing_is_refused(self):
        with self.assertRaises(RuntimeError):
            turn.apply_choice(a_state(), 0)

    def test_an_option_out_of_range_is_refused(self):
        state = a_state()
        turn.resolve(state, Orders(), Rng(1), [self.fork()])
        for index in [-1, 2, 99]:
            with self.assertRaises(IndexError):
                turn.apply_choice(state, index)

    def test_a_fired_event_is_recorded(self):
        state = a_state()
        turn.resolve(state, Orders(), Rng(1), [self.flavor(morale=1)])
        self.assertEqual(state.fired_events, ["flavor"])

    def test_a_once_event_never_comes_round_again(self):
        state = a_state(food=10_000)
        once = Event(id="once", title="T", body="B", once=True, effect=Effect(morale=1))
        fired = 0
        for _ in range(6):
            fired += turn.resolve(state, Orders(), Rng(1), [once]).event_id is not None
        self.assertEqual(fired, 1)

    def test_an_answer_that_kills_the_last_adult_buries_the_clan(self):
        # Even on the final turn, having survived the clock is not a shield against the
        # answer you just gave.
        state = a_state(
            adults=1, children=[], food=1000, turn_number=balance.TURNS_PER_RUN - 1
        )
        lethal = Event(
            id="lethal",
            title="T",
            body="B",
            options=(ChoiceOption(text="Go alone", effect=Effect(adults=-1)),),
        )
        report = turn.resolve(state, Orders(), Rng(1), [lethal])
        self.assertIs(report.outcome, Outcome.ENDURED)
        turn.apply_choice(state, 0)
        self.assertIs(state.outcome, Outcome.BURIED)

    def test_exploring_records_the_terrain_for_content_to_read(self):
        state = a_state()
        report = turn.resolve(state, Orders(scout=2), Rng(1))
        self.assertEqual(
            state.snapshot()["terrain_revealed"], str(report.revealed_terrain)
        )

    def test_terrain_revealed_starts_as_none(self):
        self.assertEqual(turn.new_game(1).snapshot()["terrain_revealed"], "none")


class TestNewGame(unittest.TestCase):
    def test_a_new_game_starts_from_balance(self):
        state = turn.new_game(seed=99)
        self.assertEqual(state.population.adults, balance.STARTING_ADULTS)
        self.assertEqual(state.population.child_count, balance.STARTING_CHILDREN)
        self.assertEqual(state.stores.food, balance.STARTING_FOOD)
        self.assertEqual(state.population.morale, balance.STARTING_MORALE)
        self.assertEqual(state.turn, 0)
        self.assertIsNone(state.outcome)

    def test_the_seed_determines_the_whole_starting_world(self):
        first, second = turn.new_game(seed=5), turn.new_game(seed=5)
        self.assertEqual(first.snapshot(), second.snapshot())
        self.assertEqual(
            {c: t.terrain for c, t in first.world.tiles.items()},
            {c: t.terrain for c, t in second.world.tiles.items()},
        )


if __name__ == "__main__":
    unittest.main()


class TestForecast(unittest.TestCase):
    """The forecast has one job: agree with what resolution actually does.

    It duplicates the food math rather than sharing code with the mutating steps, so these
    tests are the thing that keeps the two from drifting apart. If someone retunes a
    constant or reorders the tick and only fixes one side, this fails.
    """

    def _cases(self):
        for turn_number in range(4):  # one of each season
            for food in (0, 7, 40, 100):
                for adults, children in ((6, []), (3, [1, 2]), (1, [4])):
                    for orders in (
                        Orders(),
                        Orders(forage=1),
                        Orders(tend=1),
                        Orders(forage=2, tend=1),
                    ):
                        if orders.assigned > adults:
                            continue
                        yield turn_number, food, adults, children, orders

    def test_forecast_matches_resolution(self):
        for turn_number, food, adults, children, orders in self._cases():
            with self.subTest(
                turn=turn_number, food=food, adults=adults, orders=orders
            ):
                projected = turn.forecast(
                    a_state(
                        adults=adults,
                        children=list(children),
                        food=food,
                        turn_number=turn_number,
                    ),
                    orders,
                )
                report = turn.resolve(
                    a_state(
                        adults=adults,
                        children=list(children),
                        food=food,
                        turn_number=turn_number,
                    ),
                    orders,
                    Rng(1),
                )
                self.assertEqual(projected.produced, report.produced)
                self.assertEqual(projected.eaten, report.consumed)
                self.assertEqual(projected.shortfall, report.shortfall)
                self.assertEqual(projected.would_starve, report.starved)
                self.assertEqual(projected.spoiled, report.spoiled)

    def test_forecast_does_not_mutate(self):
        state = a_state(food=50, adults=6)
        before = (state.stores.food, state.population.adults, state.turn)
        turn.forecast(state, Orders(forage=3, tend=2))
        self.assertEqual(
            (state.stores.food, state.population.adults, state.turn), before
        )

    def test_closing_food_is_opening_plus_net(self):
        f = turn.forecast(a_state(food=60), Orders(forage=4))
        self.assertEqual(f.closing_food, f.opening_food + f.net)

    def test_winter_foraging_cannot_help(self):
        winter = turn.forecast(a_state(turn_number=3, food=40), Orders(forage=6))
        idle = turn.forecast(a_state(turn_number=3, food=40), Orders())
        self.assertEqual(winter.produced, 0)
        self.assertEqual(winter.closing_food, idle.closing_food)

    def test_tending_reduces_spoilage_to_a_floor(self):
        light = turn.forecast(a_state(turn_number=1, food=100), Orders(tend=1))
        heavy = turn.forecast(a_state(turn_number=1, food=100), Orders(tend=6))
        self.assertLess(heavy.spoiled, light.spoiled)
        self.assertGreaterEqual(heavy.spoil_rate, balance.SPOIL_RATE_FLOOR)
