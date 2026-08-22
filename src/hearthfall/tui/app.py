from __future__ import annotations

import argparse
import os
import pickle
from enum import StrEnum

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.command import Hit, Hits, Provider
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, RichLog, Static

from hearthfall import VERSION
from hearthfall.engine.events.loader import load_corpus
from hearthfall.engine.intel import FactKind
from hearthfall.engine.orders import Orders
from hearthfall.engine.rng import Rng
from hearthfall.engine.state import GameState
from hearthfall.engine.world import Terrain


class GlyphTier(StrEnum):
    ASCII = "ascii"
    UNICODE = "unicode"
    NERD = "nerd"

GLYPHS = {
    GlyphTier.ASCII: { Terrain.PLAIN: ".", Terrain.FOREST: "T", Terrain.HILLS: "^", Terrain.MARSH: "%", Terrain.WATER: "~", "FOG": "░", "HEARTH": "@" },
    GlyphTier.UNICODE: { Terrain.PLAIN: "·", Terrain.FOREST: "♣", Terrain.HILLS: "▲", Terrain.MARSH: "⚑", Terrain.WATER: "≈", "FOG": "░", "HEARTH": "⌂" },
    GlyphTier.NERD: { Terrain.PLAIN: "󰝤", Terrain.FOREST: "󰔎", Terrain.HILLS: "󰎙", Terrain.MARSH: "󰏠", Terrain.WATER: "󰖌", "FOG": "▒", "HEARTH": "󰋜" },
}

COLOURS: dict[Terrain, str] = {
    Terrain.PLAIN: "#a6a69c",
    Terrain.FOREST: "#8a9a7b",
    Terrain.HILLS: "#c0a36e",
    Terrain.MARSH: "#8992a7",
    Terrain.WATER: "#8ba4b0",
}

class ActionProvider(Provider):
    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        actions = [
            ("Orders: Edit Standing Orders", "set_orders"),
            ("Time: Run until Interrupted", "run_season"),
            ("View: Change Glyph Tier", "pick_glyph"),
            ("View: Glyph Test Card (Font Advisor)", "show_test_card"),
            ("System: Save Game", "save_game"),
            ("System: Load Game", "load_game"),
        ]
        for title, action in actions:
            score = matcher.match(title)
            if score > 0:
                yield Hit(score, matcher.highlight(title), lambda a=action: getattr(self.app, "action_dispatch")(a))

class HearthfallApp(App):
    CSS = """
    Screen { background: #181616; color: #c5c9c5; }
    #main { height: 1fr; }
    #rail { width: 40; height: 1fr; overflow-y: auto; background: #1d1c19; padding: 1; }
    #chronicle { height: 1fr; width: 1fr; padding: 1 2; border-left: solid #2d2b28; }
    #status { margin-bottom: 1; }
    ModalScreen { align: center middle; background: #181616 70%; }
    #modal-container { background: #1d1c19; padding: 1 2; border: solid #c0a36e; width: 50; height: auto; }
    """
    
    COMMANDS = App.COMMANDS | {ActionProvider}
    
    BINDINGS = [
        Binding("ctrl+p", "command_palette", "Commands"),
        Binding("q", "quit", "Quit")
    ]
    
    def __init__(self, state: GameState, rng: Rng) -> None:
        super().__init__()
        self.state = state
        self.rng = rng
        self.glyph_tier = GlyphTier.UNICODE
        self.corpus = load_corpus(state.snapshot())

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            with Vertical(id="rail"):
                yield Static(id="status")
                yield Static(id="map")
            yield RichLog(id="chronicle", wrap=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        if not self.state.standing_orders:
            self.state.standing_orders = Orders(is_standing=True)
        self.update_rail()
        log = self.query_one("#chronicle", RichLog)
        log.write(f"[#c0a36e]Hearthfall {VERSION}[/][#625e5a] · seed [/]{self.state.seed}")
        for entry in self.state.chronicle:
            log.write(f"[bold]{entry.season.value.title()}, Year {entry.turn // 4 + 1}[/bold]")
            for line in entry.lines:
                log.write(line)

    def on_resize(self) -> None:
        rail = self.query_one("#rail")
        if self.size.width < 80:
            rail.display = False
        else:
            rail.display = True

    def update_rail(self) -> None:
        st = self.state
        status = f"[bold]Year {st.year}, {st.season.value.title()}[/]\nPeople: {st.population.total} ({st.population.adults} adults)\nFood: {st.stores.food}  Morale: {st.population.morale}/10\n"
        self.query_one("#status", Static).update(status)
        self.query_one("#map", Static).update(self.render_map())
        
    def render_map(self) -> str:
        world = self.state.world
        ledger = self.state.ledger
        target = self.state.standing_orders.scout_target if self.state.standing_orders else None
        lines = []
        g = GLYPHS[self.glyph_tier]
        for y in range(world.height):
            cells = []
            for x in range(world.width):
                coord = (x, y)
                tile = world.tile(coord)
                if coord == world.home:
                    cells.append(f"[bold #c4746e]{g['HEARTH']}[/]")
                elif ledger.knows(FactKind.TERRAIN, coord):
                    style = COLOURS[tile.terrain]
                    if not ledger.knows(FactKind.FORAGE, coord):
                        style = f"dim {style}"
                    cells.append(f"[{style}]{g[tile.terrain]}[/]")
                elif coord == target:
                    cells.append("[bold #c0a36e]?[/]")
                else:
                    cells.append(f"[#3a3733]{g['FOG']}[/]")
            lines.append(" ".join(cells))
        
        # Legend
        lines.append("")
        lines.append(f" {g['HEARTH']} hearth   {g[Terrain.PLAIN]} plain   {g[Terrain.FOREST]} forest")
        lines.append(f" {g[Terrain.HILLS]} hills    {g[Terrain.MARSH]} marsh   {g[Terrain.WATER]} water")
        
        return "\n".join(lines)
        
    def action_dispatch(self, action: str) -> None:
        if action == "run_season":
            self.run_season()
        elif action == "save_game":
            self.save_game()
        elif action == "load_game":
            self.load_game()
        elif action == "show_test_card":
            log = self.query_one("#chronicle", type(self).app.query_one("#chronicle").__class__ if False else __import__("textual.widgets", fromlist=["RichLog"]).RichLog)
            log.write("[bold #c0a36e]Glyph Test Card[/]")
            for t in GlyphTier:
                g = GLYPHS[t]
                log.write(f"{t.value.upper():8} | {g['HEARTH']} {g[Terrain.PLAIN]} {g[Terrain.FOREST]} {g[Terrain.HILLS]} {g[Terrain.MARSH]} {g[Terrain.WATER]} {g['FOG']}")
            log.write("[italic #8ba4b0]Advisor: If you see empty boxes or overlapping characters in Unicode or Nerd tiers, your terminal font lacks those glyphs. Use the command palette (Ctrl+P) to switch to ASCII.[/]")
        elif action == "pick_glyph":
            # cycle tiers for simplicity here
            tiers = list(GlyphTier)
            idx = tiers.index(self.glyph_tier)
            self.glyph_tier = tiers[(idx + 1) % len(tiers)]
            self.update_rail()
        elif action == "set_orders":
            # Just log that it works for now, or you can build a ModalScreen for it
            log = self.query_one("#chronicle", RichLog)
            log.write("[italic #8ba4b0]Standing orders modal not yet fully implemented. Using defaults.[/]")
            
    def run_season(self) -> None:
        if self.state.is_over:
            return
            
        from hearthfall.engine.turn import InterruptReason, run_until_interrupted
        
        start_turn = self.state.turn
        reason = run_until_interrupted(self.state, self.rng, self.corpus)
        
        log = self.query_one("#chronicle", RichLog)
        
        for entry in self.state.chronicle[start_turn:]:
            log.write(f"[bold]{entry.season.value.title()}, Year {entry.turn // 4 + 1}[/bold]")
            if entry.event_title:
                log.write(f"[bold #c0a36e]Event: {entry.event_title}[/]")
            for line in entry.lines:
                log.write(line)
                
        if reason == InterruptReason.STARVATION:
            log.write("[bold #c4746e]Interrupted: Starvation predicted![/]")
        elif reason == InterruptReason.GAME_OVER:
            log.write("[bold #c4746e]The hearth goes out.[/]")
            
        self.update_rail()
        
    def save_game(self) -> None:
        with open("savegame.pkl", "wb") as f:
            pickle.dump((self.state, self.rng), f)
        log = self.query_one("#chronicle", RichLog)
        log.write("[italic #8ba4b0]Game saved to savegame.pkl[/]")
            
    def load_game(self) -> None:
        if os.path.exists("savegame.pkl"):
            with open("savegame.pkl", "rb") as f:
                self.state, self.rng = pickle.load(f)
            self.update_rail()
            log = self.query_one("#chronicle", RichLog)
            log.write("[italic #8ba4b0]Game loaded from savegame.pkl[/]")
            
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()

    seed = args.seed if args.seed else int.from_bytes(os.urandom(8), "little")
    rng = Rng(seed)
    
    from hearthfall.engine.turn import new_game
    state = new_game(seed)
    
    app = HearthfallApp(state, rng)
    app.run()

if __name__ == "__main__":
    main()
