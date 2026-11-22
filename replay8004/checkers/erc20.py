"""ERC-20 claims: "this transfer settled" (e.g. an x402 payment) and "this balance held at block N"."""
from __future__ import annotations

from eth_abi import decode, encode

from ..hashing import keccak
from ..rpc import ReceiptUnavailable

TRANSFER_TOPIC = "0x" + keccak(b"Transfer(address,address,uint256)").hex()
BALANCE_OF = "0x" + keccak(b"balanceOf(address)")[:4].hex()


def _addr(a: str) -> str:
    a = a.lower()
    if not (a.startswith("0x") and len(a) == 42):
        raise ValueError(f"bad address {a}")
    int(a, 16)
    return a


def _topic_addr(t: str) -> str:
    return "0x" + t[-40:].lower()


def check_erc20_transfer(claim: dict, rpc, verdict_cls):
    token, to = _addr(claim["token"]), _addr(claim["to"])
    frm = _addr(claim["from"]) if claim.get("from") else None
    min_amount = int(claim["minAmount"])
    min_conf = int(claim.get("minConfirmations", 2))
    if min_amount <= 0:
        raise ValueError("minAmount must be > 0")

    rec = rpc.receipt(claim["txHash"])
    if rec is None:
        # unknown, not false: pending until an RPC that keeps the receipt can decide
        raise ReceiptUnavailable(f"no receipt for {claim['txHash']} (unknown tx, or pruned by this RPC)")
    head = rpc.block_number()
    tx_block = int(rec["blockNumber"], 16)
    conf = head - tx_block + 1
    obs = {"txHash": claim["txHash"], "blockNumber": tx_block, "blockHash": rec.get("blockHash"),
           "confirmations": conf, "status": rec.get("status")}
    if int(rec.get("status", "0x0"), 16) != 1:
        return verdict_cls(0, ["transaction reverted"], obs)
    if conf < min_conf:
        return None  # decide later

    best = 0
    for log in rec.get("logs", []):
        t = log.get("topics", [])
        if log.get("address", "").lower() != token or len(t) != 3 or t[0].lower() != TRANSFER_TOPIC:
            continue
        if _topic_addr(t[2]) != to or (frm and _topic_addr(t[1]) != frm):
            continue
        best = max(best, int(log["data"], 16))
    obs["amount"] = str(best)
    if best == 0:
        return verdict_cls(0, ["no matching Transfer log (token / from / to)"], obs)
    if best < min_amount:
        return verdict_cls(min(99, best * 100 // min_amount),
                           [f"transferred {best} < claimed minimum {min_amount}"], obs)
    return verdict_cls(100, [f"transfer of {best} confirmed with {conf} confirmations"], obs)


def check_erc20_balance(claim: dict, rpc, verdict_cls):
    token, holder = _addr(claim["token"]), _addr(claim["holder"])
    block, expected = int(claim["block"]), int(claim["expected"])
    tol = int(claim.get("tolerance", 0))
    data = BALANCE_OF + encode(["address"], [holder]).hex()
    raw = rpc.eth_call(token, data, block)
    (bal,) = decode(["uint256"], bytes.fromhex(raw[2:]))
    obs = {"block": block, "balance": str(bal), "blockHash": rpc.block(block).get("hash")}
    if abs(bal - expected) <= tol:
        return verdict_cls(100, [f"balance {bal} matches claim within {tol}"], obs)
    return verdict_cls(0, [f"balance {bal} != claimed {expected} (tolerance {tol})"], obs)
