"""ReplayGate.sol against a mock registry on an in-process EVM (py-evm via eth-tester).

Needs `node contracts/build.js` first (CI does it) and the [contracts] extra; skipped otherwise.
"""
import json
from pathlib import Path

import pytest

web3 = pytest.importorskip("web3")
pytest.importorskip("eth_tester")
OUT = Path(__file__).resolve().parents[1] / "contracts" / "out"
if not (OUT / "ReplayGate.json").exists():
    pytest.skip("contracts not compiled (run: node contracts/build.js)", allow_module_level=True)

from web3 import Web3  # noqa: E402
from eth_tester.exceptions import TransactionFailed  # noqa: E402
from web3.exceptions import ContractCustomError, ContractLogicError  # noqa: E402

REVERT = (TransactionFailed, ContractCustomError, ContractLogicError)

TAG = "replay:x402_settlement"


def _art(name):
    return json.loads((OUT / f"{name}.json").read_text())


def _deploy(w3, name, *args, sender):
    a = _art(name)
    c = w3.eth.contract(abi=a["abi"], bytecode=a["bytecode"])
    rcpt = w3.eth.wait_for_transaction_receipt(c.constructor(*args).transact({"from": sender}))
    return w3.eth.contract(address=rcpt.contractAddress, abi=a["abi"])


@pytest.fixture
def env():
    w3 = Web3(Web3.EthereumTesterProvider())
    deployer, validator, other, agent_owner = w3.eth.accounts[:4]
    reg = _deploy(w3, "MockValidationRegistry", sender=deployer)
    gate = _deploy(w3, "ReplayGate", reg.address, validator, sender=deployer)
    esc = _deploy(w3, "EscrowExample", reg.address, validator, sender=deployer)

    def answer(agent, h, score, tag=TAG, by=None):
        reg.functions.request(by or validator, agent, h).transact({"from": agent_owner})
        reg.functions.respond(h, score, b"\x11" * 32, tag).transact({"from": by or validator})

    return w3, reg, gate, esc, answer, validator, other


def h(i):
    return i.to_bytes(32, "big")


def test_record_and_passes(env):
    w3, reg, gate, esc, answer, v, other = env
    assert gate.functions.record(7, TAG).call() == [0, 0]
    assert not gate.functions.passes(7, TAG, 0, 0).call()        # no history never passes
    for i, s in enumerate([100, 100, 80]):
        answer(7, h(i + 1), s)
    assert gate.functions.record(7, TAG).call() == [3, 93]        # integer average, like the registry
    assert gate.functions.passes(7, TAG, 3, 90).call()
    assert not gate.functions.passes(7, TAG, 4, 90).call()
    assert not gate.functions.passes(7, TAG, 3, 95).call()
    assert not gate.functions.passes(7, "replay:erc20_balance", 1, 0).call()
    assert gate.functions.passes(7, "", 3, 90).call()              # "" = any tag


def test_other_validators_do_not_count(env):
    w3, reg, gate, esc, answer, v, other = env
    for i in range(3):
        answer(9, h(10 + i), 100, by=other)
    assert gate.functions.record(9, TAG).call() == [0, 0]


def test_claim_status_reasons(env):
    w3, reg, gate, esc, answer, v, other = env
    answer(5, h(1), 100)
    assert gate.functions.claimStatus(h(1), 5, TAG, 100, 3600).call() == [True, 0]
    assert gate.functions.claimStatus(h(1), 6, TAG, 0, 0).call() == [False, 2]
    assert gate.functions.claimStatus(h(1), 5, "replay:erc20_balance", 0, 0).call() == [False, 6]
    answer(5, h(2), 60)
    assert gate.functions.claimStatus(h(2), 5, TAG, 90, 0).call() == [False, 4]
    reg.functions.request(v, 5, h(3)).transact({"from": w3.eth.accounts[3]})   # requested, not answered
    assert gate.functions.claimStatus(h(3), 5, "", 0, 0).call() == [False, 3]
    answer(5, h(4), 100, by=other)
    assert gate.functions.claimStatus(h(4), 5, "", 0, 0).call() == [False, 1]
    with pytest.raises(REVERT, match="unknown"):
        gate.functions.claimStatus(h(99), 5, "", 0, 0).call()                  # unknown request reverts


def test_claim_goes_stale(env):
    w3, reg, gate, esc, answer, v, other = env
    answer(5, h(1), 100)
    w3.provider.ethereum_tester.time_travel(w3.eth.get_block("latest")["timestamp"] + 2 * 86400)
    w3.provider.ethereum_tester.mine_blocks(1)
    assert gate.functions.claimStatus(h(1), 5, TAG, 100, 86400).call() == [False, 5]
    assert gate.functions.claimStatus(h(1), 5, TAG, 100, 0).call() == [True, 0]


def test_escrow_example_modifiers(env):
    w3, reg, gate, esc, answer, v, other = env
    bidder = w3.eth.accounts[5]
    with pytest.raises(REVERT):
        esc.functions.bid(1, 42).transact({"from": bidder})                    # no record yet
    for i in range(3):
        answer(42, h(20 + i), 100)
    esc.functions.bid(1, 42).transact({"from": bidder})
    assert esc.functions.bids(1).call() == 42
    answer(42, h(30), 95)                                                      # payment only partly verified
    with pytest.raises(REVERT):
        esc.functions.markPaid(1, h(30)).transact({"from": bidder})
    answer(42, h(31), 100)
    esc.functions.markPaid(1, h(31)).transact({"from": bidder})
    assert esc.functions.paid(1).call()


def test_constructor_rejects_zero():
    w3 = Web3(Web3.EthereumTesterProvider())
    with pytest.raises(Exception):
        _deploy(w3, "ReplayGate", "0x" + "00" * 20, w3.eth.accounts[1], sender=w3.eth.accounts[0])
