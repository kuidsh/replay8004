"""Register an agent in the canonical ERC-8004 IdentityRegistry (register(string agentURI)).

Dry run by default: prints from / to / calldata / gas estimate / cost and sends nothing.
  python scripts/register_agent.py --name "replay8004 test agent" --description "..."      # Celo Sepolia
  python scripts/register_agent.py --agent-uri https://.../registration.json --send
Mainnet needs --network celo-mainnet AND REPLAY8004_ALLOW_MAINNET=1 (operator decision).
The signing key is read from the OWNER_KEY environment variable only and is never printed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from replay8004 import identity, networks  # noqa: E402
from replay8004.registry import Sender  # noqa: E402
from replay8004.rpc import Rpc  # noqa: E402


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
    ap.add_argument("--agent-uri", help="https://, ipfs:// or data: URI of the registration JSON")
    ap.add_argument("--name", default="replay8004 test agent")
    ap.add_argument("--description", default="Test agent used to exercise the replay8004 validator on Celo Sepolia.")
    ap.add_argument("--send", action="store_true", help="really send (default: dry run)")
    a = ap.parse_args()

    net = networks.get(a.network, allow_mainnet=os.environ.get("REPLAY8004_ALLOW_MAINNET") == "1")
    rpc = Rpc(a.rpc or net.rpc)
    key = os.environ.get("OWNER_KEY")
    if not key:
        sys.exit("set OWNER_KEY (the agent owner's key) in the environment")
    sender = Sender(rpc, net.chain_id, key)  # also checks the RPC chain id
    del key

    uri = a.agent_uri or identity.data_uri(identity.registration_json(a.name, a.description))
    data = identity.encode_register(uri)
    gas = int(rpc.call("eth_estimateGas", [{"from": sender.address, "to": net.identity, "data": data}]), 16)
    price = int(rpc.call("eth_gasPrice", []), 16)
    bal = int(rpc.call("eth_getBalance", [sender.address, "latest"]), 16)
    plan = {"network": net.name, "chainId": net.chain_id, "from": sender.address, "to": net.identity,
            "function": "register(string agentURI)", "agentURI": uri if len(uri) <= 300 else uri[:300] + "...",
            "data": data, "gasEstimate": gas, "gasPriceGwei": round(price / 1e9, 3),
            "estCostCELO": round(gas * 1.2 * price / 1e18, 8), "maxCostCELO": round(gas * 1.2 * price * 2 / 1e18, 8),
            "balanceCELO": bal / 1e18, "send": a.send}
    print(json.dumps(plan, indent=2))
    if not a.send:
        print("dry run: nothing sent. Re-run with --send to register.")
        return

    tx = sender.send(net.identity, data)
    print(json.dumps({"tx": tx, "explorer": f"{net.explorer}/tx/{tx}"}))
    rec = wait_receipt(rpc, tx)
    if int(rec["status"], 16) != 1:
        sys.exit(f"register reverted: {tx}")
    regs = identity.registered_from_receipt(rec, net.identity, sender.address)
    if len(regs) != 1:
        sys.exit(f"expected one Registered event for {sender.address}, found {len(regs)}")
    used = int(rec["gasUsed"], 16) * int(rec.get("effectiveGasPrice", "0x0"), 16)
    print(json.dumps({"agentId": regs[0]["agentId"], "owner": regs[0]["owner"], "block": int(rec["blockNumber"], 16),
                      "gasUsed": int(rec["gasUsed"], 16), "feeCELO": used / 1e18, "tx": tx,
                      "explorer": f"{net.explorer}/tx/{tx}"}, indent=2))


if __name__ == "__main__":
    main()
