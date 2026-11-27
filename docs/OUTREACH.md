# Outreach drafts (David posts them; nothing here has been posted or sent)

Post only after the repo is public: every link points to it. v0.5 is deployed (2026-11-27), so the texts match the
live validator (x402 receipts, the `doctor` check); `pip install replay8004` and `npm install @replay8004/client` work. Facts as of 2026-11-27 (docs/MAINNET-STATUS.md).

---

## 1. First users: Celo mainnet agents that advertise an endpoint

Read 2026-11-27 from the Celo mainnet Identity Registry (`tokenURI` of the 135 newest agents, ids 10018–10154; 19 files unreachable, 8 not JSON). Kept: files whose `services` list an A2A, MCP or x402 endpoint. **Not contacted.** The registration files are self-declared; nothing in them is verified.

**x402 on Celo** column: "declared" = `x402Support: true` in the file. **yes** = the agent's owner address received USDC (`0xcebA…118C`) on Celo through `transferWithAuthorization`, the EIP-3009 call x402 `exact` settlements use (Blockscout, first 50 transfers). That is a signal, not proof: x402 can pay a `payTo` other than the owner. Duplicates: "The Defendant" (4 ids) and "Flux" (2) are one project each, so this is ~26 distinct teams.

| agentId | name | owner | endpoints | x402 on Celo |
|---|---|---|---|---|
| 10154 | Upswing BRL-Rail Agent | `0x4d9e88f9ba578d546cdb620219f8f519ff11b1c0` | A2A: `https://upswing-brlrail.upswing-labs.workers.dev/.well-known/agent-card.json`<br>MCP: `https://upswing-brlrail.upswing-labs.workers.dev/mcp`<br>X402: `https://upswing-brlrail.upswing-labs.workers.dev/v1/x402/fx-quote` | declared, no USDC seen |
| 10139 | Attestra | `0x3c80818c4eba036d54775bd0d8994d3dfc0b7a25` | X402: `https://attestra-pi.vercel.app/api/verify` | — |
| 10137 | Kovenra | `0x617b299ff63ab479283c895d2f3df95efef184fb` | X402: `https://kovenra.xyz/api/events/{slug}/buy` | — |
| 10134 | Spendguard Scout | `0xc17733165c47f80e56b1c6ed61e8988296ca8f82` | MCP: `https://spendguard-scout.liveapps.dev/mcp`<br>X402: `https://spendguard-scout.liveapps.dev/v1/brief/full` | declared; 2 USDC transfer(s) to the owner, none via EIP-3009 |
| 10116 | Vire — Autonomous Proof-of-Work & Multi-Corridor FX Settleme | `0x8ba43426d57e55c51c4fe7c4f8a68df3bf008089` | X402: `https://usevire.xyz/api/x402/verify` | declared, no USDC seen |
| 10107 | Errand | `0xc64d2153bd39053913667a5c2eec8250d8abc005` | X402: `https://errand-guard-celo.onrender.com/check` | declared, no USDC seen |
| 10094 | Tanda Payout Desk Agent | `0xed328f847ef33f35148513dcefb10069fce53725` | A2A: `https://tanda-desk.onrender.com/desk/order` | declared, no USDC seen |
| 10091 | Keel Payroll | `0x1b3577f1877c31cf1ed6a8d89ba0f7eb4aa6f389` | A2A: `https://github.com/yayguru/keel-payroll/.well-known/agent-card.json` (GitHub link, not a live endpoint) | — |
| 10084 | BotHire Verified Buyer (Concordium demo) | `0x480bcb24aaf72241688e391e7fe1dfb0df3e357f` | A2A: `https://www.bothire.io/agents/371ffd25-b25c-4e66-85a4-f81f1c527fa5/agent-card.json`<br>MCP: `https://www.bothire.io/mcp`<br>X402: `https://www.bothire.io/mcp/paid` | declared; 2 USDC transfer(s) to the owner, none via EIP-3009 |
| 10083 | BotHire Meme Desk | `0xfa90dfc6b44a36a9d24e6d5286a3d0f05ea91422` | A2A: `https://www.bothire.io/agents/571bb4a9-e32a-423a-961e-2b61e209e111/agent-card.json`<br>MCP: `https://www.bothire.io/mcp`<br>X402: `https://www.bothire.io/mcp/paid` | declared; 1 USDC transfer(s) to the owner, none via EIP-3009 |
| 10078 | NairaTag Sovereign Agent Network | `0xc519729bf6d15e5984702bba2c553f1c74a73c95` | A2A: `https://celo.nairatag.ng/api/a2a`<br>MCP: `https://celo.nairatag.ng/api/mcp` | — |
| 10072 | Altana Wallet Agent | `0x887eaf32db5328bd3f442747089985da72474bb8` | MCP: `https://docs.altana.network/.well-known/agent-card.json` | **yes**: 1 USDC transfer(s) to the owner via `transferWithAuthorization` |
| 10068 | P0 Agent Economy Index | `0xeca891e34b3e5873181fb779672564e198c55354` | A2A: `https://x402-bazaar-rank.x402-bazaar-rank-worker.workers.dev/.well-known/agent-card.json`<br>MCP: `https://x402-bazaar-rank.x402-bazaar-rank-worker.workers.dev/mcp` | **yes**: 24 USDC transfer(s) to the owner via `transferWithAuthorization` |
| 10060 | Tidewatch Verifier | `0xdcbfc06f5bccd311d3bb88c00ff1d5544386c1d8` | X402: `https://tidewatchapp.toradle.ai/api/pay/brief` | declared; 1 USDC transfer(s) to the owner, none via EIP-3009 |
| 10055 | Puente | `0x492dc215c8b7c88c5747ac79efa5d4eb894ae63b` | X402: `https://puente-agent-production-bb67.up.railway.app/v1/pay` | declared, no USDC seen |
| 10049 | Nomai Traveler Agent (Nomito) | `0x8bcf810436f39cb386d0137b738a516f44d8731c` | MCP: `https://nomaiapp.vercel.app/api/mcp` | declared, no USDC seen |
| 10045 | Pay Small Check | `0x8e23e92f0ec2bd6b8d004bc913c17ae412322d08` | X402: `https://pay-small-check.ahmardchain.workers.dev/api/checks` | declared, no USDC seen |
| 10044 | Meet | `0x9155deb21b6d7e8377c3ba2fe9ea6f0f5cf0a956` | X402: `https://usemeet.website/x402/rates` | declared, no USDC seen |
| 10043 | ADELANTO | `0xb93a6b8f3bf182780e0366be0ec6bd027c4cb2d1` | MCP: `https://adelanto.space/mcp`<br>X402: `https://adelanto.space/x402` | declared, no USDC seen |
| 10039 | ChambaPay — Tu Money, Sin Borders (LatAm FX & Payroll Agent) | `0x6268689797ca15256af2ce922836cd69940fa024` | A2A: `https://chambapay.celo.org/api/agent-card`<br>X402: `https://chambapay.celo.org/api/x402-execute` | declared; 50 USDC transfer(s) to the owner, none via EIP-3009 |
| 10038 | Flux | `0xfd3f8634674c8e8d3a3dec78b90bc9417ebef2f0` | A2A: `https://flux.mattt-dreamer.workers.dev/.well-known/agent-card.json` | not declared; 1 USDC in, none via EIP-3009 |
| 10037 | Flux | `0xfd3f8634674c8e8d3a3dec78b90bc9417ebef2f0` | A2A: `https://flux.mattt-dreamer.workers.dev/.well-known/agent-card.json` | not declared; 1 USDC in, none via EIP-3009 |
| 10034 | Contest Radar | `0x6859abd01f1686e9ddfe809cc69fab1054447457` | A2A: `https://contest-radar-celo.vercel.app/.well-known/agent.json`<br>MCP: `https://github.com/safwaankira/contest-radar/blob/main/scripts/mcp-server.mjs`<br>X402: `https://contest-radar-celo.vercel.app/api/scan` | declared; 37 USDC transfer(s) to the owner, none via EIP-3009 |
| 10033 | Cobrá Relayer | `0x9e828b877efcdb79b507ff6234d841a8265cccd5` | X402: `https://cobra-beige.vercel.app/api/x402/fx-quote` | declared, no USDC seen |
| 10029 | Cuota | `0x948dfa8f0f68573e77aaae237ce655f3fcf9d12f` | X402: `https://cuota-agent.onrender.com/pay/{agreementId}` | declared; 1 USDC transfer(s) to the owner, none via EIP-3009 |
| 10028 | Wayan Warrior | `0xaa86d03e6e8cc4c66c05c9661108f0f7efef74e3` | X402: `https://agents.wayanwarrior.pro/catalog` | declared; 1 USDC transfer(s) to the owner, none via EIP-3009 |
| 10023 | The Defendant | `0x326b4d133c5be653081d6f566eb56afa2ece2aa9` | A2A: `https://agent-on-trial.xyz/.well-known/agent-card.json` | declared, no USDC seen |
| 10021 | The Defendant | `0xf0b1029749da090c7a2601d3029f39472ff2a97e` | A2A: `https://agent-on-trial.xyz/.well-known/agent-card.json` | declared, no USDC seen |
| 10020 | The Defendant | `0x9a4f387b48108d4cb6960f132041726d7f02ada6` | A2A: `https://agent-on-trial.xyz/.well-known/agent-card.json` | declared, no USDC seen |
| 10018 | The Defendant | `0x1724707c52de2fa65ad9c586b5d38507f52d3c06` | A2A: `https://agent-on-trial.xyz/.well-known/agent-card.json` | declared; 10 USDC transfer(s) to the owner, none via EIP-3009 |

**Start with:** P0 Agent Economy Index (#10068, real x402 settlements on Celo), Upswing BRL-Rail (#10154) and Spendguard Scout (#10134) (x402 + MCP, and their product is already about verifying payments), BotHire (#10083/#10084), ChambaPay (#10039) and Contest Radar (#10034), which have the most USDC activity.

### DM template (one agent at a time; fill in the brackets; honest about what exists)
> Hi [name/team]. I saw [agent name] (ERC-8004 agent #[id] on Celo) lists a [MCP/A2A/x402] endpoint. I run replay8004,
> an open-source validator for ERC-8004's Validation Registry on Celo. Your agent (or its buyers) can send it a claim
> such as "this x402 payment settled" or "this tx paid ≥ X to Y". It re-checks the claim against Celo and answers
> on-chain with a 0-100 score plus public evidence anyone can recompute. Buyers and contracts can then read
> `getSummary(#[id], [validator], tag)` before they pay or trust you.
> It's free for agents building on Celo. So far it has answered 5 requests, all from my own test agent; you'd be one of
> the first outside users. I'm happy to send your first validation request with you (it takes one command from your
> agent's owner wallet) or to add a claim type you need. Repo: https://github.com/kuidsh/replay8004 · validator
> 0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952. No pressure if it isn't useful.

Don't promise anything the stack doesn't do: the daily cap is 20 answers (5 per agent), and paid mode is off.

---

## 2. Celo forum post (category: AI / Agents)

**Title:** Free validations for ERC-8004 agents on Celo: replay8004 is live on mainnet

Before November, Celo's ERC-8004 Validation Registry (`0x8004Cc84…AB58`) had 39 transactions, the last on 2026-03-19.
replay8004 is an open-source validator you can name in a `validationRequest` today.

**What it does.** Your agent claims something anyone can check on Celo: "this x402 receipt is real", "tx T paid ≥ X of
token K to B", "holder H had balance X at block N", or "contract C returned X at block N". replay8004 re-executes the
claim against Celo state and answers on-chain with a 0-100 score and a tag. It also publishes a hash-chained evidence
bundle whose keccak256 is the on-chain `responseHash`, so anyone can recompute the result. Claims it can't check yet stay
pending and are never scored 0.

**It's live.**
- Validator `0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952`, ERC-8004 agent #10141, Self Agent ID #218.
- 5 mainnet answers so far, 13-55 s after each request: a real payment (100), a false claim (0) and an overstated one (50).
  All are from my own test agent; I'm looking for the first outside agents.
- Every tx and evidence link: https://github.com/kuidsh/replay8004/blob/main/docs/MAINNET-STATUS.md

**Free for agents building on Celo**, with a daily cap per agent so nobody can drain the validator. Python:
```bash
pip install replay8004
replay8004 job x402-settlement --agent-id <id> --validator 0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952 \
  --requirements accepted.json --settlement "$PAYMENT_RESPONSE"     # prints the validationRequest calldata
```
TypeScript: `clients/ts` (`requestValidation()`, `x402Claim()`). MCP: `replay8004-mcp`. Contracts can gate on it with
`ReplayGate.sol`, or read `getSummary(agentId, [0xD2d6…5952], "replay:x402_settlement")`.

Note: the Validation Registry spec is still a preview, so replay8004 checks the registry on-chain before every run
(`replay8004 doctor`). Repo (Apache-2.0, 185 + 5 tests): https://github.com/kuidsh/replay8004. Which claim kinds do you
need next?

---

## 3. Discord message (Celo, AI agents channel), short

> 👋 replay8004 is live on Celo mainnet: an open-source validator for the ERC-8004 Validation Registry. Name
> `0xD2d6c6DEaaDF2A5868e8e0C17d674D49531C5952` in a `validationRequest`, and it re-checks your agent's x402 receipt,
> payment, balance or contract-read claim against Celo state. It answers on-chain with a 0-100 score and public,
> hash-chained evidence, usually within a minute. Free for agents building on Celo; looking for the first outside
> agents. Details: https://github.com/kuidsh/replay8004/blob/main/docs/MAINNET-STATUS.md. Happy to onboard yours; just reply here.

---

## 4. GitHub issue for `erc-8004/erc-8004-contracts` (draft; David opens it)

**Title:** Is `0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58` the canonical ValidationRegistry on Celo mainnet, and is a redeploy planned?

**Body:**
```markdown
Hi, and thanks for the registries.

`scripts/addresses.ts` lists `0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58` as the ValidationRegistry on Celo mainnet
(chainId 42220), but the README lists only the Identity and Reputation registries and says the validation part of the
spec will be revised. Celo's docs (Celopedia) therefore give no Validation Registry address.

I run replay8004, an open-source validator that answers on this address (5 answers so far, since 2026-11-26). Before
pointing more agents at it, I'd like to know:

1. Is `0x8004Cc84…AB58` the canonical ValidationRegistry for Celo mainnet, so builders can rely on it?
2. When the validation spec is revised, will this proxy be **upgraded in place** (it is an EIP-1967 proxy, implementation
   `0xdb31f5d9167f8ebc8b30fbbf814c4d297c2d7f99`), or will there be a **new deployment** at a new address?
   If a new one: is there a timeline, and will existing requests/responses be migrated?
3. Would you accept a README PR that lists the Celo address with a "preview" label?

What I check on-chain before every run (`getIdentityRegistry()` must return the Celo Identity Registry):
    {
      "ok": true,
      "network": "celo-mainnet",
      "rpc": "https://forno.celo.org",
      "validationRegistry": "0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58",
      "expectedIdentityRegistry": "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
      "rpcChainId": 42220,
      "head": 83858311,
      "identityRegistry": "0x8004a169fb4a3325136eb29fa0ceb6d2e539a432",
      "version": "2.0.0"
    }
(`replay8004 --network celo-mainnet doctor`, 2026-11-27). The proxy's first log is at block 58,396,736 (2026-02-05).
Celo Sepolia `0x8004Cb1BF31DAf7788923b405b754f57acEB4272` passes the same check.

Disclosure: I maintain replay8004 (https://github.com/kuidsh/replay8004, Apache-2.0).
```

---

## 5. Celo skills PR
Opened as https://github.com/celo-org/celopedia-skills/pull/126 (Celopedia; `celo-org/agent-skills` is archived). Details: docs/LAUNCH-STATUS.md (f).
It documents the Validation Registry in Celo's own `8004` skill and names no validator. replay8004's own skill lives in
this repo (`skills/replay8004/SKILL.md`) and is not part of that PR.
