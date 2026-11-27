"""Public status page built only from published evidence bundles.

Anyone can rebuild it: point `replay8004 status` at the evidence folder (or a copy of the public S3
prefix). Nothing here needs the validator key or an RPC. Output: status.json + a static index.html
that can be served from the same Object Lock bucket (`status/` prefix) or any static host.
"""
from __future__ import annotations

import html
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from . import evidence

PASS = 90          # a score at or above this counts as "held": the agent's claim checked out
BLOCK_SECONDS = 1  # Celo L2 block time used to turn block counts into seconds (estimate)


def summarize(bundles: list[dict], *, validator: str | None = None, now: str | None = None) -> dict:
    ok, chain_msg = evidence.verify_chain(bundles) if bundles else (True, "0 bundles")
    by_tag: dict[str, list[int]] = defaultdict(list)
    agents, invalid, lat = set(), 0, []
    for b in bundles:
        tag = f"replay:{b['checker']}" if b.get("checker") else "replay:invalid"
        s = int(b["verdict"]["score"])
        by_tag[tag].append(s)
        agents.add(int(b["agentId"]))
        if not b.get("checker") or any(str(f).startswith(("invalid job", "invalid claim")) for f in b["verdict"]["findings"]):
            invalid += 1
        r = b.get("request") or {}
        if r.get("block") is not None and r.get("checkedAtBlock") is not None:
            lat.append(max(0, r["checkedAtBlock"] - r["block"]) * BLOCK_SECONDS)
    scores = [s for v in by_tag.values() for s in v]
    last = max(bundles, key=lambda b: b["seq"]) if bundles else None
    return {
        "schema": "replay8004/status@1",
        "validator": validator or (last["validator"] if last else None),
        "network": last["network"] if last else None,
        "generatedAt": now,
        "chain": {"intact": ok, "detail": chain_msg, "head": evidence.response_hash(last) if last else evidence.GENESIS},
        "answered": len(bundles),
        "agents": len(agents),
        "invalid": invalid,
        "passRate": round(sum(s >= PASS for s in scores) / len(scores), 4) if scores else None,  # share of claims that held
        # how the agents' claims turned out. This is not the validator's error rate: a false claim scored 0 is a correct answer.
        "claims": {"held": sum(s >= PASS for s in scores), "partlyTrue": sum(0 < s < PASS for s in scores),
                   "false": sum(s == 0 for s in scores)},
        "avgScore": round(statistics.fmean(scores), 2) if scores else None,
        "medianSecondsToDecide": statistics.median(lat) if lat else None,
        "byTag": {t: {"count": len(v), "avg": round(statistics.fmean(v), 2), "passed": sum(s >= PASS for s in v)}
                  for t, v in sorted(by_tag.items())},
        "scoreBuckets": dict(sorted(Counter(_bucket(s) for s in scores).items())),
        "recent": [{"seq": b["seq"], "agentId": b["agentId"], "tag": f"replay:{b['checker']}" if b.get("checker") else "replay:invalid",
                    "score": b["verdict"]["score"], "requestHash": b["requestHash"], "checkedAt": b["checkedAt"],
                    "responseHash": evidence.response_hash(b)}
                   for b in sorted(bundles, key=lambda x: -x["seq"])[:25]],
    }


def _bucket(s: int) -> str:
    return "100" if s == 100 else "90-99" if s >= 90 else "50-89" if s >= 50 else "1-49" if s >= 1 else "0"


def render_html(st: dict, evidence_base_url: str = "", note: str = "") -> str:
    e = html.escape
    def fmt(v, suf=""):
        return "—" if v is None else f"{v}{suf}"
    rows = "".join(
        f"<tr><td class=n>{r['seq']}</td><td class=n>{r['agentId']}</td><td><code>{e(r['tag'])}</code></td>"
        f"<td class=n>{r['score']}</td><td>{e(r['checkedAt'])}</td><td><a href=\"{e(evidence_base_url.rstrip('/'))}/{e(r['requestHash'])}.json\">"
        f"<code>{e(r['requestHash'][:14])}…</code></a></td></tr>" for r in st["recent"]) or "<tr><td colspan=6>No validations yet.</td></tr>"
    tags = "".join(f"<tr><td><code>{e(t)}</code></td><td class=n>{v['count']}</td><td class=n>{v['avg']}</td><td class=n>{v['passed']}</td></tr>"
                   for t, v in st["byTag"].items()) or "<tr><td colspan=4>—</td></tr>"
    chain = "intact" if st["chain"]["intact"] else "BROKEN"
    c = st.get("claims") or {"held": 0, "partlyTrue": 0, "false": 0}
    held = f"{c['held']} of {st['answered']}" if st["answered"] else "—"
    note_html = f"<p class=note>{e(note)}</p>" if note else ""
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>replay8004 status</title><style>
:root{{--bg:#f6f7f5;--fg:#18201c;--muted:#5d6a63;--line:#d9dfdb;--card:#fff;--ok:#1d7a4a;--bad:#a52a2a}}
@media (prefers-color-scheme:dark){{:root{{--bg:#111613;--fg:#e5ece8;--muted:#9aa9a1;--line:#2a3530;--card:#18201c;--ok:#7fd3a3;--bad:#f09a9a}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}}main{{max-width:900px;margin:0 auto;padding:28px 16px;display:grid;gap:22px}}
h1{{margin:0;font-size:1.6rem}}.muted{{color:var(--muted)}}.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}}
.k{{background:var(--card);border:1px solid var(--line);padding:12px}}.k b{{display:block;font-size:1.4rem;font-variant-numeric:tabular-nums}}
.tbl{{overflow-x:auto;background:var(--card);border:1px solid var(--line)}}table{{border-collapse:collapse;width:100%;font-size:.9rem}}
th,td{{padding:7px 10px;border-bottom:1px solid var(--line);text-align:left}}th{{color:var(--muted);font-weight:500}}.n{{text-align:right;font-variant-numeric:tabular-nums}}
.k small{{display:block;color:var(--muted);font-size:.85rem;margin-top:2px}}.note{{border-left:3px solid var(--ok);padding:4px 0 4px 12px;margin:10px 0 0}}
.ok{{color:var(--ok)}}.bad{{color:var(--bad)}}code{{font-size:.85em}}</style></head><body><main>
<div><h1>replay8004 status</h1><p class=muted>Validator <code>{e(str(st['validator']))}</code> on {e(str(st['network']))} · generated {e(str(st['generatedAt']))} · rebuilt from public evidence bundles only</p>{note_html}</div>
<div class=kpis><div class=k><b>{st['answered']}</b>validations answered</div><div class=k><b>{st['agents']}</b>distinct agents</div>
<div class=k><b>{held}</b>claims held (score ≥ {PASS})<small>{c['partlyTrue']} partly true · {c['false']} false</small></div><div class=k><b>{fmt(st['medianSecondsToDecide'], ' s')}</b>median request → decision</div>
<div class=k><b>{st['invalid']}</b>invalid jobs (answered 0 with a reason)</div><div class=k><b class="{'ok' if st['chain']['intact'] else 'bad'}">{chain}</b>evidence chain · {e(st['chain']['detail'])}</div></div>
<section><h2>By claim type</h2><div class=tbl><table><thead><tr><th>tag</th><th class=n>answered</th><th class=n>avg score</th><th class=n>held</th></tr></thead><tbody>{tags}</tbody></table></div></section>
<section><h2>Recent answers</h2><div class=tbl><table><thead><tr><th class=n>seq</th><th class=n>agent</th><th>tag</th><th class=n>score</th><th>checked</th><th>evidence</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<p class=muted>Chain head <code>{e(st['chain']['head'])}</code>. Verify yourself: <code>replay8004 verify-evidence &lt;folder&gt;</code>. Time to decide counts blocks between the request and the head the validator had seen, at ≈{BLOCK_SECONDS} s per block; it includes the confirmation wait.</p>
</main></body></html>"""


def build_site(evidence_dir: str | Path, out_dir: str | Path, *, validator=None, now=None, evidence_base_url="",
               note: str = "") -> dict:
    bundles = [json.loads(p.read_bytes()) for p in Path(evidence_dir).glob("0x*.json")]
    st = summarize(bundles, validator=validator, now=now)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "status.json").write_text(json.dumps(st, indent=2), encoding="utf-8")
    (out / "index.html").write_text(render_html(st, evidence_base_url, note), encoding="utf-8")
    return st
