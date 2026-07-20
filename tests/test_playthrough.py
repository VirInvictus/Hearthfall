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

from hearthfall.engine import balance, turn
from hearthfall.engine.events.loader import load_corpus
from hearthfall.engine.rng import Rng
from hearthfall.engine.state import Orders, Outcome

CORPUS = load_corpus(turn.new_game(0).snapshot())


def steady_orders(state) -> Orders:
    """A plain, defensible policy: keep a scouting party and a tender, forage with the rest.

    Not a good player. Good enough that a run which still starves says something about the
    balance rather than about the policy.
    """
    adults = state.population.adults
    explore = (
        balance.EXPLORERS_PER_REVEAL if adults >= 5 and state.world.frontier() else 0
    )
    tend = 1 if adults - explore >= 3 else 0
    return Orders(forage=adults - explore - tend, explore=explore, tend=tend)


@dataclass
class Transcript:
    outcome: Outcome | None
    turns: int
    survivors: int
    food: int
    tiles_known: int
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
        tiles_known=state.world.known_count,
        events=events,
        lines=lines,
    )


def summarise(seeds: range = range(50)) -> dict[Outcome, int]:
    tally: dict[Outcome, int] = {Outcome.ENDURED: 0, Outcome.BURIED: 0}
    for seed in seeds:
        tally[play(seed).outcome] += 1
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


if __name__ == "__main__":
    print(summarise())
