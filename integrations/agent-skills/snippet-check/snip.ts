import { keccak256, toBytes } from 'viem';
import { createPublicClient, http, getAddress } from 'viem';
import { celo } from 'viem/chains';
import validationRegistryAbi from './abi.js';

const IDENTITY_REGISTRY = '0x8004A169FB4a3325136EB29fA0ceB6D2e539a432'; // Celo Mainnet (SKILL.md)
const VALIDATION_REGISTRY = '0x0000000000000000000000000000000000000001' as const; // from erc-8004-contracts scripts/addresses.ts, not from this file

const publicClient = createPublicClient({ chain: celo, transport: http('https://forno.celo.org') });

async function verifyValidationRegistry(address: `0x${string}`) {
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

import { createWalletClient } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
const walletClient = createWalletClient({ account: privateKeyToAccount('0x'+'11'.repeat(32) as `0x${string}`), chain: celo, transport: http('https://forno.celo.org') });
const VALIDATOR_ADDRESS = '0x0000000000000000000000000000000000000002' as const;
async function main(){


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

}
void main; void verifyValidationRegistry;
