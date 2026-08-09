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

    @property
    def is_empty(self) -> bool:
        return not (self.food or self.morale or self.adults or self.children)


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
    # Ids of events that have fired, so `once = true` entries do not come round again.
    fired_events: list[str] = field(default_factory=list[str])

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
            "terrain_home": str(self.world.tile(self.world.home).terrain),
            "terrain_revealed": str(self.last_revealed)
            if self.last_revealed
            else "none",
        }
