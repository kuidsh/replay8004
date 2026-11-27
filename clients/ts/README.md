# @replay8004/client

Ask the replay8004 validator to re-check an agent's claim on Celo, and read the result. Job bytes
and `requestHash` match the Python validator byte for byte (shared vectors in `tests/vectors/client.json`).

```ts
import { createWalletClient, createPublicClient, http } from "viem";
import { celoSepolia } from "viem/chains";
import { requestValidation, x402Claim, passes } from "@replay8004/client";

// after paying an x402 API: `accepted` is the PaymentRequirements you used, `paymentResponse` the header value
const claim = x402Claim(accepted, paymentResponse, { authorizationNonce: nonce });
const { hash, requestHash } = await requestValidation(wallet, {
  network: "celo-sepolia", validator: REPLAY8004, agentId: 42n, kind: "x402_settlement", claim,
});

// a marketplace or another agent gates on the on-chain result
const ok = await passes(publicClient, "celo-sepolia", 42n, REPLAY8004, "x402_settlement", 90);
```

Install: `npm install @replay8004/client viem`. `npm test` compiles and checks the shared vectors.
Source and docs: https://github.com/kuidsh/replay8004
