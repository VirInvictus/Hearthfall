with open("src/hearthfall/engine/state.py", "r") as f:
    lines = f.readlines()

out = []
for line in lines:
    if line.startswith("from hearthfall.engine.agents import Agent"):
        out.append("from typing import TYPE_CHECKING\n")
        out.append("if TYPE_CHECKING:\n")
        out.append("    from hearthfall.engine.agents import Agent\n")
    elif line.startswith("from hearthfall.engine.orders import Orders"):
        out.append("    from hearthfall.engine.orders import Orders\n")
    elif line.startswith("from hearthfall.engine.chronicle import ChronicleEntry"):
        out.append("    from hearthfall.engine.chronicle import ChronicleEntry\n")
    elif "agents: dict[str, Agent] = field(default_factory=dict[str, Agent])" in line:
        out.append("    agents: dict[str, 'Agent'] = field(default_factory=dict)\n")
    elif "chronicle: list[ChronicleEntry] = field(default_factory=list[ChronicleEntry])" in line:
        out.append("    chronicle: list['ChronicleEntry'] = field(default_factory=list)\n")
    elif "standing_orders: Orders | None = None" in line:
        out.append("    standing_orders: 'Orders' | None = None\n")
    else:
        out.append(line)

with open("src/hearthfall/engine/state.py", "w") as f:
    f.writelines(out)
