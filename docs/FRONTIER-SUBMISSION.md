# Frontier submission: paste field by field

Form: https://frontier.prezenti.xyz (fields as read from the live form on 2026-11-27; re-check them on the day).
Window closes **2026-12-29**; target **2026-12-15**. David fills in and submits the form; nothing here has been submitted.
Facts: docs/MAINNET-STATUS.md (2026-11-27). **[NEEDS DAVID]** = only David can fill it in.

## Do these first (all David, details and costs in docs/LAUNCH-STATUS.md)
1. ~~Deploy v0.5~~: done 2026-11-27 (both stacks), so x402 receipts and the `doctor` check below are live.
2. Make the repo public (the form asks "fully open source?" and links to GitHub).
3. Open the erc-8004-contracts issue (docs/OUTREACH.md §4) and paste its link into B and the proposal.
4. KarmaGAP profile, X handle, logo, payout address, read the grant policies.
5. On the day, re-count answers (`docs/MAINNET-STATUS.md` method) and update B.

## Fields

| field | paste this |
|---|---|
| Product name * | `replay8004` |
| Team name * | **[NEEDS DAVID]** (e.g. `replay8004`, or your name) |
| Website * | `https://kuidsh.github.io/replay8004/` |
| X Handle * | **[NEEDS DAVID]** |
| KarmaGAP profile * | **[NEEDS DAVID]** profile link |
| Github * | `https://github.com/kuidsh/replay8004` (**public first**) |
| ERC-8004 registration * | `Agent #10141 in the Celo mainnet IdentityRegistry 0x8004A169FB4a3325136EB29fA0ceB6D2e539a432, owned by the validator 0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952 (register tx 0x213749ece02ac2aac6a00b656669c892fd23813363cd0bf754e38e4f91963604).` |
| Fully open source? * | **Yes** (only after the repo is public) |
| Deployed on Celo mainnet * | **On Celo mainnet** |
| Self Agent ID * | **Already using Self ID** (#218, also named in A) |
| Describe your project * | text A |
| Infrastructure focus * (one line) | `A public validator for ERC-8004 on Celo: any agent names it in validationRequest and gets an on-chain 0-100 score plus recomputable evidence; contracts and marketplaces gate on it.` |
| Verifiable onchain activity * | text B |
| Demo (optional) | `https://replay8004-mainnet-evidencebucket-exgfx3xqkhfr.s3.us-east-1.amazonaws.com/evidence/status/index.html` (live status page; full table in docs/MAINNET-STATUS.md) |
| Activation path, first 10-100 * | text C |
| Distribution strategy * | text D |
| Worked with in the Celo ecosystem * | **[NEEDS DAVID]**: tick only formal engagements, otherwise **None of the above** |
| Contribution to the ecosystem * | text E |
| Technical credibility * | text F |
| Additional information | text G |
| File upload (optional) | skip, or PROPOSAL.md exported as PDF |
| Agree to the grant policies * | **[NEEDS DAVID]** after reading https://prezenti.notion.site/Legal-Documents-c8d9e7f23a444414bcb6a17e32b16652 |
| Name of lead applicant (KYC) * | **[NEEDS DAVID]** legal name |
| Email of lead applicant * | **[NEEDS DAVID]** |
| Country company is registered | **[NEEDS DAVID]** (Mexico) |
| Tech category * | **AI** (closest match; "Payments" is the alternative) |
| Your logo * | **[NEEDS DAVID]** square PNG, e.g. 512×512 |
| Grant L2 delivery address * | **[NEEDS DAVID]** a Celo address you control for USDm, **not** the validator wallet (its key is in AWS) |

### A. Describe your project
> replay8004 is an open-source re-execution validator for ERC-8004's Validation Registry on Celo. An agent names it in a
> `validationRequest` with a claim anyone can check: a settled ERC-20 payment, an x402 receipt, a balance at a block, or
> a deterministic contract read. replay8004 re-executes the claim against Celo state and answers on-chain with a 0-100
> score and a tag, plus a hash-chained evidence bundle whose keccak256 is the on-chain responseHash, so anyone can
> recompute it. It is live on Celo mainnet as ERC-8004 agent #10141 with Self Agent ID #218, running serverless on AWS.
> It never answers twice, never scores what it couldn't check, and caps answers per agent per day. Consumers get a
> Solidity gate, a TypeScript client, an MCP server and an Agent Skill. After the grant, x402 credit packs (built,
> switched off) pay for gas, with 25 free validations per agent per month.

### B. Verifiable onchain activity
> Validator 0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952 answers on the ERC-8004 ValidationRegistry
> 0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58 (address from erc-8004-contracts scripts/addresses.ts; the validation spec is
> still a preview, so replay8004 checks getIdentityRegistry() on-chain before every run. Question to the maintainers:
> **[NEEDS DAVID: issue link]**). 5 requests, 5 validationResponse txs, 13-55 s from request to answer:
> 0x7acc6c0d170e36932f4f53a3d8acad437fc7f1549676b8701e82cbc9c5a7d27f (100),
> 0xbb91d72c5f9a4f5f818c080b186f15622310e50c46de8bff8bfbf096ec2b8626 (0, false claim),
> 0x8719a84b6af6f8dc4c8b7ebb5ed4153fe5631070f477def5e789a4036f509054 (100),
> 0x0f5a53294f66460d6a8b707744b8565580a162817cdc7f2e7e04b706f2e633e3 (100),
> 0xe485b247e76c93a25169b735d7896189d1b7295c3398ee0c8681ca506a74be5a (50, overstated claim).
> Each has a public evidence bundle whose keccak256 equals the on-chain responseHash. Requests so far come from my own
> test agent #10143; external agents are milestone 1. Full table: https://github.com/kuidsh/replay8004/blob/main/docs/MAINNET-STATUS.md

(If there are more answers on submission day, update the count and add the txs.)

### C. Activation path (first 10-100 agents)
> 1) A ready PR to celo-org/agent-skills that documents the Validation Registry in Celo's official 8004 skill (it lists
> no functions today), plus replay8004's own Agent Skill and a read-only MCP server, so coding agents learn to request
> and check validations. 2) Direct, hand-held onboarding of Celo mainnet agents whose ERC-8004 registration files already
> advertise A2A, MCP or x402 endpoints (I have a shortlist from the Identity Registry). Their first validations are
> free and take one command or one TypeScript call. 3) Free validations for open-source agents, permanently (allowlist).
> x402 sellers can prove a payment settled with the x402_settlement checker.

### D. Distribution strategy
> Distribution goes through the tools agents already use: Celo's agent-skills repo, an MCP server, a TypeScript client
> on npm (@replay8004/client) and a Python package on PyPI (replay8004), both published, plus the Celo forum and Discord. Every answer is public evidence that others can
> link to, and a public status page is rebuilt from that evidence alone. **[NEEDS DAVID: prior work where you shipped
> and got users, e.g. the election-day integrity system and agentguard, with concrete numbers]**

### E. Contribution to the ecosystem
> It brings the dormant third leg of ERC-8004 back on Celo: before replay8004 the Validation Registry had 39 txs, the
> last in March 2026. Reputation alone is weak; most feedback has no payment proof. replay8004 turns "I paid / I
> delivered / my number is right" into a neutral, machine-readable score anyone can recompute. Marketplaces and x402
> sellers can gate on getSummary or inherit ReplayGate.sol. It adds no new registry contracts, and the PR to Celo's
> 8004 skill documents the Validation Registry for every builder, not only replay8004 users.

### F. Technical credibility
> Python + TypeScript, Apache-2.0. 185 Python tests (11 on an in-process EVM, including conformance tests against the
> ERC-8004 registry sources) and 5 TypeScript tests (job bytes match Python byte for byte), CI on every push. Checked
> against the live chain: registry addresses, selectors and topics verified on-chain (docs/VERIFICATION.md); end-to-end
> runs on Celo Sepolia and mainnet. Engineering found through live runs: answers are exactly-once (the signed tx is
> saved before broadcast and is done only when the chain shows our responseHash), pruned RPC receipts are never scored
> 0, a daily gas cap, state migrations that never reset the evidence chain, and least-privilege AWS deploys with a
> permissions boundary.

### G. Additional information
> Costs: ≈ 0.027 CELO (≈ US$0.0016) per answer and ≈ US$0.45/month on AWS. Paid mode (x402 credit packs, 5 USDC = 250
> validations) is built and tested but off, Sepolia first. The ValidationRegistry is a preview; if it is redeployed,
> replay8004 moves with it (one config value).

## After submitting (David)
- Keep the validator funded (13.62 CELO on 2026-11-27 ≈ 500 answers) and the stack running; reviewers will check the address.
- Season 2 decisions came 2-4 weeks after submission.
