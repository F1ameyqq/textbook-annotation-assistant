# 给 Codex 的启动提示词（直接粘贴）

你接管仓库 `D:/1800`（GitHub `F1ameyqq/textbook-annotation-assistant`）的任务 A30。先读这三份，再动手：

1. `docs/handoff/a30-to-codex-20261025/HANDOFF.md`
2. `docs/handoff/a30-to-codex-20261025/STATE.json`
3. `docs/tasks/A30-preexisting-tail-nodes-adoption-and-q12-retained-upgrade-20261025.md`（构建任务书，sha256 `3132a89043f1dc6c0a9af9036d897d5cdd5ba0924353aafc4d44ab2d876fe5bd`）

## 现状一句话

书 46007447 的第 "2 一定是直角三角形吗" 小节 16 题中 11 题已正式接受；Q12 为 `UNKNOWN_NO_RETRY`；Q13–16 平台已存在但归因 `UNKNOWN`；full16 导出/展示 `NOT_RUN`；`customer_ready=false`；`1800-a` PAUSED。上一位执行者（Claude）在离线构建开始前因余额/无产出被停止，构建**未开始**。

## 你接下来的五步

1. **离线构建**（按构建任务书六项增量）：产品新修订 → 冻结包 → 离线测试（含"真实工作区副本端到端"与"原工作区 sha 不变"）→ 只读 `--preflight`。产物路径见 HANDOFF §4 Step 1。
2. **独立代码评审**：按 `docs/tasks/A30-adoption-completion-code-review-20261025.md` 九项核验；执行者不得自我接受。
3. **绑定唯一 actual 授权**：值表见 HANDOFF §4 Step 3（head `28274dab…`、settings `56f07eb9…`、86 操作、保留组 `native/008bb17292dd4399a4d8e9d3f3351470`、`save_posts_max: 0`、`retained_reconcile_calls_max: 1`、`platform_contexts_max: 59`、`business_get_responses_max: 2997`、`official_bound_crop_downloads_max: 11`）。写进 `docs/coordination-state.json` 与私有 authority JSON。
4. **一次 actual**：`reconcile_retained`（0 平台调用）→ 校验 → `produce`（`ADOPT_EXISTING_MATCH`，0 POST）→ 校验 16 条 acceptance → 1 次原生导出 → 1 次本地展示 → 自有释放。
5. **独立 actual 评审 → 根接受**，再决定 `customer_ready` 与客户包。

## 红线（不得违反）

- 永不重发 Q12 / Q13–16；永不覆盖或删除四个先存尾节点（orders 39–42）。
- 不重放已接受的 11 次保存、旧九题、OCR、公式/模型、登录、已花额度。
- 凭据与 profile 内容不输出、不入库；`.local/` 不进 git；证书忽略只在明确授权的单次运行内使用。
- 不提交书籍、不对外发布；不提交 A03 长路径删除与无关脏文件。
- 每一阶段落盘报告/哈希；执行与评审/接受分离；`customer_ready` 只有拿到真实 full16 结果后才可能变 true。

## 工作方式

- 复杂任务用多个执行/评审会话并行，但**接受权在协调层**；每步都要可复核的 manifest（sha256/bytes）。
- 遇到 402/额度问题不要循环重试：记录 `BLOCKED_BY_BILLING` 并交回。
- 每推进一步更新 `docs/coordination-state.json` 的 A30 块与 `AGENTS.md` 的日期行。
