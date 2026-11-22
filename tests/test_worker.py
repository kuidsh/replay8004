import json

from eth_abi import decode

from replay8004 import evidence, job as jobmod, networks
from replay8004.evidence import LocalSink
from replay8004.store import FileStore
from replay8004.worker import Worker
from tests.conftest import OTHER_VALIDATOR, PAYEE, PAYER, USDC, VALIDATOR, FakeRpc, FakeSender

NET = networks.CELO_SEPOLIA
TX = "0x" + "aa" * 32


def make_worker(tmp_path, rpc, dry=False, mode="ok"):
    return Worker(network=NET, rpc=rpc, validator=VALIDATOR, sender=None if dry else FakeSender(rpc, mode=mode),
                  store=FileStore(tmp_path / "s.json", start_block=900),
                  sink=LocalSink(tmp_path / "ev", "https://ev.example"), clock=lambda: "2026-11-20T00:00:00+00:00")


def setup(tmp_path, head=1_000, dry=False):
    rpc = FakeRpc(head=head)
    return rpc, make_worker(tmp_path, rpc, dry)


def request(rpc, claim, agent=42, block=950, validator=VALIDATOR, kind="erc20_transfer", chain=NET.chain_id):
    raw = jobmod.make_job(agent, chain, kind, claim)
    h = jobmod.request_hash(raw)
    rpc.add_request(NET.validation, validator, agent, jobmod.data_uri(raw), h, block)
    return h


CLAIM = {"txHash": TX, "token": USDC, "from": PAYER, "to": PAYEE, "minAmount": "10000", "minConfirmations": 2}


def decode_calldata(cd):
    return decode(["bytes32", "uint8", "string", "bytes32", "string"], bytes.fromhex(cd[10:]))


def test_end_to_end_live(tmp_path):
    rpc, w = setup(tmp_path)
    rpc.add_transfer(TX, USDC, PAYER, PAYEE, 10_000, block=940)
    h = request(rpc, CLAIM)
    out = w.poll_once()
    assert out["new"] == 1 and len(out["answered"]) == 1 and out["dryRun"] is False
    a = out["answered"][0]
    assert a["score"] == 100 and a["tag"] == "replay:erc20_transfer" and a["tx"].startswith("0x")
    assert w.sender.sent == [(NET.validation, a["calldata"])]
    rh, score, uri, resp_hash, tag = decode_calldata(a["calldata"])
    assert "0x" + rh.hex() == h and score == 100 and uri == a["responseURI"]
    bundle = json.loads((tmp_path / "ev" / f"{h}.json").read_bytes())
    assert "0x" + resp_hash.hex() == evidence.response_hash(bundle)
    assert bundle["verdict"]["observed"]["blockNumber"] == 940


def test_dry_run_writes_nothing_and_leaves_request_for_live_run(tmp_path):
    rpc, dry = setup(tmp_path, dry=True)
    rpc.add_transfer(TX, USDC, PAYER, PAYEE, 10_000, block=940)
    h = request(rpc, CLAIM)
    out = dry.poll_once()
    a = out["answered"][0]
    assert out["dryRun"] is True and a["tx"] is None and a["score"] == 100 and out["pending"] == 1
    assert not list((tmp_path / "ev").glob("*.json"))          # no evidence written
    st = json.loads((tmp_path / "s.json").read_text())
    assert h in st["pending"] and st["done"] == {} and st["seq"] == 0 and st["pending"][h]["polls"] == 0
    assert st["head"] == evidence.GENESIS and st["last_block"] == 997  # only scan progress saved
    # a second dry run sees the same request again, still without writing anything
    assert dry.poll_once()["answered"][0]["calldata"] == a["calldata"]
    # the live run on the same state answers it, with exactly the calldata the dry run showed
    live = make_worker(tmp_path, rpc)
    res = live.poll_once()
    assert [x["calldata"] for x in res["answered"]] == [a["calldata"]] and len(live.sender.sent) == 1
    assert (tmp_path / "ev" / f"{h}.json").exists()
    assert live.poll_once()["answered"] == []                   # and never again


def test_dry_run_simulates_chain_across_several_answers(tmp_path):
    rpc, dry = setup(tmp_path, dry=True)
    hashes = []
    for i in range(3):
        tx = "0x" + f"{i:02x}" * 32
        rpc.add_transfer(tx, USDC, PAYER, PAYEE, 10_000, block=900 + i)
        hashes.append(request(rpc, dict(CLAIM, txHash=tx), block=960 - 5 * i))  # later request, earlier block
    dry_out = dry.poll_once()["answered"]
    live_out = make_worker(tmp_path, rpc).poll_once()["answered"]  # reloads state (keys sorted by hash)
    assert len(dry_out) == len(live_out) == 3
    assert [a["responseHash"] for a in dry_out] == [a["responseHash"] for a in live_out]
    assert [a["requestHash"] for a in live_out] == hashes[::-1]  # answered in request-block order
    assert evidence.verify_chain(LocalSink(tmp_path / "ev", "x").all()) == (True, "3 bundles, chain intact")


def test_ignores_requests_for_other_validators_and_reorg_buffer(tmp_path):
    rpc, w = setup(tmp_path)
    request(rpc, CLAIM, validator=OTHER_VALIDATOR)
    request(rpc, CLAIM, block=999)  # inside the 3-block reorg buffer
    out = w.poll_once()
    assert out["new"] == 0 and out["scanned_to"] == 997
    rpc.head = 1_005
    assert w.poll_once()["new"] == 1


def test_pending_until_confirmed_then_answered_once(tmp_path):
    rpc, w = setup(tmp_path)
    rpc.add_transfer(TX, USDC, PAYER, PAYEE, 10_000, block=996)
    request(rpc, dict(CLAIM, minConfirmations=10), block=990)
    first = w.poll_once()
    assert first["answered"] == [] and first["pending"] == 1
    rpc.head = 1_006
    second = w.poll_once()
    assert len(second["answered"]) == 1 and second["answered"][0]["score"] == 100
    assert w.poll_once()["answered"] == []  # never answers twice


def test_invalid_job_answered_with_zero_and_reason(tmp_path):
    rpc, w = setup(tmp_path)
    request(rpc, CLAIM, chain=42220)  # job says mainnet, request is on Sepolia
    a = w.poll_once()["answered"][0]
    assert a["score"] == 0 and a["tag"] == "replay:invalid"
    bundle = json.loads((tmp_path / "ev" / f"{a['requestHash']}.json").read_bytes())
    assert "chainId" in bundle["verdict"]["findings"][0]


def test_rpc_failure_keeps_request_pending(tmp_path):
    rpc, w = setup(tmp_path)
    request(rpc, CLAIM)

    def boom(_):
        raise ConnectionError("rpc down")
    rpc.receipt = boom
    out = w.poll_once()
    assert out["answered"] == [] and out["pending"] == 1


def test_missing_receipt_is_never_answered_and_recovers(tmp_path):
    # forno prunes receipts: a real old payment looks missing, and must not get a permanent on-chain 0
    rpc, w = setup(tmp_path)
    h = request(rpc, CLAIM)
    for _ in range(w.max_pending_polls + 5):
        out = w.poll_once()
        assert out["answered"] == [] and out["pending"] == 1
    assert w.sender.sent == [] and not (tmp_path / "ev" / f"{h}.json").exists()
    rpc.add_transfer(TX, USDC, PAYER, PAYEE, 10_000, block=940)  # e.g. moved to an archive RPC
    assert w.poll_once()["answered"][0]["score"] == 100


def test_evidence_chain_and_tamper_detection(tmp_path):
    rpc, w = setup(tmp_path)
    for i in range(3):
        tx = "0x" + f"{i:02x}" * 32
        rpc.add_transfer(tx, USDC, PAYER, PAYEE, 10_000, block=900 + i)
        request(rpc, dict(CLAIM, txHash=tx), block=950 + i)
    assert len(w.poll_once()["answered"]) == 3
    bundles = LocalSink(tmp_path / "ev", "x").all()
    assert evidence.verify_chain(bundles) == (True, "3 bundles, chain intact")
    edited = sorted(bundles, key=lambda b: b["seq"])
    edited[0]["verdict"]["score"] = 1
    assert not evidence.verify_chain(edited)[0]
    assert "gap" in evidence.verify_chain([b for b in edited if b["seq"] != 2])[1]


def test_cli_check_reports_missing_receipt_as_undecidable(tmp_path, capsys, monkeypatch):
    from replay8004 import cli
    monkeypatch.setattr(cli, "Rpc", lambda url: FakeRpc())
    job = tmp_path / "job.json"
    job.write_bytes(jobmod.make_job(42, NET.chain_id, "erc20_transfer", CLAIM))
    cli.main(["check", str(job)])
    out = json.loads(capsys.readouterr().out)
    assert out["decidable"] is False and "no receipt" in out["reason"] and "score" not in out


def test_cli_job_prints_request_calldata(tmp_path, capsys, monkeypatch):
    from replay8004.cli import main
    monkeypatch.chdir(tmp_path)
    main(["job", "erc20-transfer", "--agent-id", "42", "--validator", VALIDATOR, "--tx", TX, "--token", USDC,
          "--to", PAYEE, "--min-amount", "10000", "--out", "job.json"])
    out = json.loads(capsys.readouterr().out)
    raw = (tmp_path / "job.json").read_bytes()
    assert out["requestHash"] == jobmod.request_hash(raw) and out["to"] == NET.validation
    assert out["calldata"].startswith("0x")
