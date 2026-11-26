# Mainnet run: Celo mainnet (chain 42220)

Every mainnet transaction made for replay8004, with a running gas total. The cap is **50 CELO** in total; work
stops before it would be passed. Each transaction is listed only after its receipt was read back.

| role | address / id |
|---|---|
| validator | [`0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952`](https://celoscan.io/address/0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952) |
| validator as ERC-8004 agent | **#10141** in the IdentityRegistry `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |
| validator's Self Agent ID | **#218** in SelfAgentRegistry `0xaC3DF9ABf80d0F5c020C06B04Cced27763355944` (proof of human, registered by David) |
| ValidationRegistry | `0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58` |

Funding: 16.879989121819605 CELO from an exchange, in tx
[`0xd4afad7c…20ba`](https://celoscan.io/tx/0xd4afad7c9922640da54535e1b76c192aae276b2977ab01fa79162f42c75b20ba)
(2026-11-26 09:00 UTC).

## Transactions
| # | date (UTC) | step | from | tx | block | gas used | fee (CELO) | total gas (CELO) |
|---|---|---|---|---|---|---|---|---|
| 1 | 2026-11-26 | `register(agentURI)`: validator becomes agent #10141 (on-chain `data:` registration file, 917 bytes) | validator | [`0x213749ec…3604`](https://celoscan.io/tx/0x213749ece02ac2aac6a00b656669c892fd23813363cd0bf754e38e4f91963604) | 83,797,743 | 799,700 | 0.16193925 | **0.16193925** / 50 |
| 2 | 2026-11-26 | fund the test-agent wallet: CELO `transfer` of 3 CELO, validator → `0x070a5F24851DD4D0200EBd4064F0914F92998647` | validator | [`0x6527b43b…7dc6`](https://celoscan.io/tx/0x6527b43b6f7522e38f66eda564b84612dae9d05768ab78c998bd612740127dc6) | 83,800,463 | 39,408 | 0.00798012 | **0.16991937** / 50 |

The total counts gas only. The 3 CELO moved in #2 stay within the project and are not spent.

## Validator service on AWS
On 2026-11-26, after David's "go mainnet", stack `replay8004-mainnet` was deployed in us-east-1. It scans from block
83,798,923, keeps evidence locked for 365 days, uses the same tags and permissions boundary as Sepolia, and its
schedule doesn't retry failed runs.
1. **Dry run first:** both roles carry `replay8004-boundary`. Two runs scanned mainnet with 0 errors. A logged-out GET
   of a test file under `evidence/` returned 200 with identical bytes, while the bucket listing and anything outside
   `evidence/` returned 403. The test file was then deleted.
2. **Then live** (`DryRun=0`, key from Secrets Manager `replay8004/mainnet-validator`): the first live runs show
   `dryRun: false` and 0 errors. The Lambda only starts if the key belongs to `ValidatorAddress`, so the key is right.
   The validator nonce stayed at 1: nothing is sent until a `validationRequest` names this validator.

Evidence for mainnet answers is served from
`https://replay8004-mainnet-evidencebucket-exgfx3xqkhfr.s3.us-east-1.amazonaws.com/evidence/<requestHash>.json`.

## Checks after each step
- **#1:** the receipt has status 1 and one `Registered` event for agent 10141. `ownerOf(10141)` and
  `getAgentWallet(10141)` are both the validator. `tokenURI(10141)` is byte for byte the `data:` URI David approved
  (664 bytes of JSON, from `examples/registration.json`). The registration has no repo link and no `registrations`
  list yet; both are added with `setAgentURI` in Phase 6 (docs/PHASE6-CHECKLIST.md).
- **#2:** status 1, with one CELO `Transfer` log: validator → test-agent wallet, exactly 3.0 CELO. Balances afterwards:
  validator 13.710069751819605 CELO, test-agent wallet 3.0 CELO.
