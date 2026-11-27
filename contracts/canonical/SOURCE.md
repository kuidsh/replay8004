# Vendored canonical ERC-8004 contracts

`src/` holds unmodified copies of four files from
[erc-8004/erc-8004-contracts](https://github.com/erc-8004/erc-8004-contracts) at commit
`b9e466c250744a7e06b13dff9d3c2844ed64f825` (2026-08-15). Each file carries `SPDX-License-Identifier: MIT`.

| file | why |
|---|---|
| `ValidationRegistryUpgradeable.sol` | the registry replay8004 answers on |
| `IdentityRegistryUpgradeable.sol` | owner/operator checks for `validationRequest` |
| `HardhatMinimalUUPS.sol`, `ERC1967Proxy.sol` | the repo's own test deployment path (minimal UUPS proxy, then upgrade) |

They are used only by `tests/test_canonical_registry.py`, which deploys them on an in-process EVM
exactly as the repo's `test/upgradeable.ts` does. Re-vendor when the Validation Registry spec update lands.
