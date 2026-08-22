with open("src/hearthfall/engine/state.py", "r") as f:
    lines = f.readlines()

out = []
skip = False
for line in lines:
    if line.startswith("from typing import TYPE_CHECKING"):
        skip = True
        out.append("from hearthfall.engine.agents import Agent\n")
        out.append("from hearthfall.engine.orders import Orders\n")
        out.append("from hearthfall.engine.chronicle import ChronicleEntry\n")
    elif skip and line.startswith("class Season"):
        skip = False
        out.append(line)
    elif not skip:
        out.append(line)

with open("src/hearthfall/engine/state.py", "w") as f:
    f.writelines(out)
