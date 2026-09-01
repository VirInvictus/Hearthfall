import sys

with open("src/hearthfall/engine/turn.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == "effect = pending.options[index].effect":
        new_lines.extend([
            "    option = pending.options[index]\n",
            "    effect = option.effect\n",
            "    if state.chronicle and state.chronicle[-1].event_title == pending.title:\n",
            "        taken = option.text\n",
            "        if option.endorsements:\n",
            "            names = ', '.join(option.endorsements)\n",
            "            taken += f\" (Endorsed by {names})\"\n",
            "        state.chronicle[-1].choice_taken = taken\n"
        ])
    else:
        new_lines.append(line)

with open("src/hearthfall/engine/turn.py", "w") as f:
    f.writelines(new_lines)
