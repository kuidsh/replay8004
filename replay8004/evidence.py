"""Evidence bundles: what the validator saw, hash-chained so a skipped or edited answer shows.

responseHash posted on-chain = keccak256(canonical(bundle)). Anyone can fetch the bundle from
responseURI, recompute the hash, re-run the checker against the same blocks and follow
`prev` back to the validator's first bundle.
"""
from __future__ import annotations

import json
from pathlib import Path

from .hashing import canonical, hash_obj

SCHEMA = "replay8004/evidence@1"
GENESIS = "0x" + "00" * 32


def build(*, seq: int, prev: str, validator: str, network: str, chain_id: int, agent_id: int,
          request_hash: str, request_uri: str, job: dict | None, kind: str | None, verdict,
          checked_at: str, version: str) -> dict:
    return {"schema": SCHEMA, "seq": seq, "prev": prev, "validator": validator.lower(),
            "network": network, "chainId": chain_id, "agentId": agent_id,
            "requestHash": request_hash.lower(), "requestURI": request_uri[:2048], "job": job,
            "checker": kind, "checkerVersion": version,
            "verdict": {"score": verdict.score, "findings": verdict.findings, "observed": verdict.observed},
            "checkedAt": checked_at}


def response_hash(bundle: dict) -> str:
    return hash_obj(bundle)


def verify_chain(bundles: list[dict]) -> tuple[bool, str]:
    prev, seq = GENESIS, 0
    for b in sorted(bundles, key=lambda x: x["seq"]):
        seq += 1
        if b["seq"] != seq:
            return False, f"gap: expected seq {seq}, found {b['seq']}"
        if b["prev"] != prev:
            return False, f"seq {seq}: prev hash mismatch"
        prev = response_hash(b)
    return True, f"{seq} bundles, chain intact"


class LocalSink:
    """Writes bundles to a folder. In AWS, S3Sink writes to an Object Lock bucket instead."""

    def __init__(self, folder: str | Path, base_url: str):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url.rstrip("/")

    def put(self, bundle: dict) -> str:
        name = f"{bundle['requestHash']}.json"
        (self.folder / name).write_bytes(canonical(bundle))
        return f"{self.base_url}/{name}"

    def all(self) -> list[dict]:
        return [json.loads(p.read_bytes()) for p in self.folder.glob("0x*.json")]


class S3Sink:  # pragma: no cover - needs AWS
    def __init__(self, bucket: str, base_url: str, retain_days: int = 365):
        import boto3
        self.s3, self.bucket, self.base_url, self.retain = boto3.client("s3"), bucket, base_url.rstrip("/"), retain_days

    def put(self, bundle: dict) -> str:
        import datetime as dt
        key = f"evidence/{bundle['requestHash']}.json"
        until = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=self.retain)
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=canonical(bundle), ContentType="application/json",
                           ObjectLockMode="COMPLIANCE", ObjectLockRetainUntilDate=until)
        return f"{self.base_url}/{key}"
