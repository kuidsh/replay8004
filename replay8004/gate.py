"""Off-chain gate: the same rules as contracts/ReplayGate.sol, for agents and backends in Python.

  passes(rpc, net, agent_id, validator, tag, min_count=3, min_avg=90)   track record via getSummary
  claim_status(rpc, net, request_hash, agent_id, tag, min_score, max_age, now)  one request via getValidationStatus
Reason codes match the contract: 1 wrong validator, 2 wrong agent, 3 no response, 4 low score, 5 stale, 6 wrong tag.
"""
from __future__ import annotations

import time

from . import registry

WRONG_VALIDATOR, WRONG_AGENT, NO_RESPONSE, LOW_SCORE, STALE, WRONG_TAG = 1, 2, 3, 4, 5, 6


def record(rpc, net, agent_id: int, validator: str, tag: str = "") -> tuple[int, int]:
    return registry.decode_summary(rpc.eth_call(net.validation, registry.encode_summary(agent_id, [validator], tag)))


def passes(rpc, net, agent_id: int, validator: str, tag: str = "", min_count: int = 3, min_avg: int = 90) -> bool:
    count, avg = record(rpc, net, agent_id, validator, tag)
    return count >= max(1, min_count) and avg >= min_avg


encode_status, decode_status = registry.encode_status, registry.decode_status  # one codec, shared


def claim_status(rpc, net, request_hash: str, agent_id: int, validator: str, tag: str = "", min_score: int = 100,
                 max_age: int = 0, now: int | None = None) -> tuple[bool, int, dict]:
    s = decode_status(rpc.eth_call(net.validation, encode_status(request_hash)))
    now = int(time.time()) if now is None else now
    if s["validator"] != validator.lower():
        return False, WRONG_VALIDATOR, s
    if s["agentId"] != int(agent_id):
        return False, WRONG_AGENT, s
    if int(s["responseHash"], 16) == 0:
        return False, NO_RESPONSE, s
    if tag and s["tag"] != tag:
        return False, WRONG_TAG, s
    if s["response"] < min_score:
        return False, LOW_SCORE, s
    if max_age and now > s["lastUpdate"] + max_age:
        return False, STALE, s
    return True, 0, s
