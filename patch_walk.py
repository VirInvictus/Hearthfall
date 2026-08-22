with open("src/hearthfall/engine/turn.py", "r") as f:
    lines = f.readlines()

out = []
in_walk = False
for line in lines:
    if line.startswith("def _walk("):
        in_walk = True
    if in_walk and "return (fact,)" in line:
        out.append("    learned = [fact]\n")
        out.append("    for agent in state.agents.values():\n")
        out.append("        if agent.location == target:\n")
        out.append("            learned.append(state.ledger.learn(FactKind.PRESENCE, target, agent.name, state.turn))\n")
        out.append("    return tuple(learned)\n")
        in_walk = False
    else:
        out.append(line)

with open("src/hearthfall/engine/turn.py", "w") as f:
    f.writelines(out)
