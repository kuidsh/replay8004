# DRAFT: Prezenti Season 3 Frontier application, "replay8004"

> Form: https://frontier.prezenti.xyz. Window closes **2026-12-29**. Fill the bracketed parts after the launch steps in LAUNCH.md.

**Product:** replay8004, the first operating validator for the ERC-8004 Validation Registry on Celo.
**Lead applicant:** David Vega (Mexico). Software and data engineer, 13+ years (Python, SQL, AWS
Serverless, ETL, REST APIs). He has shipped two production Python + blockchain systems with
on-chain/off-chain verification and auditable logging, including an election-day integrity system.
**Links:** GitHub [github.com/<you>/replay8004] · KarmaGAP [profile] · X [@handle]
**Tech category:** Verification and trust infrastructure (also agent-to-agent transactions).

## Required items
- **ERC-8004:** the validator itself is registered as agent #[id] on Celo mainnet.
- **Self Agent ID:** [agent id]. The validator's operator is human-verified with Self.
- **Mainnet deployment:** the validator answers on the canonical ValidationRegistry
  `0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58` from address [0x…]. No new contract is needed, so
  there is nothing new to audit.
- **Verifiable on-chain activity:** [N] `validationResponse` txs on Celo mainnet ([CeloScan link]),
  each with a public evidence bundle.
- **Open source:** Apache-2.0, 32+ tests, CI.

## Problem
Celo has ERC-8004 identity and reputation in use, but the **Validation Registry is dormant**: 39 txs in
total, the last on 2026-03-19, with no validator operating. A 2026 study of 173k ERC-8004 agents on
Ethereum, BSC and Base found that 98.7–100% of reputation feedback has neither payment proof nor
task linkage, and that sybil reviewers dominate the rest. Agents paying each other in stablecoins
on Celo have no neutral, machine-readable way to prove "I delivered / I paid / my number was right."

## Solution
An open validator anyone can name in a `validationRequest`. It re-executes the claim against Celo
state, and answers with a 0–100 score, a tag, and a keccak-committed, hash-chained evidence bundle
(S3 Object Lock) that anyone can recompute. Claim kinds: settled ERC-20 / x402 payments, balances
at a block, and arbitrary deterministic contract reads. A requester can see why a request failed:
invalid jobs get a 0 with the reason. Consumers gate on `getSummary(agentId, [validator], tag)`.

## Milestones (ask: US$12,000)
| # | deliverable | weeks | amount |
|---|---|---|---|
| 0 | Contract signed (Prezenti's 20%) | — | US$2,400 |
| 1 | Validator live on Celo mainnet with Self Agent ID; TypeScript client; `x402_settlement` checker; docs and a 5-minute quick-start; 10 external agents onboarded | 5 | US$3,600 |
| 2 | Gate helper (viem + Solidity) for "only accept agents with a replay score ≥ N"; public status page (requests, answer latency, evidence chain); integrations with 2 Celo agent frameworks | 5 | US$3,000 |
| 3 | 100 agents or 2,000 mainnet validations; paid validation via x402 for high-volume users; usage report | 6 | US$3,000 |

## Activation path (first 10–100 agents)
1. A PR to `celo-org/agent-skills` adding a "request validation" skill next to the existing 8004 skill.
2. Direct outreach to builders on Celo Mainnet with ERC-8004 registrations and x402 activity (Aigora's 47 agents and 522 x402 calls show they exist).
3. Free validations for open-source agents; a single CLI call or one TypeScript function.

## Distribution and past execution
[Two production blockchain systems shipped; election-day integrity system; analytics prototypes for the Stellar Community Fund; agentguard, an open-source risk guard for AI agents on dYdX, live on testnet.]

## Measurable outcomes
Agents requesting validations · mainnet `validationResponse` txs · median time to answer ·
share of requests that were invalid · evidence-chain verifications by third parties.

## Previous funding
[SCF #46 Build Award application pending (Stellar analytics); no other grants.]
