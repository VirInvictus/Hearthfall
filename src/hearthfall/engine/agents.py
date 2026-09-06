from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from hearthfall.engine.units import Composition
from hearthfall.engine.world import Coord

if TYPE_CHECKING:
    from hearthfall.engine.rng import Rng
    from hearthfall.engine.world import World


class AgentType(StrEnum):
    NEIGHBOUR = "neighbour"
    WILDLIFE = "wildlife"
    WEATHER = "weather"


class IntentKind(StrEnum):
    RAID = "raid"
    TRADE = "trade"
    MIGRATE = "migrate"


@dataclass(slots=True)
class Intent:
    kind: IntentKind
    target_turn: int
    target: Coord | str | None = None


@dataclass(slots=True)
class Agent:
    id: str
    name: str
    type: AgentType
    location: Coord | None = None
    food: int = 0
    mood: int = 0
    intent: Intent | None = None
    # Spears the band can field: what it presses with, and what the ledger's
    # raider-strength fact is a read of. With a composition (below) this is
    # the mix's press total; without one it is the scalar draw, which is what
    # a hand-built band still carries.
    strength: int = 0
    # The band's mix of types, drawn the season the intent forms. None for a
    # band assembled by hand, whose scalar strength stands alone.
    composition: Composition | None = None

    def grow(
        self,
        rng: Rng,
        *,
        forage: int,
        consumption: int,
    ) -> None:
        """Process one season for this agent.

        They gather less than they eat, so the store runs down; when it runs
        out, mood drops; when mood drops low enough, they may form a hostile
        intent (like RAID) if they don't already have one. The economy arrives
        as an argument rather than being read from `balance`, for the same
        reason the half-lives do: it keeps this module a leaf of the import
        graph. The caller reads the numbers from `balance` and hands them over.

        The band's composition is not drawn here: mustering is the tick's job
        (`turn._agents_tick`), which owns the seeded draws and the ledger
        moment the read is learned.
        """
        if self.type == AgentType.NEIGHBOUR:
            self.food += forage
            self.food -= consumption

            if self.food < 0:
                self.food = 0
                self.mood -= 1
            elif self.food > 20:
                self.mood = min(10, self.mood + 1)

            # Form intents if miserable and not already holding one
            if self.mood <= 0 and self.intent is None:
                # Target turn is assigned when it forms.
                self.intent = Intent(
                    kind=IntentKind.RAID,
                    target_turn=0,
                )


def populate_agents(
    world: World, rng: Rng, band_food: tuple[int, int]
) -> dict[str, Agent]:
    """Seed the map with neighbours and wildlife.

    This replaces an empty world with one that has actors in it. The range the
    bands start with arrives as an argument, like every number this module
    uses; the caller reads it from `balance`.
    """
    agents: dict[str, Agent] = {}
    low, high = band_food

    # Generate 1-2 neighbour clans somewhere not at home.
    num_neighbours = rng.randint(1, 2)
    placed_neighbours = 0
    attempts = 0

    while placed_neighbours < num_neighbours and attempts < 100:
        attempts += 1
        x = rng.randint(0, world.width - 1)
        y = rng.randint(0, world.height - 1)
        coord = (x, y)
        if coord != world.home and world.tile(coord).terrain != "water":
            # Just some procedural names
            name = rng.choice(["Stonefold", "Ashen", "River-kin", "Hollow"])
            # Ensure unique IDs
            agent_id = f"neighbour_{placed_neighbours}"
            agents[agent_id] = Agent(
                id=agent_id,
                name=f"{name} Clan",
                type=AgentType.NEIGHBOUR,
                location=coord,
                food=rng.randint(low, high),
                mood=rng.randint(3, 7),
            )
            placed_neighbours += 1

    return agents
