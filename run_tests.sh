#!/bin/sh
# Run the stdlib unittest suite. Through uv, because the skin's pilot tests
# import Textual and that lives in the project venv, not in ambient python.
set -e
cd "$(dirname "$0")"
PYTHONPATH=src uv run python3 -m unittest discover -s tests -v
