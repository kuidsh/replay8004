# Mainnet steps (operator runbook)

Commands for taking replay8004 to Celo mainnet, in order. **David** marks the steps only David can do: real money,
keys, approvals. **Claude** marks the steps Claude runs after David's OK. Run every David command from the repo
folder in Windows PowerShell, in a terminal no assistant reads.

Related files: Self Agent ID registration (already done, agent #218) and the Sepolia deploy are in
[PHASE5.md](PHASE5.md). How to remove everything from AWS is in [AWS-TEARDOWN.md](AWS-TEARDOWN.md). The current AWS
resources are listed in [AWS-RESOURCES.md](AWS-RESOURCES.md).

| | |
|---|---|
| Mainnet validator | `0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952`, Self Agent ID #218, key in `.env` as `MAINET_WALLET_PRIVATE_KEY` |
| AWS | profile `replay8004-deployer-mfa`, region us-east-1. Renew the MFA session first if it has expired. |
| Gas cap | 50 CELO in total. Every tx goes into `docs/MAINNET-RUN.md`. |

---

## 1. Store the validator key in Secrets Manager (David)
Paste with **right-click**: Ctrl+V types one invisible character. You should see 66 `*`. Nothing is uploaded unless
the key has the right shape.
```powershell
$s = Read-Host "MAINNET validator key (paste with RIGHT-CLICK)" -AsSecureString
$k = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))
if ($k.Length -eq 66 -and $k.StartsWith("0x")) { aws secretsmanager create-secret --profile replay8004-deployer-mfa --region us-east-1 --name replay8004/mainnet-validator --tags Key=Project,Value=replay8004 --secret-string $k --query ARN --output text } else { "Not uploaded: got $($k.Length) characters, expected 66 starting with 0x." }
Remove-Variable s, k
```
Keep the printed ARN for step 5. **Keep the `.env` line for now**: step 4 signs with it.
To replace a wrong value, run the same three lines with `put-secret-value --secret-id replay8004/mainnet-validator`
in place of `create-secret --name ... --tags ...`.

## 2. Create a mainnet test-agent wallet (David)
This wallet owns the test agent and pays for its validation requests. Never reuse the Sepolia wallets.
```powershell
.venv\Scripts\python scripts\new_wallets.py mainnet-agent-owner
```
Save the key in your password manager, and add it to `.env` as `MAINNET_OWNER_KEY=0x...` for as long as the test
validations run. Send Claude **only the address**.

## 3. Buy and send CELO (David)
Buy about 10 CELO on a regulated exchange (e.g. Bitso). Withdraw on the **Celo network**, and send a small test amount
first.
- about 5 CELO to the validator `0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952`
- about 5 CELO to the mainnet test-agent wallet from step 2

Check the balances on CeloScan: https://celoscan.io/address/0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952

Expected use, measured on Sepolia and priced at 202.5 gwei: registration ≈ 0.16 CELO, one answer ≈ 0.027,
one request ≈ 0.045, one test payment ≈ 0.008.

## 4. Register the validator in the ERC-8004 IdentityRegistry
The registration file is embedded on-chain as a `data:` URI and has no repo link yet (Phase 6 adds one).

**Dry run (Claude runs it and shows you the decoded JSON, size, calldata and gas; nothing is sent):**
```powershell
$env:REPLAY8004_ALLOW_MAINNET = "1"
.venv\Scripts\python scripts\register_agent.py --network celo-mainnet --registration examples\registration.json --validator-address 0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952 --from 0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952
```
**Send (only after David approves the dry run; David runs it):**
```powershell
$env:REPLAY8004_ALLOW_MAINNET = "1"
$env:MAINET_WALLET_PRIVATE_KEY = (Select-String -Path .env -Pattern '^MAINET_WALLET_PRIVATE_KEY=(.+)$').Matches[0].Groups[1].Value.Trim()
.venv\Scripts\python scripts\register_agent.py --network celo-mainnet --registration examples\registration.json --validator-address 0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952 --key-env MAINET_WALLET_PRIVATE_KEY --send
Remove-Item Env:MAINET_WALLET_PRIVATE_KEY, Env:REPLAY8004_ALLOW_MAINNET
```
The output ends with the new **agentId** and the tx link. Send both to Claude.
**Then delete the `MAINET_WALLET_PRIVATE_KEY` line from `.env`.** From here on, the key lives only in your password
manager and Secrets Manager.

## 5. Deploy the mainnet stack (Claude, after David says "go mainnet")
First as a dry run (no key used, nothing sent). Check the logs, then redeploy with `DryRun=0`.
```bash
python scripts/build_lambda.py && sam build -t infra/template.yaml
sam deploy --profile replay8004-deployer-mfa --region us-east-1 --stack-name replay8004-mainnet \
  --resolve-s3 --capabilities CAPABILITY_IAM --no-confirm-changeset \
  --tags Project=replay8004 Stack=replay8004-mainnet \
  --parameter-overrides Network=celo-mainnet AllowMainnet=1 DryRun=1 EvidenceRetentionDays=365 \
    ValidatorAddress=0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952 StartBlock=<current mainnet block> \
    PermissionsBoundaryArn=arn:aws:iam::<account>:policy/replay8004-boundary
# after the dry-run logs look right:
#   same command with DryRun=0 ValidatorKeySecretArn=<ARN from step 1>
python scripts/aws_inventory.py --profile replay8004-deployer-mfa --markdown docs/AWS-RESOURCES.md
```
Before the first answer, Claude checks:
- the logged-out evidence URL test
- that the Lambda accepts the key (it refuses one that doesn't belong to `ValidatorAddress`)
- the scan range: mainnet forno accepts at most 5,000 blocks per `eth_getLogs`

Mainnet evidence stays locked for 365 days. The bucket is kept when the stack is deleted, because the on-chain
answers link to it.

## 6. Run 5-10 real validations
Test-agent wallet: `0x070a5F24851DD4D0200EBd4064F0914F92998647` (`.env`: `MAINET_AGENT_PRIVATE_KEY`).
Every command below is a dry run without `--send`: Claude runs that first and shows you the result. You run the
`--send` version only after approving it. Claude verifies every answer and logs every tx, with the running gas total,
in `docs/MAINNET-RUN.md`. Claude stops before the total passes 50 CELO.

Load the keys into the current PowerShell window (and nothing else), then clear them at the end:
```powershell
$env:REPLAY8004_ALLOW_MAINNET = "1"
$env:MAINET_WALLET_PRIVATE_KEY = (Select-String -Path .env -Pattern '^MAINET_WALLET_PRIVATE_KEY=(.+)$').Matches[0].Groups[1].Value.Trim()
$env:MAINET_AGENT_PRIVATE_KEY  = (Select-String -Path .env -Pattern '^MAINET_AGENT_PRIVATE_KEY=(.+)$').Matches[0].Groups[1].Value.Trim()
# ... commands ...
Remove-Item Env:MAINET_WALLET_PRIVATE_KEY, Env:MAINET_AGENT_PRIVATE_KEY, Env:REPLAY8004_ALLOW_MAINNET
```

**6a. Fund the test-agent wallet with 3 CELO from the validator** (one ERC-20 transfer of CELO, gas ≈ 0.008):
```powershell
.venv\Scripts\python scripts\request_validation.py --network celo-mainnet --key-env MAINET_WALLET_PRIVATE_KEY pay --to 0x070a5F24851DD4D0200EBd4064F0914F92998647 --amount-wei 3000000000000000000 --send
```

**6b. Register the test agent** (owner = the test-agent wallet; gas ≈ 0.09). Send Claude the agentId it prints:
```powershell
.venv\Scripts\python scripts\register_agent.py --network celo-mainnet --key-env MAINET_AGENT_PRIVATE_KEY --name "replay8004 mainnet test agent" --description "Test agent run by the replay8004 operator to exercise the validator on Celo mainnet." --send
```

**6c. For each validation: a payment, then a request for it.** The agent pays the validator 0.01 CELO (gas ≈ 0.008).
Then it asks replay8004 to validate that payment (gas ≈ 0.045). The validator's answer costs it ≈ 0.027.
```powershell
.venv\Scripts\python scripts\request_validation.py --network celo-mainnet --key-env MAINET_AGENT_PRIVATE_KEY pay --to 0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952 --amount-wei 10000000000000000 --send
.venv\Scripts\python scripts\request_validation.py --network celo-mainnet --key-env MAINET_AGENT_PRIVATE_KEY request --agent-id <test agent id> --validator 0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952 --tx <payment tx from the line above> --to 0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952 --min-amount 10000000000000000 --payer 0x070a5F24851DD4D0200EBd4064F0914F92998647 --send
```
`request` re-checks the claim locally before sending and shows the expected score. It saves the exact job file under
`docs/mainnet/`. The AWS validator answers within about a minute.
At least one validation should be deliberately wrong, for example a `--to` that wasn't paid, expecting score 0.

Budget for 10 validations: ≈ 0.6 CELO from the test-agent wallet and ≈ 0.27 CELO from the validator.

## 7. Afterwards
- The Sepolia stack costs about US$0.45/month while it runs live. Remove it (step 1 of [AWS-TEARDOWN.md](AWS-TEARDOWN.md)),
  or redeploy it with `DryRun=1`.
- Delete `MAINNET_OWNER_KEY` from `.env` when the test validations are done.
- Phase 6 (the repo goes public, `setAgentURI` with the repo link, the Frontier form) is in
  [PHASE6-CHECKLIST.md](PHASE6-CHECKLIST.md).
