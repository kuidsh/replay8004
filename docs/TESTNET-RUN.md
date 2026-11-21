# Testnet run: Celo Sepolia, 2026-11-21

The full flow ran end to end on Celo Sepolia (chain 11142220), on the canonical ERC-8004 registries.
No contracts were deployed and only testnet CELO was used. These were the first requests and
responses ever made on the Sepolia ValidationRegistry.

| role | address |
|---|---|
| validator (replay8004) | [`0x163296ca93f9887dD10e3053Ea0459c49A770A86`](https://celo-sepolia.blockscout.com/address/0x163296ca93f9887dD10e3053Ea0459c49A770A86) |
| test agent owner | [`0x119D0a02F33F749f07E4aCB74A8FB22878F657db`](https://celo-sepolia.blockscout.com/address/0x119D0a02F33F749f07E4aCB74A8FB22878F657db) |
| test agent | **#1037** in the IdentityRegistry `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| ValidationRegistry | [`0x8004Cb1BF31DAf7788923b405b754f57acEB4272`](https://celo-sepolia.blockscout.com/address/0x8004Cb1BF31DAf7788923b405b754f57acEB4272) |

Both wallets are testnet-only and were funded from faucet.celo.org: 1 CELO for the owner and
2 CELO for the validator.

## Transactions
| # | step | from | tx | block | fee (CELO) |
|---|---|---|---|---|---|
| 1 | `register(agentURI)`: test agent #1037 (data: URI registration file) | owner | [`0xbdc71904…b2ff`](https://celo-sepolia.blockscout.com/tx/0xbdc71904c493c86cce24c44397070c6854f6fb3e36c7677ac23543c3e72db2ff) | 41,958,131 | 0.02141601 |
| 2 | the payment being claimed: CELO ERC-20 `transfer` of 0.01 CELO, owner → validator | owner | [`0xa6552a0b…1ffa`](https://celo-sepolia.blockscout.com/tx/0xa6552a0bf81e9fd51b4c91876debd2106613916087f5e6c54a61f7e83dcc1ffa) | 41,958,171 | 0.00206147 |
| 3 | `validationRequest`: job 1 (correct claim) | owner | [`0x1b02ec2b…1a01`](https://celo-sepolia.blockscout.com/tx/0x1b02ec2b38d1c2a7e8102c479a8a5ccaafb175cc9722988226a49566cfaa1a01) | 41,958,199 | 0.01177229 |
| 4 | `validationResponse`: job 1, **score 100**, `replay:erc20_transfer` | validator | [`0xeae6bd78…c076`](https://celo-sepolia.blockscout.com/tx/0xeae6bd7849bdf85da3867a83806a68977c28c521f328e5ab835bba115099c076) | 41,958,256 | 0.00707837 |
| 5 | `validationRequest`: job 2 (deliberately bad: names agent 1036) | owner | [`0xfe7f8da3…b4bf`](https://celo-sepolia.blockscout.com/tx/0xfe7f8da32810b03950f38df941afae2847f9c9e770372a084ab832432a32b4bf) | 41,958,295 | 0.01001774 |
| 6 | `validationResponse`: job 2, **score 0**, `replay:invalid` | validator | [`0xa2b66c4a…f4b2`](https://celo-sepolia.blockscout.com/tx/0xa2b66c4a44d8195c7093a8beb23f0e0b9ff4db5e979cc09cbb94930d59c4f4b2) | 41,958,308 | 0.00602858 |

Gas in total: 0.05837444 CELO. The validator paid 0.01310694 CELO for 2 responses, about 0.0066 each.
The owner paid 0.04526750. Ending balances: validator 1.99689306 CELO (it also received the
0.01 CELO payment) and owner 0.94473251 CELO.

## Requests and answers
| job file | requestHash | answer | finding | responseHash |
|---|---|---|---|---|
| [`testnet/job-1-good.json`](testnet/job-1-good.json) | `0x03245a62e38e4ff64d57f70d2d86b76369c9a0e1fe9dafe511373e5913d8adae` | 100, `replay:erc20_transfer` | "transfer of 10000000000000000 confirmed with 81 confirmations" | `0xec2ffe478397dadb6416ac7ddaddd9c0cf0fb9db0792cab150c1386f5639bedf` |
| [`testnet/job-2-bad-agent.json`](testnet/job-2-bad-agent.json) | `0xba24d0e582c8f3f087f1631ea30b65f63491f32359b9758f1410bb1be63b99da` | 0, `replay:invalid` | "invalid job: job agentId does not match the on-chain request" | `0xe808e607f435860511e8dafb375d863115da3e1d748c42e3108b68642cdba80a` |

The evidence bundles are in [`testnet/evidence/`](testnet/evidence/). Each on-chain `responseURI`
points to `https://raw.githubusercontent.com/kuidsh/replay8004/main/docs/testnet/evidence/<requestHash>.json`,
which resolves once the repository is public. Job 1 was sent as an inline `data:` URI, so the
`requestURI` on-chain holds the job itself.

## Checks done after the run
- Both receipts have status 1. Each contains a `ValidationResponse` event from the validator for agent
  1037 with the expected score, tag and `responseHash`.
- `replay8004 status --request-hash …` (`getValidationStatus`) returns validator `0x1632…0a86`,
  agent 1037, with 100 / `replay:erc20_transfer` and 0 / `replay:invalid`.
- `getSummary(1037, [validator], tag)` returns `(2, 50)` with no tag, `(1, 100)` for
  `replay:erc20_transfer` and `(1, 0)` for `replay:invalid`.
- keccak256 of each evidence file equals the on-chain `responseHash`.
- `replay8004 verify-evidence docs/testnet/evidence` prints "OK: 2 bundles, chain intact".
  Bundle 2's `prev` is bundle 1's `responseHash`.
- The validator never answered a request twice: the second run answered only the new request.
- A dry run before the first answer found the request (score 100), wrote no evidence and left it
  pending. The live run then answered it.
- `tests/test_live_fixtures.py` checks the committed evidence offline against these on-chain hashes.

## Reproduce
```bash
replay8004 status --request-hash 0x03245a62e38e4ff64d57f70d2d86b76369c9a0e1fe9dafe511373e5913d8adae
replay8004 summary --agent-id 1037 --validator 0x163296ca93f9887dD10e3053Ea0459c49A770A86
replay8004 verify-evidence docs/testnet/evidence
replay8004 check docs/testnet/job-1-good.json         # re-runs the claim against Sepolia: 100
```

## How it was run
- Wallets were created by the operator in their own terminal (`scripts/new_wallets.py`). The keys
  were kept in a password manager and a git-ignored `.env`, loaded into the environment only for the
  command that signs. They were never printed or logged.
- Agent: `python scripts/register_agent.py --send` (register(string), with agentId read from the `Registered` event).
- Job 1: `replay8004 job erc20-transfer --agent-id 1037 --tx 0xa6552a0b… --token 0x471EcE…a438 --from <owner> --to <validator> --min-amount 10000000000000000`.
- Validator: `replay8004 run --validator 0x1632…0A86 --send --once --evidence-base-url https://raw.githubusercontent.com/kuidsh/replay8004/main/docs/testnet/evidence`.
