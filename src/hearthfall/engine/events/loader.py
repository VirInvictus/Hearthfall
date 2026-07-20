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
from dataclasses import dataclass
from importlib import resources

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


@dataclass(frozen=True)
class Event:
    id: str
    title: str
    body: str
    weight: int = 1
    once: bool = False
    when: tuple[Condition, ...] = ()
    options: tuple[ChoiceOption, ...] = ()
    effect: Effect = Effect()

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
        document = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise EventError(f"{source}: not valid TOML: {error}") from error

    unknown = set(document) - {"event"}
    if unknown:
        raise EventError(f"{source}: unknown top-level key(s) {sorted(unknown)}")

    raw_events = document.get("event", [])
    if not isinstance(raw_events, list):
        raise EventError(f"{source}: [[event]] must be an array of tables")

    return [_parse_event(raw, source, reference) for raw in raw_events]


def _parse_event(raw: object, source: str, reference: Snapshot) -> Event:
    if not isinstance(raw, dict):
        raise EventError(f"{source}: each event must be a table")

    identifier = raw.get("id")
    if not isinstance(identifier, str) or not identifier:
        raise EventError(f"{source}: an event is missing a non-empty string id")

    where = f"{source}: event {identifier!r}"

    unknown = set(raw) - EVENT_KEYS
    if unknown:
        raise EventError(f"{where} has unknown key(s) {sorted(unknown)}")

    title = _require_text(raw, "title", where)
    body = _require_text(raw, "body", where)

    weight = raw.get("weight", 1)
    if not isinstance(weight, int) or isinstance(weight, bool) or weight < 1:
        raise EventError(
            f"{where} has weight {weight!r}; it must be an integer above zero"
        )

    once = raw.get("once", False)
    if not isinstance(once, bool):
        raise EventError(f"{where} has once = {once!r}; it must be true or false")

    when = raw.get("when", [])
    if not isinstance(when, list) or not all(
        isinstance(clause, str) for clause in when
    ):
        raise EventError(f"{where} has a `when` that is not a list of strings")
    try:
        conditions = parse_all(when, reference)
    except ValueError as error:
        raise EventError(f"{where}: {error}") from error

    has_choice = "choice" in raw
    has_effect = "effect" in raw
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
            options=_parse_choices(raw["choice"], where),
        )

    return Event(
        id=identifier,
        title=title,
        body=body,
        weight=weight,
        once=once,
        when=conditions,
        effect=_parse_effect(raw.get("effect", {}), where),
    )


def _parse_choices(raw: object, where: str) -> tuple[ChoiceOption, ...]:
    if not isinstance(raw, list) or not raw:
        raise EventError(f"{where} has an empty or malformed [[event.choice]] array")

    options: list[ChoiceOption] = []
    for index, choice in enumerate(raw):
        label = f"{where}, choice {index}"
        if not isinstance(choice, dict):
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
    if not isinstance(raw, dict):
        raise EventError(f"{where} has an effect that is not a table")

    unknown = set(raw) - EFFECT_KEYS
    if unknown:
        known = ", ".join(sorted(EFFECT_KEYS))
        raise EventError(
            f"{where} has unknown effect key(s) {sorted(unknown)}; known: {known}"
        )

    for key, value in raw.items():
        if not isinstance(value, int) or isinstance(value, bool):
            raise EventError(
                f"{where} has effect {key} = {value!r}; it must be an integer"
            )

    return Effect(**raw)


def _require_text(raw: dict[str, object], key: str, where: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EventError(f"{where} is missing a non-empty {key}")
    return value
