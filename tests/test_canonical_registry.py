"""replay8004 against the *canonical* ERC-8004 registries, not a mock.

Deploys IdentityRegistryUpgradeable + ValidationRegistryUpgradeable on an in-process EVM exactly as
erc-8004-contracts test/upgradeable.ts does (HardhatMinimalUUPS proxy, then upgradeToAndCall), then
drives them with replay8004's own calldata encoders and reads them back with gate.py, the worker's
log decoder, verify_deployment and ReplayGate.sol.

Needs `node contracts/canonical/build.js` (and `node contracts/build.js` for ReplayGate) plus the
[contracts] extra; skipped otherwise.
"""
import json
from pathlib import Path

import pytest

web3 = pytest.importorskip("web3")
pytest.importorskip("eth_tester")
ROOT = Path(__file__).resolve().parents[1]
CAN = ROOT / "contracts" / "out" / "canonical"
if not (CAN / "ValidationRegistryUpgradeable.json").exists():
    pytest.skip("canonical contracts not compiled (run: node contracts/canonical/build.js)", allow_module_level=True)

from eth_abi import encode  # noqa: E402
from eth_tester.exceptions import TransactionFailed  # noqa: E402
from web3 import Web3  # noqa: E402
from web3.exceptions import ContractLogicError  # noqa: E402

from replay8004 import gate, networks, registry  # noqa: E402
from replay8004.networks import Network  # noqa: E402

REVERT = (TransactionFailed, ContractLogicError, ValueError)
TAG = "replay:x402_settlement"
SKILL_ABI = ROOT / "integrations" / "agent-skills" / "skills" / "8004" / "references" / "validation-registry-abi.json"


def _art(name, d=CAN):
    return json.loads((d / f"{name}.json").read_text())


def _deploy(w3, name, *args, sender, d=CAN):
    a = _art(name, d)
    c = w3.eth.contract(abi=a["abi"], bytecode=a["bytecode"])
    r = w3.eth.wait_for_transaction_receipt(c.constructor(*args).transact({"from": sender, "gas": 9_000_000}))
    return w3.eth.contract(address=r.contractAddress, abi=a["abi"])


def _proxy(w3, impl_name, init_data, sender):
    minimal = _deploy(w3, "HardhatMinimalUUPS", sender=sender)
    init = minimal.encode_abi("initialize", ["0x" + "00" * 20])
    proxy = _deploy(w3, "ERC1967Proxy", minimal.address, init, sender=sender)
    real = _deploy(w3, impl_name, sender=sender)
    m = w3.eth.contract(address=proxy.address, abi=_art("HardhatMinimalUUPS")["abi"])
    m.functions.upgradeToAndCall(real.address, init_data).transact({"from": sender, "gas": 9_000_000})
    return w3.eth.contract(address=proxy.address, abi=_art(impl_name)["abi"])


class W3Rpc:
    """The slice of replay8004.rpc.Rpc that gate.py / verify_deployment use, backed by web3."""

    def __init__(self, w3):
        self.w3 = w3

    def eth_call(self, to, data, block="latest"):
        return "0x" + self.w3.eth.call({"to": Web3.to_checksum_address(to), "data": data}).hex().removeprefix("0x")

    def logs(self, address, topics, frm, to):
        out = self.w3.eth.get_logs({"address": Web3.to_checksum_address(address), "topics": topics,
                                    "fromBlock": frm, "toBlock": to})
        return [{"topics": ["0x" + t.hex().removeprefix("0x") for t in lg["topics"]],
                 "data": "0x" + lg["data"].hex().removeprefix("0x"), "blockNumber": hex(lg["blockNumber"]),
                 "transactionHash": "0x" + lg["transactionHash"].hex().removeprefix("0x")} for lg in out]


@pytest.fixture
def env():
    w3 = Web3(Web3.EthereumTesterProvider())
    deployer, owner, validator, stranger = w3.eth.accounts[:4]
    ident = _proxy(w3, "IdentityRegistryUpgradeable", "0x8129fc1c", deployer)            # initialize()
    vr_init = "0xc4d66de8" + encode(["address"], [ident.address]).hex()                  # initialize(address)
    vr = _proxy(w3, "ValidationRegistryUpgradeable", vr_init, deployer)
    ident.functions.register("ipfs://agent").transact({"from": owner})                    # agentId 0
    net = Network("test", w3.eth.chain_id, "", identity=ident.address.lower(), reputation="0x" + "00" * 20,
                  validation=vr.address.lower(), explorer="", mainnet=False)
    return w3, ident, vr, net, owner, validator, stranger


def _send(w3, frm, to, data):
    r = w3.eth.wait_for_transaction_receipt(
        w3.eth.send_transaction({"from": frm, "to": Web3.to_checksum_address(to), "data": data, "gas": 1_000_000}))
    if r.status != 1:
        raise ValueError("reverted")
    return r


def h(i):
    return "0x" + i.to_bytes(32, "big").hex()


def test_our_calldata_drives_the_canonical_registry(env):
    w3, ident, vr, net, owner, validator, stranger = env
    rpc = W3Rpc(w3)
    r = _send(w3, owner, net.validation, registry.encode_request(validator, 0, "data:application/json,{}", h(1)))
    assert r.status == 1
    logs = rpc.logs(net.validation, [registry.TOPIC_REQUEST, registry.topic_address(validator)], 0, "latest")
    ev = registry.decode_request_log(logs[0])
    assert ev["validator"] == validator.lower() and ev["agentId"] == 0 and ev["requestHash"] == h(1)
    # unanswered: lastUpdate is already set, responseHash is zero -> NO_RESPONSE, not STALE or LOW_SCORE
    ok, why, s = gate.claim_status(rpc, net, h(1), 0, validator, TAG, min_score=90, max_age=10**9)
    assert (ok, why) == (False, gate.NO_RESPONSE) and s["lastUpdate"] > 0
    assert _send(w3, validator, net.validation, registry.encode_response(h(1), 95, "ipfs://ev", h(99), TAG)).status == 1
    ok, why, s = gate.claim_status(rpc, net, h(1), 0, validator, TAG, min_score=90)
    assert ok and why == 0 and s["response"] == 95 and s["tag"] == TAG
    assert gate.record(rpc, net, 0, validator, TAG) == (1, 95)
    assert registry.decode_agent_validations(rpc.eth_call(net.validation, registry.encode_agent_validations(0))) == [h(1)]


def test_canonical_rules_we_rely_on(env):
    w3, ident, vr, net, owner, validator, stranger = env
    rpc = W3Rpc(w3)
    with pytest.raises(REVERT):   # only owner/operator may request
        _send(w3, stranger, net.validation, registry.encode_request(validator, 0, "x", h(2)))
    _send(w3, owner, net.validation, registry.encode_request(validator, 0, "x", h(2)))
    with pytest.raises(REVERT):   # requestHash is global and first-come ("exists")
        _send(w3, owner, net.validation, registry.encode_request(stranger, 0, "y", h(2)))
    with pytest.raises(REVERT):   # only the named validator may answer
        _send(w3, stranger, net.validation, registry.encode_response(h(2), 100, "u", h(9), TAG))
    _send(w3, validator, net.validation, registry.encode_response(h(2), 100, "u", h(9), TAG))
    _send(w3, validator, net.validation, registry.encode_response(h(2), 40, "u2", h(8), TAG))  # overwrite allowed
    assert gate.record(rpc, net, 0, validator, TAG) == (1, 40)
    # a validator the owner controls can't lift the score if consumers pass only trusted validators
    _send(w3, owner, net.validation, registry.encode_request(stranger, 0, "z", h(3)))
    _send(w3, stranger, net.validation, registry.encode_response(h(3), 100, "u", h(7), TAG))
    assert gate.record(rpc, net, 0, validator, TAG) == (1, 40)
    assert registry.decode_summary(rpc.eth_call(net.validation, registry.encode_summary(0, [], TAG))) == (2, 70)


def test_verify_deployment(env):
    w3, ident, vr, net, owner, validator, stranger = env
    rpc = W3Rpc(w3)
    dep = registry.verify_deployment(rpc, net)
    assert dep["identityRegistry"] == net.identity and dep["version"]
    wrong = Network(**{**net.__dict__, "identity": "0x" + "12" * 20})
    with pytest.raises(registry.DeploymentError, match="points at identity registry"):
        registry.verify_deployment(rpc, wrong)
    empty = Network(**{**net.__dict__, "validation": stranger.lower()})        # an EOA: no code
    with pytest.raises(registry.DeploymentError):
        registry.verify_deployment(rpc, empty)


def test_replaygate_on_canonical_registry(env):
    gate_out = ROOT / "contracts" / "out"
    if not (gate_out / "ReplayGate.json").exists():
        pytest.skip("ReplayGate not compiled (run: node contracts/build.js)")
    w3, ident, vr, net, owner, validator, stranger = env
    g = _deploy(w3, "ReplayGate", vr.address, validator, sender=owner, d=gate_out)
    for i, s in enumerate([100, 100, 80]):
        _send(w3, owner, net.validation, registry.encode_request(validator, 0, "x", h(10 + i)))
        _send(w3, validator, net.validation, registry.encode_response(h(10 + i), s, "u", h(50 + i), TAG))
    assert list(g.functions.record(0, TAG).call()) == [3, 93]
    assert g.functions.passes(0, TAG, 3, 90).call()
    _send(w3, owner, net.validation, registry.encode_request(validator, 0, "x", h(20)))   # unanswered
    ok, why = g.functions.claimStatus(bytes.fromhex(h(20)[2:]), 0, TAG, 90, 0).call()
    assert (ok, why) == (False, gate.NO_RESPONSE)
    ok, why = g.functions.claimStatus(bytes.fromhex(h(10)[2:]), 0, TAG, 90, 0).call()
    assert (ok, why) == (True, 0)


def test_skill_abi_matches_canonical_and_our_signatures():
    """The ABI we contribute to celo-org/agent-skills is a subset of the compiled canonical ABI."""
    if not SKILL_ABI.exists():
        pytest.skip("integrations/agent-skills not present")
    canon = {(x["type"], x.get("name"), json.dumps(x.get("inputs"), sort_keys=True))
             for x in _art("ValidationRegistryUpgradeable")["abi"]}
    ours = json.loads(SKILL_ABI.read_text())
    for x in ours:
        key = (x["type"], x.get("name"), json.dumps(
            [{k: v for k, v in i.items()} for i in x.get("inputs", [])], sort_keys=True))
        names = {(t, n) for t, n, _ in canon}
        assert (x["type"], x.get("name")) in names, x.get("name")
    fn = {x["name"]: "(" + ",".join(i["type"] for i in x["inputs"]) + ")" for x in ours if x["type"] == "function"}
    for sig in (registry.SIG_REQUEST, registry.SIG_RESPONSE, registry.SIG_SUMMARY, registry.SIG_STATUS,
                registry.SIG_IDENTITY, registry.SIG_VERSION, registry.SIG_AGENT_VALIDATIONS):
        name = sig.split("(")[0]
        assert name + fn[name] == sig
    assert networks.CELO_MAINNET.validation not in SKILL_ABI.read_text()
