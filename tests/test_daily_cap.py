"""Gas guard: anyone can name this validator, and every answer costs gas, so answers are capped per UTC day."""
import json

from replay8004 import job as jobmod
from replay8004.evidence import LocalSink
from replay8004.store import FileStore
from replay8004.worker import Worker
from tests.conftest import PAYEE, PAYER, USDC, VALIDATOR, FakeRpc, FakeSender
from tests.test_worker import CLAIM, NET


class Clock:
    def __init__(self, day="2026-11-27"):
        self.day = day

    def __call__(self):
        return f"{self.day}T12:00:00+00:00"


def worker(tmp_path, rpc, clock, per_day=20, per_agent=5, dry=False, mode="ok"):
    return Worker(network=NET, rpc=rpc, validator=VALIDATOR, sender=None if dry else FakeSender(rpc, mode=mode),
                  store=FileStore(tmp_path / "s.json", start_block=900),
                  sink=LocalSink(tmp_path / "ev", "https://ev.example"), clock=clock,
                  max_answers_per_day=per_day, max_answers_per_agent_per_day=per_agent)


def requests(rpc, n, agent=42, start=0, block=950):
    hashes = []
    for i in range(start, start + n):
        tx = "0x" + f"{i:02x}" * 32
        rpc.add_transfer(tx, USDC, PAYER, PAYEE, 10_000, block=900)
        raw = jobmod.make_job(agent, NET.chain_id, "erc20_transfer", dict(CLAIM, txHash=tx))
        h = jobmod.request_hash(raw)
        rpc.add_request(NET.validation, VALIDATOR, agent, jobmod.data_uri(raw), h, block + i)
        hashes.append(h)
    return hashes


def state(tmp_path):
    return json.loads((tmp_path / "s.json").read_text())


def test_one_agent_cannot_use_more_than_its_daily_share(tmp_path):
    rpc, clock = FakeRpc(head=1_000), Clock()
    hs = requests(rpc, 7)
    w = worker(tmp_path, rpc, clock, per_agent=5)
    out = w.poll_once()
    assert [a["requestHash"] for a in out["answered"]] == hs[:5]   # oldest first
    assert out["capped"] == 2 and out["answeredToday"] == 5 and len(w.sender.sent) == 5
    assert w.poll_once()["answered"] == []                           # same day: still waiting, never scored 0
    assert set(hs[5:]) <= set(state(tmp_path)["pending"])
    clock.day = "2026-11-28"                                         # next UTC day
    assert [a["requestHash"] for a in w.poll_once()["answered"]] == hs[5:]


def test_global_cap_across_agents(tmp_path):
    rpc, clock = FakeRpc(head=1_000), Clock()
    requests(rpc, 2, agent=1, start=0)
    requests(rpc, 2, agent=2, start=10)
    out = worker(tmp_path, rpc, clock, per_day=3, per_agent=5).poll_once()
    assert len(out["answered"]) == 3 and out["capped"] == 1
    assert state(tmp_path)["daily"] == {"date": "2026-11-27", "total": 3, "agents": {"1": 2, "2": 1}}


def test_zero_pauses_answering(tmp_path):
    rpc, clock = FakeRpc(head=1_000), Clock()
    requests(rpc, 2)
    out = worker(tmp_path, rpc, clock, per_day=0).poll_once()
    assert out["answered"] == [] and out["capped"] == 2 and out["pending"] == 2


def test_capped_requests_cost_no_rpc_calls(tmp_path):
    rpc, clock = FakeRpc(head=1_000), Clock()
    requests(rpc, 3)
    w = worker(tmp_path, rpc, clock, per_day=0)
    calls = []
    orig = rpc.eth_call
    rpc.eth_call = lambda *a: calls.append(a) or orig(*a)
    w.poll_once()
    assert calls == []   # no status check, no fetch, no checker for requests that must wait


def test_dry_run_counts_without_persisting(tmp_path):
    rpc, clock = FakeRpc(head=1_000), Clock()
    requests(rpc, 3)
    out = worker(tmp_path, rpc, clock, per_agent=2, dry=True).poll_once()
    assert len(out["answered"]) == 2 and out["capped"] == 1      # the preview respects the cap
    assert state(tmp_path)["daily"]["total"] == 0                # but a dry run spends nothing
    live = worker(tmp_path, rpc, clock, per_agent=2).poll_once()
    assert len(live["answered"]) == 2


def test_resending_a_reverted_answer_counts_and_waits_at_the_cap(tmp_path):
    rpc, clock = FakeRpc(head=1_000), Clock()
    (h,) = requests(rpc, 1)
    w = worker(tmp_path, rpc, clock, per_day=1, mode="revert")
    w.poll_once()                                                    # answer 1 of 1 today; it reverts
    rpc.head += 5
    w.sender.mode = "ok"
    w.poll_once()
    assert state(tmp_path)["inflight"][h]["attempts"] == 1 and len(w.sender.sent) == 1   # waits: cap used
    clock.day = "2026-11-28"
    w.poll_once()                                                    # new day: re-sent with the same calldata
    rpc.head += 5
    assert w.poll_once()["confirmed"][0]["requestHash"] == h and len(w.sender.sent) == 2
    assert state(tmp_path)["daily"]["total"] == 1


def test_template_and_lambda_expose_the_caps():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    t = (root / "infra" / "template.yaml").read_text(encoding="utf-8")
    assert "MAX_ANSWERS_PER_DAY: !Ref MaxAnswersPerDay" in t and "MAX_ANSWERS_PER_AGENT_PER_DAY: !Ref MaxAnswersPerAgentPerDay" in t
    src = (root / "replay8004" / "lambda_handler.py").read_text(encoding="utf-8")
    assert 'max_answers_per_day=int(os.environ.get("MAX_ANSWERS_PER_DAY", "20"))' in src
