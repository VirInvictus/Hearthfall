"""Entry point for the Textual app.

Phase 0 is not built yet. This stub exists so the console script declared in
`pyproject.toml` resolves to something honest instead of an import error.
"""

from __future__ import annotations

from hearthfall import VERSION


def main() -> int:
    print(f"Hearthfall {VERSION}: pre-alpha. Phase 0 is not built yet.")
    print("See roadmap.md for what the first playable slice needs.")
    return 0
