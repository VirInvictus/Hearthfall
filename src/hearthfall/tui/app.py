from __future__ import annotations

import argparse
import os
import pickle
import typing
from enum import StrEnum
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.command import Hit, Hits, Provider
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, RichLog, Static

from hearthfall import VERSION
from hearthfall.engine.chronicle import ChronicleEntry
from hearthfall.engine.events.loader import load_corpus
from hearthfall.engine.intel import FactKind
from hearthfall.engine.orders import Orders
from hearthfall.engine.rng import Rng
from hearthfall.engine.state import GameState
from hearthfall.engine.turn import InterruptReason, apply_choice, run_until_interrupted
from hearthfall.engine.world import Terrain

# One save file, in the user's state directory. A save written to "whatever
# the working directory was" is a save the player cannot find again tomorrow.
SAVE_PATH = Path.home() / ".local" / "state" / "hearthfall" / "savegame.pkl"


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
                yield Hit(
                    score,
                    matcher.highlight(title),
                    lambda a=action: typing.cast(
                        "HearthfallApp", self.app
                    ).action_dispatch(a),
                )


def interrupt_line(reason: InterruptReason) -> str:
    """Why the background run handed control back, as one chronicle line.

    A stop the player is never told the reason for reads as a hang, which is
    exactly what a fired event used to be: the run broke and nothing said why.
    """
    return {
        InterruptReason.EVENT: "[bold #c0a36e]Interrupted: the clan faces a choice.[/]",
        InterruptReason.STARVATION: "[bold #c4746e]Interrupted: Starvation predicted![/]",
        InterruptReason.DIRECTOR: "[bold #c0a36e]Interrupted: the director broke the standing orders. The chronicle tells it.[/]",
        InterruptReason.GAME_OVER: "[bold #c4746e]The hearth goes out.[/]",
    }[reason]


class EventChoiceScreen(ModalScreen[None]):
    """The event the world just put to the clan, and the answers it will take.

    Everything on this screen is engine-formed: title, body, and options are
    `state.pending` (`PendingChoice`), built by the tick that fired the event.
    Choosing calls `turn.apply_choice`, which is the only way a pending choice
    clears; before this screen existed, a fired choice re-interrupted the run
    forever, and the game could not be played past the first event that asked
    a question.
    """

    CSS = """
    EventChoiceScreen { align: center middle; }
    #event-modal { background: #1d1c19; padding: 1 2; border: solid #c0a36e; width: 64; height: auto; max-height: 80%; }
    #event-title { text-style: bold; color: #c0a36e; margin-bottom: 1; }
    #event-body { margin-bottom: 1; }
    EventChoiceScreen Button { width: 100%; margin-bottom: 1; }
    """

    BINDINGS: typing.ClassVar = [
        Binding("escape", "peek", "Read the chronicle", priority=True),
        Binding("1", "answer(0)"),
        Binding("2", "answer(1)"),
        Binding("3", "answer(2)"),
    ]

    def __init__(self, state: GameState) -> None:
        super().__init__()
        self.state = state

    def compose(self) -> ComposeResult:
        pending = self.state.pending
        if (
            pending is None
        ):  # unreachable: the screen is only pushed for a pending choice
            return
        with Vertical(id="event-modal"):
            yield Static(pending.title, id="event-title")
            yield Static(pending.body, id="event-body")
            for index, option in enumerate(pending.options):
                label = f"{index + 1}. {option.text}"
                if option.endorsements:
                    label += "\n" + ", ".join(option.endorsements)
                yield Button(label, id=f"option-{index}")

    def action_peek(self) -> None:
        """Step back over the modal without answering. The choice stays
        pending; the next run puts the question straight back."""
        self.dismiss()

    def action_answer(self, index: int) -> None:
        pending = self.state.pending
        if pending is None or not 0 <= index < len(pending.options):
            return
        option = pending.options[index]
        apply_choice(self.state, index)
        log = self.app.query_one("#chronicle", RichLog)
        taken = option.text
        if option.endorsements:
            taken += f" ({', '.join(option.endorsements)})"
        log.write(f"[#8ea4a2]→ {taken}[/]")
        app = typing.cast("HearthfallApp", self.app)
        app.update_rail()
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id and event.button.id.startswith("option-"):
            self.action_answer(int(event.button.id.removeprefix("option-")))


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
        # Why the last background run stopped. Surfaced for tests, and honest
        # state for any future widget that wants to show it.
        self.last_interrupt: InterruptReason | None = None

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
        log.write(
            f"[#c0a36e]Hearthfall {VERSION}[/][#625e5a] · seed [/]{self.state.seed}"
        )
        for entry in self.state.chronicle:
            self._write_entry(log, entry)

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
        target = (
            self.state.standing_orders.scout_target
            if self.state.standing_orders
            else None
        )
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
        lines.append(
            f" {g['HEARTH']} hearth   {g[Terrain.PLAIN]} plain   {g[Terrain.FOREST]} forest"
        )
        lines.append(
            f" {g[Terrain.HILLS]} hills    {g[Terrain.MARSH]} marsh   {g[Terrain.WATER]} water"
        )

        return "\n".join(lines)

    def action_dispatch(self, action: str) -> None:
        if action == "run_season":
            self.run_season()
        elif action == "save_game":
            self.save_game()
        elif action == "load_game":
            self.load_game()
        elif action == "show_test_card":
            log = self.query_one(
                "#chronicle",
                type(self).app.query_one("#chronicle").__class__
                if False
                else __import__("textual.widgets", fromlist=["RichLog"]).RichLog,
            )
            log.write("[bold #c0a36e]Glyph Test Card[/]")
            for t in GlyphTier:
                g = GLYPHS[t]
                log.write(
                    f"{t.value.upper():8} | {g['HEARTH']} {g[Terrain.PLAIN]} {g[Terrain.FOREST]} {g[Terrain.HILLS]} {g[Terrain.MARSH]} {g[Terrain.WATER]} {g['FOG']}"
                )
            log.write(
                "[italic #8ba4b0]Advisor: If you see empty boxes or overlapping characters in Unicode or Nerd tiers, your terminal font lacks those glyphs. Use the command palette (Ctrl+P) to switch to ASCII.[/]"
            )
        elif action == "pick_glyph":
            # cycle tiers for simplicity here
            tiers = list(GlyphTier)
            idx = tiers.index(self.glyph_tier)
            self.glyph_tier = tiers[(idx + 1) % len(tiers)]
            self.update_rail()
        elif action == "set_orders":
            # Just log that it works for now, or you can build a ModalScreen for it
            log = self.query_one("#chronicle", RichLog)
            log.write(
                "[italic #8ba4b0]Standing orders modal not yet fully implemented. Using defaults.[/]"
            )

    def _write_entry(self, log: RichLog, entry: ChronicleEntry) -> None:
        """One chronicle entry, exactly as the run wrote it: the season
        header, the event, the season's lines, and the answer if one was
        given."""
        log.write(
            f"[bold]{entry.season.value.title()}, Year {entry.turn // 4 + 1}[/bold]"
        )
        if entry.event_title:
            log.write(f"[bold #c0a36e]Event: {entry.event_title}[/]")
        for line in entry.lines:
            log.write(line)
        if entry.choice_taken:
            log.write(f"[#8ea4a2]→ {entry.choice_taken}[/]")

    def _render_chronicle(self) -> None:
        """Rebuild the whole pane from the state's chronicle. Used on mount
        and after a load; before the rewrite, a loaded run kept the old
        run's seasons on screen above its own."""
        log = self.query_one("#chronicle", RichLog)
        log.clear()
        for entry in self.state.chronicle:
            self._write_entry(log, entry)

    def run_season(self) -> None:
        if self.state.is_over:
            return

        start_turn = self.state.turn
        reason = run_until_interrupted(self.state, self.rng, self.corpus)
        self.last_interrupt = reason

        log = self.query_one("#chronicle", RichLog)
        for entry in self.state.chronicle[start_turn:]:
            self._write_entry(log, entry)

        log.write(interrupt_line(reason))
        if reason is InterruptReason.EVENT and self.state.pending is not None:
            self.push_screen(EventChoiceScreen(self.state))

        self.update_rail()

    def save_game(self) -> None:
        """Pickle the state and the rng to one fixed save file.

        The save lives in the user's state directory rather than in whatever
        the working directory happened to be when the game launched, and it
        lands via a temp file and a rename so a crash mid-write cannot leave
        a torn save where a good one used to be.
        """
        SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = SAVE_PATH.with_suffix(".pkl.tmp")
        with open(tmp_path, "wb") as f:
            pickle.dump((self.state, self.rng), f)
        os.replace(tmp_path, SAVE_PATH)
        log = self.query_one("#chronicle", RichLog)
        log.write(f"[italic #8ba4b0]Game saved to {SAVE_PATH}[/]")

    def load_game(self) -> None:
        """Swap in the saved state, or say why not.

        A missing save is a normal state, not an error. An unreadable one
        (truncated, corrupt, or written by an older shape of the game) is
        refused and the running game keeps going; the old code would have
        replaced the live run with the exception mid-load.
        """
        log = self.query_one("#chronicle", RichLog)
        if not SAVE_PATH.exists():
            log.write(f"[italic #8ba4b0]No saved game at {SAVE_PATH}.[/]")
            return
        try:
            with open(SAVE_PATH, "rb") as f:
                state, rng = pickle.load(f)
            if not isinstance(state, GameState) or not isinstance(rng, Rng):
                raise TypeError("not a Hearthfall save")
        except (
            pickle.PickleError,
            EOFError,
            AttributeError,
            ImportError,
            IndexError,
            KeyError,
            TypeError,
            ValueError,
        ):
            # The set of exceptions a corrupt or hostile pickle file can
            # raise while being read, per the pickle module's own docs.
            log.write(
                "[bold #c4746e]The save could not be read. It may be corrupt "
                "or from an older version of the game. This run continues.[/]"
            )
            return
        self.state, self.rng = state, rng
        if not self.state.standing_orders:
            self.state.standing_orders = Orders(is_standing=True)
        # The corpus parses conditions against a state's snapshot for
        # validation only; reload it against the loaded state so the skin
        # carries nothing over from the run it was showing.
        self.corpus = load_corpus(self.state.snapshot())
        self.last_interrupt = None
        self._render_chronicle()
        log.write(f"[italic #8ba4b0]Game loaded from {SAVE_PATH}[/]")
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
