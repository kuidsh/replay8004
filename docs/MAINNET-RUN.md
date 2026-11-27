# Mainnet run: Celo mainnet (chain 42220)

Every mainnet transaction made for replay8004, with a running gas total. The cap is **50 CELO** in total; work
stops before it would be passed. Each transaction is listed only after its receipt was read back.

| role | address / id |
|---|---|
| validator | [`0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952`](https://celoscan.io/address/0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952) |
| validator as ERC-8004 agent | **#10141** in the IdentityRegistry `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |
| validator's Self Agent ID | **#218** in SelfAgentRegistry `0xaC3DF9ABf80d0F5c020C06B04Cced27763355944` (proof of human, registered by David) |
| ValidationRegistry | `0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58` |
| test-agent wallet | [`0x070a5F24851DD4D0200EBd4064F0914F92998647`](https://celoscan.io/address/0x070a5F24851DD4D0200EBd4064F0914F92998647), owns test agent **#10143** |

Funding: 16.879989121819605 CELO from an exchange, in tx
[`0xd4afad7c…20ba`](https://celoscan.io/tx/0xd4afad7c9922640da54535e1b76c192aae276b2977ab01fa79162f42c75b20ba)
(2026-11-26 09:00 UTC).

## Transactions
| # | date (UTC) | step | from | tx | block | gas used | fee (CELO) | total gas (CELO) |
|---|---|---|---|---|---|---|---|---|
| 1 | 2026-11-26 | `register(agentURI)`: validator becomes agent #10141 (on-chain `data:` registration file, 917 bytes) | validator | [`0x213749ec…3604`](https://celoscan.io/tx/0x213749ece02ac2aac6a00b656669c892fd23813363cd0bf754e38e4f91963604) | 83,797,743 | 799,700 | 0.16193925 | **0.16193925** / 50 |
| 2 | 2026-11-26 | fund the test-agent wallet: CELO `transfer` of 3 CELO, validator → `0x070a5F24851DD4D0200EBd4064F0914F92998647` | validator | [`0x6527b43b…7dc6`](https://celoscan.io/tx/0x6527b43b6f7522e38f66eda564b84612dae9d05768ab78c998bd612740127dc6) | 83,800,463 | 39,408 | 0.00798012 | **0.16991937** / 50 |
| 3 | 2026-11-26 | `register(agentURI)`: mainnet test agent #10143, owned by the test-agent wallet | test agent | [`0x39d3719e…f8b6`](https://celoscan.io/tx/0x39d3719e11abe7b8a93fee16a12c63623f26863663ffe63df49ab1040a8ff8b6) | 83,800,669 | 430,955 | 0.08726839 | **0.25718776** / 50 |
| 4 | 2026-11-26 | validation 1, the payment: test agent pays the validator 0.01 CELO (CELO `transfer`) | test agent | [`0x9918c97f…5bb7`](https://celoscan.io/tx/0x9918c97f454753411d2ebe27c1d7263855ec82eae7c76bbdf020ee216b045bb7) | 83,800,861 | 39,396 | 0.00797769 | **0.26516545** / 50 |
| 5 | 2026-11-26 | validation 1, the request: `validationRequest` by agent #10143 (job [`mainnet/job-4a5795f3.json`](mainnet/job-4a5795f3.json), requestHash `0x4a5795f3…da15`) | test agent | [`0x02090b85…86f1`](https://celoscan.io/tx/0x02090b85eb285eb96aaf4a0f1070d1a501bd9d63f6b458719c3076054c5a86f1) | 83,800,939 | 222,530 | 0.04506233 | **0.31022778** / 50 |
| 6 | 2026-11-26 | validation 1, **the answer: score 100**, `replay:erc20_transfer`, sent by the AWS Lambda on its own | validator | [`0x7acc6c0d…d27f`](https://celoscan.io/tx/0x7acc6c0d170e36932f4f53a3d8acad437fc7f1549676b8701e82cbc9c5a7d27f) | 83,800,969 | 135,354 | 0.02740919 | **0.33763696** / 50 |
| 7 | 2026-11-26 | validation 2, the payment: 0.02 CELO, test agent → validator | test agent | [`0x6165257d…dd37`](https://celoscan.io/tx/0x6165257d46f98af3b2ead33c1a0849a8cdf4f81330e510d3de132be12202dd37) | 83,801,267 | 39,396 | 0.00797769 | **0.34561465** / 50 |
| 8 | 2026-11-26 | validation 3, the payment: 0.005 CELO, test agent → validator | test agent | [`0x59728986…facc`](https://celoscan.io/tx/0x597289861ea2e781489c128bc0d180ca31db999cd83cae35ed6d89be6e9afacc) | 83,801,278 | 39,408 | 0.00798012 | **0.35359477** / 50 |
| 9 | 2026-11-26 | validation 5, the payment: 0.01 CELO, test agent → validator (its request will claim 0.02) | test agent | [`0x6b1a4325…6318`](https://celoscan.io/tx/0x6b1a43253faeaa8d036ced5d9b8505033d95554a5f086ec37470b8bc2a356318) | 83,801,292 | 39,396 | 0.00797769 | **0.36157246** / 50 |
| 10 | 2026-11-26 | validation 4, the request, **deliberately wrong**: claims that validation 1's payment went to `0x…dEaD` (job [`mainnet/job-449960bb.json`](mainnet/job-449960bb.json)) | test agent | [`0x5c7bce07…9811`](https://celoscan.io/tx/0x5c7bce07dedd3d8c3ee08da070fd9832e3dc3c71f2613317d64ee27c2acf9811) | 83,801,307 | 190,562 | 0.03858881 | **0.40016127** / 50 |
| 11 | 2026-11-26 | validation 4, **the answer: score 0**, `replay:erc20_transfer` ("no matching Transfer log"), sent by the Lambda | validator | [`0xbb91d72c…8626`](https://celoscan.io/tx/0xbb91d72c5f9a4f5f818c080b186f15622310e50c46de8bff8bfbf096ec2b8626) | 83,801,329 | 115,442 | 0.02337701 | **0.42353827** / 50 |
| 12 | 2026-11-26 | validation 2, the request (job [`mainnet/job-23e65532.json`](mainnet/job-23e65532.json)) | test agent | [`0xea21f51b…7265`](https://celoscan.io/tx/0xea21f51b6e792d743a1f443c589f6a8f33a483f0812ab1f6f33cb6a35aad7265) | 83,804,835 | 188,330 | 0.03813683 | **0.46167510** / 50 |
| 13 | 2026-11-26 | validation 3, the request (job [`mainnet/job-aaf6c203.json`](mainnet/job-aaf6c203.json)) | test agent | [`0x0213eb68…30a3`](https://celoscan.io/tx/0x0213eb68e55ae8e41e76eeca86e424c5c79e981720003bc427bdadfa9c9630a3) | 83,804,858 | 188,282 | 0.03812711 | **0.49980220** / 50 |
| 14 | 2026-11-26 | validation 2, **the answer: score 100** | validator | [`0x8719a84b…9054`](https://celoscan.io/tx/0x8719a84b6af6f8dc4c8b7ebb5ed4153fe5631070f477def5e789a4036f509054) | 83,804,869 | 135,366 | 0.02741162 | **0.52721382** / 50 |
| 15 | 2026-11-26 | validation 3, **the answer: score 100** | validator | [`0x0f5a5329…33e3`](https://celoscan.io/tx/0x0f5a53294f66460d6a8b707744b8565580a162817cdc7f2e7e04b706f2e633e3) | 83,804,871 | 135,366 | 0.02741162 | **0.55462543** / 50 |
| 16 | 2026-11-26 | validation 5, the request: claims 0.02 for a 0.01 payment (job [`mainnet/job-e7a4c7b2.json`](mainnet/job-e7a4c7b2.json)) | test agent | [`0x46c3e570…dd66`](https://celoscan.io/tx/0x46c3e5708c7ac74fbd504bd93a7eacd92314d4092c62aa484577b0f5cc72dd66) | 83,804,875 | 189,890 | 0.03845273 | **0.59307816** / 50 |
| 17 | 2026-11-26 | validation 5, **the answer: score 50** ("transferred 0.01 < claimed 0.02") | validator | [`0xe485b247…be5a`](https://celoscan.io/tx/0xe485b247e76c93a25169b735d7896189d1b7295c3398ee0c8681ca506a74be5a) | 83,804,930 | 135,366 | 0.02741162 | **0.62048977** / 50 |

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
- **#3:** status 1, with one `Registered` event for agent 10143. `ownerOf(10143)` is the test-agent wallet, and
  `tokenURI(10143)` is the approved `data:` URI (266 bytes of JSON: name "replay8004 mainnet test agent").
- **#4:** status 1, with one CELO `Transfer` log (test agent → validator, 0.01 CELO). The local re-check of the claim
  for validation 1 scored 100 (15 confirmations) before the request was sent.
- **#5:** status 1, with a `ValidationRequest` event whose requestHash matches the job file. The file saved by the
  script hashes to that requestHash.
- **#6 (the first replay8004 answer on mainnet):** the Lambda answered 30 blocks after the request (about a minute)
  and confirmed it on its next run. `getValidationStatus` gives validator `0xd2d6…5952`, agent 10143, response 100,
  tag `replay:erc20_transfer`, responseHash `0x6932b3cddd92e4594560be5067dbb5c1b88eca005ce5b486572dc699156af28c`.
  The evidence at `https://replay8004-mainnet-evidencebucket-exgfx3xqkhfr.s3.us-east-1.amazonaws.com/evidence/0x4a5795f3….json`
  returned HTTP 200 to a logged-out GET (1,735 bytes). Its keccak256 equals the on-chain responseHash and the one in the
  answer's calldata. The bundle is seq 1 of the mainnet chain ("1 bundles, chain intact"); a copy is in
  [`mainnet/evidence/`](mainnet/evidence/). Worker state: 1 done, 0 in flight, pending or failed. The validator nonce
  is 3 (registration, funding, this answer), so it answered once. The Lambda logs show 0 errors.
- **#7-#9:** status 1, each with one CELO `Transfer` log (0.02, 0.005 and 0.01 CELO to the validator).
- **#10-#11 (validation 4, the deliberate failure):** the request's event matches the job file
  (requestHash `0x449960bb…e55a`). The local re-check scored 0 before sending. The Lambda answered 22 blocks later:
  `getValidationStatus` gives response 0, tag `replay:erc20_transfer`, and the finding is "no matching Transfer log
  (token / from / to)". The evidence (HTTP 200 logged out, 1,855 bytes) hashes to responseHash
  `0xde5cd32c587cbd5e9c6f2f23c1bfb1bcff5ad74304547adb702b551d8683c5f2`. It is seq 2 and its `prev` is validation 1's
  hash: "2 bundles, chain intact". Worker state: 2 done, 0 in flight, pending or failed. The validator nonce is 4.
- **#12-#17:** every request's event matches its job file. The Lambda answered each request within 1-2 runs, and every
  answer's evidence returned HTTP 200 logged out and hashed to its on-chain responseHash. After the batch:
  `verify-evidence docs/mainnet/evidence` reports "5 bundles, chain intact". Worker state: 5 done, 0 in flight, pending
  or failed. The validator nonce is 7 (registration, funding, 5 answers): each request was answered once. The Lambda
  logs show 0 errors.

## Summary of the first batch (5 validations by the AWS validator)
| validation | claim by agent #10143 | answer | requestHash | evidence (seq) |
|---|---|---|---|---|
| 1 | paid ≥ 0.01 CELO to the validator in `0x9918c97f…` (it did) | **100** | `0x4a5795f3…` | 1 |
| 4 | paid ≥ 0.01 CELO to `0x…dEaD` in `0x9918c97f…` (deliberately false) | **0**: no matching Transfer log | `0x449960bb…` | 2 |
| 2 | paid ≥ 0.02 CELO in `0x6165257d…` (it did) | **100** | `0x23e65532…` | 3 |
| 3 | paid ≥ 0.005 CELO in `0x59728986…` (it did) | **100** | `0xaaf6c203…` | 4 |
| 5 | paid ≥ 0.02 CELO in `0x6b1a4325…` (it paid 0.01) | **50**: score scales with the amount paid | `0xe7a4c7b2…` | 5 |

Gas per answer was 0.0234-0.0274 CELO (115k-135k gas at 202.5 gwei). Everything so far (2 registrations, 1 funding
transfer, 4 payments, 5 requests, 5 answers) cost **0.62048977 CELO** in gas, out of the 50 CELO cap.
The evidence copies are in [`mainnet/evidence/`](mainnet/evidence/) and the job files in [`mainnet/`](mainnet/).

## Stack updates (no transactions, no gas)
| when (UTC) | stack | change | check after |
|---|---|---|---|
| 2026-11-27 05:16 / 05:30 | sepolia / mainnet | gas guard: 20 answers per UTC day, 5 per agent (`1762303`) | 12 / 3 runs, 0 errors |
| 2026-11-27 06:28 / 06:37 | sepolia / mainnet | **v0.5.0** (`1d83aa5`): x402 checker, `verify_deployment` before the key, request-block evidence, state migration, paid mode off | migration once (`usage`, `expired`), then clean runs; mainnet still `seq 5`, head `0x97d1…ca1c` |

Details: docs/MAINNET-STATUS.md (section 6) and docs/RECONCILE-v05.md.
