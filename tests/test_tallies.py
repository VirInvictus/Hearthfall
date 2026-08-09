"""The tallies: what the clan remembers, and why a typo cannot hide in it.

A tally is one integer that survives the whole run, written by event effects and read by event
conditions as `tally_<name>`. That is the whole mechanism, and it is what lets the corpus have
a memory without the condition evaluator growing by a single line: `spec.md` §6 and decision 5
of the replan both say the evaluator stays `key op value`, and `snapshot()` is where new
questions are allowed to appear.

The half of this worth testing hardest is not the arithmetic, it is the strictness. A tally
written under a misspelled name would increment a counter no condition ever reads, and content
that looks authored but does nothing is indistinguishable from content that needs rewriting.
"""

from __future__ import annotations

import unittest

from hearthfall.engine import turn
from hearthfall.engine.events.loader import (
    EventError,
    load_tallies,
    parse_corpus,
    parse_tallies,
)
from hearthfall.engine.state import Effect

TALLIES = ("elder_resentment", "elder_standing")


def a_state():
    return turn.new_game(1, tallies=TALLIES)


def reference():
    return a_state().snapshot()


def one_event(body: str):
    return parse_corpus({"test.toml": body}, reference())


class TestTheRegistry(unittest.TestCase):
    def test_declared_tallies_start_at_zero_and_are_all_present(self):
        state = a_state()
        self.assertEqual(state.tallies, {"elder_resentment": 0, "elder_standing": 0})

    def test_the_shipped_registry_parses(self):
        self.assertIn("elder_resentment", load_tallies())

    def test_a_tally_declared_twice_is_an_error(self):
        with self.assertRaises(EventError) as caught:
            parse_tallies(
                '[[tally]]\nname = "a"\n[[tally]]\nname = "a"\n', "tallies.toml"
            )
        self.assertIn("declared twice", str(caught.exception))

    def test_an_unknown_key_in_the_registry_is_an_error(self):
        with self.assertRaises(EventError):
            parse_tallies('[[tally]]\nname = "a"\ndescription = "x"\n', "tallies.toml")


class TestWritingATally(unittest.TestCase):
    def test_an_effect_moves_the_counter(self):
        state = a_state()
        turn.apply_effect(state, Effect(tally=(("elder_resentment", 3),)))
        self.assertEqual(state.tallies["elder_resentment"], 3)

    def test_deltas_accumulate_across_a_run(self):
        state = a_state()
        for _ in range(3):
            turn.apply_effect(state, Effect(tally=(("elder_resentment", 2),)))
        self.assertEqual(state.tallies["elder_resentment"], 6)

    def test_a_tally_never_goes_below_zero(self):
        # A negative grudge is not forgiveness, it is an event with the sign wrong. Clamping
        # here means a mending choice cannot bank credit against a future slight.
        state = a_state()
        turn.apply_effect(state, Effect(tally=(("elder_resentment", 2),)))
        turn.apply_effect(state, Effect(tally=(("elder_resentment", -9),)))
        self.assertEqual(state.tallies["elder_resentment"], 0)

    def test_an_effect_carrying_only_a_tally_is_not_empty(self):
        # `_draw_event` skips an empty effect, so a purely book-keeping event would silently
        # never write its tally if this were wrong.
        self.assertFalse(Effect(tally=(("elder_resentment", 1),)).is_empty)

    def test_the_snapshot_exposes_it_under_a_prefix(self):
        state = a_state()
        turn.apply_effect(state, Effect(tally=(("elder_standing", 4),)))
        self.assertEqual(state.snapshot()["tally_elder_standing"], 4)


class TestUndeclaredTalliesFailLoudly(unittest.TestCase):
    """The whole reason the registry exists."""

    def test_writing_an_undeclared_tally_is_a_load_error(self):
        with self.assertRaises(EventError) as caught:
            one_event("""
[[event]]
id = "x"
title = "T"
body = "B"
[event.effect.tally]
elder_resentmnt = 1
""")
        message = str(caught.exception)
        self.assertIn("undeclared tally", message)
        self.assertIn(
            "elder_resentment", message, "the error should suggest the real one"
        )

    def test_reading_an_undeclared_tally_is_a_load_error(self):
        # This one comes free from condition validation, but it is asserted here so the two
        # halves are seen to be guarded by the same reference snapshot.
        with self.assertRaises(EventError):
            one_event("""
[[event]]
id = "x"
title = "T"
body = "B"
when = ["tally_nonesuch > 1"]
""")

    def test_a_tally_must_be_an_integer(self):
        with self.assertRaises(EventError):
            one_event("""
[[event]]
id = "x"
title = "T"
body = "B"
[event.effect.tally]
elder_resentment = "lots"
""")

    def test_a_declared_tally_loads_from_both_an_effect_and_a_condition(self):
        events = one_event("""
[[event]]
id = "writes"
title = "T"
body = "B"
[event.effect.tally]
elder_resentment = 2

[[event]]
id = "reads"
title = "T"
body = "B"
when = ["tally_elder_resentment > 1"]
""")
        self.assertEqual(events[0].effect.tally, (("elder_resentment", 2),))
        self.assertEqual(str(events[1].when[0]), "tally_elder_resentment > 1")


class TestAChainRemembersTheAnswerAndNotJustTheEvent(unittest.TestCase):
    """The point of the whole slice.

    A chain gated on `fired_events` could only ask whether something happened. Gating on a
    tally written by a *choice* asks how you answered, which is the difference between a
    corpus with a memory and one with a checklist.
    """

    CORPUS = """
[[event]]
id = "slight"
title = "T"
body = "B"
[[event.choice]]
text = "Overrule him."
[event.choice.effect.tally]
elder_resentment = 3
[[event.choice]]
text = "Defer."
[event.choice.effect.tally]
elder_standing = 2

[[event]]
id = "consequence"
title = "T"
body = "B"
when = ["tally_elder_resentment > 2"]
"""

    def eligible_after(self, index: int) -> bool:
        from hearthfall.engine.events import table

        events = parse_corpus({"c.toml": self.CORPUS}, reference())
        slight = next(e for e in events if e.id == "slight")
        consequence = next(e for e in events if e.id == "consequence")

        state = a_state()
        turn.apply_effect(state, slight.options[index].effect)
        return bool(table.eligible([consequence], state.snapshot(), already_fired=[]))

    def test_the_answer_that_slights_him_opens_the_consequence(self):
        self.assertTrue(self.eligible_after(0))

    def test_the_answer_that_defers_does_not(self):
        self.assertFalse(self.eligible_after(1))


if __name__ == "__main__":
    unittest.main()
