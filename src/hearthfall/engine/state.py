"""World, population, and stores: plain data with no rules in it.

Rules live in `turn.py` and numbers live in `balance.py`. What lives here is the shape of a
run, and `GameState.snapshot()`, which is the single seam between the simulation and the
content. Every key an event condition may test is produced there and nowhere else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from hearthfall.engine.intel import FactKind, Ledger
from hearthfall.engine.people import Household, Rationing
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
    """The pool, held as households.

    Every aggregate here is derived rather than stored, so households are the single source of
    truth and the clan-wide numbers cannot drift from the kin groups they are made of. The
    read API (`adults`, `child_count`, `total`, `morale`) is unchanged from when this held flat
    counts, which is what let households arrive without touching the frontend or the corpus.

    Mutation is the part that had to change. A clan does not lose "an adult", a *household*
    does, and which household it is turns out to be the whole game.
    """

    households: list[Household] = field(default_factory=list[Household])

    @classmethod
    def of(
        cls, adults: int, children: list[int] | None = None, morale: int = 5
    ) -> Population:
        """Build a single-household population. The old flat shape, for fixtures and tests."""
        return cls(
            households=[
                Household(adults=adults, children=list(children or []), mood=morale)
            ]
        )

    @property
    def adults(self) -> int:
        return sum(h.adults for h in self.households)

    @property
    def children(self) -> list[int]:
        return [age for h in self.households for age in h.children]

    @property
    def child_count(self) -> int:
        return sum(h.child_count for h in self.households)

    @property
    def total(self) -> int:
        return self.adults + self.child_count

    @property
    def morale(self) -> int:
        """The clan-wide number, as the average of the households that still exist.

        Kept because roughly thirty shipped events read `morale`, and because "how is the clan"
        is still a real question. What it no longer is, is the only question: a clan averaging
        five with one household at zero is a different clan from one where everybody is at
        five, and `worst_household_mood` is what tells them apart.
        """
        living = [h for h in self.households if not h.is_empty]
        return sum(h.mood for h in living) // len(living) if living else 0

    @property
    def worst_mood(self) -> int:
        living = [h.mood for h in self.households if not h.is_empty]
        return min(living) if living else 0

    def resentful(self, threshold: int) -> int:
        return sum(
            1 for h in self.households if not h.is_empty and h.resentment >= threshold
        )

    @property
    def living_households(self) -> int:
        return sum(1 for h in self.households if not h.is_empty)

    # --- Mutation, which now has to choose a household ---------------------------------

    def shift_mood(self, delta: int, low: int, high: int) -> None:
        for household in self.households:
            household.mood = max(low, min(high, household.mood + delta))

    def add_adults(self, count: int) -> None:
        """New hands join the smallest household, which is how a kin group recovers."""
        for _ in range(count):
            if not self.households:
                self.households.append(Household(adults=0))
            smallest = min(self.households, key=lambda h: (h.size, id(h)))
            smallest.adults += 1

    def add_child(self, matures_after: int) -> None:
        for household in sorted(self.households, key=lambda h: (h.size, id(h))):
            if household.adults:
                household.children.append(matures_after)
                return

    def take_people(self, count: int) -> int:
        """Lose `count` people, worst-off household first. Returns how many actually went.

        Worst-off means lowest mood, because a household already at the end of its rope is
        where a death lands hardest and where the resentment it produces will matter most.
        """
        taken = 0
        for _ in range(count):
            candidates = [h for h in self.households if not h.is_empty]
            if not candidates:
                break
            if min(candidates, key=lambda h: (h.mood, -h.size, id(h))).take_a_person():
                taken += 1
        return taken

    def grow(
        self,
        target: int,
        mood_floor: int,
        needs_adults: int,
        lost: int,
        matures_after: int,
    ) -> int:
        """Advance every household's bond and bear a child wherever it has come due.

        Returns how many were born. Deterministic: a fed, content hearth with two adults in it
        grows on a schedule, and a hungry one loses ground. That is what ties growth to how the
        player rationed, which the old global food-and-morale gate could not do because it
        asked about the clan as a whole and therefore about nobody.
        """
        born = 0
        for household in self.households:
            if household.is_empty:
                continue
            settled = (
                household.adults >= needs_adults
                and household.mood >= mood_floor
                and not household.went_short
            )
            if settled:
                household.bond += 1
                if household.bond >= target:
                    household.bond = 0
                    household.children.append(matures_after)
                    born += 1
            else:
                household.bond = max(0, household.bond - lost)
        return born

    def split_crowded(self, limit: int) -> int:
        """Break up any hearth that has outgrown itself. Returns how many split off.

        A household holds kin, not a barracks. Splitting is what takes three groups toward the
        ten to forty `spec.md` §5 wants, and every new hearth is somewhere a grievance can live
        that was not there before.
        """
        made = 0
        for household in list(self.households):
            if household.size < limit or household.adults < 2:
                continue
            # Half the adults and half the children leave, taking the mood with them but not
            # the grudge: resentment belongs to the people who were fed last, and the ones who
            # walked out to found a new hearth are starting something rather than nursing it.
            moving = household.adults // 2
            household.adults -= moving
            taken = household.children[moving:]
            household.children = household.children[:moving]
            self.households.append(
                Household(adults=moving, children=taken, mood=household.mood)
            )
            made += 1
        return made

    def clear_hunger(self) -> None:
        for household in self.households:
            household.went_short = 0

    def mature(self) -> int:
        """Age every child by one season and count those who became hands."""
        matured = 0
        for household in self.households:
            remaining: list[int] = []
            for turns_left in household.children:
                if turns_left <= 1:
                    matured += 1
                    household.adults += 1
                else:
                    remaining.append(turns_left - 1)
            household.children = remaining
        return matured


@dataclass(slots=True)
class Stores:
    food: int = 0


@dataclass(slots=True)
class Orders:
    """One turn's labor allocation. Everything not assigned still eats."""

    forage: int = 0
    scout: int = 0
    tend: int = 0
    scout_target: Coord | None = None
    # How a short store gets divided. Only bites when there is not enough to go round, which
    # is what keeps it a decision about scarcity rather than a setting.
    rationing: Rationing = Rationing.EQUAL

    @property
    def assigned(self) -> int:
        return self.forage + self.scout + self.tend

    def validate(self, adults: int) -> None:
        if min(self.forage, self.scout, self.tend) < 0:
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
    # How much resentment makes a household count as resentful when content asks. Carried here
    # for the same reason `forage_capacity` is: `snapshot()` needs it, and `balance` imports
    # `state`, so reading it directly would close the import loop. `new_game` sets it.
    resentful_at: int = 3
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
            # The household layer, as the flat scalars the evaluator can compare. Decision 5
            # of the replan: every any/count/worst question is precomputed here so the
            # fifty-line evaluator never has to learn how to ask one.
            "households": self.population.living_households,
            "worst_household_mood": self.population.worst_mood,
            "households_resentful": self.population.resentful(self.resentful_at),
            "tiles_known": self.ledger.known_count,
            "tiles_unknown": self.ledger.unknown_count(self.world),
            # Walked and surveyed are two different amounts of knowing (slice 3), so content
            # can tell a clan that has seen a lot of ground from one that understands any of
            # it. Never larger than tiles_known: a survey re-walks the tile it looks at.
            "tiles_surveyed": len(self.ledger.surveyed()),
            # The first staleness key content can read (slice 5). Not "how wrong are we",
            # which the clan cannot know, but "how long since anybody checked", which it can.
            "stale_surveys": self.ledger.stale_count(FactKind.FORAGE, self.turn),
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
