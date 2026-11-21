"""Offline demo: four validation requests against a fake Celo Sepolia chain.
Run from the repo root:  python -m examples.demo
"""
import json
import tempfile
from pathlib import Path

from replay8004 import evidence, job as jobmod, networks
from replay8004.evidence import LocalSink
from replay8004.store import FileStore
from replay8004.worker import Worker
from tests.conftest import PAYEE, PAYER, USDC, VALIDATOR, FakeRpc

NET = networks.CELO_SEPOLIA


def main():
    tmp = Path(tempfile.mkdtemp())
    rpc = FakeRpc(head=1_000)
    cases = [
        ("Agent #42: 'I paid 0.01 USDC for the API call'", 42, "0x" + "a1" * 32, 10_000, PAYEE, NET.chain_id),
        ("Agent #43: 'I paid 0.01 USDC' (only 0.0025 was paid)", 43, "0x" + "a2" * 32, 2_500, PAYEE, NET.chain_id),
        ("Agent #44: 'I paid the seller' (paid someone else)", 44, "0x" + "a3" * 32, 10_000, PAYER, NET.chain_id),
        ("Agent #45: job says mainnet, request is on Sepolia", 45, "0x" + "a4" * 32, 10_000, PAYEE, 42220),
    ]
    labels = {}
    for i, (label, agent, tx, paid, to, chain) in enumerate(cases):
        rpc.add_transfer(tx, USDC, PAYER, to, paid, block=900 + i)
        claim = {"txHash": tx, "token": USDC, "from": PAYER, "to": PAYEE, "minAmount": "10000", "minConfirmations": 2}
        raw = jobmod.make_job(agent, chain, "erc20_transfer", claim)
        h = jobmod.request_hash(raw)
        rpc.add_request(NET.validation, VALIDATOR, agent, jobmod.data_uri(raw), h, 950 + i)
        labels[h] = label
    w = Worker(network=NET, rpc=rpc, validator=VALIDATOR, store=FileStore(tmp / "s.json", start_block=900),
               sink=LocalSink(tmp / "ev", "https://evidence.example"), clock=lambda: "2026-11-20T12:00:00+00:00")
    out = w.poll_once()
    rows = []
    for a in out["answered"]:
        b = json.loads((tmp / "ev" / f"{a['requestHash']}.json").read_bytes())
        rows.append({"request": labels[a["requestHash"]], "score": a["score"], "tag": a["tag"],
                     "finding": b["verdict"]["findings"][0], "seq": b["seq"], "responseHash": a["responseHash"]})
    print(json.dumps({"rows": rows, "chain": evidence.verify_chain(LocalSink(tmp / "ev", "x").all())}, indent=2))


if __name__ == "__main__":
    main()
