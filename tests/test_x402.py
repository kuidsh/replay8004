import base64
import json

import pytest

from replay8004 import job as jobmod
from replay8004.checkers import CHECKERS, TAGS, Verdict
from replay8004.checkers.x402 import AUTHORIZATION_USED_TOPIC, decode_header
from replay8004.rpc import ReceiptUnavailable
from tests.conftest import PAYEE, PAYER, USDC, FakeRpc

TX = "0x" + "bb" * 32
NONCE = "0x" + "77" * 32
FACILITATOR = "0x5555555555555555555555555555555555555555"
CHAIN = "eip155:11142220"


def claim(**kw):
    req = {"scheme": "exact", "network": CHAIN, "amount": "10000", "asset": USDC, "payTo": PAYEE,
           "maxTimeoutSeconds": 60, "extra": {"name": "USDC", "version": "2"}}
    st = {"success": True, "transaction": TX, "network": CHAIN, "payer": PAYER, "amount": "10000"}
    req.update(kw.pop("req", {}))
    st.update(kw.pop("st", {}))
    c = {"requirements": req, "settlement": st, "minConfirmations": 2}
    c.update(kw)
    return c


def run(rpc, c):
    return CHECKERS["x402_settlement"](c, rpc, Verdict)


def settled(amount=10_000, **kw):
    rpc = FakeRpc()
    rpc.add_x402_settlement(TX, USDC, PAYER, PAYEE, amount, block=990, nonce=NONCE, **kw)
    return rpc


def test_registered_with_tag():
    assert TAGS["x402_settlement"] == "replay:x402_settlement"


def test_authorization_used_topic():
    # keccak256("AuthorizationUsed(address,bytes32)") from EIP-3009
    assert AUTHORIZATION_USED_TOPIC == "0x98de503528ee59b575ef0c0a2576a82497bfc029a5685b209e9ec333479b10a5"


def test_settled_payment_scores_100():
    v = run(settled(), claim(authorizationNonce=NONCE, facilitator=FACILITATOR))
    assert v.score == 100 and v.observed["moved"] == "10000"
    assert "nonce consumed" in v.findings[1]


def test_base64_header_is_accepted():
    st = {"success": True, "transaction": TX, "network": CHAIN, "payer": PAYER}
    b64 = base64.b64encode(json.dumps(st).encode()).decode().rstrip("=")
    c = claim(); c["settlement"] = b64
    assert run(settled(), c).score == 100
    assert decode_header(json.dumps(st)) == st


def test_underpaid_scores_proportionally():
    assert run(settled(amount=5_000), claim(st={"amount": None})).score == 50


def test_overreported_receipt_scores_zero():
    v = run(settled(amount=5_000), claim(st={"amount": "10000"}))
    assert v.score == 0 and "only 5000 moved" in v.findings[0]


@pytest.mark.parametrize("kw,msg", [
    ({"req": {"network": "eip155:42220"}}, "network mismatch"),
    ({"st": {"network": "eip155:8453"}}, "network mismatch"),
    ({"st": {"success": False, "errorReason": "insufficient_funds"}}, "insufficient_funds"),
    ({"st": {"transaction": ""}}, "no transaction hash"),
    ({"req": {"payTo": PAYER}}, "no Transfer"),
    ({"authorizationNonce": "0x" + "78" * 32}, "nonce was not consumed"),
    ({"facilitator": PAYER}, "not the claimed facilitator"),
])
def test_false_claims_score_zero(kw, msg):
    v = run(settled(), claim(**kw))
    assert v.score == 0 and msg in v.findings[0]


def test_missing_and_reverted():
    with pytest.raises(ReceiptUnavailable):  # a missing receipt is unknown (pruned RPC), never a 0
        run(FakeRpc(), claim())
    rpc = FakeRpc(); rpc.add_x402_settlement(TX, USDC, PAYER, PAYEE, 10_000, block=990, status=0)
    assert "reverted" in run(rpc, claim()).findings[0]


def test_waits_for_confirmations():
    rpc = FakeRpc(head=1_000); rpc.add_x402_settlement(TX, USDC, PAYER, PAYEE, 10_000, block=1_000)
    assert run(rpc, claim(minConfirmations=3)) is None
    rpc.head = 1_002
    assert run(rpc, claim(minConfirmations=3)).score == 100


@pytest.mark.parametrize("kw", [{"req": {"scheme": "upto"}}, {"req": {"amount": "0"}}, {"st": {"payer": None}}])
def test_malformed_claims_raise(kw):
    with pytest.raises(ValueError):
        run(settled(), claim(**kw))


def test_job_kind_accepted():
    raw = jobmod.make_job(7, 11142220, "x402_settlement", claim())
    assert jobmod.parse(raw, jobmod.request_hash(raw), 7, 11142220)["kind"] == "x402_settlement"
