"""Unit types, and the groups assembled from them.

`spec.md` §5 calls the AoE2 layer dessert, not the meal, so this module is
deliberately the smallest thing that makes composition real: a type is two
numbers (`strength`, what it adds when its side presses; `guard`, what it adds
when its side holds), and a group is counts per type. The tension is the
decision: a type good at one thing is not good at the other, so *who* holds
the line matters and not just *how many*.

Parsing is pure and reading files is a thin wrapper, mirroring the event
loader, so the rules can be tested without touching a disk. Like tallies, the
shipped table is the only place a type is declared: a composition naming an
undeclared type is an error at resolve time, not a silent zero.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from typing import cast

DATA_PACKAGE = "hearthfall.data"
UNITS_FILE = "units.toml"
UNIT_KEYS = frozenset({"name", "strength", "guard", "about"})

# A registry of declared types, keyed by type id. Injected wherever a
# composition is priced, the way half-lives are injected into a ledger: the
# engine reads the numbers it is handed, never the disk.
UnitDefs = Mapping[str, "UnitDef"]


class UnitError(ValueError):
    """Malformed unit content. Names the source and the type it came from."""


@dataclass(frozen=True, slots=True)
class UnitDef:
    """One declared type. A value: two numbers, a name, and a line of prose."""

    key: str
    name: str
    strength: int
    guard: int
    about: str = ""


@dataclass(frozen=True, slots=True)
class Composition:
    """A group assembled from types: counts per type id, nothing more.

    The counts are a sorted tuple of pairs rather than a dict so the value is
    genuinely immutable and two compositions built from the same table compare
    equal, the same shape `Effect.tally` uses. Pricing goes through
    `strength`/`guard`, which take the registry as an argument: a composition
    is counts, and the numbers live in the declared types.
    """

    counts: tuple[tuple[str, int], ...] = ()

    @classmethod
    def of(cls, counts: Mapping[str, int]) -> Composition:
        """Build from a mapping. Zero and negative counts are dropped, so a
        caller can pass a full order and let the empty lines fall away."""
        return Composition(
            counts=tuple(
                sorted((key, count) for key, count in counts.items() if count > 0)
            )
        )

    def count(self, key: str) -> int:
        return dict(self.counts).get(key, 0)

    def total(self) -> int:
        return sum(count for _, count in self.counts)

    def strength(self, defs: UnitDefs) -> int:
        """What the group adds when its side presses."""
        return self._total(defs, "strength")

    def guard(self, defs: UnitDefs) -> int:
        """What the group adds when its side holds."""
        return self._total(defs, "guard")

    def _total(self, defs: UnitDefs, stat: str) -> int:
        total = 0
        for key, count in self.counts:
            unit = defs.get(key)
            if unit is None:
                raise ValueError(
                    f"composition names {key!r}, which no declared unit type answers"
                )
            total += count * getattr(unit, stat)
        return total


def load_units() -> dict[str, UnitDef]:
    """Read the shipped unit table. The storage half of the loader."""
    text = (
        resources.files(DATA_PACKAGE).joinpath(UNITS_FILE).read_text(encoding="utf-8")
    )
    return parse_units(text, UNITS_FILE)


def parse_units(text: str, source: str) -> dict[str, UnitDef]:
    """Parse the unit registry, rejecting anything malformed or undeclared.

    Validation is strict for the same reason the event loader's is: a typo
    that quietly prices a spear as a bow is exactly the failure mode that
    looks, seasons later, like balance that needs rewriting.
    """
    try:
        document: dict[str, object] = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise UnitError(f"{source}: not valid TOML: {error}") from error

    unknown = set(document) - {"unit"}
    if unknown:
        raise UnitError(f"{source}: unknown top-level key(s) {sorted(unknown)}")

    table = cast("dict[str, object]", document.get("unit", {}))
    defs: dict[str, UnitDef] = {}
    for key, entry in table.items():
        fields = cast("dict[str, object]", entry) if isinstance(entry, dict) else None
        if fields is None:
            raise UnitError(f"{source}: [unit.{key}] must be a table")
        extra = set(fields) - UNIT_KEYS
        if extra:
            raise UnitError(
                f"{source}: [unit.{key}] has unknown key(s) {sorted(extra)}"
            )
        name = fields.get("name")
        if not isinstance(name, str) or not name:
            raise UnitError(f"{source}: [unit.{key}] needs a non-empty name")
        strength = fields.get("strength")
        guard = fields.get("guard")
        if not isinstance(strength, int) or isinstance(strength, bool):
            raise UnitError(f"{source}: [unit.{key}] strength must be a whole number")
        if not isinstance(guard, int) or isinstance(guard, bool):
            raise UnitError(f"{source}: [unit.{key}] guard must be a whole number")
        if strength < 0 or guard < 0:
            raise UnitError(
                f"{source}: [unit.{key}] strength and guard cannot be negative"
            )
        about = fields.get("about", "")
        if not isinstance(about, str):
            raise UnitError(f"{source}: [unit.{key}] about must be prose")
        defs[key] = UnitDef(
            key=key, name=name, strength=strength, guard=guard, about=about
        )
    return defs
