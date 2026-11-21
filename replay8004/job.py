"""Validation jobs: the off-chain payload an agent commits to with `requestHash`.

The agent (or its owner) publishes the job bytes somewhere the validator can read
(https://, ipfs:// or an inline data: URI) and calls
  validationRequest(validator, agentId, requestURI, keccak256(job bytes)).
"""
from __future__ import annotations

import base64
import json
import urllib.parse
import urllib.request

from .checkers import CHECKERS
from .hashing import canonical, keccak

SCHEMA = "replay8004/job@1"
MAX_JOB_BYTES = 64 * 1024
IPFS_GATEWAY = "https://ipfs.io/ipfs/"


class JobError(ValueError):
    pass


def make_job(agent_id: int, chain_id: int, kind: str, claim: dict, note: str = "") -> bytes:
    if kind not in CHECKERS:
        raise JobError(f"unknown kind {kind}; one of {sorted(CHECKERS)}")
    return canonical({"schema": SCHEMA, "agentId": int(agent_id), "chainId": int(chain_id),
                      "kind": kind, "claim": claim, "note": note[:500]})


def request_hash(job_bytes: bytes) -> str:
    return "0x" + keccak(job_bytes).hex()


def data_uri(job_bytes: bytes) -> str:
    return "data:application/json;base64," + base64.b64encode(job_bytes).decode()


def fetch(uri: str, opener=None) -> bytes:
    if uri.startswith("data:"):
        head, _, payload = uri.partition(",")
        raw = base64.b64decode(payload) if head.endswith(";base64") else urllib.parse.unquote_to_bytes(payload)
    elif uri.startswith(("https://", "ipfs://")):
        url = IPFS_GATEWAY + uri[len("ipfs://"):] if uri.startswith("ipfs://") else uri
        with (opener or urllib.request.urlopen)(url, timeout=15) as r:
            raw = r.read(MAX_JOB_BYTES + 1)
    else:
        raise JobError("requestURI must be https://, ipfs:// or data:")
    if len(raw) > MAX_JOB_BYTES:
        raise JobError(f"job larger than {MAX_JOB_BYTES} bytes")
    return raw


def parse(raw: bytes, expected_hash: str, agent_id: int, chain_id: int) -> dict:
    if request_hash(raw) != expected_hash.lower():
        raise JobError("requestHash does not match keccak256 of the job bytes")
    try:
        job = json.loads(raw)
    except ValueError as e:
        raise JobError(f"job is not JSON: {e}") from e
    if job.get("schema") != SCHEMA:
        raise JobError(f"schema must be {SCHEMA}")
    if int(job.get("agentId", -1)) != agent_id:
        raise JobError("job agentId does not match the on-chain request")
    if int(job.get("chainId", -1)) != chain_id:
        raise JobError("job chainId does not match this network")
    if job.get("kind") not in CHECKERS:
        raise JobError(f"unknown kind {job.get('kind')}")
    return job
