# A30 采纳 + Q12 保留读回升级：独立代码评审

## 结论前置

本任务只做**离线独立代码评审**，不执行 actual、不打开浏览器/profile、不连平台、不发 POST、不登录、不改工作区 `D:/1800-private/a30-continuation-live-20261024-01/workspace`、不改产品/包/旧证据、不 git commit/push、不生成 ZIP。
评审通过后由根另行绑定唯一 actual 授权；**你的接受不等于 actual 授权**。

评审身份：新会话（不得是执行者 `a30-exec-20261025-01`），思考强度 max。

## 输入

- 实现任务书：`docs/tasks/A30-preexisting-tail-nodes-adoption-and-q12-retained-upgrade-20261025.md`（sha256 `d84c414c85629ad65116ccecc571fbb909817d842290da5d6d086c42bdeeb0ea`）
- 基线依据（已正式/根接受，不要重开）：`docs/evidence/coordinator/a30-launch-r1-actual-closure/receipt.json`（`9b6a05a5…`）、`root-index.json`（`a837dec0…`）
- 执行者交付：`D:/1800-private/a30-adoption-completion-build-20261025-01/`（`REPORT.md`、`build-report.json`、`manifest.json`、`raw/`）
- 产品新修订：交付报告声明的产品目录（`D:/1800-private/a30-integrated-flow-r1-fixed-20261025-01`）与 manifest
- 冻结包：`D:/1800-private/a30-adoption-completion-launch-fixed-20261025-01/`
- 产品基线（用于 diff）：`D:/1800-private/a30-integrated-flow-r1-fixed-20261024-20`（manifest `19a3497ef23fa8e128d88b286f65267c5291a674ffe6fa0c68b07e34c6ad817a`，249 源文件）

先核交付 manifest 自身（成员 sha/bytes 全部重算），再核产品 diff 是否**只**含任务书允许的六项变更。任何越界文件、既有测试被删/被弱化，都是 REWORK。

## 必须核验的九项

1. **比较器默认零变化**：`compare_readback` 在 `preexisting_extras` 缺省时行为与原版等价（可用旧版对同一输入逐字段比对结果；至少证明旧测试全绿且新增参数没有被 `produce` 的实际保存路径传入）。
2. **剪除不可泛化**：只按绑定的 `node_id` 剪除；`order_in_level` 必须 > 新题 order；`created_at` 必须在原发送窗口（含 ±5s 容差）之外；四个 node_id 互不相同。反例必须 Hold：未绑定多一题、order 不匹配、created_at 不匹配、created_at 落在窗口内、只绑定三题而平台多两题。
3. **`reconcile_retained` 零平台调用**：代码里不得构造 `UsenseTransport`/浏览器/上下文；只读绑定 capture group；每个 summary/成员 sha 校验；重复成员 `json_same`；合并成员数等于绑定值；新 op kind `reconcile-retained`、key `digest([identity, previous['output'], 'retained-upgrade:1'])`、一次性；原 `UNKNOWN_NO_RETRY` save op 与 `FAILED_NO_RETRY` reconcile op 均不被改写。失败路径必须写 `FAILED_NO_RETRY` 且 save op 仍为 UNKNOWN。
4. **Q12 结果诚实**：接受记录必须 `reconciled_readonly: True` 且 `retained_reconcile_provenance.platform_calls == 0`，并保留 `previous_output`；不得出现任何“新发送/新回执”字段把离线升级伪装成平台确认。
5. **`existing_candidate` 顺序修正**：rect_id 比较改为候选顺序（`bound`，即 `image_order_in_annotation_zone`）；`ocr_result` 全文相等、分区 success、未覆盖分区 absent、`bound_frames` 几何/地址校验**全部不变**。用真实快照证明 13/14/15/16 全部命中、且构造一个 rect_id 集合相同但顺序不同的反例仍失败。
6. **`existing_fill.make/compare` 同一不变量**：提交按 `image_order_in_annotation_zone` 升序，0..n-1 全排列校验；数组顺序=image_order 时输出不变。
7. **采纳零 POST**：`ADOPT_EXISTING_MATCH` 只校验后返回 None；`produce` 允许 None 且采纳后 `pending` 为空；采纳只写 `CustomerCurrentExistingRead/v1`（`existing_record_only: True`、`new_save_performed: False`、`platform_status='REUSED_CURRENT_EXISTING'`），**不得**出现 `store.begin('save:...')`/任何写请求路径。构造性证明：ADOPT-only 运行时 transport 的写方法调用次数为 0。
8. **冻结包完整性**：binding 的每个值都能在工作区独立复算命中（head `28274dab…`、settings `56f07eb9…`、操作数 86、Q12 save/reconcile key 与 output、保留组 9 runs/302 成员、13–16 的 node/info/order/created_at/rect_ids）；`limits` 里 `save_posts_max: 0`、`readonly_reconcile_calls_max: 0`、`retained_reconcile_calls_max: 1`、`automatic_retries: 0`；`--preflight` 只读（不建 live 目录/不写工作区），且报告 `platform_calls: 0`；entry 无重试分支、单次 launch intent、1800s 窗口 + 60s 释放宽限；`run_once.py` 的 child 顺序正确（reconcile_retained → 校验 → produce → 校验 16 条 acceptance/导出/展示），任一校验失败即 Hold 且不继续。
9. **测试质量**：真实工作区副本端到端测试必须证明（a）副本上 Q12 被解析为唯一 COMPLETE 且 `preexisting_extras_pruned` 等于四绑定 node；（b）**原工作区** `state.sqlite`/`settings.json`/`native/` 的 sha 前后不变；（c）全流程未构造 transport。回归测试条数/耗时如实记录；跳过/失败必须列出，不得用“全部通过”概括。

## 你可以做的

- 读任意文件、重算任意 sha、在工作区**副本**上运行离线测试、运行 `--preflight`（仅当确认不写工作区/不建 live 目录；有疑问就不跑，改读代码）。
- 在 `D:/1800-private/a30-adoption-completion-code-review-20261025-01/` 写你的产物。

## 交付

私有目录 `D:/1800-private/a30-adoption-completion-code-review-20261025-01/`：
`REVIEW.md`（公开可入库版本另放 `docs/evidence/A30/review/adoption-completion-code-01/REVIEW.md`）、`decision.json`、`manifest.json`（自身除外的成员 sha/bytes）、`raw/`（你跑的测试输出、复算脚本、sha 清单）。

`decision.json` schema `A30AdoptionCompletionCodeReviewDecision/v1`，必须含：
- `decision`: `ACCEPTED_OFFLINE_CODE_AND_PACKAGE` 或 `REWORK`
- `findings`: 列表，每项 `{severity: BLOCKER|MAJOR|MINOR|NOTE, file, line, issue, evidence}`
- `tests_run`: 命令、条数、通过/失败/跳过、耗时
- `verified_bindings`: 你独立复算的 binding 值（逐个给 sha/值）
- `actual_run_authorized`: 必须为 `false`
- `customer_ready`: 必须为 `false`
- `independence_limitations`: 如实写明同模型家族、新会话、原 Codex 复核不可用、用户已批准 M1

## 判定标准

- 出现任何“可能重发 Q12/13–16”的路径、任何采纳路径可发写请求、任何剪除可泛化、任何既有校验被放宽，直接 `REWORK`。
- 仅有文档/命名/可读性小问题 → `ACCEPTED_OFFLINE_CODE_AND_PACKAGE` + `MINOR/NOTE` findings。
- 你不得自行修复产品；发现问题只报告。
