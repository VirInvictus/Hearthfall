"""The condition evaluator.

A condition is `key op value`. Conditions on an event are AND-ed. That is the whole
language, and `spec.md` §6 is explicit that it stays that way: no OR, no parentheses, no
functions, no arithmetic, until a hundred real events prove the need with evidence rather
than aesthetics.

Conditions are validated at load time against a reference snapshot, so an event naming a
key that does not exist, or ordering a value that cannot be ordered, fails loudly when the
corpus loads instead of silently never matching.
"""

from __future__ import annotations

import operator
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

Snapshot = Mapping[str, int | str]

# Values are validated against a reference snapshot before an operator ever sees them, so
# the comparison is known to be well-typed by the time it runs.
OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
    "==": operator.eq,
    "!=": operator.ne,
    "<=": operator.le,
    ">=": operator.ge,
    "<": operator.lt,
    ">": operator.gt,
}

# Only these work on a string value. Asking whether a season is less than another is a
# content bug, not a question.
EQUALITY_ONLY = frozenset({"==", "!="})


class ConditionError(ValueError):
    """A condition that cannot be parsed or cannot ever be meaningfully evaluated."""


@dataclass(frozen=True)
class Condition:
    key: str
    op: str
    value: int | str

    def __str__(self) -> str:
        return f"{self.key} {self.op} {self.value}"

    def evaluate(self, snapshot: Snapshot) -> bool:
        return OPERATORS[self.op](snapshot[self.key], self.value)


def parse(text: str, reference: Snapshot) -> Condition:
    """Parse one `key op value` clause, validated against a reference snapshot."""
    parts = text.split()
    if len(parts) != 3:
        raise ConditionError(
            f"condition {text!r} is not `key op value` (got {len(parts)} tokens)"
        )

    key, op, raw_value = parts

    if key not in reference:
        known = ", ".join(sorted(reference))
        raise ConditionError(
            f"condition {text!r} names unknown key {key!r}; known: {known}"
        )
    if op not in OPERATORS:
        known = ", ".join(OPERATORS)
        raise ConditionError(
            f"condition {text!r} uses unknown operator {op!r}; known: {known}"
        )

    expected = reference[key]
    if isinstance(expected, str):
        if op not in EQUALITY_ONLY:
            raise ConditionError(
                f"condition {text!r} orders {key!r}, which is text; use == or !="
            )
        return Condition(key=key, op=op, value=raw_value)

    try:
        return Condition(key=key, op=op, value=int(raw_value))
    except ValueError:
        raise ConditionError(
            f"condition {text!r} compares numeric {key!r} against {raw_value!r}"
        ) from None


def parse_all(clauses: list[str], reference: Snapshot) -> tuple[Condition, ...]:
    return tuple(parse(clause, reference) for clause in clauses)


def matches(conditions: tuple[Condition, ...], snapshot: Snapshot) -> bool:
    """True when every condition holds. An empty condition list always matches."""
    return all(condition.evaluate(snapshot) for condition in conditions)
