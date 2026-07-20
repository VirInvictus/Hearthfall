"""The tick: resolve a turn, advance time.

Resolution order is load-bearing. Producing before consuming means this turn's foraging can
feed this turn's mouths; spoiling after consuming means you never rot food someone was
about to eat. Changing the order changes the balance of every constant in `balance.py`, so
the order is fixed here and documented step by step rather than left to be inferred.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from hearthfall.engine import balance
from hearthfall.engine.rng import Rng
from hearthfall.engine.state import (
    Effect,
    GameState,
    Orders,
    Outcome,
    PendingChoice,
    Population,
    Season,
    Stores,
)
from hearthfall.engine.world import Coord, Terrain, World


@dataclass
class TurnReport:
    """What happened, in numbers the caller can render and in lines it can print.

    The frontend computes nothing. If the player should see it, it is in here.
    """

    turn: int
    season: Season
    produced: int = 0
    consumed: int = 0
    shortfall: int = 0
    starved: int = 0
    spoiled: int = 0
    matured: int = 0
    born: int = 0
    revealed: Coord | None = None
    revealed_terrain: Terrain | None = None
    log: list[str] = field(default_factory=list)
    pending: PendingChoice | None = None
    outcome: Outcome | None = None

    def note(self, line: str) -> None:
        self.log.append(line)


def new_game(seed: int) -> GameState:
    """A fresh run. Everything downstream of this is a function of the seed."""
    rng = Rng(seed)
    world = World.generate(
        width=balance.MAP_WIDTH,
        height=balance.MAP_HEIGHT,
        rng=rng,
        weights=balance.TERRAIN_WEIGHTS,
    )
    return GameState(
        seed=seed,
        world=world,
        population=Population(
            adults=balance.STARTING_ADULTS,
            children=[balance.CHILD_MATURES_AFTER] * balance.STARTING_CHILDREN,
            morale=balance.STARTING_MORALE,
        ),
        stores=Stores(food=balance.STARTING_FOOD),
    )


def resolve(state: GameState, orders: Orders, rng: Rng) -> TurnReport:
    """Advance the world by one season."""
    if state.is_over:
        raise RuntimeError("the run is over; no further turns resolve")
    if state.pending is not None:
        raise RuntimeError(
            "an event choice is outstanding; call apply_choice before the next turn"
        )
    orders.validate(state.population.adults)

    season = state.season
    report = TurnReport(turn=state.turn, season=season)

    _produce(state, orders, season, report)
    _consume(state, report)
    _starve(state, report)
    _spoil(state, orders, season, report)
    _explore(state, orders, rng, report)
    _draw_event(state, rng, report)
    _grow(state, rng, report)
    _advance(state, report)

    return report


def apply_choice(state: GameState, index: int) -> Effect:
    """Answer the outstanding event choice.

    The effect lands on the state the turn left behind, which means a choice made at the
    end of turn N is felt at the start of turn N+1. That is deliberate: the player sees the
    consequence in the numbers they allocate against next.
    """
    pending = state.pending
    if pending is None:
        raise RuntimeError("no event choice is outstanding")
    if not 0 <= index < len(pending.options):
        raise IndexError(
            f"choice {index} is out of range for event {pending.event_id!r}"
        )

    effect = pending.options[index].effect
    state.pending = None
    apply_effect(state, effect)
    _judge(state)
    return effect


def apply_effect(state: GameState, effect: Effect) -> None:
    """Apply a bundle of deltas, clamped so the state stays legal."""
    state.stores.food = max(0, state.stores.food + effect.food)
    state.population.morale = _clamp_morale(state.population.morale + effect.morale)
    state.population.adults = max(0, state.population.adults + effect.adults)

    for _ in range(effect.children):
        state.population.children.append(balance.CHILD_MATURES_AFTER)
    for _ in range(-effect.children):
        _take_a_child(state.population)


# --- Steps, in resolution order ---------------------------------------------------------


def _produce(
    state: GameState, orders: Orders, season: Season, report: TurnReport
) -> None:
    produced = orders.forage * balance.FORAGE_YIELD[season]
    state.stores.food += produced
    report.produced = produced
    if produced:
        report.note(f"Foragers brought in {produced} food.")
    elif orders.forage:
        report.note("The foragers came back with nothing.")


def _consume(state: GameState, report: TurnReport) -> None:
    population = state.population
    demand = (
        population.adults * balance.FOOD_PER_ADULT
        + population.child_count * balance.FOOD_PER_CHILD
    )
    eaten = min(demand, state.stores.food)
    state.stores.food -= eaten
    report.consumed = eaten
    report.shortfall = demand - eaten
    report.note(f"{population.total} mouths ate {eaten} food.")


def _starve(state: GameState, report: TurnReport) -> None:
    if not report.shortfall:
        return

    population = state.population
    deaths = math.ceil(report.shortfall / balance.FOOD_PER_STARVATION_DEATH)
    deaths = min(deaths, population.total)

    for _ in range(deaths):
        if population.children:
            _take_a_child(population)
        else:
            population.adults -= 1

    report.starved = deaths
    population.morale = _clamp_morale(
        population.morale
        - balance.MORALE_LOSS_PER_STARVATION
        - deaths * balance.MORALE_LOSS_PER_DEATH
    )
    report.note(
        f"The stores ran {report.shortfall} short. {deaths} did not survive it."
    )


def _spoil(
    state: GameState, orders: Orders, season: Season, report: TurnReport
) -> None:
    rate = max(
        balance.SPOIL_RATE_FLOOR,
        balance.SPOIL_RATE[season] - orders.tend * balance.SPOIL_REDUCTION_PER_TENDER,
    )
    spoiled = int(state.stores.food * rate)
    state.stores.food -= spoiled
    report.spoiled = spoiled
    if spoiled:
        report.note(f"{spoiled} food rotted in the store.")


def _explore(state: GameState, orders: Orders, rng: Rng, report: TurnReport) -> None:
    if orders.explore < balance.EXPLORERS_PER_REVEAL:
        if orders.explore:
            report.note("Too few went out to find anything worth the walk.")
        return

    frontier = state.world.frontier()
    if not frontier:
        report.note("There is nothing left within reach to walk into.")
        return

    target = orders.explore_target
    if target is None:
        target = rng.choice(frontier)
    elif target not in frontier:
        raise ValueError(f"{target} is not on the frontier; it cannot be explored into")

    tile = state.world.reveal(target)
    report.revealed = target
    report.revealed_terrain = tile.terrain
    report.note(
        f"The scouts came back knowing {tile.terrain} to the {_bearing(state, target)}."
    )


def _draw_event(state: GameState, rng: Rng, report: TurnReport) -> None:
    """Fire at most one event from the corpus.

    Wired in step 2 of the build order. Until then a turn is pure simulation, which is
    enough to balance the food math against.
    """
    return


def _grow(state: GameState, rng: Rng, report: TurnReport) -> None:
    population = state.population

    remaining: list[int] = []
    matured = 0
    for turns_left in population.children:
        if turns_left <= 1:
            matured += 1
        else:
            remaining.append(turns_left - 1)
    population.children = remaining
    population.adults += matured
    report.matured = matured
    if matured:
        report.note(f"{matured} came of age.")

    if (
        state.stores.food >= balance.BIRTH_FOOD_THRESHOLD
        and population.morale >= balance.BIRTH_MORALE_THRESHOLD
        and rng.chance(balance.BIRTH_CHANCE)
    ):
        population.children.append(balance.CHILD_MATURES_AFTER)
        report.born = 1
        report.note("A child was born to the hearth.")

    # Morale drifts back toward the middle when nothing pushes it, so one bad winter does
    # not flatten the clan for the rest of the run and leave every later event landing on
    # the floor.
    if population.morale < balance.MORALE_DRIFT_TARGET:
        population.morale += 1
    elif population.morale > balance.MORALE_DRIFT_TARGET:
        population.morale -= 1


def _advance(state: GameState, report: TurnReport) -> None:
    state.turn += 1
    _judge(state)
    report.outcome = state.outcome
    report.pending = state.pending
    if state.outcome is Outcome.BURIED:
        report.note("No one is left to keep the fire. The hearth goes out.")
    elif state.outcome is Outcome.ENDURED:
        report.note("Five winters. The fire is still lit.")


# --- Helpers -----------------------------------------------------------------------------


def _judge(state: GameState) -> None:
    """Decide whether the run is over. Losing takes precedence over finishing."""
    if state.outcome is not None:
        return
    if state.population.adults <= 0:
        state.outcome = Outcome.BURIED
    elif state.turn >= balance.TURNS_PER_RUN:
        state.outcome = Outcome.ENDURED


def _take_a_child(population: Population) -> None:
    """Remove the child furthest from maturity.

    Deterministic, and it leaves the clan the ones closest to being hands. That is the
    kinder outcome mechanically and the colder one to read, which is about right.
    """
    if not population.children:
        return
    population.children.remove(max(population.children))


def _clamp_morale(value: int) -> int:
    return max(balance.MORALE_MIN, min(balance.MORALE_MAX, value))


def _bearing(state: GameState, target: Coord) -> str:
    """A rough compass word for a revealed tile, relative to the hearth."""
    home_x, home_y = state.world.home
    x, y = target
    vertical = "north" if y < home_y else "south" if y > home_y else ""
    horizontal = "west" if x < home_x else "east" if x > home_x else ""
    return f"{vertical}{horizontal}" or "edge of the clearing"
