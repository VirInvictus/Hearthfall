with open("src/hearthfall/engine/turn.py", "r") as f:
    lines = f.readlines()

out = []
in_survey = False
for line in lines:
    if line.startswith("def _survey("):
        in_survey = True
    
    if in_survey and "return learned + (ground, worth)" in line:
        out.append("    agent_facts = []\n")
        out.append("    for agent in state.agents.values():\n")
        out.append("        if agent.location == coord:\n")
        out.append("            agent_facts.append(ledger.learn(FactKind.PRESENCE, coord, agent.name, state.turn))\n")
        out.append("            agent_facts.append(ledger.learn(FactKind.AGENT_FOOD, agent.id, agent.food, state.turn))\n")
        out.append("            agent_facts.append(ledger.learn(FactKind.AGENT_MOOD, agent.id, agent.mood, state.turn))\n")
        out.append("            intent_str = agent.intent.kind if agent.intent else \"none\"\n")
        out.append("            agent_facts.append(ledger.learn(FactKind.AGENT_INTENT, agent.id, intent_str, state.turn))\n")
        out.append("    return learned + (ground, worth) + tuple(agent_facts)\n")
        in_survey = False
    else:
        out.append(line)

with open("src/hearthfall/engine/turn.py", "w") as f:
    f.writelines(out)
