"""Worker state: last scanned block, answered requests, pending (undecided) ones, evidence chain head."""
from __future__ import annotations

import json
from pathlib import Path

from .evidence import GENESIS

# Never created, changed or dropped by migrate(): scan progress, what was answered, and the evidence chain.
# A new deployment must continue from exactly these (the next bundle is seq + 1 with prev = head).
PROTECTED = ("last_block", "done", "seq", "head")
# Containers added by later versions, each empty by default: inflight/failed (exactly-once sending, 0.1.1+),
# usage (paid-mode counters, 0.5) and expired (paid-mode requests that were never covered, 0.5).
ADDED = ("pending", "inflight", "failed", "usage", "expired")


def empty(start_block: int) -> dict:
    return {"last_block": start_block - 1, "done": {}, "pending": {}, "inflight": {}, "failed": {},
            "usage": {}, "expired": {}, "seq": 0, "head": GENESIS}


def migrate(st: dict) -> list[str]:
    """Bring a state written by an older version up to date, in place. Adds missing keys only.

    Refuses a state that lacks one of PROTECTED: inventing scan progress or a chain head would re-answer old
    requests or fork the evidence chain. Returns the keys it added (empty when the state is already current).
    """
    missing = [k for k in PROTECTED if k not in st]
    if missing:
        raise ValueError(f"state is missing {missing}; refusing to guess (it would re-answer or fork the chain)")
    added = [k for k in ADDED if k not in st]
    for k in added:
        st[k] = {}
    return added


class FileStore:
    def __init__(self, path: str | Path, start_block: int = 0, default=None):
        self.path, self.start, self.default = Path(path), start_block, default

    def _empty(self) -> dict:
        return self.default() if self.default else empty(self.start)

    def load(self) -> dict:
        return json.loads(self.path.read_text()) if self.path.exists() else self._empty()

    def save(self, st: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(st, sort_keys=True))
        tmp.replace(self.path)


class DynamoStore:  # pragma: no cover - needs AWS
    """One item; conditional write on a version so two overlapping Lambdas can't both answer."""

    def __init__(self, table: str, key: str = "worker", start_block: int = 0, default=None):
        import boto3
        self.t, self.key, self.start = boto3.resource("dynamodb").Table(table), key, start_block
        self.default, self._ver = default, 0

    def load(self) -> dict:
        item = self.t.get_item(Key={"pk": self.key}).get("Item")
        if not item:
            self._ver = 0
            return self.default() if self.default else empty(self.start)
        self._ver = int(item["ver"])
        return json.loads(item["state"])

    def save(self, st: dict) -> None:
        self.t.put_item(Item={"pk": self.key, "ver": self._ver + 1, "state": json.dumps(st, sort_keys=True)},
                        ConditionExpression="attribute_not_exists(pk) OR ver = :v",
                        ExpressionAttributeValues={":v": self._ver})
        self._ver += 1


class MemoryStore:
    """In-process store (tests, local demos)."""

    def __init__(self, default=None, start_block: int = 0):
        self.default, self.start, self.data = default, start_block, None

    def load(self) -> dict:
        if self.data is None:
            return self.default() if self.default else empty(self.start)
        return json.loads(self.data)

    def save(self, st: dict) -> None:
        self.data = json.dumps(st, sort_keys=True)
