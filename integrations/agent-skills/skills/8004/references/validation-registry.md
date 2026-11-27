# ERC-8004 Validation Registry (preview)

> **Status.** The Validation Registry part of ERC-8004 is still being revised with the TEE community
> ([erc-8004-contracts README](https://github.com/erc-8004/erc-8004-contracts#validation-registry)).
> The interface below is the one in `ValidationRegistryUpgradeable.sol` today. It may change.
> This file deliberately gives **no Celo address**: Celopedia does not list one yet. Look the
> address up in the contracts repo and **verify it on-chain** (below) before you build on it.

## What it is

The Identity Registry says *who* an agent is and the Reputation Registry collects *opinions* about
it. The Validation Registry records *checks*: an agent's owner asks a named validator to verify a
piece of work, and the validator posts a 0–100 result on-chain. A validator can be anything that
can sign a transaction: a service that re-runs the work, a staked re-executor, a zkML verifier or a
TEE oracle. The registry itself does not judge anything; it only records who asked whom and what
they answered.

## Interface

| Function | Who may call | Notes |
|---|---|---|
| `validationRequest(address validatorAddress, uint256 agentId, string requestURI, bytes32 requestHash)` | the agent's owner or an approved operator | Reverts `"bad validator"` for the zero address, `"exists"` if `requestHash` was used before, `"Not authorized"` otherwise |
| `validationResponse(bytes32 requestHash, uint8 response, string responseURI, bytes32 responseHash, string tag)` | only the validator named in the request | `response` is 0–100 (`"resp>100"`). Can be called again: the latest answer overwrites the earlier one and updates `lastUpdate` |
| `getValidationStatus(bytes32 requestHash)` | anyone | Returns `(validatorAddress, agentId, response, responseHash, tag, lastUpdate)`. Reverts `"unknown"` for a hash never requested |
| `getSummary(uint256 agentId, address[] validatorAddresses, string tag)` | anyone | Returns `(uint64 count, uint8 avgResponse)` over **answered** requests only; integer average; `""` tag = all tags; `[]` validators = all validators |
| `getAgentValidations(uint256 agentId)` | anyone | All `requestHash`es for an agent |
| `getValidatorRequests(address validatorAddress)` | anyone | All `requestHash`es sent to a validator |
| `getIdentityRegistry()` | anyone | The Identity Registry this deployment checks ownership against |

Events: `ValidationRequest(validatorAddress indexed, agentId indexed, requestURI, requestHash indexed)` and
`ValidationResponse(validatorAddress indexed, agentId indexed, requestHash indexed, response, responseURI, responseHash, tag)`.
ABI: [`validation-registry-abi.json`](./validation-registry-abi.json).

`requestHash` should be `keccak256` of the exact bytes behind `requestURI` (the job you want checked),
so the validator and anyone else can confirm they are looking at the same request. `responseHash`
is the same for the validator's evidence behind `responseURI`.

## Verify the deployment first

A Validation Registry is only meaningful if it points at the same Identity Registry your agents are
registered in. Check that before trusting any address:

```javascript
import { createPublicClient, http, getAddress } from 'viem';
import { celo } from 'viem/chains';
import validationRegistryAbi from './validation-registry-abi.json';

const IDENTITY_REGISTRY = '0x8004A169FB4a3325136EB29fA0ceB6D2e539a432'; // Celo Mainnet (SKILL.md)
const VALIDATION_REGISTRY = '0x...'; // from erc-8004-contracts scripts/addresses.ts, not from this file

const publicClient = createPublicClient({ chain: celo, transport: http('https://forno.celo.org') });

async function verifyValidationRegistry(address) {
  const code = await publicClient.getCode({ address });
  if (!code || code === '0x') throw new Error('no contract at this address');
  const identity = await publicClient.readContract({
    address, abi: validationRegistryAbi, functionName: 'getIdentityRegistry',
  });
  if (getAddress(identity) !== getAddress(IDENTITY_REGISTRY)) {
    throw new Error(`points at identity registry ${identity}, expected ${IDENTITY_REGISTRY}`);
  }
  return publicClient.readContract({ address, abi: validationRegistryAbi, functionName: 'getVersion' });
}
```

## Request a validation (agent owner)

```javascript
import { keccak256, toBytes } from 'viem';

// 1. Publish the job somewhere the validator can read (https://, ipfs:// or a data: URI).
const job = JSON.stringify({
  agentId: '42',
  nonce: crypto.randomUUID(), // keeps requestHash unique (see Pitfalls)
  claim: { txHash: '0x...', minAmount: '10000' },
});
const requestURI = `data:application/json;base64,${Buffer.from(job).toString('base64')}`;
const requestHash = keccak256(toBytes(job));

// 2. Ask a validator. Must be sent by the agent's owner or approved operator.
const hash = await walletClient.writeContract({
  address: VALIDATION_REGISTRY,
  abi: validationRegistryAbi,
  functionName: 'validationRequest',
  args: [VALIDATOR_ADDRESS, 42n, requestURI, requestHash],
});
```

Which job format a validator accepts is up to that validator; read its documentation (for example
the services in its own ERC-8004 registration file).

## Read results (anyone)

```javascript
// One request: who answered, what, and when.
const [validator, agentId, response, responseHash, tag, lastUpdate] = await publicClient.readContract({
  address: VALIDATION_REGISTRY,
  abi: validationRegistryAbi,
  functionName: 'getValidationStatus',
  args: [requestHash],
});
// response 0 can be a real "failed" answer; see Pitfalls for telling it from "not answered yet"

// Track record with validators you trust, for one tag.
const [count, avgResponse] = await publicClient.readContract({
  address: VALIDATION_REGISTRY,
  abi: validationRegistryAbi,
  functionName: 'getSummary',
  args: [42n, [VALIDATOR_ADDRESS], ''],
});
```

## Pitfalls

- **Always pass the validators you trust** to `getSummary`. With `[]`, anyone the owner names
  (including a validator the owner runs) counts toward the average.
- **`getSummary` has no time window.** For freshness, check `lastUpdate` on the specific request.
- **Answers can be overwritten** by the same validator; re-read before acting on an old result.
- **Unanswered vs. failed:** the contract stores a `hasResponse` flag but `getValidationStatus`
  does not return it, and `lastUpdate` is already set when the request is made. An unanswered
  request reads as `response = 0`, `responseHash = 0`. Treat `responseHash != 0` as "answered" only
  if the validator documents that it always posts a non-zero hash; otherwise look for its
  `ValidationResponse` event.
- **`requestHash` is global and first-come.** A second request with the same hash reverts
  `"exists"`, even from another agent. Put the `agentId` and a fresh nonce in the job so the hash is
  unique and can't be squatted from the mempool.
- **The owner chooses what to submit.** A high average shows the submitted claims checked out, not
  that every claim the agent made was checked.
