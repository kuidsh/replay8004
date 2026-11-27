# Prezenti Season 3 Frontier application: replay8004

> Form: https://frontier.prezenti.xyz. Window closes **2026-12-29**; target **2026-12-15**. Every on-chain number here
> was read on 2026-11-27 (docs/MAINNET-STATUS.md). Paste-ready text for each form field: docs/FRONTIER-SUBMISSION.md.
> **[NEEDS DAVID]** marks what only David can supply or confirm.

**Product:** replay8004, an open-source re-execution validator for the ERC-8004 Validation Registry on Celo. It is live on
mainnet and has answered every request it has received.
**Lead applicant:** David Vega (Mexico). Software and data engineer, 13+ years (Python, SQL, AWS Serverless, ETL, REST
APIs). **[NEEDS DAVID: confirm]** He has shipped two production Python + blockchain systems with on-chain/off-chain
verification and auditable logging, including an election-day integrity system.
**Links:** GitHub https://github.com/kuidsh/replay8004 (**private today; made public before submitting**) ·
KarmaGAP **[NEEDS DAVID]** · X **[NEEDS DAVID]**
**Tech category:** verification and trust infrastructure for agent-to-agent payments.

## Required items

| item | status | evidence |
|---|---|---|
| ERC-8004 registration | the validator is **agent #10141** in the Celo mainnet IdentityRegistry `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`; `ownerOf(10141)` = the validator | [register tx](https://celoscan.io/tx/0x213749ece02ac2aac6a00b656669c892fd23813363cd0bf754e38e4f91963604) (block 83,797,743) |
| Self Agent ID | **#218** in SelfAgentRegistry `0xaC3DF9ABf80d0F5c020C06B04Cced27763355944` ("Self Agent ID", SAID); `ownerOf(218)` = the validator; operator verified with a passport scan | [registry](https://celoscan.io/address/0xaC3DF9ABf80d0F5c020C06B04Cced27763355944) |
| Mainnet deployment | validator [`0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952`](https://celoscan.io/address/0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952) answers on the ValidationRegistry `0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58` from an AWS Lambda that runs every minute (live since 2026-11-26; v0.5 since 2026-11-27) | docs/MAINNET-STATUS.md |
| Verifiable on-chain activity | **5 requests, 5 `validationResponse` txs**, 13–55 s from request to answer (median 30 s), 0.133 CELO of gas in total | table below |
| Open source | Apache-2.0; **185 Python tests** (11 on an in-process EVM, incl. conformance tests against the ERC-8004 registry sources) + **5 TypeScript** tests; CI on every push | https://github.com/kuidsh/replay8004 |

### The registry's status, stated plainly
The ERC-8004 Validation Registry is still a **preview**. The erc-8004-contracts README lists only the Identity and
Reputation registries and says the validation part of the spec will be revised; Celopedia gives no Celo Validation
Registry address. The address replay8004 uses, `0x8004Cc84…AB58`, comes from that repo's deployment script
(`scripts/addresses.ts`). replay8004 checks it on-chain before it loads its key, on every run (`replay8004 doctor`):
`getIdentityRegistry()` must return Celo's Identity Registry. Today it does, and `getVersion()` is `2.0.0`. We have asked the
maintainers whether this is the canonical Celo deployment and whether a redeploy is planned
**[NEEDS DAVID: issue link once opened, and their answer]**. If the registry is redeployed, replay8004 moves with it: the
address is one config value, and the job, evidence and gate code don't depend on it. Milestone 1 covers that migration if
it happens.

### On-chain activity (Celo mainnet, all on 2026-11-26)
Requester: test agent #10143 (owner `0x070a5F24851DD4D0200EBd4064F0914F92998647`), run by the operator to exercise a true,
a false and an overstated payment claim. There are no external users yet; that is milestone 1.

| # | request tx | answer tx | time | score | evidence |
|---|---|---|---|---|---|
| 1 | [0x02090b85…86f1](https://celoscan.io/tx/0x02090b85eb285eb96aaf4a0f1070d1a501bd9d63f6b458719c3076054c5a86f1) | [0x7acc6c0d…d27f](https://celoscan.io/tx/0x7acc6c0d170e36932f4f53a3d8acad437fc7f1549676b8701e82cbc9c5a7d27f) | 30 s | 100 | [bundle](https://replay8004-mainnet-evidencebucket-exgfx3xqkhfr.s3.us-east-1.amazonaws.com/evidence/0x4a5795f367e0ecf31add8c0f09c30d7b70e2daa81afcc547c8670580936ada15.json) |
| 2 | [0x5c7bce07…9811](https://celoscan.io/tx/0x5c7bce07dedd3d8c3ee08da070fd9832e3dc3c71f2613317d64ee27c2acf9811) | [0xbb91d72c…8626](https://celoscan.io/tx/0xbb91d72c5f9a4f5f818c080b186f15622310e50c46de8bff8bfbf096ec2b8626) | 22 s | 0 (false claim) | [bundle](https://replay8004-mainnet-evidencebucket-exgfx3xqkhfr.s3.us-east-1.amazonaws.com/evidence/0x449960bb103c3556a9ba1ece244a208e0b89cd4ae61200da4e53fa229353e55a.json) |
| 3 | [0xea21f51b…7265](https://celoscan.io/tx/0xea21f51b6e792d743a1f443c589f6a8f33a483f0812ab1f6f33cb6a35aad7265) | [0x8719a84b…9054](https://celoscan.io/tx/0x8719a84b6af6f8dc4c8b7ebb5ed4153fe5631070f477def5e789a4036f509054) | 34 s | 100 | [bundle](https://replay8004-mainnet-evidencebucket-exgfx3xqkhfr.s3.us-east-1.amazonaws.com/evidence/0x23e65532bedeef67469f96bf4d89267c38e64ceae7add9751f39a566e3b61341.json) |
| 4 | [0x0213eb68…30a3](https://celoscan.io/tx/0x0213eb68e55ae8e41e76eeca86e424c5c79e981720003bc427bdadfa9c9630a3) | [0x0f5a5329…33e3](https://celoscan.io/tx/0x0f5a53294f66460d6a8b707744b8565580a162817cdc7f2e7e04b706f2e633e3) | 13 s | 100 | [bundle](https://replay8004-mainnet-evidencebucket-exgfx3xqkhfr.s3.us-east-1.amazonaws.com/evidence/0xaaf6c203afb74c01e74549997bc173d6ec8051bf8b6f1596fab99d35eb2d810f.json) |
| 5 | [0x46c3e570…dd66](https://celoscan.io/tx/0x46c3e5708c7ac74fbd504bd93a7eacd92314d4092c62aa484577b0f5cc72dd66) | [0xe485b247…be5a](https://celoscan.io/tx/0xe485b247e76c93a25169b735d7896189d1b7295c3398ee0c8681ca506a74be5a) | 55 s | 50 (overstated) | [bundle](https://replay8004-mainnet-evidencebucket-exgfx3xqkhfr.s3.us-east-1.amazonaws.com/evidence/0xe7a4c7b2de516aeccb53ad75eab486d0a737c1ca36206a361bd401cdd68bbcf9.json) |

Anyone can check an answer end to end: keccak256 of the public bundle equals the `responseHash` on-chain, and the 5 bundles
form one hash chain (`replay8004 verify-evidence`).

## Problem
Celo has ERC-8004 identity and reputation in use, but before replay8004 the **Validation Registry was dormant**: 39 txs
in total, the last on 2026-03-19, when one agent (#1870) sent 21 requests to 21 different addresses in a single day and
17 answered. A 2026 study of 173k ERC-8004 agents on Ethereum, BSC and Base found that 98.7–100% of reputation feedback has
neither payment proof nor task linkage, and that sybil reviewers dominate the rest. Agents paying each other in
stablecoins on Celo have no neutral, machine-readable way to prove "I paid / I delivered / my number was right".

## Solution
A public validator anyone can name in a `validationRequest`. It re-executes the claim against Celo state and answers with
a 0–100 score, a tag, and a keccak-committed, hash-chained evidence bundle (S3 Object Lock) that anyone can recompute.
Claim kinds: settled ERC-20 payments, **x402 receipts** (`x402_settlement`: the PaymentRequirements and SettlementResponse
are checked against the on-chain Transfer and the EIP-3009 nonce), balances at a block, and deterministic contract reads.
Invalid jobs get a 0 with the reason; claims it can't check yet (too few confirmations, a pruned receipt) stay pending
and are never scored. It never answers a request twice, and it caps answers at 20 a day and 5 per agent so nobody can
drain it. Measured cost: ≈ 0.027 CELO (≈ US$0.0016, CeloScan) per answer plus ≈ US$0.45/month on AWS.

For consumers there is `getSummary(agentId, [validator], tag)`, a Solidity gate (`ReplayGate.sol`: `onlyValidatedAgent`,
`onlyValidatedClaim`) with the same rules in Python and TypeScript, a read-only MCP server, an Agent Skill, a TypeScript
client (`@replay8004/client`) and a status page rebuilt from the public evidence alone. All of it is built and tested
(v0.5, deployed 2026-11-27); the TypeScript client and the PyPI package are not published yet.

## Sustainability: paid mode (built, off)
After the grant, x402 **credit packs** pay for gas and AWS: 5 USDC for 250 validations, 40 USDC for 2,500. Packs, not
per-call payments, because Celo's facilitator charges gas plus 0.3% per settlement (US$0.004 per tx in its config):
≈ 20% of a US$0.02 call, but 0.4% of a 5 USDC pack. Estimated margin ≈ US$4.55 per starter pack; one pack a month covers
AWS. **25 free validations per agent per month** and an open-source allowlist keep it a public good, and a request that
isn't paid for is held, never scored 0. The paywall re-checks every settlement on-chain with replay8004's own
`x402_settlement` checker before crediting, and holds no key that can move funds. Paid mode is built and tested offline
(docs/PAID.md). It is **off** (`PaidMode=0`), and the deployment template refuses to turn it on for mainnet until a
Sepolia purchase has worked end to end. No buyer has been asked yet.

## Milestones (ask: US$12,000)
| # | deliverable | weeks | amount |
|---|---|---|---|
| 0 | Contract signed (Prezenti's 20%) | — | US$2,400 |
| 1 | `@replay8004/client` on npm and `replay8004` on PyPI; 5-minute quick-start; the Validation Registry documented in Celo's `8004` agent skill (PR ready); registry migration if it is redeployed; **10 external agents** validated | 5 | US$3,600 |
| 2 | Status page published; `ReplayGate` contract package published; integrations with 2 Celo agent frameworks; first outside contract or marketplace gating on replay8004 | 5 | US$3,000 |
| 3 | **100 agents or 2,000 mainnet validations**; paid mode on (Sepolia first, then mainnet); public usage report | 6 | US$3,000 |

Already done before applying: the validator live on mainnet with 5 answers, ERC-8004 #10141, Self Agent ID #218, and
v0.5 deployed (x402 receipts, the on-chain `doctor` check, request-block evidence); the TS client, the gate contract, the
MCP server, the skill PR and paid mode are built and tested.

## Activation path (first 10–100 agents)
1. A PR to `celo-org/agent-skills` that documents the Validation Registry in Celo's official `8004` skill (today it
   lists no functions), plus replay8004's own Agent Skill and MCP server, so coding agents learn to request validations.
2. Direct outreach to Celo mainnet agents whose registration files already advertise A2A, MCP or x402 endpoints
   (shortlist in docs/OUTREACH.md). Their first validations are free, onboarded by hand.
3. Free validations for open-source agents: one CLI call, one TypeScript function or one MCP tool.

## Distribution and past execution
**[NEEDS DAVID: confirm and add numbers]** Two production blockchain systems shipped; an election-day integrity system;
analytics prototypes for the Stellar Community Fund; agentguard, an open-source risk guard for AI agents on dYdX, live
on testnet. For this project, the validator went from a dormant registry to 5 live mainnet answers with public evidence
in under a week (docs/MAINNET-RUN.md).

## Measurable outcomes
Agents requesting validations · mainnet `validationResponse` txs · median time to answer (now 30 s) · share of invalid
requests · third-party evidence verifications · credit packs sold.

## Previous funding
**[NEEDS DAVID: confirm]** SCF #46 Build Award application pending (Stellar analytics); no other grants.
