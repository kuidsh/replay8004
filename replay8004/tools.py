"""Agent-facing operations behind the MCP server (replay8004/mcp_server.py). Pure apart from the RPC given.

Nothing here holds or asks for a key. Writes come back as unsigned calldata for the agent owner's
own wallet to send, so an MCP client can never move funds or answer as the validator through us.
"""
from __future__ import annotations

import json

from . import gate, job as jobmod, registry
from .checkers import CHECKERS

REASONS = {0: "ok", gate.WRONG_VALIDATOR: "wrong validator", gate.WRONG_AGENT: "wrong agent",
           gate.NO_RESPONSE: "not answered yet", gate.LOW_SCORE: "score below minimum",
           gate.STALE: "answer older than max_age", gate.WRONG_TAG: "wrong tag"}


def build_request(net, agent_id: int, validator: str, kind: str, claim: dict, note: str = "") -> dict:
    """Job bytes, requestHash and the validationRequest calldata (unsigned) for the agent owner to send."""
    if kind not in CHECKERS:
        raise ValueError(f"kind must be one of {sorted(CHECKERS)}")
    raw = jobmod.make_job(agent_id, net.chain_id, kind, claim, note)
    h = jobmod.request_hash(raw)
    uri = jobmod.data_uri(raw)
    return {"network": net.name, "chainId": net.chain_id, "kind": kind, "tag": f"replay:{kind}",
            "job": json.loads(raw), "requestHash": h, "requestURI": uri,
            "tx": {"to": net.validation, "data": registry.encode_request(validator, agent_id, uri, h), "value": "0"},
            "send_from": "the agent's owner or approved operator (the registry rejects anyone else)"}


def claim_status(rpc, net, request_hash: str, agent_id: int, validator: str, tag: str = "",
                 min_score: int = 100, max_age: int = 0) -> dict:
    ok, why, s = gate.claim_status(rpc, net, request_hash, agent_id, validator, tag, min_score, max_age)
    return {"ok": ok, "reason": why, "reasonText": REASONS[why], "status": s}


def agent_record(rpc, net, agent_id: int, validator: str, tag: str = "", min_count: int = 3, min_avg: int = 90) -> dict:
    count, avg = gate.record(rpc, net, agent_id, validator, tag)
    return {"count": count, "avg": avg, "tag": tag, "validator": validator.lower(),
            "passes": count >= max(1, min_count) and avg >= min_avg, "minCount": min_count, "minAvg": min_avg}


def agent_validations(rpc, net, agent_id: int, limit: int = 50) -> dict:
    hashes = registry.decode_agent_validations(rpc.eth_call(net.validation, registry.encode_agent_validations(agent_id)))
    return {"agentId": agent_id, "total": len(hashes), "requestHashes": hashes[-limit:]}


def registry_info(rpc, net) -> dict:
    try:
        return {"ok": True, "network": net.name, "validationRegistry": net.validation, **registry.verify_deployment(rpc, net)}
    except registry.DeploymentError as e:
        return {"ok": False, "network": net.name, "validationRegistry": net.validation, "error": str(e)}
