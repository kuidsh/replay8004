# PR to `celo-org/agent-skills`: document the Validation Registry in the `8004` skill

> **Superseded 2026-11-27.** `celo-org/agent-skills` is archived (read-only); this content was adapted for Celopedia and
> opened as https://github.com/celo-org/celopedia-skills/pull/126. See docs/LAUNCH-STATUS.md (f) and `integrations/celopedia/`.

**Base:** `celo-org/agent-skills@c414cbb` (main, 2026-09-13). **Patch:** `0001-8004-validation-registry.patch`
(made with `git diff`, so you author the commit). The changed files are also copied under `skills/8004/` here.

## Why (verified 2026-11-25)

- The `8004` skill (v1.1.0) names the Validation Registry but lists no functions ("Custom validators"),
  no ABI and no example. Agents using the skill can't call it.
- Celopedia (`references/ai-agents.md`) says: "Do not give a Celo Validation Registry address", because the
  contracts repo README lists only Identity and Reputation and marks the validation spec as being revised.
- So this PR adds the **interface, ABI, examples and pitfalls, but no address**, plus an on-chain check
  (`getIdentityRegistry()` must equal the skill's Identity Registry) for whatever address a builder takes from
  the contracts repo. That stays consistent with Celopedia.
- Every function, revert string and behaviour in the reference was read from
  `ValidationRegistryUpgradeable.sol` at erc-8004-contracts `b9e466c`, and is exercised by
  `tests/test_canonical_registry.py` in replay8004 (canonical contracts compiled with the repo's settings,
  deployed via its own minimal-UUPS path, on an in-process EVM).

## Changes

| file | change |
|---|---|
| `skills/8004/SKILL.md` | version 1.1.0 → 1.2.0; Validation Registry row lists its real functions; ABI note; the "Validation Registry" section gets a 2-line how-to and a pointer to the reference. 488 lines (limit 500) |
| `skills/8004/references/validation-registry-abi.json` | new: the 10 public entries (8 functions, 2 events) from the official `abis/ValidationRegistry.json`, without the proxy/ownership admin entries |
| `skills/8004/references/validation-registry.md` | new: interface table with who may call and revert strings, verify-the-deployment code, request and read examples (viem), pitfalls |

## Pitfalls it documents (each checked in the contract source)

- `getSummary` with `[]` validators counts **every** validator, including one the agent's owner runs.
- `getSummary` has no time window; `lastUpdate` is set at request time and again on each answer.
- Answers can be overwritten by the same validator.
- `getValidationStatus` doesn't return `hasResponse`; unanswered reads as response 0, responseHash 0.
- `requestHash` is global and first-come (`"exists"`), so jobs should include the agentId and a nonce.

## How to submit (David)

```bash
gh repo fork celo-org/agent-skills --clone && cd agent-skills
git checkout -b validation-registry-docs
git apply /path/to/replay8004/integrations/agent-skills/0001-8004-validation-registry.patch
git add -A && git commit -m "8004: document the Validation Registry interface (preview) with ABI and on-chain verification"
git push -u origin validation-registry-docs && gh pr create --fill
```
Paste the "Why" and "Changes" sections above as the PR body. Disclose that you run replay8004 (a validator);
the PR itself names no validator.

## Testing

- `tests/test_canonical_registry.py` (replay8004): every behaviour in the pitfalls list, on the canonical contracts.
- The reference's viem snippets compile under **strict** TypeScript against viem (see `snippet-check/`: the
  snippets pasted unchanged except for a const-typed ABI import, a typed parameter and placeholder addresses).
- 2026-11-27: the patch applies cleanly to `celo-org/agent-skills@c414cbb` (still `main`); SKILL.md is 488 lines.
  `snippet-check/` typechecks under strict TS (viem 2.21.54, TS 5.6.3); `abi.ts` is the ABI file as a const export.
  The doc's code blocks differ from `snip.ts` only in the 3 documented lines.
- 2026-11-27, **read-only on Celo Sepolia** (same script pointed at `0x8004Cb1B…4272`, viem 2.58.8): `2.0.0`, the "no contract"
  error, an answered request read back (score 100), `getSummary(1037, [validator], "")` = (3, 66), and the `"unknown"`
  revert for a never-requested hash. Strict typecheck also passes on viem 2.58.8. All links checked (no 404s).
- 2026-11-27, **read-only on Celo mainnet** (`npx tsx snippet-check/verify_live.ts`): `verifyValidationRegistry`
  on `0x8004Cc84…AB58` returns `2.0.0`, throws "no contract" on an empty address; `getValidationStatus` on a real
  replay8004 answer returns it (score 100, tag `replay:erc20_transfer`); `getSummary(10143, [validator], "")` =
  (5, 70); a never-requested hash reverts, as the reference says ("unknown").
