from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

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


def populate_agents(world: World, rng: Rng) -> dict[str, Agent]:
    """Seed the map with neighbours and wildlife.

    This replaces an empty world with one that has actors in it.
    """
    agents: dict[str, Agent] = {}

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
                food=rng.randint(20, 50),
                mood=rng.randint(3, 7),
            )
            placed_neighbours += 1

    return agents
