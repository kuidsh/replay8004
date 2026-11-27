# Paid validations (v0.5): x402 credit packs

**Status:** built and tested offline (`tests/test_billing_paywall.py`). The worker's billing hook is deployed on both
stacks since 2026-11-27 but inactive (`PaidMode=0`); the paywall Function URL is not deployed. Celo Sepolia first; the
template refuses `PaidMode=1` on mainnet.

## The offer
| | price | per validation | what it covers |
|---|---|---|---|
| Free tier | US$0 | — | 25 answered validations per agent per month |
| Open-source allowlist | US$0 | — | unlimited (`FreeAccounts`, chosen by the operator) |
| `starter` pack | 5 USDC | US$0.020 | 250 validations, no expiry |
| `scale` pack | 40 USDC | US$0.016 | 2,500 validations, no expiry |

An account is one ERC-8004 agent on one chain (`<chainId>:<agentId>`). Anyone may top it up, usually
its owner. A credit is used when replay8004 **answers** a request for that agent, including a 0 for an
invalid job (it still costs gas and evidence). A request that isn't covered is **held, not answered**,
for up to 7 days, then expires unanswered. An unpaid request never puts a 0 on an agent's record.

## Why packs, not a payment per validation
Celo's x402 facilitator charges the seller **gas at cost plus 0.3% of the payment** for each
settlement, and its config lists **4,000 micro-USD (US$0.004) per tx** (GET
`https://api.x402.celo.org/api/config`, read 2026-11-26; 100 free settlements on mainnet, 1,000 on
Sepolia). On a single US$0.02 call that is ≈ 20% of revenue. A 5 USDC pack settles once:
≈ US$0.004 + US$0.015 = ≈ US$0.019, or 0.4%.

## Unit economics (per 250-validation pack)
| line | amount | status |
|---|---|---|
| Revenue | US$5.00 | price we set |
| Facilitator fee (gas + 0.3%) | −US$0.02 | Celo facilitator config, 2026-11-26 |
| Validator gas, 250 × `validationResponse` | −US$0.43 at the conservative 150k gas × 202 gwei (≈ US$0.0017 each); −US$0.05 at March 2026's 0.0036 CELO | CeloScan 2026-11-21; CELO US$0.0549 |
| AWS (whole service, not per pack) | ≈ US$1/month | COSTS.md |
| **Margin per pack** | **≈ US$4.55** | estimate |

Break-even on AWS is 1 pack a month. Recovering a US$15 start plus 3 months of AWS (≈ US$18) needs
**4 packs in 3 months**, or 1 pack from 4 different builders. *No buyer has been asked yet.*

## Buying credits (x402 v2)
```
POST /v1/credits/42/starter                     → 402, PAYMENT-REQUIRED: base64(PaymentRequired)
POST /v1/credits/42/starter  PAYMENT-SIGNATURE  → 200 credited | 202 pending | 402 rejected | 409 reused
GET  /v1/accounts/42                            → freeRemaining, purchased, usedPaid, creditsRemaining
GET  /v1/pricing
```
Any x402 v2 client works (e.g. `@x402/fetch` against the Function URL). The paywall:
1. requires `accepted` to equal the issued requirements: scheme `exact`, `eip155:<chain>`, amount,
   USDC address, `payTo` (EIP-712 domain `USDC` / `2`, per Celo's docs);
2. requires `authorization.to == payTo` and `authorization.value == price`, and a 32-byte nonce;
3. calls the facilitator `/verify`, then `/settle` (`X-API-Key`);
4. **re-checks the settlement on Celo with replay8004's own `x402_settlement` checker** (Transfer
   payer → payTo of the full price, the EIP-3009 nonce consumed in that tx). A facilitator that
   reports more than moved gets nothing credited;
5. credits once per tx hash **and** per authorization nonce. A tx our RPC hasn't seen yet is
   `pending` and is credited by `reconcile()` on a later call; one that never appears is rejected
   after 60 tries.

The paywall Lambda holds **no key that can move funds**: USDC goes straight from the payer to
`payTo` by EIP-3009, and the facilitator pays the gas. Its only secret is the facilitator API key.

## Operator steps (David)
1. Create the facilitator API key: connect the **payTo** wallet at `https://x402.celo.org`, click
   *Create API key*, sign the off-chain message (no gas). This is an account on Celo's facilitator,
   so it is David's step. Store it in Secrets Manager.
2. Give the deployer user `lambda:CreateFunctionUrlConfig`, `lambda:UpdateFunctionUrlConfig`,
   `lambda:DeleteFunctionUrlConfig` and `lambda:AddPermission` on `function:replay8004-*`
   (infra/iam/deployer-policy.json does not have them yet; the worker never needed a Function URL).
3. Deploy the **Sepolia** stack with every current parameter plus
   `PaidMode=1 PayTo=0x... FacilitatorKeySecretArn=arn:...` (PayTo is a fresh wallet, not the validator).
   This creates `replay8004-sepolia-paywall` and its URL (stack output `PaywallUrl`).
4. Buy a `starter` pack on Sepolia with test USDC (Circle faucet) and check `GET /v1/accounts/<id>`.
5. Mainnet: the template **refuses** `PaidMode=1` with `Network=celo-mainnet` (rule
   `PaidModeNotOnMainnetYet`). Lifting it is a deliberate template change after step 4 works and after
   the Frontier decision. The live mainnet validator stays free (`PaidMode=0`, the default).

## Mexico
Pack sales are income from services provided by David. Sales paid in USDC are taxable in MXN at
the exchange rate on the day received; a CFDI is normally required for each sale, and foreign
buyers get a CFDI with the generic foreign RFC (`XEXX010101000`). This is not a regulated
financial service under Ley Fintech: no custody, no exchange, no payments for third parties; the
buyer pays David for a service. Confirm regime and invoicing with a contador before the first
mainnet sale.
