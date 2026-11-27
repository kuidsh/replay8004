# Outreach drafts (David posts them; nothing here has been posted)

Post these only after (1) the repo is public (docs/PHASE6-CHECKLIST.md), since every link needs it, and (2) the daily
answer cap is deployed to the mainnet stack: the texts promise it.

---

## 1. Celo forum post (category: AI / Agents)

**Title:** Free validations for ERC-8004 agents on Celo: replay8004 is live on mainnet

Celo's ERC-8004 Validation Registry (`0x8004Cc84…AB58`) has recorded no answers since March. Only one agent ever used it,
on a single day. replay8004 is an open-source validator that you can name in a `validationRequest` today.

**What it does.** Your agent claims something anyone can check on Celo, for example "tx T paid ≥ X of token K to B" (an
x402 settlement), "holder H had balance X at block N", or "contract C returned X at block N". replay8004 re-executes the
claim against Celo state and answers on-chain with a 0-100 score and a tag. It also publishes a hash-chained evidence
bundle whose keccak256 is the on-chain `responseHash`, so anyone can recompute the result.

**It's live.**
- Validator `0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952`, ERC-8004 agent #10141, Self Agent ID #218.
- 5 mainnet answers so far: a real payment (100), a false claim (0), and a claim of 0.02 against an actual payment of 0.01 (50).
- Answers arrive within about a minute; every tx is in [MAINNET-RUN.md](https://github.com/kuidsh/replay8004/blob/main/docs/MAINNET-RUN.md).

**Free for agents building on Celo.** Requests go into a public queue, with a daily cap per agent so nobody can drain the
validator. One command builds the job and sends the request from your agent's owner wallet:
```bash
git clone https://github.com/kuidsh/replay8004 && cd replay8004 && pip install -e .
export REPLAY8004_ALLOW_MAINNET=1        # mainnet is opt-in; without --send this is a dry run
python scripts/request_validation.py --network celo-mainnet --key-env OWNER_KEY request \
  --agent-id <your agent> --validator 0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952 \
  --tx <payment tx> --to <payee> --min-amount <wei> --send
```
Consumers read the result with `getSummary(agentId, [0xD2d6…5952], "replay:erc20_transfer")`.

Repo (Apache-2.0, 102 tests): https://github.com/kuidsh/replay8004. Feedback on which claim kinds you need next is very
welcome: `x402_settlement` and a TypeScript client are next on the list.

---

## 2. Discord message (Celo, AI agents channel), short

> 👋 replay8004 is live on Celo mainnet: an open-source validator for the ERC-8004 Validation Registry. Name
> `0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952` in a `validationRequest`, and it re-checks your agent's payment, balance or
> contract-read claim against Celo state. It answers on-chain with a 0-100 score and public, hash-chained evidence,
> usually within a minute. Free for agents building on Celo. 5 mainnet answers so far:
> https://github.com/kuidsh/replay8004/blob/main/docs/MAINNET-RUN.md. Happy to onboard your agent; just reply here.

---

## 3. Pull request to `celo-org/agent-skills`

Their CONTRIBUTING.md asks for: the Agent Skills spec (a `SKILL.md` with frontmatter), contract addresses verified on
explorers, tested code examples, Celo Sepolia testing, under 500 lines, and a README update when adding a skill. Fork,
then branch `add-replay8004-validation`.

**PR title:** Add replay8004 skill: request ERC-8004 validations on Celo

**PR description:**
```markdown
## What
A new skill, `skills/replay8004/`, that teaches agents to request and read ERC-8004 *validations* on Celo. The existing
`8004` skill covers identity and reputation in depth but lists the Validation Registry only as "custom validators".
This skill fills that gap with a working, open-source validator:

- how a `validationRequest` / `validationResponse` round trip works (selectors verified against the deployed registry)
- building a job for a claim (settled ERC-20 / x402 payment, balance at a block, deterministic contract read)
- sending the request from the agent owner's wallet and reading the result with `getSummary` / `getValidationStatus`
- checking the public evidence bundle (keccak256 == on-chain `responseHash`)

## Verified
- Registry addresses checked with `eth_getCode` on Celo mainnet and Celo Sepolia, and against erc-8004-contracts.
- Every command was run on Celo Sepolia and on Celo mainnet. 5 mainnet answers are listed here:
  https://github.com/kuidsh/replay8004/blob/main/docs/MAINNET-RUN.md
- SKILL.md is under 500 lines; README updated with the new skill.

## Disclosure
I maintain replay8004 (Apache-2.0). The skill works with any ERC-8004 validator; replay8004 is the example.
```

**Draft `skills/replay8004/SKILL.md`** (check every command again before opening the PR):
```markdown
---
name: replay8004
description: Request and read ERC-8004 validations on Celo. Use when an agent must prove a claim another agent can check (an x402 or ERC-20 payment settled, a balance at a block, a contract read) and get an on-chain 0-100 score with public evidence.
license: Apache-2.0
metadata:
  author: kuidsh
  version: "1.0.0"
---

# Request ERC-8004 validations with replay8004

## When to use
- Prove to another agent or a marketplace that a payment settled, without a trusted middleman
- Gate access on a validator score: `getSummary(agentId, [validator], tag)`
- Add "validation" to an agent's `supportedTrust`

## Addresses (Celo mainnet, chain 42220)
| | |
|---|---|
| ValidationRegistry | `0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58` |
| IdentityRegistry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |
| replay8004 validator | `0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952` (agent #10141) |
Celo Sepolia ValidationRegistry: `0x8004Cb1BF31DAf7788923b405b754f57acEB4272`.

## Flow
1. The agent owner calls `validationRequest(validator, agentId, requestURI, requestHash)`. `requestURI` holds the job
   (an inline `data:` URI is fine) and `requestHash = keccak256(job bytes)`.
2. The validator re-executes the claim against Celo state, then calls
   `validationResponse(requestHash, score, responseURI, responseHash, tag)`.
3. Anyone reads `getValidationStatus(requestHash)` or `getSummary(agentId, [validator], tag)`, and can download
   `responseURI` and check that keccak256 of it equals `responseHash`.

## Request a payment validation
    git clone https://github.com/kuidsh/replay8004 && cd replay8004 && pip install -e .
    export REPLAY8004_ALLOW_MAINNET=1
    python scripts/request_validation.py --network celo-mainnet --key-env OWNER_KEY request \
      --agent-id <id> --validator 0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952 \
      --tx <payment tx> --to <payee> --min-amount <wei> [--payer <payer>]        # dry run; add --send
The command re-checks the claim locally and prints the expected score before anything is sent.

## Read the result (read-only; mainnet still needs REPLAY8004_ALLOW_MAINNET=1)
    replay8004 --network celo-mainnet status --request-hash <hash>
    replay8004 --network celo-mainnet summary --agent-id <id> --validator 0xD2d6…5952 --tag replay:erc20_transfer

## Scores and tags
- 100: the claim holds. Lower: a partial payment scores in proportion to the amount paid. 0: the claim is false.
- `replay:invalid` with score 0 means the job was malformed (wrong hash, agent or chain); the reason is in the evidence.
- A claim that can't be checked yet (too few confirmations, receipt unavailable) stays pending. It is never scored 0.
```

Also add one line to their README's skill list: `| replay8004 | Request and read ERC-8004 validations on Celo |`.
