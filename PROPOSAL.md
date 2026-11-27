# DRAFT: Prezenti Season 3 Frontier application, "replay8004"

> Form: https://frontier.prezenti.xyz. Window closes **2026-12-29**; target 2026-12-15. On-chain facts below were checked on
> 2026-11-26/27. Items marked **(David)** are facts only David can confirm. Paste-ready answers for every form field are in
> docs/FRONTIER-CHECKLIST.md.

**Product:** replay8004, an open-source re-execution validator for the ERC-8004 Validation Registry on Celo, where no answer has been recorded since 2026-03-19.
**Lead applicant:** David Vega (Mexico). Software and data engineer, 13+ years (Python, SQL, AWS
Serverless, ETL, REST APIs). He has shipped two production Python + blockchain systems with
on-chain/off-chain verification and auditable logging, including an election-day integrity system.
**Links:** GitHub https://github.com/kuidsh/replay8004 (public before submitting; see docs/PHASE6-CHECKLIST.md) ·
KarmaGAP **(David: profile link)** · X **(David: @handle)**
**Tech category:** Verification and trust infrastructure (also agent-to-agent transactions).

## Required items
- **ERC-8004:** the validator itself is registered as **agent #10141** in the Celo mainnet IdentityRegistry
  `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`
  ([tx](https://celoscan.io/tx/0x213749ece02ac2aac6a00b656669c892fd23813363cd0bf754e38e4f91963604)), with an on-chain registration file.
- **Self Agent ID:** **#218** in SelfAgentRegistry `0xaC3DF9ABf80d0F5c020C06B04Cced27763355944`, owned by the validator
  address. Its operator is human-verified with a passport scan in Self.
- **Mainnet deployment:** the validator answers on the canonical ValidationRegistry
  `0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58` from address [`0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952`](https://celoscan.io/address/0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952),
  as a scheduled AWS Lambda that has answered every request within about a minute. No new contract is needed, so
  there is nothing new to audit.
- **Verifiable on-chain activity:** **5** `validationResponse` txs on Celo mainnet so far (scores 100, 0, 100, 100, 50:
  a true claim, a false one and an overstated one), all listed in docs/MAINNET-RUN.md and on
  [CeloScan](https://celoscan.io/address/0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952). Each has a public, hash-chained evidence bundle.
- **Open source:** Apache-2.0, 102 offline tests, CI on every push.

## Problem
Celo has ERC-8004 identity and reputation in use, but the **Validation Registry is dormant**: 39 txs in
total, the last on 2026-03-19, when one agent (#1870) sent 21 requests to 21 different
addresses in a single day and 17 answered. Nothing has been requested or answered since. A 2026 study of 173k ERC-8004 agents on
Ethereum, BSC and Base found that 98.7–100% of reputation feedback has neither payment proof nor
task linkage, and that sybil reviewers dominate the rest. Agents paying each other in stablecoins
on Celo have no neutral, machine-readable way to prove "I delivered / I paid / my number was right."

## Solution
An open validator anyone can name in a `validationRequest`. It re-executes the claim against Celo
state, and answers with a 0–100 score, a tag, and a keccak-committed, hash-chained evidence bundle
(S3 Object Lock) that anyone can recompute. Claim kinds: settled ERC-20 / x402 payments, balances
at a block, and arbitrary deterministic contract reads. A requester can see why a request failed:
invalid jobs get a 0 with the reason. Consumers gate on `getSummary(agentId, [validator], tag)`. It runs serverless for about US$0.45/month plus about 0.027 CELO of
gas per answer, with a daily answer cap per agent so it can't be drained.

## Milestones (ask: US$12,000)
| # | deliverable | weeks | amount |
|---|---|---|---|
| 0 | Contract signed (Prezenti's 20%) | — | US$2,400 |
| 1 | TypeScript client; `x402_settlement` checker; docs and a 5-minute quick-start; `celo-org/agent-skills` skill; 10 external agents onboarded. (Already done before applying: validator live on mainnet, ERC-8004 #10141, Self Agent ID #218.) | 5 | US$3,600 |
| 2 | Gate helper (viem + Solidity) for "only accept agents with a replay score ≥ N"; public status page (requests, answer latency, evidence chain); integrations with 2 Celo agent frameworks | 5 | US$3,000 |
| 3 | 100 agents or 2,000 mainnet validations; paid validation via x402 for high-volume users; usage report | 6 | US$3,000 |

## Activation path (first 10–100 agents)
1. A PR to `celo-org/agent-skills` adding a "request validation" skill next to the existing 8004 skill.
2. Direct outreach to builders on Celo Mainnet with ERC-8004 registrations and x402 activity (Aigora's 47 agents and 522 x402 calls show they exist).
3. Free validations for open-source agents; a single CLI call or one TypeScript function.

## Distribution and past execution
**(David to confirm)** Two production blockchain systems shipped; an election-day integrity system; analytics prototypes for the
Stellar Community Fund; agentguard, an open-source risk guard for AI agents on dYdX, live on testnet. For this project,
the validator went from a dormant registry to 5 live mainnet answers with public evidence in under a week (docs/MAINNET-RUN.md).

## Measurable outcomes
Agents requesting validations · mainnet `validationResponse` txs · median time to answer ·
share of requests that were invalid · evidence-chain verifications by third parties.

## Previous funding
**(David to confirm)** SCF #46 Build Award application pending (Stellar analytics); no other grants.
