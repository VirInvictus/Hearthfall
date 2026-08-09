"""World, population, and stores: plain data with no rules in it.

Rules live in `turn.py` and numbers live in `balance.py`. What lives here is the shape of a
run, and `GameState.snapshot()`, which is the single seam between the simulation and the
content. Every key an event condition may test is produced there and nowhere else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from hearthfall.engine.intel import Ledger
from hearthfall.engine.world import Coord, Terrain, World


class Season(StrEnum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


SEASONS: tuple[Season, ...] = (
    Season.SPRING,
    Season.SUMMER,
    Season.AUTUMN,
    Season.WINTER,
)


class Outcome(StrEnum):
    ENDURED = "endured"  # the run was survived to its end
    BURIED = "buried"  # no adults remain


@dataclass(frozen=True, slots=True)
class Effect:
    """A bundle of deltas an event choice applies. Structured, never an expression string.

    `spec.md` §6 is emphatic about this: `food = -5` needs no parser, and a parser is the
    event DSL that starves the corpus.
    """

    food: int = 0
    morale: int = 0
    adults: int = 0
    children: int = 0
    # Deltas to the run's persistent counters, as (name, delta) pairs sorted by name. A tuple
    # rather than a dict so the effect stays genuinely immutable and two effects built from
    # the same table compare equal. This is what gives the corpus a memory: a tally written by
    # a *choice* lets a later event require not just that something happened but that you
    # answered it a particular way.
    tally: tuple[tuple[str, int], ...] = ()

    @property
    def is_empty(self) -> bool:
        return not (
            self.food or self.morale or self.adults or self.children or self.tally
        )


@dataclass(frozen=True, slots=True)
class ChoiceOption:
    text: str
    effect: Effect


@dataclass(frozen=True, slots=True)
class PendingChoice:
    """A fired event awaiting the player's answer.

    The engine cannot resolve a choice inside a turn without a callback, and a callback
    would make the engine undrivable from a REPL. So the turn returns this instead and
    stops; `turn.apply_choice` finishes the job.
    """

    event_id: str
    title: str
    body: str
    options: tuple[ChoiceOption, ...]


@dataclass(slots=True)
class Population:
    adults: int
    # One entry per child, holding the turns remaining until they can be assigned work.
    children: list[int] = field(default_factory=list[int])
    morale: int = 5

    @property
    def child_count(self) -> int:
        return len(self.children)

    @property
    def total(self) -> int:
        return self.adults + self.child_count


@dataclass(slots=True)
class Stores:
    food: int = 0


@dataclass(slots=True)
class Orders:
    """One turn's labor allocation. Everything not assigned still eats."""

    forage: int = 0
    explore: int = 0
    tend: int = 0
    explore_target: Coord | None = None

    @property
    def assigned(self) -> int:
        return self.forage + self.explore + self.tend

    def validate(self, adults: int) -> None:
        if min(self.forage, self.explore, self.tend) < 0:
            raise ValueError("orders cannot assign a negative number of people")
        if self.assigned > adults:
            raise ValueError(
                f"orders assign {self.assigned} people but only {adults} adults exist"
            )


@dataclass(slots=True)
class GameState:
    seed: int
    world: World
    # What is true and what the clan believes are two objects on purpose; the gap between
    # them is the game (`spec.md` §1).
    ledger: Ledger
    population: Population
    stores: Stores
    turn: int = 0
    outcome: Outcome | None = None
    pending: PendingChoice | None = None
    # The terrain most recently walked into. Kept on the state rather than passed around
    # per turn so that `snapshot()` stays the only seam content reads through.
    last_revealed: Terrain | None = None
    # How many foragers the known ground supports. Cached here for the same reason, and by
    # necessity: computing it needs the per-terrain tables, `balance` imports `state`, so a
    # `state` that imported `balance` would close the loop. `turn._refresh_ground` owns it and
    # a test asserts the cache never disagrees with a live count.
    forage_capacity: int = 0
    # Ids of events that have fired, so `once = true` entries do not come round again.
    fired_events: list[str] = field(default_factory=list[str])
    # What the clan remembers. Every declared tally is present from the first turn at zero, so
    # `snapshot()` has a stable key set and a condition naming a tally that does not exist
    # fails when the corpus loads rather than silently never matching. See `data/tallies.toml`.
    tallies: dict[str, int] = field(default_factory=dict[str, int])

    @property
    def season(self) -> Season:
        return SEASONS[self.turn % len(SEASONS)]

    @property
    def year(self) -> int:
        return self.turn // len(SEASONS) + 1

    @property
    def is_over(self) -> bool:
        return self.outcome is not None

    def snapshot(self) -> dict[str, int | str]:
        """The flat view an event condition is evaluated against.

        Adding a condition key means adding it here and nowhere else. Keep it flat and
        keep the values primitive; the evaluator compares with `==` and `<`, nothing more.
        """
        return {
            "turn": self.turn,
            "year": self.year,
            "season": str(self.season),
            "adults": self.population.adults,
            "children": self.population.child_count,
            "people": self.population.total,
            "food": self.stores.food,
            "morale": self.population.morale,
            "tiles_known": self.ledger.known_count,
            "tiles_unknown": self.ledger.unknown_count(self.world),
            # Lets content fire on a clan with more hands than ground, which is the pressure
            # slice 2 introduced and the reason a season starts to feel cramped.
            "forage_capacity": self.forage_capacity,
            "hands_without_ground": max(
                0, self.population.adults - self.forage_capacity
            ),
            "terrain_home": str(self.world.tile(self.world.home).terrain),
            "terrain_revealed": str(self.last_revealed)
            if self.last_revealed
            else "none",
            # Namespaced so a tally can never collide with a real state key, and so a reader
            # of an event condition can see at a glance that `tally_elder_resentment` is
            # something the corpus wrote rather than something the simulation computed.
            **{f"tally_{name}": value for name, value in self.tallies.items()},
        }
