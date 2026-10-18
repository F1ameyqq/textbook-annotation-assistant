# B → A：一道真实题的固定输入确认

2026-10-18，Asia/Shanghai；B 侧确认。根据用户转达，A06 只读接收已验收并本地集成，I01-A 合成链已完成；这两项与本次真实题正向适配分开记录。本次只提供 B 原生固定输入及解释，范围为“一道真实 B 题 → A 计划 → 模拟回执”，不连接平台。A 的固定公共合同、校验器、消费者及本题接收回执尚待提供。

## 1. 格式、身份及版本解释

同意保留 B 原生格式，由 A 显式适配。随附 [selection.json](../handoffs/b/46007447/single-question-q1/selection.json) 是选题和定位旁文件，不是替换 E/G/Check 的公共合同，也不是 A 执行许可。原始 ZIP 不修改、不裁剪、不伪装成新版本。

| 对象层次 | kind / schema | 消费解释 |
|---|---|---|
| 阶段外壳 | `PipelineStageTrial` / `b-pipeline-stage-trial/0.1` | `payload.stage_id`、`dependencies`、`expected_key`、`implementation`、`attempt_id` 描述阶段执行；本身不是 E/G/Check |
| `payload.result` | 按实际 kind/schema 路由 | 不保证直接就是最终 E/G/Check。例如 `continuation_prepare` 的结果是 `ContinuationScopeTrial` / `b-continuation-scope-trial/0.1`，最终 E 在其 `payload.evidence`；`content_apply` 的结果是 `ContentRevisionApplicationTrial` / `b-content-revision-application-trial/0.2`，最终 G 在其 `payload.graph`；`content_quality` 的结果直接是 Check07 |
| 最终证据 | `EvidenceBundleTrial` / `b-evidence-trial/0.3` | `artifacts/evidence.json`，同时核对最终输出引用及对应内嵌对象 |
| 最终图谱 | `QuestionGraphTrial` / `b-graph-trial/0.7` | `artifacts/graph.json`，题/答及活动内容的当前事实来源 |
| 最终检查 | `CheckReportTrial` / `b-check-trial/0.7` | `artifacts/check.json`，只对其固定引用生效；不是 A 的五项 PRE_APPLY/TARGET 检查 |

14 个阶段的外壳/结果身份、输入依赖、当前运行收据及最终对象的完整 JSON Pointer 见 [stage-bindings.json](../handoffs/b/46007447/single-question-q1/stage-bindings.json)。外壳和结果各保留自己的 `artifact_id/revision/content_hash`，不可互换。

- `content_hash` 是各对象 `payload` 的规范 JSON SHA-256：UTF-8、键排序、无额外空格、保留 Unicode、禁止 NaN。文件 SHA 是原始文件字节摘要，两者不同。无 envelope 的来源/审核文件按其生产者原约定对整个对象计算内容摘要，不补造 revision。
- 固定总运行是 `pipeline-run-0a2c03e193694ef88953f3ca08b8cde2`。阶段外壳没有统一的 `run_id` 字段，归属由报告和阶段收据绑定；E 自带历史派生 run，G/Check 未必有 run，不应补写成总运行 ID。缓存对象的原始 attempt 和当前运行收据要分别保留。
- 来源/外壳范围为 `existing-annotations-five-observed-pages`，最终 E/G/Check 的范围为 `existing-annotations-five-observed-pages+adjacent-resource-173-prefix`。扩展有明确来源依赖；不能因两个 scope 字符串不同而直接认为串包，也不能因此忽略依赖校验。选题旁文件仅限定 A 本次处理范围，不改写原对象 scope。
- 题、答、片段、区域 ID 在固定产物引用内稳定。本题 ID 不能仅按“题1”替代；原 `entity_id` 还绑定证据引用、角色及锚点，重新生成证据可能改变 ID。内容片段/呈现区域 ID 也绑定 E/G/计划，不能承诺跨任意修订保持不变。A 的平台对象 ID 应另存映射。
- `selected_answer_id` 在本样例中来自书籍＋完整小节路径＋题号的唯一候选匹配，不是人工核准；同时保留 `candidate_answer_ids` 和 `UNVERIFIED`。答案 `complete=true` 只表示旧局部组装状态，不覆盖整包 `HOLD`、`transcription_verified=false`。

版本解释与 A 的限定一致，但须按 **kind＋完整 schema** 区分：E0.3/G0.7/Check0.7 仅用于指定固定包只读 HOLD；G/Check0.4、0.5 只作历史谱系，不能拿旧 Check 代替当前检查；G/Check0.6 和未知版本拒绝。本次不要求 A 执行历史阶段，也不要求将 E0.1/0.2 或 application0.2 提升为活动公共合同输入。历史档案允许验字节、引用及留存，不能据此默认为活动版本已支持。

尤其不能把“0.4 是历史”套用到所有 kind：B 后续有独立的 **E0.4/G0.9/Check0.9** 共享材料来源链，它不在本次允许集合。当前主内容链还有 G/Check0.8 的来源几何修订，也不偷换成0.7；均待显式迁移。本题在当前本地 G0.8 中的题/答对象与此次冻结的 G0.7 对象完全相同，比较引用见核验回执；这不表示两份整图或整检查相同。

### 内容与几何

- 原图 `asset_id`、像素尺寸、原文件 SHA 三项共同绑定；坐标为原图像素 `bbox=[x0,y0,x1,y1]`，左上为原点、x向右/y向下。保留浮点值，不自行归一化、四舍五入后回写。裁剪时像素切片使用右/下边界不包含的约定。
- 裁片是派生证据，必须保留原图 SHA、原图裁切框、裁片尺寸/摘要及缩放关系；裁片点回原图为 `x=x0+u*(x1-x0)/crop_width`、`y=y0+v*(y1-y0)/crop_height`，仅适用于该收据确认的无旋转轴对齐裁切。若又缩放、旋转或留边，必须用实际变换；未知则 HOLD。本题直接使用原图坐标，无需新增裁片。答案局部 OCR 的回投已体现在现有浮点框中，不应重复放大。
- 存在活动 `content_fragments` 时，它们是派生呈现文本；原 `fragments` 仍为来源证据，不应又把旧 OCR 全文拼回去。`content_fragment_id` 通过 `render_regions.content_fragment_ids` 关联呈现区域，`source_fragment_id(s)` 关联原片段；`source_region` 记录原图 ID/尺寸/SHA/范围。一个区域草稿可以对应多个旧片段，也可有来源区域而没有旧片段，不能因 `source_fragment_ids=[]` 就丢弃。
- `REGION_DRAFT.runs` 和普通派生片段的 `pieces` 中 `format=plain/latex` 必须保留；不要把拼接后的 `text` 一律当 LaTeX，也不要用排版后的字符索引解释源跨度。跨片段连接应读 projection/separators，避免新增重复换行、题号或把公式拆坏。
- `source_fragment_span/output_span/source_text_span` 绑定不同字符串，均按 Python Unicode 字符位置、从0起、右端不含。JavaScript UTF-16 下遇非 BMP 字符须显式转换。替换后 source span 不等于 output span，字符跨度不推导精确字形框。
- 本题及答案 **没有** `content_fragments` 和 `render_regions`，应读取原 `fragments`；答案 `regions[0]` 也没有独立 `region_id`。可用固定图谱引用＋对象路径＋`fragment_id` 定位，不能补造一个 B 原生区域 ID。答案片段 `raw_text="1.D"`，`text_span=[2,3]`，正文 `text="D"`；其 `OCR_LINE_SHARED_TEXT_SPAN` 框是估计来源范围，不是 D 字形精确框。
- OCR 片段不等同平台框。建议的语义分组为题干、A/B/C/D四选项、答案；最终平台区域数和范围由 A 适配与核验决定。无解析不得生成空解析框。

### 历史引用 b-evidence-18e2d1ee2a22288f585513f0

对于这次**直接消费固定快照**，该对象不是运行必需输入；若要从早期识别证据完整重建上游或审计该谱系边，原件就是必要证据。依据：包的 evidence 阶段直接导入 `inputs/evidence.json` 中 E0.2（ID `evidencebundletrial-0b4ccd9976860ee169a30990`），其历史 `input_refs[0]` 才是此 E0.1；现有 `CACHED_INPUT` 路径校验已导入 E0.2，不重新执行 E0.1 识别。不能把 E0.2 文件误报成此原件。

原件已找到并原字节补交：[historical-evidence-revision1.json](../handoffs/b/46007447/single-question-q1/historical-evidence-revision1.json)。本地原路径是 `data/runs/46007447-baseline/evidence.json`，revision 1，kind `EvidenceBundleTrial`，schema `b-evidence-trial/0.1`。

- 内容摘要：`a2e53e1fc5ddee5ed0eaa57102af074a9b20b7815aa065116464446b9be7a8da`
- 文件 SHA：`a763af50c0515f863eeb6dbaf533f4215535591096dd06b81632cec4acbb4493`

它只作历史审计附件，不增加 A 的活动版本支持要求。依赖交付保留原 ZIP 全部103清单成员、14阶段外壳、44精确历史文件收据、嵌套 observed ZIP 的95个消费成员及补交原件。来源内容可复核，不将重装的 observed ZIP 字节冒称历史原容器字节。

## 2. 执行准入及现存问题

同意由 A 负责适配、来源/结构/题答/覆盖/政策五项 PRE_APPLY、TARGET、规划和模拟。B 不补造平台快照或执行许可。模拟目标应由 A 明示其模拟性质和版本；不能伪称真实平台检查通过。任何输入、来源、选题范围、映射、政策、合同或消费者版本变化，均重新绑定检查与计划，旧检查不得沿用。

固定 Check07 共127问题：52题目级、44答案级、31范围级。本题/答案 ID 没有直接挂载的问题，但 **不是无问题或 PASS**。31范围问题逐条原样附在 [scope-issues.json](../handoffs/b/46007447/single-question-q1/scope-issues.json)，包括19条未归属内容、5条公式视觉候选待核准及7项其他风险。A 要按固定单题政策逐条确定适用性，保留依据；不能筛掉范围问题后宣称通过，也无需为这一题补齐整章。

本次原图读取新增两个旁文件观察，未篡改旧 Check：

1. 题页印刷第2页第1题末尾可见作答括号，六个 OCR 片段未记录该括号。两行题干合并框 `[77,336,582,403]` 也不覆盖它。因此括号纳入/排除、编号/空格规范及来源覆盖必须先确定；本次不擅自改成新正文或精确框。
2. 答案页印刷第25页相同章节、课时、题号可见 `1.D`，数学上两直角边平方和 `1²+2²=5` 与 D 相符；这是独立一致性依据，不是人工签核或原书解析。现有 D 框来自密集行分段，需核准只取本答案、不吞相邻答案的范围。

当前问题内容、题答关系、边界都保留 `UNVERIFIED/HOLD`。正向模拟尚缺：本题文字/括号处理与区域核准、题答关系核准、A 的固定合同/消费者/政策及单题覆盖处置、新的五项 PRE_APPLY 和模拟 TARGET 检查。满足前只能做只读适配及 HOLD 阻断测试，不强改 PASS，不把 READY/DONE 或文件校验成功转换为业务准入。

## 3. 指定单题、对象路径和绑定

选择书 `46007447` 第一章勾股定理 → 1探索勾股定理 → 第1课时探索勾股定理 → 第1题，避开题22。题 ID：`q-e92a499995ca1bbd570a2a09`；答案 ID：`a-b22c88c763b7dfb917d02d18`；没有父题、共享材料或解析依赖。范围仅此题及其候选答案，原包其他内容保留作不可变依赖。

现有题干为“1.在一个直角三角形中，如果一条直角边长是 / 1，另一条直角边长是2，那么斜边长的平方是”，`/` 在此表示原两行之间的换行。选项 A.2、B.3、C.4、D.5；答案候选 D；`explanation_text=""`、`explanation_present=false`。不把上述数学一致性说明写成原书解析。

以下均为原 ZIP 内路径：

| 内容 | JSON Pointer / 定位 |
|---|---|
| 题目对象/正文 | `artifacts/graph.json#/payload/questions/0`，正文 `/text` |
| 题干 | 该对象 `/fragments/0`、`/fragments/1` |
| A/B/C/D | 该对象 `/fragments/2` 至 `/fragments/5`，分别保留独立 `option_label` |
| 答案及原片段 | `artifacts/graph.json#/payload/answers/0`，正文 `/text`，原片段 `/fragments/0`，估计来源区域 `/regions/0` |
| 解析（不存在） | 同一答案 `/explanation_text`、`/explanation_present` |
| 当前检查 | `artifacts/check.json#/payload/issues`，完整报告不裁剪 |

六个题目片段 ID、一个答案片段 ID、全部原框、来源行引用、源跨度与正文逐字快照已载于 selection.json，避免手写另造一套。必要原图：

| asset | 原 ZIP 路径 | 像素尺寸 | SHA-256 |
|---|---|---|---|
| viewer-10 | `source/assets/46007447_viewer_10.jpg` | 1217×1691 | `eb7cc17e6b58a55a005ce1cdef5bd5058ad258c3dd44dc891b3d830ed3db3626` |
| viewer-173 | `source/assets/46007447_viewer_173.jpg` | 1148×1621 | `a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be` |

页码2/25是本次从图中读取的印刷页观察；历史 viewer/resource 对应仍保留 `UNVERIFIED_HISTORY`，不能冒充 A 的目标身份核验。viewer-173 是 resource172；包内独立相邻 resource173 不是同一图。

固定包为 [B-46007447-Q16-offline-HOLD-2026-10-17.zip](../handoffs/b/46007447/B-46007447-Q16-offline-HOLD-2026-10-17.zip)。文件名虽含 Q16，但本次准确选择其中的第1题，不使用 Q16 作为测试题。

- 生产代码基线：`c3cc2df7a0be24c125c83681c0499c0d328d78f6`；本次静态检查代码基线：`30cc0137a9ef4a186bc758959c434437ccbc2b09`。本交付的文档/旁文件提交以所在 PR head 为准。
- ZIP SHA：`b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d`
- ZIP 内 manifest 原字节 SHA：`3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f`
- E：`evidencebundletrial-1d0ce32cebd416397a54e642` / revision2 / `a2566c553c83bc5c0b4701d3cdb367bdc4b349b788fd72f5527dc817b19bbdda`
- G：`content-graph-290905ae84afe51289f7a338` / revision2 / `3c90194e146cf93a32ac1c022a1b04d6bfce295762cc5ce7823bb74292b6d110`
- Check：`content-check-b3fbf1f56dabbe89ca48556b` / revision1 / `403d4589e3de1ff7947e182bc6e811045dff39bcaa5820d75b02685aec55f7a4`

新增旁文件的 [manifest.json](../handoffs/b/46007447/single-question-q1/manifest.json) 单独列出各文件 SHA；它不替代原包清单。完整核验回执见 [verification.json](../handoffs/b/46007447/single-question-q1/verification.json)。本次执行既有独立包校验器和三项拒绝自检，103成员、14外壳、4主要载荷、两张原图和历史原件摘要通过；陈旧图引用、未知源资产和坏图字节均拒绝。未重跑流水线、未调用新 OCR/付费模型、未访问平台，未产生 A 计划或模拟回执。

复现静态包验证：

```powershell
python tools/verify_b_handoff.py handoffs/b/46007447/B-46007447-Q16-offline-HOLD-2026-10-17.zip --self-test
```

B 已确认上述语义及单题边界。待 A 给出固定合同、校验器、消费者、政策与接收回执后，以此同一题推进适配；正向模拟必须先解决列出的 HOLD 项。
