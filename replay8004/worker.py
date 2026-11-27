"""Poll the ValidationRegistry for requests naming this validator, re-check them, answer on-chain.

  poll_once():
    1. reconcile answers already signed: confirmed on-chain -> done; not mined yet -> rebroadcast the SAME tx
    2. read ValidationRequest logs (topic1 = our address) from the last scanned block to head - reorg_buffer
    3. for each new request (and each still-pending one): skip it if the registry already holds an answer,
       else fetch requestURI, check keccak == requestHash, parse the job, run the checker
    4. undecidable yet (e.g. too few confirmations) -> stays pending, retried next poll (max_pending_polls)
    5. otherwise write a hash-chained evidence bundle, sign validationResponse, persist the signed tx, broadcast
  An invalid job (bad hash, wrong agent/chain, malformed claim) is answered with score 0 and the reason,
  so the requester sees why. A job that cannot be downloaded, or a receipt the RPC no longer has, is unknown
  rather than false: it stays pending and is never scored.

  Never answered twice: the signed tx is saved before it is broadcast and only that tx (one nonce, so it can be
  mined once) is ever rebroadcast. A request is done only when the registry holds our responseHash at
  head - reorg_buffer. It is re-signed, with the same calldata, only if at that same block the nonce is used up
  and the registry still has no answer (our tx reverted, or the wallet was used elsewhere).

  Dry run (no sender): reports the answers it *would* send (calldata included) but writes no evidence and
  leaves every request pending with the evidence chain head unchanged. Only scan progress is saved, so a
  later live run on the same state answers everything the dry run saw.
"""
from __future__ import annotations

import copy
import datetime as dt
import logging

from . import __version__, evidence, job as jobmod, registry
from .checkers import CHECKERS, TAGS, Verdict

log = logging.getLogger("replay8004")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


class Worker:
    def __init__(self, *, network, rpc, store, sink, validator: str, sender=None, fetch=jobmod.fetch,
                 reorg_buffer: int = 3, chunk: int = 5_000, max_pending_polls: int = 120, max_attempts: int = 3,
                 max_answers_per_day: int = 20, max_answers_per_agent_per_day: int = 5, clock=_now):
        self.net, self.rpc, self.store, self.sink = network, rpc, store, sink
        self.validator = validator.lower()
        self.sender, self.fetch, self.clock = sender, fetch, clock
        self.reorg_buffer, self.chunk, self.max_pending_polls = reorg_buffer, chunk, max_pending_polls
        self.max_attempts = max_attempts
        # gas guard: anyone can name this validator, and every answer costs gas. Over the cap, requests wait for a
        # later UTC day (oldest first) instead of being answered; 0 pauses answering entirely.
        self.max_per_day, self.max_per_agent = max_answers_per_day, max_answers_per_agent_per_day

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
        except (jobmod.FetchError, OSError):
            raise  # transient: keep pending, never score it
        except Exception as e:
            return Verdict(0, [f"invalid job: {e}"]), None, None
        kind = job["kind"]
        try:
            v = CHECKERS[kind](job["claim"], self.rpc, Verdict)
        except (KeyError, ValueError, TypeError) as e:
            return Verdict(0, [f"invalid claim: {e}"]), job, kind
        return v, job, kind  # v is None -> not decidable yet; RPC errors propagate -> retry later

    @property
    def dry_run(self) -> bool:
        return self.sender is None

    def _answer(self, st: dict, chain: dict, req: dict, v: Verdict, job, kind) -> tuple[dict, dict | None]:
        bundle = evidence.build(seq=chain["seq"] + 1, prev=chain["head"], validator=self.validator,
                                network=self.net.name, chain_id=self.net.chain_id, agent_id=req["agentId"],
                                request_hash=req["requestHash"], request_uri=req["requestURI"], job=job, kind=kind,
                                verdict=v, checked_at=self.clock(), version=__version__)
        rh = evidence.response_hash(bundle)
        # live: the evidence bundle is written BEFORE the answer is sent; dry run: nothing is written
        uri = self.sink.url_for(bundle) if self.dry_run else self.sink.put(bundle)
        tag = TAGS.get(kind, "replay:invalid")
        data = registry.encode_response(req["requestHash"], v.score, uri, rh, tag)
        signed = None if self.dry_run else self.sender.sign(self.net.validation, data, self._min_nonce(st))
        chain["seq"], chain["head"] = bundle["seq"], rh
        res = {"requestHash": req["requestHash"], "agentId": req["agentId"], "score": v.score, "tag": tag,
               "responseURI": uri, "responseHash": rh, "tx": signed["tx"] if signed else None, "calldata": data,
               "dryRun": self.dry_run}
        return res, signed

    # -- sending ----------------------------------------------------------------
    @staticmethod
    def _min_nonce(st: dict) -> int:
        return max((f["nonce"] + 1 for f in st["inflight"].values()), default=0)

    def _on_chain(self, request_hash: str, block: int | str = "latest") -> dict | None:
        """The registry's answer for this request at `block`, or None if it has not been answered."""
        s = registry.decode_status(self.rpc.eth_call(self.net.validation, registry.encode_status(request_hash), block))
        return s if int(s["responseHash"], 16) else None  # every replay8004 answer has a non-zero hash

    def _broadcast(self, request_hash: str, raw: str) -> None:
        try:
            self.sender.broadcast(raw)
        except Exception as e:  # lost reply, "already known", ...: the next poll reads the chain to find out
            log.warning("broadcast of %s: %s", request_hash, e)

    def _reconcile(self, st: dict) -> list[dict]:
        confirmed: list[dict] = []
        if not st["inflight"]:
            return confirmed
        try:  # nonce and answers are read at ONE block: RPC backends are at different heads
            safe = self.rpc.block_number() - self.reorg_buffer
            used = self.rpc.nonce_at(self.validator, safe)
        except Exception as e:
            log.warning("cannot reconcile: %s", e)
            return confirmed
        for h, f in sorted(st["inflight"].items(), key=lambda kv: kv[1]["nonce"]):
            try:
                s = self._on_chain(h, safe)
            except Exception as e:
                log.warning("cannot read status of %s: %s", h, e)
                continue
            if s:
                if s["responseHash"] != f["responseHash"]:
                    log.error("%s holds a different answer on-chain; leaving it untouched", h)
                st["done"][h] = {"score": s["response"], "tx": f["tx"], "responseHash": s["responseHash"]}
                del st["inflight"][h]
                self.store.save(st)
                confirmed.append({"requestHash": h, **st["done"][h]})
            elif used <= f["nonce"]:
                self._broadcast(h, f["raw"])  # not mined yet: same tx again, harmless if already known
            elif f["attempts"] >= self.max_attempts:
                log.error("%s: gave up after %s attempts", h, f["attempts"])
                st["failed"][h] = st["inflight"].pop(h)
                self.store.save(st)
            elif self._capped(self._today(st), None):
                log.warning("%s: daily answer cap reached; re-sending tomorrow", h)
            else:
                try:
                    signed = self.sender.sign(self.net.validation, f["calldata"], self._min_nonce(st))
                except Exception as e:
                    log.warning("cannot re-sign %s: %s", h, e)
                    continue
                f.update(signed, attempts=f["attempts"] + 1)
                self._count(self._today(st), None)
                self.store.save(st)
                self._broadcast(h, f["raw"])
        return confirmed

    def _today(self, st: dict) -> dict:
        day = self.clock()[:10]
        if st.get("daily", {}).get("date") != day:
            st["daily"] = {"date": day, "total": 0, "agents": {}}
        return st["daily"]

    def _capped(self, daily: dict, agent) -> bool:
        return daily["total"] >= self.max_per_day or daily["agents"].get(str(agent), 0) >= self.max_per_agent

    @staticmethod
    def _count(daily: dict, agent) -> None:
        daily["total"] += 1
        if agent is not None:
            daily["agents"][str(agent)] = daily["agents"].get(str(agent), 0) + 1

    def poll_once(self) -> dict:
        st = self.store.load()
        for k in ("inflight", "failed"):  # state files written before these fields existed
            st.setdefault(k, {})
        confirmed = [] if self.dry_run else self._reconcile(st)
        new = self._scan(st)
        for q in new:
            if not any(q["requestHash"] in st[k] for k in ("done", "pending", "inflight", "failed")):
                st["pending"][q["requestHash"]] = dict(q, polls=0)
        chain = {"seq": st["seq"], "head": st["head"]}  # a dry run advances only this local copy
        daily = copy.deepcopy(self._today(st)) if self.dry_run else self._today(st)
        answered, still, capped = [], 0, 0
        # deterministic order (request block, then hash): the evidence chain then doesn't depend on how the
        # state file happened to order its keys, and a dry run previews exactly what the live run sends
        for h, req in sorted(st["pending"].items(), key=lambda kv: (kv[1].get("blockNumber", 0), kv[0])):
            if self._capped(daily, req["agentId"]):  # checked first: no RPC is spent on requests that must wait
                still += 1
                capped += 1
                continue
            try:
                prior = self._on_chain(h)  # e.g. the local state was lost after answering
                if not prior:
                    v, job, kind = self.decide(req)
            except Exception as e:  # RPC or download trouble: keep pending
                log.warning("deferring %s: %s", h, e)
                still += 1
                continue
            if prior:
                log.warning("%s is already answered on-chain; not answering again", h)
                if not self.dry_run:
                    st["done"][h] = {"score": prior["response"], "tx": None, "responseHash": prior["responseHash"]}
                    del st["pending"][h]
                continue
            polls = req.get("polls", 0) + 1
            if not self.dry_run:
                req["polls"] = polls
            if v is None and polls < self.max_pending_polls:
                still += 1
                continue
            if v is None:
                v = Verdict(0, [f"still undecidable after {polls} polls"])
            try:
                res, signed = self._answer(st, chain, req, v, job, kind)
            except Exception as e:
                log.error("could not answer %s: %s", h, e)
                still += 1
                continue
            answered.append(res)
            self._count(daily, req["agentId"])
            if self.dry_run:
                still += 1  # stays pending for the live run
                continue
            st["seq"], st["head"] = chain["seq"], chain["head"]
            st["inflight"][h] = dict(signed, calldata=res["calldata"], responseHash=res["responseHash"],
                                     score=res["score"], attempts=1, agentId=req["agentId"])
            del st["pending"][h]
            self.store.save(st)  # persisted BEFORE broadcasting: a crash or lost reply never double-answers
            self._broadcast(h, signed["raw"])
        self.store.save(st)  # dry run: only scan progress and newly seen (still pending) requests change
        return {"scanned_to": st["last_block"], "new": len(new), "answered": answered, "confirmed": confirmed,
                "pending": still, "capped": capped, "inflight": len(st["inflight"]), "failed": len(st["failed"]),
                "answeredToday": daily["total"], "dryRun": self.dry_run}
