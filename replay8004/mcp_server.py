"""replay8004 MCP server (stdio). Read-only plus unsigned calldata; no keys, no sending.

  pip install "replay8004[mcp]"
  REPLAY8004_VALIDATOR=0x... replay8004-mcp            # Celo Sepolia by default
Claude Desktop / Code, Celina-style MCP agents or any MCP client:
  {"mcpServers": {"replay8004": {"command": "replay8004-mcp", "env": {"REPLAY8004_VALIDATOR": "0x..."}}}}
Mainnet reads need REPLAY8004_NETWORK=celo-mainnet and REPLAY8004_ALLOW_MAINNET=1 (reads only; still no keys).
"""
from __future__ import annotations

import os

from . import networks, tools
from .rpc import Rpc


def _ctx():
    net = networks.get(os.environ.get("REPLAY8004_NETWORK", "celo-sepolia"),
                       allow_mainnet=os.environ.get("REPLAY8004_ALLOW_MAINNET") == "1")
    return net, Rpc(os.environ.get("REPLAY8004_RPC", net.rpc))


def _validator(v: str | None) -> str:
    v = v or os.environ.get("REPLAY8004_VALIDATOR", "")
    if not (v.startswith("0x") and len(v) == 42):
        raise ValueError("pass validator or set REPLAY8004_VALIDATOR to the replay8004 validator address")
    return v


def build_server():
    from mcp.server.fastmcp import FastMCP  # mcp<2 (2.x renamed FastMCP)
    srv = FastMCP("replay8004")

    @srv.tool()
    def request_validation(agent_id: int, kind: str, claim: dict, validator: str | None = None, note: str = "") -> dict:
        """Build a replay8004 validation request for one of your agent's claims (kinds: erc20_transfer,
        erc20_balance, contract_read, x402_settlement). Returns unsigned calldata: the agent's owner
        sends it from their own wallet. Nothing is signed or sent here."""
        net, _ = _ctx()
        return tools.build_request(net, agent_id, _validator(validator), kind, claim, note)

    @srv.tool()
    def check_claim(request_hash: str, agent_id: int, tag: str = "", min_score: int = 100, max_age: int = 0,
                    validator: str | None = None) -> dict:
        """Has this validation request been answered by the validator, for this agent and tag, with at
        least min_score and no older than max_age seconds? Same rules as ReplayGate.sol."""
        net, rpc = _ctx()
        return tools.claim_status(rpc, net, request_hash, agent_id, _validator(validator), tag, min_score, max_age)

    @srv.tool()
    def agent_track_record(agent_id: int, tag: str = "", min_count: int = 3, min_avg: int = 90,
                           validator: str | None = None) -> dict:
        """An agent's answered validations from this validator only (count, integer average) and
        whether it passes the thresholds. Use before trusting or paying another agent."""
        net, rpc = _ctx()
        return tools.agent_record(rpc, net, agent_id, _validator(validator), tag, min_count, min_avg)

    @srv.tool()
    def list_agent_validations(agent_id: int, limit: int = 50) -> dict:
        """All validation requestHashes recorded for an agent (any validator), newest last."""
        net, rpc = _ctx()
        return tools.agent_validations(rpc, net, agent_id, limit)

    @srv.tool()
    def registry_check() -> dict:
        """Verify the configured ValidationRegistry points at this network's Identity Registry."""
        net, rpc = _ctx()
        return tools.registry_info(rpc, net)

    return srv


def main():  # pragma: no cover
    build_server().run()


if __name__ == "__main__":  # pragma: no cover
    main()
