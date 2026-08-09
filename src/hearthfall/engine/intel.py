"""The fact ledger: what we know, when we learned it, and how far to trust it.

`spec.md` §1 makes this the spine module. The generalisation it encodes is that fog is not a
property of a tile, it is a property of a *fact*. "Have we walked there" and "how many spears
did Stonefold field when we last looked" are then the same question asked of the same
structure, which is what makes five tiers of play one loop instead of five systems.

A fact has three things and no more: a value, the turn we learned it, and a kind that decides
how fast it rots. Terrain never rots, because ground does not move. That case is what lets the
old boolean fog keep working unchanged underneath all of this.

Half-lives arrive as an argument rather than being read from `balance`, for the same reason
`world.py` takes its terrain weights: it keeps the import graph acyclic. `balance` imports
`state`, and `state` owns a Ledger, so a Ledger that imported `balance` would close the loop.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from hearthfall.engine.world import Coord, World

# A fact hangs off either a place or a named thing. Tiles are all Phase 1 needs; the named
# form exists now so sub-project 4 does not have to reshape the keys to add neighbours.
Subject = Coord | str


class FactKind(StrEnum):
    TERRAIN = "terrain"  # what the ground is. never goes stale.
    FORAGE = "forage"  # what can be taken from it. rots slowly.
    PRESENCE = "presence"  # who or what was there. rots fast.


class Staleness(StrEnum):
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"
    NEVER = "never"  # not a degree of trust: we have never looked


@dataclass(frozen=True, slots=True)
class Fact:
    kind: FactKind
    subject: Subject
    value: int | str
    learned_turn: int


def _key(kind: FactKind, subject: Subject) -> str:
    """Namespace places and names apart.

    The separators differ so that the tile (1, 2) and a neighbour unluckily called "1,2"
    cannot overwrite each other. A test asserts it, because the collision would be silent
    and would look like a fact spontaneously changing value.
    """
    if isinstance(subject, tuple):
        x, y = subject
        return f"{kind}@{x},{y}"
    return f"{kind}#{subject}"


@dataclass(slots=True)
class Ledger:
    """Everything the clan believes, and when it last checked.

    Belief, not truth. The world may have moved on; that gap is the game.
    """

    # A None half-life means the fact never goes stale.
    halflives: Mapping[FactKind, int | None]
    facts: dict[str, Fact] = field(default_factory=dict[str, Fact])

    # --- Learning and recall ------------------------------------------------------------

    def learn(
        self, kind: FactKind, subject: Subject, value: int | str, turn: int
    ) -> Fact:
        """Record what we saw. Looking again overwrites, and resets the clock.

        Returns the fact it stored, so a caller can hand what was learned straight to a report
        without going back to the ledger to ask what it just put there.
        """
        fact = Fact(kind=kind, subject=subject, value=value, learned_turn=turn)
        self.facts[_key(kind, subject)] = fact
        return fact

    def fact(self, kind: FactKind, subject: Subject) -> Fact | None:
        return self.facts.get(_key(kind, subject))

    def knows(self, kind: FactKind, subject: Subject) -> bool:
        return _key(kind, subject) in self.facts

    def value(
        self, kind: FactKind, subject: Subject, default: int | str | None = None
    ) -> int | str | None:
        found = self.fact(kind, subject)
        return found.value if found is not None else default

    def age(self, kind: FactKind, subject: Subject, now: int) -> int | None:
        """Seasons since we looked. None means we never have."""
        found = self.fact(kind, subject)
        return None if found is None else now - found.learned_turn

    def staleness(self, kind: FactKind, subject: Subject, now: int) -> Staleness:
        """How far to trust what we hold.

        Two half-lives wide rather than a single cutoff, so the UI has a middle band to
        show. A fact that flips straight from trustworthy to worthless gives the player no
        warning and therefore no decision; the warning *is* the decision.
        """
        age = self.age(kind, subject, now)
        if age is None:
            return Staleness.NEVER

        halflife = self.halflives.get(kind)
        if halflife is None:
            return Staleness.FRESH
        if age <= halflife:
            return Staleness.FRESH
        if age <= halflife * 2:
            return Staleness.AGING
        return Staleness.STALE

    # --- The map, as the ledger's first client -------------------------------------------

    def reveal(self, world: World, coord: Coord, turn: int) -> Fact:
        """Walk onto a tile and learn what the ground is."""
        return self.learn(FactKind.TERRAIN, coord, world.tile(coord).terrain, turn)

    def survey(self, coord: Coord, capacity: int, turn: int) -> Fact:
        """Stop on a tile and work out how much of it the clan can actually work.

        The second rung of slice 3's gradient. Walking a tile answers *what* it is; surveying
        it answers *how many hands it will take*, which is the number the food math is
        bounded by. The capacity arrives as an argument for the same reason the half-lives
        do: it comes from `balance`, and `balance` imports `state`, which owns a Ledger.

        Surveying the same ground again is legal and resets the clock, which is what makes it
        a standing cost rather than a box to tick once a FORAGE fact can go stale.
        """
        return self.learn(FactKind.FORAGE, coord, capacity, turn)

    def revealed(self) -> list[Coord]:
        """Tiles whose terrain we have learned, sorted for determinism.

        Only terrain counts. Seeing smoke over a ridge is a PRESENCE fact and does not mean
        anyone has walked the ground.
        """
        return sorted(
            fact.subject
            for fact in self.facts.values()
            if fact.kind is FactKind.TERRAIN and isinstance(fact.subject, tuple)
        )

    def surveyed(self) -> list[Coord]:
        """Tiles the clan has looked at properly, sorted for determinism."""
        return sorted(
            fact.subject
            for fact in self.facts.values()
            if fact.kind is FactKind.FORAGE and isinstance(fact.subject, tuple)
        )

    def frontier(self, world: World) -> list[Coord]:
        """Unknown tiles orthogonally adjacent to something known.

        The map opens outward from the hearth rather than letting anyone poke at a far
        corner.
        """
        edge = {
            neighbour
            for coord in self.revealed()
            for neighbour in world.neighbours(coord)
            if not self.knows(FactKind.TERRAIN, neighbour)
        }
        return sorted(edge)

    @property
    def known_count(self) -> int:
        return len(self.revealed())

    def unknown_count(self, world: World) -> int:
        return len(world.tiles) - self.known_count

    def fully_explored(self, world: World) -> bool:
        return not self.frontier(world)
