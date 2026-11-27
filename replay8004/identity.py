"""ERC-8004 IdentityRegistry: register an agent and read its agentId.

Signatures from the verified IdentityRegistryUpgradeable on Celo (Blockscout, read 2026-11-21) and
docs.celo.org/build/agents/8004:
  register(string agentURI) -> uint256 agentId     (mints the agent NFT to msg.sender)
  setAgentURI(uint256 agentId, string newURI)
  event Registered(uint256 indexed agentId, string agentURI, address indexed owner)
Registration file (EIP-8004): type, name, description, image, services[{name, endpoint, version?}], x402Support,
active, registrations[{agentId, agentRegistry: "{namespace}:{chainId}:{identityRegistry}"}], supportedTrust.
EIP-8004 defines no way for a validator to advertise itself, so registration() publishes a "replay8004-validator"
service whose endpoint is the CAIP-10 account to name in validationRequest, plus the job schema and the tags.
Per the Celo docs, take agentId from the Registered event in the receipt, not from the simulated return
value (that is _lastId at simulation time and is wrong if someone else registers first).
"""
from __future__ import annotations

import base64
import json

from eth_abi import decode, encode

from .checkers import TAGS
from .hashing import canonical, keccak
from .job import SCHEMA

SIG_REGISTER = "register(string)"
SIG_SET_URI = "setAgentURI(uint256,string)"
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


# -- validator self-registration (v0.5) ------------------------------------------------------------
def registration(*, network, validator: str, repo: str, image: str = "", agent_id: int | None = None,
                 evidence_base_url: str = "", name: str = "replay8004 validator") -> dict:
    v = validator.lower()
    if not (v.startswith("0x") and len(v) == 42):
        raise ValueError("validator must be a 0x address")
    if not repo.startswith("https://"):
        raise ValueError("repo must be an https:// URL")
    doc = {
        "type": REGISTRATION_TYPE,
        "name": name,
        "description": ("Re-execution validator for the ERC-8004 Validation Registry on Celo. Name the "
                        "replay8004-validator account below as validatorAddress in validationRequest. Jobs follow "
                        f"{SCHEMA}; answers are 0-100 with public, hash-chained evidence. Claim kinds: "
                        + ", ".join(sorted(TAGS)) + "."),
        "image": image,
        "services": [
            {"name": "web", "endpoint": repo},
            {"name": "replay8004-validator", "endpoint": f"eip155:{network.chain_id}:{v}", "version": SCHEMA,
             "tags": sorted(TAGS.values()), "validationRegistry": f"eip155:{network.chain_id}:{network.validation}"},
        ],
        "x402Support": False,
        "active": True,
        "registrations": [],
        "supportedTrust": [],
    }
    if evidence_base_url:
        doc["services"].append({"name": "evidence", "endpoint": evidence_base_url})
    if agent_id is not None:
        doc["registrations"].append({"agentId": int(agent_id),
                                     "agentRegistry": f"eip155:{network.chain_id}:{network.identity}"})
    return doc


def registration_bytes(doc: dict) -> bytes:
    return canonical(doc)


def encode_set_uri(agent_id: int, uri: str) -> str:
    return "0x" + (keccak(SIG_SET_URI.encode())[:4] + encode(["uint256", "string"], [int(agent_id), uri])).hex()


def agent_id_from_receipt(receipt: dict, identity_registry: str) -> int:
    """The new agentId from the Registered event in a register() receipt."""
    found = registered_from_receipt(receipt, identity_registry)
    if not found:
        raise ValueError("no Registered event from the Identity Registry in this receipt")
    return found[0]["agentId"]


def decode_registered_uri(log: dict) -> str:
    (uri,) = decode(["string"], bytes.fromhex(log["data"][2:]))
    return uri
