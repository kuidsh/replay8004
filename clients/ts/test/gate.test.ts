import { test } from "node:test";
import assert from "node:assert/strict";
import { decideClaim, REASON, type ValidationStatus } from "../src/index.js";

const V = "0x3333333333333333333333333333333333333333" as const;
const base: ValidationStatus = { validatorAddress: V, agentId: 42n, response: 100, responseHash: `0x${"11".repeat(32)}`,
  tag: "replay:x402_settlement", lastUpdate: 1000n };
const p = { validator: V, agentId: 42n, now: 2000n };

test("decideClaim matches ReplayGate.claimStatus reason codes", () => {
  assert.deepEqual(decideClaim(base, p), { ok: true, reason: REASON.OK });
  assert.equal(decideClaim({ ...base, validatorAddress: "0x4444444444444444444444444444444444444444" }, p).reason, REASON.WRONG_VALIDATOR);
  assert.equal(decideClaim({ ...base, agentId: 41n }, p).reason, REASON.WRONG_AGENT);
  assert.equal(decideClaim({ ...base, responseHash: `0x${"00".repeat(32)}` }, p).reason, REASON.NO_RESPONSE);
  assert.equal(decideClaim(base, { ...p, tag: "replay:erc20_balance" }).reason, REASON.WRONG_TAG);
  assert.equal(decideClaim({ ...base, response: 95 }, p).reason, REASON.LOW_SCORE);
  assert.equal(decideClaim(base, { ...p, maxAge: 60n }).reason, REASON.STALE);
  assert.equal(decideClaim(base, { ...p, maxAge: 0n }).ok, true);
});
