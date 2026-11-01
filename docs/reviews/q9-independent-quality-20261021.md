# 46007447 第一章 Q9 与章节覆盖独立审计

日期：2026-10-21（Asia/Shanghai）
角色：独立质量审计；共享仓库只读
总判定：**HOLD**

## 1. 分层结论

| 层次 | 结论 | 边界 |
|---|---|---|
| 三个固定 ZIP 的字节与清单 | PASS | ZIP SHA、成员安全、解包后清单成员/字节数/SHA 均一致 |
| Q9 答案证据结构绑定 | PASS | 目标答案、33 原片段、15 呈现区域、跨页顺序、图 3–7 与 20cm/25cm 全部固定一致 |
| Q9 题答交付 | **BLOCKED / HOLD** | 完整题页、真实 `question_id`、题答关系均未建立；不可凭答案或印刷题号 9 补造 |
| Q9 内容/几何人工验收 | 未完成 | 本次是独立离线结构、像素目视与变异审计，不是人工业务验收 |
| 第一章完整覆盖 | **BLOCKED / HOLD** | 8 张只是 observed subset；章节页数、题数、答案数、共享材料数分母均为 `null` |
| 网站/平台状态 | 未触碰 | 0 网站写入、0 平台动作、0 新 OCR、0 付费模型调用 |

因此，当前可保留的准确表述是：**Q9 的两页答案证据形成了完整的离线结构候选，但 Q9 仍是 `ANSWER_EVIDENCE_ONLY`，不能升级为已配题、已验收或可提交。第一章也不能按 8 张图或 42 个工作视图候选销账。**

## 2. 固定输入完整性

| 包 | 固定 SHA-256 | ZIP 成员 | 清单核对 |
|---|---|---:|---|
| observed eight sources v2 | `ec77d52ebcf25b3fec64579f63400c010cc08a623d71e20506e6ed46125ea695` | 15 | 14/14 非清单文件一致 |
| Q15 revision9 current baseline | `8c812330b93cc60b920f6ccd1cd7784f0afe8d293336166a586e1aeaab8231ad` | 301 | 300/300 非清单文件一致 |
| Q4/Q9/Q16 next batch | `b646fad9008e03e79a3dddfb4ead912d7ceadefbcee331c2e2af2415abf6f673` | 24 | 23/23 非清单文件一致；内部 staging 9/9 一致 |

三个 ZIP 均未发现重复成员、绝对路径、`..`、反斜杠成员或符号链接成员。

## 3. Q9 唯一目标与两页证据

唯一允许的答案对象：

- `answer_id = a-9a6c21dd0fe88b1059b7919e`
- 节路径：`第一章 勾股定理 / 问题解决策略 反思`
- `question_id = null`
- `question_snapshot = null`
- 模式：`ANSWER_EVIDENCE_ONLY`
- 决策：`HOLD`
- `complete=false`、`transcription_verified=false`、`human_verified=false`

固定 next-batch 中的 `answer_snapshot` 与 Q15 revision9 `reference/final/graph.json` 中该答案对象逐字段完全相等。

### 跨页顺序

1. `viewer-173`：印刷 25 页右下，Q9 答案开头；正文给出图 3 的 `AB=20cm`，并出现图 3、图 4。
2. `resource-173`：原图可见印刷页码 26，页首接续“如图4”，继续给出最短路线 20cm；第二问依次比较图 5、图 6、图 7，最终得到蚂蚁沿长方体表面的最短路程 25cm。
3. `resource-173` 下半已进入“第二章 实数”，所以第一章只允许使用页首已绑定的续文和图 5–7；不能把整页算入第一章内容。

当前 continuation 固定为：

- `viewer-173/ocr/156` → `resource-173/ocr/0..24`
- `from_asset_id=viewer-173`
- `to_asset_id=resource-173`
- `verification_status=UNVERIFIED`

### 15 个呈现区域

| 顺序 | 页资产 | 区域 |
|---:|---|---|
| 1 | viewer-173 | 正文 1 区 |
| 2–3 | viewer-173 | 图 3、图 4 |
| 4–12 | resource-173 | 连续正文 9 区 |
| 13–15 | resource-173 | 图 5、图 6、图 7 |

精确图框：

- 图 3：`viewer-173 [709,1417,834,1539]`
- 图 4：`viewer-173 [876,1382,959,1540]`
- 图 5：`resource-173 [147,249,230,441]`
- 图 6：`resource-173 [247,291,379,441]`
- 图 7：`resource-173 [396,267,491,441]`

## 4. 同号题隔离

revision9 图谱中另有两个真实印刷号 9：

| `question_id` | 小节 | 已选答案 |
|---|---|---|
| `q-ef054d09d41282f4716de397` | 1 探索勾股定理 / 第1课时 | `a-9a1ebdea7a5ee71a4700767a` |
| `q-7d1579fe39d5acc3319646ca` | 2 一定是直角三角形吗 | `a-1c34eb20e2abcfd254399e16` |

两者均不选择目标答案 `a-9a6c21dd0fe88b1059b7919e`。全图谱中选择目标答案的题节点数为 0。因此：

- 不得把任一同号题 9 拼到“问题解决策略·反思”答案；
- 不得以 `printed_number=9` 作为关系身份；
- 不得从 20cm/25cm 或蚂蚁路径反推、补写题页；
- 只有取得真实题页并建立来源哈希绑定后，才可提出新的题答候选关系。

## 5. 独立变异回归

独立校验器对固定基线零报错，并运行 9 个定向变异；9/9 均在预期规则层被拒绝：

| 变异 | 预期拒绝 |
|---|---|
| resource 页提前，交换跨页呈现顺序 | `RENDER_PAGE_ORDER` |
| continuation 的 from/to 对调 | `CROSS_PAGE_CONTINUATION` |
| 删除图 5 | `FIGURE_3_TO_7_BINDING` |
| 交换图 5/图 6 | `FIGURE_3_TO_7_BINDING` |
| 删除末行 25cm，并截断最后来源行/区域 | `TEXT_CONTINUATION_TRUNCATED` |
| 拼入第1课时同号题 9 | `QUESTION_ID_MUST_REMAIN_NULL` |
| 拼入“2 一定是直角三角形吗”同号题 9 | `QUESTION_ID_MUST_REMAIN_NULL` |
| 用另一同号题 9 的答案替换目标答案 | `TARGET_ANSWER_ID` |
| 无题页却升级为题答候选、PASS、人工/联合接受 | `MODE_NOT_ANSWER_EVIDENCE_ONLY` 与 `STATUS_ESCALATED` |

原 next-batch 生产器已有完整快照冻结，能以通用 `FROZEN_SNAPSHOT_CHANGED` 拒绝部分篡改，但其 Q9 专项生成断言只检查“5 个图像区域”和“两个资产首次出现顺序”，没有独立锁定图号 3–7、25 条续页行、续文方向及 20cm/25cm 终点。已在独立目录提供一个最小加固补丁：补入这些高层断言和四个针对性负例。该补丁未写入共享仓库；`git apply --check` 通过，隔离副本 `py_compile` 通过，并用固定 Q15 ZIP 完整重放成功，仍输出 `READY_FOR_A_EXTENSION_REVIEW_HOLD`。

## 6. 第一章覆盖姿态

固定来源包自身明确：

- `inventory_frozen=false`
- `scope_state=PARTIAL`
- `decision=HOLD`
- `independent_denominator_verified=false`
- 8 是“declared observed subset only”，不是完整章节页数
- `question_pages / answer_pages / questions / answers / shared_materials` 五个分母均为 `null`

42 个题目候选是合并后的内部工作视图计数；它混合旧六资产、viewer-13 与 viewer-15 分支，项目文档也明确“不把 42 称为整章题数”。同理，viewer/resource 序号及印刷页码的局部观察不能推导缺页数、整章边界或周测纳入规则。

### 第一章完整交付仍缺的对象

1. 第一章完整来源清单，含每个原文件/页资产的 SHA、尺寸和稳定阅读顺序；
2. 第一章首个题页、最后题页、首个答案页和最后答案页的来源依据；
3. “周测（第一章）”是否纳入本次章节范围的明确规则；
4. 与前章/第二章交界页的包含与排除范围；
5. 独立全章 census：题页数、答页数、题目数、答案数、共享材料/任务数；
6. 对 8 个已观察资产与新增/缺失资产的逐项 reconciliation；
7. 人工内容/几何验收，以及有权消费者对新题答关系的明确回执。

在这些对象齐备前，只能继续做离线候选整理和定向复核，不能宣称第一章完整、Q9 已配题、已人工验收或可平台提交。

## 7. 交付物

- 机器回执：`outputs/q9-chapter-independent-audit-20261021.json`
- 可重跑校验器：`tools/q9_chapter_independent_audit.py`
- 未应用的最小加固补丁：`outputs/q9-reflection-staging-hardening-20261021.patch`

所有结论均来自固定本地包、固定图谱和原像素只读检查；未访问或修改网站标注。
