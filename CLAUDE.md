# replay8004: notes for Claude Code

Re-execution validator for the ERC-8004 ValidationRegistry on Celo. Owner: David (Mexico). Apache-2.0.
Goal: Prezenti S3 Frontier grant (deadline 2026-12-29), then paid validations via x402.

## Commands
- Setup: `pip install -e ".[dev]"` · Tests: `pytest -q` (185, offline; the 11 EVM tests need `pip install -e ".[contracts,mcp]"`,
  `node contracts/build.js` and `node contracts/canonical/build.js`, see .github/workflows/ci.yml) · TS: `cd clients/ts && npm ci && npm test`
- Lint infra: `cfn-lint infra/template.yaml` · Lambda: `python scripts/build_lambda.py; sam build -t infra/template.yaml`

## Hard rules
- Celo Sepolia by default. Mainnet only with REPLAY8004_ALLOW_MAINNET=1 set by David; never flip the default.
- Keys only from env/Secrets Manager; never print, log, store or return them.
- Checkers stay pure apart from the RPC they're given; never execute code from a job.
- Never answer a request twice; persist state after each answer (the signed tx is saved before it is broadcast).
- Every answer writes an evidence bundle first; responseHash = keccak256(canonical(bundle)).
- Unknown is not false: a missing receipt or an unreachable job stays pending, never scored 0.
- Never reset or fork the evidence chain: state changes go through `store.migrate()`, which only adds keys and never
  touches last_block/seq/head/done.
- Job bytes must stay identical in Python and TS: after changing job/canonical code run `python tests/make_vectors.py`.
- Never hardcode trust in the Validation Registry address: `registry.verify_deployment` must pass before sending.
- MCP tools return unsigned calldata only; never add a tool that signs or sends.
- Paid mode: never answer a request with 0 for lack of payment (hold, then expire). Credit a payment only after the
  on-chain x402_settlement check scores 100; one credit per tx hash and per EIP-3009 nonce. The paywall holds no
  fund-moving key. PaidMode stays 0 on mainnet (the template refuses 1 there).
- Template: keep the fixed function names, Retain on the bucket, the boundary, no reserved concurrency (tests/test_packaging.py).
- npm installs under contracts/ and contracts/canonical/ must use `--prefix .`.
- New checker = allow + deny tests + a tag in checkers/__init__.py.
- Gate rules and reason codes must match in ReplayGate.sol, gate.py and clients/ts decideClaim.

## Next
Branch v0.5-merge: built, changesets created (not executed). David: deploy (Sepolia, then mainnet), make the repo
public, publish npm/PyPI, open the skill PR and the erc-8004-contracts issue (docs/LAUNCH-STATUS.md). Then outreach
(docs/OUTREACH.md) and the Frontier form (docs/FRONTIER-SUBMISSION.md) by 2026-12-15.
