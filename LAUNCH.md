# Launch plan: steps only David can do

> **2026-11-27:** steps 1–7 are mostly done; current status, evidence and the remaining David-only steps are in
> [docs/LAUNCH-STATUS.md](docs/LAUNCH-STATUS.md). This table is kept as the original plan.

These need a person: a passport scan, real funds, accepting terms, or posting publicly. Claude
cannot do them. Total cost ≈ US$3–15.

| # | step | why | cost | time |
|---|---|---|---|---|
| 1 | Push to the **private** GitHub repo `replay8004` (CI runs pytest). Make it public before step 9: see docs/PHASE6-CHECKLIST.md | Frontier asks for GitHub and open source | free | 5 min |
| 2 | Create a **validator-only wallet** (e.g. `cast wallet new`, or MetaMask). Store the key in a password manager; never reuse a wallet that holds savings | the validator signs `validationResponse` | free | 5 min |
| 3 | **Celo Sepolia test**: get faucet CELO (faucet.celo.org may need a sign-in), run `replay8004 run --validator <addr> --send`, then send one `validationRequest` from a test agent and confirm the answer on Blockscout | prove the flow before mainnet | free | 30 min |
| 4 | **Self Agent ID** (`npm i -g @selfxyz/agent-sdk`, `self-agent register init --network mainnet`, scan your passport in the Self app) | Frontier requirement | free | 15 min |
| 5 | **Register the validator as an ERC-8004 agent** on Celo mainnet (Identity Registry `0x8004A169…a432`) with a registration JSON that describes the validator | Frontier requirement | < US$0.01 gas | 10 min |
| 6 | **Buy ≈ 50 CELO** on a regulated exchange (e.g. Bitso) and send it to the validator wallet | gas for mainnet answers | ≈ US$3 | 10 min |
| 7 | **Run on mainnet** (`REPLAY8004_ALLOW_MAINNET=1 … --send`, locally or via `sam deploy` in your AWS account) and do 5–10 real validations: validate your own test agent's payments first, then outside agents | "verifiable on-chain activity" | gas | 1 h |
| 8 | **Post** in the Celo forum / Discord (AI agents channel) offering free validations; open the `celo-org/agent-skills` PR | activation path and traction | free | 1 h |
| 9 | **Fill the Frontier form** with PROPOSAL.md before **2026-12-29** (target: 2026-12-15). Accept Prezenti's grant policies; KYC; give a Celo address for USDm | the grant | free | 45 min |

Mexico: a grant received in USDm is taxable income in MXN when received. Selling it later is an
*enajenación*. Running a validator is not a regulated financial activity, but confirm the regime
(RESICO or actividad empresarial) and invoicing to a Canadian payer with a contador.
