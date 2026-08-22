with open("src/hearthfall/engine/state.py", "r") as f:
    lines = f.readlines()

new_lines = []
in_header = True

for line in lines:
    if line.startswith("class Season"):
        break

new_lines.append('"""World, population, and stores: plain data with no rules in it.\n\nRules live in `turn.py` and numbers live in `balance.py`. What lives here is the shape of a\nrun, and `GameState.snapshot()`, which is the single seam between the simulation and the\ncontent. Every key an event condition may test is produced there and nowhere else.\n"""\n\n')
new_lines.append('from __future__ import annotations\n\n')
new_lines.append('from dataclasses import dataclass, field\n')
new_lines.append('from enum import StrEnum\n')
new_lines.append('from typing import TYPE_CHECKING\n\n')
new_lines.append('if TYPE_CHECKING:\n')
new_lines.append('    from hearthfall.engine.agents import Agent\n')
new_lines.append('    from hearthfall.engine.chronicle import ChronicleEntry\n')
new_lines.append('    from hearthfall.engine.orders import Orders\n\n')
new_lines.append('from hearthfall.engine.intel import FactKind, Ledger\n')
new_lines.append('from hearthfall.engine.people import Household\n')
new_lines.append('from hearthfall.engine.world import Coord, Terrain, World\n\n\n')

found_class = False
for line in lines:
    if line.startswith("class Season"):
        found_class = True
    
    if found_class:
        if line.startswith("    standing_orders:"):
            new_lines.append("    standing_orders: Orders | None = None\n")
        elif line.startswith("    agents:"):
            new_lines.append("    agents: dict[str, Agent] = field(default_factory=dict)  # type: ignore\n")
        elif line.startswith("    chronicle:"):
            new_lines.append("    chronicle: list[ChronicleEntry] = field(default_factory=list)  # type: ignore\n")
        else:
            new_lines.append(line)

with open("src/hearthfall/engine/state.py", "w") as f:
    f.writelines(new_lines)
