"""The event loader and the draw.

The loader's job is to be strict. Every test in TestRejection describes a typo that would
otherwise produce content that looks authored and does nothing.
"""

from __future__ import annotations

import unittest

from hearthfall.engine.events import table
from hearthfall.engine.events.loader import (
    Event,
    EventError,
    parse_corpus,
    parse_document,
)
from hearthfall.engine.rng import Rng
from hearthfall.engine.state import Effect

REFERENCE = {"food": 30, "morale": 5, "season": "spring", "turn": 0}

FLAVOR = """
[[event]]
id = "quiet.frost"
title = "First Frost"
body = "The puddles hold their shape until noon."
weight = 2
when = ["season == spring"]

[event.effect]
morale = -1
"""

FORK = """
[[event]]
id = "winter.granary_rats"
title = "Something in the Grain"
body = "The stores are lighter than the tally says."

  [[event.choice]]
  text = "Set the children to hunting them."
  [event.choice.effect]
  food = -5
  morale = -1

  [[event.choice]]
  text = "Do nothing."
  [event.choice.effect]
  food = -12
"""


def parse_one(text: str) -> Event:
    events = parse_document(text, "test.toml", REFERENCE)
    assert len(events) == 1
    return events[0]


class TestParsing(unittest.TestCase):
    def test_a_flavor_event_carries_its_effect(self):
        event = parse_one(FLAVOR)
        self.assertEqual(event.id, "quiet.frost")
        self.assertEqual(event.title, "First Frost")
        self.assertEqual(event.weight, 2)
        self.assertEqual(event.effect, Effect(morale=-1))
        self.assertFalse(event.has_choices)
        self.assertEqual(len(event.when), 1)

    def test_a_fork_carries_its_options(self):
        event = parse_one(FORK)
        self.assertTrue(event.has_choices)
        self.assertEqual(len(event.options), 2)
        self.assertEqual(event.options[0].effect, Effect(food=-5, morale=-1))
        self.assertEqual(event.options[1].effect, Effect(food=-12))

    def test_defaults_are_sane(self):
        event = parse_one(FORK)
        self.assertEqual(event.weight, 1)
        self.assertFalse(event.once)
        self.assertEqual(event.when, ())

    def test_several_documents_make_one_corpus(self):
        corpus = parse_corpus({"a.toml": FLAVOR, "b.toml": FORK}, REFERENCE)
        self.assertEqual(
            [event.id for event in corpus], ["quiet.frost", "winter.granary_rats"]
        )

    def test_an_empty_document_is_legal(self):
        self.assertEqual(parse_document("", "empty.toml", REFERENCE), [])


class TestRejection(unittest.TestCase):
    def assert_refused(self, text: str, *, mentioning: str = ""):
        with self.assertRaises(EventError) as caught:
            parse_document(text, "test.toml", REFERENCE)
        if mentioning:
            self.assertIn(mentioning, str(caught.exception))

    def test_an_unknown_effect_key_is_refused(self):
        # The typo this catches: `moral = -1` would parse fine and change nothing.
        self.assert_refused(
            '[[event]]\nid = "a"\ntitle = "T"\nbody = "B"\n[event.effect]\nmoral = -1\n',
            mentioning="moral",
        )

    def test_an_unknown_event_key_is_refused(self):
        self.assert_refused(
            '[[event]]\nid = "a"\ntitle = "T"\nbody = "B"\nwieght = 3\n',
            mentioning="wieght",
        )

    def test_an_unknown_choice_key_is_refused(self):
        self.assert_refused(
            '[[event]]\nid = "a"\ntitle = "T"\nbody = "B"\n'
            '[[event.choice]]\ntext = "x"\neffects = {}\n',
            mentioning="effects",
        )

    def test_an_unknown_top_level_key_is_refused(self):
        self.assert_refused('[[events]]\nid = "a"\n', mentioning="events")

    def test_a_missing_id_is_refused(self):
        self.assert_refused('[[event]]\ntitle = "T"\nbody = "B"\n', mentioning="id")

    def test_a_missing_title_or_body_is_refused(self):
        self.assert_refused('[[event]]\nid = "a"\nbody = "B"\n', mentioning="title")
        self.assert_refused('[[event]]\nid = "a"\ntitle = "T"\n', mentioning="body")

    def test_a_blank_title_is_refused(self):
        self.assert_refused('[[event]]\nid = "a"\ntitle = "  "\nbody = "B"\n')

    def test_a_bad_weight_is_refused(self):
        for weight in ["0", "-2", '"three"', "true"]:
            self.assert_refused(
                f'[[event]]\nid = "a"\ntitle = "T"\nbody = "B"\nweight = {weight}\n'
            )

    def test_a_non_integer_effect_is_refused(self):
        self.assert_refused(
            '[[event]]\nid = "a"\ntitle = "T"\nbody = "B"\n[event.effect]\nfood = 1.5\n'
        )

    def test_a_bad_condition_is_refused_with_the_event_named(self):
        self.assert_refused(
            '[[event]]\nid = "a"\ntitle = "T"\nbody = "B"\nwhen = ["stores > 1"]\n',
            mentioning="'a'",
        )

    def test_an_event_cannot_both_ask_and_happen(self):
        self.assert_refused(
            '[[event]]\nid = "a"\ntitle = "T"\nbody = "B"\n'
            "[event.effect]\nfood = 1\n"
            '[[event.choice]]\ntext = "x"\n',
            mentioning="both",
        )

    def test_an_empty_choice_list_is_refused(self):
        self.assert_refused(
            '[[event]]\nid = "a"\ntitle = "T"\nbody = "B"\nchoice = []\n'
        )

    def test_invalid_toml_is_refused(self):
        self.assert_refused("[[event]\nid =", mentioning="TOML")

    def test_duplicate_ids_across_files_are_refused(self):
        with self.assertRaises(EventError) as caught:
            parse_corpus({"a.toml": FLAVOR, "b.toml": FLAVOR}, REFERENCE)
        self.assertIn("quiet.frost", str(caught.exception))


class TestEligibility(unittest.TestCase):
    def setUp(self):
        self.spring = parse_one(FLAVOR)
        self.always = parse_one(FORK)
        self.corpus = [self.spring, self.always]

    def test_conditions_gate_eligibility(self):
        summer = dict(REFERENCE, season="summer")
        self.assertEqual(table.eligible(self.corpus, summer), [self.always])
        self.assertEqual(len(table.eligible(self.corpus, REFERENCE)), 2)

    def test_a_once_event_is_dropped_after_firing(self):
        once = Event(id="unique", title="T", body="B", once=True)
        self.assertEqual(table.eligible([once], REFERENCE), [once])
        self.assertEqual(
            table.eligible([once], REFERENCE, already_fired=["unique"]), []
        )

    def test_a_repeatable_event_survives_firing(self):
        repeatable = Event(id="again", title="T", body="B")
        self.assertEqual(
            table.eligible([repeatable], REFERENCE, already_fired=["again"]),
            [repeatable],
        )


class TestDraw(unittest.TestCase):
    def test_an_empty_corpus_draws_nothing(self):
        self.assertIsNone(table.draw([], REFERENCE, Rng(1)))

    def test_a_corpus_of_spent_events_draws_nothing(self):
        spent = Event(id="w", title="T", body="B", once=True)
        self.assertIsNone(table.draw([spent], REFERENCE, Rng(1), already_fired=["w"]))

    def test_the_same_seed_draws_the_same_event(self):
        corpus = [Event(id=str(index), title="T", body="B") for index in range(10)]
        self.assertEqual(
            table.draw(corpus, REFERENCE, Rng(3)).id,
            table.draw(corpus, REFERENCE, Rng(3)).id,
        )

    def test_weight_biases_the_draw(self):
        corpus = [
            Event(id="rare", title="T", body="B", weight=1),
            Event(id="common", title="T", body="B", weight=19),
        ]
        rng = Rng(2026)
        drawn = [table.draw(corpus, REFERENCE, rng).id for _ in range(500)]
        self.assertGreater(drawn.count("common"), drawn.count("rare") * 5)


class TestShippedCorpus(unittest.TestCase):
    def test_the_shipped_corpus_loads_and_validates(self):
        from hearthfall.engine import turn
        from hearthfall.engine.events.loader import load_corpus

        corpus = load_corpus(turn.new_game(1).snapshot())
        self.assertGreaterEqual(
            len(corpus), 20, "Phase 0 wants a corpus of about twenty"
        )

    def test_every_shipped_event_has_a_unique_id(self):
        from hearthfall.engine import turn
        from hearthfall.engine.events.loader import load_corpus

        corpus = load_corpus(turn.new_game(1).snapshot())
        self.assertEqual(len({event.id for event in corpus}), len(corpus))


if __name__ == "__main__":
    unittest.main()
