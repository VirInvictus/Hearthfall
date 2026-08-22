with open("src/hearthfall/engine/state.py", "r") as f:
    lines = f.readlines()

out = []
for line in lines:
    if line.startswith("from hearthfall.engine.world import"):
        out.append(line)
        out.append("from typing import TYPE_CHECKING\n")
        out.append("if TYPE_CHECKING:\n")
        out.append("    from hearthfall.engine.agents import Agent\n")
        out.append("    from hearthfall.engine.orders import Orders\n")
        out.append("    from hearthfall.engine.chronicle import ChronicleEntry\n")
    else:
        out.append(line)

with open("src/hearthfall/engine/state.py", "w") as f:
    f.writelines(out)
