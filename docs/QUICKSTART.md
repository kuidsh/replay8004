# 5-minute quick-start: gate on replay8004 from your agent or contract

Three ways to use the result. All read the ERC-8004 ValidationRegistry (a preview spec: check the address with
`replay8004 doctor`); none needs an account with us. Examples use Celo Sepolia; the live mainnet validator is
`0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952` on `0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58`.

## 1. Your agent paid an x402 API on Celo: get the payment validated (TypeScript)
```ts
import { requestValidation, x402Claim } from "@replay8004/client";
const claim = x402Claim(accepted, paymentResponseHeader, { authorizationNonce });
const { requestHash } = await requestValidation(wallet, {
  network: "celo-sepolia", validator: REPLAY8004, agentId: MY_AGENT_ID, kind: "x402_settlement", claim });
// about a minute later the answer is on-chain (it waits for confirmations first)
```
The wallet must be the agent's owner or approved operator (registry rule).

## 2. Someone else wants proof before working with your agent (backend, Python or TS)
```bash
replay8004 gate --agent-id 42 --validator 0xREPLAY --tag replay:x402_settlement --min-count 3 --min-avg 90   # exit 0 = pass
replay8004 gate --agent-id 42 --validator 0xREPLAY --request-hash 0x... --min-score 100 --max-age 86400     # one claim
```
```ts
import { passes, claimStatus } from "@replay8004/client";
await passes(publicClient, "celo-sepolia", 42n, REPLAY8004, "x402_settlement", 90, 3n);
const { ok, reason } = await claimStatus(publicClient, "celo-sepolia", requestHash, { validator: REPLAY8004, agentId: 42n, maxAge: 86400n });
```

## 3. On-chain: inherit ReplayGate (Solidity)
```solidity
import "replay8004/contracts/ReplayGate.sol";
contract JobBoard is ReplayGate {
    constructor() ReplayGate(IValidationRegistry(0x8004Cb1BF31DAf7788923b405b754f57acEB4272), REPLAY8004) {}  // Celo Sepolia
    function bid(uint256 jobId, uint256 agentId)
        external onlyValidatedAgent(agentId, "replay:x402_settlement", 3, 90) { /* ... */ }
    function release(uint256 jobId, bytes32 paymentRequest)
        external onlyValidatedClaim(paymentRequest, agentOf[jobId], "replay:x402_settlement", 100, 1 days) { /* ... */ }
}
```
See `contracts/test/EscrowExample.sol`. ReplayGate holds no funds, has no owner and no upgrade path.

**What a track record means.** The agent's owner chooses which claims to submit, so `passes` tells you
"N submitted claims were checked, average S", not "every claim this agent made was honest". For money,
check the specific claim with `onlyValidatedClaim` / `claimStatus`.

Reason codes (same in all three): 1 wrong validator · 2 wrong agent · 3 not answered yet · 4 score too low · 5 too old · 6 wrong tag.

## Public status page
```bash
replay8004 status --evidence .replay8004/evidence --out site --validator 0xREPLAY   # status.json + index.html
aws s3 sync site/ s3://<evidence-bucket>/status/                                      # optional, operator's AWS
```
Built only from public evidence bundles, so anyone can rebuild it and compare.
