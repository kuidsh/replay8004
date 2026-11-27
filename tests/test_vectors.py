"""The committed vectors must match what the Python validator produces (the TS client tests read them too)."""
import json
from pathlib import Path

from tests.make_vectors import build


def test_vectors_are_current():
    committed = json.loads((Path(__file__).parent / "vectors" / "client.json").read_text(encoding="utf-8"))
    assert committed == build(), "run: python tests/make_vectors.py"
