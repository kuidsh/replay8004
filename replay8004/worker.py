"""Poll the ValidationRegistry for requests naming this validator, re-check them, answer on-chain.

  poll_once():
    1. read ValidationRequest logs (topic1 = our address) from the last scanned block to head - reorg_buffer
    2. for each new request (and each still-pending one): fetch requestURI, check keccak == requestHash,
       parse the job, run the checker
    3. undecidable yet (e.g. too few confirmations) -> stays pending, retried next poll (max_pending_age)
    4. otherwise write a hash-chained evidence bundle, then call validationResponse(score, responseURI, responseHash, tag)
  An invalid job (bad hash, wrong agent/chain, malformed claim) is answered with score 0 and the reason,
  so the requester sees why. Submission failures leave the request pending; nothing is answered twice.
"""
from __future__ import annotations

import datetime as dt
import logging

from . import __version__, evidence, job as jobmod, registry
from .checkers import CHECKERS, TAGS, Verdict

log = logging.getLogger("replay8004")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


class Worker:
    def __init__(self, *, network, rpc, store, sink, validator: str, sender=None, fetch=jobmod.fetch,
                 reorg_buffer: int = 3, chunk: int = 5_000, max_pending_polls: int = 120, clock=_now):
        self.net, self.rpc, self.store, self.sink = network, rpc, store, sink
        self.validator = validator.lower()
        self.sender, self.fetch, self.clock = sender, fetch, clock
        self.reorg_buffer, self.chunk, self.max_pending_polls = reorg_buffer, chunk, max_pending_polls

    # -- scanning -------------------------------------------------------------
    def _scan(self, st: dict) -> list[dict]:
        head = self.rpc.block_number() - self.reorg_buffer
        found, start = [], st["last_block"] + 1
        while start <= head:
            end = min(head, start + self.chunk - 1)
            logs = self.rpc.logs(self.net.validation, [registry.TOPIC_REQUEST, registry.topic_address(self.validator)],
                                 start, end)
            found += [registry.decode_request_log(lg) for lg in logs]
            st["last_block"] = end
            start = end + 1
        return found

    # -- deciding -------------------------------------------------------------
    def decide(self, req: dict) -> tuple[Verdict | None, dict | None, str | None]:
        try:
            raw = self.fetch(req["requestURI"])
            job = jobmod.parse(raw, req["requestHash"], req["agentId"], self.net.chain_id)
        except Exception as e:
            return Verdict(0, [f"invalid job: {e}"]), None, None
        kind = job["kind"]
        try:
            v = CHECKERS[kind](job["claim"], self.rpc, Verdict)
        except (KeyError, ValueError, TypeError) as e:
            return Verdict(0, [f"invalid claim: {e}"]), job, kind
        return v, job, kind  # v is None -> not decidable yet; RPC errors propagate -> retry later

    def _answer(self, st: dict, req: dict, v: Verdict, job, kind) -> dict:
        bundle = evidence.build(seq=st["seq"] + 1, prev=st["head"], validator=self.validator, network=self.net.name,
                                chain_id=self.net.chain_id, agent_id=req["agentId"], request_hash=req["requestHash"],
                                request_uri=req["requestURI"], job=job, kind=kind, verdict=v,
                                checked_at=self.clock(), version=__version__)
        rh = evidence.response_hash(bundle)
        uri = self.sink.put(bundle)
        tag = TAGS.get(kind, "replay:invalid")
        data = registry.encode_response(req["requestHash"], v.score, uri, rh, tag)
        tx = self.sender.send(self.net.validation, data) if self.sender else None  # None = dry run
        st["seq"], st["head"] = bundle["seq"], rh
        return {"requestHash": req["requestHash"], "agentId": req["agentId"], "score": v.score, "tag": tag,
                "responseURI": uri, "responseHash": rh, "tx": tx, "calldata": None if self.sender else data}

    def poll_once(self) -> dict:
        st = self.store.load()
        new = self._scan(st)
        for r in new:
            if r["requestHash"] not in st["done"] and r["requestHash"] not in st["pending"]:
                st["pending"][r["requestHash"]] = dict(r, polls=0)
        answered, still = [], 0
        for h, req in list(st["pending"].items()):
            try:
                v, job, kind = self.decide(req)
            except Exception as e:  # RPC trouble: keep pending
                log.warning("deferring %s: %s", h, e)
                still += 1
                continue
            req["polls"] = req.get("polls", 0) + 1
            if v is None and req["polls"] < self.max_pending_polls:
                still += 1
                continue
            if v is None:
                v = Verdict(0, [f"still undecidable after {req['polls']} polls"])
            try:
                res = self._answer(st, req, v, job, kind)
            except Exception as e:
                log.error("could not answer %s: %s", h, e)
                still += 1
                continue
            st["done"][h] = {"score": res["score"], "tx": res["tx"], "responseHash": res["responseHash"]}
            del st["pending"][h]
            answered.append(res)
            self.store.save(st)  # persist after each answer so a crash never double-answers
        self.store.save(st)
        return {"scanned_to": st["last_block"], "new": len(new), "answered": answered, "pending": still}
