"""Offline replays of data captured from live Celo, plus constants verified against the chain.

Verified 2026-11-20/21 (see docs/VERIFICATION.md): registry addresses (eth_getCode on both networks
and erc-8004-contracts scripts/addresses.ts), selectors and event topic (verified source on
Blockscout and PUSH4/PUSH32 in the deployed bytecode), RPC chain ids.
"""
import json
import urllib.request
from pathlib import Path

import pytest

from replay8004 import job as jobmod, networks, registry
from replay8004.checkers import CHECKERS, Verdict
from replay8004.rpc import Rpc

FIX = Path(__file__).parent / "fixtures"


class ReceiptRpc:
    """Serves one captured receipt and the head block recorded when it was captured."""

    def __init__(self, fixture: dict):
        self.fx = fixture

    def receipt(self, h):
        r = self.fx["receipt"]
        return r if h.lower() == r["transactionHash"].lower() else None

    def block_number(self):
        return self.fx["head"]


def _replay(job_name: str) -> Verdict:
    fx = json.loads((FIX / "receipt-mainnet-usdc-transfer.json").read_text())
    raw = (FIX / job_name).read_bytes()
    job = jobmod.parse(raw, jobmod.request_hash(raw), 1, networks.CELO_MAINNET.chain_id)
    return CHECKERS[job["kind"]](job["claim"], ReceiptRpc(fx), Verdict)


def test_real_mainnet_usdc_transfer_scores_100():
    v = _replay("job-mainnet-usdc-ok.json")
    assert v.score == 100
    assert v.observed["amount"] == "10000000"
    assert v.observed["blockNumber"] == 83339241
    assert v.observed["confirmations"] == 491


def test_real_mainnet_usdc_transfer_wrong_recipient_scores_0():
    v = _replay("job-mainnet-usdc-wrong-to.json")
    assert v.score == 0
    assert v.findings == ["no matching Transfer log (token / from / to)"]


def test_fixture_job_hashes_are_stable():
    # the job bytes are what requestHash commits to; a line-ending or reformat change would break it
    assert jobmod.request_hash((FIX / "job-mainnet-usdc-ok.json").read_bytes()) == \
        "0x1c561345e99d134943f86c1c9545f6ba5c0739ed5edfc3ce6121535ad873768b"
    assert jobmod.request_hash((FIX / "job-mainnet-usdc-wrong-to.json").read_bytes()) == \
        "0xd5aa6b733aeee33cf3591229f60249a5294ffa06515b39620791629796039c01"


# -- constants verified against the live chain ---------------------------------------------------

@pytest.mark.parametrize("net,identity,reputation,validation", [
    (networks.CELO_SEPOLIA, "0x8004A818BFB912233c491871b3d84c89A494BD9e",
     "0x8004B663056A597Dffe9eCcC1965A193B7388713", "0x8004Cb1BF31DAf7788923b405b754f57acEB4272"),
    (networks.CELO_MAINNET, "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
     "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63", "0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58"),
])
def test_canonical_registry_addresses(net, identity, reputation, validation):
    assert (net.identity, net.reputation, net.validation) == (identity, reputation, validation)


def test_chain_ids_and_rpc():
    assert (networks.CELO_SEPOLIA.chain_id, networks.CELO_SEPOLIA.rpc) == \
        (11142220, "https://forno.celo-sepolia.celo-testnet.org")
    assert (networks.CELO_MAINNET.chain_id, networks.CELO_MAINNET.rpc) == (42220, "https://forno.celo.org")


def test_validation_registry_deploy_blocks():
    # proxy creation txs: Sepolia 0x9751b92d..cc3b, mainnet 0x25555ad0..9dfe (Blockscout)
    assert networks.CELO_SEPOLIA.validation_deploy_block == 17_013_556
    assert networks.CELO_MAINNET.validation_deploy_block == 58_396_736


def test_run_starts_scanning_at_deploy_block_not_genesis(monkeypatch, tmp_path):
    from replay8004 import cli
    scanned = []

    class StubRpc:
        def __init__(self, url):
            pass

        def block_number(self):
            return networks.CELO_SEPOLIA.validation_deploy_block + 10

        def logs(self, address, topics, frm, to):
            scanned.append((frm, to))
            return []

    monkeypatch.setattr(cli, "Rpc", StubRpc)
    cli.main(["run", "--validator", "0x" + "33" * 20, "--once", "--state-dir", str(tmp_path)])
    assert scanned[0][0] == networks.CELO_SEPOLIA.validation_deploy_block


def test_selectors_and_topic_match_deployed_bytecode():
    assert registry._sel(registry.SIG_REQUEST).hex() == "aaf400c4"
    assert registry._sel(registry.SIG_RESPONSE).hex() == "3d659a96"
    assert registry._sel(registry.SIG_SUMMARY).hex() == "1b7cabd6"
    assert registry._sel(registry.SIG_STATUS).hex() == "ff2febfc"
    assert registry.TOPIC_REQUEST == "0x530436c3634a98e1e626b0898be2f1e9980cc1bd2a78c07a0aba52d0a48a5059"


def test_decode_real_get_summary():
    # getSummary(1870, [], "") on Celo mainnet: 17 responses, average 99
    raw = "0x" + f"{17:064x}" + f"{99:064x}"
    assert registry.decode_summary(raw) == (17, 99)


# -- forno rejects urllib's default User-Agent with HTTP 403 --------------------------------------

class _Resp:
    def __init__(self, body: bytes):
        self.body = body

    def read(self, n=-1):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_rpc_sends_explicit_user_agent(monkeypatch):
    seen = []

    def fake_urlopen(req, timeout=None):
        seen.append(req)
        return _Resp(b'{"jsonrpc":"2.0","id":1,"result":"0xa4ec"}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert Rpc("https://forno.celo.org").chain_id() == 42220
    ua = seen[0].get_header("User-agent")
    assert ua and ua.startswith("replay8004/") and "Python-urllib" not in ua


def test_job_fetch_sends_explicit_user_agent():
    seen = []

    def opener(req, timeout=None):
        seen.append(req)
        return _Resp(b"{}")

    assert jobmod.fetch("https://example.org/job.json", opener=opener) == b"{}"
    assert seen[0].get_header("User-agent").startswith("replay8004/")
