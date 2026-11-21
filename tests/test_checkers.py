import pytest
from eth_abi import encode

from replay8004.checkers import CHECKERS, Verdict
from replay8004.checkers.erc20 import TRANSFER_TOPIC
from replay8004.hashing import keccak
from tests.conftest import PAYEE, PAYER, USDC, FakeRpc

TX = "0x" + "aa" * 32


def transfer(rpc, **kw):
    claim = {"txHash": TX, "token": USDC, "to": PAYEE, "from": PAYER, "minAmount": "10000", "minConfirmations": 2}
    claim.update(kw)
    return CHECKERS["erc20_transfer"](claim, rpc, Verdict)


def test_transfer_topic_is_the_erc20_event():
    assert TRANSFER_TOPIC == "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def test_transfer_settled():
    rpc = FakeRpc(); rpc.add_transfer(TX, USDC, PAYER, PAYEE, 10_000, block=990)
    v = transfer(rpc)
    assert v.score == 100 and v.observed["confirmations"] == 11 and v.observed["amount"] == "10000"


def test_transfer_partial_amount_scores_proportionally():
    rpc = FakeRpc(); rpc.add_transfer(TX, USDC, PAYER, PAYEE, 2_500, block=990)
    assert transfer(rpc).score == 25


@pytest.mark.parametrize("kw", [{"to": PAYER}, {"from": PAYEE}, {"token": PAYER}])
def test_transfer_wrong_party_or_token(kw):
    rpc = FakeRpc(); rpc.add_transfer(TX, USDC, PAYER, PAYEE, 10_000, block=990)
    v = transfer(rpc, **kw)
    assert v.score == 0 and "no matching Transfer" in v.findings[0]


def test_transfer_reverted_and_missing():
    rpc = FakeRpc(); rpc.add_transfer(TX, USDC, PAYER, PAYEE, 10_000, block=990, status=0)
    assert transfer(rpc).findings == ["transaction reverted"]
    assert transfer(FakeRpc()).findings == ["transaction not found"]


def test_transfer_waits_for_confirmations():
    rpc = FakeRpc(head=1_000); rpc.add_transfer(TX, USDC, PAYER, PAYEE, 10_000, block=1_000)
    assert transfer(rpc, minConfirmations=5) is None
    rpc.head = 1_004
    assert transfer(rpc, minConfirmations=5).score == 100


def test_transfer_rejects_bad_input():
    with pytest.raises(ValueError):
        transfer(FakeRpc(), minAmount="0")
    with pytest.raises(ValueError):
        transfer(FakeRpc(), to="0x123")


def test_balance_claim():
    rpc = FakeRpc(); rpc.set_balance(USDC, PAYEE, 900, 5_000)
    ok = CHECKERS["erc20_balance"]({"token": USDC, "holder": PAYEE, "block": 900, "expected": "5000"}, rpc, Verdict)
    near = CHECKERS["erc20_balance"]({"token": USDC, "holder": PAYEE, "block": 900, "expected": "5003", "tolerance": "5"}, rpc, Verdict)
    bad = CHECKERS["erc20_balance"]({"token": USDC, "holder": PAYEE, "block": 900, "expected": "6000"}, rpc, Verdict)
    assert (ok.score, near.score, bad.score) == (100, 100, 0)


def test_contract_read():
    rpc = FakeRpc()
    data = "0x" + keccak(b"totalSupply()")[:4].hex()
    rpc.calls[(USDC, data, 800)] = "0x" + encode(["uint256"], [123]).hex()
    base = {"to": USDC, "signature": "totalSupply()(uint256)", "block": 800}
    assert CHECKERS["contract_read"](dict(base, expected=["123"]), rpc, Verdict).score == 100
    assert CHECKERS["contract_read"](dict(base, expected=["124"]), rpc, Verdict).score == 0


def test_contract_read_with_address_arg():
    rpc = FakeRpc()
    data = "0x" + keccak(b"balanceOf(address)")[:4].hex() + encode(["address"], [PAYEE]).hex()
    rpc.calls[(USDC, data, 800)] = "0x" + encode(["uint256"], [7]).hex()
    c = {"to": USDC, "signature": "balanceOf(address)(uint256)", "args": [PAYEE], "block": 800, "expected": [7]}
    assert CHECKERS["contract_read"](c, rpc, Verdict).score == 100


def test_contract_read_bad_signature():
    with pytest.raises(ValueError):
        CHECKERS["contract_read"]({"to": USDC, "signature": "totalSupply", "block": 1, "expected": []}, FakeRpc(), Verdict)


def test_verdict_score_bounds():
    with pytest.raises(ValueError):
        Verdict(101)
