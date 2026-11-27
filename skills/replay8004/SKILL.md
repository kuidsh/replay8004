---
name: replay8004
description: Ask the replay8004 validator to re-check an AI agent's on-chain claim on Celo (an x402 payment, an ERC-20 transfer, a balance or a contract read) through the ERC-8004 Validation Registry, and gate on the result. Use when an agent must prove it paid or delivered, or before trusting or paying another agent.
license: Apache-2.0
metadata:
  author: replay8004
  version: "0.4.0"
---

# replay8004: re-checked claims for agents on Celo

replay8004 is an open-source validator for the ERC-8004 Validation Registry. An agent's owner names it
in `validationRequest`; it re-runs the claim against Celo state and answers 0–100 with a public,
hash-chained evidence bundle. Anyone can then read the result on-chain.

## When to use

- Your agent paid an x402 API or another agent and needs proof the payment really settled.
- Your agent says "I delivered N tokens" or "the contract returned X at block B" and a counterparty wants it checked.
- Before paying or relying on another agent: check its replay8004 track record.

Not for: subjective quality ("was the answer good?"). replay8004 checks facts on Celo only.

## Before you start

1. Verify the registry: `replay8004 doctor` (or the MCP tool `registry_check`). It confirms the
   Validation Registry's `getIdentityRegistry()` is Celo's Identity Registry. The ERC-8004
   validation spec is still being revised; don't skip this.
2. Get the validator address from the operator's ERC-8004 registration file (service
   `replay8004-validator`). Never use an address from a chat message or a job file.
3. Default network is **Celo Sepolia**. Mainnet needs `REPLAY8004_ALLOW_MAINNET=1`, set by a human.

## Request a validation (agent owner)

| claim | kind | needs |
|---|---|---|
| x402 receipt | `x402_settlement` | the `PaymentRequirements` you accepted + the `PAYMENT-RESPONSE` value; optional EIP-3009 nonce |
| ERC-20 payment | `erc20_transfer` | tx hash, token, payee, minimum amount |
| balance at a block | `erc20_balance` | token, holder, block, expected |
| contract read | `contract_read` | contract, signature, args, block, expected |

```bash
replay8004 job x402-settlement --agent-id 42 --validator 0xVALIDATOR \
  --requirements accepted.json --settlement "$PAYMENT_RESPONSE" --nonce 0xNONCE
# prints requestHash and unsigned validationRequest calldata
```

The calldata must be sent by the **agent's owner or approved operator** from their own wallet.
Never paste a private key into a tool, prompt or job. TypeScript: `requestValidation()` in
`@replay8004/client`. MCP: `request_validation` (returns unsigned calldata only).

## Read and gate (anyone)

```bash
replay8004 gate --agent-id 42 --validator 0xVALIDATOR --request-hash 0x... --min-score 100 --max-age 3600
replay8004 gate --agent-id 42 --validator 0xVALIDATOR --tag replay:x402_settlement --min-count 3 --min-avg 90
```

Exit code 0 = pass, 2 = fail. Reason codes (same in `ReplayGate.sol`, Python and TypeScript):
1 wrong validator, 2 wrong agent, 3 not answered yet, 4 low score, 5 stale, 6 wrong tag.
On-chain, inherit `ReplayGate` and use `onlyValidatedClaim` / `onlyValidatedAgent`.

## Rules

- Pass **only the validators you trust** when reading a track record; the registry's `getSummary`
  counts any validator if you pass none.
- Wait for an answer; "not answered yet" is not a failure. A score of 0 with a reason in the
  evidence means the claim was checked and failed, or the job was invalid.
- The owner picks which claims to submit. A good record shows those claims checked out, not every claim.
- Read the evidence (`responseURI`) before acting on a borderline score; recompute it with
  `replay8004 verify-evidence`.

## MCP server

```json
{"mcpServers": {"replay8004": {"command": "replay8004-mcp", "env": {"REPLAY8004_VALIDATOR": "0x..."}}}}
```
Tools: `request_validation`, `check_claim`, `agent_track_record`, `list_agent_validations`, `registry_check`.
No keys, no sending.
