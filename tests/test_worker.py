import json

from eth_abi import decode

from replay8004 import evidence, job as jobmod, networks
from replay8004.evidence import LocalSink
from replay8004.store import FileStore
from replay8004.worker import Worker
from tests.conftest import OTHER_VALIDATOR, PAYEE, PAYER, USDC, VALIDATOR, FakeRpc

NET = networks.CELO_SEPOLIA
TX = "0x" + "aa" * 32


def setup(tmp_path, head=1_000):
    rpc = FakeRpc(head=head)
    w = Worker(network=NET, rpc=rpc, validator=VALIDATOR, store=FileStore(tmp_path / "s.json", start_block=900),
               sink=LocalSink(tmp_path / "ev", "https://ev.example"), clock=lambda: "2026-11-20T00:00:00+00:00")
    return rpc, w


def request(rpc, claim, agent=42, block=950, validator=VALIDATOR, kind="erc20_transfer", chain=NET.chain_id):
    raw = jobmod.make_job(agent, chain, kind, claim)
    h = jobmod.request_hash(raw)
    rpc.add_request(NET.validation, validator, agent, jobmod.data_uri(raw), h, block)
    return h


CLAIM = {"txHash": TX, "token": USDC, "from": PAYER, "to": PAYEE, "minAmount": "10000", "minConfirmations": 2}


def decode_calldata(cd):
    return decode(["bytes32", "uint8", "string", "bytes32", "string"], bytes.fromhex(cd[10:]))


def test_end_to_end_dry_run(tmp_path):
    rpc, w = setup(tmp_path)
    rpc.add_transfer(TX, USDC, PAYER, PAYEE, 10_000, block=940)
    h = request(rpc, CLAIM)
    out = w.poll_once()
    assert out["new"] == 1 and len(out["answered"]) == 1
    a = out["answered"][0]
    assert a["score"] == 100 and a["tag"] == "replay:erc20_transfer" and a["tx"] is None
    rh, score, uri, resp_hash, tag = decode_calldata(a["calldata"])
    assert "0x" + rh.hex() == h and score == 100 and uri == a["responseURI"]
    bundle = json.loads((tmp_path / "ev" / f"{h}.json").read_bytes())
    assert "0x" + resp_hash.hex() == evidence.response_hash(bundle)
    assert bundle["verdict"]["observed"]["blockNumber"] == 940


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


def test_cli_job_prints_request_calldata(tmp_path, capsys, monkeypatch):
    from replay8004.cli import main
    monkeypatch.chdir(tmp_path)
    main(["job", "erc20-transfer", "--agent-id", "42", "--validator", VALIDATOR, "--tx", TX, "--token", USDC,
          "--to", PAYEE, "--min-amount", "10000", "--out", "job.json"])
    out = json.loads(capsys.readouterr().out)
    raw = (tmp_path / "job.json").read_bytes()
    assert out["requestHash"] == jobmod.request_hash(raw) and out["to"] == NET.validation
    assert out["calldata"].startswith("0x")
