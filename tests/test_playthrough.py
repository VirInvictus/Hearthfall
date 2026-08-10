"""A full run, headless.

This is invariant 1 demonstrated rather than claimed. If a whole game can be played here,
with the shipped corpus, with no terminal anywhere in the call stack, then the engine really
is a library and the Textual skin really is shed-able.

It is also the harness a balance pass runs against: `summarise()` plays a fixed set of seeds
and reports how they ended.
"""

from __future__ import annotations

import unittest
from dataclasses import dataclass

from support import not_none

from hearthfall.engine import balance, turn
from hearthfall.engine.events.loader import load_corpus
from hearthfall.engine.people import Rationing
from hearthfall.engine.rng import Rng
from hearthfall.engine.state import Orders, Outcome, Season

CORPUS = load_corpus(turn.new_game(0).snapshot())


def ground_capacity(state) -> int:
    """How many foragers the ground the clan has walked will support."""
    return turn.forage_take(state.ledger, foragers=0, season=state.season).capacity


def steady_orders(state) -> Orders:
    """A plain, defensible policy: keep a scouting party and a tender, forage with the rest.

    Not a good player, and since slice 2 it is a visibly naive one: it will happily send six
    hands to ground that supports two. Kept exactly as it was because it is the baseline the
    Phase 0 numbers were measured against, and re-basing it would throw that comparison away.
    """
    adults = state.population.adults
    scout = (
        balance.SCOUTS_TO_WALK
        if adults >= 5 and state.ledger.frontier(state.world)
        else 0
    )
    tend = 1 if adults - scout >= 3 else 0
    return Orders(forage=adults - scout - tend, scout=scout, tend=tend)


# --- Policies that differ in exactly one thing -------------------------------------------
#
# The three below form a ladder, each adding a single insight to the one before it, so that a
# comparison between any two of them measures that insight and nothing else. The older pair
# (`steady_orders` and `winter_scout_orders`) differ in two dimensions at once, which did not
# matter while exploring paid nothing and became actively misleading the moment it did: the
# "naive" policy scouted more, so it won, and the test read that as the winter insight being
# worthless.


def homebody_orders(state) -> Orders:
    """Never scouts. Works the ground it was born on, as well as that ground can be worked.

    The floor of the kill-switch comparison: a player who understands capacity but refuses to
    pay to look.
    """
    adults = state.population.adults
    forage = min(adults, ground_capacity(state))
    return Orders(forage=forage, tend=adults - forage)


def scouting_orders(state) -> Orders:
    """Scouts while the map is the binding constraint, forages once it is not.

    One insight above the homebody: ground you have walked is ground you can work, so when
    there are more hands than ground, hands should go and find ground.
    """
    adults = state.population.adults
    capacity = ground_capacity(state)
    scouting_is_free = capacity <= adults - balance.SCOUTS_TO_WALK
    scout = (
        balance.SCOUTS_TO_WALK
        if scouting_is_free and state.ledger.frontier(state.world)
        else 0
    )
    forage = min(adults - scout, capacity)
    return Orders(forage=forage, scout=scout, tend=adults - scout - forage)


def surveying_orders(state) -> Orders:
    """`scouting_orders` with one more insight: send the third scout and look properly.

    One rung above `scouting_orders` and identical to it in every other respect, so the gap
    between the two measures the slice 3 gradient and nothing else. The third hand costs a
    season's foraging and buys a tile worth its full terrain capacity instead of a token crew.
    """
    adults = state.population.adults
    capacity = ground_capacity(state)
    scout = (
        balance.SCOUTS_TO_SURVEY
        if capacity <= adults - balance.SCOUTS_TO_SURVEY
        else balance.SCOUTS_TO_WALK
        if capacity <= adults - balance.SCOUTS_TO_WALK
        else 0
    )
    scout = min(scout, max(0, adults - 1))
    forage = min(adults - scout, capacity)
    return Orders(forage=forage, scout=scout, tend=adults - scout - forage)


def season_aware_orders(state) -> Orders:
    """`scouting_orders` plus the winter insight: winter yields nothing, so do not forage it.

    The one dimension that separates this from `scouting_orders`. In winter the foraging hands
    go to tending instead, which is worth real food because winter stores are what the clan
    lives on and rot is the only thing still taking from them.
    """
    if state.season is not Season.WINTER:
        return scouting_orders(state)

    adults = state.population.adults
    scout = (
        balance.SCOUTS_TO_WALK
        if adults >= balance.SCOUTS_TO_WALK + 1 and state.ledger.frontier(state.world)
        else 0
    )
    return Orders(forage=0, scout=scout, tend=adults - scout)


def watchful_orders(state) -> Orders:
    """`surveying_orders`, plus a party out every winter, when foraging is worthless anyway.

    One insight above surveying: a picture of the ground does not stay true, so a hand that
    has nothing better to do in winter should go and look. The comparison against
    `surveying_orders` measures exactly that and nothing else.

    It has to be winter that separates them, because a surveying policy stops sending parties
    of its own accord once the ground outruns the hands, and a "settles down after year two"
    policy therefore turns out to be the same function with a different name. That mistake
    already cost this project a version once, with WORKERS and CHILDREN rationing.
    """
    if state.season is not Season.WINTER:
        return surveying_orders(state)
    adults = state.population.adults
    scout = balance.SCOUTS_TO_SURVEY if adults > balance.SCOUTS_TO_SURVEY else 0
    return Orders(forage=0, scout=scout, tend=adults - scout)


def unequal_orders(state) -> Orders:
    """`steady_orders`, feeding the workers first when the store is short.

    A player who has decided that keeping the hands standing is worth a hearth remembering it.
    In the spread it is the only policy that ever makes a household resentful, which is the
    condition a good deal of the corpus is keyed on, and it has to be built on the *naive*
    policy to manage it: rationing only bites when the store is short, and a competent player
    is rarely short, so a competent policy rationing unequally rations unequally almost never.
    """
    orders = steady_orders(state)
    orders.rationing = Rationing.WORKERS
    return orders


def _food_lost_to_stale_intel(seed: int, policy) -> int:
    """How much food a run expected and did not get, because its numbers were out of date."""
    state = turn.new_game(seed)
    rng = Rng(seed)
    lost = 0
    while not state.is_over:
        report = turn.resolve(state, policy(state), rng, CORPUS)
        lost += max(0, report.expected - report.produced)
        if state.pending is not None:
            turn.apply_choice(state, 0)
    return lost


@dataclass
class Transcript:
    outcome: Outcome | None
    turns: int
    survivors: int
    food: int
    tiles_known: int
    tiles_surveyed: int
    events: list[str]
    lines: list[str]


def play(seed: int, choice: int = 0) -> Transcript:
    """Play one run start to finish, answering every fork the same way."""
    state = turn.new_game(seed)
    rng = Rng(seed)
    events: list[str] = []
    lines: list[str] = []

    while not state.is_over:
        report = turn.resolve(state, steady_orders(state), rng, CORPUS)
        lines.extend(report.log)
        if report.event_id:
            events.append(report.event_id)
        if state.pending is not None:
            index = min(choice, len(state.pending.options) - 1)
            turn.apply_choice(state, index)

    return Transcript(
        outcome=state.outcome,
        turns=state.turn,
        survivors=state.population.total,
        food=state.stores.food,
        tiles_known=state.ledger.known_count,
        tiles_surveyed=len(state.ledger.surveyed()),
        events=events,
        lines=lines,
    )


def winter_scout_orders(state) -> Orders:
    """A policy that has noticed winter foraging yields nothing, and scouts instead.

    Kept beside the naive one so the tests can compare them. If the two policies fare the
    same, the allocation is not a decision and Phase 0 has failed its own question.
    """
    adults = state.population.adults
    winter = state.season is Season.WINTER
    scout = (
        balance.SCOUTS_TO_WALK
        if winter and adults >= 3 and state.ledger.frontier(state.world)
        else 0
    )
    tend = 1 if adults - scout >= 2 else 0
    return Orders(forage=adults - scout - tend, scout=scout, tend=tend)


def play_with(seed: int, policy, choice: int = 0) -> Transcript:
    state = turn.new_game(seed)
    rng = Rng(seed)
    events: list[str] = []

    while not state.is_over:
        report = turn.resolve(state, policy(state), rng, CORPUS)
        if report.event_id:
            events.append(report.event_id)
        if state.pending is not None:
            turn.apply_choice(state, min(choice, len(state.pending.options) - 1))

    return Transcript(
        outcome=state.outcome,
        turns=state.turn,
        survivors=state.population.total,
        food=state.stores.food,
        tiles_known=state.ledger.known_count,
        tiles_surveyed=len(state.ledger.surveyed()),
        events=events,
        lines=[],
    )


def summarise(seeds: range = range(50)) -> dict[Outcome, int]:
    tally: dict[Outcome, int] = {Outcome.ENDURED: 0, Outcome.BURIED: 0}
    for seed in seeds:
        tally[not_none(play(seed).outcome)] += 1
    return tally


class TestAFullRun(unittest.TestCase):
    def test_a_run_plays_to_an_end_with_no_terminal_in_sight(self):
        transcript = play(seed=1)
        self.assertIn(transcript.outcome, (Outcome.ENDURED, Outcome.BURIED))
        self.assertLessEqual(transcript.turns, balance.TURNS_PER_RUN)
        self.assertTrue(
            transcript.lines, "a run that reports nothing cannot be rendered"
        )

    def test_every_seed_reaches_an_ending(self):
        for seed in range(30):
            with self.subTest(seed=seed):
                self.assertIsNotNone(play(seed).outcome)

    def test_the_same_seed_replays_exactly(self):
        first, second = play(7), play(7)
        self.assertEqual(first, second)

    def test_different_seeds_tell_different_stories(self):
        transcripts = [play(seed) for seed in range(12)]
        self.assertGreater(len({tuple(t.events) for t in transcripts}), 1)

    def test_a_different_answer_changes_the_run(self):
        # If choosing differently never diverges, the forks are decoration.
        first = play(4, choice=0)
        second = play(4, choice=1)
        self.assertNotEqual(first, second)

    def test_scouts_open_the_map(self):
        self.assertGreater(play(seed=1).tiles_known, 1)

    def test_the_corpus_actually_fires(self):
        self.assertTrue(play(seed=1).events, "twenty events and none of them came up")


class TestTheShapeOfARun(unittest.TestCase):
    """Loose balance guards. These do not pin the numbers; they catch a broken loop.

    A tuning pass is expected to move the tally. What must not happen is a game that every
    seed wins or every seed loses, because either way the allocation is not a decision.
    """

    # A tenth of the seeds either way. Loose enough to survive a tuning pass or a dozen new
    # events, tight enough that a loop which quietly stopped being a game trips it.
    FLOOR = 5

    def test_the_run_is_not_a_formality(self):
        tally = summarise()
        self.assertGreaterEqual(
            tally[Outcome.BURIED],
            self.FLOOR,
            "almost nothing can be lost; nothing is at stake",
        )

    def test_the_run_is_not_hopeless(self):
        tally = summarise()
        self.assertGreaterEqual(
            tally[Outcome.ENDURED],
            self.FLOOR,
            "almost nothing can be won; the loop is broken",
        )


class TestTheCorpusIsAlive(unittest.TestCase):
    """Dead content is the other half of the loader's job.

    The loader stops an event that is malformed. Nothing stops an event that is perfectly
    formed and simply unreachable, because its conditions describe a world state the game
    never produces. That looks exactly like content needing a rewrite, so it gets caught
    here instead: every shipped event must fire at least once across a spread of runs.
    """

    def fired(self) -> set[str]:
        # The spread runs across the policy ladder, not just one policy answered two ways.
        # Reachability depends on how prosperous a run gets, and a corpus entry gated on high
        # morale is only ever seen by a player good enough to earn it.
        #
        # The ladder has to keep up with the engine, and it did not: this spread predated
        # slice 3, so nothing in it ever sent a third scout, and a whole file of content keyed
        # on surveys and staleness was unreachable by construction of the harness rather than
        # by anything wrong with the content. Same for rationing, which no policy here ever set
        # away from equal shares, so nothing gated on a resentful hearth could ever be seen.
        seen: set[str] = set()
        for seed in range(60):
            seen.update(play(seed).events)
            seen.update(play_with(seed, homebody_orders).events)
            seen.update(play_with(seed, scouting_orders).events)
            seen.update(play_with(seed, season_aware_orders).events)
            seen.update(play_with(seed, season_aware_orders, choice=1).events)
            seen.update(play_with(seed, surveying_orders).events)
            seen.update(play_with(seed, watchful_orders).events)
            seen.update(play_with(seed, unequal_orders).events)
            seen.update(play_with(seed, unequal_orders, choice=1).events)
        return seen

    def test_every_shipped_event_can_actually_happen(self):
        unreachable = {event.id for event in CORPUS} - self.fired()
        self.assertEqual(
            unreachable, set(), "authored, shipped, and never seen by a player"
        )


def endured(policy, seeds: range = range(60), choice: int = 0) -> int:
    return sum(
        1
        for seed in seeds
        if play_with(seed, policy, choice).outcome is Outcome.ENDURED
    )


def people_left(policy, seeds: range = range(60), choice: int = 0) -> int:
    """Total survivors across a spread of runs. The measure that still discriminates.

    Binary endurance has saturated: measured over 200 seeds, a scouting policy ends 198 and a
    season-reading one 199, which is noise, while a clan that never scouts still "endures" 152
    times. It does so by shrinking to one or two adults on one tile, which is a stable state
    the win condition happens to count as survival.

    Clan size separates the same policies 1.4 / 6.5 / 7.8, because the interesting question
    slice 2 introduced is not whether anyone is left but how many the ground could carry. An
    integer total rather than a mean, so the comparison never rides on float fuzz.
    """
    return sum(play_with(seed, policy, choice).survivors for seed in seeds)


class TestAllocationIsADecision(unittest.TestCase):
    def test_reading_the_seasons_beats_not_reading_them(self):
        # Phase 0's whole question. If a policy that understands winter does no better than
        # one that ignores it, the loop is a slider and not a game.
        #
        # Both sides scout identically; winter allocation is the only difference between
        # them. This used to compare two policies that also scouted at different rates, which
        # was harmless while exploring paid nothing and became a lie the moment it did: the
        # "naive" policy scouted more, so it won, and the test read that as winter not
        # mattering.
        self.assertGreater(
            people_left(season_aware_orders), people_left(scouting_orders)
        )


class TestPayingToLookPullsYouForward(unittest.TestCase):
    """Sub-project 1's kill switch, as an assertion rather than a note in the roadmap.

    `roadmap.md` says: if the fog does not pull here, the central premise is wrong, and no
    amount of council drama or combat depth retrofits a reason to scout. Stop.

    Before slice 2 this could not have been written down. `FORAGE_YIELD` was keyed on season
    alone, so a revealed tile fed nothing but the event table and a scout was a hand thrown
    away. The two policies differ in exactly one thing: whether they ever pay to look.

    If this fails, do not tune until it passes. It is the question, and a no is an answer.
    """

    def test_a_clan_that_scouts_outlives_one_that_stays_home(self):
        scouting, homebody = endured(scouting_orders), endured(homebody_orders)
        self.assertGreater(
            scouting,
            homebody,
            f"scouting endured {scouting}/60 against {homebody}/60 for staying home; "
            "paying to look does not pay, which is the premise failing",
        )

    def test_a_clan_that_scouts_is_a_clan_and_not_a_remnant(self):
        # The sharper form of the same question. Staying home does not usually wipe you out,
        # it grinds you down to two or three people on one tile, which the win condition is
        # generous enough to call surviving. What scouting buys is a clan worth the name.
        scouting, homebody = people_left(scouting_orders), people_left(homebody_orders)
        self.assertGreater(scouting, homebody * 2)

    def test_looking_harder_pays_more_than_looking_wider(self):
        """Slice 3's own question, and the reason the third scout exists.

        Measured over 200 seeds while the slice was built: a policy that only ever walks ends
        with 3.1 people, one that surveys with 4.9. Before slice 3 the same third hand was
        worth *nothing* (5.8 against 6.2, i.e. slightly harmful), because a walked tile and a
        surveyed one were the same tile. That is the threshold-into-slope, in survivors.

        The value of `WALKED_CAPACITY` is what this rides on and it was picked here: at 0 a
        walking party is useless (14 runs in 200 endured) and the cliff has merely moved to
        three scouts; at 2 only a forest gains anything from a survey and the gap collapses to
        5.2 against 5.6. One is the value that leaves both rungs worth standing on.
        """
        surveying, walking = people_left(surveying_orders), people_left(scouting_orders)
        self.assertGreater(
            surveying,
            walking,
            f"surveying left {surveying} people against {walking} for walking alone; "
            "the third scout buys nothing and the gradient is flat",
        )

    def test_a_survey_is_the_only_thing_that_lifts_a_tile_to_its_full_worth(self):
        # The mechanism behind the outcome above. Walking the same ground with a smaller party
        # leaves the ceiling where it was, however many tiles get walked.
        for seed in range(8):
            with self.subTest(seed=seed):
                surveying = play_with(seed, surveying_orders)
                walking = play_with(seed, scouting_orders)
                self.assertGreater(surveying.tiles_surveyed, walking.tiles_surveyed)

    def test_a_clan_that_stops_looking_stops_knowing_what_its_ground_is_worth(self):
        """Slice 5's own question, and the reason wear takes richness rather than room.

        Measured across these thirty seeds: a clan that keeps a party out in winter loses 161
        food to numbers gone out of date, and one that stops sending parties the moment its
        ground outruns its hands loses 403. Over 120 seeds that is 2.2 disappointing seasons a
        run against 4.7.

        When wear took *capacity* rather than richness, the same two policies measured 1.2
        against 1.0 and the mechanic taught nothing. This clan is hands-limited (`roadmap.md`,
        the plateau), so a tile losing a forager it never had the people to send costs it
        exactly nothing.
        """
        watchful, settled = 0, 0
        for seed in range(30):
            watchful += _food_lost_to_stale_intel(seed, watchful_orders)
            settled += _food_lost_to_stale_intel(seed, surveying_orders)
        self.assertGreater(
            settled,
            watchful,
            f"settling lost {settled} food to stale intel against {watchful} for keeping a "
            "party out; letting the picture rot costs nothing and the slice does not bite",
        )

    def test_scouting_actually_raises_the_food_ceiling(self):
        # The mechanism behind the outcome, asserted separately so a pass above cannot be
        # coming from somewhere else (a lucky event spread, say).
        for seed in range(12):
            with self.subTest(seed=seed):
                self.assertGreater(
                    play_with(seed, scouting_orders).tiles_known,
                    play_with(seed, homebody_orders).tiles_known,
                )


if __name__ == "__main__":
    print(summarise())
