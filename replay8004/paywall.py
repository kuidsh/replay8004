"""x402 paywall for validation credits: an HTTP handler for a Lambda Function URL (not deployed).

Routes
  GET  /v1/pricing                       packs, free quota, network, payTo
  GET  /v1/accounts/<agentId>            free remaining this month, credits purchased / used / remaining
  POST /v1/credits/<agentId>/<packId>    no PAYMENT-SIGNATURE -> 402 + PAYMENT-REQUIRED (base64 JSON)
                                         with PAYMENT-SIGNATURE -> verify, settle, re-check on-chain, credit

Buying credits, step by step (x402 v2, scheme exact, USDC by EIP-3009):
  1. the client's `accepted` must equal the requirements we issue (scheme, network, amount, asset, payTo)
  2. the signed authorization must pay payTo exactly that amount
  3. facilitator POST /verify, then POST /settle (X-API-Key; Celo docs, read 2026-11-26)
  4. we do not trust the facilitator's word: the settlement is re-checked with our own x402_settlement
     checker against Celo (Transfer payer -> payTo, amount, the EIP-3009 nonce consumed in that tx)
  5. credits are added once per payment, keyed by tx hash AND authorization nonce. Not confirmed yet
     -> recorded as pending (HTTP 202) and credited by reconcile() on a later call.
The handler holds no key that can move funds: the facilitator pays gas, USDC goes straight to payTo.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.request

from . import billing
from .checkers import Verdict
from .checkers.x402 import check_x402_settlement

log = logging.getLogger("replay8004.paywall")
_ROUTE_CREDITS = re.compile(r"^/v1/credits/(\d{1,30})/([a-z0-9-]{1,32})$")
_ROUTE_ACCOUNT = re.compile(r"^/v1/accounts/(\d{1,30})$")
MAX_HEADER = 16_384


class HttpFacilitator:  # pragma: no cover - network
    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 20):
        self.base, self.key, self.timeout = base_url.rstrip("/"), api_key, timeout

    def _post(self, path: str, body: dict) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["X-API-Key"] = self.key
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read())

    def verify(self, payload: dict, req: dict) -> dict:
        return self._post("/verify", {"x402Version": 2, "paymentPayload": payload, "paymentRequirements": req})

    def settle(self, payload: dict, req: dict) -> dict:
        return self._post("/settle", {"x402Version": 2, "paymentPayload": payload, "paymentRequirements": req})


def _resp(status: int, body: dict, headers: dict | None = None) -> dict:
    h = {"Content-Type": "application/json", "Cache-Control": "no-store"}
    h.update(headers or {})
    return {"statusCode": status, "headers": h, "body": json.dumps(body, sort_keys=True)}


class Paywall:
    def __init__(self, *, network, rpc, ledger_store, usage_store, facilitator, pay_to: str,
                 plan: billing.Plan = billing.Plan(), base_url: str = "https://validator.example", clock=None):
        self.net, self.rpc, self.ledger_store, self.usage_store = network, rpc, ledger_store, usage_store
        self.fac, self.pay_to, self.plan, self.base_url = facilitator, pay_to, plan, base_url.rstrip("/")
        self.clock = clock
        self.max_reconcile_attempts = 60

    # -- reads ---------------------------------------------------------------
    def pricing(self) -> dict:
        return {"network": f"eip155:{self.net.chain_id}", "asset": billing.USDC[self.net.name], "payTo": self.pay_to,
                "freePerMonth": self.plan.free_per_month,
                "packs": [{"id": p.id, "credits": p.credits, "priceUsd": p.usd, "amount": str(p.price),
                           "perValidationUsd": f"{p.price / p.credits / 10**billing.DECIMALS:.4f}"}
                          for p in self.plan.packs],
                "unpaid": "requests not covered are held (not answered) for up to 7 days, then expire unanswered"}

    def account(self, agent_id: int) -> dict:
        acct = billing.account(self.net.chain_id, agent_id)
        ledger = self.ledger_store.load()
        usage = self.usage_store.load().get("usage", {})
        month = billing.month_of(self.clock() if self.clock else None)
        return billing.balance(acct, month, int(ledger["purchased"].get(acct, 0)), usage, self.plan)

    # -- buying ----------------------------------------------------------------
    def _required(self, agent_id, pack, error=None):
        pr = billing.payment_required(self.net, pack, self.pay_to, self.plan,
                                      f"{self.base_url}/v1/credits/{agent_id}/{pack.id}", agent_id, error)
        return _resp(402, pr, {"PAYMENT-REQUIRED": billing.b64(pr)})

    def buy(self, agent_id: int, pack_id: str, payment_header: str | None) -> dict:
        try:
            pack = self.plan.pack(pack_id)
        except KeyError as e:
            return _resp(404, {"error": str(e)})
        if not payment_header:
            return self._required(agent_id, pack)
        if len(payment_header) > MAX_HEADER:
            return self._required(agent_id, pack, "PAYMENT-SIGNATURE too large")
        want = billing.requirements(self.net, pack, self.pay_to, self.plan)
        try:
            payload = billing.decode_payment(payment_header)
        except ValueError as e:
            return self._required(agent_id, pack, f"bad PAYMENT-SIGNATURE: {e}")
        bad = billing.mismatches(payload["accepted"], want)
        auth = payload["payload"].get("authorization") or {}
        if str(auth.get("to", "")).lower() != self.pay_to.lower():
            bad.append("authorization.to is not payTo")
        if str(auth.get("value")) != want["amount"]:
            bad.append("authorization.value is not the pack price")
        nonce = str(auth.get("nonce", "")).lower()
        if not re.fullmatch(r"0x[0-9a-f]{64}", nonce):
            bad.append("authorization.nonce must be 32 bytes hex")
        if bad:
            return self._required(agent_id, pack, "; ".join(bad))

        ledger = self.ledger_store.load()
        if f"nonce:{nonce}" in ledger["payments"]:
            return _resp(409, {"error": "this authorization was already used", **self.account(agent_id)})

        try:
            v = self.fac.verify(payload, want)
        except Exception as e:  # noqa: BLE001
            log.warning("facilitator verify failed: %s", e)
            return _resp(502, {"error": "facilitator unavailable; nothing was charged"})
        if not v.get("isValid"):
            return self._required(agent_id, pack, f"payment invalid: {v.get('invalidReason', 'unknown')}")
        try:
            st = self.fac.settle(payload, want)
        except Exception as e:  # noqa: BLE001 - may or may not have settled; the nonce check on retry decides
            log.error("facilitator settle failed: %s", e)
            return _resp(502, {"error": "settlement status unknown; retry with the same PAYMENT-SIGNATURE"})
        if not st.get("success"):
            return self._required(agent_id, pack, f"settlement failed: {st.get('errorReason', 'unknown')}")

        acct = billing.account(self.net.chain_id, agent_id)
        claim = {"requirements": want, "settlement": st, "authorizationNonce": nonce, "minConfirmations": 1,
                 "payer": auth.get("from")}
        rec = {"account": acct, "pack": pack.id, "credits": pack.credits, "amount": want["amount"],
               "tx": st.get("transaction"), "nonce": nonce, "payer": st.get("payer") or auth.get("from"),
               "claim": claim, "state": "pending"}
        verdict = self._check(claim)
        if verdict is not None and verdict.score < 100:
            rec.update(state="rejected", findings=verdict.findings)
        elif verdict is not None:
            rec["state"] = "credited"
        tx_key = f"tx:{str(st.get('transaction', '')).lower()}"
        if tx_key in ledger["payments"]:
            return _resp(409, {"error": "this settlement transaction was already credited"})
        billing.record_payment(ledger, tx_key, rec)
        ledger["payments"][f"nonce:{nonce}"] = {"ref": tx_key, "state": "ref"}
        self.ledger_store.save(ledger)

        headers = {"PAYMENT-RESPONSE": billing.b64(st)}
        if rec["state"] == "rejected":
            return _resp(402, {"error": "settlement did not check out on-chain", "findings": rec["findings"]}, headers)
        code = 200 if rec["state"] == "credited" else 202
        return _resp(code, {"state": rec["state"], "tx": rec["tx"], **self.account(agent_id)}, headers)

    def _check(self, claim) -> Verdict | None:
        """None = not decidable yet. A settlement tx our RPC hasn't seen yet is lag, not fraud."""
        try:
            tx = claim["settlement"].get("transaction", "")
            if re.fullmatch(r"0x[0-9a-fA-F]{64}", tx or "") and self.rpc.receipt(tx) is None:
                return None
            return check_x402_settlement(claim, self.rpc, Verdict)
        except Exception as e:  # noqa: BLE001 - RPC trouble: stay pending, reconcile later
            log.warning("on-chain check deferred: %s", e)
            return None

    def reconcile(self) -> int:
        """Credit pending payments whose settlement now checks out; reject those that never will."""
        ledger, n = self.ledger_store.load(), 0
        for key, rec in ledger["payments"].items():
            if rec.get("state") != "pending":
                continue
            v = self._check(rec["claim"])
            if v is None:
                rec["attempts"] = rec.get("attempts", 0) + 1
                if rec["attempts"] >= self.max_reconcile_attempts:  # the tx never showed up
                    rec.update(state="rejected", findings=["settlement transaction never appeared on chain"])
                continue
            if v.score == 100:
                n += billing.credit_pending(ledger, key)
            else:
                rec.update(state="rejected", findings=v.findings)
        self.ledger_store.save(ledger)
        return n

    # -- HTTP -------------------------------------------------------------------
    def handle(self, event: dict) -> dict:
        method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
        path = event.get("rawPath", "/")
        headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
        try:
            if method == "GET" and path == "/v1/pricing":
                return _resp(200, self.pricing())
            if method == "GET" and (m := _ROUTE_ACCOUNT.match(path)):
                self.reconcile()
                return _resp(200, self.account(int(m.group(1))))
            if method == "POST" and (m := _ROUTE_CREDITS.match(path)):
                return self.buy(int(m.group(1)), m.group(2), headers.get("payment-signature"))
        except Exception:  # noqa: BLE001
            log.exception("paywall error")
            return _resp(500, {"error": "internal error"})
        return _resp(404, {"error": "not found"})
