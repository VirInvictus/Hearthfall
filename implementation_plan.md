# Sub-project 5: The Ring - Implementation Plan

## Overview
Sub-project 5 transitions the game from managing anonymous kin groups to dealing with a named council (The Ring). This introduces personalities, agendas, and internal political friction. The core philosophy of this sub-project is that "losing an argument to your own council is worse than losing to winter."

## 1. Named Cast (`engine/people.py`)
We will introduce a `Person` dataclass to represent the named cast.
- **Attributes:** `id`, `name`, `household_id`, `age`, `trait` (personal character), and `ambition` (what they want the clan to focus on).
- **Lifecycle:** 
  - They are born from/attached to a `Household`.
  - They age each season.
  - They can die (due to age, events, or starvation in their household).
- **Generation:** A `Person` is generated deterministically when a Household becomes influential or when the Ring is formed. We will add a simple name generator or list in `data/names.toml`.

## 2. The Ring and Tiers (`engine/tiers.py` and `engine/state.py`)
- We will define the concept of the clan's "Tier". Starting as a disorganized clan, they hit an **emergence condition** (e.g., reaching 10 households or a certain food surplus) that triggers "The Named Moment" — the formation of The Ring.
- **The Ring:** A list of `Person` references acting as the active council. 
- The Ring limits the player's absolute power by injecting *Advisors* into the event loop.

## 3. Agendas and Council Advice
- **Characteristic Agendas:** Advisors will have logic to evaluate pending choices in an event. Based on their `trait` or `ambition` (e.g., *Militaristic*, *Cautious*, *Greedy*), they will endorse specific event choices.
- **The Wrong Answer:** Advisors are designed to be "wrong in characteristic ways." A cautious advisor will always suggest hoarding, even if you need to spend to survive. The player must weigh their advice against reality.

## 4. Chronicle Integration
- When a `PendingChoice` (Event) is presented, if The Ring exists, the advisors' endorsements will be injected into the event's presentation.
- The `TurnReport` and Chronicle will render these council decisions inline, showing not just what happened, but *who pushed for it*.

## 5. Event Corpus Gating
- We will add new events to `data/events` that only fire if the Ring exists, or if a specific advisor type is on the council (e.g., `condition = [{key = "ring_has_trait", op = "==", value = "ambitious"}]`).

## Step-by-Step Execution
1. Add `Person`, name generation, and lifecycle logic to `people.py` and `state.py`.
2. Create `tiers.py` with emergence logic for The Ring.
3. Update `turn.py` and `chronicle.py` to append advisor opinions to event choices.
4. Add new TOML events gated on these new state properties.
5. Ensure tests pass without consuming arbitrary RNG and breaking existing sequences.
