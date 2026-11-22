"""Never answer twice, never score what could not be checked, and only call it done once the chain says so."""
import io
import json
import urllib.error

import pytest

from replay8004 import job as jobmod, networks, registry
from replay8004.hashing import keccak
from replay8004.rpc import RpcError
from tests.conftest import PAYEE, PAYER, USDC, VALIDATOR, FakeRpc
from tests.test_worker import CLAIM, NET, TX, make_worker, request


def ready(tmp_path, mode="ok"):
    rpc = FakeRpc(head=1_000)
    rpc.add_transfer(TX, USDC, PAYER, PAYEE, 10_000, block=940)
    return rpc, make_worker(tmp_path, rpc, mode=mode), request(rpc, CLAIM)


def state(tmp_path):
    return json.loads((tmp_path / "s.json").read_text())


def test_done_only_after_the_registry_shows_our_answer(tmp_path):
    rpc, w, h = ready(tmp_path)
    out = w.poll_once()
    assert len(out["answered"]) == 1 and out["inflight"] == 1 and state(tmp_path)["done"] == {}
    assert w.poll_once()["confirmed"] == []                      # still inside the reorg buffer
    rpc.head += 3
    out = w.poll_once()
    assert [c["requestHash"] for c in out["confirmed"]] == [h] and out["inflight"] == 0
    assert state(tmp_path)["done"][h]["score"] == 100 and len(w.sender.sent) == 1


def test_lost_reply_does_not_answer_twice(tmp_path):
    rpc, w, h = ready(tmp_path, mode="lost")
    w.poll_once()
    w.poll_once()
    rpc.head += 10
    assert w.poll_once()["confirmed"][0]["requestHash"] == h and len(rpc.mined) == 1


@pytest.mark.parametrize("mode", ["crash_before", "crash_after"])
def test_crash_around_broadcast_does_not_answer_twice(tmp_path, mode):
    rpc, w, h = ready(tmp_path, mode=mode)
    with pytest.raises(KeyboardInterrupt):
        w.poll_once()
    signed = state(tmp_path)["inflight"][h]
    again = make_worker(tmp_path, rpc)                           # process restarts on the saved state
    again.poll_once()
    rpc.head += 10
    out = again.poll_once()
    assert out["confirmed"][0]["tx"] == signed["tx"] and len(rpc.mined) == 1


def test_unmined_tx_is_rebroadcast_not_resigned(tmp_path):
    rpc, w, h = ready(tmp_path, mode="dropped")
    w.poll_once()
    raw = state(tmp_path)["inflight"][h]["raw"]
    rpc.head += 50
    w.poll_once()
    assert state(tmp_path)["inflight"][h]["raw"] == raw and rpc.mined == []
    w.sender.mode = "ok"
    w.poll_once()
    rpc.head += 5
    assert w.poll_once()["confirmed"] and len(rpc.mined) == 1


def test_lost_local_state_does_not_answer_twice(tmp_path):
    rpc, w, h = ready(tmp_path)
    w.poll_once()
    (tmp_path / "s.json").unlink()
    again = make_worker(tmp_path, rpc)
    assert again.poll_once()["answered"] == [] and again.sender.sent == []
    assert h in state(tmp_path)["done"]


def test_reverted_answer_is_not_done_and_is_retried_with_the_same_calldata(tmp_path):
    rpc, w, h = ready(tmp_path, mode="revert")
    w.poll_once()
    rpc.head += 5
    w.sender.mode = "ok"
    assert w.poll_once()["confirmed"] == [] and state(tmp_path)["inflight"][h]["attempts"] == 2
    rpc.head += 5
    assert w.poll_once()["confirmed"][0]["requestHash"] == h
    assert len(w.sender.sent) == 2 and w.sender.sent[0] == w.sender.sent[1]


def test_gives_up_after_max_attempts(tmp_path):
    rpc, w, h = ready(tmp_path, mode="revert")
    for _ in range(6):
        out = w.poll_once()
        rpc.head += 5
    assert len(w.sender.sent) == 3 and out["failed"] == 1 and h in state(tmp_path)["failed"]
    assert state(tmp_path)["done"] == {}


def test_stale_store_version_stops_the_broadcast(tmp_path):
    rpc, w, h = ready(tmp_path)

    def conflict(_):
        raise RuntimeError("ConditionalCheckFailed")             # another Lambda saved first
    w.store.save = conflict
    with pytest.raises(RuntimeError):
        w.poll_once()
    assert w.sender.sent == [] and rpc.mined == []


@pytest.mark.parametrize("err", [TimeoutError("slow"), ConnectionResetError(), urllib.error.URLError("dns"),
                                 urllib.error.HTTPError("u", 404, "nope", {}, io.BytesIO()),
                                 urllib.error.HTTPError("u", 503, "busy", {}, io.BytesIO())])
def test_failed_download_is_never_scored_and_recovers(tmp_path, err):
    rpc = FakeRpc(head=1_000)
    rpc.add_transfer(TX, USDC, PAYER, PAYEE, 10_000, block=940)
    raw = jobmod.make_job(42, NET.chain_id, "erc20_transfer", CLAIM)
    rpc.add_request(NET.validation, VALIDATOR, 42, "https://jobs.example/j.json", jobmod.request_hash(raw), 950)
    w = make_worker(tmp_path, rpc)

    def opener(req, timeout=None):
        raise err
    w.fetch = lambda uri: jobmod.fetch(uri, opener=opener)
    for _ in range(w.max_pending_polls + 5):
        out = w.poll_once()
        assert out["answered"] == [] and out["pending"] == 1
    assert w.sender.sent == [] and not list((tmp_path / "ev").glob("*.json"))
    w.fetch = lambda uri: raw
    assert w.poll_once()["answered"][0]["score"] == 100


@pytest.mark.parametrize("uri", ["data:application/json;base64,abc", "http://insecure/j.json", "https://bad host/j.json"])
def test_unusable_request_uri_is_still_answered_zero(tmp_path, uri):
    rpc = FakeRpc(head=1_000)
    rpc.add_request(NET.validation, VALIDATOR, 42, uri, "0x" + "ee" * 32, 950)
    a = make_worker(tmp_path, rpc).poll_once()["answered"][0]
    assert a["score"] == 0 and a["tag"] == "replay:invalid"


def test_sender_sign_does_not_broadcast_and_respects_min_nonce():
    from eth_account import Account
    rpc = FakeRpc()
    s = registry.Sender(rpc, 11142220, Account.create().key.hex())  # throwaway key, never funded
    data = registry.encode_response("0x" + "ab" * 32, 100, "u", "0x" + "cd" * 32, "t")
    signed = s.sign(networks.CELO_SEPOLIA.validation, data)
    assert rpc.sent == [] and signed["nonce"] == 5
    assert signed["tx"] == "0x" + keccak(bytes.fromhex(signed["raw"][2:])).hex()
    assert s.sign(networks.CELO_SEPOLIA.validation, data, min_nonce=9)["nonce"] == 9
    assert s.broadcast(signed["raw"]) == signed["tx"] and rpc.sent == [signed["raw"]]


def test_rpc_error_while_reading_status_defers(tmp_path):
    rpc, w, h = ready(tmp_path)

    def boom(*a):
        raise RpcError("down")
    rpc.eth_call = boom
    out = w.poll_once()
    assert out["answered"] == [] and out["pending"] == 1 and w.sender.sent == []


def test_send_refuses_the_placeholder_evidence_url(tmp_path):
    from replay8004.cli import main
    with pytest.raises(SystemExit, match="evidence-base-url"):
        main(["run", "--validator", VALIDATOR, "--send", "--once", "--state-dir", str(tmp_path)])
