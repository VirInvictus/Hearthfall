import sys

with open("src/hearthfall/engine/people.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == "class Trait(StrEnum):":
        new_lines.extend([
            "class Ambition(StrEnum):\n",
            "    CAUTIOUS = 'cautious'\n",
            "    MILITARISTIC = 'militaristic'\n",
            "    EXPANSIONIST = 'expansionist'\n",
            "    COMMUNAL = 'communal'\n",
            "\n\n",
            "@dataclass(slots=True)\n",
            "class Person:\n",
            "    \"\"\"A named member of the cast, drawn from a household.\"\"\"\n",
            "    id: str\n",
            "    name: str\n",
            "    household_id: int\n",
            "    age: int\n",
            "    trait: Trait\n",
            "    ambition: Ambition\n",
            "    alive: bool = True\n",
            "\n\n"
        ])
    new_lines.append(line)

with open("src/hearthfall/engine/people.py", "w") as f:
    f.writelines(new_lines)
