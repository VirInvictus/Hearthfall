# Sub-project 4: Neighbours and the Director (Implementation Plan)

## 1. Goal
Introduce an active world map containing agents (neighbours, wildlife, weather) with their own state, needs, and intents. Agents exist on the map and their state can be learned (and goes stale) via the fact ledger. The `director` orchestrates agent behavior, driving pressure rather than just relying on the harshness of winter.

## 2. Phase 1: Agents and Intents (`engine/agents.py`)
Introduce the core types for other entities in the world.
- `AgentType` (Enum): `NEIGHBOUR`, `WILDLIFE`, `WEATHER`.
- `Intent` (Dataclass): Something the agent plans to do (e.g., "raid", "trade", "migrate") and the `target_turn` when it will execute.
- `Agent` (Dataclass):
  - `id: str`: Unique identifier.
  - `name: str`: Display name (e.g., "Stonefold Clan", "Winter Storm").
  - `type: AgentType`: The kind of agent.
  - `location: Coord | None`: Where they are on the map.
  - `food: int`: Their grain store.
  - `mood: int`: Their disposition toward us or generally.
  - `intent: Intent | None`: What they are currently plotting.
- Update `GameState` to own `agents: list[Agent]`.

## 3. Phase 2: Learning about Agents
- Add new `FactKind` enum values if needed, or re-use `PRESENCE` and introduce `AGENT_INTENT`, `AGENT_STORE`, `AGENT_MOOD` to the ledger.
- A scout walking into a tile with an agent discovers their presence.
- A survey of the tile can reveal their `food`, `mood`, and `intent`.
- Crucially, this intel rots quickly. You might survey a tile and learn they are plotting a raid, but if you don't act on it or check back, that intent might change or execute while the fact is "aging" or "stale".

## 4. Phase 3: The Director (`engine/director.py`)
- Pacing engine that runs at the end of every season.
- Updates agent states (e.g., they eat their food, their mood shifts).
- Generates `Intents` based on their needs. If a neighbour is starving, they generate a "raid" intent against a known target (us).
- The honesty guarantee: The director can only generate a raid intent if the player *could* have scouted it. Agents don't magically spawn and attack in the same turn.

## 5. Phase 4: Interrupts and the Chronicle
- When an agent's `Intent` resolves, it interrupts the player's standing orders.
- The reason is logged in the `Chronicle` (e.g., "Stonefold raided our stores. Standing orders interrupted.").

## Next Steps
I will begin by creating `engine/agents.py` and extending `GameState` to support them. Does this structure align with your vision for Sub-project 4, or is there a different angle you'd like to take for the agent definitions?
