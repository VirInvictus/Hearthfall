"""Turn TOML into events, and refuse anything malformed.

Validation here is deliberately strict and deliberately loud. The corpus is heading for
hundreds of entries, and the worst possible failure mode is a typo that quietly does
nothing: an event with a misspelled effect key that never moves a number, or a condition
naming a field that no longer exists so the event simply never fires. Either would look
exactly like content that needs rewriting. So every unknown key is an error at load.

Parsing is pure. Reading files is a thin wrapper over it, kept separate so the rules can be
tested without touching a disk.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from importlib import resources
from typing import cast

from hearthfall.engine.events.conditions import Condition, Snapshot, parse_all
from hearthfall.engine.state import ChoiceOption, Effect

EVENT_KEYS = frozenset(
    {"id", "weight", "once", "when", "title", "body", "effect", "choice"}
)
CHOICE_KEYS = frozenset({"text", "effect"})
EFFECT_KEYS = frozenset({"food", "morale", "adults", "children"})

DATA_PACKAGE = "hearthfall.data"
EVENTS_DIRECTORY = "events"


class EventError(ValueError):
    """Malformed content. Always names the source and the event it came from."""


# `tomllib` always produces str-keyed tables, but a `dict` narrowed from `object` reads as
# `dict[Unknown, Unknown]` to a strict type checker, and that unknown then leaks into every
# rule below. These two do the narrowing once so the parse rules stay about content rather
# than about types. The casts are safe by the TOML grammar: keys are strings, always.
def _as_table(value: object) -> dict[str, object] | None:
    return cast("dict[str, object]", value) if isinstance(value, dict) else None


def _as_array(value: object) -> list[object] | None:
    return cast("list[object]", value) if isinstance(value, list) else None


@dataclass(frozen=True, slots=True)
class Event:
    id: str
    title: str
    body: str
    weight: int = 1
    once: bool = False
    when: tuple[Condition, ...] = ()
    options: tuple[ChoiceOption, ...] = ()
    effect: Effect = field(default_factory=Effect)

    @property
    def has_choices(self) -> bool:
        return bool(self.options)


def load_corpus(reference: Snapshot) -> list[Event]:
    """Read and parse every shipped event file.

    This is the one function in the engine that touches storage. It reads through
    `importlib.resources` so an installed wheel works the same as a source checkout.
    """
    directory = resources.files(DATA_PACKAGE).joinpath(EVENTS_DIRECTORY)
    documents = {
        entry.name: entry.read_text(encoding="utf-8")
        for entry in sorted(directory.iterdir(), key=lambda entry: entry.name)
        if entry.name.endswith(".toml")
    }
    return parse_corpus(documents, reference)


def parse_corpus(documents: Mapping[str, str], reference: Snapshot) -> list[Event]:
    """Parse several TOML documents into one corpus, rejecting duplicate ids."""
    events: list[Event] = []
    seen: dict[str, str] = {}

    for source, text in documents.items():
        for event in parse_document(text, source, reference):
            if event.id in seen:
                raise EventError(
                    f"{source}: event id {event.id!r} already defined in {seen[event.id]}"
                )
            seen[event.id] = source
            events.append(event)

    return events


def parse_document(text: str, source: str, reference: Snapshot) -> list[Event]:
    try:
        document: dict[str, object] = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise EventError(f"{source}: not valid TOML: {error}") from error

    unknown = set(document) - {"event"}
    if unknown:
        raise EventError(f"{source}: unknown top-level key(s) {sorted(unknown)}")

    raw_events = _as_array(document.get("event", []))
    if raw_events is None:
        raise EventError(f"{source}: [[event]] must be an array of tables")

    return [_parse_event(raw, source, reference) for raw in raw_events]


def _parse_event(raw: object, source: str, reference: Snapshot) -> Event:
    table = _as_table(raw)
    if table is None:
        raise EventError(f"{source}: each event must be a table")

    identifier = table.get("id")
    if not isinstance(identifier, str) or not identifier:
        raise EventError(f"{source}: an event is missing a non-empty string id")

    where = f"{source}: event {identifier!r}"

    unknown = set(table) - EVENT_KEYS
    if unknown:
        raise EventError(f"{where} has unknown key(s) {sorted(unknown)}")

    title = _require_text(table, "title", where)
    body = _require_text(table, "body", where)

    weight = table.get("weight", 1)
    if not isinstance(weight, int) or isinstance(weight, bool) or weight < 1:
        raise EventError(
            f"{where} has weight {weight!r}; it must be an integer above zero"
        )

    once = table.get("once", False)
    if not isinstance(once, bool):
        raise EventError(f"{where} has once = {once!r}; it must be true or false")

    raw_when = _as_array(table.get("when", []))
    if raw_when is None:
        raise EventError(f"{where} has a `when` that is not a list of strings")
    when: list[str] = []
    for clause in raw_when:
        if not isinstance(clause, str):
            raise EventError(f"{where} has a `when` that is not a list of strings")
        when.append(clause)
    try:
        conditions = parse_all(when, reference)
    except ValueError as error:
        raise EventError(f"{where}: {error}") from error

    has_choice = "choice" in table
    has_effect = "effect" in table
    if has_choice and has_effect:
        raise EventError(
            f"{where} has both choices and a top-level effect; "
            "an event either asks a question or simply happens"
        )

    if has_choice:
        return Event(
            id=identifier,
            title=title,
            body=body,
            weight=weight,
            once=once,
            when=conditions,
            options=_parse_choices(table["choice"], where),
        )

    return Event(
        id=identifier,
        title=title,
        body=body,
        weight=weight,
        once=once,
        when=conditions,
        effect=_parse_effect(table.get("effect", {}), where),
    )


def _parse_choices(raw: object, where: str) -> tuple[ChoiceOption, ...]:
    array = _as_array(raw)
    if array is None or not array:
        raise EventError(f"{where} has an empty or malformed [[event.choice]] array")

    options: list[ChoiceOption] = []
    for index, entry in enumerate(array):
        label = f"{where}, choice {index}"
        choice = _as_table(entry)
        if choice is None:
            raise EventError(f"{label} is not a table")

        unknown = set(choice) - CHOICE_KEYS
        if unknown:
            raise EventError(f"{label} has unknown key(s) {sorted(unknown)}")

        options.append(
            ChoiceOption(
                text=_require_text(choice, "text", label),
                effect=_parse_effect(choice.get("effect", {}), label),
            )
        )

    return tuple(options)


def _parse_effect(raw: object, where: str) -> Effect:
    table = _as_table(raw)
    if table is None:
        raise EventError(f"{where} has an effect that is not a table")

    unknown = set(table) - EFFECT_KEYS
    if unknown:
        known = ", ".join(sorted(EFFECT_KEYS))
        raise EventError(
            f"{where} has unknown effect key(s) {sorted(unknown)}; known: {known}"
        )

    # Validating and collecting in one pass, so what reaches Effect is already int-typed.
    # `bool` is excluded explicitly because it is an int subclass, and `food = true` should
    # be a content error rather than a silent 1.
    deltas: dict[str, int] = {}
    for key, value in table.items():
        if not isinstance(value, int) or isinstance(value, bool):
            raise EventError(
                f"{where} has effect {key} = {value!r}; it must be an integer"
            )
        deltas[key] = value

    return Effect(**deltas)


def _require_text(raw: dict[str, object], key: str, where: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EventError(f"{where} is missing a non-empty {key}")
    return value
