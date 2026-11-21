# Costs, revenue and payback

## Starting investment (non-AWS)
| item | cost | status |
|---|---|---|
| Prezenti Frontier application | US$0 | verified (no fee on the form) |
| CELO for gas: 50 CELO | ≈ US$2.75 | CELO US$0.0549 and 202 gwei (CeloScan gas tracker, 2026-11-21). Per `validationResponse`: 0.0036 CELO in the registry's March 2026 txs; a conservative 150k gas × 202 gwei ≈ 0.03 CELO ≈ US$0.0017 today. 50 CELO ≈ 1,600 responses at the conservative figure |
| Self Agent ID registration | US$0 (smart-wallet mode is gasless on mainnet per the Self docs) | docs; cost not explicitly stated |
| Domain for docs / status page (optional) | ≈ US$12/yr | estimate |
| **Total** | **≈ US$3–15** | |

## AWS per month (mx-central-1; us-east-1 list prices)
| service | volume | estimate |
|---|---|---|
| Lambda arm64 256 MB, every minute | 43.8k invocations × ~1.5 s × 0.25 GB ≈ 16.4k GB-s | US$0 (free tier: 1M requests + 400k GB-s) |
| EventBridge Scheduler | 43.8k invocations | US$0 (14M free per month) |
| DynamoDB on-demand | ≈ 44k writes + 44k reads | ≈ US$0.03 ($0.625/M writes, $0.125/M reads) |
| S3 Object Lock evidence | 1,000 bundles (≈ 3 KB) PUT + public GETs | ≈ US$0.01 |
| Secrets Manager | 1 secret | US$0.40 |
| CloudWatch Logs | < 1 GB, 30-day retention | ≈ US$0.50 |
| **Total** | | **≈ US$1/month** |

The Lambda and DynamoDB rates were read on 2026-11-16 and 2026-11-19 (see the opportunity log).
The S3 PUT, Secrets Manager and Logs prices are standard list prices that weren't re-read.
Volumes are estimates.

## Revenue
1. **Prezenti Season 3 Frontier grant.** Capped at US$15,000, paid in USDm (Mento USD): 20% at
   contract, 80% on milestones, 4 months to deliver. Applications close **2026-12-29**. Season 2
   outcomes came 2–4 weeks after submission. **Draft ask: US$12,000**, so US$2,400 at contract.
   *Season 2 funded 2 of 34 Frontier applications (≈ 6%).*
2. **Paid validations (v1.0).** x402-priced checks at ≈ US$0.01–0.05 each for high-volume agents.
   At US$0.02, 10k validations a month ≈ US$200 against ≈ US$1 of AWS plus ≈ US$17 of gas (conservative). *Not validated.*
3. **Follow-on pools.** Prezenti Anchor and Boost, or Celo ecosystem RFPs, once usage exists.

## Payback
Start ≈ US$3–15 plus ≈ US$1/month AWS. If an application submitted around 2026-12-15 is decided
in 2–4 weeks, the 20% upfront (≈ US$2,400) arrives around mid-to-late January 2027, inside the
3-month window, and covers the start costs plus years of AWS and gas.
**Success test:** a signed Frontier contract (20% paid), **or** 10+ external agents requesting
validations on Celo mainnet, plus one written commitment to pay.
