# replay8004: a re-execution validator for ERC-8004 on Celo

**Status (2026-11-27): live on Celo mainnet** since 2026-11-26 as validator `0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952` (ERC-8004 agent #10141, Self Agent ID #218): 5 requests, 5 answers, 13–55 s each (docs/MAINNET-STATUS.md). Site: https://kuidsh.github.io/replay8004/ · live status, rebuilt from the public evidence: https://replay8004-mainnet-evidencebucket-exgfx3xqkhfr.s3.us-east-1.amazonaws.com/evidence/status/index.html Both stacks (mainnet and Sepolia) run **v0.5** since 2026-11-27. Celo Sepolia is the CLI default. 185 Python tests (11 on an in-process EVM) + 5 TypeScript tests pass, offline.

v0.5 merges the reference v0.5 into the live code (docs/RECONCILE-v05.md): the `x402_settlement` checker, `doctor` (the registry is checked on-chain before any key is loaded), `request.block` in evidence, a state migration that never resets the evidence chain, `ReplayGate.sol` + the same rules off-chain (`gate`), a status page built from public evidence (`status --evidence`), the validator's registration file (`identity`), a TypeScript client (`clients/ts`), a read-only MCP server, an Agent Skill, a ready PR for Celo's `8004` skill, and **paid mode** (x402 credit packs, off by default and refused on mainnet for now; docs/PAID.md).

ERC-8004 gives AI agents three on-chain registries: identity, reputation and **validation**. On
Celo the first two are in use. The Validation Registry
(`0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58` on mainnet; the validation spec is still a preview, so replay8004
checks the address on-chain before using it) had 39 transactions before replay8004, the last
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
| `x402_settlement` (`replay:x402_settlement`) | "this x402 receipt (PaymentRequirements + SettlementResponse) is real" | scheme `exact`; CAIP-2 network matches; tx succeeded and is confirmed; the asset's `Transfer` from payer to payTo covers `amount`; a receipt that reports more than moved scores 0; optional EIP-3009 `AuthorizationUsed` nonce and facilitator checks |

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
reason**, so the requester learns why. An RPC outage, a job that can't be downloaded or a receipt the RPC no longer
has leaves the request pending: unknown is never scored 0. A request is never answered twice.

## Quick start (offline)
```bash
pip install replay8004                     # from PyPI; or, to run the tests, from a clone:
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                                  # 185 tests, fake chain, no network (EVM tests: pip install -e ".[contracts]" + node contracts/build.js)
replay8004 job erc20-transfer --agent-id 42 --validator 0xVALIDATOR \
  --tx 0xPAYMENT_TX --token 0xTOKEN --to 0xPAYEE --min-amount 10000 --out job.json
# prints requestHash, an inline data: requestURI and the validationRequest calldata
# the agent owner sends it from their own wallet, e.g.:
cast send 0x8004Cb1BF31DAf7788923b405b754f57acEB4272 <calldata> --rpc-url https://forno.celo-sepolia.celo-testnet.org --account owner
replay8004 doctor                          # is the configured ValidationRegistry wired to this network's Identity Registry?
```

### x402 receipts
```bash
# accepted.json = the PaymentRequirements entry you paid (from PAYMENT-REQUIRED accepts[i])
replay8004 job x402-settlement --agent-id 42 --validator 0xVALIDATOR \
  --requirements accepted.json --settlement "$PAYMENT_RESPONSE" --nonce 0xYOUR_EIP3009_NONCE
python -m examples.demo_x402        # offline: a real receipt (100), an over-reported one (0), a wrong authorization (0)
```

### Consumers: gate, status page, MCP, TypeScript
```bash
replay8004 gate --agent-id 42 --validator 0xVALIDATOR --tag replay:erc20_transfer   # ReplayGate rules; exit 0 = pass
replay8004 status --request-hash 0x..                                              # one request, on-chain
replay8004 status --evidence <folder of bundles> --out site                        # public status page, no RPC, no key
pip install -e ".[mcp]" && REPLAY8004_VALIDATOR=0x... replay8004-mcp               # read-only MCP server
```
Solidity: inherit `contracts/ReplayGate.sol` (`onlyValidatedAgent`, `onlyValidatedClaim`). TypeScript: `clients/ts`
(`requestValidation()`, `x402Claim()`, `getSummary()`, `passes()`); job bytes match Python (`tests/vectors/client.json`).

### The validator's own ERC-8004 identity
```bash
replay8004 --network celo-mainnet identity --validator 0xVALIDATOR --repo https://github.com/<you>/replay8004 \
  [--agent-id N] [--uri <hosted file>] --out registration.json      # prints register / setAgentURI calldata; sends nothing
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

## AWS (running for Celo mainnet and Celo Sepolia)
`infra/template.yaml` (passes `cfn-lint`) sets up:
- an EventBridge schedule that runs the worker Lambda (arm64, 256 MB) once a minute, without retries;
- a DynamoDB table for the worker's state, written conditionally so that two overlapping runs cannot both answer;
- a gas guard: at most 20 answers per UTC day and 5 per agent (`MaxAnswersPerDay`, `MaxAnswersPerAgentPerDay`; 0 pauses
  answering). Requests over the cap wait, oldest first, and are never scored 0;
- an S3 bucket with Object Lock for evidence, readable by the public only under `evidence/`;
- a Secrets Manager secret holding only the validator key, which the Lambda checks against `ValidatorAddress`, after
  `verify_deployment` has checked the registry on-chain;
- paid mode (`PaidMode`, default 0): with 1, an x402 paywall Function URL sells credit packs and the worker answers only
  covered requests. A template rule refuses it on `celo-mainnet` until it has run end to end on Sepolia.

Every resource is tagged `Project=replay8004`, and every IAM role it creates carries the permissions boundary in
`infra/iam/`. It starts in `DryRun=1` on Celo Sepolia. Measured runs take about 1 s. Cost is about US$0.05/month in
dry run, or about US$0.45/month per live stack (us-east-1 list prices, checked 2026-11-26). The deploy command is in docs/PHASE5.md. Taking it all
down is described in docs/AWS-TEARDOWN.md, and the resources are listed in docs/AWS-RESOURCES.md.
```bash
python scripts/build_lambda.py   # stages only the package and its requirements
sam build -t infra/template.yaml
sam deploy ...                   # full command with tags and boundary: docs/PHASE5.md
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
| `replay8004/checkers/` | `erc20_transfer`, `erc20_balance`, `contract_read`, `x402_settlement`: pure apart from RPC |
| `replay8004/job.py` | job schema, canonical bytes, `requestHash`, fetch and validation |
| `replay8004/evidence.py` | evidence bundles, `responseHash`, chain verification, local and S3 Object Lock sinks |
| `replay8004/registry.py` | ValidationRegistry calldata, event decoding, `getSummary`, transaction signer |
| `replay8004/worker.py` | scan → decide → evidence → respond, with pending retries and no double answers |
| `replay8004/lambda_handler.py`, `infra/template.yaml`, `infra/iam/` | AWS deployment (running for Celo Sepolia) and its IAM policies |
| `replay8004/store.py` | worker state (file, DynamoDB, memory) and `migrate()`, which never touches `last_block/seq/head/done` |
| `replay8004/cli.py` | `job`, `check`, `run`, `summary`, `status`, `identity`, `doctor`, `gate`, `verify-evidence` |
| `replay8004/identity.py`, `scripts/register_agent.py` | registration file, `register`/`setAgentURI` calldata, `Registered` decoding; dry-run-first registration script |
| `replay8004/gate.py`, `contracts/ReplayGate.sol`, `replay8004/status.py` | gate rules (Python and Solidity); status page from evidence bundles |
| `replay8004/tools.py`, `replay8004/mcp_server.py`, `skills/replay8004/` | MCP tools (read-only + unsigned calldata); Agent Skill |
| `replay8004/billing.py`, `replay8004/paywall.py` | paid mode: credit packs, free quota, admit rule; x402 paywall (verify → settle → on-chain re-check → credit) |
| `clients/ts/` | `@replay8004/client` (viem) + tests against `tests/vectors/client.json` |
| `contracts/canonical/`, `tests/test_canonical_registry.py` | ERC-8004 registry sources and conformance tests |
| `integrations/celopedia/` | the Validation Registry reference sent to Celo's Celopedia skill ([PR #126](https://github.com/celo-org/celopedia-skills/pull/126)); `integrations/agent-skills/` is the earlier version for the archived agent-skills repo |

## Roadmap
- **Done:** mainnet validator with Self Agent ID and ERC-8004 registration (2026-11-26); gas guard; v0.5 merged
  (x402 checker, TS client, gate, status page, MCP, skill PR, paid mode).
- **Done 2026-11-27:** v0.5 deployed to both stacks.
- **Done 2026-11-27:** repo public, site on GitHub Pages, status page, `replay8004` on PyPI, `@replay8004/client` on npm.
- **Open:** [Celopedia PR #126](https://github.com/celo-org/celopedia-skills/pull/126) (Validation Registry docs).
- **Next (Frontier milestone 1):**
  10 external agents.
- **Then:** publish the status page and the gate package; framework integrations; paid mode on Sepolia, then mainnet.

See COSTS.md, PROPOSAL.md (Prezenti Frontier application), docs/LAUNCH-STATUS.md (what's done and the steps only the operator can do).
License: Apache-2.0.
