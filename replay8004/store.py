"""Worker state: last scanned block, answered requests, pending (undecided) ones, evidence chain head."""
from __future__ import annotations

import json
from pathlib import Path

from .evidence import GENESIS


def empty(start_block: int) -> dict:
    return {"last_block": start_block - 1, "done": {}, "pending": {}, "inflight": {}, "failed": {},
            "seq": 0, "head": GENESIS}


class FileStore:
    def __init__(self, path: str | Path, start_block: int = 0):
        self.path, self.start = Path(path), start_block

    def load(self) -> dict:
        return json.loads(self.path.read_text()) if self.path.exists() else empty(self.start)

    def save(self, st: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(st, sort_keys=True))
        tmp.replace(self.path)


class DynamoStore:  # pragma: no cover - needs AWS
    """One item; conditional write on a version so two overlapping Lambdas can't both answer."""

    def __init__(self, table: str, key: str = "worker", start_block: int = 0):
        import boto3
        self.t, self.key, self.start = boto3.resource("dynamodb").Table(table), key, start_block
        self._ver = 0

    def load(self) -> dict:
        item = self.t.get_item(Key={"pk": self.key}).get("Item")
        if not item:
            self._ver = 0
            return empty(self.start)
        self._ver = int(item["ver"])
        return json.loads(item["state"])

    def save(self, st: dict) -> None:
        self.t.put_item(Item={"pk": self.key, "ver": self._ver + 1, "state": json.dumps(st, sort_keys=True)},
                        ConditionExpression="attribute_not_exists(pk) OR ver = :v",
                        ExpressionAttributeValues={":v": self._ver})
        self._ver += 1
