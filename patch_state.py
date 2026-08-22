with open("src/hearthfall/engine/state.py", "r") as f:
    lines = f.readlines()

out = []
for line in lines:
    if line.strip() == "stores: Stores":
        out.append(line)
        out.append("    agents: dict[str, Agent] = field(default_factory=dict)\n")
    else:
        out.append(line)

with open("src/hearthfall/engine/state.py", "w") as f:
    f.writelines(out)
