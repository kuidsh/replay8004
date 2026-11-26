import importlib.util
import json
from pathlib import Path

import pytest
from eth_abi import decode

from replay8004 import job as jobmod, networks, registry
from replay8004.checkers.erc20 import TRANSFER_TOPIC

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("request_validation", ROOT / "scripts" / "request_validation.py")
rv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rv)

V = "0x163296ca93f9887dd10e3053ea0459c49a770a86"
PAYEE = "0x2222222222222222222222222222222222222222"


def test_transfer_calldata_is_erc20_transfer():
    data = rv.transfer_calldata(PAYEE, 3 * 10**18)
    assert data[:10] == "0xa9059cbb"
    to, amount = decode(["address", "uint256"], bytes.fromhex(data[10:]))
    assert (to, amount) == (PAYEE, 3 * 10**18)
    with pytest.raises(ValueError):
        rv.transfer_calldata(PAYEE, 0)


def test_build_request_commits_to_the_exact_job_bytes():
    net = networks.CELO_MAINNET
    r = rv.build_request(net, 10141, V, "0x" + "ab" * 32, rv.CELO_TOKEN, PAYEE, 10**16, payer=V, note="t")
    job = json.loads(r["job"])
    assert job["chainId"] == 42220 and job["agentId"] == 10141 and job["kind"] == "erc20_transfer"
    assert job["claim"] == {"txHash": "0x" + "ab" * 32, "token": rv.CELO_TOKEN, "to": PAYEE, "from": V,
                            "minAmount": str(10**16), "minConfirmations": 2}
    assert r["requestHash"] == jobmod.request_hash(r["job"]) and r["to"] == net.validation
    validator, agent, uri, h = decode(["address", "uint256", "string", "bytes32"], bytes.fromhex(r["calldata"][10:]))
    assert r["calldata"][:10] == "0xaaf400c4" and validator == V and agent == 10141
    assert jobmod.fetch(uri) == r["job"] and "0x" + h.hex() == r["requestHash"]
    # what the validator will do with it: the job parses against the on-chain request
    assert jobmod.parse(jobmod.fetch(uri), r["requestHash"], 10141, 42220)["claim"]["to"] == PAYEE


def test_celo_token_constant_and_transfer_topic():
    assert rv.CELO_TOKEN == "0x471EcE3750Da237f93B8E339c536989b8978a438"
    assert TRANSFER_TOPIC == "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    assert registry.TOPIC_REQUEST.startswith("0x530436c3")


@pytest.mark.parametrize("argv", [
    ["--network", "celo-mainnet", "--key-env", "K", "--send", "pay", "--to", PAYEE, "--amount-wei", "5"],
    ["--network", "celo-mainnet", "--key-env", "K", "pay", "--to", PAYEE, "--amount-wei", "5", "--send"],
    ["pay", "--network", "celo-mainnet", "--key-env", "K", "--to", PAYEE, "--amount-wei", "5", "--send"],
])
def test_options_work_before_or_after_the_subcommand(argv):
    # the runbook puts --send at the end; that once failed with "unrecognized arguments"
    a = rv.parse(argv)
    assert (a.cmd, a.network, a.key_env, a.send, a.amount_wei) == ("pay", "celo-mainnet", "K", True, 5)


def test_defaults_and_required_key_env():
    a = rv.parse(["--key-env", "K", "pay", "--to", PAYEE, "--amount-wei", "1"])
    assert (a.network, a.send, a.from_, a.rpc) == ("celo-sepolia", False, None, None)
    with pytest.raises(SystemExit):
        rv.parse(["pay", "--to", PAYEE, "--amount-wei", "1"])
