# replay8004: a re-execution validator for ERC-8004 on Celo

**Status: v0.1.1 (2026-11-21). Celo Sepolia by default. 74 tests pass. Checked against live Celo (docs/VERIFICATION.md) and run end to end on Celo Sepolia (docs/TESTNET-RUN.md). Not on mainnet yet.**

ERC-8004 gives AI agents three on-chain registries: identity, reputation and **validation**. On
Celo the first two are in use. The Validation Registry
(`0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58` on mainnet) has had 39 transactions in total, the last
on 2026-03-19. Its 21 requests were all for one agent (#1870) on that one day; 17 were answered, each by
a different address, and nothing has been requested or answered since. Without active validators, "trust" on Celo comes down to
reputation feedback. A 2026 study of 173k ERC-8004 agents found 98.7–100% of that feedback has no
payment proof or task link, and sybil reviewers dominate it.

replay8004 is an open-source validator any agent can name in a `validationRequest`. It
**re-executes the agent's claim against Celo state** and answers with a 0–100 score, plus a
hash-chained evidence bundle anyone can re-check.

| claim kind (tag) | what the agent says | how it is re-checked |
|---|---|---|
| `erc20_transfer` (`replay:erc20_transfer`) | "payment tx T moved ≥ X of token K from A to B" (e.g. a settled x402 payment) | reads the receipt: status, `Transfer` log, confirmations. Score scales with the amount paid |
| `erc20_balance` (`replay:erc20_balance`) | "holder H had balance X of K at block N" | `balanceOf(H)` via `eth_call` at block N, optional tolerance |
| `contract_read` (`replay:contract_read`) | "calling f(args) on C at block N returned X" | the same `eth_call` at block N, ABI-decoded and compared |

Consumers (other agents, marketplaces, payment gates) read the result on-chain with
`getSummary(agentId, [validator], tag)` or `replay8004 summary`, and can follow `responseURI` to the
evidence.

## How a validation flows
```
agent owner ── validationRequest(validator, agentId, requestURI, keccak256(job)) ──▶ ValidationRegistry (Celo)
                                                                                         │ ValidationRequest event
replay8004 worker (Lambda, every minute) ◀── eth_getLogs(topic1 = validator) ────────────┘
  1. fetch requestURI (https://, ipfs:// or inline data:) and check keccak256 == requestHash
  2. check the job's agentId and chainId match the on-chain request
  3. re-run the claim against Celo (waits for confirmations; never answers early)
  4. write the evidence bundle (S3 Object Lock), hash-chained to the previous one
  5. validationResponse(requestHash, score, responseURI, keccak256(bundle), tag)
```
An invalid job (wrong hash, agent or chain, or a malformed claim) is answered with **0 and the
reason**, so the requester learns why. An RPC outage leaves the request pending. A request is
never answered twice.

## Quick start (offline)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                                  # 74 tests, fake chain, no network
replay8004 job erc20-transfer --agent-id 42 --validator 0xVALIDATOR \
  --tx 0xPAYMENT_TX --token 0xTOKEN --to 0xPAYEE --min-amount 10000 --out job.json
# prints requestHash, an inline data: requestURI and the validationRequest calldata
# the agent owner sends it from their own wallet, e.g.:
cast send 0x8004Cb1BF31DAf7788923b405b754f57acEB4272 <calldata> --rpc-url https://forno.celo-sepolia.celo-testnet.org --account owner
```

## Run the validator
```bash
replay8004 run --validator 0xVALIDATOR --once --start-block N  # dry run: prints the calldata it would send; N = block the validator went live (default: registry deployment block)
export REPLAY8004_VALIDATOR_KEY=0x...                         # a key used ONLY for this validator, from a secrets manager
replay8004 run --validator 0xVALIDATOR --send --interval 30 --evidence-base-url https://PUBLIC_HOST/evidence   # Celo Sepolia
REPLAY8004_ALLOW_MAINNET=1 replay8004 --network celo-mainnet run --validator 0x... --send --evidence-base-url https://PUBLIC_HOST/evidence   # operator decision
replay8004 verify-evidence .replay8004/evidence               # recompute hashes and the chain
```
Gas on Celo can be paid in stablecoins (fee abstraction). v0.1 pays in CELO: 0.0036 CELO per
`validationResponse` in the registry's March 2026 transactions, and at most ≈ 0.03 CELO
(≈ US$0.002) at today's 202 gwei.

## AWS (not deployed)
`infra/template.yaml` (passes `cfn-lint`) sets up: an EventBridge schedule that runs the worker
Lambda (arm64, 256 MB) once a minute with concurrency 1; a DynamoDB table for its state, using
conditional writes; an S3 bucket with Object Lock for evidence, readable by the public only under
`evidence/`; and a Secrets Manager secret holding only the validator key. It starts in `DryRun=1`
on Celo Sepolia. Cost is about US$1/month (see COSTS.md).
```bash
sam build -t infra/template.yaml
sam deploy --guided --parameter-overrides ValidatorAddress=0x... Network=celo-sepolia DryRun=1
```

## Security rules
- Mainnet is off unless the operator sets `REPLAY8004_ALLOW_MAINNET=1`.
- Keys come only from the environment or Secrets Manager. They are never logged, stored or returned.
- The validator wallet holds gas money only, a few CELO.
- The validator only reads Celo state and the job file. It never runs code from a job.
- Job files are capped at 64 KB. Only `https://`, `ipfs://` and `data:` URIs are accepted.

## Layout
| file | role |
|---|---|
| `replay8004/checkers/` | `erc20_transfer`, `erc20_balance`, `contract_read`: pure apart from RPC |
| `replay8004/job.py` | job schema, canonical bytes, `requestHash`, fetch and validation |
| `replay8004/evidence.py` | evidence bundles, `responseHash`, chain verification, local and S3 Object Lock sinks |
| `replay8004/registry.py` | ValidationRegistry calldata, event decoding, `getSummary`, transaction signer |
| `replay8004/worker.py` | scan → decide → evidence → respond, with pending retries and no double answers |
| `replay8004/lambda_handler.py`, `infra/template.yaml` | AWS deployment (not deployed) |
| `replay8004/cli.py` | `job`, `check`, `run`, `summary`, `status`, `verify-evidence` |
| `replay8004/identity.py`, `scripts/register_agent.py` | IdentityRegistry `register(agentURI)` and `Registered` decoding; dry-run-first registration script |

## Roadmap
- **v0.2:** Self Agent ID for the validator itself; register the validator as an ERC-8004 agent;
  `x402_settlement` checker (ties a payment to an x402 `PAYMENT-RESPONSE`); a TypeScript client
  (`@replay8004/client`) so JS agents can request validation in one call.
- **v0.3:** gate contract / viem helper: "accept this agent only if replay score ≥ N in the last
  30 days"; a public status page (requests answered, median time to answer, the evidence chain).
- **v1.0:** paid validations through x402 (≈ US$0.01–0.05 each) for high-volume agents. Free for
  open-source agents.

See COSTS.md, PROPOSAL.md (Prezenti Frontier application draft) and LAUNCH.md (steps only the operator can do).
License: Apache-2.0.
