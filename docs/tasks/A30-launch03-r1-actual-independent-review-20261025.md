# A30 launch03-r1 实际单次运行独立复核

## 角色与独立性

- 复核上下文：`a30-review-actual-r1-20261025-01`（新开 Agent 上下文，思考强度 max）。
- 不得是执行者 `a30-exec-20261025-01`，不得修改任何输入、工作区、设置、产品、包、live 输出。
- 独立性限制：同一模型家族、不同会话；原 Codex 复核额度耗尽，用户已批准 M1。必须写入结论，不得称为原正式复核或不同模型供应商。
- 本次复核的对象是**一次已经发生、不可重试的真实运行**。不得重跑、不得补发、不得调用平台/浏览器/Edge/OCR/模型/登录。

## 输入

- 批准与派发：`docs/approvals/A30-coordinator-takeover-and-m1-20261025.json`；`docs/evidence/coordinator/a30-launch03-r1-dispatch/dispatch-intent.json`（`ee56538f…`）。
- 已接受差量：私有 `D:/1800-private/a30-launch-r1-review-20261025-01/decision.json`（`24498ac3…`，结论 `ACCEPTED_OFFLINE_EXECUTOR_IDENTITY_DELTA_ONLY`）；公开 `docs/evidence/A30/review/launch-r1-01/REVIEW.md`（`6a8a4b78…`）。
- 唯一 authority：`D:/1800-private/a30-root-20261025/authority-a30-full16-launch-r1-20261025-01.json`（`10e9330b…`）。
- 冻结包：`D:/1800-private/a30-full16-reconcile-continue-launch-fixed-20261025-01`（manifest `55a6af31…`、entry `fbfa8673…`、binding `35f87bd5…`、plan `eabbb944…`）。
- live 输出：`D:/1800-private/a30-full16-reconcile-continue-live-20261025-01/`（`launch-intent.json`、`child-entered.json`、`outer-outcome.json`、`reconcile-result.json`（如有）、`production-result.json`、`console.stdout.txt`、`console.stderr.txt`、`console.exit.txt`、`production-outer/`）。
- 先前已接受的实际复核：`docs/evidence/A30/review/full16-actual-02/REVIEW.md`（11/16、Q12 UNKNOWN_NO_RETRY）。

## 必须核验

1. **授权绑定**：authority 字节哈希等于 dispatch intent；schema `A30Full16ReconcileContinueAuthority/v1`、`activated=true`、`executor="a30-exec-20261025-01"`、窗口 ≤1800 秒且运行时间落在窗口内；entry/binding/plan 哈希等于冻结包；`limits` 与 `expected_cost` 与 binding/plan 完全相等；16 个 selected_keys 顺序一致；≥4 个 root receipts 哈希匹配。
2. **单次性**：`launch-intent.json` 恰一份、`spent=1/remaining=0/automatic_retry=false`；`child-entered.json` 恰一份；无第二次 outer/child、无 retry 目录/文件；console 退出码与 `outer-outcome.json` 一致。
3. **Q12 只读对账不重发**：`reconcile-result.json` 状态为 `ORIGINAL_Q12_RECONCILED_READONLY_NO_RESEND`、`q12_resaves=0`；恢复的 receipt sha 等于原 receipt `435dfed0…`、节点 `1792848391723`；接受记录的 `comparison.new_node_id` 相同、`reconciled_readonly=true`、`previous_output.interrupted_receipt_recovered=true`、`original_operation.state=INTENT/output=null`；工作区 operations 中 Q12 原 save 记录由 INTENT 解析为唯一 COMPLETE 接受，且**没有**新的 Q12 POST 证据。
4. **13–16 首次保存**：四题各有 `acceptance_ref`，`platform_status="SAVED_AND_INDEPENDENTLY_READ_BACK"`；新鲜独立读回证据存在；新增 save POST 恰为 4（operations 新增含 `save:46007447` 且状态 COMPLETE 的记录计数与 selection 对应）；无第五次 POST、无重复保存。
5. **11 复用不重存**：1/5/10/11 与 2/3/4/6/7/8/9 的 `acceptance_ref` 与已接受值完全相同；这些题无新 save 操作。
6. **全16 交付**：native export 恰 1 次；`delivery.mapped_count=16`；导出引用、mapped 内容与 16 题一一对应；1 次本地展示 context 有证据；formula/image 计数如实记录。
7. **预算与禁止项**：业务 GET ≤2997、POST ≤4、平台 context ≤59、绑定题图裁剪 ≤11；OCR 0、付费/本地公式模型 0、登录 0、旧九题重存 0、原始源图重取 0；`settings.json` sha 仍为 `56f07eb9…`。
8. **状态与失败语义**：`production-result.json` 的 status 如实；若 STOPPED，逐字保留 type/message、successors NOT_RUN，并核验未重试、未越界；若成功，核验 `remaining_unaccepted_count=0`、job/head 与 delivery 一致；不得把 UNKNOWN/HOLD 软化为成功。
9. **哈希与冻结**：复核者自行计算 live 全部产物、authority、包的 SHA-256/字节；记录 console 原文边界与任何截断；不得只引用执行者报告。
10. **输出**：私有 `D:/1800-private/a30-launch-r1-actual-review-20261025-01/`（`REVIEW.md`、`decision.json`、`manifest.json`、`raw/`）；公开 `docs/evidence/A30/review/launch-r1-actual-01/REVIEW.md`。结论枚举：
    - `ACCEPTED_ACTUAL_FULL16_SAVES_READBACKS_EXPORT_DISPLAY`
    - `ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY`（失败时）
    - `REWORK`（有可修复缺陷或证据不足）
    - `UNKNOWN_NO_RETRY`（结果不可判定）
11. `decision.json` 必含 `reviewer`、`decision`、`independence_limitations`、`actual_platform_calls`（复核上下文自身应为 0）、`workspace_writes`（0）、`profile_reads`（0）、`run_observed`（`COMPLETED`/`STOPPED`）、`authority_sha256`、`authority_spent`、`customer_ready`（false，除非另有根决定）。

## 补充：已发生结果与必须独立核验的新事实

本次实际运行已经发生且不可重试；根不把下列观察当作已接受结论，复核者必须从字节和原始证据自行核验：

1. **运行结果**：`production-result.json` 的 `status="STOPPED_NO_RETRY"`、`type="Hold"`、`message` 为 U+8BFB/U+56DE/U+9898/U+6570/U+6216/U+4E66/U+7C4D/U+4E0D/U+4E00/U+81F4/U+3002（“读回题数或书籍不一致。”）、`successors="NOT_RUN"`、`elapsed_seconds≈92.099`、`spent=1/remaining=0`；`outer-outcome.json` 的 `exit_code=2`、`owned_os_release_confirmed=true`、`automatic_retry=false`。`reconcile-result.json` 预期**不存在**（失败先于写成功结果），不得把缺失误判为成功或重跑理由。
2. **Q12 只读对账状态**：原 save 操作 `56232bbf…` 仍为 `UNKNOWN_NO_RETRY`，未被解析为 COMPLETE；新 reconcile 操作 `d779d3db…` 为 `FAILED_NO_RETRY`（output `521de423…`）。没有新的 Q12 POST/重发证据。
3. **计数不一致的原始证据**：原计划 blob `6163be59…` 的 `before_count=37`、`book_id=46007447`、`new_order=38`；本次运行保留的合并读回（`workspace/native/008bb17292dd4399a4d8e9d3f3351470/` 下 9 个 `usense-readonly-20261025-04*` 分片）目录问题数为 **42**、`capture-summary.json` 的 `book_id=46007447`、`save_attempts=0`。`native_plan.compare_readback` 的节点检查（回执节点/实际节点）已通过，失败只落在 `len(new_questions) == len(old_questions)+1`（37→42）一侧；请独立复算确认是计数一侧而非 book_id 一侧。
4. **多出的四个节点属先前已有状态，不是本次运行产生**：orders 39–42 的节点创建时间为平台时间 `2026-10-25T01:53:11`、`01:54:14`、`01:55:14`、`01:56:21`，早于 authority 窗口 `2026-10-25T04:07:37Z–04:37:37Z`。请自行核验其 `question/choice/answer` 文本与 job head `28274dab…` 中 printed 13–16 候选一致，且其 frame `rect_id` 等于由候选确定的 `uuid5(NAMESPACE_URL,"customer/"+source_key+"/"+index)`；并核实保留工作区 operations 中**没有** 13–16 的 save 记录/回执，任何保留工作区也没有这四题的保存输出。四题来源归因无法证明时必须记为 `UNKNOWN`。不得因此重发或覆盖这四题。
5. **本次运行只读**：从 9 个 `network-events.json` 独立汇总的请求应全部为 GET（根计数 661）、POST=0；`save_attempts=0`；无登录/OCR/公式模型/付费模型；`settings.json` 的 sha 仍为 `56f07eb9…`。若你复算不一致，以你的原始计数为准并报告差异。
6. **业务影响**：Q13–16 在平台上可能已存在（内容与候选一致），但没有保存回执、没有 `acceptance_ref`、job 仍为 NOT_RUN，因此**不得**把它们记为已保存/已接受；本次实际仍只能按固定失败和自有释放收口，后续须另立最小只读核对/归属范围，且永不重发这四题。
7. `decision.json` 的 `run_observed` 应为 `STOPPED`，`authority_spent=1`，`customer_ready=false`；结论枚举优先 `ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY`。

## 禁止

- 不运行 actual/`--child`/preflight/任何平台调用；不启动浏览器/Edge；不读 profile 内容；不写 workspace/settings/产品/包/live 输出；不删除任何证据；不执行 git/commit/push。
- 不得以执行者报告或 console 单方陈述替代字节核验；不得重放已接受矩阵。
