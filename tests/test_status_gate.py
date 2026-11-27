import json

import pytest
from eth_abi import encode

from replay8004 import gate, networks, registry, status
from replay8004.cli import main
from tests.conftest import PAYEE, PAYER, USDC, VALIDATOR, OTHER_VALIDATOR
from tests.test_worker import CLAIM, TX, request, setup

NET = networks.CELO_SEPOLIA


def _answer_three(tmp_path):
    rpc, w = setup(tmp_path, head=1_000)
    rpc.add_transfer(TX, USDC, PAYER, PAYEE, 10_000, block=940)
    request(rpc, CLAIM, agent=42, block=950)
    request(rpc, dict(CLAIM, minAmount="20000"), agent=42, block=951)       # paid half: score 50
    rpc.add_request(NET.validation, VALIDATOR, 7, "data:application/json,{}", "0x" + "ee" * 32, 952)  # bad job
    w.poll_once()
    return rpc, w


def test_bundles_carry_request_block(tmp_path):
    _answer_three(tmp_path)
    b = [json.loads(p.read_bytes()) for p in (tmp_path / "ev").glob("0x*.json")]
    assert {x["request"]["block"] for x in b} == {950, 951, 952}
    assert all(x["request"]["checkedAtBlock"] == 1_000 for x in b)


def test_status_summary_and_html(tmp_path):
    _answer_three(tmp_path)
    st = status.build_site(tmp_path / "ev", tmp_path / "site", now="2026-11-22T00:00:00+00:00")
    assert st["answered"] == 3 and st["agents"] == 2 and st["invalid"] == 1
    assert st["chain"]["intact"] and st["byTag"]["replay:erc20_transfer"]["count"] == 2
    assert st["byTag"]["replay:invalid"] == {"count": 1, "avg": 0, "passed": 0}
    assert st["passRate"] == round(1 / 3, 4)
    assert st["claims"] == {"held": 1, "partlyTrue": 1, "false": 1}     # counts claims, not validator mistakes
    assert st["medianSecondsToDecide"] == 49          # 1000 - 951
    page = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert "chain" in page and "intact" in page and "<script" not in page
    assert "1 of 3</b>claims held" in page and "1 partly true · 1 false" in page and "passed" not in page
    assert json.loads((tmp_path / "site" / "status.json").read_text())["answered"] == 3


def test_status_flags_broken_chain(tmp_path):
    _answer_three(tmp_path)
    p = sorted((tmp_path / "ev").glob("0x*.json"))[0]
    b = json.loads(p.read_bytes()); b["verdict"]["score"] = 100
    p.write_text(json.dumps(b))
    assert not status.build_site(tmp_path / "ev", tmp_path / "site")["chain"]["intact"]


def test_status_escapes_untrusted_fields(tmp_path):
    st = status.summarize([])
    st["recent"] = [{"seq": 1, "agentId": 1, "tag": "<img src=x onerror=alert(1)>", "score": 0,
                     "requestHash": "0x\"><script>", "checkedAt": "<b>", "responseHash": "0x"}]
    html = status.render_html(st)
    assert "<img src=x" not in html and "<script>" not in html


def test_status_empty(tmp_path):
    (tmp_path / "ev").mkdir()
    st = status.build_site(tmp_path / "ev", tmp_path / "site")
    assert st["answered"] == 0 and st["passRate"] is None and st["chain"]["intact"]


class SummaryRpc:
    def __init__(self, count=3, avg=93, status_tuple=None):
        self.count, self.avg, self.st, self.calls = count, avg, status_tuple, []

    def eth_call(self, to, data, block="latest"):
        self.calls.append(data)
        if data.startswith(registry.encode_summary(0, [], "")[:10]):
            return "0x" + encode(["uint64", "uint8"], [self.count, self.avg]).hex()
        return "0x" + encode(["address", "uint256", "uint8", "bytes32", "string", "uint256"], list(self.st)).hex()


def test_gate_passes():
    assert gate.passes(SummaryRpc(3, 93), NET, 42, VALIDATOR, "replay:erc20_transfer", 3, 90)
    assert not gate.passes(SummaryRpc(2, 100), NET, 42, VALIDATOR, min_count=3)
    assert not gate.passes(SummaryRpc(0, 0), NET, 42, VALIDATOR, min_count=0, min_avg=0)  # no history never passes
    assert not gate.passes(SummaryRpc(5, 89), NET, 42, VALIDATOR, min_avg=90)


@pytest.mark.parametrize("st,args,expect", [
    ((VALIDATOR, 42, 100, b"\x11" * 32, "replay:x402_settlement", 1000), {}, (True, 0)),
    ((OTHER_VALIDATOR, 42, 100, b"\x11" * 32, "t", 1000), {}, (False, gate.WRONG_VALIDATOR)),
    ((VALIDATOR, 41, 100, b"\x11" * 32, "t", 1000), {}, (False, gate.WRONG_AGENT)),
    ((VALIDATOR, 42, 0, b"\x00" * 32, "", 1000), {}, (False, gate.NO_RESPONSE)),
    ((VALIDATOR, 42, 100, b"\x11" * 32, "replay:erc20_balance", 1000), {"tag": "replay:x402_settlement"}, (False, gate.WRONG_TAG)),
    ((VALIDATOR, 42, 95, b"\x11" * 32, "t", 1000), {}, (False, gate.LOW_SCORE)),
    ((VALIDATOR, 42, 100, b"\x11" * 32, "t", 1000), {"max_age": 60}, (False, gate.STALE)),
])
def test_gate_claim_status(st, args, expect):
    ok, reason, _ = gate.claim_status(SummaryRpc(status_tuple=st), NET, "0x" + "ab" * 32, 42, VALIDATOR, now=2000, **args)
    assert (ok, reason) == expect


def test_gate_selector_matches_contract():
    assert gate.encode_status("0x" + "00" * 32)[:10] == "0x" + registry._sel("getValidationStatus(bytes32)").hex()


def test_cli_status(tmp_path, capsys):
    _answer_three(tmp_path)
    with pytest.raises(SystemExit) as e:
        main(["status", "--evidence", str(tmp_path / "ev"), "--out", str(tmp_path / "site")])
    assert e.value.code == 0 and json.loads(capsys.readouterr().out)["answered"] == 3


def test_status_note_is_plain_text(tmp_path):
    _answer_three(tmp_path)
    status.build_site(tmp_path / "ev", tmp_path / "site", note="Tests by <b>us</b> & friends")
    page = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert "Tests by &lt;b&gt;us&lt;/b&gt; &amp; friends" in page and "<b>us</b>" not in page
