"""ERC-8004 ValidationRegistry: calldata encoding, event decoding and reads.

Signatures from erc-8004-contracts ValidationRegistryUpgradeable.sol (read 2026-11-20):
  validationRequest(address validatorAddress, uint256 agentId, string requestURI, bytes32 requestHash)
  validationResponse(bytes32 requestHash, uint8 response, string responseURI, bytes32 responseHash, string tag)
  getSummary(uint256 agentId, address[] validatorAddresses, string tag) -> (uint64 count, uint8 avgResponse)
  getIdentityRegistry() -> address, getVersion() -> string, getAgentValidations(uint256) -> bytes32[]
  event ValidationRequest(address indexed validatorAddress, uint256 indexed agentId, string requestURI, bytes32 indexed requestHash)
Only the agent's owner/operator may request; only the named validator may respond.
"""
from __future__ import annotations

from eth_abi import decode, encode

from .hashing import hex32, keccak


def _sel(sig: str) -> bytes:
    return keccak(sig.encode())[:4]


SIG_REQUEST = "validationRequest(address,uint256,string,bytes32)"
SIG_RESPONSE = "validationResponse(bytes32,uint8,string,bytes32,string)"
SIG_SUMMARY = "getSummary(uint256,address[],string)"
SIG_STATUS = "getValidationStatus(bytes32)"
SIG_IDENTITY = "getIdentityRegistry()"
SIG_VERSION = "getVersion()"
SIG_AGENT_VALIDATIONS = "getAgentValidations(uint256)"
TOPIC_REQUEST = "0x" + keccak(b"ValidationRequest(address,uint256,string,bytes32)").hex()


def topic_address(a: str) -> str:
    return "0x" + "00" * 12 + a.lower()[2:]


def encode_request(validator: str, agent_id: int, uri: str, request_hash: str) -> str:
    return "0x" + (_sel(SIG_REQUEST) + encode(["address", "uint256", "string", "bytes32"],
                                              [validator, int(agent_id), uri, hex32(request_hash)])).hex()


def encode_response(request_hash: str, score: int, uri: str, response_hash: str, tag: str) -> str:
    if not 0 <= score <= 100:
        raise ValueError("score must be 0..100")
    return "0x" + (_sel(SIG_RESPONSE) + encode(["bytes32", "uint8", "string", "bytes32", "string"],
                                               [hex32(request_hash), score, uri, hex32(response_hash), tag])).hex()


def encode_summary(agent_id: int, validators: list[str], tag: str) -> str:
    return "0x" + (_sel(SIG_SUMMARY) + encode(["uint256", "address[]", "string"], [int(agent_id), validators, tag])).hex()


def decode_summary(raw: str) -> tuple[int, int]:
    count, avg = decode(["uint64", "uint8"], bytes.fromhex(raw[2:]))
    return int(count), int(avg)


def encode_status(request_hash: str) -> str:
    return "0x" + (_sel(SIG_STATUS) + encode(["bytes32"], [hex32(request_hash)])).hex()


def decode_status(raw: str) -> dict:
    """getValidationStatus -> (validatorAddress, agentId, response, responseHash, tag, lastUpdate).
    The call reverts ("unknown") for a requestHash that was never requested."""
    va, agent, resp, rh, tag, last = decode(["address", "uint256", "uint8", "bytes32", "string", "uint256"],
                                            bytes.fromhex(raw[2:]))
    return {"validator": va.lower(), "agentId": int(agent), "response": int(resp), "responseHash": "0x" + rh.hex(),
            "tag": tag, "lastUpdate": int(last)}


def decode_request_log(log: dict) -> dict:
    t = log["topics"]
    if t[0].lower() != TOPIC_REQUEST:
        raise ValueError("not a ValidationRequest log")
    (uri,) = decode(["string"], bytes.fromhex(log["data"][2:]))
    return {"validator": "0x" + t[1][-40:].lower(), "agentId": int(t[2], 16), "requestHash": t[3].lower(),
            "requestURI": uri, "blockNumber": int(log["blockNumber"], 16), "txHash": log.get("transactionHash")}


class DeploymentError(RuntimeError):
    pass


def verify_deployment(rpc, net) -> dict:
    """Refuse a ValidationRegistry that isn't wired to the network's Identity Registry.

    The Validation Registry spec is still a preview and the erc-8004-contracts README lists no Celo address,
    so the address in networks.py (erc-8004-contracts scripts/addresses.ts) is checked on-chain before use:
    getIdentityRegistry() must return net.identity. Returns {"identityRegistry", "version"}.
    """
    try:
        raw = rpc.eth_call(net.validation, "0x" + _sel(SIG_IDENTITY).hex())
    except Exception as e:  # no contract, revert, or RPC failure
        raise DeploymentError(f"cannot read getIdentityRegistry() at {net.validation}: {e}") from e
    if not raw or raw == "0x":
        raise DeploymentError(f"no ValidationRegistry at {net.validation}")
    (ident,) = decode(["address"], bytes.fromhex(raw[2:]))
    if ident.lower() != net.identity.lower():
        raise DeploymentError(f"{net.validation} points at identity registry {ident}, expected {net.identity}")
    try:
        (version,) = decode(["string"], bytes.fromhex(rpc.eth_call(net.validation, "0x" + _sel(SIG_VERSION).hex())[2:]))
    except Exception:
        version = "unknown"
    return {"identityRegistry": ident.lower(), "version": version}


def encode_agent_validations(agent_id: int) -> str:
    return "0x" + (_sel(SIG_AGENT_VALIDATIONS) + encode(["uint256"], [int(agent_id)])).hex()


def decode_agent_validations(raw: str) -> list[str]:
    (hashes,) = decode(["bytes32[]"], bytes.fromhex(raw[2:]))
    return ["0x" + h.hex() for h in hashes]


class Sender:
    """Signs and sends one transaction with the validator key (env var only, never logged)."""

    def __init__(self, rpc, chain_id: int, private_key: str):
        from eth_account import Account
        self.rpc, self.chain_id = rpc, chain_id
        try:
            self._acct = Account.from_key(private_key)
        except Exception:  # never let the library echo (part of) the key into a traceback or log
            raise ValueError("the validator key is not a valid private key (expected 0x + 64 hex characters)") from None
        self.address = self._acct.address
        if rpc.chain_id() != chain_id:
            raise RuntimeError(f"RPC chain id {rpc.chain_id()} != expected {chain_id}")

    def sign(self, to: str, data: str, min_nonce: int = 0) -> dict:
        """Sign without broadcasting, so the caller can persist the exact tx first. `min_nonce` keeps a
        lagging RPC backend from reusing the nonce of a tx that is still in flight."""
        nonce = max(int(self.rpc.call("eth_getTransactionCount", [self.address, "pending"]), 16), min_nonce)
        gas = int(self.rpc.call("eth_estimateGas", [{"from": self.address, "to": to, "data": data}]), 16)
        base = int(self.rpc.call("eth_gasPrice", []), 16)
        tip = int(self.rpc.call("eth_maxPriorityFeePerGas", []), 16)
        tx = {"chainId": self.chain_id, "nonce": nonce, "to": to, "data": data, "value": 0,
              "gas": gas * 12 // 10, "maxFeePerGas": base * 2 + tip, "maxPriorityFeePerGas": tip, "type": 2}
        signed = self._acct.sign_transaction(tx)
        raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        return {"raw": "0x" + raw.hex().removeprefix("0x"), "tx": "0x" + signed.hash.hex().removeprefix("0x"),
                "nonce": nonce}

    def broadcast(self, raw: str) -> str:
        return self.rpc.call("eth_sendRawTransaction", [raw])

    def send(self, to: str, data: str) -> str:
        return self.broadcast(self.sign(to, data)["raw"])
