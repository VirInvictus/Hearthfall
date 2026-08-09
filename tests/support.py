"""Narrowing helpers shared by the test modules.

Two of the engine's deliberate design choices produce optional and union types that a test
then has to unwrap: `table.draw` returns `Event | None` because a quiet turn is not an error,
and `snapshot()` values are `int | str` because that union is exactly what keeps the condition
evaluator to fifty lines. Both are correct, and both mean a test that asserts on the value has
to say so.

`assertIsNotNone` does not narrow a type, so without these every such test either carries a
redundant second assertion or an ignore comment. These raise on the bad case, so a test that
was wrong still fails loudly rather than passing on a None.
"""

from __future__ import annotations


def not_none[T](value: T | None) -> T:
    """Assert a value is present and hand it back with the Optional stripped."""
    if value is None:
        raise AssertionError("expected a value, got None")
    return value


def an_int(value: int | str) -> int:
    """Read a snapshot value that must be numeric."""
    if isinstance(value, str):
        # AssertionError, not TypeError: this is a test helper, and a snapshot key that has
        # turned into a string is a failed assertion about the engine rather than a caller
        # passing the wrong thing.
        raise AssertionError(f"expected an integer, got {value!r}")  # noqa: TRY004
    return value
