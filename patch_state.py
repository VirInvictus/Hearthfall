import sys

with open("src/hearthfall/engine/state.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == "agents: dict[str, Agent] = field(default_factory=dict)":
        new_lines.append(line)
        new_lines.extend([
            "    tier: str = \"clan\"\n",
            "    next_person_id: int = 1\n",
            "    cast: dict[str, 'Person'] = field(default_factory=dict)\n",
            "    council: 'Council' | None = None\n",
        ])
    else:
        new_lines.append(line)

with open("src/hearthfall/engine/state.py", "w") as f:
    f.writelines(new_lines)
