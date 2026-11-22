"""Minimal JSON-RPC client (stdlib only) plus the typed calls the checkers need."""
from __future__ import annotations

import json
import time
import urllib.request

from . import __version__

# forno.celo.org returns HTTP 403 to urllib's default "Python-urllib/3.x" User-Agent on every call tried;
# Celo Sepolia forno accepts it (checked 2026-11-20 and 2026-11-21).
USER_AGENT = f"replay8004/{__version__}"


class RpcError(RuntimeError):
    pass


class ReceiptUnavailable(RpcError):
    """The RPC returned no receipt. That is NOT proof the tx does not exist: forno prunes old receipts
    (Celo Sepolia after 10-20k blocks, mainnet after 200k-1M), so it must never be scored 0."""


class Rpc:
    def __init__(self, url: str, timeout: float = 15, retries: int = 2):
        self.url, self.timeout, self.retries = url, timeout, retries
        self._id = 0

    def call(self, method: str, params: list):
        self._id += 1
        body = json.dumps({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}).encode()
        last = None
        for attempt in range(self.retries + 1):
            try:
                req = urllib.request.Request(self.url, data=body, headers={"Content-Type": "application/json",
                                                                           "User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    out = json.loads(r.read())
                if "error" in out:
                    raise RpcError(f"{method}: {out['error']}")
                return out["result"]
            except RpcError:
                raise
            except Exception as e:  # network: back off, then give up (the job is retried next poll)
                last = e
                time.sleep(0.5 * (attempt + 1))
        raise RpcError(f"{method}: {last}")

    # typed helpers -----------------------------------------------------------
    def chain_id(self) -> int:
        return int(self.call("eth_chainId", []), 16)

    def block_number(self) -> int:
        return int(self.call("eth_blockNumber", []), 16)

    def receipt(self, tx_hash: str) -> dict | None:
        return self.call("eth_getTransactionReceipt", [tx_hash])

    def block(self, number: int) -> dict:
        return self.call("eth_getBlockByNumber", [hex(number), False])

    def eth_call(self, to: str, data: str, block: int | str = "latest") -> str:
        return self.call("eth_call", [{"to": to, "data": data}, hex(block) if isinstance(block, int) else block])

    def logs(self, address: str, topics: list, from_block: int, to_block: int) -> list:
        return self.call("eth_getLogs", [{"address": address, "topics": topics,
                                          "fromBlock": hex(from_block), "toBlock": hex(to_block)}])
