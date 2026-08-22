from __future__ import annotations

import argparse
import os
import pickle
import typing
from enum import StrEnum

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.command import Hit, Hits, Provider
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, RichLog, Static

from hearthfall.engine.events.loader import load_corpus
from hearthfall.engine.orders import Orders
from hearthfall.engine.rng import Rng
from hearthfall.engine.state import GameState
from hearthfall.engine.world import Terrain


class GlyphTier(StrEnum):
    ASCII = "ascii"
    UNICODE = "unicode"
    NERD = "nerd"


GLYPHS = {
    GlyphTier.ASCII: {
        Terrain.PLAIN: ".",
        Terrain.FOREST: "T",
        Terrain.HILLS: "^",
        Terrain.MARSH: "%",
        Terrain.WATER: "~",
        "FOG": "░",
        "HEARTH": "@",
    },
    GlyphTier.UNICODE: {
        Terrain.PLAIN: "·",
        Terrain.FOREST: "♣",
        Terrain.HILLS: "▲",
        Terrain.MARSH: "⚑",
        Terrain.WATER: "≈",
        "FOG": "░",
        "HEARTH": "⌂",
    },
    GlyphTier.NERD: {
        Terrain.PLAIN: "󰝤",
        Terrain.FOREST: "󰔎",
        Terrain.HILLS: "󰎙",
        Terrain.MARSH: "󰏠",
        Terrain.WATER: "󰖌",
        "FOG": "▒",
        "HEARTH": "󰋜",
    },
}


class ActionProvider(Provider):
    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        actions = [
            ("Set standing orders", "set_orders"),
            ("Start season (Run)", "run_season"),
            ("Change glyph tier", "pick_glyph"),
            ("Save game", "save_game"),
            ("Load game", "load_game"),
        ]
        for title, action in actions:
            score = matcher.match(title)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(title),
                    lambda a=action: typing.cast(
                        "HearthfallApp", self.app
                    ).action_dispatch(a),
                )


class HearthfallApp(App):
    CSS = """
    Screen { background: #181616; color: #c5c9c5; }
    #main { height: 1fr; }
    #rail { width: 40; overflow-y: auto; background: #1d1c19; padding: 1; }
    #chronicle { height: 1fr; }
    """

    COMMANDS = App.COMMANDS | {ActionProvider}

    BINDINGS: typing.ClassVar = [
        Binding("ctrl+p", "command_palette", "Commands"),
        Binding("q", "quit", "Quit"),
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
        self.update_rail()
        if not self.state.standing_orders:
            self.state.standing_orders = Orders(is_standing=True)

    def update_rail(self) -> None:
        # Status
        st = self.state
        status = f"Year {st.year}, {st.season.value.title()}\nPeople: {st.population.total}\nFood: {st.stores.food}"
        self.query_one("#status", Static).update(status)

        # Map
        lines = []
        # basic map rendering for now...

        self.query_one("#map", Static).update("\n".join(lines))

    def action_dispatch(self, action: str) -> None:
        if action == "run_season":
            self.run_season()
        elif action == "save_game":
            self.save_game()
        elif action == "load_game":
            self.load_game()

    def run_season(self) -> None:
        from hearthfall.engine.turn import run_until_interrupted

        _reason = run_until_interrupted(self.state, self.rng, self.corpus)
        log = self.query_one("#chronicle", RichLog)

        # append the new chronicle entries to the UI
        for entry in self.state.chronicle:
            log.write(
                f"[bold]{entry.season.value.title()}, Year {entry.turn // 4}[/bold]"
            )
            for line in entry.lines:
                log.write(line)

        self.update_rail()

    def save_game(self) -> None:
        with open("savegame.pkl", "wb") as f:
            pickle.dump((self.state, self.rng), f)

    def load_game(self) -> None:
        if os.path.exists("savegame.pkl"):
            with open("savegame.pkl", "rb") as f:
                self.state, self.rng = pickle.load(f)
            self.update_rail()


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
