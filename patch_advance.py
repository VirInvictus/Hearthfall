import sys

with open("src/hearthfall/engine/turn.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == "state.turn += 1":
        new_lines.extend([
            line,
            "    # Check if ring formed\n",
            "    if state.ledger.tallies.get('ring_formed', 0) > 0 and state.tier == 'clan':\n",
            "        from hearthfall.engine.tiers import Tier, Council, generate_person\n",
            "        state.tier = Tier.RING\n",
            "        state.council = Council()\n",
            "        # Add one representative from each household to the council\n",
            "        for hh in state.population.households:\n",
            "            if not hh.is_empty:\n",
            "                person = generate_person(state, hh.id, rng)\n",
            "                state.council.advisors.append(person.id)\n",
            "        report.note(f\"The Ring is formed with {len(state.council.advisors)} advisors.\")\n"
        ])
    elif line.startswith("def _advance(state: GameState, report: TurnReport) -> None:"):
        new_lines.append("def _advance(state: GameState, rng: Rng, report: TurnReport) -> None:\n")
    elif line.strip() == "_advance(state, report)":
        new_lines.append("    _advance(state, rng, report)\n")
    else:
        new_lines.append(line)

with open("src/hearthfall/engine/turn.py", "w") as f:
    f.writelines(new_lines)
