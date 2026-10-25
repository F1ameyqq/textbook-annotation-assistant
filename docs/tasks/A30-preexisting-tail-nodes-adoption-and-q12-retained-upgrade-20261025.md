# A30 既有尾节点采纳 + Q12 保留读回离线升级（离线实现、冻结包、只读预检）

## 结论前置

本任务只做**离线实现 + 冻结包 + 只读预检**。不得执行 actual、不得打开浏览器/profile、不得调用平台、不得发 POST、不得重发 Q12 或 13–16、不得修改已接受记录、不得生成发布 ZIP。
actual 必须等独立代码评审通过、根绑定新唯一授权后另行派发。

执行身份：`a30-exec-20261025-01`（思考强度 max）。执行者不能自行验收本任务。

## 已接受事实（唯一依据）

- 实际运行 `a30-full16-reconcile-continue-20261025-01` 已按**固定失败 + 自有释放**收口：
  `docs/evidence/coordinator/a30-launch-r1-actual-closure/receipt.json`（`9b6a05a5…`）、`root-index.json`（`a837dec0…`）。
  - `STOPPED_NO_RETRY`/`Hold`/“读回题数或书籍不一致。”/`successors=NOT_RUN`/92.099s/exit 2/`owned_os_release_confirmed=true`/spent 1/remaining 0。
  - 网络 661 GET、0 POST；9 个只读分片、`save_attempts=0`；settings `56f07eb9…` 不变。
  - Q12 原 save op `56232bbf…` 仍 `UNKNOWN_NO_RETRY`；reconcile op `d779d3db6997363af73144a23b74ac02529d433bcadd16ff7e86ec602dde07db` 为 `FAILED_NO_RETRY`，output `521de423…`（Hold）。
  - 13–16 平台节点已存在（orders 39–42），内容与候选一致、rect_id 等于本工具确定性 uuid5；但**无 save 回执/无 acceptance_ref/platform_status=NOT_RUN**，归因 `UNKNOWN`，**永不重发、永不覆盖**。
- 根离线证明：把四个先存尾节点排除后，Q12 严格比对完全通过（37 旧题/125 旧框/新节点 `1792848391723`/info `2113985491617890305`）：
  `D:/1800-private/a30-root-20261025/preexisting-q13-16-report.json`（`e3c06c5b…`）。
- 根离线采纳预检（只读，已通过）：13/14/15/16 在“候选顺序 rect_id”下全部唯一绑定；`figure_requirements` 全为 0；5 个绑定题图。
  报告脚本 `D:/1800-private/a30-root-20261025/check_next_scope_blockers.py`。

## 唯一目标

一次只读 actual 内完成：Q12 离线升级（**0 平台调用**）+ 13–16 采纳（**0 POST**）+ 全 16 原生导出与本地展示。
为此本轮先交付可审查的产品差量和冻结包。

## 产品差量（必须最小、可单测）

产品基线目录：`D:/1800-private/a30-integrated-flow-r1-fixed-20261024-20`（manifest `19a3497ef23fa8e128d88b286f65267c5291a674ffe6fa0c68b07e34c6ad817a`，249 源文件）。
新修订目录：`D:/1800-private/a30-integrated-flow-r1-fixed-20261025-01`（整目录复制基线后仅做下列修改）。

### 1. `customer/native_plan.py`：绑定式既有尾节点剪除（`compare_readback` 新关键字参数）

- 新增仅关键字参数 `preexisting_extras=None`；**默认 None 时行为与现在逐字节相同**（`produce` 的实际保存路径绝不传）。
- 传入时必须是 list，每项 `{node_id, order_in_level, created_at}`（来自冻结计划），逐项强校验：
  1. `node_id` 在 `after['questions']` 中存在且不等于本次新节点；
  2. `order_in_level` 等于绑定值，且 `int(order) > plan['new_order']`；
  3. `created_at` 字符串等于绑定值，且解析后**严格落在原发送窗口之外**（窗口含 ±5s 容差仍不重叠）；
  4. 四个绑定 node_id 互不相同。
- 仅按这些 node_id 剪除 `directory`（递归 children）、`questions`、`frames`（`order_in_level` 命中且 `rect_id` 属于该节点 annotations）；**不得**按“任意尾部多出的题”泛化剪除。
- 剪除后必须重新 `validate_current` 并继续执行现有全部严格校验（节点回执、目录、旧题、旧框、新增分区、`annotations_upsert`、pages…）。
- 剪除后若仍存在任何未绑定题（`len(new_questions) != len(old_questions)+1`），照旧 Hold。
- 返回结果新增：`preexisting_extras_pruned`（node_id 列表）、`preexisting_extras_rule: "BOUND_NODE_ID_AND_CREATED_AT_OUTSIDE_SEND_WINDOW"`；`readback_hash` 仍为**完整** `after` 的 digest。
- 新增离线测试覆盖：绑定四项→match；未绑定多一项→Hold；绑定但 order ≤ new_order→Hold；绑定但 created_at 不同→Hold；绑定但落在窗口内→Hold；无 extras 时既有测试全部照旧通过。

### 2. `customer/production.py`：`reconcile_retained(...)`（Q12 离线升级）

新函数（与 `reconcile` 并列，不改动 `reconcile` 语义）：
`reconcile_retained(store, identity, settings, *, retained_scope)`。

- 前置链（任一不满足即 Hold，且**不写任何操作**）：
  - job/head 正常，`verify_sources(job['pages'])`；
  - 唯一 `pending_plan_ref` 且 `platform_status == 'INTENT_UNKNOWN_UNTIL_READBACK'` 的候选（printed 12）；
  - save op 存在、`state == 'UNKNOWN_NO_RETRY'`、output 有 `sent`/`writer`，`post_attempts == 1`、`release.context_runtime_release_confirmed is True`、进程记录 hash/exit/释放与 `reconcile` 相同；
  - 原 `reconcile` op（`recovery_key = digest([identity, previous['output']])`）**恰好存在且为 `FAILED_NO_RETRY`**；其 output 只含 `{type,message}`（无 `sent`、无新发送）；
  - 新 op `('reconcile-retained', digest([identity, previous['output'], 'retained-upgrade:1']))` **不存在**（一次性）；
  - `retained_scope` 与冻结计划逐字段一致（下方 schema）。
- 只读重建：不得构造 `UsenseTransport`；从 `workspace/native/<capture_group>/` 读取绑定的 9 个 run 目录：
  - 每个 `capture-summary.json` 的 sha256 等于绑定值，且 `status=='NATIVE_GETS_CAPTURED'`、`save_attempts==0`、`book_id=='46007447'`、`release.context_runtime_release_confirmed is True`；
  - 每个成员 json 的 sha256 等于 summary 内声明值；重复成员必须 `json_same`；
  - 合并成员数等于绑定值（302）；`wire.snapshot(flat, book, plan['before']['pages'])`；
  - `validate_current` 得 42 题，恰好四个绑定尾节点。
- 比对：`compare_readback(plan, after, sent['receipt'], runtime_actor_hashes=writer['runtime_actor_hashes'], send_window={'start':writer['send_intent_at'],'end':writer['finished_at']}, preexisting_extras=retained_scope['expected_extras'])`；要求 `match is True` 且 `preexisting_extras_pruned` 等于绑定 node_id 列表。
- 落账：`store.begin('reconcile-retained', key)` → `store.finish(..., 'COMPLETE', receipt)` → `store.resolve('save:'+book, source_key, previous, receipt)`；候选 `acceptance_ref`、`platform_status='SAVED_AND_INDEPENDENTLY_READ_BACK'`；job `platform_status='RECONCILED_RETAINED_NO_PLATFORM_CALL'`。
- receipt：`CustomerSaveReadback/v1` + `reconciled_readonly: True` + `retained_reconcile_provenance`：
  `{schema:'CustomerRetainedReconcileProvenance/v1', origin:'RETAINED_READONLY_CAPTURE_GROUP', capture_group, runs:[{name,summary_sha256}], merged_members, platform_calls:0, original_operation:{state:'UNKNOWN_NO_RETRY', output: previous['output']}, previous_failed_reconcile:{key, state:'FAILED_NO_RETRY', output}}`。
- 失败时：新 op 置 `FAILED_NO_RETRY` 并保留原 save op 不动；绝不重发。
- 必须用**真实工作区副本**做一次端到端离线测试（见测试要求）。

### 3. `customer/legacy_ledger.py`：`existing_candidate` 的 rect_id 顺序缺陷

现状用 GET `annotations` 数组顺序比较 `data['rect_ids']`。平台数组顺序与 `image_order_in_annotation_zone` 顺序不一致（Q15 证据：数组 `[b945fc57, e4f9448a, e9bdfd9a]`，rect_ids `[b945fc57, e9bdfd9a, e4f9448a]`），导致合法既有题被 Hold。
改为与**候选顺序的 `bound` 绑定**比较：`data['rect_ids'] == [f['rect_id'] for f in bound if f['type']==zone]`（`bound_frames` 已证明使用全部原生框且一一对应）。
其余校验一律不动（`ocr_result` 全文相等、分区 success、未覆盖分区必须 absent、`bound_frames` 的几何/图片地址校验）。

### 4. `customer/existing_fill.py`：同类 rect_id 顺序缺陷（同一不变量）

`make()` 的 `ocr_submissions[].rect_ids` 改为按 `image_order_in_annotation_zone` 升序（int 校验，0..n-1 全排列），不再用 `annotations` 数组顺序；`compare()` 仍与计划提交值比较，因此两侧同时规范化。
新增离线测试：数组顺序≠image_order 时提交为 image_order 顺序；数组顺序=image_order 时输出不变。

### 5. `customer/production.py`：`ADOPT_EXISTING_MATCH` 范围操作

- `_execution_plan` 在调用 `make_plan` **之前**分流：`bound['intended_operation']=='ADOPT_EXISTING_MATCH'` 时：
  - `matched = existing_candidate(current, candidate)` 必须非 None（否 Hold）；
  - `matched['node_id'] == bound['expected_existing_node']`；
  - `info.id == bound['expected_existing_info']`；
  - 每分区 `data['rect_ids'] == bound['expected_rect_ids_by_zone'][zone]`（list 逐项相等，候选顺序）；
  - `sorted(candidate['zones']) == sorted(bound['zones'])`；
  - 返回 `None`（本操作无写入计划）。
- `produce()` 中两处 `_execution_plan` 预检循环必须允许 `None`；采纳写入循环后 `pending` 必须为空（否则 Hold：ADOPT 之外不得残留待写项）。
- 采纳记录保持现有 `CustomerCurrentExistingRead/v1` 语义（`existing_record_only: True`、`new_save_performed: False`、`platform_status='REUSED_CURRENT_EXISTING'`、`store.record_read`，**不得** `begin`/POST）。
- 新增测试：ADOPT-only 的 `selected` 经 `produce(..., transport_factory=...)` 后 0 POST、4 条 `CustomerCurrentExistingRead/v1`、`remaining_unaccepted_count==0`；错误 node id→Hold 且 0 POST；scope 缺 `expected_existing_node`→Hold。

## 冻结包（新目录，不得改写旧包）

`D:/1800-private/a30-adoption-completion-launch-fixed-20261025-01/`，schema `A30Full16AdoptionCompletionPackage/v1`，成员：
`manifest.json`、`run_once.py`、`authority-template.json`、`binding.json`、`completion-plan.json`、`q12-retained-upgrade.json`、`report.json`、`receipt.json`。

`binding.json` 必须绑定（值必须等于下列实测，不得推测）：
- workspace `D:/1800-private/a30-continuation-live-20261024-01/workspace`；`job_id 55f20a7e27147150bc608f72d8dd9cc63f39d635`；
- `expected_head 28274dab55969aa33d365ee2e4078c6ad58593929b589aa2a7581a3de20b1abc`（当前 head，platform_status `UNKNOWN_NO_RETRY`，11 个 acceptance_ref）；
- `expected_operation_count 86`；save op 12（11 COMPLETE + Q12 `56232bbf…` UNKNOWN）；无 13–16 save op；
- `settings_sha256 56f07eb98e9712b662a13b016d9758c3d2c12109421a7b1f557a972e2b565f5f`；
- 产品 manifest/`app_root`/`source_files` 各文件 sha；entry/binding/plan 自身 sha；
- profile 指纹沿用现有机械方法（只读指纹，不读凭据内容）；
- `limits`（**沿用 launch03-r1 已正式接受的同一全量预算**，只把保存 POST 降为 0）：
  `save_posts_max: 0`、`native_exports_max: 1`、`local_display_max: 1`、
  `official_bound_crop_downloads_max: 11`、`platform_contexts_max: 59`、`business_get_responses_max: 2997`、
  `readonly_reconcile_calls_max: 0`、`retained_reconcile_calls_max: 1`、`ocr_calls: 0`、`formula_model_calls: 0`、
  `paid_model_calls: 0`、`login: 0`、`automatic_retries: 0`、`old_nine_resaves: 0`、`accepted_eleven_resaves: 0`、
  `original_q12_resaves: 0`、`q13_16_resaves: 0`、`uploads_or_signatures: 0`。
  为什么不是更小：本次虽然只有 4 个待采纳项，`produce` 仍会做**整书只读 capture**（launch03-r1 实测 9 个分片上下文、661 GET），随后 `finish()` 还要 1 次原生导出上下文、1 次本地展示上下文，以及交付时最多 11 次绑定图下载。把 contexts/crops 写成个位数会让一次性的真实运行在预算处 Hold。只在有实测依据时才允许把上限调低；调高必须写明理由。
- Q12 绑定：save key `56232bbf755aaf07…`（全长从工作区读）、output `27361bc49a9df05d…`、pending_plan_ref `6163be59…`、node `1792848391723`、info `2113985491617890305`、reconcile key `d779d3db6997363af73144a23b74ac02529d433bcadd16ff7e86ec602dde07db`、reconcile output `521de423…`；
- 保留读回组 `native/008bb17292dd4399a4d8e9d3f3351470`，9 个 `usense-readonly-20261025-04*` run 的 `capture-summary.json` sha、成员总数 302；
- 13–16 采纳绑定（逐题）：

| 印刷 | node | info | order | created_at |
|---|---|---|---|---|
| 13 | 1792864390658 | 2114052595989790722 | 39 | 2026-10-25T01:53:11 |
| 14 | 1792864454350 | 2114052863003377666 | 40 | 2026-10-25T01:54:14 |
| 15 | 1792864513549 | 2114053111524278273 | 41 | 2026-10-25T01:55:14 |
| 16 | 1792864580902 | 2114053393872240642 | 42 | 2026-10-25T01:56:21 |

各分区 rect_ids（`image_order_in_annotation_zone` 升序，根于 2026-10-25 从保留快照独立重算）：

| 印刷 | question | choice | answer |
|---|---|---|---|
| 13 | `82e61cfa-94bf-574a-9666-c7d9ec1e1818`, `e70c1110-6348-566f-9542-e80a2488e9b4` | `f94901b7-4227-56cd-b613-051c9a478f01` | `315b2db9-854e-51a5-a5f7-cbc855ccc972` |
| 14 | `0eeddf0b-1c0f-5e93-8b72-afed19d3b61d` | —（候选无此分区） | `4216f69d-9e5f-5f5b-88d5-bd833de75bd0` |
| 15 | `df78ab22-8ebc-5bbb-80ca-4d1d86c6dbeb`, `f72e1317-74db-5f2b-85b1-fd5785dfe20e` | —（候选无此分区） | `b945fc57-df04-51c6-9aa0-7dd97360213c`, `e9bdfd9a-aca3-5422-ad28-716cd705d068`, `e4f9448a-bc38-5711-bf1b-8de207afb67e` |
| 16 | `92a58361-6398-5ef9-8faa-6af7e20d7550`, `f6b1281e-1274-530d-99a1-842d1ef4aa36` | —（候选无此分区） | `47445b8c-35b2-537a-873b-8655b9dda1b8`, `c546611a-6f1d-559c-b83a-e3cf78879d22` |

上表是根已独立重算的期望值，**不是**可直接照抄的输入：执行者必须自行从工作区 blob（merged snapshot 的 `annotations`，按 `image_order_in_annotation_zone` 排序）重算并断言与本表逐项相等，再写入 binding；任何不一致必须报告根而不是自行改表。Q15 的 `annotations` 数组顺序为 `b945fc57, df78ab22, e4f9448a, e9bdfd9a, f72e1317`，与候选顺序不同——这正是变更 3 的动机，不要按数组顺序绑定。
`content_hash`/`key`/`source_key` 同样必须实测。

`completion-plan.json`：`expected_initial_native_count 42`、`expected_final_native_count 42`、selection 仅 13–16 且 `intended_operation='ADOPT_EXISTING_MATCH'`、`expected_api_budget` 与 `limits` 相等、`maximum_window_seconds 1800`、`outer_release_grace_seconds 60`。

`run_once.py` 要求：
- `--preflight`：纯离线校验 binding/plan/工作区/操作表/保留组 sha/产品 sha/head/settings，打印 `READONLY_BINDING_PREFLIGHT_PASS` 与 `platform_calls: 0`，**不得**创建 live 目录、不得写工作区。
- actual 外层：沿用 `owned_process.py` 单次 launch intent（`spent 1/0`、`automatic_retry false`）+ child。
- child 顺序：`reconcile_retained` → 校验 Q12 接受记录（`comparison.preexisting_extras_pruned` 等于四绑定 node、`reconciled_readonly True`、`retained_reconcile_provenance.platform_calls == 0`、`previous_output` 未变）→ `produce(selected_keys=13…16, execution_scope=plan)` → 校验 16 个 `acceptance_ref`、13–16 `platform_status=='REUSED_CURRENT_EXISTING'` 且接受 blob schema `CustomerCurrentExistingRead/v1`/`new_save_performed False`、`remaining_unaccepted_count==0`、`delivery['mapped_count']==16`、`native_export_status` 完成、1 次本地展示。
- 结果必须写 `q12-retained-result.json` 与 `production-result.json`，逐题记录 `platform_status` 与 `acceptance_ref`，并写明 `q12_resaves=0`、`q13_16_resaves=0`、`save_posts`。

## 测试要求（全部离线，0 平台）

1. 新增/更新单测（放入产品 `app/tests/`，命名 `test_a30_*`），至少覆盖上文 1–5 的反例。
2. **真实工作区副本端到端**：把工作区整目录复制到私有临时目录（约 60MB），在副本上运行 `reconcile_retained`，断言：
   - 原 save op 由 `UNKNOWN_NO_RETRY` 解析为唯一 COMPLETE，`reconcile-retained` op COMPLETE；
   - 接受的 `comparison.match is True`、`preexisting_extras_pruned` 等于四 node、42 题剪除后 38 题；
   - 副本写入前后**原工作区** `state.sqlite`/`settings.json`/`native/` 的 sha 不变（证明只改了副本）；
   - 全流程未构造 `UsenseTransport`（可用 monkeypatch/计数断言），平台调用 0。
3. 全量既有测试回归（产品 `app/tests` 中与 customer 相关的测试至少全部通过；记录条数与耗时）。

## 交付物

私有交付目录 `D:/1800-private/a30-adoption-completion-build-20261025-01/`：
`REPORT.md`、`build-report.json`、`manifest.json`（自身除外的成员 sha/bytes）、`raw/`（测试输出、preflight 输出、真实副本测试输出、产品文件索引、产品 diff 清单、包成员索引）。

## 禁止

- 不执行 actual/`--child`/任何平台或浏览器操作；不读 profile 内容；不入库任何凭据；
- 不修改工作区、settings、已接受记录、旧包、旧证据、`docs/coordination-state.json`；
- 不 git commit/push；不生成 ZIP/发布目录；
- 不重发 Q12/13–16；不把采纳写成“已保存”。

## 完成后

把交付目录、冻结包、产品新 manifest 的 sha 与 `REPORT.md` 路径回报根。根将立即派发独立代码评审（新会话），通过后才绑定 actual 授权。
