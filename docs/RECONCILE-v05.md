# Reconciling the live repo with the v0.5 reference

Compared 2026-11-27: this repo at `91d23ec` (main, deployed to both stacks on 2026-11-27 05:16 / 05:30 UTC)
against the v0.5 reference (`../replay8004-v0.5`, unpacked from `replay8004-v0.5.zip`).
Method: `git ls-files` here vs every file in the reference, then `diff --strip-trailing-cr` on each shared file.

**Main finding: v0.5 was branched from an older copy of this repo** (about v0.1.1, before 2026-11-21) and
never received the fixes made while going live. So v0.5's versions of the core modules are *regressions*
for the parts they share. The merge therefore keeps this repo's core and ports v0.5's **additions** into it;
nothing core is copied over wholesale.

Counts: 3 files identical, 28 in both but different, 48 only in this repo (docs/fixtures/scripts/tests),
51 only in the reference.

## Identical (nothing to do)

`LICENSE`, `replay8004/hashing.py`, `replay8004/checkers/read.py`, `tests/test_registry_job.py`.

`hashing.py` (canonical JSON, keccak) and `job.make_job` are the same in both, so **job bytes and
requestHashes are unchanged** by the merge. `tests/vectors/client.json` (from v0.5) pins that across Python and TS.

## Only in the reference → added

| What | Files | Notes on how it is merged |
|---|---|---|
| x402_settlement checker | `replay8004/checkers/x402.py`, `tests/test_x402.py` | **Changed:** a missing receipt raises `ReceiptUnavailable` (unknown, stays pending) instead of scoring 0, matching this repo's `erc20` fix: forno prunes receipts, and a real payment must never get a permanent on-chain 0. Test updated. |
| Paid mode | `replay8004/billing.py`, `replay8004/paywall.py`, `docs/PAID.md`, `tests/test_billing_paywall.py` | Worker hook ported into *this* worker (see below). `PaidMode` defaults to `0`. |
| Off-chain gate + contract | `replay8004/gate.py`, `contracts/ReplayGate.sol`, `contracts/build.js`, `contracts/test/*`, `contracts/out/*.json`, `tests/test_gate_contract.py` | `gate.py` reuses `registry.encode_status/decode_status` (this repo already had them) instead of a second copy. |
| Canonical registry tests | `contracts/canonical/**`, `tests/test_canonical_registry.py` | Compiles the upstream `ValidationRegistryUpgradeable` with solc and runs replay8004's calldata against it. Skipped when web3/eth-tester or the build output are absent. |
| MCP server | `replay8004/mcp_server.py`, `replay8004/tools.py`, `tests/test_tools_mcp.py` | Read-only + unsigned calldata; extra `mcp` in pyproject. |
| Status page | `replay8004/status.py`, `examples/status/*`, `tests/test_status_gate.py` | CLI name clash resolved, see `status` below. |
| TS client | `clients/ts/**`, `tests/make_vectors.py`, `tests/test_vectors.py`, `tests/vectors/client.json` | Unchanged. |
| Agent Skill + celo-org PR | `skills/replay8004/SKILL.md`, `integrations/agent-skills/**` | Unchanged; the PR is not opened. |
| Docs | `docs/QUICKSTART.md` | Unchanged apart from the CLI notes below. |
| `registry.verify_deployment`, `getAgentValidations` | in `registry.py` | Added to this repo's `registry.py`. |
| `store.MemoryStore`, `default=` on stores | in `store.py` | Added. |
| Evidence `request.{block,tx,checkedAtBlock}` | in `evidence.py` | Added as optional fields (see below). |
| CLI `doctor`, `identity`, `gate`, `job x402-settlement` | in `cli.py` | Added to this repo's CLI. `run` keeps its existing guards. |
| CI: TS job, solc builds with `npm i --prefix .`, Python 3.13 | `.github/workflows/ci.yml` | Taken, plus this repo's `cfn-lint` step kept. |

## Only in this repo → kept (the reference never had them)

| What | Why it stays |
|---|---|
| `scripts/build_lambda.py`, `scripts/aws_inventory.py`, `scripts/renew-mfa.ps1`, `infra/iam/*.json` | How the live stacks are built and deployed (`CodeUri: ../build/lambda`, permissions boundary, MFA deployer). |
| `scripts/register_agent.py`, `scripts/request_validation.py`, `scripts/new_wallets.py` | Used for mainnet #1–#17 (docs/MAINNET-RUN.md). |
| `tests/test_daily_cap.py`, `test_exactly_once.py`, `test_key_handling.py`, `test_live_fixtures.py`, `test_packaging.py`, `test_request_script.py`, `tests/fixtures/*` | Guard live behaviour v0.5 lacks (below). |
| `docs/*` (MAINNET-RUN, AWS-*, VERIFICATION, …), `docs/mainnet/**`, `docs/testnet/**` | Run records and the evidence/jobs of the real answers. |
| `.gitattributes`, `.gitleaks.toml` | Line endings; secret scanning. |

## In both but different: what wins and why

### Core modules: this repo wins; v0.5 additions ported in

| File | This repo has (v0.5 lacks) | Taken from v0.5 |
|---|---|---|
| `worker.py` | **Exactly-once sending**: the signed tx is saved before broadcast, only that tx is rebroadcast, `_reconcile` confirms on-chain at `head − reorg_buffer`, `inflight`/`failed` state, a re-sign only when the nonce is used and there's no answer, `max_attempts`. **Skips requests already answered on-chain** (lost state). **Daily gas cap** (20/day, 5/agent; `daily` state key). A **dry run writes no evidence** and leaves the chain head untouched. Deterministic order by request block. Download failures are never scored. v0.5's `_answer` calls `sender.send()` with nothing persisted first, so a crash between send and save **answers twice**, which breaks a hard rule. | `request.block/tx/checkedAtBlock` in evidence; the billing hook (`billing=`, `usage` state, held/expired requests). Order inside a poll: the daily cap is checked first (no RPC), then billing, then deciding. |
| `rpc.py` | `User-Agent: replay8004/<ver>`: **forno.celo.org returns HTTP 403 to urllib's default UA** (that's why mainnet works at all). `ReceiptUnavailable`, `nonce_at`. | — |
| `job.py` | User-Agent on job downloads; `FetchError` (a transient download failure is never scored 0); malformed-URL handling. | — (job format identical) |
| `checkers/erc20.py` | Missing receipt → `ReceiptUnavailable`, not "transaction not found" = 0. | — |
| `networks.py` | `validation_deploy_block` (mainnet 58,396,736): fresh state starts there, not at genesis. | — |
| `registry.py` | `Sender.sign()` / `broadcast()` split with `min_nonce`; a bad key error never echoes the key; `encode_status/decode_status`. | `verify_deployment`, `DeploymentError`, `getVersion`, `getAgentValidations`. |
| `store.py` | `inflight`/`failed` in `empty()`. | `default=`, `MemoryStore`. Plus a new `migrate()` (below). |
| `evidence.py` | `url_for()` (dry run previews the URI without writing). | Optional `request` field. |
| `lambda_handler.py` | `make_sender` refuses a key that isn't `VALIDATOR_ADDRESS`; the secret is cached per container; retention days; daily caps; deploy-block fallback. | `verify_deployment` before the key is loaded; `_billing_from_env`; `paywall_handler`. |
| `cli.py` | `run --send` refuses `example.invalid` evidence URLs; `--max-answers-*`; `check` reports a missing receipt as undecidable; `status --request-hash` (getValidationStatus). | `doctor`, `identity`, `gate`, `job x402-settlement`, the status page, and `verify_deployment` in `run` (refuses `--send` if it fails). **`status` clash:** one command; `--request-hash` reads the chain, otherwise it builds the page. |
| `identity.py` | `registration_json`, `data_uri`, `registered_from_receipt` (used by `scripts/register_agent.py` to register agent #10141). | `registration()`, `registration_bytes`, `encode_set_uri`, `agent_id_from_receipt`. Both sets kept. |
| `checkers/__init__.py`, `__init__.py` | — | x402 tag; version **0.5.0**. |

### `infra/template.yaml`: this repo wins; only paid mode added

v0.5's template would damage the live stacks if deployed:

| v0.5 change | Effect on the live stack | Decision |
|---|---|---|
| Drops `DeletionPolicy/UpdateReplacePolicy: Retain` on the evidence bucket | Deleting the stack would try to delete locked evidence that on-chain answers link to | keep Retain |
| Drops `FunctionName: ${Stack}-worker` and the pre-created log group | CloudFormation **replaces** the function; the log group name collides | keep |
| `ReservedConcurrentExecutions: 1` | This account's concurrency quota made the stack `CREATE_FAILED` on 2026-11-26 (`tests/test_packaging.py` forbids it). Exactly-once comes from the conditional state write + on-chain checks | not taken |
| `Runtime: python3.12`, `CodeUri: ..` | Ships the whole repo (tests, docs, evidence) instead of `build/lambda` | keep 3.11 + build dir |
| Drops `PermissionsBoundary`, tags, the schedule name, `RetryPolicy: 0`, `Outputs` | Breaks the IAM boundary policy and teardown docs; the default retry re-runs failed polls 185 times | keep |
| Drops `EvidenceRetentionDays` MinValue, `MaxAnswersPerDay`, `MaxAnswersPerAgentPerDay` | Loses the gas guard | keep |
| **Adds** `PaidMode` (default 0), `PayTo`, `FacilitatorKeySecretArn`, `FreePerMonth`, `FreeAccounts`, `PaywallFunction` + logs (condition `Paid`) | With `PaidMode=0` nothing new is created | **taken**, rewritten in this template's style (fixed name, boundary, tags, retained logs, no reserved concurrency) |

### Other shared files

| File | Decision |
|---|---|
| `pyproject.toml` | Keep `setuptools>=77` + SPDX `license`/`license-files` (needed for `tests/test_packaging.py`); take version 0.5.0, `contracts` + `mcp` extras, the `replay8004-mcp` script, pytest config. |
| `.gitignore` | Keep this repo's (`.env*`, keys, `keystore/`, `.self/`, `.aws-sam/`, `build/`); add v0.5's `contracts/node_modules`, `contracts/out/*`, `clients/ts/{node_modules,dist}`, `site/`. |
| `tests/conftest.py` | Keep `FakeSender`, the nonce/answer simulation, `getValidationStatus`; add `add_x402_settlement`. |
| `tests/test_worker.py`, `test_checkers.py`, `test_identity.py` | Keep this repo's (they test the live semantics); add v0.5's identity tests in a new section. |
| `examples/demo.py` | Keep (uses `FakeSender`); add `examples/demo_x402.py`, adapted the same way. |
| `examples/registration.json` | Take v0.5's (generated by `replay8004 identity`, includes the x402 tag). |
| `README.md`, `index.html`, `LAUNCH.md`, `COSTS.md`, `PROPOSAL.md`, `CLAUDE.md` | Keep this repo's facts (it is private, live on mainnet, agent #10141, Self #218); add v0.5's new sections (doctor, x402, MCP, gate, status page, TS client, paid mode). |

## State migration (DynamoDB item `pk=worker`)

The live item was written by 0.1.1 + the gas guard: `last_block, done, pending, inflight, failed, seq, head, daily`.
v0.5 adds `usage` (paid mode) and may add `expired`. `store.migrate(st)` adds missing keys only, using `setdefault`,
and **never touches `last_block`, `seq`, `head` or `done`**. It runs at the start of each `poll_once()`, so the first
poll after the deploy writes the upgraded item through the same conditional (`ver`) write as always. No separate
migration step or downtime. Tested in `tests/test_migration.py`, including chain continuity from a copy of the live head.

## Evidence format

- New answers carry `request: {block, tx, checkedAtBlock}` and `checkerVersion: "0.5.0"`.
- The 5 live mainnet bundles (`checkerVersion: "0.1.1"`, no `request`) still verify: `request` is optional,
  `verify_chain` doesn't read it, and the status page skips bundles without it when computing latency.
- `responseHash = keccak256(canonical(bundle))` is unchanged; the next bundle is `seq = live seq + 1` with
  `prev = live head`.
