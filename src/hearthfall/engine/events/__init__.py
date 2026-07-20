"""Event tables and the condition evaluator. See spec.md §6.

`conditions` is the `key op value` evaluator, `loader` turns TOML into `Event` objects with
strict validation, and `table` filters and draws. The engine that reads the corpus is meant
to stay a weekend's work; the corpus is the project.
"""

from __future__ import annotations
