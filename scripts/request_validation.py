"""Agent-side helper: pay with an ERC-20 and ask replay8004 to validate that payment.

Dry run by default: prints what would be sent (decoded), the gas estimate and the cost, and sends nothing.
  pay      --to 0x.. --amount-wei N [--token 0x..]        ERC-20 transfer (CELO itself is an ERC-20 on Celo, so
                                                          this also funds a wallet)
  request  --agent-id N --validator 0x.. --tx 0x.. --to 0x.. --min-amount N [--token 0x..] [--payer 0x..]
           builds the job (inline data: URI), re-checks the claim locally, then sends validationRequest
Common: --network (celo-sepolia default; celo-mainnet needs REPLAY8004_ALLOW_MAINNET=1), --key-env VAR (the
signing key's environment variable; the key is never printed), --from 0x.. (dry run without a key), --send.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eth_abi import decode, encode  # noqa: E402

from replay8004 import job as jobmod, networks, registry  # noqa: E402
from replay8004.checkers import CHECKERS, Verdict  # noqa: E402
from replay8004.checkers.erc20 import TRANSFER_TOPIC  # noqa: E402
from replay8004.hashing import keccak  # noqa: E402
from replay8004.rpc import ReceiptUnavailable, Rpc  # noqa: E402

CELO_TOKEN = "0x471EcE3750Da237f93B8E339c536989b8978a438"  # same address on Celo mainnet and Celo Sepolia


def transfer_calldata(to: str, amount: int) -> str:
    if amount <= 0:
        raise ValueError("amount must be > 0")
    return "0x" + (keccak(b"transfer(address,uint256)")[:4] + encode(["address", "uint256"], [to, int(amount)])).hex()


def build_request(net, agent_id: int, validator: str, tx: str, token: str, to: str, min_amount: int,
                  payer: str | None = None, note: str = "") -> dict:
    claim = {"txHash": tx, "token": token, "to": to, "minAmount": str(int(min_amount)), "minConfirmations": 2}
    if payer:
        claim["from"] = payer
    raw = jobmod.make_job(agent_id, net.chain_id, "erc20_transfer", claim, note)
    h = jobmod.request_hash(raw)
    uri = jobmod.data_uri(raw)
    return {"job": raw, "requestHash": h, "requestURI": uri, "to": net.validation,
            "calldata": registry.encode_request(validator, agent_id, uri, h)}


def wait_receipt(rpc: Rpc, tx: str, timeout: int = 180) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        rec = rpc.receipt(tx)
        if rec:
            return rec
        time.sleep(3)
    raise TimeoutError(f"no receipt for {tx} after {timeout}s")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", default="celo-sepolia", choices=sorted(networks.NETWORKS))
    ap.add_argument("--rpc")
    ap.add_argument("--key-env", required=True, help="environment variable that holds the signing key")
    ap.add_argument("--from", dest="from_", help="dry run only: sender address, no key needed")
    ap.add_argument("--send", action="store_true", help="really send (default: dry run)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pay")
    p.add_argument("--to", required=True)
    p.add_argument("--amount-wei", type=int, required=True)
    p.add_argument("--token", default=CELO_TOKEN)
    q = sub.add_parser("request")
    q.add_argument("--agent-id", type=int, required=True)
    q.add_argument("--validator", required=True)
    q.add_argument("--tx", required=True, help="the payment tx being claimed")
    q.add_argument("--to", required=True, help="who was paid")
    q.add_argument("--min-amount", type=int, required=True)
    q.add_argument("--token", default=CELO_TOKEN)
    q.add_argument("--payer", help="optional: who paid")
    q.add_argument("--note", default="")
    q.add_argument("--out-dir", default="docs/mainnet", help="where the job file is saved before sending")
    a = ap.parse_args()

    net = networks.get(a.network, allow_mainnet=os.environ.get("REPLAY8004_ALLOW_MAINNET") == "1")
    rpc = Rpc(a.rpc or net.rpc)
    if a.from_:
        if a.send:
            sys.exit("--from is for dry runs only")
        sender, addr = None, a.from_
    else:
        key = os.environ.get(a.key_env)
        if not key:
            sys.exit(f"set {a.key_env} in the environment, or use --from for a dry run")
        sender = registry.Sender(rpc, net.chain_id, key)  # checks the RPC chain id; never echoes the key
        del key
        addr = sender.address

    if a.cmd == "pay":
        (sym,) = decode(["string"], bytes.fromhex(rpc.eth_call(a.token, "0x" + keccak(b"symbol()")[:4].hex())[2:]))
        (dec,) = decode(["uint8"], bytes.fromhex(rpc.eth_call(a.token, "0x" + keccak(b"decimals()")[:4].hex())[2:]))
        to_contract, data = a.token, transfer_calldata(a.to, a.amount_wei)
        what = {"action": f"transfer {a.amount_wei / 10**dec} {sym}", "token": a.token, "recipient": a.to}
    else:
        r = build_request(net, a.agent_id, a.validator, a.tx, a.token, a.to, a.min_amount, a.payer, a.note)
        try:
            v = CHECKERS["erc20_transfer"](json.loads(r["job"])["claim"], rpc, Verdict)
            local = "not decidable yet (too few confirmations)" if v is None else {"score": v.score, "findings": v.findings}
        except ReceiptUnavailable as e:
            local = f"not decidable: {e}"
        to_contract, data = r["to"], r["calldata"]
        what = {"action": "validationRequest", "agentId": a.agent_id, "validator": a.validator,
                "requestHash": r["requestHash"], "job": json.loads(r["job"]), "localCheck": local}

    gas = int(rpc.call("eth_estimateGas", [{"from": addr, "to": to_contract, "data": data}]), 16)
    price = int(rpc.call("eth_gasPrice", []), 16)
    bal = int(rpc.call("eth_getBalance", [addr, "latest"]), 16)
    print(json.dumps({"network": net.name, "chainId": net.chain_id, "from": addr, "to": to_contract, **what,
                      "calldataBytes": len(data) // 2 - 1, "gasEstimate": gas, "gasPriceGwei": round(price / 1e9, 3),
                      "estFeeCELO": round(gas * price / 1e18, 8), "maxFeeCELO": round(gas * 1.2 * price * 2 / 1e18, 8),
                      "balanceCELO": bal / 1e18, "send": a.send}, indent=2))
    if not a.send:
        print("dry run: nothing sent. Re-run with --send to send it.")
        return

    if a.cmd == "request":  # keep the exact job bytes the requestHash commits to
        out = Path(a.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / f"job-{r['requestHash'][2:10]}.json").write_bytes(r["job"])
    tx = sender.send(to_contract, data)
    print(json.dumps({"tx": tx, "explorer": f"{net.explorer}/tx/{tx}"}))
    rec = wait_receipt(rpc, tx)
    fee = int(rec["gasUsed"], 16) * int(rec.get("effectiveGasPrice", "0x0"), 16)
    res = {"status": int(rec["status"], 16), "block": int(rec["blockNumber"], 16), "gasUsed": int(rec["gasUsed"], 16),
           "feeCELO": fee / 1e18, "tx": tx, "explorer": f"{net.explorer}/tx/{tx}"}
    if a.cmd == "pay":
        res["transferLogs"] = sum(1 for lg in rec["logs"] if lg["topics"] and lg["topics"][0].lower() == TRANSFER_TOPIC)
    else:
        logs = [lg for lg in rec["logs"] if lg["address"].lower() == net.validation.lower()
                and lg["topics"][0].lower() == registry.TOPIC_REQUEST]
        res["validationRequestEvent"] = bool(logs) and registry.decode_request_log(logs[0])["requestHash"] == r["requestHash"]
        res["requestHash"] = r["requestHash"]
    print(json.dumps(res, indent=2))
    if res["status"] != 1:
        sys.exit("the transaction reverted")


if __name__ == "__main__":
    main()
