"""ERC-8004 IdentityRegistry: register an agent and read its agentId.

Signatures from the verified IdentityRegistryUpgradeable on Celo (Blockscout, read 2026-11-21) and
docs.celo.org/build/agents/8004:
  register(string agentURI) -> uint256 agentId     (mints the agent NFT to msg.sender)
  event Registered(uint256 indexed agentId, string agentURI, address indexed owner)
Per the Celo docs, take agentId from the Registered event in the receipt, not from the simulated return
value (that is _lastId at simulation time and is wrong if someone else registers first).
"""
from __future__ import annotations

import base64
import json

from eth_abi import decode, encode

from .hashing import keccak

SIG_REGISTER = "register(string)"
TOPIC_REGISTERED = "0x" + keccak(b"Registered(uint256,string,address)").hex()
REGISTRATION_TYPE = "https://eips.ethereum.org/EIPS/eip-8004#registration-v1"


def encode_register(agent_uri: str) -> str:
    return "0x" + (keccak(SIG_REGISTER.encode())[:4] + encode(["string"], [agent_uri])).hex()


def registration_json(name: str, description: str, services: list[dict] | None = None,
                      registrations: list[dict] | None = None, supported_trust: list[str] | None = None,
                      **extra) -> dict:
    doc = {"type": REGISTRATION_TYPE, "name": name, "description": description, "services": services or [],
           "active": True, "supportedTrust": supported_trust or ["validation"]}
    if registrations:
        doc["registrations"] = registrations
    doc.update(extra)
    return doc


def data_uri(doc: dict) -> str:
    raw = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    return "data:application/json;base64," + base64.b64encode(raw).decode()


def decode_data_uri(uri: str) -> bytes:
    return base64.b64decode(uri.split(",", 1)[1])


def registered_from_receipt(receipt: dict, registry: str, owner: str | None = None) -> list[dict]:
    """All Registered events emitted by `registry` in the receipt (optionally only for `owner`)."""
    out = []
    for lg in receipt.get("logs", []):
        t = lg.get("topics", [])
        if lg.get("address", "").lower() != registry.lower() or len(t) != 3 or t[0].lower() != TOPIC_REGISTERED:
            continue
        who = "0x" + t[2][-40:].lower()
        if owner and who != owner.lower():
            continue
        (uri,) = decode(["string"], bytes.fromhex(lg["data"][2:]))
        out.append({"agentId": int(t[1], 16), "owner": who, "agentURI": uri})
    return out
