import base64
import json

from eth_abi import decode, encode

from replay8004 import identity, networks

REG = networks.CELO_SEPOLIA.identity
OWNER = "0x119d0a02f33f749f07e4acb74a8fb22878f657db"


def test_register_selector_and_topic_match_deployed_contract():
    # register(string) PUSH4 found in IdentityRegistryUpgradeable bytecode; topic seen on 15 real Sepolia logs
    assert identity.encode_register("x")[:10] == "0xf2c298be"
    assert identity.TOPIC_REGISTERED == "0xca52e62c367d81bb2e328eb795f7c7ba24afb478408a26c0e201d155c449bc4a"


def test_encode_register_round_trips_uri():
    uri = "https://example.org/agent.json"
    (got,) = decode(["string"], bytes.fromhex(identity.encode_register(uri)[10:]))
    assert got == uri


def test_registration_json_and_data_uri():
    doc = identity.registration_json("t", "d", registrations=[{"agentId": 7, "agentRegistry": f"eip155:11142220:{REG}"}])
    assert doc["type"] == "https://eips.ethereum.org/EIPS/eip-8004#registration-v1" and doc["active"] is True
    uri = identity.data_uri(doc)
    assert json.loads(base64.b64decode(uri.split(",", 1)[1])) == doc


def _log(agent_id, owner, uri, address=REG):
    return {"address": address, "data": "0x" + encode(["string"], [uri]).hex(),
            "topics": [identity.TOPIC_REGISTERED, "0x" + f"{agent_id:064x}", "0x" + "00" * 12 + owner[2:]]}


def test_registered_from_receipt_filters_registry_and_owner():
    other = "0x" + "77" * 20
    rec = {"logs": [_log(5, other, "a"), _log(9, OWNER, "b"), _log(11, OWNER, "c", address="0x" + "88" * 20),
                    {"address": REG, "topics": ["0x" + "00" * 32], "data": "0x"}]}
    assert identity.registered_from_receipt(rec, REG, OWNER) == [{"agentId": 9, "owner": OWNER, "agentURI": "b"}]
    assert [r["agentId"] for r in identity.registered_from_receipt(rec, REG)] == [5, 9]
