# 来源绑定的内容修订与当前质检

2026-10-17，B侧，基线`89f30f653a3cfe3caa49e64b7730aff35d0b9a07`。继续[长期路线](b-long-term-goal.md)的内容闭环：在现有行内候选之后，按显式计划重建答案和解析，并重新检查配答及内容。全部离线，网站标注保持只读；公共合同仍为草案，A接收及联调为PENDING_A。

## 修订计划与真实重建

`b-content-revision-plan-trial/0.1`绑定当前E、G05和Check05。每次修改产生新计划，保存完整前版；操作列表是针对原G05的完整快照，不是对上次结果再打一次补丁。清空操作列表可显式撤销草稿修改。当前检查变化时，旧计划明确失效，需要新版本重新绑定，不能静默迁移审核依据。

| 操作 | 内容来源与约束 |
|---|---|
| EDIT_TEXT | 明确答案、既有answer/explanation角色、原片段内区间及旧文字；替换文字另存。支持不等长、多处不重叠修改，保留全部未修改字符，不凭“解”虚构解析或更改归属 |
| SELECT_INLINE | 明确原文区间，另绑定已有candidate/call/unit；逐字符使用保存的raw_latex，原候选及所有分歧保留。语法支持或多遍一致都不能代替内容核准 |
| JOIN_RAW_WRAP | 选择已有同题同角色的原文关系，只去掉两个相邻文字片段间的聚合换行。片段、文字呈现区和原图位置仍各自保留；不能跨图片、角色、未归属行或新题边界拼接 |

三个字符空间分别管理：原OCR元素的`fragment.text_span`、原片段内部的修订`fragment_span`、补读OCR字符串中的`unit.char_span`。补读索引和CTC估计框不能自动变成原文的替换区间；选择候选也必须由计划独立声明原区间。修改不生成精确字形坐标，不把编辑后的文字冒充原始OCR。

这些字符串区间均按Unicode码点计数、左闭右开，不按UTF-8字节或UTF-16单元计数；A的JavaScript消费者须显式转换，不能直接把含扩展数学字母的码点索引用作UTF-16字符串切片。

新G06（`b-graph-trial/0.6`）实际更新活动`answer.text`、`explanation_text`和文字呈现区；`content_fragments`逐段记录新文字来自原文还是某条操作，保留输入/输出区间。原fragments、来源账本、图片、图内诊断及所有行内候选不改；完整G05、Check05和计划作为历史档案。几何仍为原OCR/呈现区范围，文字修订不证明字框精度或图像语义。

全部题目的配答候选和题型依据当前答案重算，仍限定书籍、章节/课时命名空间和印刷题号。没有对应题页的反思Q9不会因此取得新配答；19条未归属来源也不能用文字修订强行分配。该格式需要显式支持修订层的消费者，不能交给仅识别旧schema的A适配器后猜测已兼容。

## 新检查如何处理旧问题

Check06（`b-check-trial/0.6`）绑定实际G06和当前计划，重新运行题目覆盖、同范围配答、选项、标量答案及相关规则；题型派生和全部内容投影也由独立消费者重建。原来源层、图片和账本与G05逐字段核对。修改后的完整业务core没有被宣称与G05相同。

旧Check05逐项保留：只有与旧图谱上题目规则检查的完整finding严格相同的问题，才能记为已由当前同一规则重检，并记录新的finding或消失依据。其余问题显式携带原检查引用和保留理由。不能按整题或整个错误码清空风险，也不能把上一版本的标量检查当成修改后文字的检查。

每条编辑、选择和换行关系都有当前草稿风险；选择未知语法或模型多余闭合操作数时另加明确问题。`MODEL_DRAFT`和`HUMAN_DRAFT`表示编辑者声明的来源类别，均不等于人工独立核准。执行READY、来源审计accepted和内容选择是不同状态，结果仍为HOLD、complete=false、transcription_verified=false、business_acceptance=false。

## 本地准备与执行

准备工具读取明确的当前E/G05/Check05、操作列表和编辑者说明，只创建新的本地计划文件，拒绝覆盖、重复JSON键、非有限数值和准备过程中变化的输入。它不应用计划、不调用识别模型，也不操作平台。

```powershell
Expand-Archive tests/fixtures/book46007447/content-revision-inputs.zip data/runs/content-revision-inputs
python tools/prepare_content_revision_b.py --evidence data/runs/content-revision-inputs/evidence.json --graph data/runs/content-revision-inputs/graph.json --base-check data/runs/content-revision-inputs/base-check.json --operations C:/drafts/operations.json --author-kind MODEL_DRAFT --author-id B-offline-development --author-note "Offline development draft; not human verified" --out data/runs/content-plan-v1.json
```

`operations.json`必须是完整操作数组，元素字段见生产模块及回归；不接受仅带一句自然语言指令的文件。修改已有计划时用`--previous`归档前版，仍提供完整新数组。作者类别、来源绑定和每条理由均保留，不能把agent开发修订标成人工验收。

在[现有12阶段命令](b-pipeline-inline-46007447.md)上增加`--content-revision <计划JSON>`，会在`inline_quality`之后追加`content_apply`和`content_quality`。可以用`--stop-after content_apply`停止，再在同目录恢复；只有全部声明阶段完成才提供当前E/G06/Check06。计划无效、过期、独立检查拒绝或执行中输入变化时，最终引用为null，历史成功/失败及不可变物件保留。计划单独变化只重做这两个阶段，不隐式重跑OCR。

本地回滚要求调用方独立保存的当前G06引用，核对精确投影后返回完整原G05；该引用是版本一致性约束，不是签名或授权。后续编辑不能通过更新内部摘要让旧回滚静默丢弃它。

空操作计划会撤销正文等内容修改，但产物仍是G06，并保留新增的complete=false、transcription_verified=false、new_model_calls=0三项显式草稿标记。实际样本已核对其余业务payload与G05完全相同；需要完整原G05对象时使用上述有外部版本约束的回滚API，不把空计划的新版本称为旧对象本身。

## 固定样本与验收边界

`content-revision-inputs.zip`冻结上一版本实际处理的E6/G05/Check05及当前review，四份对象以新的UTF-8 JSON文件导出，原对象内容、引用和生产者不改。清单保留原不可变stage wrapper的SHA、导出代码版本及六张来源摘要；新文件字节不冒充历史原文件字节。输入来自已经做过来源检查的无模型实际运行，包中没有原图、权重或人工金标准；仅靠此包重放修订不能重新证明原图像素或内容准确率。

原模型错误、候选选择和人工修订入口均保留为离线开发范围，真实计划使用MODEL_DRAFT。确切计划版本、真实执行/故障控制、最终回归、干净Git导出及运行环境证据在本轮评估中记录。转写核准、复杂二维结构、更多题页/材料身份、整书来源、独立留出与A固定消费者仍须继续完成。

最终干净Git导出984项完整回归通过（此前908、新增76），196个受版本管理的源码、工具、测试及固定输入文件与导出核对相同；两套依赖环境均禁止模型导入和网络，实际完成14阶段，最终E/G06/Check06引用一致。完整套件只在基础环境运行，第二环境验证实际流程。本轮15份实际执行回执含停止、失败及故障控制，另有两份导出环境完整重放；见`evaluation/book-46007447-content-revision.json`。

真实v2有4个既有候选选择、1条开发编辑、2处原文换行关系，实际修改一个答案而没有虚构对应题页或新配答。Check06当前126问题：66项旧问题按不变来源保留、52项旧finding逐项重检，另有8项草稿风险；全部旧118问题仍归档。`925.625`的标点/小数歧义及“妈蚁”等旧OCR错误还在，不能称全文已正确转写。实际v1错误`=1725`及闭合风险保留为负例，v3空操作验证撤销。
