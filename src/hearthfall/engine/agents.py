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
    # Spears the band can field. Set when a raid intent forms (the range
    # arrives as an argument — see the import-graph note on half-lives), and
    # what the ledger's raider-strength fact is a read of.
    strength: int = 0

    def grow(self, rng: Rng, raid_strength: tuple[int, int] | None = None) -> None:
        """Process one season for this agent.

        They consume food. If they run out, mood drops. If mood drops low enough,
        they may form a hostile intent (like RAID) if they don't already have one.
        """
        if self.type == AgentType.NEIGHBOUR:
            # Abstract foraging: they find some food, but it might not be enough
            foraged = 9
            self.food += foraged
            self.food -= 10  # Base consumption

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
                # The band musters its spears the season it decides to use
                # them. The draw is seeded, so the band is reproducible.
                if raid_strength is not None:
                    low, high = raid_strength
                    self.strength = rng.randint(low, high)


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
