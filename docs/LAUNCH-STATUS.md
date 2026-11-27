# Launch checklist status (checked 2026-11-27)

Every "done" below was verified by an on-chain read, the GitHub API, the npm/PyPI registries or the files, on
2026-11-27. Nothing was sent, published, pushed or posted. Steps marked **David** are his alone.

| | item | status | evidence |
|---|---|---|---|
| a | Validator registered as an ERC-8004 agent | **done** (agent **#10141**); registration file **updated** 2026-11-27 | below |
| b | Self Agent ID | **done** (**#218**) | below |
| c | Public GitHub repo, green CI, matching what's deployed | **done** 2026-11-27: public, CI green, `main` = deployed v0.5, site on GitHub Pages | below |
| d | `@replay8004/client` on npm, `replay8004` on PyPI | **prepared**, not published; both names unclaimed | below |
| e | Status page published | **built** (`./site`), not published; path proposed | below |
| f | celo-org/agent-skills PR | **ready** on a local branch, typechecked, verify code tested on mainnet; not opened | below |
| g | GitHub issue to erc-8004/erc-8004-contracts | **drafted** | docs/OUTREACH.md §4 |
| h | Celo forum + Discord posts | **drafted** | docs/OUTREACH.md §2–3 |
| i | KarmaGAP profile, Celo address for USDm | **missing** (David) | steps below |

## a. ERC-8004 registration: done
- Identity Registry `0x8004A169…a432`: `balanceOf(0xD2d6…5952) = 1`; one `Registered` event with owner = the validator:
  **agent #10141**, block 83,797,743, [tx 0x2137…3604](https://celoscan.io/tx/0x213749ece02ac2aac6a00b656669c892fd23813363cd0bf754e38e4f91963604).
  `ownerOf(10141)` = the validator. The test agent #10143 is owned by `0x070a…8647`.
- Its current file (on-chain `data:` URI, 917 chars) is the 0.1.1 format: name, description, one `validator` service.
  It has no repo link, no tags, no x402 kind and no `registrations[]` back-reference.
- **Updated 2026-11-27** ([tx 0x13cdf93c…f4c1](https://celoscan.io/tx/0x13cdf93c1f2f6d4bdac3f0c24c54686b3b664fccaf3be3cd1cd1a18d9ee6f4c1), block 83,891,414, 0.16496 CELO, sent by David with
  `scripts/register_agent.py --update-agent-id 10141`; `tokenURI(10141)` now equals the file below byte for byte). It was
  generated with `replay8004 identity`:
  `docs/mainnet/registration-10141-v05.json` (1,313 bytes) and `docs/mainnet/setAgentURI-10141-v05.calldata.txt`
  (`setAgentURI(10141, data:application/json;base64,…)` to `0x8004A169…a432`). It adds the repo, the
  `replay8004-validator` service with its 4 tags, the evidence base URL and `registrations[{agentId: 10141}]`.
  Estimated 829,872 gas (≈ 0.168 CELO); it used 814,606 gas (0.16496 CELO, ≈ US$0.01).

## b. Self Agent ID: done
SelfAgentRegistry `0xaC3DF9ABf80d0F5c020C06B04Cced27763355944` (`name()` = "Self Agent ID", `symbol()` = "SAID"):
`ownerOf(218)` = `0xd2d6…5952`, `balanceOf(validator)` = 1. Nothing more to do. To re-check yourself: open the Self app,
your agent #218 should list the validator address. If Self ever asks you to re-verify (passport expiry), use the same app.

## c. Public GitHub repo: missing
- **Public since 2026-11-27**; landing page on GitHub Pages: https://kuidsh.github.io/replay8004/ (`index.html`, `.nojekyll`).
- **Done 2026-11-27:** `v0.5-merge` pushed; CI passed all three jobs (Python 3.11, 3.12, TypeScript; solc builds and the
  EVM tests included); `main` fast-forwarded to `1d83aa5` and pushed; that code is deployed to both stacks (06:28 and
  06:37 UTC). So `main` matches what's deployed.
- Before making it public (done 2026-11-27): gitleaks over all 28 commits finds no leaks; no `.env`, key or keystore file
  was ever committed; the AWS account ID appears in no tracked file or commit; commits use the GitHub no-reply email.
- Remaining: nothing.

## d. npm and PyPI: prepared, not published
- `https://registry.npmjs.org/@replay8004%2fclient` → 404 and `https://pypi.org/pypi/replay8004/json` → 404: both
  names are free today. The `@replay8004` scope needs an npm organization named `replay8004` (free for public packages).
- PyPI: `python -m build` → `replay8004-0.5.0-py3-none-any.whl` (28 files) + sdist; `twine check` PASSED.
- npm: `clients/ts` 0.5.0, `npm pack --dry-run` = 4 files (`dist/src/index.{js,d.ts}`, README, package.json); 5 tests pass.
  Changed today: version 0.3.0 → 0.5.0, and `files` now leaves out the compiled tests.
- **David** (free; needs accounts with 2FA):
  ```
  python -m build && python -m twine upload dist/*          # PyPI API token
  npm org create replay8004   # or create it on npmjs.com
  cd clients/ts && npm ci && npm run build && npm publish --access public
  ```
  Publish from the commit you deploy, after the repo is public (the READMEs link to it).

## e. Status page: built, not published
`./site/index.html` + `status.json`, rebuilt from the 5 public bundles (chain intact, 5 answered, pass rate 60%).
**Proposed path:** `s3://replay8004-mainnet-evidencebucket-exgfx3xqkhfr/evidence/status/`, served at
`https://replay8004-mainnet-evidencebucket-exgfx3xqkhfr.s3.us-east-1.amazonaws.com/evidence/status/index.html`.
- Why there: the bucket policy already allows public GET on `evidence/*` only, so **no template or policy change**.
  The bucket has Object Lock enabled but **no default retention** (`get-object-lock-configuration`), so an upload
  without lock headers stays replaceable. `verify-evidence` and the status builder read only `0x*.json`, so a
  `status/` folder doesn't disturb them.
- Alternative: GitHub Pages from the public repo (needs a rebuild step in CI).
- **David** (≈ US$0.00; 2 PUTs):
  ```
  aws s3 cp site/index.html  s3://replay8004-mainnet-evidencebucket-exgfx3xqkhfr/evidence/status/index.html  --content-type "text/html; charset=utf-8" --cache-control max-age=300 --profile replay8004-deployer-mfa --region us-east-1
  aws s3 cp site/status.json s3://replay8004-mainnet-evidencebucket-exgfx3xqkhfr/evidence/status/status.json --content-type application/json --cache-control max-age=300 --profile replay8004-deployer-mfa --region us-east-1
  ```
  Rebuild it after new answers (`replay8004 status --evidence <synced folder> --out site …`); automating it is milestone 2.

## f. celo-org/agent-skills PR: ready, not opened
- Cloned `celo-org/agent-skills` to `../agent-skills-pr` (upstream `main` is still `c414cbb`, the patch's base), branch
  `validation-registry-docs`, `git apply` of `integrations/agent-skills/0001-8004-validation-registry.patch`: **clean**.
  Left uncommitted so David authors the commit. `skills/8004/SKILL.md` is 488 lines (limit 500). The three changed files
  equal the copies under `integrations/agent-skills/skills/8004/` (ignoring CRLF).
- Typecheck: `snippet-check/` (now self-contained: `package.json`, `abi.ts`) passes strict `tsc` (viem 2.21.54, TS 5.6.3).
  The doc's code blocks differ from what was typechecked only in the 3 documented lines.
- **Mainnet, read-only** (`npm run live` = `verify_live.ts`): `verifyValidationRegistry(0x8004Cc84…AB58)` → `2.0.0`; it
  throws "no contract at this address" on an empty address; `getValidationStatus` of a real answer → score 100, tag
  `replay:erc20_transfer`; `getSummary(10143, [validator], "")` → (5, 70); a never-requested hash reverts (`"unknown"`),
  as the reference says.
- **David** (free): fork, then commit and open the PR from `../agent-skills-pr`, as in `integrations/agent-skills/PR.md`
  ("How to submit"). The fork creates a public repo under your account.

## g–h. Drafts
GitHub issue (with the doctor output), forum post, Discord message and a DM template: docs/OUTREACH.md. v0.5 is
deployed, so the texts match the live validator; post only after the repo is public (every link points to it).

## i. KarmaGAP profile and a Celo address for USDm (David)
**Payout address first** (the grant is paid in **USDm**, Mento Dollar, `0x765DE816845861e75A25fCA122bb6898B8B1282a` on
Celo; `symbol()` = USDm, 18 decimals, read 2026-11-27):
1. Create a **new** wallet you control and that is not the validator (its key is in AWS and your secrets store): a hardware
   wallet, or a fresh software wallet (MetaMask/Valora/Rabby) on an offline-backed-up seed. Don't reuse a test wallet.
2. Write the seed on paper; never paste it into a tool, chat or file.
3. Add Celo mainnet (chainId 42220, RPC `https://forno.celo.org`). Check the address on CeloScan. Holding USDm needs no
   gas; moving it later needs a few cents of CELO (or USDm via fee abstraction).
4. Use this address for the form's "Grant L2 delivery address" and as `PayTo` if paid mode ever goes live.

**KarmaGAP** (free):
1. https://gap.karmahq.xyz → connect the **payout** wallet (not the validator) → *Create project*.
2. Name `replay8004`; description = FRONTIER-SUBMISSION.md text A; links: GitHub, X, website/status page.
3. Add the 4 milestones from PROPOSAL.md (0: contract signed; 1–3 with their deliverables and dates).
4. If it asks you to choose a community or program, pick Celo / Prezenti Frontier when offered. Copy the profile URL
   into the form. (Karma may ask you to sign an attestation; if it asks for gas, it is cents of CELO.)
