# Sub-project 4: Neighbours and the Director - Implementation Plan

This plan addresses the un-checked goals for **Sub-project 4: Neighbours and the Director** in `roadmap.md`. The design adheres to `spec.md`'s rigid demand for the "honesty guarantee" (intents must exist as scoutable facts before they execute) and the separation of pacing (the Director) from threat generation (Agents).

## 1. `engine/agents.py`: Stateful Neighbors
Currently, agents (like "Stonefold Clan") are placed on the map during `new_game` but they sit frozen. We will:
- Implement `Agent.grow(season)`: Agents will consume food each season. If `food <= 0`, their `mood` plummets.
- **Intent Formation:** When an agent is starving (or resentful), they form an `Intent` (e.g., `IntentKind.RAID`). 
- **The Honesty Guarantee:** This intent is stored directly on `agent.intent`. It doesn't instantly strike the player. Because it exists on the agent, the player can scout the agent's tile and discover this fact *before* it happens, placing it in the Fact Ledger.

## 2. `engine/director.py`: The Pacing Layer
The Director never spawns threats out of thin air; it only marshals the intents that Agents have already formed. We will:
- Create `Director.evaluate(state, rng)`: Looks at all `agent.intent`s.
- **Pacing Logic:** The Director looks at the player's "slack" (e.g., current food stores, mood). If the player is cruising effortlessly, the Director accelerates the execution of a pending `RAID` intent. If the player is already starving, the Director might delay it (within reason).
- **Interrupts:** When the Director decides an intent must surface, it raises an `Interrupt`.

## 3. Integration into `turn.py` & `state.py`
- Modify `turn.py`'s `resolve_season()` to step the agents (letting them consume food and form intents).
- Pass the state to `Director.evaluate()`. If the Director fires an interrupt, `run_until_interrupted` (the standing orders loop from Sub-project 3) is immediately broken.
- The cause of the interrupt is logged to the `chronicle`.

## 4. Testing
- Write `test_agents.py` to assert that isolated agents naturally consume stores and form RAID intents when starving.
- Write `test_director.py` to assert that the Director *never* surfaces a raid if no agent possesses a RAID intent (testing the Honesty Guarantee).

**Does this implementation plan align with your vision for Sub-project 4? If so, I'll begin with `agents.py` and `director.py`.**
