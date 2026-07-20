"""The condition evaluator, and the validation that keeps bad content out of the corpus."""

from __future__ import annotations

import unittest

from hearthfall.engine.events.conditions import (
    Condition,
    ConditionError,
    matches,
    parse,
    parse_all,
)

REFERENCE = {"food": 30, "morale": 5, "season": "spring", "turn": 0}


class TestParsing(unittest.TestCase):
    def test_a_numeric_clause_parses_its_value_as_a_number(self):
        self.assertEqual(parse("food > 20", REFERENCE), Condition("food", ">", 20))

    def test_a_text_clause_keeps_its_value_as_text(self):
        self.assertEqual(
            parse("season == winter", REFERENCE), Condition("season", "==", "winter")
        )

    def test_every_operator_is_accepted(self):
        for op in ["==", "!=", "<", "<=", ">", ">="]:
            self.assertEqual(parse(f"food {op} 10", REFERENCE).op, op)

    def test_parse_all_returns_a_condition_per_clause(self):
        conditions = parse_all(["food > 20", "season == spring"], REFERENCE)
        self.assertEqual(len(conditions), 2)


class TestValidation(unittest.TestCase):
    def test_an_unknown_key_is_refused(self):
        # The failure this prevents: an event that silently never fires for the whole life
        # of the corpus because it tests a field that does not exist.
        with self.assertRaises(ConditionError) as caught:
            parse("stores > 20", REFERENCE)
        self.assertIn("stores", str(caught.exception))

    def test_an_unknown_operator_is_refused(self):
        with self.assertRaises(ConditionError):
            parse("food => 20", REFERENCE)

    def test_a_malformed_clause_is_refused(self):
        for clause in ["food", "food >", "food > 20 or morale > 3", ""]:
            with self.assertRaises(ConditionError):
                parse(clause, REFERENCE)

    def test_ordering_a_text_field_is_refused(self):
        # "Is spring less than winter" is a content bug, not a question.
        for op in ["<", "<=", ">", ">="]:
            with self.assertRaises(ConditionError):
                parse(f"season {op} winter", REFERENCE)

    def test_comparing_a_numeric_field_against_text_is_refused(self):
        with self.assertRaises(ConditionError):
            parse("food > plenty", REFERENCE)

    def test_a_negative_threshold_is_legal(self):
        self.assertEqual(parse("morale > -1", REFERENCE).value, -1)


class TestEvaluation(unittest.TestCase):
    def test_numeric_comparisons(self):
        snapshot = {"food": 30, "morale": 5, "season": "spring", "turn": 0}
        for clause, expected in [
            ("food > 20", True),
            ("food > 30", False),
            ("food >= 30", True),
            ("food < 40", True),
            ("food <= 29", False),
            ("food == 30", True),
            ("food != 30", False),
        ]:
            self.assertIs(parse(clause, REFERENCE).evaluate(snapshot), expected, clause)

    def test_text_comparisons(self):
        snapshot = dict(REFERENCE)
        self.assertTrue(parse("season == spring", REFERENCE).evaluate(snapshot))
        self.assertFalse(parse("season == winter", REFERENCE).evaluate(snapshot))
        self.assertTrue(parse("season != winter", REFERENCE).evaluate(snapshot))

    def test_conditions_are_anded(self):
        snapshot = dict(REFERENCE)
        both = parse_all(["food > 20", "season == spring"], REFERENCE)
        one = parse_all(["food > 20", "season == winter"], REFERENCE)
        self.assertTrue(matches(both, snapshot))
        self.assertFalse(matches(one, snapshot))

    def test_no_conditions_always_match(self):
        self.assertTrue(matches((), dict(REFERENCE)))


if __name__ == "__main__":
    unittest.main()
