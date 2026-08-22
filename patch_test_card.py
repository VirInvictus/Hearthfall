with open("src/hearthfall/tui/app.py", "r") as f:
    lines = f.readlines()

out = []
for line in lines:
    if '("View: Change Glyph Tier", "pick_glyph"),' in line:
        out.append(line)
        out.append('            ("View: Glyph Test Card (Font Advisor)", "show_test_card"),\n')
    elif 'elif action == "pick_glyph":' in line:
        out.append('        elif action == "show_test_card":\n')
        out.append('            log = self.query_one("#chronicle", type(self).app.query_one("#chronicle").__class__ if False else __import__("textual.widgets", fromlist=["RichLog"]).RichLog)\n')
        out.append('            log.write("[bold #c0a36e]Glyph Test Card[/]")\n')
        out.append('            for t in GlyphTier:\n')
        out.append('                g = GLYPHS[t]\n')
        out.append('                log.write(f"{t.value.upper():8} | {g[\'HEARTH\']} {g[Terrain.PLAIN]} {g[Terrain.FOREST]} {g[Terrain.HILLS]} {g[Terrain.MARSH]} {g[Terrain.WATER]} {g[\'FOG\']}")\n')
        out.append('            log.write("[italic #8ba4b0]Advisor: If you see empty boxes or overlapping characters in Unicode or Nerd tiers, your terminal font lacks those glyphs. Use the command palette (Ctrl+P) to switch to ASCII.[/]")\n')
        out.append(line)
    else:
        out.append(line)

with open("src/hearthfall/tui/app.py", "w") as f:
    f.writelines(out)
