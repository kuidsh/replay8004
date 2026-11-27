# Frontier form: field by field

Form: https://frontier.prezenti.xyz (fields read from the live form on 2026-11-27). Window closes **2026-12-29**; target
**2026-12-15**. **David** fills and submits the form; Claude never submits it.

## Before opening the form (all David)
- [ ] **Gas guard deployed** to `replay8004-mainnet` (the answers below describe the per-agent daily cap).
- [ ] **Phase 6 gate** ([PHASE6-CHECKLIST.md](PHASE6-CHECKLIST.md)): repo public, gitleaks clean on the full history,
      `setAgentURI` adds the repo link to agent #10141. The form asks "fully open source?" and links to GitHub.
- [ ] **KarmaGAP profile:** create it at https://gap.karmahq.xyz → "Create project": name replay8004, link the repo, add
      the milestones from [PROPOSAL.md](../PROPOSAL.md). Copy the profile link.
- [ ] **X handle:** the account you want reviewers to see.
- [ ] **Website:** the repo URL works. GitHub Pages for `index.html` is nicer, but first update its header line ("Web3
      lead 3 · prototype v0.1"), which is out of date.
- [ ] **Logo:** a square PNG (e.g. 512×512). The registration file's green check mark can be turned into one; ask Claude.
- [ ] **Read the grant policies:** https://prezenti.notion.site/Legal-Documents-c8d9e7f23a444414bcb6a17e32b16652.
      The form asks you to agree. KYC follows Prezenti's Canadian company rules.
- [ ] **Payout address:** a Celo address you control, **not** the validator wallet (its key is in AWS). For example, a
      new wallet from `scripts/new_wallets.py` kept offline, or a hardware wallet. Grants are paid in USDm on Celo.
- [ ] **Tax (Mexico):** the grant is income in MXN when received. Ask your contador about the regime (RESICO or
      actividad empresarial) and invoicing to a Canadian payer (see LAUNCH.md).

## The fields (paste-ready text)
| field | answer |
|---|---|
| Product name * | `replay8004` |
| Team name * | **(David)** e.g. `replay8004` or your name |
| Website * | `https://github.com/kuidsh/replay8004` (or the GitHub Pages URL) |
| X Handle * | **(David)** |
| KarmaGAP profile * | **(David)** link from the step above |
| Github * | `https://github.com/kuidsh/replay8004` |
| ERC-8004 registration * | `Agent #10141 in the Celo mainnet IdentityRegistry 0x8004A169FB4a3325136EB29fA0ceB6D2e539a432, owned by the validator 0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952 (tx 0x213749ece02ac2aac6a00b656669c892fd23813363cd0bf754e38e4f91963604).` |
| Fully open source? * | **Yes** (only once the repo is public) |
| Deployed on Celo mainnet * | **On Celo mainnet** |
| Self Agent ID * | **Already using Self ID** (mention #218 in "Describe your project") |
| Describe your project * | see A below |
| Infrastructure focus * (one line) | `A public validator other agents and marketplaces call: any agent names it in validationRequest and gets an on-chain score plus recomputable evidence; consumers gate on getSummary().` |
| Verifiable onchain activity * | see B below |
| Demo (optional) | `https://github.com/kuidsh/replay8004/blob/main/docs/MAINNET-RUN.md` |
| Activation path, first 10-100 * | see C below |
| Distribution strategy * | see D below |
| Worked with in the Celo ecosystem * | **(David)**: tick only formal engagements. Otherwise **None of the above** |
| Contribution to the ecosystem * | see E below |
| Technical credibility * | see F below |
| Additional information | `Costs: ~US$0.45/month on AWS plus ~0.027 CELO per answer. Daily answer cap per agent. No new contracts (nothing new to audit).` |
| File upload (optional) | (skip, or PROPOSAL.md as PDF) |
| Agree to the grant policies * | **(David)** Yes, after reading them |
| Name of lead applicant (KYC) * | **(David)** your legal name |
| Email of lead applicant * | **(David)** |
| Country company is registered | **(David)** Mexico |
| Tech category * | **AI** (the closest match; "Payments" is the alternative) |
| Your logo * | **(David)** the PNG from above |
| Grant L2 delivery address * | **(David)** the payout address from above |

### A. Describe your project
> replay8004 is the open-source validator for ERC-8004's Validation Registry on Celo, which has recorded no answers since
> March 2026. An agent names it in a `validationRequest` with a claim anyone can check: a settled ERC-20/x402 payment,
> a balance at a block, or a deterministic contract read. replay8004 re-executes the claim against Celo state and
> answers on-chain with a 0-100 score and a tag. It also publishes a hash-chained evidence bundle whose keccak256 is the
> on-chain `responseHash`. It is live on mainnet as ERC-8004 agent #10141, with Self Agent ID #218, and runs serverless
> on AWS. It never answers twice, never scores what it couldn't check, and caps answers per agent per day.

### B. Verifiable onchain activity
> Validator `0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952` on the canonical ValidationRegistry
> `0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58`. Five `validationResponse` txs, each with public evidence:
> 0x7acc6c0d170e36932f4f53a3d8acad437fc7f1549676b8701e82cbc9c5a7d27f (100), 0xbb91d72c5f9a4f5f818c080b186f15622310e50c46de8bff8bfbf096ec2b8626 (0, false claim),
> 0x8719a84b6af6f8dc4c8b7ebb5ed4153fe5631070f477def5e789a4036f509054 (100), 0x0f5a53294f66460d6a8b707744b8565580a162817cdc7f2e7e04b706f2e633e3 (100),
> 0xe485b247e76c93a25169b735d7896189d1b7295c3398ee0c8681ca506a74be5a (50, overstated claim). Full log with requests and payments:
> https://github.com/kuidsh/replay8004/blob/main/docs/MAINNET-RUN.md

Update the count and add new txs if there are more answers by submission day.

### C. Activation path (first 10-100 agents)
> 1) A `replay8004` skill in celo-org/agent-skills, next to the existing 8004 skill, so coding agents learn to request
> validations. 2) Direct outreach to Celo agents that already have ERC-8004 registrations or x402 traffic. I onboard
> each one by hand: their first validation is free and takes one command. 3) Free validations for open-source agents.
> Milestone 1 adds a TypeScript client and an `x402_settlement` checker, so x402 sellers can prove payment in one call.

### D. Distribution strategy
> Distribution goes through the tools agents already use: the agent-skills repo, the Celo forum and Discord, and the
> SDK quick-start. Each mainnet answer is public evidence that others can link to. **(David: add prior work where you
> shipped and got users, e.g. the election-day integrity system and agentguard. Name concrete numbers if you have them.)**

### E. Contribution to the ecosystem
> It brings the dormant third leg of ERC-8004 back on Celo. Reputation alone is weak: most feedback has no payment proof.
> replay8004 turns "I paid / I delivered / my number is right" into a neutral, machine-readable score that anyone can
> recompute. Marketplaces and x402 sellers can gate on `getSummary`. No new contracts are needed: it uses the canonical
> registries.

### F. Technical credibility
> Python, Apache-2.0, 102 offline tests and CI. Checked against the live chain: registry addresses, selectors and
> topics were verified against the deployed bytecode (docs/VERIFICATION.md). End-to-end runs on Celo Sepolia and Celo
> mainnet are in docs/TESTNET-RUN.md and docs/MAINNET-RUN.md. Engineering found and fixed through live tests: answers
> are exactly-once (the signed tx is saved before broadcast; done only once the chain shows our responseHash), pruned RPC
> receipts are never scored 0, there is a daily gas cap, and deploys use a least-privilege AWS user with a permissions
> boundary.

## After submitting (David)
- Keep the validator funded and the Lambda running. Reviewers will check the address.
- Season 2 decisions came 2-4 weeks after submission.
