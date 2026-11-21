"""Generic deterministic read: "calling f(args) on contract C at block N returned X"."""
from __future__ import annotations

import re

from eth_abi import decode, encode

from ..hashing import keccak

_SIG = re.compile(r"^(\w+)\(([^()]*)\)\(([^()]*)\)$")


def _types(s: str) -> list[str]:
    return [t.strip() for t in s.split(",") if t.strip()]


def _norm(v):
    if isinstance(v, bytes):
        return "0x" + v.hex()
    if isinstance(v, (list, tuple)):
        return [_norm(x) for x in v]
    if isinstance(v, str) and v.startswith("0x"):
        return v.lower()
    if isinstance(v, int) and not isinstance(v, bool):
        return str(v)
    return v


def check_contract_read(claim: dict, rpc, verdict_cls):
    m = _SIG.match(claim["signature"].replace(" ", ""))
    if not m:
        raise ValueError("signature must look like name(argtypes)(returntypes), e.g. totalSupply()(uint256)")
    name, ins, outs = m.group(1), _types(m.group(2)), _types(m.group(3))
    args = claim.get("args", [])
    if len(args) != len(ins):
        raise ValueError("args do not match the signature")
    py_args = [int(a) if t.startswith(("uint", "int")) else a for t, a in zip(ins, args)]
    sel = keccak(f"{name}({','.join(ins)})".encode())[:4]
    data = "0x" + sel.hex() + encode(ins, py_args).hex()
    block = int(claim["block"])
    raw = rpc.eth_call(claim["to"], data, block)
    got = _norm(list(decode(outs, bytes.fromhex(raw[2:]))))
    want = _norm(list(claim["expected"]))
    obs = {"block": block, "returned": got, "blockHash": rpc.block(block).get("hash")}
    if got == want:
        return verdict_cls(100, ["return value matches claim"], obs)
    return verdict_cls(0, [f"returned {got} != claimed {want}"], obs)
