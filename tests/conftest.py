"""A fake Celo chain: enough JSON-RPC for the checkers, worker and sender, no network."""
from eth_abi import decode, encode

from replay8004 import registry
from replay8004.checkers.erc20 import BALANCE_OF, TRANSFER_TOPIC
from replay8004.hashing import keccak
from replay8004.rpc import RpcError

USDC = "0xceba9300f2b948710d2653dd7b07f33a8b32118c"   # example token address (format only)
PAYER = "0x1111111111111111111111111111111111111111"
PAYEE = "0x2222222222222222222222222222222222222222"
VALIDATOR = "0x3333333333333333333333333333333333333333"
OTHER_VALIDATOR = "0x4444444444444444444444444444444444444444"


def t_addr(a):
    return "0x" + "00" * 12 + a[2:].lower()


class FakeSender:
    """Stands in for registry.Sender (no key). `sent` lists txs the fake chain accepted (one per nonce).
    mode: ok | lost (accepted, reply lost) | revert (mined, reverts) | dropped (never reaches the chain)
          | crash_after / crash_before (process dies around the broadcast)"""

    def __init__(self, rpc, address=VALIDATOR, mode="ok"):
        self.rpc, self.address, self.mode, self.sent = rpc, address, mode, []

    def sign(self, to, data, min_nonce=0):
        nonce = max(len(self.rpc.mined), min_nonce)
        raw = f"{nonce}|{to}|{data}"
        return {"raw": raw, "tx": "0x" + keccak(raw.encode()).hex(), "nonce": nonce}

    def broadcast(self, raw):
        nonce, to, data = raw.split("|")
        if self.mode == "crash_before":
            raise KeyboardInterrupt
        if self.mode == "dropped":
            raise RpcError("connection reset")
        if int(nonce) != len(self.rpc.mined):
            raise RpcError("nonce too low")
        self.sent.append((to, data))
        self.rpc.mine_response(data, reverts=self.mode == "revert")
        if self.mode == "crash_after":
            raise KeyboardInterrupt
        if self.mode == "lost":
            raise RpcError("timed out")
        return "0x" + keccak(raw.encode()).hex()


class FakeRpc:
    def __init__(self, chain_id=11142220, head=1_000):
        self.cid, self.head = chain_id, head
        self.receipts, self.calls, self.req_logs, self.sent = {}, {}, [], []
        self.mined, self.answers = [], {}  # block of each validator tx (index = nonce); requestHash -> answer

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
        if data.startswith("0x" + registry._sel(registry.SIG_STATUS).hex()):
            at = self.head if block == "latest" else block
            b, resp, rh, tag = self.answers.get("0x" + data[10:], (None, 0, bytes(32), ""))
            if b is None or b > at:
                resp, rh, tag = 0, bytes(32), ""
            return "0x" + encode(["address", "uint256", "uint8", "bytes32", "string", "uint256"],
                                 [VALIDATOR, 0, resp, rh, tag, 0]).hex()
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

    def nonce_at(self, address, block):
        return sum(1 for b in self.mined if b <= block)

    def mine_response(self, calldata, reverts=False):
        self.mined.append(self.head)
        if not reverts:
            h, resp, _, rh, tag = decode(["bytes32", "uint8", "string", "bytes32", "string"], bytes.fromhex(calldata[10:]))
            self.answers["0x" + h.hex()] = (self.head, resp, rh, tag)

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

    def add_x402_settlement(self, tx, token, payer, pay_to, amount, block, nonce=None, sender=None, status=1):
        """A transferWithAuthorization receipt: AuthorizationUsed + Transfer from the token contract."""
        from replay8004.checkers.x402 import AUTHORIZATION_USED_TOPIC
        logs = []
        if nonce:
            logs.append({"address": token, "topics": [AUTHORIZATION_USED_TOPIC, t_addr(payer), nonce], "data": "0x"})
        logs.append({"address": token, "topics": [TRANSFER_TOPIC, t_addr(payer), t_addr(pay_to)],
                     "data": "0x" + amount.to_bytes(32, "big").hex()})
        self.receipts[tx] = {"blockNumber": hex(block), "blockHash": "0x" + "ab" * 32, "status": hex(status),
                             "from": sender or "0x5555555555555555555555555555555555555555", "logs": logs}

    def set_balance(self, token, holder, block, amount):
        data = BALANCE_OF + encode(["address"], [holder]).hex()
        self.calls[(token.lower(), data, block)] = "0x" + amount.to_bytes(32, "big").hex()

    def add_request(self, validation_addr, validator, agent_id, uri, req_hash, block):
        self.req_logs.append({"address": validation_addr, "blockNumber": hex(block),
                              "transactionHash": "0x" + "cd" * 32,
                              "topics": [registry.TOPIC_REQUEST, t_addr(validator), "0x" + f"{agent_id:064x}",
                                         req_hash],
                              "data": "0x" + encode(["string"], [uri]).hex()})
