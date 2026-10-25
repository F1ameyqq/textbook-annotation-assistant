# A30 launch03-r1 实际单次运行独立复核报告

- 复核上下文：`a30-review-actual-r1-20261025-01`（新开 Agent 会话，思考强度 max）
- 复核时间：2026-10-25T05:30Z（复核本身 0 平台调用 / 0 workspace 写入 / 0 profile 读取）
- 对象：一次已经发生、不可重试的真实运行（authority `a30-full16-reconcile-continue-20261025-01`）
- 独立性限制：同一模型家族、不同会话；原 Codex 复核额度耗尽，用户已批准 M1。本报告不是原正式复核，也不是不同模型供应商复核。
- 结论：**ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY**

## 1. 授权绑定（核验通过）

| 项 | 复核者独立计算值 | 期望值 | 结论 |
|---|---|---|---|
| authority SHA-256（4313 字节） | `10e9330b19254c50f8f369c143de3a66fbe40989114baf2b583675c82e3ce14d` | dispatch intent `ee56538f…` | 一致 |
| schema / activated / executor | `A30Full16ReconcileContinueAuthority/v1` / true / `a30-exec-20261025-01` | 同 | 一致 |
| 窗口 | not_before `04:07:37.882163Z` → expires_at `04:37:37.882163Z` = **1800.0 秒** | ≤1800 | 一致 |
| 运行落点 | launch `04:09:16.048751Z`，child entered `04:09:30.389530Z`，finished `04:11:02.584543Z` | 全部落在窗口内 | 一致 |
| entry `run_once.py`（15415 字节） | `fbfa8673…ef7606a` | 同 | 一致 |
| binding.json（3425 字节） | `35f87bd5…2905688` | 同 | 一致 |
| continuation-plan.json（99586 字节） | `eabbb944…dc1860c8` | 同 | 一致 |
| package manifest.json（2153 字节） | `55a6af31…ce855df` | 同 | 一致 |
| `authority.limits == binding.limits` | 逐字节 JSON 相等 | 完全相等 | 一致 |
| `authority.expected_cost == plan.expected_api_budget` | 逐字节 JSON 相等 | 完全相等 | 一致 |
| 16 个 selected_keys | 与 `plan.selection[].key` 顺序完全一致（16/16） | 顺序一致 | 一致 |
| ≥4 root receipts | `d9b3e9e2…`(3714)、`4a1f4abb…`(7716)、`70d6bdb5…`(5687)、`96f2dae9…`(95328) | 与 dispatch intent 哈希/字节一致 | 一致 |

## 2. 单次性（核验通过）

- `launch-intent.json` 恰 1 份（spent=1/remaining=0/automatic_retry=false，command 含 `--authority … --sha256 10e9330b… --child`）。
- `child-entered.json` 恰 1 份（spent=1/remaining=0）。
- live 目录顶层仅 10 个文件，全部为预期产物；全目录递归扫描无任何 retry 目录/文件。
- `console.exit.txt` = `"2"`（1 字节）与 `outer-outcome.json` 的 `exit_code=2` 一致。
- `reconcile-result.json` **不存在**（失败先于写成功结果；按补充说明这是预期状态，不构成重跑理由）。

## 3. Q12 只读对账不重发（核验通过）

- 工作区 operations 表共 86 行；`save:46007447` 恰 12 行：11 行 COMPLETE（先前已接受批次）+ 1 行 `56232bbf…` 仍为 **UNKNOWN_NO_RETRY**（未解析为 COMPLETE）。
- `reconcile` 恰 2 行：`06937fa7…` COMPLETE（先前批次）+ `d779d3db…` **FAILED_NO_RETRY**，output `521de423…` = `{"type":"Hold","message":"读回题数或书籍不一致。"}`。
- 恢复记录：receipt_sha256 `435dfed0…`、节点 `1792848391723`、`interrupted_receipt_recovered=true`、`original_operation.state=INTENT/output=null`、`new_platform_calls=0`、`new_save_attempts=0`。
- 本次运行窗口内工作区事件恰 1 条：`INTERRUPTED_WRITER_RECEIPT_RECOVERED_NO_RESEND`（本地恢复，非平台操作）。
- 9 个分片汇总 **POST=0**；无任何新的 Q12 POST/重发证据。

## 4. 计数不一致的原始证据（复核者独立复算，与根观察一致）

- 原计划 blob `6163be59…`：`before_count=37`、`book_id=46007447`、`new_order=38`。
- 本次合并读回（9 个 `usense-readonly-20261025-04*` 分片）目录问题数 **42**，`save_attempts=0`。
- 节点检查通过：回执节点 `1792848391723` = 读回第 38 位；前 38 个读回 id 与 before 37 个 id + 节点 38 逐一相同。
- book_id 两侧均为 `46007447`。
- **失败只落在 `len(new_questions) == len(old_questions)+1` 一侧（42 ≠ 37+1=38），不是 book_id 一侧。**

## 5. 多出的四个节点（orders 39–42）

- 平台创建时间 `2026-10-25T01:53:11`、`01:54:14`、`01:55:14`、`01:56:21`，**全部早于 authority 窗口**（04:07:37Z 起）——不是本次运行产生。
- 15 个 frame 的 bbox/zone 与 job head `28274dab…` 中 printed 13–16 候选逐一一致；zone 文本核对一致（13 网格三角形/D；14 周髀算经/26；15 正方形ABCD/解…；16 清华附中/（1）60，61。）。
- 15 个 `rect_id` 均等于 `uuid5(NAMESPACE_URL,"customer/"+source_key+"/"+index)` 的独立重算值。
- 保留工作区 operations **没有** 13–16 的 save 记录/回执；全 workspace `native/` 下不存在与四个候选 key 匹配的 `write-*` 目录（现存 write 目录全部属于先前批次，含 Q12 原 writer 的 `write-56232bbf…`）；四题 `acceptance_ref=null`、`platform_status=NOT_RUN`。
- **归因：UNKNOWN。** 不得记为已保存/已接受，不得重发或覆盖。

## 6. 本次运行只读（核验通过）

- 9 个 `network-events.json` 独立汇总：**GET 661**（326 xhr + 326 fetch + 9 document）、**POST 0**、PUT/DELETE/PATCH/HEAD/OPTIONS 0 —— 与根计数 661 一致。
- 9 个 `capture-summary.json` 全部 `save_attempts=0`、`NATIVE_GETS_CAPTURED`、book `46007447`，finish 时间全部落在窗口内。
- 9 个 `release.json`：`automatic_login_performed=false`、`login_requests_per_layer={}`、`context_runtime_release_confirmed=true`、`pending_callbacks=0`。
- TLS probe：DIRECT、proxy null、`EXACT_LEAF_CONFIRMED`、leaf `52d86421…`（与已接受叶子一致）。
- OCR 0、公式/付费模型 0、登录 0、旧九题重存 0、原始源图重取 0（分片 9 仅 5 个 231–233 字节的页面 JSON 体，无二进制源图）。
- `settings.json` SHA-256 仍为 `56f07eb98e9712b662a13b016d9758c3d2c12109421a7b1f557a972e2b565f5f`（1103 字节）。

## 7. 状态与失败语义（核验通过）

- `production-result.json`：`status=STOPPED_NO_RETRY`、`type=Hold`、`message="读回题数或书籍不一致。"`（逐字保留）、`successors=NOT_RUN`、`elapsed_seconds=92.09928860000218`、`spent=1/remaining=0`、`original_settings_unchanged=true`。
- `outer-outcome.json`：`exit_code=2`、`owned_os_release_confirmed=true`、`automatic_retry=false`。
- `production-outer.stderr`（96 字节）与 production-result 的 type/message 逐字一致；stdout 0 字节。
- job head `28274dab…`：`platform_status=UNKNOWN_NO_RETRY`、`remaining_unaccepted_count=12`、`customer_ready` 未变；13–16 全部 `NOT_RUN`/`acceptance_ref=null`。
- 未重试、未越界；失败未软化为成功。

## 8. 哈希与冻结（复核者自行计算）

- live 全部 10 个产物、authority、包 4 成员、4 个 root receipts、workspace `settings.json` 的 SHA-256/字节均由本复核会话独立重算（见私有 `raw/hashes.txt` 与 `manifest.json`）。
- console 原文边界：`console.stdout.txt` 403 字节（单行 outer outcome JSON）、`console.stderr.txt` 0 字节、`console.exit.txt` 1 字节（"2"）、`production-outer.stderr` 96 字节、`production-outer.stdout` 0 字节。未观察到任何截断。

## 9. 输出与后续

- 私有：`D:/1800-private/a30-launch-r1-actual-review-20261025-01/`（`REVIEW.md`、`decision.json`、`manifest.json`、`raw/` 30 个原始证据文件）。
- 公开：`D:/1800/docs/evidence/A30/review/launch-r1-actual-01/REVIEW.md`。
- `run_observed=STOPPED`、`authority_spent=1`、`customer_ready=false`。
- 后续另立最小只读核对/归属范围处理 Q13–16 平台已有节点；永不重发这四题，也不重发 Q12。
