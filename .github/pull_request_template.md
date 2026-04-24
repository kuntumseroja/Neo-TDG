<!--
Thanks for opening a PR!
Keep the template intact — the CI job checks for these sections.
Delete inline comment lines that don't apply.
-->

## Summary

<!-- one-line description of what this change does -->

## KT-Pro task references

<!-- if this PR implements part of the KT-Pro plan, link the task file(s) and sections -->
- [ ] `docs/TASK_KT_PRO_UPGRADE.md` § …
- [ ] `docs/TASK_KT_PRO_ORPHAN_MODE.md` § …
- [ ] `docs/TASK_KT_PRO_DOC_STYLE.md` § …
- [ ] `docs/TASK_KT_PRO_SANDBOX.md` § …
- [ ] N/A — hotfix / infra change outside KT-Pro

## Acceptance criteria met

<!-- copy the checklist from the relevant TASK file and tick only what is actually done -->

- [ ] …
- [ ] …

## Sandbox validation

<!-- required for every change that touches chunks, prompts, retrieval, or generated docs -->

- Sandbox name: `kt-pro-v?`
- Sandbox diff report: <attach or link>
- `AIRGAP=1 ./scripts/sandbox_start.sh`: PASS / FAIL
- `./scripts/smoke_kt_pro.sh` against sandbox: PASS / FAIL

## Feature flag

<!-- any new behaviour must be toggleable -->

- New flag(s): `kt_pro.<name>`
- Default value in `config.yaml`: **false** (production behaviour unchanged on merge)

## Airgap check

- [ ] No new outbound URL in source (grep-verified)
- [ ] No new non-loopback listener
- [ ] New module honours `AIRGAP=1` (refuses / degrades gracefully when offline)
- [ ] Follows `docs/TASK_AIRGAP_HARDENING.md`

## Risk / rollback

<!-- which flag to flip to disable, or which commit to revert, or 'none' for docs-only -->

## Screenshots / artefacts (if UI or doc output changed)

<!-- drag-and-drop PNGs of the diff, or link to a generated DOCX -->
