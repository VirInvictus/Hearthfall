import re

with open('src/hearthfall/engine/turn.py', 'r') as f:
    content = f.read()

content = content.replace("    Orders,\n", "")
content = content.replace("from hearthfall.engine.rng import Rng", "from hearthfall.engine.rng import Rng\nfrom hearthfall.engine.orders import Orders")

with open('src/hearthfall/engine/turn.py', 'w') as f:
    f.write(content)
