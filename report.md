# City Tier & Research Paradigm (Analysis)

**Context:** A proposal to introduce a game-mode transition between Stage 1 (managing a small group) and Stage 2 (managing a city). This transition is gated by two specific research breakthroughs: *City Planning* and *Calendar*. 
- **City Planning** unlocks buildings, adding passive resource generation and shifting labor from individual placement to population-level assignment.
- **Calendar** attempts to shift the game from seasonal turn-based play to real-time (clock-based) flow.
- A **30-tier research system** drives passive progress, accelerated by educational buildings.

This report measures the proposal against the project's foundational constraints (`spec.md`).

---

## 1. What Aligns Perfectly

### Abstracting the Chore (Stage 1 to Stage 2)
The shift from micro-managing individual foragers to managing population aggregates and building slots is exactly what `spec.md` §9.9 demands: *"Each tier abstracts the one below it. A new tier that adds a screen without retiring a chore has made the game longer, not deeper."* Retiring the manual labor placement of Stage 1 to focus on city-wide workflows is the correct mechanical evolution.

### Infrastructure & Passive Yields
City Planning allowing buildings that provide a `+x` passive return fits cleanly into the planned **Sub-project 9 (Infrastructure and Upgrades)**. A granary that reduces spoilage, or a lumber camp that guarantees seasonal wood, replaces the "go out and forage" loop with permanent economic floors. 

## 2. Where the Design Frictions Lie

### The Real-Time Trap vs. The Chronicle
The proposal suggests the *Calendar* research shifts the game into real-time. 
**The Spec Constraint (`spec.md` §4):** *"The engine always ticks one season. Forever. Tiers do not change the clock; they change how many seasons resolve before the game stops and asks you something."*

Switching the core engine loop to actual real-time (tick-based by seconds) would require throwing away the deterministic turn-based engine (`turn.py`). 

**The Hearthfall Translation:** The game *already* has a design for this, located in **Sub-project 3 (The Chronicle)**. The "real-time flow" is achieved through **standing orders and interrupts**. Once *Calendar* is researched, the player sets standing orders, and the engine rapidly resolves seasons in the background (`turn.run_until_interrupted`), printing lines to the chronicle. Time compresses, feeling like a real-time sim, but the underlying arithmetic remains strictly seasonal and deterministic.

### The Research Tree vs. The Spine
A 30-tier passive research tree is a classic 4X mechanic, but Hearthfall's core spine (`spec.md` §1) is: *"Read the unknown at cost. Then commit resources you cannot take back."*

If research is just a meter that fills up over time, it violates the spine. 
**The Hearthfall Translation:** Research must be tied to the **Fact Ledger**. You cannot research *Masonry* just by waiting; you must have paid scouts to survey a *Stone Quarry*. Educational buildings (like a *Shaman's Tent* or *Scriptorium*) don't just produce generic "research points"; they process Facts brought back from the map into usable Tech. This keeps exploration mandatory even in the city phase.

## 3. Roadmap Integration

This proposal refines the later stages of the roadmap. The ideas map directly to the following sub-projects:

- **Sub-project 3 (The Chronicle):** Implements the "Calendar" feel. Standing orders allow the game to run unattended for years, compressing time to feel like real-time without breaking the turn-based engine.
- **Sub-project 9 (Infrastructure and Upgrades):** Introduces *City Planning*, buildings, and passive yields. 
- **Sub-project 10 (City and Power):** The formal transition where the manual labor allocation (Stage 1) is entirely retired and replaced by population assignment. The 30-tier tech tree (driven by the fact ledger) lives here.

*(See `roadmap.md` for the updated sequencing).*
