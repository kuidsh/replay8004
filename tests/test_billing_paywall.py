import base64
import json

from replay8004 import billing, networks
from replay8004.evidence import LocalSink
from replay8004.paywall import Paywall
from replay8004.store import MemoryStore
from replay8004.worker import Worker
from tests.conftest import PAYEE, PAYER, VALIDATOR, FakeRpc, FakeSender
from tests.test_worker import CLAIM, TX, request

NET = networks.CELO_SEPOLIA
USDC_SEP = billing.USDC["celo-sepolia"].lower()
PAY_TO = "0x6666666666666666666666666666666666666666"
SETTLE_TX = "0x" + "ee" * 32
NONCE = "0x" + "12" * 32
PLAN = billing.Plan(free_per_month=2)
CLOCK = lambda: "2026-11-26T12:00:00+00:00"  # noqa: E731


class FakeFacilitator:
    def __init__(self, valid=True, success=True, amount=None):
        self.valid, self.success, self.amount, self.calls = valid, success, amount, []

    def verify(self, payload, req):
        self.calls.append(("verify", req))
        return {"isValid": self.valid, "invalidReason": None if self.valid else "invalid_signature", "payer": PAYER}

    def settle(self, payload, req):
        self.calls.append(("settle", req))
        if not self.success:
            return {"success": False, "errorReason": "insufficient_funds", "transaction": "", "network": req["network"]}
        return {"success": True, "transaction": SETTLE_TX, "network": req["network"], "payer": PAYER,
                "amount": self.amount or req["amount"]}


def payment(pack="starter", **over):
    p = PLAN.pack(pack)
    accepted = billing.requirements(NET, p, PAY_TO, PLAN) | over.pop("accepted", {})
    auth = {"from": PAYER, "to": PAY_TO, "value": str(p.price), "validAfter": "0", "validBefore": "9999999999",
            "nonce": NONCE} | over.pop("auth", {})
    body = {"x402Version": 2, "accepted": accepted, "payload": {"signature": "0x" + "99" * 65, "authorization": auth}}
    return base64.b64encode(json.dumps(body).encode()).decode()


def make(fac=None, head=1_000):
    rpc = FakeRpc(chain_id=NET.chain_id, head=head)
    ledger, usage = MemoryStore(default=billing.empty_ledger), MemoryStore(start_block=900)
    pw = Paywall(network=NET, rpc=rpc, ledger_store=ledger, usage_store=usage, facilitator=fac or FakeFacilitator(),
                 pay_to=PAY_TO, plan=PLAN, base_url="https://v.example", clock=CLOCK)
    return rpc, pw, ledger, usage


def ev(method, path, headers=None):
    return {"requestContext": {"http": {"method": method}}, "rawPath": path, "headers": headers or {}}


def settle_onchain(rpc, amount=5_000_000, block=990):
    rpc.add_x402_settlement(SETTLE_TX, USDC_SEP, PAYER, PAY_TO, amount, block, nonce=NONCE)


# -- unit rules ------------------------------------------------------------------
def test_admit_order_free_then_credit_then_hold():
    plan, usage, a, m = billing.Plan(free_per_month=1), {}, "11142220:42", "2026-11"
    assert billing.admit(a, m, 1, usage, plan) == "free"
    billing.consume(a, m, "free", usage)
    assert billing.admit(a, m, 1, usage, plan) == "credit"
    billing.consume(a, m, "credit", usage)
    assert billing.admit(a, m, 1, usage, plan) is None
    assert billing.admit(a, "2026-12", 1, usage, plan) == "free"  # quota resets monthly
    assert billing.admit(a, m, 1, usage, billing.Plan(allowlist=frozenset({a}))) == "allowlist"


def test_pack_economics_beat_per_call_settlement_fee():
    # facilitator: gas + 0.3%, US$0.004 per tx in its config. A pack keeps the fee under 1%.
    for p in billing.Plan().packs:
        fee = 4_000 + p.price * 3 // 1000
        assert fee / p.price < 0.01


# -- paywall -------------------------------------------------------------------------
def test_402_without_payment_lists_exact_requirements():
    _, pw, _, _ = make()
    r = pw.handle(ev("POST", "/v1/credits/42/starter"))
    assert r["statusCode"] == 402
    pr = json.loads(base64.b64decode(r["headers"]["PAYMENT-REQUIRED"]))
    assert pr["x402Version"] == 2 and pr == json.loads(r["body"])
    acc = pr["accepts"][0]
    assert acc == {"scheme": "exact", "network": "eip155:11142220", "amount": "5000000",
                   "asset": billing.USDC["celo-sepolia"], "payTo": PAY_TO, "maxTimeoutSeconds": 300,
                   "extra": {"name": "USDC", "version": "2"}}


def test_paid_and_confirmed_credits_once():
    rpc, pw, ledger, _ = make()
    settle_onchain(rpc)
    r = pw.handle(ev("POST", "/v1/credits/42/starter", {"Payment-Signature": payment()}))
    body = json.loads(r["body"])
    assert r["statusCode"] == 200 and body["state"] == "credited" and body["creditsRemaining"] == 250
    assert json.loads(base64.b64decode(r["headers"]["PAYMENT-RESPONSE"]))["transaction"] == SETTLE_TX
    again = pw.handle(ev("POST", "/v1/credits/42/starter", {"payment-signature": payment()}))
    assert again["statusCode"] == 409
    assert pw.account(42)["purchased"] == 250


def test_pending_until_confirmed_then_reconciled():
    rpc, pw, _, _ = make()
    r = pw.buy(42, "starter", payment())  # facilitator says settled, but the tx isn't on our RPC yet
    assert r["statusCode"] == 202 and json.loads(r["body"])["creditsRemaining"] == 0
    settle_onchain(rpc)
    assert pw.reconcile() == 1 and pw.reconcile() == 0
    assert pw.account(42)["creditsRemaining"] == 250


def test_pending_that_never_lands_is_rejected():
    _, pw, ledger, _ = make()
    pw.max_reconcile_attempts = 3
    assert pw.buy(42, "starter", payment())["statusCode"] == 202
    for _ in range(3):
        assert pw.reconcile() == 0
    assert ledger.load()["payments"]["tx:" + SETTLE_TX]["state"] == "rejected"
    assert pw.account(42)["purchased"] == 0


def test_facilitator_overstatement_is_rejected_by_onchain_check():
    rpc, pw, _, _ = make()
    settle_onchain(rpc, amount=1_000_000)  # only 1 USDC moved
    r = pw.buy(42, "starter", payment())
    assert r["statusCode"] == 402 and pw.account(42)["purchased"] == 0


def test_wrong_terms_never_reach_the_facilitator():
    fac = FakeFacilitator()
    _, pw, _, _ = make(fac)
    for bad in (payment(accepted={"amount": "1"}), payment(accepted={"payTo": PAYER}),
                payment(accepted={"network": "eip155:42220"}), payment(auth={"to": PAYER}),
                payment(auth={"value": "1"}), payment(auth={"nonce": "0x12"}), "not-base64!!"):
        assert pw.buy(42, "starter", bad)["statusCode"] == 402
    assert fac.calls == []


def test_invalid_or_failed_settlement_credits_nothing():
    for fac in (FakeFacilitator(valid=False), FakeFacilitator(success=False)):
        rpc, pw, _, _ = make(fac)
        settle_onchain(rpc)
        assert pw.buy(42, "starter", payment())["statusCode"] == 402
        assert pw.account(42)["purchased"] == 0


def test_routes_and_unknown_pack():
    _, pw, _, _ = make()
    assert pw.handle(ev("GET", "/v1/pricing"))["statusCode"] == 200
    assert json.loads(pw.handle(ev("GET", "/v1/pricing"))["body"])["packs"][0]["perValidationUsd"] == "0.0200"
    assert pw.handle(ev("POST", "/v1/credits/42/huge"))["statusCode"] == 404
    assert pw.handle(ev("GET", "/v1/accounts/abc"))["statusCode"] == 404
    assert json.loads(pw.handle(ev("GET", "/v1/accounts/42"))["body"])["freeRemaining"] == 2


# -- worker in paid mode ---------------------------------------------------------------
# Live worker (FakeSender): a dry run changes no state by design, so holds/expiry/usage are only recorded live.
# Answers go inflight first and become done once reconcile sees them at head - reorg_buffer (hence head += 5).
def paid_worker(tmp_path, ledger, plan=PLAN):
    rpc = FakeRpc(head=1_000)
    w = Worker(network=NET, rpc=rpc, validator=VALIDATOR, sender=FakeSender(rpc), store=MemoryStore(start_block=900),
               sink=LocalSink(tmp_path / "ev", "https://ev.example"), clock=CLOCK,
               billing=billing.Billing(plan, ledger))
    return rpc, w


def test_worker_answers_free_quota_then_holds_then_uses_credits(tmp_path):
    ledger = MemoryStore(default=billing.empty_ledger)
    rpc, w = paid_worker(tmp_path, ledger)
    rpc.add_transfer(TX, "0x" + "77" * 20, PAYER, PAYEE, 10_000, block=940)
    for i in range(3):
        request(rpc, dict(CLAIM, note=str(i)))
    out = w.poll_once()
    assert len(out["answered"]) == 2 and out["held"] == 1
    assert {a["agentId"] for a in out["answered"]} == {42}
    rpc.head += 5
    out = w.poll_once()
    assert out["held"] == 1 and len(out["confirmed"]) == 2  # still not covered; never answered with a 0 for non-payment
    led = billing.empty_ledger()
    billing.record_payment(led, "tx:0x1", {"account": "11142220:42", "credits": 250, "state": "credited"})
    ledger.save(led)
    out = w.poll_once()
    assert len(out["answered"]) == 1 and out["held"] == 0 and out["answered"][0]["paidBy"] == "credit"
    rpc.head += 5
    w.poll_once()
    st = w.store.load()
    assert st["usage"]["11142220:42"] == {"paid": 1, "free": {"2026-11": 2}}
    assert sorted(d["paidBy"] for d in st["done"].values()) == ["credit", "free", "free"]
    assert len(w.sender.sent) == 3  # one tx per answer, never a second one


def test_worker_expires_unpaid_requests_without_answering(tmp_path):
    rpc, w = paid_worker(tmp_path, None, billing.Plan(free_per_month=0, max_hold_polls=2))
    request(rpc, CLAIM)
    assert w.poll_once()["held"] == 1
    out = w.poll_once()
    assert out["expired"] == 1 and out["answered"] == []
    st = w.store.load()
    assert st["pending"] == {} and st["done"] == {} and list(st["expired"].values())[0]["reason"] == "payment_required"
    assert w.sender.sent == [] and not list((tmp_path / "ev").glob("*.json"))  # no gas, no evidence


def test_dry_run_in_paid_mode_changes_no_billing_state(tmp_path):
    rpc, live = paid_worker(tmp_path, None, billing.Plan(free_per_month=1, max_hold_polls=2))
    dry = Worker(network=NET, rpc=rpc, validator=VALIDATOR, store=live.store, clock=CLOCK,
                 sink=LocalSink(tmp_path / "ev", "https://ev.example"), billing=live.billing)
    rpc.add_transfer(TX, "0x" + "77" * 20, PAYER, PAYEE, 10_000, block=940)
    for i in range(2):
        request(rpc, dict(CLAIM, note=str(i)))
    for _ in range(3):  # more polls than max_hold_polls: a dry run must never expire anything
        out = dry.poll_once()
        assert len(out["answered"]) == 1 and out["held"] == 1 and out["expired"] == 0
    st = live.store.load()
    assert st["usage"] == {} and st["expired"] == {} and len(st["pending"]) == 2
    assert all("held" not in r for r in st["pending"].values())
