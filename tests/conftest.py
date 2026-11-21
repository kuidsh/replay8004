"""A fake Celo chain: enough JSON-RPC for the checkers, worker and sender, no network."""
from eth_abi import encode

from replay8004 import registry
from replay8004.checkers.erc20 import BALANCE_OF, TRANSFER_TOPIC
from replay8004.hashing import keccak

USDC = "0xceba9300f2b948710d2653dd7b07f33a8b32118c"   # example token address (format only)
PAYER = "0x1111111111111111111111111111111111111111"
PAYEE = "0x2222222222222222222222222222222222222222"
VALIDATOR = "0x3333333333333333333333333333333333333333"
OTHER_VALIDATOR = "0x4444444444444444444444444444444444444444"


def t_addr(a):
    return "0x" + "00" * 12 + a[2:].lower()


class FakeRpc:
    def __init__(self, chain_id=11142220, head=1_000):
        self.cid, self.head = chain_id, head
        self.receipts, self.calls, self.req_logs, self.sent = {}, {}, [], []

    # typed helpers used by checkers / worker
    def chain_id(self):
        return self.cid

    def block_number(self):
        return self.head

    def receipt(self, h):
        return self.receipts.get(h)

    def block(self, n):
        return {"number": hex(n), "hash": "0x" + keccak(str(n).encode()).hex()}

    def eth_call(self, to, data, block="latest"):
        key = (to.lower(), data, block)
        if key not in self.calls:
            raise AssertionError(f"unexpected eth_call {key}")
        return self.calls[key]

    def logs(self, address, topics, frm, to):
        out = []
        for lg in self.req_logs:
            b = int(lg["blockNumber"], 16)
            if lg["address"].lower() == address.lower() and frm <= b <= to and \
                    all(t is None or t.lower() == lg["topics"][i].lower() for i, t in enumerate(topics)):
                out.append(lg)
        return out

    # raw calls used by Sender
    def call(self, method, params):
        if method == "eth_getTransactionCount":
            return "0x5"
        if method == "eth_estimateGas":
            return hex(120_000)
        if method == "eth_gasPrice":
            return hex(25 * 10**9)
        if method == "eth_maxPriorityFeePerGas":
            return hex(10**8)
        if method == "eth_sendRawTransaction":
            self.sent.append(params[0])
            return "0x" + keccak(bytes.fromhex(params[0][2:])).hex()
        raise AssertionError(method)

    # builders ------------------------------------------------------------
    def add_transfer(self, tx, token, frm, to, amount, block, status=1):
        self.receipts[tx] = {"blockNumber": hex(block), "blockHash": "0x" + "ab" * 32, "status": hex(status),
                             "logs": [{"address": token, "topics": [TRANSFER_TOPIC, t_addr(frm), t_addr(to)],
                                       "data": "0x" + amount.to_bytes(32, "big").hex()}]}

    def set_balance(self, token, holder, block, amount):
        data = BALANCE_OF + encode(["address"], [holder]).hex()
        self.calls[(token.lower(), data, block)] = "0x" + amount.to_bytes(32, "big").hex()

    def add_request(self, validation_addr, validator, agent_id, uri, req_hash, block):
        self.req_logs.append({"address": validation_addr, "blockNumber": hex(block),
                              "transactionHash": "0x" + "cd" * 32,
                              "topics": [registry.TOPIC_REQUEST, t_addr(validator), "0x" + f"{agent_id:064x}",
                                         req_hash],
                              "data": "0x" + encode(["string"], [uri]).hex()})
