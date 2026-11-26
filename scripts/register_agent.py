"""Register an agent in the canonical ERC-8004 IdentityRegistry (register(string agentURI)).

Dry run by default: prints from / to / calldata / gas estimate / cost and sends nothing.
  python scripts/register_agent.py --name "replay8004 test agent" --description "..."      # Celo Sepolia
  python scripts/register_agent.py --agent-uri https://.../registration.json --send
Mainnet needs --network celo-mainnet AND REPLAY8004_ALLOW_MAINNET=1 (operator decision).
--registration FILE --validator-address 0x.. embeds a JSON template as a data: URI and shows the decoded JSON
and its size. --from 0x.. does a dry run without any key.
The signing key is read from an environment variable only (OWNER_KEY, or the one named by --key-env) and is
never printed.
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
    ap.add_argument("--registration", help="registration JSON template to embed as a data: URI")
    ap.add_argument("--validator-address", help="fills <validator address> in the template")
    ap.add_argument("--from", dest="from_", help="dry run only: sender address, no key needed")
    ap.add_argument("--name", default="replay8004 test agent")
    ap.add_argument("--description", default="Test agent used to exercise the replay8004 validator on Celo Sepolia.")
    ap.add_argument("--send", action="store_true", help="really send (default: dry run)")
    ap.add_argument("--key-env", default="OWNER_KEY", help="environment variable that holds the signing key")
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
            sys.exit(f"set {a.key_env} (the signing key) in the environment, or use --from for a dry run")
        sender = Sender(rpc, net.chain_id, key)  # also checks the RPC chain id
        del key
        addr = sender.address

    if a.registration:
        text = Path(a.registration).read_text(encoding="utf-8")
        if a.validator_address:
            text = text.replace("<validator address>", a.validator_address)
        if "<" in text:
            sys.exit("the registration file still has a <placeholder>")
        doc = json.loads(text)
        uri = identity.data_uri(doc)
        print(json.dumps({"decodedRegistration": json.loads(identity.decode_data_uri(uri)),
                          "jsonBytes": len(identity.decode_data_uri(uri)), "dataUriBytes": len(uri)}, indent=2))
    else:
        uri = a.agent_uri or identity.data_uri(identity.registration_json(a.name, a.description))
    data = identity.encode_register(uri)
    gas = int(rpc.call("eth_estimateGas", [{"from": addr, "to": net.identity, "data": data}]), 16)
    price = int(rpc.call("eth_gasPrice", []), 16)
    bal = int(rpc.call("eth_getBalance", [addr, "latest"]), 16)
    plan = {"network": net.name, "chainId": net.chain_id, "from": addr, "to": net.identity,
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
