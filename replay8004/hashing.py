"""Hashing helpers. ERC-8004 commits to off-chain payloads with keccak256."""
from __future__ import annotations

import json

from eth_hash.auto import keccak as _keccak


def keccak(data: bytes) -> bytes:
    return _keccak(data)


def canonical(obj) -> bytes:
    """Deterministic JSON bytes: sorted keys, no whitespace, UTF-8. Hash this, never pretty JSON."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def hash_obj(obj) -> str:
    return "0x" + keccak(canonical(obj)).hex()


def hex32(h: str) -> bytes:
    b = bytes.fromhex(h[2:] if h.startswith("0x") else h)
    if len(b) != 32:
        raise ValueError("expected 32 bytes")
    return b
