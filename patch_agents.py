with open("src/hearthfall/engine/agents.py", "r") as f:
    lines = f.readlines()

out = []
for line in lines:
    if line.startswith("from hearthfall.engine.world import Coord"):
        out.append(line)
        out.append("from typing import TYPE_CHECKING\n")
        out.append("if TYPE_CHECKING:\n")
        out.append("    from hearthfall.engine.world import World\n")
        out.append("    from hearthfall.engine.rng import Rng\n")
    elif line.startswith("def populate_agents("):
        out.append("def populate_agents(world: 'World', rng: 'Rng') -> dict[str, Agent]:\n")
    else:
        out.append(line)

with open("src/hearthfall/engine/agents.py", "w") as f:
    f.writelines(out)
