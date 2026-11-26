# Taking replay8004 down from AWS

Everything lives in **us-east-1** in one account. Every resource is either named `replay8004-*` / `replay8004/*`
or tagged `Project=replay8004`, and every stack also tags its resources with `Stack=<stack name>`.
`scripts/aws_inventory.py` lists all of them, read-only:

```bash
python scripts/aws_inventory.py --profile replay8004-deployer-mfa
```

## What exists
| resource | how it is created | name |
|---|---|---|
| CloudFormation stack | `sam deploy` | `replay8004-sepolia`, later `replay8004-mainnet` |
| ↳ worker Lambda, log group, schedule | stack | `<stack>-worker`, `/aws/lambda/<stack>-worker`, `<stack>-every-minute` |
| ↳ state table, 2 IAM roles | stack | `<stack>-StateTable-…`, `<stack>-WorkerFunctionRole-…`, `<stack>-WorkerFunctionEveryMinuteRole-…` |
| ↳ evidence bucket | stack, **kept when the stack is deleted** | `<stack>-evidencebucket-…` |
| SAM upload bucket | first `sam deploy --resolve-s3` | stack `aws-sam-cli-managed-default` |
| validator key | David, Secrets Manager | `replay8004/<network>-validator` (tag it `Project=replay8004`) |
| deploy user and policies | root, once | user `replay8004-deployer`; policies `replay8004-deployer`, `replay8004-deployer-extra`, `replay8004-boundary` |

The schedule cannot carry tags (AWS::Scheduler::Schedule has none). It is found by name and is deleted with its stack.

## Order (profile `replay8004-deployer-mfa` unless it says root)
1. **Stop answering.** Delete each stack: `sam delete --stack-name replay8004-mainnet --profile replay8004-deployer-mfa --region us-east-1`
   (then `replay8004-sepolia`). This removes the Lambda, schedule, log group, table and roles. The evidence bucket stays.
2. **Secrets:** `aws secretsmanager delete-secret --secret-id replay8004/<network>-validator --recovery-window-in-days 7 ...`
   Move the CELO left in the wallet first, if any.
3. **SAM upload bucket:** empty every object version, then delete stack `aws-sam-cli-managed-default`.
   This bucket is shared by every SAM project in this account and region. Skip this step if another project uses it.
4. **Evidence buckets:** each file is locked (S3 Object Lock, COMPLIANCE) for `EvidenceRetentionDays` after it was
   written: 1 day on Sepolia, 365 on mainnet. Nobody can delete a locked file early, not even root. Once the last
   lock has expired, delete all object versions, then the bucket. While it exists it costs cents. On mainnet, keep it
   as long as anyone may still check the on-chain answers, because they link to it.
5. **Root, last:** delete user `replay8004-deployer` (its access keys and MFA device first), then the three policies.
6. Re-run the inventory with the root profile, or check Resource Groups → Tag Editor for `Project=replay8004` in every region.
   It must come back empty.
