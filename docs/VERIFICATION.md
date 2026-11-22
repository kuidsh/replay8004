# v0.1.1: replay8004 checked against live Celo

Checked 2026-11-21 (UTC), read-only. No keys were used and no transactions were sent. Every
constant below is pinned by a test in `tests/test_live_fixtures.py`.

## Registry addresses
Source: [erc-8004/erc-8004-contracts `scripts/addresses.ts`](https://github.com/erc-8004/erc-8004-contracts/blob/master/scripts/addresses.ts)
(branch `master`, last pushed 2026-08-15). Celo 42220 is in `MAINNET_CHAIN_IDS` and Celo Sepolia
11142220 is in `TESTNET_CHAIN_IDS`. `replay8004/networks.py` matches it exactly.

`eth_getCode` shows that each address is a 130-byte ERC-1967 proxy. The implementation
(EIP-1967 slot) is the same on both chains:

| registry | Celo Sepolia (11142220) | Celo mainnet (42220) | implementation (both) |
|---|---|---|---|
| Identity | `0x8004A818BFB912233c491871b3d84c89A494BD9e` | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` | `0x7274e874…9c02` (14,474 B) |
| Reputation | `0x8004B663056A597Dffe9eCcC1965A193B7388713` | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` | `0x16e0fa7f…da34` (10,491 B) |
| Validation | `0x8004Cb1BF31DAf7788923b405b754f57acEB4272` | `0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58` | `0xdb31f5d9…7f99` (5,876 B) |

ValidationRegistry proxy creation:
- Sepolia: block 17,013,556, tx `0x9751b92d5a2c420622b133e1c1961a3d5491d1e3c8c9bbd8f6a29754be05cc3b`
- mainnet: block 58,396,736, tx `0x25555ad05cc5a794ce9b7f0e564717647082b86e9b75b3b9732270a020d99dfe`

On mainnet, `eth_getCode` returns 0 bytes at block 58,396,735 and 130 bytes at 58,396,736. Sepolia
forno doesn't serve historical state, so the Sepolia block comes from Blockscout.

## ValidationRegistry ABI
Source: `ValidationRegistryUpgradeable`, solc v0.8.24, fully verified on
[Celo Blockscout](https://celo.blockscout.com/address/0xdb31f5d9167f8ebc8b30fbbf814c4d297c2d7f99) and
[Celo Sepolia Blockscout](https://celo-sepolia.blockscout.com/address/0xdb31f5d9167f8ebc8b30fbbf814c4d297c2d7f99).
Each selector was also found as a `PUSH4` in the deployed bytecode on both chains, and the event topic as a `PUSH32`.

| item | signature | selector / topic |
|---|---|---|
| `validationRequest` | `(address,uint256,string,bytes32)` | `0xaaf400c4` |
| `validationResponse` | `(bytes32,uint8,string,bytes32,string)` | `0x3d659a96` |
| `getSummary` | `(uint256,address[],string) → (uint64,uint8)` | `0x1b7cabd6` |
| `getValidationStatus` | `(bytes32) → (address,uint256,uint8,bytes32,string,uint256)` | `0xff2febfc` |
| event `ValidationRequest` | `(address indexed,uint256 indexed,string,bytes32 indexed)` | `0x530436c3634a98e1e626b0898be2f1e9980cc1bd2a78c07a0aba52d0a48a5059` |

Contract behaviour that matters to the worker:
- `validationRequest` reverts with `"exists"` if `requestHash` is already used, by any validator.
- `validationRequest` reverts with `"Not authorized"` unless the sender is the agent's owner or an approved operator.
- `validationResponse` can be called again and overwrites the previous answer. Only the chain
  enforces who may answer; replay8004's "answer once" rule is enforced by its own state.
- `getSummary` averages only the requests that have a response (`hasResponse`), with optional
  validator and tag filters.

`getSummary` decoding:
- `getSummary(1, [], "")` returns `(0, 0)` on both chains.
- On mainnet, agent #1870 returns `(17, 99)`, the same as recomputing from its 17
  `ValidationResponse` events. With a validator and tag filter it returns `(1, 100)`.

Registry activity on mainnet: 39 txs, 21 requests and 17 responses, the last on 2026-03-19 (block
62,055,690). On Sepolia: only the deployment tx and no requests.

## RPC
| network | URL | `eth_chainId` | Celo docs |
|---|---|---|---|
| Celo Sepolia | `https://forno.celo-sepolia.celo-testnet.org` | `0xaa044c` = 11142220 | [network overview](https://docs.celo.org/tooling/overview/network-overview): same URL ("best effort"), same chain id, explorer `celo-sepolia.blockscout.com` |
| Celo mainnet | `https://forno.celo.org` | `0xa4ec` = 42220 | |

Range limits for `eth_getLogs` on forno: Sepolia accepts 100,000 blocks but not 1,000,000. Mainnet
accepts 5,000 but not 10,000. The worker's chunk size of 5,000 works on both.

Retention on forno (measured later on 2026-11-21/22): Sepolia serves receipts 10,000 blocks back but
no blocks or state 20,000 back. Mainnet serves receipts 200,000 blocks back but not 1,000,000. Older
payments need an archive RPC (`--rpc`). A missing receipt is treated as undecidable and is never scored.

## End-to-end check on mainnet (read-only)
Payment used: [`0x52659095…1875`](https://celoscan.io/tx/0x52659095845053c3411eadea3cc9b8cc91c0cb0a3ff1da9f46289b3b5acd1875),
a plain USDC `transfer()` (`0xcebA9300f2b948710d2653dD7B07f33A8B32118C`, 6 decimals). It sent 10 USDC
from `0x5758…6f22` to `0x02a7…ce3c` in block 83,339,241.

| job | command | result |
|---|---|---|
| `tests/fixtures/job-mainnet-usdc-ok.json` | `REPLAY8004_ALLOW_MAINNET=1 replay8004 --network celo-mainnet check …` | **100**: "transfer of 10000000 confirmed with 479 confirmations" |
| `tests/fixtures/job-mainnet-usdc-wrong-to.json` (recipient `0x…dEaD`) | same | **0**: "no matching Transfer log (token / from / to)" |

`tests/fixtures/receipt-mainnet-usdc-transfer.json` is the receipt as captured, with head block
83,339,731. The tests replay it offline.

A dry run of `replay8004 run --once` on Celo Sepolia (no key, recent start block) scanned to block
41,956,638 and found no requests, as expected.

## What changed in the code
1. **User-Agent (bug).** `forno.celo.org` answers HTTP 403 to urllib's default `Python-urllib/3.x`
   User-Agent on every call tried. Celo Sepolia forno accepts it. A custom User-Agent
   gets 200 on both. `Rpc` and the `https://` job fetch now send `User-Agent: replay8004/<version>`.
   Before this fix, every mainnet RPC call from the validator failed.
2. **Scan start.** A fresh state used to scan from block 0. It now starts at the
   ValidationRegistry's deployment block (`Network.validation_deploy_block`) unless
   `--start-block` or `START_BLOCK` is set. For a new validator, the block where it goes live is better still.
3. **Tests.** 12 new offline tests: the real-receipt replays (100 and 0), stable fixture hashes,
   pinned addresses, chain ids, selectors, topic and deployment blocks, `getSummary` decoding, the
   User-Agent for RPC and job fetch, and the scan start.
