"""MCP tools: unsigned calldata only, and the read tools against the canonical registry."""
import asyncio
import json

import pytest

from replay8004 import job as jobmod, networks, registry, tools
from tests.conftest import PAYEE, USDC, VALIDATOR

NET = networks.CELO_SEPOLIA
CLAIM = {"txHash": "0x" + "ab" * 32, "token": USDC, "to": PAYEE, "minAmount": "10000", "minConfirmations": 2}


def test_build_request_is_unsigned_and_hash_matches():
    out = tools.build_request(NET, 42, VALIDATOR, "erc20_transfer", CLAIM, note="n1")
    raw = jobmod.fetch(out["requestURI"])
    assert jobmod.request_hash(raw) == out["requestHash"]
    assert out["tx"]["to"] == NET.validation and out["tx"]["value"] == "0"
    assert out["tx"]["data"] == registry.encode_request(VALIDATOR, 42, out["requestURI"], out["requestHash"])
    assert set(out) >= {"job", "tag", "send_from"} and "signature" not in json.dumps(out).lower()
    with pytest.raises(ValueError):
        tools.build_request(NET, 42, VALIDATOR, "run_my_code", {})


def test_mcp_server_exposes_only_safe_tools(monkeypatch):
    pytest.importorskip("mcp")
    from replay8004 import mcp_server
    monkeypatch.setenv("REPLAY8004_VALIDATOR", VALIDATOR)
    srv = mcp_server.build_server()
    names = {t.name for t in asyncio.run(srv.list_tools())}
    assert names == {"request_validation", "check_claim", "agent_track_record", "list_agent_validations", "registry_check"}
    res = asyncio.run(srv.call_tool("request_validation", {"agent_id": 42, "kind": "erc20_transfer", "claim": CLAIM}))
    text = json.dumps(res, default=str)
    assert NET.validation in text and "requestHash" in text


def test_mcp_refuses_mainnet_without_flag(monkeypatch):
    pytest.importorskip("mcp")
    from replay8004 import mcp_server
    monkeypatch.setenv("REPLAY8004_NETWORK", "celo-mainnet")
    monkeypatch.delenv("REPLAY8004_ALLOW_MAINNET", raising=False)
    with pytest.raises(RuntimeError):
        mcp_server._ctx()


def test_read_tools_on_canonical_registry():
    pytest.importorskip("web3")
    from tests import test_canonical_registry as c
    if not (c.CAN / "ValidationRegistryUpgradeable.json").exists():
        pytest.skip("canonical contracts not compiled")
    from web3 import Web3
    w3 = Web3(Web3.EthereumTesterProvider())
    deployer, owner, validator = w3.eth.accounts[:3]
    ident = c._proxy(w3, "IdentityRegistryUpgradeable", "0x8129fc1c", deployer)
    from eth_abi import encode
    vr = c._proxy(w3, "ValidationRegistryUpgradeable", "0xc4d66de8" + encode(["address"], [ident.address]).hex(), deployer)
    ident.functions.register("ipfs://a").transact({"from": owner})
    net = networks.Network("t", w3.eth.chain_id, "", identity=ident.address.lower(), reputation="0x" + "00" * 20,
                           validation=vr.address.lower(), explorer="", mainnet=False)
    rpc = c.W3Rpc(w3)
    req = tools.build_request(net, 0, validator, "erc20_transfer", CLAIM)
    c._send(w3, owner, req["tx"]["to"], req["tx"]["data"])                      # what the owner's wallet would send
    assert tools.claim_status(rpc, net, req["requestHash"], 0, validator, req["tag"], 90)["reasonText"] == "not answered yet"
    c._send(w3, validator, net.validation, registry.encode_response(req["requestHash"], 100, "u", "0x" + "11" * 32, req["tag"]))
    assert tools.claim_status(rpc, net, req["requestHash"], 0, validator, req["tag"], 90)["ok"]
    assert tools.agent_record(rpc, net, 0, validator, req["tag"], min_count=1)["passes"]
    assert tools.agent_validations(rpc, net, 0)["requestHashes"] == [req["requestHash"]]
    assert tools.registry_info(rpc, net)["ok"]
