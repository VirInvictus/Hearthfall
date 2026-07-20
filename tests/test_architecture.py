"""The invariants from spec.md §9, enforced mechanically.

The engine/skin separation is the thing that lets the game be tested, driven from a REPL,
and re-skinned later. It rots silently: one convenient import and it is gone. So it is a
test, not a promise.
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent / "src" / "hearthfall" / "engine"


def engine_modules() -> list[Path]:
    return sorted(ENGINE.rglob("*.py"))


def imports_of(path: Path) -> set[str]:
    """Every absolute module name imported by a file. Relative imports stay inside the
    engine by construction, so they are not interesting here."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module)
    return names


class TestEngineIsolation(unittest.TestCase):
    def test_there_are_engine_modules_to_check(self):
        # Guards against this whole file passing vacuously if the tree moves.
        self.assertTrue(engine_modules(), f"no engine modules found under {ENGINE}")

    def test_engine_imports_no_third_party_modules(self):
        allowed = sys.stdlib_module_names | {"hearthfall"}
        for module in engine_modules():
            for name in imports_of(module):
                root = name.split(".")[0]
                self.assertIn(
                    root,
                    allowed,
                    f"{module.name} imports third-party module {name!r}; "
                    "the engine is stdlib-only (spec.md §9.2)",
                )

    def test_engine_never_imports_the_frontend(self):
        for module in engine_modules():
            for name in imports_of(module):
                self.assertFalse(
                    name.startswith("hearthfall.tui"),
                    f"{module.name} imports {name!r}; "
                    "the engine may not know the frontend exists (spec.md §9.1)",
                )

    def test_only_rng_touches_the_random_module(self):
        for module in engine_modules():
            if module.name == "rng.py":
                continue
            roots = {name.split(".")[0] for name in imports_of(module)}
            self.assertNotIn(
                "random",
                roots,
                f"{module.name} imports random directly; every draw goes through "
                "engine/rng.py so runs reproduce (spec.md §9.3)",
            )
            self.assertNotIn("secrets", roots, f"{module.name} imports secrets")


if __name__ == "__main__":
    unittest.main()
