import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { canonical, makeJob, requestCalldata, summaryCalldata, x402Claim, tagFor, type Kind } from "../src/index.js";

const vectors = JSON.parse(readFileSync(new URL("../../../../tests/vectors/client.json", import.meta.url), "utf8"));

for (const v of vectors) {
  test(`job bytes, hash and calldata match Python: ${v.input.kind}`, () => {
    const j = makeJob(v.input.agentId, v.input.chainId, v.input.kind as Kind, v.input.claim, v.input.note);
    assert.equal(j.text, v.jobUtf8);
    assert.equal(j.requestHash, v.requestHash);
    assert.equal(j.dataUri, v.dataUri);
    assert.equal(requestCalldata(v.validator, v.input.agentId, j.dataUri, j.requestHash), v.requestCalldata);
    assert.equal(summaryCalldata(v.input.agentId, [v.validator], tagFor(v.input.kind)), v.summaryCalldata);
  });
}

test("canonical sorts keys and drops whitespace", () => {
  assert.equal(canonical({ b: 1, a: [true, null, "x"] }), '{"a":[true,null,"x"],"b":1}');
  assert.throws(() => canonical({ a: 1.5 }));
});

test("x402Claim accepts a base64 PAYMENT-RESPONSE value", () => {
  const st = { success: true, transaction: "0x" + "bb".repeat(32), network: "eip155:42220" };
  const c = x402Claim({ scheme: "exact" }, Buffer.from(JSON.stringify(st)).toString("base64"));
  assert.deepEqual(c.settlement, st);
  assert.equal(c.minConfirmations, 2);
});
