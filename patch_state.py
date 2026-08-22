with open('src/hearthfall/engine/state.py', 'r') as f:
    lines = f.readlines()

out = []
for line in lines:
    if line.startswith("    pending: PendingChoice | None = None"):
        out.append(line)
        out.append("    standing_orders: 'Orders' | None = None\n")
        out.append("    chronicle: list['ChronicleEntry'] = field(default_factory=list)\n")
    else:
        out.append(line)

with open('src/hearthfall/engine/state.py', 'w') as f:
    f.writelines(out)
