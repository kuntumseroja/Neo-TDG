# Contributing to Lumen.AI / Neo-TDG

Thanks for working on Lumen. This guide is deliberately short and tactical —
it covers the branch-sandbox-flag workflow that protects production data
during the ongoing KT-Pro upgrade. For full design context, read
`docs/TASK_KT_PRO_README.md` first.

---

## 1. Golden rules

1. **Production data is sacred.** Never run branch code against the prod
   ChromaDB (`knowledge_base/chroma/`) or the prod conversation DB
   (`knowledge_base/conversations.db`). Always set `SANDBOX_NAME` when
   running a feature branch.
2. **Airgap-first.** Every new module must work under `AIRGAP=1`. If it
   needs internet, redesign it. See `docs/TASK_AIRGAP_HARDENING.md`.
3. **Features behind flags.** New behaviour lands `false` by default in
   `config.yaml : kt_pro.*`. Merging to `main` does not change production
   behaviour until an operator flips the flag for a tenant.
4. **Evidence or silence.** Answers without citations are rejected for the
   L1/L2/L3 personas. See `docs/TASK_KT_PRO_ORPHAN_MODE.md §2.1`.

---

## 2. The workflow, end to end

```bash
# 1. Start fresh
git checkout main && git pull

# 2. Branch per phase or per logical unit
git checkout -b feat/kt-pro-phase-1

# 3. Do the work locally. Run against a sandbox — never prod.
export SANDBOX_NAME=kt-pro-v1
export AIRGAP=1
./scripts/sandbox_start.sh

# 4. Iterate. When you have a change, test it.
pytest -q
./scripts/smoke_kt_pro.sh || true   # available after Phase 2 lands

# 5. Compare answers against production before opening the PR
python scripts/sandbox_diff.py \
    --sandbox kt-pro-v1 \
    --personas architect,developer,l2 \
    --questions-file tests/eval/goldens.yaml \
    --out diff_report.md

# 6. Commit, push, open PR
git add -A
git commit -m "feat(kt-pro/phase-1): personas + citation enforcement"
git push -u origin feat/kt-pro-phase-1
gh pr create --fill --label "kt-pro"

# 7. Wait for CI to pass; attach diff_report.md to the PR; request review.

# 8. After approval, squash-merge.
gh pr merge --squash --delete-branch
```

---

## 3. Branch naming

| Pattern | When |
|---|---|
| `feat/kt-pro-phase-N-short-description` | one phase of the KT-Pro plan |
| `feat/<area>` | new feature unrelated to KT-Pro |
| `fix/<issue>` | bug fix |
| `chore/<area>` | build / dev-experience changes |
| `docs/<area>` | docs-only changes |

Example: `feat/kt-pro-phase-2-docx-builder`.

---

## 4. Commit messages

Use Conventional Commits. For KT-Pro work, scope commits with the phase:

```
feat(kt-pro/phase-1): persona registry + citation validator
feat(kt-pro/phase-2): DocxBuilder + six-persona bundle
fix(kt-pro/sandbox): correct port offset for roslyn bridge
docs(kt-pro): clarify merge vs flag-flip separation
```

When a commit implements a section of a TASK file, reference it in the
body:

```
Implements docs/TASK_KT_PRO_UPGRADE.md §7.3 (drafter).
Closes acceptance criteria bullets 1, 2, 4 of §7.10.
```

---

## 5. Running tests locally

```bash
# Fast path
pytest -q

# With eval harness (Phase 8+)
pytest tests/eval -q

# With airgap mode forced on
AIRGAP=1 SANDBOX_NAME=ci pytest -q
```

Unit tests **must not** make LLM or network calls. Use a fake / stub LLM
from `tests/fakes/` and mock `requests`. CI enforces airgap mode.

---

## 6. Pull requests

Every PR against `main` inherits the template in
`.github/pull_request_template.md`. Fill it in. The CI
`guardrails → PR template fields present` step will fail if required
sections are missing.

CI must pass before merge:

- `lint` — ruff (non-blocking during early KT-Pro phases; becomes blocking
  later).
- `test` — `pytest -q` + `pytest tests/eval -q` in airgap mode.
- `guardrails` — no hard-coded state paths, no hard-coded "CoreTax" in
  prod code, no new outbound URLs in KT-Pro modules, PR template sections
  present.
- `docx_smoke` — generated DOCX round-trips cleanly through `python-docx`.

Branch protection should be configured on `main` (GitHub → Settings →
Branches):

- Require PR before merging.
- Require status checks to pass (select the four jobs above).
- Require branches to be up to date before merging.
- Require conversation resolution.
- Apply rules to administrators.
- (Optional) Require Code Owner approval — see `.github/CODEOWNERS`.

---

## 7. Reviewing

Reviewer checklist:

- [ ] CI green.
- [ ] PR template fully filled in.
- [ ] Acceptance criteria from the referenced TASK file actually met
      (open the file alongside the diff).
- [ ] New behaviour behind a feature flag that defaults to `false`.
- [ ] No hard-coded state paths / ports / tenant names.
- [ ] No outbound network calls; `AIRGAP=1` honoured.
- [ ] Tests added for new code paths; existing tests still pass.
- [ ] Sandbox diff report attached and shows no regression.
- [ ] If prompts changed: at least one eval scenario covers the change.
- [ ] Rollback plan in the PR body is realistic (which flag, which
      commit).

If any box is unchecked, request changes — don't approve.

### 7.1 Solo-reviewing

If you are the only developer available, **wait at least one hour** after
opening the PR, then re-read the diff as if someone else wrote it, using
the checklist above. Only approve if you'd approve the same change from
someone else.

---

## 8. Merging

**Strategy: Squash and merge.** One clean commit lands on `main` per PR,
with the PR title as the commit message. This keeps `git log main`
readable. Auto-delete the source branch.

**Never force-push to `main`.** Never skip CI. Never merge with a red
check, even trivially.

---

## 9. After merge

Merging does **not** deploy. It does **not** change prod behaviour (flags
default to `false`). Deployment is a separate manual or scheduled action.
Flag-flipping happens per tenant after sandbox validation — see
`docs/TASK_KT_PRO_README.md §2`.

---

## 10. Getting stuck

1. Read the relevant section of the TASK file again — most questions are
   already answered there.
2. Ask in the team channel; paste the exact symptom + what you tried.
3. If you change something risky (prompts, reranker weights, chunker),
   open the PR as Draft and request early feedback before finishing.

---

*Last updated: 2026-04-24*
