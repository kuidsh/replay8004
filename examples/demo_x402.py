"""Offline demo of the x402_settlement checker: three x402 receipts re-checked against a fake Celo Sepolia.
Run from the repo root:  python -m examples.demo_x402
"""
import json
import tempfile
from pathlib import Path

from replay8004 import evidence, job as jobmod, networks
from replay8004.evidence import LocalSink
from replay8004.store import FileStore
from replay8004.worker import Worker
from tests.conftest import PAYEE, PAYER, USDC, VALIDATOR, FakeRpc, FakeSender

NET = networks.CELO_SEPOLIA
NONCE = "0x" + "77" * 32


def main():
    tmp = Path(tempfile.mkdtemp())
    rpc = FakeRpc(head=1_000)
    req = {"scheme": "exact", "network": "eip155:11142220", "amount": "10000", "asset": USDC, "payTo": PAYEE,
           "maxTimeoutSeconds": 60, "extra": {"name": "USDC", "version": "2"}}
    cases = [  # label, agent, tx, on-chain amount, reported amount, nonce in claim
        ("Agent #50: x402 receipt for a 0.01 USDC API call", 50, "0x" + "b1" * 32, 10_000, "10000", NONCE),
        ("Agent #51: receipt says 0.01 USDC, chain shows 0.004", 51, "0x" + "b2" * 32, 4_000, "10000", None),
        ("Agent #52: receipt cites a tx that used another authorization", 52, "0x" + "b3" * 32, 10_000, "10000",
         "0x" + "99" * 32),
    ]
    labels = {}
    for i, (label, agent, tx, moved, reported, nonce) in enumerate(cases):
        rpc.add_x402_settlement(tx, USDC, PAYER, PAYEE, moved, block=900 + i, nonce=NONCE)
        st = {"success": True, "transaction": tx, "network": "eip155:11142220", "payer": PAYER, "amount": reported}
        claim = {"requirements": req, "settlement": st, "minConfirmations": 2}
        if nonce:
            claim["authorizationNonce"] = nonce
        raw = jobmod.make_job(agent, NET.chain_id, "x402_settlement", claim)
        h = jobmod.request_hash(raw)
        rpc.add_request(NET.validation, VALIDATOR, agent, jobmod.data_uri(raw), h, 950 + i)
        labels[h] = label
    w = Worker(network=NET, rpc=rpc, validator=VALIDATOR, sender=FakeSender(rpc),  # fake chain, fake sender: no key
               store=FileStore(tmp / "s.json", start_block=900),
               sink=LocalSink(tmp / "ev", "https://evidence.example"), clock=lambda: "2026-11-21T12:00:00+00:00")
    rows = []
    for a in w.poll_once()["answered"]:
        b = json.loads((tmp / "ev" / f"{a['requestHash']}.json").read_bytes())
        rows.append({"request": labels[a["requestHash"]], "score": a["score"], "tag": a["tag"],
                     "finding": b["verdict"]["findings"][0], "seq": b["seq"], "responseHash": a["responseHash"]})
    print(json.dumps({"rows": rows, "chain": evidence.verify_chain(LocalSink(tmp / "ev", "x").all())}, indent=2))


if __name__ == "__main__":
    main()
