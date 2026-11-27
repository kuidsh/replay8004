# Mainnet status (read-only checks, 2026-11-27 06:05 UTC)

Everything below was read from Celo mainnet (forno.celo.org, cross-checked with celo.blockscout.com), the
public evidence bucket and the stack's own logs and state. Nothing was sent, signed or deployed.

**Running:** stack `replay8004-mainnet` (us-east-1), **v0.5.0** (`main` at `1d83aa5`), deployed 2026-11-27 06:37 UTC.
The checks in sections 1–5 were made at 06:05 UTC, on the previous code (0.1.1 + gas guard, `91d23ec`); section 6 records
the deploy and the checks after it.

| | |
|---|---|
| Validator | [`0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952`](https://celoscan.io/address/0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952) |
| ValidationRegistry | [`0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58`](https://celoscan.io/address/0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58): 49 txs in total (Blockscout counter) |
| Identity Registry | [`0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`](https://celoscan.io/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432) |
| Requests naming the validator | **5** (full history since the registry's deployment block 58,396,736, Blockscout) |
| Answered | **5 of 5**, none pending, none twice |
| Time from request to answer | 13–55 s, median 30 s (block timestamps) |
| Gas | 0.0234–0.0274 CELO per answer, **0.1330 CELO** for all 5 |
| Evidence chain | 5 bundles, intact; head `0x97d152326c523de65a26bc81809beca1e8726c8ce7345d46a44780728ad0ca1c` = DynamoDB `head`, `seq` 5 |
| Worker health since the 05:30 deploy | mainnet 36 runs, sepolia 36 runs, 0 errors or warnings |

## 1. `replay8004 --network celo-mainnet doctor`
```json
{
  "ok": true,
  "network": "celo-mainnet",
  "rpc": "https://forno.celo.org",
  "validationRegistry": "0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58",
  "expectedIdentityRegistry": "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
  "rpcChainId": 42220,
  "head": 83858311,
  "identityRegistry": "0x8004a169fb4a3325136eb29fa0ceb6d2e539a432",
  "version": "2.0.0"
}
```
`getIdentityRegistry()` on the ValidationRegistry returns Celo's Identity Registry and `getVersion()` is 2.0.0,
so the v0.5 Lambda's `verify_deployment` check (run before the key is loaded) passes on mainnet.
Caveat: the address comes from erc-8004-contracts `scripts/addresses.ts`; the README lists no Celo
ValidationRegistry and the validation spec is still a preview. Sepolia (`0x8004Cb1B…4272`) also passes.

## 2. Evidence: downloaded from the bucket and verified
`aws s3 sync s3://replay8004-mainnet-evidencebucket-exgfx3xqkhfr/evidence/ .replay8004/mainnet-live/evidence/`
(5 objects), then `replay8004 verify-evidence .replay8004/mainnet-live/evidence`:
```
OK: 5 bundles, chain intact
```
- The 5 downloaded files are byte-identical to `docs/mainnet/evidence/`.
- Each responseURI fetched **anonymously** returns HTTP 200, and keccak256 of the bytes served equals the
  `responseHash` in the `ValidationResponse` event. Anyone can check an answer end to end.
- All 5 bundles report `checkerVersion: "0.1.1"` and have no `request` block (0.1.1 didn't write it).
  The first v0.5 answer will be `seq 6`, `prev = 0x97d1…ca1c` (tested in `tests/test_migration.py` against a copy
  of the live state).

## 3. Status page built into `./site`
`replay8004 status --evidence .replay8004/mainnet-live/evidence --out site --validator 0xD2d6…5952 --evidence-base-url https://replay8004-mainnet-evidencebucket-exgfx3xqkhfr.s3.us-east-1.amazonaws.com/evidence`
```json
{"answered": 5, "agents": 1, "passRate": 0.6, "avgScore": 70.0, "medianSecondsToDecide": null,
 "chain": {"intact": true, "detail": "5 bundles, chain intact", "head": "0x97d152326c523de65a26bc81809beca1e8726c8ce7345d46a44780728ad0ca1c"},
 "byTag": {"replay:erc20_transfer": {"count": 5, "avg": 70.0, "passed": 3}}, "scoreBuckets": {"0": 1, "100": 3, "50-89": 1}}
```
`medianSecondsToDecide` is empty because the page only uses bundles that carry `request.block` (v0.5+). The
on-chain median is 30 s (table below). `site/` is git-ignored and **not published** (see docs/LAUNCH-STATUS.md, item e).

## 4. Every ValidationRequest / ValidationResponse for the validator

Requester: agent **#10143** (owner `0x070a5F24851DD4D0200EBd4064F0914F92998647`). All tags `replay:erc20_transfer`.

| seq | requestHash | request (block, UTC) | response (block, UTC) | blocks / s | score | gas used | fee CELO |
|---|---|---|---|---|---|---|---|
| 1 | `0x4a5795f3…da15` | [83,800,939](https://celoscan.io/tx/0x02090b85eb285eb96aaf4a0f1070d1a501bd9d63f6b458719c3076054c5a86f1) 14:01:37 | [83,800,969](https://celoscan.io/tx/0x7acc6c0d170e36932f4f53a3d8acad437fc7f1549676b8701e82cbc9c5a7d27f) 14:02:07 | 30 / 30 | 100 | 135,354 | 0.027409 |
| 2 | `0x449960bb…e55a` | [83,801,307](https://celoscan.io/tx/0x5c7bce07dedd3d8c3ee08da070fd9832e3dc3c71f2613317d64ee27c2acf9811) 14:07:45 | [83,801,329](https://celoscan.io/tx/0xbb91d72c5f9a4f5f818c080b186f15622310e50c46de8bff8bfbf096ec2b8626) 14:08:07 | 22 / 22 | 0 | 115,442 | 0.023377 |
| 3 | `0x23e65532…1341` | [83,804,835](https://celoscan.io/tx/0xea21f51b6e792d743a1f443c589f6a8f33a483f0812ab1f6f33cb6a35aad7265) 15:06:33 | [83,804,869](https://celoscan.io/tx/0x8719a84b6af6f8dc4c8b7ebb5ed4153fe5631070f477def5e789a4036f509054) 15:07:07 | 34 / 34 | 100 | 135,366 | 0.027412 |
| 4 | `0xaaf6c203…810f` | [83,804,858](https://celoscan.io/tx/0x0213eb68e55ae8e41e76eeca86e424c5c79e981720003bc427bdadfa9c9630a3) 15:06:56 | [83,804,871](https://celoscan.io/tx/0x0f5a53294f66460d6a8b707744b8565580a162817cdc7f2e7e04b706f2e633e3) 15:07:09 | 13 / 13 | 100 | 135,366 | 0.027412 |
| 5 | `0xe7a4c7b2…cbf9` | [83,804,875](https://celoscan.io/tx/0x46c3e5708c7ac74fbd504bd93a7eacd92314d4092c62aa484577b0f5cc72dd66) 15:07:13 | [83,804,930](https://celoscan.io/tx/0xe485b247e76c93a25169b735d7896189d1b7295c3398ee0c8681ca506a74be5a) 15:08:08 | 55 / 55 | 50 | 135,366 | 0.027412 |

All on 2026-11-26. Score 0 (#2) and 50 (#5) were the intended negative and partial cases (docs/MAINNET-RUN.md).
Correction to the brief: the fastest answer took **13 s**, not 22 s. Time includes the 2-confirmation wait
and the 3-block reorg buffer.

Evidence: `https://replay8004-mainnet-evidencebucket-exgfx3xqkhfr.s3.us-east-1.amazonaws.com/evidence/<requestHash>.json`

## 5. Live state (DynamoDB `pk=worker`, ver 991, GetItem 2026-11-27)
`last_block 83857901, seq 5, head 0x97d1…ca1c, done 5, pending 0, inflight 0, failed 0, daily {2026-11-27: 0}`.
No `usage`/`expired` keys yet. The v0.5 worker adds them (`store.migrate`) in its first write and leaves the rest alone.

## 6. v0.5 deploy (2026-11-27)
The changesets were first created with `sam deploy --no-execute-changeset` and the current parameters, reviewed, and then
deployed with the same parameters and the same code artifact (`9edda1f2…`): Sepolia at 06:28 UTC, mainnet at 06:37 UTC.

| stack | changes |
|---|---|
| replay8004-mainnet | `WorkerFunction` Modify (code + env `PAID_MODE=0`, `FREE_PER_MONTH=25`, `FREE_ACCOUNTS=""`), no replacement. Scheduler role + schedule: Modify, caused only by the `WorkerFunction.Arn` reference (the ARN doesn't change). |
| replay8004-sepolia | the same three Modify entries, no replacement |

Not in either changeset: the evidence bucket, the DynamoDB table and its item. The Secrets Manager secret is
not a stack resource (passed by ARN), so it can't be replaced. No paywall resources (`PaidMode=0`).

After the deploy (read 06:40 UTC):
- mainnet worker: `PAID_MODE=0`, `MAX_ANSWERS_PER_DAY=20`; first run logged `state migrated: added ['usage', 'expired']`
  (once); the next runs report `held 0, expired 0`, no errors.
- DynamoDB `pk=worker` (ver 1040): `seq 5`, head `0x97d152326c523de65a26bc81809beca1e8726c8ce7345d46a44780728ad0ca1c`, 5 done,
  0 pending; keys now include `usage` and `expired`. The next answer will be bundle 6 with `prev` = that head.
- Sepolia: the same migration once, then clean runs; its state kept `seq 1` and its done request.
- Every run now calls `verify_deployment` (getIdentityRegistry() == Celo's Identity Registry) before loading the key.
