# 46007447 “漫话勾股世界”G09 只读候选身份绑定 v2

- 日期：2026-10-18
- 决策：`HOLD`
- 证据等级：`MODEL_VISUAL_CANDIDATE`，非人工事实
- 操作边界：离线读取固定冷启动产物、既有五来源行交叉表与七裁片清单；未新增 OCR、未联网、未修改共享仓库、未写生产配答、未改变19条未归属来源行；`production_assignment_allowed=false`。

## 固定目标

本次绑定到以下固定冷启动字节，而不是只依赖易漂移的目录名或“G09”简称：

- `cold-assemble.json` SHA-256：`fd58025e9111bdca4db415b46d40756e9187aa6861aa31d3119600cd8d4ee295`
- 产物：`questiongraphtrial-a2022f6695d80cd6764d2aee`，revision `1`
- content hash：`8cd1dc649f13cb1856fb90f81f9cfa1fb623266a6910371fce2668cabf6aaee7`
- 总控报告的合入提交简称：`b5cc1ea`
- 随附 receipt 记录的运行基线：`13204a7ac3232a1042fdfa9e981e90c8857615da`

“G09”是总控/评估使用的组标签；固定 `cold-assemble.json` 内没有序列化 `group_id=G09`。因此本报告以实际 `material_id`、`task_id`、产物 content hash 和文件 SHA 为身份锚点。

冷启动产物包含1个共享材料、3个任务和48条原题页来源覆盖记录；本次不改变这些内容。

## 实际材料与任务 ID

共享材料：

- `material_id`: `material-940010e304a65065ce384006`
- `source_material_id`: `viewer13-reading-material`
- 标题：`漫话勾股世界 / 教材P6“阅读·思考”变式`
- 路径：`第一章 勾股定理 > 阅读材料`
- 状态：`NOT_A_QUESTION / UNVERIFIED`

三个任务：

| 标签 | 实际 task_id | 题页锚点 | 候选答案范围 |
|---|---|---|---|
| `(1)` | `task-f76ca3153a12aea40b7d481b` | `viewer-13/ocr/41` | 赵爽弦图证明的三个空；五保留行中的102只覆盖第一空。 |
| `(2)` | `task-0a662336bef0b2eaec440a6b` | `viewer-13/ocr/18` | 图2面积验证过程；104只是一个分子字形，108只贡献左侧收尾。 |
| `(3)` | `task-b8a3d034281fd685a5509780` | `viewer-13/ocr/29` | 恒等式、括注与图形；108右侧、110续行和完整图候选共同构成。 |

## 五条来源行绑定

| 答页来源行 | 候选目标 | 必须保留的边界 |
|---|---|---|
| `viewer-173/ocr/102` | `(1)` → `task-f76ca3153a12aea40b7d481b` | 只代表任务1第一空 `a-b`；不能扩成同一物理行上肉眼可见的后三值/整题答案。 |
| `viewer-173/ocr/104` | `(2)` → `task-0a662336bef0b2eaec440a6b` | 仅是任务2公式内分数的分子 `1`；不能解释成独立数值答案或完整证明。 |
| `viewer-173/ocr/108` | 同时跨 `(2)` 与 `(3)` | 不是可原子分配的一行：`x<228` 的候选裁片归任务2收尾，`x≥228` 的候选裁片从可见 `(3)` 标记起归任务3。 |
| `viewer-173/ocr/110` | `(3)` → `task-b8a3d034281fd685a5509780` | 只是上一行末尾“（答”的续文“案不唯一）”；不能作为新任务或独立答案。 |
| `viewer-173/ocr/112` | `(3)` → `task-b8a3d034281fd685a5509780` | 只覆盖图中的一个 `b` 标签；不能代替整幅图。 |

这五条仍保持 `UNASSIGNED / UNVERIFIED`。它们是五个证据片段，不是五个答案实体，也不与三个任务形成一一映射。

## 七块几何裁片绑定

几何清单 SHA-256：`44534f326649eadf32c267afe92bf812cfeeb107e5ef0a4956ec61560a03ccb2`。

| segment_id | bbox `[x1,y1,x2,y2)` | PNG SHA-256 | 目标 task_id | 说明 |
|---|---:|---|---|---|
| `task1-line1` | `[54,1012,282,1044)` | `2408634a37c308e6165651aaa0e3bf924aa47e91abacf0031f26e4f5421c780f` | `task-f76ca3153a12aea40b7d481b` | 宽裁片含任务1三个可见值；102只覆盖第一值。 |
| `task2-line1-tail` | `[282,1012,548,1044)` | `4b748c7dc6bff06a9583590205b1c50d1475744f511f07027f3723bd6be3eed2` | `task-0a662336bef0b2eaec440a6b` | 任务2证明起点；纯模型目视像素，没有新增 OCR 行。 |
| `task2-line2` | `[54,1044,548,1084)` | `5282ec39bd25815eef27fb175480bb8171fe111390931c38298ac1dab179f425` | `task-0a662336bef0b2eaec440a6b` | 任务2证明中段；104只是其中一个分子字形。 |
| `task2-line3-prefix` | `[54,1084,228,1104)` | `de13eb1566a0196f03e51d34131bf9a1fcb8111a269f2ae777f75b285618158b` | `task-0a662336bef0b2eaec440a6b` | 108左段，任务2收尾。 |
| `task3-line3-suffix` | `[228,1084,548,1104)` | `ba6505414add251dbce780785884158f41e1d26cddf1572b632d1938770d36de` | `task-b8a3d034281fd685a5509780` | 108右段，从可见 `(3)` 标记开始。 |
| `task3-line4-continuation` | `[54,1104,154,1124)` | `a92491e265072b776b0c7c4c8520c3946729b7198a50156813fda3fc64e6a764` | `task-b8a3d034281fd685a5509780` | 110续行，不是独立答案。 |
| `task3-diagram` | `[225,1118,372,1240)` | `aa2e04a4189b8df323763b14ced98dea8c6a4fef2fbbf6866abc5e39fdff7817` | `task-b8a3d034281fd685a5509780` | 整图候选，包含外框、分割线和四个 `a/b` 标签；112只覆盖顶部一个 `b`。 |

七矩形两两不重叠；108的左右两段在 `x=228` 相接。既有独立几何复核（SHA-256 `062171e541bf8d15ac3a27a4cca4d9f90d9ab98049e85d46efbd4e40f2a7118e`）在冻结原图与阈值170检查下未发现底边裁切证据，因此不要求扩展 `y2=1240`。这不是人工验收，`FIGURE_EXTENT_UNVERIFIED` 继续保留。

## 版本与账本限制

- 五来源行仍属于19条 `unassigned_answer_lines` 账本的一部分；本次只做版本绑定后的本地候选 sidecar，因此19保持19，不能消账。
- 本材料没有被写成五个答案，也没有自动形成三个生产答案对象。
- 固定 G09 的材料和任务仍为 `UNVERIFIED`，并保留 `FIGURE_EXTENT_UNVERIFIED`、`BUSINESS_REVIEW_REQUIRED` 等限制。
- JSON 中的 `target_task_id` 是待人工复核的候选消费者身份，不是人工核准事实；后续若要写正式共享材料消费关系，必须另行审核并显式执行。

## 交付

机器可读 sidecar：`46007447-math-world-g09-readonly-binding-sidecar-v2-20261018.json`。`candidate_has_single_task_target` 只描述候选目标基数：102、104、110、112为 `true`，跨任务的108为 `false`；每条来源绑定和几何绑定均另置 `production_assignment_allowed=false`，不得把候选基数当成生产授权。

其内部自检确认：固定冷产物 SHA 一致、材料 ID 唯一存在、三个 task_id 与固定材料完全一致、5条来源行和7个几何段完整、所有几何 bbox 与 PNG SHA 均与既有清单一致、未归属行计数前后均为19。

## 历史保留

v1 文件保持原字节不变：sidecar SHA-256 8d8c1df28635ecbceffb6a6a5df038fd38d8b2320a46970d1fc0c3eaa863292e；报告 SHA-256 a38fe070effca0738f38ebe46719e1d92bc70cfe83efebce6bb3915205f5281。v2 仅澄清候选基数与生产权限、以及图底边的历史复核口径，不改变五行/七裁片/三任务映射。
