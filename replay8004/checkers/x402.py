"""x402 claims: "this x402 payment really settled on Celo, for what the resource server asked".

An agent that paid for an API with x402 holds two things: the PaymentRequirements it accepted
(from the server's base64 PAYMENT-REQUIRED header, `accepts[i]`) and the SettlementResponse the
server returned after the facilitator settled it (x402 spec v2: success, transaction, network,
payer, amount). Either side of the trade can ask replay8004 to re-check that pair against Celo.

Checks, in order:
  1. scheme is "exact" (the only scheme Celo's facilitator settles today)
  2. requirements.network == settlement.network == eip155:<chain id of this RPC>
  3. settlement.success is true and settlement.transaction is a tx hash
  4. the tx exists, did not revert, and has enough confirmations (else: decide later)
  5. a Transfer log from `asset` moves value from `payer` to `payTo`
     (EIP-3009 transferWithAuthorization and Permit2 both end in the token's Transfer event)
  6. the amount moved covers requirements.amount; a SettlementResponse that reports more than
     moved on-chain is a misreported receipt and scores 0
  7. optional: `authorizationNonce` was consumed in this tx (EIP-3009 AuthorizationUsed event),
     which ties the on-chain transfer to the exact signed authorization
  8. optional: `facilitator` sent the tx (receipt.from)
Sources: x402 spec v2 (x402-foundation/x402, specs/x402-specification-v2.md); Celo x402 docs
(docs.celo.org/build-on-celo/build-with-ai/x402), both read 2026-11-21.
"""
from __future__ import annotations

import base64
import json
import re

from ..hashing import keccak
from ..rpc import ReceiptUnavailable
from .erc20 import TRANSFER_TOPIC, _addr, _topic_addr

AUTHORIZATION_USED_TOPIC = "0x" + keccak(b"AuthorizationUsed(address,bytes32)").hex()
_TX = re.compile(r"^0x[0-9a-fA-F]{64}$")


def decode_header(value) -> dict:
    """Accept a SettlementResponse as a dict, a JSON string, or base64(JSON) as sent in headers."""
    if isinstance(value, dict):
        return value
    s = str(value).strip()
    if s.startswith("{"):
        return json.loads(s)
    try:
        return json.loads(base64.b64decode(s + "=" * (-len(s) % 4)))
    except Exception as e:  # noqa: BLE001 - any decode failure is a malformed claim
        raise ValueError(f"settlement is neither JSON nor base64 JSON: {e}") from e


def check_x402_settlement(claim: dict, rpc, verdict_cls):
    req = claim["requirements"]
    st = decode_header(claim["settlement"])
    if req.get("scheme") != "exact":
        raise ValueError(f"unsupported x402 scheme {req.get('scheme')!r}; only 'exact' is checked")
    asset, pay_to = _addr(req["asset"]), _addr(req["payTo"])
    want = int(req["amount"])
    if want <= 0:
        raise ValueError("requirements.amount must be > 0")
    min_conf = int(claim.get("minConfirmations", 2))
    tx = st.get("transaction", "")
    obs = {"transaction": tx, "network": st.get("network"), "asset": asset, "payTo": pay_to,
           "required": str(want)}

    chain = f"eip155:{rpc.chain_id()}"
    if req.get("network") != chain or st.get("network") != chain:
        return verdict_cls(0, [f"network mismatch: requirements {req.get('network')}, settlement "
                               f"{st.get('network')}, validator chain {chain}"], obs)
    if st.get("success") is not True:
        return verdict_cls(0, [f"settlement reports failure: {st.get('errorReason', 'success != true')}"], obs)
    if not _TX.match(tx or ""):
        return verdict_cls(0, ["settlement has no transaction hash"], obs)
    payer = _addr(st["payer"]) if st.get("payer") else (_addr(claim["payer"]) if claim.get("payer") else None)
    if payer is None:
        raise ValueError("payer missing from both the settlement and the claim")
    obs["payer"] = payer

    rec = rpc.receipt(tx)
    if rec is None:
        # unknown, not false (same rule as erc20): forno prunes old receipts, so a real payment can look missing
        raise ReceiptUnavailable(f"no receipt for settlement {tx} (unknown tx, or pruned by this RPC)")
    tx_block = int(rec["blockNumber"], 16)
    conf = rpc.block_number() - tx_block + 1
    obs.update(blockNumber=tx_block, blockHash=rec.get("blockHash"), confirmations=conf,
               sentBy=(rec.get("from") or "").lower() or None)
    if int(rec.get("status", "0x0"), 16) != 1:
        return verdict_cls(0, ["settlement transaction reverted"], obs)
    if conf < min_conf:
        return None  # decide later

    moved, nonce_used = 0, False
    nonce = claim.get("authorizationNonce")
    for lg in rec.get("logs", []):
        t = [x.lower() for x in lg.get("topics", [])]
        if lg.get("address", "").lower() != asset or not t:
            continue
        if t[0] == TRANSFER_TOPIC and len(t) == 3 and _topic_addr(t[1]) == payer and _topic_addr(t[2]) == pay_to:
            moved += int(lg["data"], 16)
        if nonce and t[0] == AUTHORIZATION_USED_TOPIC and len(t) == 3 and _topic_addr(t[1]) == payer \
                and t[2] == nonce.lower():
            nonce_used = True
    obs["moved"] = str(moved)

    findings = []
    if moved == 0:
        return verdict_cls(0, ["no Transfer of the asset from payer to payTo in the settlement tx"], obs)
    if st.get("amount") is not None and int(st["amount"]) > moved:
        return verdict_cls(0, [f"settlement reports {st['amount']} but only {moved} moved on chain"], obs)
    if nonce:
        obs["authorizationNonce"] = nonce.lower()
        if not nonce_used:
            return verdict_cls(0, ["authorization nonce was not consumed in the settlement tx"], obs)
        findings.append("EIP-3009 authorization nonce consumed in this tx")
    if claim.get("facilitator") and obs["sentBy"] != _addr(claim["facilitator"]):
        return verdict_cls(0, [f"tx sent by {obs['sentBy']}, not the claimed facilitator"], obs)
    if moved < want:
        return verdict_cls(min(99, moved * 100 // want),
                           [f"moved {moved} < required {want}"] + findings, obs)
    return verdict_cls(100, [f"x402 payment of {moved} to payTo settled with {conf} confirmations"] + findings, obs)
