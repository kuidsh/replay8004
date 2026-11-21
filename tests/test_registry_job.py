import base64

import pytest
from eth_abi import decode

from replay8004 import job as jobmod, networks, registry
from replay8004.hashing import keccak
from tests.conftest import VALIDATOR, FakeRpc

H = "0x" + "11" * 32


def test_selectors():
    assert registry.encode_request(VALIDATOR, 1, "u", H)[:10] == "0x" + keccak(registry.SIG_REQUEST.encode())[:4].hex()
    assert registry.encode_response(H, 100, "u", H, "t")[:10] == "0x3d659a96"


def test_response_roundtrip():
    data = registry.encode_response(H, 87, "https://x/e.json", "0x" + "22" * 32, "replay:erc20_transfer")
    rh, score, uri, resp, tag = decode(["bytes32", "uint8", "string", "bytes32", "string"], bytes.fromhex(data[10:]))
    assert (score, uri, tag) == (87, "https://x/e.json", "replay:erc20_transfer") and rh == bytes.fromhex("11" * 32)
    with pytest.raises(ValueError):
        registry.encode_response(H, 101, "", H, "")


def test_decode_request_log():
    rpc = FakeRpc()
    rpc.add_request(networks.CELO_SEPOLIA.validation, VALIDATOR, 42, "data:,x", H, block=10)
    r = registry.decode_request_log(rpc.req_logs[0])
    assert r == {"validator": VALIDATOR, "agentId": 42, "requestHash": H, "requestURI": "data:,x",
                 "blockNumber": 10, "txHash": "0x" + "cd" * 32}


def test_summary_decode():
    from eth_abi import encode
    assert registry.decode_summary("0x" + encode(["uint64", "uint8"], [3, 95]).hex()) == (3, 95)


def test_job_roundtrip_and_hash():
    raw = jobmod.make_job(42, 11142220, "erc20_transfer", {"txHash": "0x1"})
    h = jobmod.request_hash(raw)
    assert jobmod.fetch(jobmod.data_uri(raw)) == raw
    assert jobmod.parse(raw, h, 42, 11142220)["kind"] == "erc20_transfer"
    assert jobmod.make_job(42, 11142220, "erc20_transfer", {"txHash": "0x1"}) == raw  # canonical bytes


@pytest.mark.parametrize("agent,chain,hash_ok,msg", [
    (7, 11142220, True, "agentId"), (42, 42220, True, "chainId"), (42, 11142220, False, "requestHash")])
def test_job_parse_rejects(agent, chain, hash_ok, msg):
    raw = jobmod.make_job(42, 11142220, "erc20_transfer", {})
    with pytest.raises(jobmod.JobError, match=msg):
        jobmod.parse(raw, jobmod.request_hash(raw) if hash_ok else H, agent, chain)


def test_job_unknown_kind_and_size_and_scheme():
    with pytest.raises(jobmod.JobError):
        jobmod.make_job(1, 1, "anything", {})
    big = "data:application/json;base64," + base64.b64encode(b"x" * (jobmod.MAX_JOB_BYTES + 1)).decode()
    with pytest.raises(jobmod.JobError, match="larger"):
        jobmod.fetch(big)
    with pytest.raises(jobmod.JobError, match="https"):
        jobmod.fetch("http://insecure/job.json")


def test_mainnet_is_off_by_default():
    with pytest.raises(RuntimeError, match="REPLAY8004_ALLOW_MAINNET"):
        networks.get("celo-mainnet")
    assert networks.get("celo-mainnet", allow_mainnet=True).chain_id == 42220
    assert networks.get("celo-sepolia").validation == "0x8004Cb1BF31DAf7788923b405b754f57acEB4272"


def test_sender_signs_for_the_right_chain():
    from eth_account import Account
    acct = Account.create()  # throwaway key generated for the test; never funded
    rpc = FakeRpc()
    s = registry.Sender(rpc, 11142220, acct.key.hex())
    tx = s.send(networks.CELO_SEPOLIA.validation, registry.encode_response(H, 100, "u", H, "t"))
    assert tx.startswith("0x") and len(rpc.sent) == 1
    with pytest.raises(RuntimeError, match="chain id"):
        registry.Sender(FakeRpc(chain_id=42220), 11142220, acct.key.hex())
