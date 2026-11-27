// Read-only run of the skill's verify code (verbatim from validation-registry.md, block 0) against Celo mainnet,
// plus the doc's read calls on replay8004's real answers. No wallet, no writes.
import { createPublicClient, http, getAddress } from 'viem';
import { celo } from 'viem/chains';
import validationRegistryAbi from './abi.js';

const IDENTITY_REGISTRY = '0x8004A169FB4a3325136EB29fA0ceB6D2e539a432'; // Celo Mainnet (SKILL.md)
const VALIDATION_REGISTRY = '0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58' as const; // erc-8004-contracts scripts/addresses.ts

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

const VALIDATOR = '0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952' as const;
const ANSWERED = '0x4a5795f367e0ecf31add8c0f09c30d7b70e2daa81afcc547c8670580936ada15' as const;
const NEVER = ('0x' + '00'.repeat(31) + '01') as `0x${string}`;

const version = await verifyValidationRegistry(VALIDATION_REGISTRY);
console.log('verifyValidationRegistry(mainnet) ->', version);
try {
  await verifyValidationRegistry('0x0000000000000000000000000000000000000001');
} catch (e) {
  console.log('verify(no contract) throws as documented ->', (e as Error).message);
}
const [validatorAddress, agentId, response, responseHash, tag, lastUpdate] = await publicClient.readContract({
  address: VALIDATION_REGISTRY, abi: validationRegistryAbi, functionName: 'getValidationStatus', args: [ANSWERED],
});
console.log('getValidationStatus(answered) ->', { validatorAddress, agentId, response, responseHash, tag, lastUpdate });
const [count, avg] = await publicClient.readContract({
  address: VALIDATION_REGISTRY, abi: validationRegistryAbi, functionName: 'getSummary', args: [10143n, [VALIDATOR], ''],
});
console.log('getSummary(10143, [replay8004], "") ->', { count, avg });
try {
  const s = await publicClient.readContract({
    address: VALIDATION_REGISTRY, abi: validationRegistryAbi, functionName: 'getValidationStatus', args: [NEVER],
  });
  console.log('getValidationStatus(never requested) ->', s);
} catch (e) {
  console.log('getValidationStatus(never requested) reverts ->', (e as Error).message.split('\n')[0]);
}
