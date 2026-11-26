# replay8004: notes for Claude Code

Re-execution validator for the ERC-8004 ValidationRegistry on Celo. Owner: David (Mexico). Apache-2.0.
Goal: Prezenti S3 Frontier grant (deadline 2026-12-29), then paid validations via x402.

## Commands
- Setup: `pip install -e ".[dev]"` · Tests: `pytest -q` (78, offline) · Lint infra: `cfn-lint infra/template.yaml`

## Hard rules
- Celo Sepolia by default. Mainnet only with REPLAY8004_ALLOW_MAINNET=1 set by David; never flip the default.
- Keys only from env/Secrets Manager; never print, log, store or return them.
- Checkers stay pure apart from the RPC they're given; never execute code from a job.
- Never answer a request twice; persist state after each answer.
- Every answer writes an evidence bundle first; responseHash = keccak256(canonical(bundle)).
- New checker = allow + deny tests + a tag in checkers/__init__.py.

## Next
v0.2: Self Agent ID for the validator, ERC-8004 registration JSON, x402_settlement checker, TypeScript client.
