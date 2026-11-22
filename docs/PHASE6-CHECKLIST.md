# Phase 6 checklist

Frontier requires open source, and the repository is private until step 2 is done. **Make the repo public, run
gitleaks on the full history again, then setAgentURI to a registration file that links to the repo. Steps 1-5
must be finished BEFORE the Frontier form is submitted.**

- [ ] 1. Run the tests, `cfn-lint infra/template.yaml`, and `gitleaks detect --log-opts="--all"` on the full history.
- [ ] 2. Make the repo public (David), then run gitleaks on the full history again.
- [ ] 3. Check from a logged-out browser or curl that the repo, the two testnet evidence files and at least one
      mainnet evidence URL open.
- [ ] 4. `setAgentURI(agentId, newURI)` to a registration file that links to the repo ("web" service) and lists this
      agent under `registrations` (agentId + `eip155:42220:0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`).
      David approves the tx.
- [ ] 5. Read `tokenURI(agentId)` back and check the decoded JSON.
- [ ] 6. Fill PROPOSAL.md, then submit the form (David) by 2026-12-15. The window closes 2026-12-29.
