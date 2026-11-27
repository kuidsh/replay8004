import json

import pytest
from eth_abi import decode, encode

from replay8004 import identity, networks
from replay8004.hashing import keccak
from tests.conftest import VALIDATOR

NET = networks.CELO_SEPOLIA


def test_registration_document():
    doc = identity.registration(network=NET, validator=VALIDATOR, repo="https://github.com/x/replay8004",
                                agent_id=12, evidence_base_url="https://ev.example/evidence")
    assert doc["type"] == identity.REGISTRATION_TYPE and doc["active"] is True
    svc = {s["name"]: s for s in doc["services"]}
    assert svc["replay8004-validator"]["endpoint"] == f"eip155:11142220:{VALIDATOR}"
    assert "replay:x402_settlement" in svc["replay8004-validator"]["tags"]
    assert doc["registrations"] == [{"agentId": 12, "agentRegistry": f"eip155:11142220:{NET.identity}"}]
    assert json.loads(identity.registration_bytes(doc)) == doc


@pytest.mark.parametrize("kw", [{"validator": "0x12"}, {"repo": "http://insecure"}])
def test_registration_rejects_bad_input(kw):
    base = {"network": NET, "validator": VALIDATOR, "repo": "https://github.com/x/r"}
    base.update(kw)
    with pytest.raises(ValueError):
        identity.registration(**base)


def test_register_calldata():
    data = identity.encode_register("ipfs://cid")
    assert data[:10] == "0x" + keccak(b"register(string)")[:4].hex()
    assert decode(["string"], bytes.fromhex(data[10:])) == ("ipfs://cid",)
    d2 = identity.encode_set_uri(5, "https://x")
    assert decode(["uint256", "string"], bytes.fromhex(d2[10:])) == (5, "https://x")


def test_agent_id_from_receipt():
    log = {"address": NET.identity, "topics": [identity.TOPIC_REGISTERED, "0x" + f"{77:064x}", "0x" + "00" * 12 + VALIDATOR[2:]],
           "data": "0x" + encode(["string"], ["ipfs://cid"]).hex()}
    assert identity.agent_id_from_receipt({"logs": [log]}, NET.identity) == 77
    assert identity.decode_registered_uri(log) == "ipfs://cid"
    with pytest.raises(ValueError):
        identity.agent_id_from_receipt({"logs": [dict(log, address=NET.validation)]}, NET.identity)


def test_cli_identity_and_x402_job(tmp_path, capsys):
    from replay8004 import cli, job as jobmod
    from tests.test_x402 import claim
    reg = tmp_path / "reg.json"
    cli.main(["identity", "--validator", VALIDATOR, "--repo", "https://github.com/x/r", "--uri", "ipfs://cid",
              "--out", str(reg)])
    out = json.loads(capsys.readouterr().out)
    assert out["function"] == "register(string)" and json.loads(reg.read_bytes())["name"] == "replay8004 validator"
    c = claim()
    (tmp_path / "req.json").write_text(json.dumps(c["requirements"]))
    cli.main(["job", "x402-settlement", "--agent-id", "9", "--validator", VALIDATOR,
              "--requirements", str(tmp_path / "req.json"), "--settlement", json.dumps(c["settlement"]),
              "--out", str(tmp_path / "job.json")])
    res = json.loads(capsys.readouterr().out)
    raw = (tmp_path / "job.json").read_bytes()
    assert res["requestHash"] == jobmod.request_hash(raw)
    assert json.loads(raw)["claim"]["settlement"]["transaction"] == c["settlement"]["transaction"]
