import sys

with open("src/hearthfall/engine/state.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    new_lines.append(line)
    if line.strip() == "from hearthfall.engine.orders import Orders":
        new_lines.extend([
            "    from hearthfall.engine.people import Person\n",
            "    from hearthfall.engine.tiers import Council\n",
        ])

with open("src/hearthfall/engine/state.py", "w") as f:
    f.writelines(new_lines)
