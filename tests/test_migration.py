"""0.1.1 -> 0.5 state migration and evidence-chain continuity, from a copy of the LIVE mainnet state.

tests/fixtures/state-mainnet-live-2026-11-27.json is the DynamoDB item `pk=worker` of stack replay8004-mainnet
(read with GetItem on 2026-11-27, ver 991; public data only). docs/mainnet/evidence/ holds the 5 bundles it
chains. The first 0.5 answer must be seq 6 with prev = that head: no reset, no fork, nothing answered twice.
"""
import copy
import json
from pathlib import Path

import pytest

from replay8004 import evidence, job as jobmod, networks, status, store
from replay8004.evidence import LocalSink
from replay8004.store import MemoryStore
from replay8004.worker import Worker
from tests.conftest import PAYEE, PAYER, USDC, FakeRpc, FakeSender

ROOT = Path(__file__).parent.parent
LIVE = json.loads((Path(__file__).parent / "fixtures" / "state-mainnet-live-2026-11-27.json").read_text(encoding="utf-8"))
LIVE_BUNDLES = [json.loads(p.read_bytes()) for p in sorted((ROOT / "docs" / "mainnet" / "evidence").glob("0x*.json"))]
NET = networks.get("celo-mainnet", allow_mainnet=True)  # only a Network object: FakeRpc, no RPC is reached
VALIDATOR = "0xd2d6c6deaadf2a5868e8e0c17d674d49531c5952"
TX = "0x" + "aa" * 32
CLAIM = {"txHash": TX, "token": USDC, "from": PAYER, "to": PAYEE, "minAmount": "10000", "minConfirmations": 2}


def test_fixture_is_the_live_chain_head():
    assert LIVE["seq"] == 5 and len(LIVE_BUNDLES) == 5
    assert evidence.verify_chain(LIVE_BUNDLES) == (True, "5 bundles, chain intact")
    last = max(LIVE_BUNDLES, key=lambda b: b["seq"])
    assert evidence.response_hash(last) == LIVE["head"]
    assert {b["requestHash"] for b in LIVE_BUNDLES} == set(LIVE["done"])
    assert {b["checkerVersion"] for b in LIVE_BUNDLES} == {"0.1.1"} and not any("request" in b for b in LIVE_BUNDLES)


def test_migrate_adds_only_missing_keys():
    st = copy.deepcopy(LIVE)
    assert "usage" not in st and "expired" not in st
    assert store.migrate(st) == ["usage", "expired"]
    assert st["usage"] == {} and st["expired"] == {}
    for k in LIVE:  # every existing key, protected or not, is byte-for-byte what it was
        assert json.dumps(st[k], sort_keys=True) == json.dumps(LIVE[k], sort_keys=True), k
    assert store.migrate(st) == []  # idempotent


def test_migrate_never_overwrites_existing_containers():
    st = copy.deepcopy(LIVE)
    st["usage"] = {"42220:7": {"paid": 3, "free": {"2026-11": 2}}}
    st["failed"] = {"0x" + "01" * 32: {"nonce": 9}}
    before = copy.deepcopy(st)
    store.migrate(st)
    assert st["usage"] == before["usage"] and st["failed"] == before["failed"]


@pytest.mark.parametrize("key", store.PROTECTED)
def test_migrate_refuses_a_state_missing_a_protected_key(key):
    st = copy.deepcopy(LIVE)
    del st[key]
    with pytest.raises(ValueError, match="refusing to guess"):
        store.migrate(st)


def test_migrate_upgrades_a_pre_exactly_once_state():
    old = {k: copy.deepcopy(LIVE[k]) for k in ("last_block", "done", "pending", "seq", "head")}  # 0.1.0 shape
    assert store.migrate(old) == ["inflight", "failed", "usage", "expired"]


def live_worker(tmp_path, head):
    rpc = FakeRpc(chain_id=NET.chain_id, head=head)
    mem = MemoryStore()
    mem.save(copy.deepcopy(LIVE))
    sink = LocalSink(tmp_path / "ev", "https://ev.example/evidence")
    w = Worker(network=NET, rpc=rpc, validator=VALIDATOR, sender=FakeSender(rpc, address=VALIDATOR), store=mem,
               sink=sink, clock=lambda: "2026-11-28T00:00:00+00:00")
    return rpc, w, mem, sink


def request(rpc, claim, block, agent=10143):
    raw = jobmod.make_job(agent, NET.chain_id, "erc20_transfer", claim)
    h = jobmod.request_hash(raw)
    rpc.add_request(NET.validation, VALIDATOR, agent, jobmod.data_uri(raw), h, block)
    return h


def test_first_v05_answer_continues_the_live_chain(tmp_path):
    lb = LIVE["last_block"]
    rpc, w, mem, sink = live_worker(tmp_path, head=lb + 20)
    rpc.add_transfer(TX, USDC, PAYER, PAYEE, 10_000, block=lb + 2)
    h = request(rpc, CLAIM, block=lb + 5)
    out = w.poll_once()
    assert out["new"] == 1 and len(out["answered"]) == 1 and out["scanned_to"] == lb + 17
    new = json.loads((tmp_path / "ev" / f"{h}.json").read_bytes())
    assert new["seq"] == LIVE["seq"] + 1 == 6 and new["prev"] == LIVE["head"]
    assert new["checkerVersion"] == "0.5.0"
    assert new["request"] == {"block": lb + 5, "tx": new["request"]["tx"], "checkedAtBlock": lb + 20}
    assert out["answered"][0]["responseHash"] == evidence.response_hash(new)
    # the 5 live 0.1.1 bundles and the new 0.5 one verify as ONE chain
    assert evidence.verify_chain(LIVE_BUNDLES + [new]) == (True, "6 bundles, chain intact")
    st = mem.load()
    assert st["seq"] == 6 and st["head"] == evidence.response_hash(new)
    assert all(st["done"][k] == LIVE["done"][k] for k in LIVE["done"])  # old answers untouched
    assert st["usage"] == {} and st["expired"] == {}  # migrated in the same write


def test_old_requests_seen_again_are_never_reanswered(tmp_path):
    # e.g. a rescan after a reorg or a lost last_block: the 5 live requests reappear in the logs
    lb = LIVE["last_block"]
    rpc, w, mem, _ = live_worker(tmp_path, head=lb + 20)
    for b in LIVE_BUNDLES:
        rpc.add_request(NET.validation, VALIDATOR, b["agentId"], b["requestURI"], b["requestHash"], lb + 3)
    out = w.poll_once()
    assert out["new"] == 5 and out["answered"] == [] and out["pending"] == 0
    assert w.sender.sent == [] and mem.load()["seq"] == 5 and mem.load()["head"] == LIVE["head"]


def test_dry_run_on_the_live_state_previews_seq_6_and_writes_nothing(tmp_path):
    lb = LIVE["last_block"]
    rpc, live, mem, sink = live_worker(tmp_path, head=lb + 20)
    dry = Worker(network=NET, rpc=rpc, validator=VALIDATOR, store=mem, sink=sink,
                 clock=lambda: "2026-11-28T00:00:00+00:00")
    rpc.add_transfer(TX, USDC, PAYER, PAYEE, 10_000, block=lb + 2)
    request(rpc, CLAIM, block=lb + 5)
    preview = dry.poll_once()["answered"][0]
    st = mem.load()
    assert st["seq"] == 5 and st["head"] == LIVE["head"] and not list((tmp_path / "ev").glob("*.json"))
    assert live.poll_once()["answered"][0]["responseHash"] == preview["responseHash"]  # same bundle, seq 6


def test_status_page_over_mixed_versions(tmp_path):
    lb = LIVE["last_block"]
    rpc, w, _, sink = live_worker(tmp_path, head=lb + 20)
    rpc.add_transfer(TX, USDC, PAYER, PAYEE, 10_000, block=lb + 2)
    request(rpc, CLAIM, block=lb + 5)
    w.poll_once()
    st = status.summarize(LIVE_BUNDLES + sink.all(), now="2026-11-28T00:00:00+00:00")
    assert st["answered"] == 6 and st["chain"]["intact"] is True
    assert st["medianSecondsToDecide"] == 15  # only the 0.5 bundle has request blocks; 0.1.1 ones are skipped


def test_live_jobs_still_hash_to_their_on_chain_request_hashes():
    # job format byte-for-byte compatible: the 5 mainnet jobs rebuild to the same bytes and requestHashes
    jobs = sorted((ROOT / "docs" / "mainnet").glob("job-*.json"))
    assert len(jobs) == 5
    for p in jobs:
        raw = p.read_bytes()
        j = json.loads(raw)
        assert jobmod.request_hash(raw) in LIVE["done"], p.name
        assert jobmod.make_job(j["agentId"], j["chainId"], j["kind"], j["claim"], j.get("note", "")) == raw, p.name
        assert jobmod.parse(raw, jobmod.request_hash(raw), j["agentId"], NET.chain_id)["kind"] == j["kind"]
