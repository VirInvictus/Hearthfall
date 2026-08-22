import re

with open('CLAUDE.md', 'r') as f:
    content = f.read()

replacement = """- Engine dataclasses carry `slots=True`, and `frozen=True` too when they are value types.
  This is deliberate (`spec.md` §8): it is a chunk of what a stricter language would have
  given, bought without leaving Python.
- **Deterministic IDs**: Always assign a deterministic `id` incrementally (like `next_household_id` in `Population`) rather than relying on object identity, memory addresses, or list indices (which shift on deletion). This is required so households can map affinities persistently across seasons without breaking the seeded RNG guarantees."""

content = content.replace(
    "- Engine dataclasses carry `slots=True`, and `frozen=True` too when they are value types.\n  This is deliberate (`spec.md` §8): it is a chunk of what a stricter language would have\n  given, bought without leaving Python.",
    replacement
)

with open('CLAUDE.md', 'w') as f:
    f.write(content)
