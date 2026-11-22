"""replay8004 CLI.

Agent side (build a job and the validationRequest calldata to send from the agent owner's wallet):
  replay8004 job erc20-transfer --agent-id 42 --tx 0x.. --token 0x.. --to 0x.. --min-amount 10000 --validator 0x..
  replay8004 job erc20-balance  --agent-id 42 --token 0x.. --holder 0x.. --block 123 --expected 5 --validator 0x..
  replay8004 job contract-read  --agent-id 42 --contract 0x.. --sig "totalSupply()(uint256)" --block 123 --expected 1000 --validator 0x..
Validator side:
  replay8004 run --validator 0x.. [--once] [--send]   (default: dry run, prints calldata instead of sending)
Anyone:
  replay8004 check job.json                          re-run a job locally, nothing written on-chain
  replay8004 summary --agent-id 42 --validator 0x.. [--tag replay:erc20_transfer]
  replay8004 status --request-hash 0x..             getValidationStatus: who answered, score, responseHash, tag
  replay8004 verify-evidence .replay8004/evidence    recompute hashes and the evidence chain
Network: --network celo-sepolia (default) | celo-mainnet (needs REPLAY8004_ALLOW_MAINNET=1).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from . import evidence, job as jobmod, networks, registry
from .checkers import CHECKERS, Verdict
from .rpc import ReceiptUnavailable, Rpc


def _net(a):
    return networks.get(a.network, allow_mainnet=os.environ.get("REPLAY8004_ALLOW_MAINNET") == "1")


def _claim(a) -> tuple[str, dict]:
    if a.kind == "erc20-transfer":
        c = {"txHash": a.tx, "token": a.token, "to": a.to, "minAmount": str(a.min_amount),
             "minConfirmations": a.confirmations}
        if a.from_:
            c["from"] = a.from_
        return "erc20_transfer", c
    if a.kind == "erc20-balance":
        return "erc20_balance", {"token": a.token, "holder": a.holder, "block": a.block,
                                 "expected": str(a.expected), "tolerance": str(a.tolerance)}
    return "contract_read", {"to": a.contract, "signature": a.sig, "args": a.arg or [], "block": a.block,
                             "expected": a.expected_list}


def cmd_job(a):
    net = _net(a)
    kind, claim = _claim(a)
    raw = jobmod.make_job(a.agent_id, net.chain_id, kind, claim, a.note)
    h = jobmod.request_hash(raw)
    out = Path(a.out or f"job-{h[2:10]}.json")
    out.write_bytes(raw)
    uri = a.uri or jobmod.data_uri(raw)
    print(json.dumps({"job_file": str(out), "requestHash": h, "requestURI": uri if len(uri) < 300 else uri[:300] + "...",
                      "to": net.validation,
                      "calldata": registry.encode_request(a.validator, a.agent_id, uri, h),
                      "send_from": "the agent owner's wallet (or an approved operator)",
                      "cast_example": f"cast send {net.validation} <calldata> --rpc-url {net.rpc} --account <owner>"},
                     indent=2))


def cmd_check(a):
    net = _net(a)
    raw = Path(a.job).read_bytes()
    job = jobmod.parse(raw, jobmod.request_hash(raw), int(json.loads(raw)["agentId"]), net.chain_id)
    try:
        v = CHECKERS[job["kind"]](job["claim"], Rpc(a.rpc or net.rpc), Verdict)
    except ReceiptUnavailable as e:
        print(json.dumps({"decidable": False, "reason": str(e)}, indent=2))
        return
    print(json.dumps({"decidable": v is not None, **({"score": v.score, "findings": v.findings,
                                                       "observed": v.observed} if v else {})}, indent=2))


def cmd_run(a):
    from .evidence import LocalSink
    from .store import FileStore
    from .worker import Worker
    net = _net(a)
    rpc = Rpc(a.rpc or net.rpc)
    sender = None
    if a.send:
        if "example.invalid" in a.evidence_base_url:
            sys.exit("--send needs --evidence-base-url: it is written on-chain for good and must be publicly readable")
        key = os.environ.get("REPLAY8004_VALIDATOR_KEY")
        if not key:
            sys.exit("set REPLAY8004_VALIDATOR_KEY (a key used only for this validator) to send transactions")
        sender = registry.Sender(rpc, net.chain_id, key)
        del key
        if sender.address.lower() != a.validator.lower():
            sys.exit("REPLAY8004_VALIDATOR_KEY does not match --validator")
    base = Path(a.state_dir)
    w = Worker(network=net, rpc=rpc, validator=a.validator, sender=sender,
               store=FileStore(base / f"state-{net.name}.json", start_block=a.start_block or net.validation_deploy_block),
               sink=LocalSink(base / "evidence", a.evidence_base_url))
    while True:
        print(json.dumps(w.poll_once(), indent=2, default=str))
        if a.once:
            return
        time.sleep(a.interval)


def cmd_summary(a):
    net = _net(a)
    raw = Rpc(a.rpc or net.rpc).eth_call(net.validation, registry.encode_summary(a.agent_id, a.validator or [], a.tag))
    count, avg = registry.decode_summary(raw)
    print(json.dumps({"agentId": a.agent_id, "count": count, "avgResponse": avg, "tag": a.tag}))


def cmd_status(a):
    net = _net(a)
    raw = Rpc(a.rpc or net.rpc).eth_call(net.validation, registry.encode_status(a.request_hash))
    print(json.dumps({"requestHash": a.request_hash.lower(), **registry.decode_status(raw)}))


def cmd_verify(a):
    bundles = evidence.LocalSink(a.folder, "file://").all()
    for b in bundles:
        expected_name = f"{b['requestHash']}.json"
        if not (Path(a.folder) / expected_name).exists():
            print(f"BROKEN: bundle for {b['requestHash']} stored under another name")
            sys.exit(1)
    ok, msg = evidence.verify_chain(bundles)
    print(("OK: " if ok else "BROKEN: ") + msg)
    sys.exit(0 if ok else 1)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="replay8004")
    ap.add_argument("--network", default="celo-sepolia", choices=sorted(networks.NETWORKS))
    ap.add_argument("--rpc", help="override the RPC URL")
    sub = ap.add_subparsers(dest="cmd", required=True)

    j = sub.add_parser("job")
    j.add_argument("kind", choices=["erc20-transfer", "erc20-balance", "contract-read"])
    j.add_argument("--agent-id", type=int, required=True)
    j.add_argument("--validator", required=True)
    j.add_argument("--uri", help="where you host the job file; default is an inline data: URI")
    j.add_argument("--out")
    j.add_argument("--note", default="")
    j.add_argument("--tx"); j.add_argument("--token"); j.add_argument("--to"); j.add_argument("--from", dest="from_")
    j.add_argument("--min-amount", type=int); j.add_argument("--confirmations", type=int, default=2)
    j.add_argument("--holder"); j.add_argument("--block", type=int); j.add_argument("--expected")
    j.add_argument("--tolerance", type=int, default=0)
    j.add_argument("--contract"); j.add_argument("--sig"); j.add_argument("--arg", action="append")
    j.set_defaults(fn=cmd_job)

    c = sub.add_parser("check"); c.add_argument("job"); c.set_defaults(fn=cmd_check)

    r = sub.add_parser("run")
    r.add_argument("--validator", required=True)
    r.add_argument("--send", action="store_true", help="really send validationResponse (default: dry run)")
    r.add_argument("--once", action="store_true")
    r.add_argument("--interval", type=int, default=30)
    r.add_argument("--start-block", type=int, default=0,
                   help="first block to scan on a fresh state file (default: the registry's deployment block)")
    r.add_argument("--state-dir", default=".replay8004")
    r.add_argument("--evidence-base-url", default="https://example.invalid/evidence")
    r.set_defaults(fn=cmd_run)

    s = sub.add_parser("summary")
    s.add_argument("--agent-id", type=int, required=True)
    s.add_argument("--validator", action="append")
    s.add_argument("--tag", default="")
    s.set_defaults(fn=cmd_summary)

    st = sub.add_parser("status")
    st.add_argument("--request-hash", required=True)
    st.set_defaults(fn=cmd_status)

    v = sub.add_parser("verify-evidence"); v.add_argument("folder"); v.set_defaults(fn=cmd_verify)

    a = ap.parse_args(argv)
    if a.cmd == "job":
        need = {"erc20-transfer": ["tx", "token", "to", "min_amount"], "erc20-balance": ["token", "holder", "block", "expected"],
                "contract-read": ["contract", "sig", "block", "expected"]}[a.kind]
        missing = [n for n in need if getattr(a, n) in (None, "")]
        if missing:
            ap.error(f"{a.kind} needs --{' --'.join(m.replace('_', '-') for m in missing)}")
        if a.kind == "contract-read":
            a.expected_list = json.loads(a.expected) if a.expected.startswith("[") else [a.expected]
    a.fn(a)


if __name__ == "__main__":
    main()
