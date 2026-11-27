"""replay8004 CLI.

Agent side (build a job and the validationRequest calldata to send from the agent owner's wallet):
  replay8004 job erc20-transfer --agent-id 42 --tx 0x.. --token 0x.. --to 0x.. --min-amount 10000 --validator 0x..
  replay8004 job erc20-balance  --agent-id 42 --token 0x.. --holder 0x.. --block 123 --expected 5 --validator 0x..
  replay8004 job contract-read  --agent-id 42 --contract 0x.. --sig "totalSupply()(uint256)" --block 123 --expected 1000 --validator 0x..
  replay8004 job x402-settlement --agent-id 42 --requirements accepted.json --settlement <PAYMENT-RESPONSE value or file> --validator 0x..
Validator identity (ERC-8004 registration of the validator itself; prints files/calldata, sends nothing):
  replay8004 identity --validator 0x.. --repo https://github.com/<you>/replay8004 [--agent-id N] [--uri ipfs://..]
Validator side:
  replay8004 run --validator 0x.. [--once] [--send]   (default: dry run, prints calldata instead of sending)
Anyone:
  replay8004 check job.json                          re-run a job locally, nothing written on-chain
  replay8004 summary --agent-id 42 --validator 0x.. [--tag replay:erc20_transfer]
  replay8004 status --request-hash 0x..             getValidationStatus: who answered, score, responseHash, tag
  replay8004 status --evidence <folder> --out site  public status page (status.json + index.html), no RPC, no key
  replay8004 verify-evidence .replay8004/evidence    recompute hashes and the evidence chain
  replay8004 doctor                                  check the ValidationRegistry on-chain (getIdentityRegistry == Identity Registry)
  replay8004 gate --agent-id 42 --validator 0x.. [--tag ..] [--request-hash 0x..]   ReplayGate rules off-chain
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
from .checkers.x402 import decode_header
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
    if a.kind == "x402-settlement":
        req = json.loads(Path(a.requirements).read_text(encoding="utf-8"))
        try:
            st = Path(a.settlement).read_text(encoding="utf-8").strip() if Path(a.settlement).is_file() else a.settlement
        except OSError:  # a long header value is not a path
            st = a.settlement
        c = {"requirements": req, "settlement": decode_header(st), "minConfirmations": a.confirmations}
        if a.nonce:
            c["authorizationNonce"] = a.nonce
        if a.facilitator:
            c["facilitator"] = a.facilitator
        return "x402_settlement", c
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
    try:  # before any key is read: never answer on a registry that isn't wired to this network's identity registry
        dep = registry.verify_deployment(rpc, net)
        print(json.dumps({"validationRegistry": net.validation, **dep}), file=sys.stderr)
    except registry.DeploymentError as e:
        if a.send:
            sys.exit(f"refusing to send: {e}")
        print(f"warning (dry run continues): {e}", file=sys.stderr)
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
               sink=LocalSink(base / "evidence", a.evidence_base_url),
               max_answers_per_day=a.max_answers_per_day, max_answers_per_agent_per_day=a.max_answers_per_agent_per_day)
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
    """One command, two uses: --request-hash reads getValidationStatus; otherwise build the public status page."""
    if a.request_hash:
        net = _net(a)
        raw = Rpc(a.rpc or net.rpc).eth_call(net.validation, registry.encode_status(a.request_hash))
        print(json.dumps({"requestHash": a.request_hash.lower(), **registry.decode_status(raw)}))
        return
    import datetime as dt
    from . import status
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    st = status.build_site(a.evidence, a.out, validator=a.validator, now=now, evidence_base_url=a.evidence_base_url,
                           note=a.note)
    print(json.dumps({k: st[k] for k in ("answered", "agents", "claims", "medianSecondsToDecide", "chain")}, indent=2))
    sys.exit(0 if st["chain"]["intact"] else 1)


def cmd_identity(a):
    from . import identity
    net = _net(a)
    doc = identity.registration(network=net, validator=a.validator, repo=a.repo, image=a.image,
                                agent_id=a.agent_id, evidence_base_url=a.evidence_base_url or "")
    out = Path(a.out)
    out.write_bytes(identity.registration_bytes(doc))
    res = {"registration_file": str(out), "host_it_at": "ipfs:// or https:// (then pass --uri)",
           "identityRegistry": net.identity}
    if a.uri:
        res["calldata"] = (identity.encode_set_uri(a.agent_id, a.uri) if a.agent_id is not None
                           else identity.encode_register(a.uri))
        res["function"] = "setAgentURI(uint256,string)" if a.agent_id is not None else "register(string)"
        res["send_from"] = "the agent owner's wallet, after review (nothing is sent here)"
    print(json.dumps(res, indent=2))


def cmd_gate(a):
    from . import gate
    net = _net(a)
    rpc = Rpc(a.rpc or net.rpc)
    if a.request_hash:
        ok, reason, s = gate.claim_status(rpc, net, a.request_hash, a.agent_id, a.validator, a.tag, a.min_score, a.max_age)
        print(json.dumps({"ok": ok, "reason": reason, "status": s}, indent=2))
    else:
        count, avg = gate.record(rpc, net, a.agent_id, a.validator, a.tag)
        ok = count >= max(1, a.min_count) and avg >= a.min_avg
        print(json.dumps({"ok": ok, "count": count, "avg": avg, "tag": a.tag}, indent=2))
    sys.exit(0 if ok else 2)


def cmd_doctor(a):
    """Check the configured ValidationRegistry on-chain before anyone builds on it. Read-only."""
    net = _net(a)
    rpc = Rpc(a.rpc or net.rpc)
    out = {"network": net.name, "rpc": a.rpc or net.rpc, "validationRegistry": net.validation,
           "expectedIdentityRegistry": net.identity}
    try:
        out["rpcChainId"] = rpc.chain_id()
        out["head"] = rpc.block_number()
        dep = registry.verify_deployment(rpc, net)
    except Exception as e:  # noqa: BLE001 - DeploymentError or RPC trouble: report, don't crash
        print(json.dumps({"ok": False, **out, "error": str(e)}, indent=2))
        sys.exit(2)
    ok = out["rpcChainId"] == net.chain_id
    print(json.dumps({"ok": ok, **out, **dep, **({} if ok else {"error": "RPC is on another chain"})}, indent=2))
    sys.exit(0 if ok else 2)


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
    j.add_argument("kind", choices=["erc20-transfer", "erc20-balance", "contract-read", "x402-settlement"])
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
    j.add_argument("--requirements", help="JSON file: the PaymentRequirements entry you accepted")
    j.add_argument("--settlement", help="PAYMENT-RESPONSE value (base64 or JSON) or a file holding it")
    j.add_argument("--nonce", help="EIP-3009 authorization nonce you signed (optional, stronger check)")
    j.add_argument("--facilitator", help="address that must have sent the settlement tx (optional)")
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
    r.add_argument("--max-answers-per-day", type=int, default=20, help="gas guard: answers per UTC day (0 pauses)")
    r.add_argument("--max-answers-per-agent-per-day", type=int, default=5, help="gas guard: answers per agent per UTC day")
    r.set_defaults(fn=cmd_run)

    s = sub.add_parser("summary")
    s.add_argument("--agent-id", type=int, required=True)
    s.add_argument("--validator", action="append")
    s.add_argument("--tag", default="")
    s.set_defaults(fn=cmd_summary)

    st = sub.add_parser("status", help="--request-hash: on-chain status; otherwise build the public status page")
    st.add_argument("--request-hash", help="read getValidationStatus for one request")
    st.add_argument("--evidence", default=".replay8004/evidence", help="folder of evidence bundles (page mode)")
    st.add_argument("--out", default="site")
    st.add_argument("--validator")
    st.add_argument("--evidence-base-url", default="../evidence")
    st.add_argument("--note", default="", help="one line of context shown on the page (plain text)")
    st.set_defaults(fn=cmd_status)

    i = sub.add_parser("identity")
    i.add_argument("--validator", required=True)
    i.add_argument("--repo", required=True)
    i.add_argument("--image", default="")
    i.add_argument("--agent-id", type=int)
    i.add_argument("--uri", help="where the registration file is hosted; adds register/setAgentURI calldata")
    i.add_argument("--evidence-base-url")
    i.add_argument("--out", default="registration.json")
    i.set_defaults(fn=cmd_identity)

    d = sub.add_parser("doctor", help="verify the ValidationRegistry is wired to this network's Identity Registry")
    d.set_defaults(fn=cmd_doctor)

    v = sub.add_parser("verify-evidence"); v.add_argument("folder"); v.set_defaults(fn=cmd_verify)

    g = sub.add_parser("gate", help="same rules as ReplayGate.sol; exit 0 = pass, 2 = fail")
    g.add_argument("--agent-id", type=int, required=True)
    g.add_argument("--validator", required=True)
    g.add_argument("--tag", default="")
    g.add_argument("--min-count", type=int, default=3)
    g.add_argument("--min-avg", type=int, default=90)
    g.add_argument("--request-hash", help="check one request instead of the track record")
    g.add_argument("--min-score", type=int, default=100)
    g.add_argument("--max-age", type=int, default=0, help="seconds; 0 = no limit")
    g.set_defaults(fn=cmd_gate)

    a = ap.parse_args(argv)
    if a.cmd == "job":
        need = {"erc20-transfer": ["tx", "token", "to", "min_amount"], "erc20-balance": ["token", "holder", "block", "expected"],
                "contract-read": ["contract", "sig", "block", "expected"],
                "x402-settlement": ["requirements", "settlement"]}[a.kind]
        missing = [n for n in need if getattr(a, n) in (None, "")]
        if missing:
            ap.error(f"{a.kind} needs --{' --'.join(m.replace('_', '-') for m in missing)}")
        if a.kind == "contract-read":
            a.expected_list = json.loads(a.expected) if a.expected.startswith("[") else [a.expected]
    a.fn(a)


if __name__ == "__main__":
    main()
