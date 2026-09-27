# DSH 文件沙箱策略（会话工作区）

## File policy

**Current DSH file policy: workspace-write.** Any available operation enforced by the DSH file sandbox may modify files under the session workspace:

`D:\AICodes\ZR_AI_Coding\pythonProject_zr_aicoding`

Some platform temporary areas may also be writable.

## Approval policy

**Approval policy: ask.** Operations that require approval may ask through the configured answerers; **without an available answerer, the request fails closed.**
