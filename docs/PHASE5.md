# Phase 5 runbook (repo private)

Each step needs David's go-ahead. Mainnet stays off until David says "go mainnet" and sets
`REPLAY8004_ALLOW_MAINNET=1`.

## 1. Self Agent ID (David runs this, in a terminal no assistant reads)
Sources: docs.celo.org/build/agents/self-agent-id, docs.self.xyz/docs/agent-id/cli, and the code of
`@selfxyz/agent-sdk` 0.3.1.

The CLI's `wallet-free` mode creates the agent key on this machine and cannot import an existing one, so the new
key becomes the mainnet validator wallet. (The SDK/API route creates the key on Self's server: don't use it.)
The session file holds the key in plain text. Keep it outside the repo and delete it once the key is stored.
Sessions expire after 30 minutes. Run it with `--network testnet` first, with a mock document.

```powershell
$S = "$HOME\self-replay8004.json"
npx -p @selfxyz/agent-sdk@0.3.1 self-agent register init --mode wallet-free --network mainnet --out $S
npx -p @selfxyz/agent-sdk@0.3.1 self-agent register open --session $S
npx -p @selfxyz/agent-sdk@0.3.1 self-agent register wait --session $S --timeout-seconds 1800
npx -p @selfxyz/agent-sdk@0.3.1 self-agent register export --session $S --unsafe --print-private-key
Remove-Item $S    # only after the key is saved in the password manager
```
Disclosures such as age or nationality are optional and are stored on-chain, so none is requested here.

## 2. Registration file
`python scripts/register_agent.py --registration examples/registration.json --validator-address 0x.. --from 0x..`
shows the decoded JSON, size, calldata and gas without a key. The wallet needs CELO before the tx can be sent.

## AWS access
Profile `kuidsh-own-mfa` only. Deploys run as the IAM user `replay8004-deployer`, never as root. Its policy
(`infra/iam/deployer-policy.json`) covers only `replay8004-*` stacks, buckets, tables, functions, schedules, log groups and
`replay8004/*` secrets. It is limited to us-east-1 and mx-central-1 and requires an MFA session. It can store the validator
key but never read it back. Every role the stack creates gets the boundary `infra/iam/boundary-policy.json`, so pass it on deploy:
`--parameter-overrides PermissionsBoundaryArn=arn:aws:iam::<account>:policy/replay8004-boundary`.
Name the validator-key secret `replay8004/<network>-validator`.

## 3. Evidence host, before the first mainnet answer
Upload a test object, then open it logged out (`curl -i <url>`). It must return 200 with the same bytes.
Then repeat a full Sepolia validation against that host, because the sending code changed after docs/TESTNET-RUN.md.

## 4. Mainnet
Gas cap 50 CELO in total. Every tx goes into docs/MAINNET-RUN.md.
