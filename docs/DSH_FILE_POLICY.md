# DSH 文件沙箱策略（会话工作区）

## File policy

**Current DSH file policy: workspace-write.** Any available operation enforced by the DSH file sandbox may modify files under the session workspace:

`D:\AICodes\ZR_AI_Coding\pythonProject_zr_aicoding`

Some platform temporary areas may also be writable.

## Approval policy

**Approval policy: ask.** Operations that require approval may ask through the configured answerers; **without an available answerer, the request fails closed.**

## Dev pipeline（一体化写码）

**File sandbox approval ≠ dev-pipeline step 5 gate.** DSH `ask` applies to workspace file writes, not to pausing the integrated coding pipeline for human confirmation.

**Step 5（写代码）** in the 8-step dev pipeline runs **automatically** with steps 1–4 and 6–8. Do **not** tell the user that step 5 will pause and wait for confirmation.

Canonical user notice and flags: repository root `config.yaml` → `dev_pipeline.integrated_coding` / `dev_pipeline.linked_run_user_notice`. ERP exposes the same via `GET /api/dev-pipeline/meta`.
