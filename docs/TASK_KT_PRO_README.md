# KT-Pro — Task Files Index (read me first)

KT-Pro is the set of upgrades that turns Neo-TDG / Lumen.AI from a one-shot
doc generator into a **persona-aware, evidence-grounded, RAG-queryable
knowledge system for orphaned codebases** — i.e. codebases whose original
developers have left, leaving only source code (and maybe a BRD) behind.

The work is specified across five files in this directory. Read and execute
them in the order below.

---

## 1. Reading order (do not skip)

| # | File | Why |
|---|------|-----|
| 1 | `TASK_KT_PRO_SANDBOX.md` | Stand up an isolated parallel instance (own ChromaDB, own SQLite, own ports) so none of the work below can damage production state. **Do this first.** |
| 2 | `TASK_KT_PRO_ORPHAN_MODE.md` | Product intent: "no original owner" reframing. Hard citation refusal, confidence tags, inheritor briefing, BRD gap analyser, institutional-memory write-back. These **amend** the upgrade file — read before touching code. |
| 3 | `TASK_KT_PRO_UPGRADE.md` | Main 9-phase execution plan (personas, DOCX bundle, Roslyn bridge, tree-sitter, self-critique, tenant, diagrams, eval, security). Apply orphan-mode amendments inline. |
| 4 | `TASK_KT_PRO_DOC_STYLE.md` | Consumed during Phase 2 of the upgrade. Contains the complete Python `DocxBuilder` class + style tokens + diagram rules that match the ESSA reference quality. |
| 5 | (existing) `TASK_AIRGAP_HARDENING.md` | Security baseline every new module must respect. |
| 6 | (existing) `TASK_OFFLINE_DIAGRAM_RENDERER.md` | Coordinate with Phase 7 of the upgrade. Do not duplicate. |

Reference artefacts (not executable, but useful) sit in `docs/reference/`:

- `ESSA_KT_Document_reference.docx` — the visual quality target.
- `essa_build_reference.js` — the docx-js source that produced the reference.
- `essa_seq_diagram.py`, `essa_other_diagrams.py`, `essa_design_diagrams.py`
  — Pillow diagram scripts to port into `src/crawler/diagram_renderer_pillow.py`.
- `fig_sequence.png`, `fig_current_vs_target.png`, `fig_persona_matrix.png`
  — sample outputs.

---

## 2. Execution sequence (git + sandbox, combined)

All work happens on branches off `main`. Every branch is tested with
`SANDBOX_NAME=kt-pro-v1 ./scripts/sandbox_start.sh` so production state is
never touched.

```
Step 0    Branch: feat/kt-pro-sandbox    ── execute TASK_KT_PRO_SANDBOX.md
          Merge to main when sandbox infrastructure is green.

Step 1    Branch: feat/kt-pro-phase-1    ── Phase 1 of UPGRADE + §2.1-2.5 of ORPHAN_MODE
          Sandbox diff against prod (expect tone + citations to change).
          Merge with kt_pro.personas flag OFF by default.

Step 2    Branch: feat/kt-pro-phase-2    ── Phase 2 of UPGRADE + TASK_KT_PRO_DOC_STYLE
          Visual compare generated DOCX with ESSA reference.
          Merge with kt_pro.multi_variant_docs flag OFF by default.

Step 3    Branch: feat/kt-pro-phase-3    ── Phase 3 of UPGRADE (Roslyn bridge, optional)
          Merge. Flag default OFF.

Step 4    Branch: feat/kt-pro-phase-4    ── Phase 4 of UPGRADE (tree-sitter + code chunker)
          Merge. Flag default ON (pure-Python, airgap-safe).

Step 5    Branch: feat/kt-pro-phase-5    ── Phase 5 of UPGRADE (self-critique)

Step 6    Branch: feat/kt-pro-phase-6    ── Phase 6 of UPGRADE (tenant awareness)
                                            + §3 of ORPHAN_MODE (provenance metadata)
                                            + §4 of ORPHAN_MODE (institutional memory)

Step 7    Branch: feat/kt-pro-phase-7    ── Phase 7 of UPGRADE (offline diagrams)

Step 8    Branch: feat/kt-pro-phase-8    ── Phase 8 of UPGRADE (eval harness)
                                            + §5 of ORPHAN_MODE (BRD gap analyser)

Step 9    Branch: feat/kt-pro-phase-9    ── Phase 9 of UPGRADE (security hardening)
                                            Reconcile TASK_AIRGAP_HARDENING items.

Final     Smoke test: scripts/smoke_kt_pro.sh against sandbox AND prod flags.
          Flip kt_pro.* flags to ON one tenant at a time.
```

---

## 3. Rules of engagement

- **Data is sacred.** Never write to `knowledge_base/chroma/` or
  `knowledge_base/conversations.db` from a branch build. Use `SANDBOX_NAME`.
- **Features are flag-gated.** Every new behaviour must be toggleable via
  `config.yaml : kt_pro.*`. Default OFF so prod is unchanged post-merge.
- **Evidence is required.** For personas L1/L2/L3 a citation ratio of 1.0
  is the bar; if the LLM cannot cite, **refuse** (do not warn).
- **Honest uncertainty.** Every paragraph in every generated doc carries
  HIGH / MED / LOW confidence. "I don't know" is an acceptable answer.
- **Airgap-first.** If a feature needs internet, redesign it. See
  `TASK_AIRGAP_HARDENING.md`.
- **ESSA-quality DOCX.** The style bar is non-negotiable. See
  `TASK_KT_PRO_DOC_STYLE.md` and the reference DOCX.

---

## 4. Definition of Done (whole initiative)

- [ ] All five KT-Pro TASK files have every `[ ]` checked.
- [ ] `scripts/smoke_kt_pro.sh` passes against sandbox.
- [ ] 20-question side-by-side diff (`scripts/sandbox_diff.py`) shows no
      regressions in answer quality or citation accuracy.
- [ ] Generated DOCX for the bundled `essa/` sample visually matches
      `docs/reference/ESSA_KT_Document_reference.docx`.
- [ ] `AIRGAP=1` startup + operation verified end-to-end.
- [ ] `README.md` top-level updated with a short "Designed for inherited
      codebases" section summarising the orphan-mode principles.
- [ ] Feature flags flipped ON in a pilot tenant; at least one real KT
      bundle delivered and accepted by a human reviewer.

---

*Last updated: 2026-04-24*
