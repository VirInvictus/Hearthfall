with open("README.md", "r") as f:
    lines = f.readlines()

out = []
for line in lines:
    if line.startswith("> **Status:"):
        out.append("> **Status: v0.13.0. Sub-project 3 of ten, in progress.** Playable start to finish, and\n")
    elif line.startswith("`f` `e` `t` assign a job"):
        out.append("Hit `Ctrl+P` to open the command palette, where you can set standing orders, advance the season, change your glyph tier (ascii/unicode/nerd), and save or load the game.\n")
    else:
        out.append(line)

with open("README.md", "w") as f:
    f.writelines(out)
