with open("src/hearthfall/engine/turn.py", "r") as f:
    lines = f.readlines()

out = []
in_new_game = False
for line in lines:
    if line.startswith("def new_game"):
        in_new_game = True
        out.append("from hearthfall.engine.agents import populate_agents\n")
        out.append(line)
    elif in_new_game and "state = GameState(" in line:
        out.append("    agents = populate_agents(world, rng)\n")
        out.append("    state = GameState(\n")
        out.append("        agents=agents,\n")
    elif in_new_game and "return state" in line:
        out.append(line)
        in_new_game = False
    else:
        out.append(line)

with open("src/hearthfall/engine/turn.py", "w") as f:
    f.writelines(out)
