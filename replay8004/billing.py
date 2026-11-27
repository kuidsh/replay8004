"""Paid validations: credit packs bought with x402, a free monthly quota, and the worker's admit rule.

Why packs, not a payment per validation: Celo's x402 facilitator charges the resource server gas at
cost plus 0.3% of the payment for every settlement, with a 4,000-micro-USD (US$0.004) per-tx figure
in its config (GET https://api.x402.celo.org/api/config, read 2026-11-26). On a US$0.02 check that is
≈ 20% of revenue, before our own validationResponse gas. One US$5 pack settles once, so the fee is
≈ US$0.019 (0.4%) for 250 validations.

Who pays: anyone may buy credits for an ERC-8004 agent (account = "<chainId>:<agentId>"), usually its
owner. Credits are consumed when the validator *answers* a request for that agent, including an answer
of 0 for an invalid job (it still costs gas and evidence). Requests that are not covered are held,
never answered with a 0 for lack of payment, so an unpaid request cannot hurt an agent's record.

Split of state, so the paywall and the worker never write the same item:
  * the paywall appends purchases to the ledger (purchased totals only grow);
  * the worker counts usage in its own state, saved in the same write as the answer.
  available = purchased - used_paid.
"""
from __future__ import annotations

import base64
import datetime as dt
import json
from dataclasses import dataclass, field

from .checkers.x402 import decode_header

X402_VERSION = 2
DECIMALS = 6  # USDC on Celo

# USDC per Celo docs (build-on-celo/build-with-ai/x402, read 2026-11-26): EIP-3009, EIP-712 name "USDC", version "2"
USDC = {
    "celo-mainnet": "0xcebA9300f2b948710d2653dD7B07f33A8B32118C",
    "celo-sepolia": "0x01C5C0122039549AD1493B8220cABEdD739BC44E",
}
FACILITATOR = {
    "celo-mainnet": "https://api.x402.celo.org",
    "celo-sepolia": "https://api.x402.sepolia.celo.org",
}


@dataclass(frozen=True)
class Pack:
    id: str
    credits: int
    price: int  # USDC atomic units (6 decimals)

    @property
    def usd(self) -> str:
        return f"{self.price / 10**DECIMALS:.2f}"


@dataclass(frozen=True)
class Plan:
    packs: tuple = (Pack("starter", 250, 5_000_000), Pack("scale", 2_500, 40_000_000))
    free_per_month: int = 25
    allowlist: frozenset = field(default_factory=frozenset)  # accounts that never pay (open-source agents)
    max_hold_polls: int = 7 * 24 * 60  # one week at one poll a minute, then the request expires unanswered
    max_timeout_seconds: int = 300

    def pack(self, pack_id: str) -> Pack:
        for p in self.packs:
            if p.id == pack_id:
                return p
        raise KeyError(f"unknown pack {pack_id!r}")


def account(chain_id: int, agent_id) -> str:
    return f"{int(chain_id)}:{int(agent_id)}"


def month_of(ts: str | None = None) -> str:
    d = dt.datetime.fromisoformat(ts) if ts else dt.datetime.now(dt.timezone.utc)
    return d.strftime("%Y-%m")


# -- x402 messages -------------------------------------------------------------
def b64(obj) -> str:
    return base64.b64encode(json.dumps(obj, separators=(",", ":"), sort_keys=True).encode()).decode()


def requirements(net, pack: Pack, pay_to: str, plan: Plan) -> dict:
    """One x402 v2 PaymentRequirements entry (scheme exact, USDC via EIP-3009)."""
    return {"scheme": "exact", "network": f"eip155:{net.chain_id}", "amount": str(pack.price),
            "asset": USDC[net.name], "payTo": pay_to, "maxTimeoutSeconds": plan.max_timeout_seconds,
            "extra": {"name": "USDC", "version": "2"}}


def payment_required(net, pack: Pack, pay_to: str, plan: Plan, resource_url: str, agent_id, error=None) -> dict:
    out = {"x402Version": X402_VERSION,
           "resource": {"url": resource_url, "mimeType": "application/json", "serviceName": "replay8004",
                        "description": f"{pack.credits} replay8004 validations for ERC-8004 agent {agent_id} "
                                       f"on chain {net.chain_id}"},
           "accepts": [requirements(net, pack, pay_to, plan)]}
    if error:
        out["error"] = error
    return out


def mismatches(accepted: dict, expected: dict) -> list[str]:
    """What a client's `accepted` gets wrong against the requirements we issue. Empty list = match."""
    bad = []
    for k in ("scheme", "network", "amount"):
        if str(accepted.get(k)) != str(expected[k]):
            bad.append(f"{k}: got {accepted.get(k)!r}, want {expected[k]!r}")
    for k in ("asset", "payTo"):
        if str(accepted.get(k, "")).lower() != expected[k].lower():
            bad.append(f"{k}: got {accepted.get(k)!r}, want {expected[k]!r}")
    return bad


def decode_payment(header_value) -> dict:
    p = decode_header(header_value)
    if p.get("x402Version") != X402_VERSION:
        raise ValueError(f"x402Version must be {X402_VERSION}")
    if not isinstance(p.get("accepted"), dict) or not isinstance(p.get("payload"), dict):
        raise ValueError("PaymentPayload needs 'accepted' and 'payload'")
    return p


# -- ledger (paywall side) -------------------------------------------------------
def empty_ledger() -> dict:
    return {"purchased": {}, "payments": {}}


def record_payment(ledger: dict, key: str, rec: dict) -> bool:
    """Store a payment once. Returns False if this key (tx hash or authorization nonce) was seen."""
    if key in ledger["payments"]:
        return False
    ledger["payments"][key] = rec
    if rec["state"] == "credited":
        ledger["purchased"][rec["account"]] = ledger["purchased"].get(rec["account"], 0) + rec["credits"]
    return True


def credit_pending(ledger: dict, key: str) -> bool:
    rec = ledger["payments"][key]
    if rec["state"] != "pending":
        return False
    rec["state"] = "credited"
    ledger["purchased"][rec["account"]] = ledger["purchased"].get(rec["account"], 0) + rec["credits"]
    return True


# -- usage (worker side) ---------------------------------------------------------
def admit(acct: str, month: str, purchased: int, usage: dict, plan: Plan) -> str | None:
    """How the next answer for `acct` is covered: 'allowlist', 'free', 'credit', or None (hold)."""
    if acct in plan.allowlist:
        return "allowlist"
    u = usage.get(acct, {})
    if u.get("free", {}).get(month, 0) < plan.free_per_month:
        return "free"
    if u.get("paid", 0) < purchased:
        return "credit"
    return None


def consume(acct: str, month: str, how: str, usage: dict) -> None:
    u = usage.setdefault(acct, {"paid": 0, "free": {}})
    if how == "free":
        u["free"][month] = u["free"].get(month, 0) + 1
    elif how == "credit":
        u["paid"] = u.get("paid", 0) + 1


def balance(acct: str, month: str, purchased: int, usage: dict, plan: Plan) -> dict:
    u = usage.get(acct, {})
    used_free = u.get("free", {}).get(month, 0)
    return {"account": acct, "month": month, "allowlisted": acct in plan.allowlist,
            "freeRemaining": max(0, plan.free_per_month - used_free), "purchased": purchased,
            "usedPaid": u.get("paid", 0), "creditsRemaining": max(0, purchased - u.get("paid", 0))}


class Billing:
    """What the worker needs: the plan and the purchased totals (read once per poll from the ledger store)."""

    def __init__(self, plan: Plan, ledger_store=None):
        self.plan, self.ledger_store = plan, ledger_store
        self._ledger = None

    def refresh(self) -> None:
        self._ledger = self.ledger_store.load() if self.ledger_store else empty_ledger()

    def purchased(self, acct: str) -> int:
        if self._ledger is None:
            self.refresh()
        return int(self._ledger["purchased"].get(acct, 0))
