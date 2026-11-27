"""Write tests/vectors/client.json: jobs, hashes and calldata the TypeScript client must reproduce."""
import json
from pathlib import Path

from replay8004 import job as jobmod, registry
from replay8004.checkers.x402 import decode_header  # noqa: F401  (kind exists)

VALIDATOR = "0x3333333333333333333333333333333333333333"
CASES = [
    (42, 11142220, "erc20_transfer", {"txHash": "0x" + "aa" * 32, "token": "0x01C5C0122039549AD1493B8220cABEdD739BC44E",
                                      "to": "0x2222222222222222222222222222222222222222", "minAmount": "10000",
                                      "minConfirmations": 2}, ""),
    (7, 42220, "x402_settlement", {"requirements": {"scheme": "exact", "network": "eip155:42220", "amount": "10000",
                                                    "asset": "0xcebA9300f2b948710d2653dD7B07f33A8B32118C",
                                                    "payTo": "0x2222222222222222222222222222222222222222",
                                                    "maxTimeoutSeconds": 60, "extra": {"name": "USDC", "version": "2"}},
                                   "settlement": {"success": True, "transaction": "0x" + "bb" * 32,
                                                  "network": "eip155:42220",
                                                  "payer": "0x1111111111111111111111111111111111111111"},
                                   "minConfirmations": 2}, "pagó por la API ✓ \"quoted\" \\ tab\t"),
]


def build():
    out = []
    for agent, chain, kind, claim, note in CASES:
        raw = jobmod.make_job(agent, chain, kind, claim, note)
        h = jobmod.request_hash(raw)
        uri = jobmod.data_uri(raw)
        out.append({"input": {"agentId": agent, "chainId": chain, "kind": kind, "claim": claim, "note": note},
                    "jobUtf8": raw.decode(), "requestHash": h, "dataUri": uri,
                    "requestCalldata": registry.encode_request(VALIDATOR, agent, uri, h), "validator": VALIDATOR,
                    "summaryCalldata": registry.encode_summary(agent, [VALIDATOR], "replay:" + kind)})
    return out


if __name__ == "__main__":
    p = Path(__file__).parent / "vectors" / "client.json"
    p.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n")
    print(p)
