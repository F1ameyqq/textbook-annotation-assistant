# A30 launch03-r1 实际单次运行独立复核（公开报告）

- 复核上下文：`a30-review-actual-r1-20261025-01`（新开 Agent 会话，思考强度 max）
- 复核时间：2026-10-25T05:30Z
- 对象：一次已经发生、不可重试的真实运行（authority `a30-full16-reconcile-continue-20261025-01`）
- 独立性限制：同一模型家族、不同会话；原 Codex 复核额度耗尽，用户已批准 M1。本报告不是原正式复核，也不是不同模型供应商复核。
- **结论：ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY**
- `run_observed=STOPPED`、`authority_spent=1`、`customer_ready=false`

## 核验结论（全部由复核者从字节和原始证据独立重算）

1. **授权绑定**：authority SHA-256 `10e9330b19254c50f8f369c143de3a66fbe40989114baf2b583675c82e3ce14d` 与 dispatch intent 一致；schema `A30Full16ReconcileContinueAuthority/v1`、`activated=true`、`executor="a30-exec-20261025-01"`；窗口 1800.0 秒，launch/child/finish 全部落在窗口内；entry `fbfa8673…`、binding `35f87bd5…`、plan `eabbb944…`、manifest `55a6af31…` 与冻结包一致；`limits` 与 `expected_cost` 与 binding/plan 逐字节相等；16 个 selected_keys 顺序与 plan 完全一致；4 个 root receipts 哈希匹配（`d9b3e9e2…`、`4a1f4abb…`、`70d6bdb5…`、`96f2dae9…`）。
2. **单次性**：`launch-intent.json` 恰 1 份、`child-entered.json` 恰 1 份、spent=1/remaining=0/automatic_retry=false；无 retry 目录/文件；console 退出码 "2" 与 `outer-outcome.json` 一致；`reconcile-result.json` 不存在（失败先于写成功结果，符合预期）。
3. **Q12 只读对账不重发**：原 save 操作 `56232bbf…` 仍为 `UNKNOWN_NO_RETRY`；新 reconcile 操作 `d779d3db…` 为 `FAILED_NO_RETRY`（output `521de423…` = `{"type":"Hold","message":"读回题数或书籍不一致。"}`）；窗口内仅 1 条工作区事件 `INTERRUPTED_WRITER_RECEIPT_RECOVERED_NO_RESEND`（本地恢复）；恢复记录 receipt `435dfed0…`/节点 `1792848391723`/`new_save_attempts=0`；9 分片汇总 POST=0——无任何新 Q12 POST/重发证据。
4. **计数不一致独立复算**：旧 37 题 + 回执节点 = 38，读回 42 题；节点检查通过、book_id 两侧均为 `46007447`；失败只落在 `len(new_questions) == len(old_questions)+1` 一侧（42 ≠ 38），不是 book_id 一侧。
5. **多出四节点（orders 39–42）**：平台创建时间 `01:53:11/01:54:14/01:55:14/01:56:21` 早于窗口；内容与 printed 13–16 候选一致；15 个 rect_id 均等于确定性 `uuid5(NAMESPACE_URL,"customer/"+source_key+"/"+index)` 重算值；工作区无四题 save 记录/回执/`write-*` 输出、`acceptance_ref=null`、`platform_status=NOT_RUN`。**归因 UNKNOWN**——不得记为已保存/已接受，不得重发或覆盖。
6. **本次运行只读**：GET 661（326 xhr + 326 fetch + 9 document）、POST 0；9 个 capture-summary 全部 `save_attempts=0`；`automatic_login_performed=false`、`login_requests_per_layer={}`；OCR/公式/付费模型/登录 0；旧九题重存 0；无二进制源图重取（分片 9 仅 5 个 231–233 字节页面 JSON）；`settings.json` SHA-256 仍为 `56f07eb9…`。
7. **失败语义**：`production-result.json` `STOPPED_NO_RETRY`/`Hold`/`"读回题数或书籍不一致。"`/`successors=NOT_RUN`/`elapsed≈92.099s`；`outer-outcome.json` `exit_code=2`、`owned_os_release_confirmed=true`；job head `platform_status=UNKNOWN_NO_RETRY`、`remaining_unaccepted_count=12`。未重试、未越界、未软化为成功。
8. **哈希与冻结**：live 全部产物、authority、包、receipts、settings 均由复核者独立重算 SHA-256/字节；console 边界（stdout 403 字节/单行 JSON、stderr 0、exit "2" 1 字节、outer.stderr 96 字节）无截断。

## 边界与后续

- 本次实际只能按**固定失败和自有释放**收口。
- Q13–16 在平台上可能已存在（内容与候选一致），但没有保存回执、没有 acceptance_ref、job 仍为 NOT_RUN；后续须另立最小只读核对/归属范围，且**永不重发这四题**。
- Q12 保持 UNKNOWN_NO_RETRY，未重发；本复核不授权任何重发。
- Full16 导出/展示本轮未运行；`customer_ready=false`。
- 私有复核产物：`D:/1800-private/a30-launch-r1-actual-review-20261025-01/`（`REVIEW.md`、`decision.json`、`manifest.json`、`raw/` 30 个原始证据文件）。

## 补充复核（team-lead 追加：排除四额外节点的离线比较器重建）

追加任务（固定失败范围，复核自身 0 平台调用/0 写入/0 profile 读取）：独立重建九个 `usense-readonly-20261025-04*` 分片的合并读回，仅移除 orders 39–42 的四个节点及其题框/题目，用冻结产品源码的 `native_plan.compare_readback` 对计划 blob `6163be59…` 与恢复记录 blob `27361bc4…`（sent.receipt + sent.writer）离线比较。

- **分片完整性**：9 个 capture-summary 全部通过（status `NATIVE_GETS_CAPTURED`、`save_attempts=0`、book `46007447`、`release.context_runtime_release_confirmed=true`；每个 capture 的 sha256/status=200/request_counts={context:1,native:1} 对照文件字节重算一致）。
- **合并一致性**：directory/frames/source 在 9 个分片间 `json_same` 全等。
- **合并读回**：42 题、143 框（125 旧 + 3 个 Q12 新框 + 15 个额外框）。
- **未清理读回在第 256 行**：`Hold("读回题数或书籍不一致。")`——42 ≠ 37+1；实际失败只求值了计数一侧（短路），book_id 两侧独立核验相等（46007447）。
- **清理后比较（仅移除 orders 39–42 及其 15 框）**：`validate_current` PASS；`compare_readback` **PASS**：`old_questions_preserved=37`、`old_frames_preserved=125`、`new_node_id="1792848391723"`、`new_info_id="2113985491617890305"`、`readback_hash="cceb4298fb93bb8b4afd01c489bf4cdf7284bc52834594bb92dfc7a38094d449"`、`native_clock_tolerance_seconds=5`、`runtime_actor_and_send_window_checked=true`。
- **时间戳/操作者窗口已核**：新题 info created_at==updated_at==13:26:32Z（原 writer 窗口 13:26:31.68–13:26:32.12Z 内，±5s 边界内）；runtime_actor_hashes 来自原 writer，新题框 user_id 摘要与 `runtime_user_id_sha256` 匹配（比较器内部检查通过）。
- **定性**：实际失败真实且 Hold 行为正确；清理后通过只证明底层 Q12 写证据内部一致，**不改变结论**——仍为固定失败+自有释放，Q12 仍 UNKNOWN_NO_RETRY，不授权重发/补对账/新运行；orders 39–42 归因仍 UNKNOWN、永不重发或覆盖。
- 证据：私有 `raw/comparator-reconstruction.txt`、`decision-addendum.json`、`reconstruct_compare.py`。
