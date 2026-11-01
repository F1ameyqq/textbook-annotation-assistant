# 模块接口约定 v1（待 M0 固化）

日期：2026-10-16。配套：[架构](architecture.md) · [开发计划](development-plan.md)。

本文件定义模块交接语义，不代表已有实现。M0 将本约定变成可校验的数据类型及固定样例；业务必填字段变化须由双方共同审查、唯一负责人合并。

## 1. 公共信封与存储约定

所有产物包含：
- schema_version、artifact_id、revision、kind。
- run_id、book_id、scope_id：区分运行、书籍和明确处理范围。
- input_refs：依赖产物及版本/摘要。
- producer：模块与实现版本、配置/政策/模型/提示版本（适用时）。
- content_hash、created_at、payload。

文件引用使用相对资产路径或 asset_id，不把个人电脑绝对路径写进共享合同。图像引用带 SHA-256、宽高；登录状态不作为业务产物传递。

运行状态属于 runtime；算法不能通过修改产物中的 status 字段控制其他模块。

## 2. 核心产物

| 产物 | 必需内容 | 约束 |
|---|---|---|
| SourceBundle | 原图清单、目录树、明确页范围、外部页码映射、历史参考及其质量标记 | 原图不可覆盖；250 页元数据不代表已取得 250 页 |
| EvidenceBundle | 区域、原图框、裁片变换、文字/公式/图表证据、候选题号与全页覆盖线索 | 未确认候选保留不确定性；不同证据来源明确标记 |
| QuestionGraph | 稳定题目/片段 ID、语义角色、内容类型、阅读顺序、父子/共享/跨页关系、答案候选与选定关系 | 一个逻辑题可包含多页多框；平台属性只能作为 external_refs |
| CheckReport | stage、输入版本、逐项问题、页级 coverage、决策、建议策略及其原因 | PASS 必须有必需检查结果；不能只存一个置信度 |
| ApplyPlan | 图谱版本、内容和目标两份通过报告、政策、目标快照、能力要求、动作及预期效果 | 任一依赖变动须重新评估；默认不包含最终提交 |
| ExecutionReceipt | 每动作结果、平台 ID、执行前后证据、读回内容或其引用、未决事项 | UNKNOWN 不能归为普通可重试失败 |
| ReviewPatch | 基线版本、实体 ID、改动、操作者/原因、相关异常 ID | 生成新版本；不能绕过自动检查直接进入执行 |
| BatchReport | 范围清单、各题状态、覆盖检查、成本、人工时间、未决事项、submission_status 和 content_check_status | 提交事实与内容质量独立；不把异常/跳过从总量里删除 |

PlatformSnapshot 是交付接口的快照对象，包含 target_id、observed_at、observed_version/hash、现有目录/题目/框和能力引用。source 和 delivery 可通过同一个受控只读适配器取得所需数据，但使用不同业务视图。

## 3. 统一坐标与身份

- bbox = [x1, y1, x2, y2]，原图像素，左上原点，右/下边界采用半开区间，可用浮点。
- 合法范围：0 ≤ x1 < x2 ≤ width，0 ≤ y1 < y2 ≤ height。
- 历史越界数据作为原始证据保留；修正生成派生版本，不静默裁边覆盖原件。
- crop_transform 保存原图到处理图的缩放、偏移、旋转及补边；无法准确回投时报告异常。
- question_id、fragment_id、region_id 稳定独立，不能用 bbox、印刷题号或平台顺序作为唯一 ID。
- 新一轮识别若不能可靠对应旧实体，使用新 ID 并记录关系待核，禁止错误套用人工 patch。
- 平台 Q/W/A/E、CSS 坐标和 YOLO 类别不进入通用语义枚举。

## 4. 统一问题对象和决策

Issue 必须包含：
`issue_id, code, scope_type, scope_id, evidence_refs, severity, blocks, suggested_strategy`。

建议 code：
`SOURCE_MISSING, PAGE_MAPPING_UNCERTAIN, UNASSIGNED_CONTENT, CROSS_PAGE_OPEN,
OPTION_INCOMPLETE, ANSWER_AMBIGUOUS, POLICY_UNRESOLVED, UNSUPPORTED_LAYOUT,
TARGET_CHANGED, CONTENT_MISMATCH, SAVE_UNKNOWN, LOGIN_REQUIRED, BUDGET_LIMIT`。

决策枚举为 PASS / RETRY / EXCEPTION / HOLD；stage 为 PRE_APPLY / TARGET / POST_APPLY。由 CheckReport 决定哪一阶段可继续，runtime 执行重试或暂停。建议策略是标识及参数，不能包含任意可执行代码或自由文本浏览器指令。

以下为示意 payload（完整文件还需公共信封）：

```json
{
  "stage": "PRE_APPLY",
  "subject": {"artifact_id": "graph-demo", "revision": 3},
  "decision": "EXCEPTION",
  "coverage": {
    "scope_id": "unit-demo",
    "pages_expected": ["asset-8", "asset-9"],
    "pages_checked": ["asset-8", "asset-9"],
    "unassigned_region_ids": ["region-42"]
  },
  "issues": [{
    "issue_id": "issue-7",
    "code": "CROSS_PAGE_OPEN",
    "scope_type": "question",
    "scope_id": "question-demo-12",
    "evidence_refs": ["region-42"],
    "severity": "blocking",
    "blocks": ["PLAN"],
    "suggested_strategy": "LOAD_ADJACENT_PAGE"
  }]
}
```

示例中的 EXCEPTION 表示自动补救未解决或当前无法继续；有预算且策略尚可执行时应返回 RETRY。coverage 是必填范围说明，不以一个统计比例代替实质内容的归属证据。

## 5. 模块调用边界

以下为规划接口签名，不是已存在的命令或可导入 API。

```text
source.collect(scope, source_config) -> SourceBundle
recognition.extract(SourceBundle, recognition_config) -> EvidenceBundle
assembly.build(SourceBundle, EvidenceBundle, domain_policy) -> QuestionGraph
quality.precheck(SourceBundle, EvidenceBundle, QuestionGraph, support_profile) -> CheckReport

platform.snapshot(target) -> PlatformSnapshot
quality.targetcheck(QuestionGraph, PlatformSnapshot, platform_policy, authorized_scope) -> CheckReport
delivery.plan(QuestionGraph, precheck_report, targetcheck_report, PlatformSnapshot, platform_policy) -> ApplyPlan
delivery.apply(ApplyPlan, BrowserSession) -> ExecutionReceipt
delivery.reconcile(ApplyPlan, ExecutionReceipt, PlatformSnapshot) -> ReconciliationResult
quality.postcheck(QuestionGraph, ApplyPlan, ExecutionReceipt, platform_content) -> CheckReport

exceptions.patch(base_artifact, ReviewPatch) -> new_artifact_revision
runtime.summarize(run_id) -> BatchReport
```

组题模块可在内部区分 semantic labeling 和 assembly；它们使用可替换实现，不必增加顶层服务。公式识别和外部模型调用通过统一网关，计费和重试不写进题型规则。

precheck_report 与 targetcheck_report 必须均为 PASS，并绑定同一图谱/政策以及当前目标快照，planner 才可运行。TARGET_CHANGED、本计划必需能力未验证或范围不符由 targetcheck 返回具体问题与 EXCEPTION/HOLD；不能让 planner 猜测或悄悄降级。已明确选择并验证的同会话有窗口方案，可以不要求重启后草稿恢复能力。

runtime 根据依赖关系调用模块；模块间仅传合同，禁止跨模块读取私有文件/数据库或共享可变全局变量。

## 6. 执行事务和恢复合同

每个 Action 至少包含：
`action_id, target, source_entity_ids, expected_before, operation, expected_after, depends_on`。

- expected_before 只检查本动作相关事实；前一步由本程序造成的预期变化不能被误判为外部冲突。
- 写入前持久化 intent；写入后取得实际读回，再持久化 receipt。
- 同一计划/动作 ID 用于本地去重。平台不支持幂等键时，仍必须依赖读回核对。
- APPLIED 需要实际效果证据；NOT_APPLIED 需要明确未生效证据；其他情况是 UNKNOWN。
- UNKNOWN 或重启后存在 intent 无结论时，先 reconcile；不得自动重发。
- 目标状态变化则使相关计划失效，重新读取、检查和规划。
- ReviewPatch 改动已经录入的题时，产生新计划并引用旧回执；只有明确支持的差量修改才能执行。

ReconciliationResult 包含 `RESOLVED_APPLIED / RESOLVED_NOT_APPLIED / STILL_UNKNOWN` 以及证据；STILL_UNKNOWN 保持该书写入暂停。

## 7. 平台能力和最终内容

能力记录逐项使用 VERIFIED / UNKNOWN / UNSUPPORTED，并带测试证据与适用平台版本：
`persistent_draft, frame_readback, content_readback, ocr_before_submit,
resume_after_restart, multi_session`。

- POST_APPLY 必须区分框结构一致与最终文字/公式内容一致。
- OCR 未完成、内容不可读或只有任务成功标记时，不能输出“内容已核验”。
- OCR 只能最终提交触发时，批次保留 CONTENT_PENDING 并走人工提交后核验分支。
- 不提供“自动确认最终提交”的隐含动作。最终提交观察与业务质量检查是两种独立证据。

submission_status 枚举：NOT_SUBMITTED / CONFIRMED / UNKNOWN。
content_check_status 枚举：PENDING / VERIFIED / MISMATCH / UNAVAILABLE。
只有提交 CONFIRMED、内容 VERIFIED 且必需框结构检查通过，整批才可标为 COMPLETED。提交后 OCR 分支先更新提交事实，再等待并检查内容。

## 8. 固定样例与独立验收

每个共享样例包含 `input.json, expected.json, assets/, README.md`；说明来源、适用合同版本、哪些值精确比较、哪些采用范围/语义断言。

最小样例组：
1. 普通单页选择题，正常自动通过。
2. 两个目录都有第 1 题，防止串答。
3. 同题跨页、组合题共享材料、多框属于一题。
4. 拼合答案图切片后回投原图。
5. 整题未进入候选列表：整页覆盖必须发现未归属内容。
6. 保存实际成功但响应超时，恢复不能重复建框。
7. 目标在计划后被修改，计划不能盲执行。
8. 人工 patch 后重识别，旧修改不会静默丢失。
9. 平台 OCR 结束但公式/选项缺失，后置检查不能直接通过。
10. 登录失效、预算用尽、未支持类型和内容尚未可读。

真实样例与人为故障样例分别标识；构造用例可验证接口与状态机，不能替代平台验收或真实识别精度评测。用于调参的样例不进入独立验收成绩。
