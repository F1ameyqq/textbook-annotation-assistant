# C01 有界返修 R1：平台引用闭合

日期：2026-10-16。状态：待原执行对话处理。此任务沿用 C01 原执行工作树和独立验收对话，不新建重复任务。主调度已复现两项失败，结论 REWORK，不释放 A01/A02/A04。

## 版本与证据

- 返修基线：`b8c4341d277d205dddfae22b26c245b646a1cea2`，实现版本 `4660e8e4120af1b8550c2e0ee3dd02593aa38aac`。
- 工作树：`C:\Users\ASUS\.codex\worktrees\c01-contracts\1800`，分支 `codex/c01-contracts`。原始 workflow_commit `30bc00cbaa3e40d78fd8d5cac98e81bd354763b2` 继续适用，本任务单是附加返修要求。
- [独立验收报告](C01-review-report.md)。原执行报告位于上述 worktree 的 `docs/tasks/C01-execution-report.md`，主工作区尚未集成。
- [主调度复现记录](../evidence/C01/coordinator/reference-gaps-reproduced.json)。两份输入 SHA-256 分别为 `91315dde2e4cdefdb0069301047c0e02f35123ca84439c1030ca19a968710101`、`d0bc9967abae687a450975d25043183563f3226676c6c003b46e4ec96e55366d`。
- [F1 完整输入](../evidence/C01/review/counterexamples/snapshot_question_missing_directory/input.json) 与 [F2 完整输入](../evidence/C01/review/counterexamples/action_missing_platform_question/input.json) 均包含同目录资源。两例重算全部依赖摘要后，完整资源校验及 `assert_plan_ready` 仍放行；不是坏摘要导致的失败。

## 必须修复的两项

1. **F1：PlatformSnapshot 的题目到目录引用不闭合。** 每个题目的 `directory_id` 必须属于同一快照的目录集合；缺失时返回可定位字段错误。正常目录引用仍通过。不以宽松默认值或跳过规则放行未知目录。
2. **F2：ApplyPlan 的动作到平台题目引用不闭合。** 非空 `target.platform_question_id` 必须存在于计划绑定快照；核对其与内部目标、已存在外部映射的关系，拒绝错目标。null 作为新题目标的合法路径保持可用；不得把所有新题一律要求已有平台 ID。存在目标、空目标、悬空目标和错误映射都需明确正反例。

实现范围限于上述校验、必要的定向回归及对既有语义的说明。可以检查与 F1/F2 直接相关的现有外部映射，不能扩展为 executor、真实平台探测、重构公共类型或 A03 恢复。若发现必须新增合同字段/改变语义的阻塞，先给最小提案和失败例，不自行冒充共同确认。

## 交付与复验

- 在原分支增量提交，不重置、强推或覆盖其他改动。不得修改根目录的独立验收报告、反例或调度状态，也不改原始固定样例来隐藏失败。
- 在修复提交上运行两份完整反例：CLI 应以非零退出，公开 API 给出与悬空字段相关的错误；重封签的错误目标映射同样拒绝。正常样例、合法既有目标及新题 null 目标通过。
- 重跑受影响合同测试和四组跨目录消费；保留 UNKNOWN、防重复、两份 PASS、路径和摘要检查。必要时增加测试，不弱化原有门槛。
- 新增 `docs/tasks/C01-rework-R1-report.md`，记录精确修复提交、环境、命令、结果、两份反例前后差异、新增正反例、未解决项。报告可以单独提交，最终回执同时给代码提交和交付 HEAD。
- 交付后保持工作树干净并停止修改，状态交回 REVIEW。明确本轮未启动浏览器/profile、未读取凭据、无模型调用/费用；未推送、未集成、未代表 B 确认。
- 原独立验收对话在新交付完成后进行 R1 复验，保留首轮失败证据；主调度核对并复现后才决定是否 ACCEPTED。若仍失败，记录剩余具体缺口，再决定下一次有界修复，不无限重复相同尝试。
