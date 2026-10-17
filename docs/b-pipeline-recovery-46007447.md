# B侧自动接入局部回补与派生审核

2026-10-17，基线`7759776b0614dff883a91d60da15429414e70374`。本增量继续长期L2/L5：把已有来源绑定的局部OCR回补接入离线pipeline，并将派生审核单独缓存。公共合同仍为草案，新增格式为B trial；来源/执行完整性、内容核准和业务验收分别记录，结果始终HOLD。A接收验证仍为PENDING_A。

本文说明接口、身份和恢复行为。本轮真实运行、完整回归、Git导出及确切提交的最终记录由[状态入口](status/b.md)和对应`evaluation/`材料汇总；不以合成回归代替真实运行结果。前轮基础pipeline记录保留在[b-pipeline-46007447.md](b-pipeline-46007447.md)。

实际结果：主目录与Git导出目录均通过558项测试。真实5页复用旧CPU页缓存，新增32次答案行OCR后自动迁移回补；结果为34题、66答案候选、34唯一同范围链接候选、19未归属行及110项问题，全部HOLD。停止续跑、只改review、损坏recover后的重建及4组真实负例已验证，原图不变。导出将包和三个JSON从CRLF转为LF，实际字节SHA发生变化，文本SHA及全部裁片/像素回执不变；新E3、图谱和质检三个引用与主目录一致。隔离依赖环境也取得相同三个引用。完整记录为`evaluation/book-46007447-pipeline-recovery.json`；本轮网站请求及标注操作为0。

## 新增阶段

提供`--recovery PACKAGE.json`后，阶段顺序为：

| 模式 | 阶段 | 识别边界 |
|---|---|---|
| LIVE_BATCH | recognition → refine → recover → assemble → recovery_review → quality | 默认几何模式仍在refine前以OCR_REQUIRED等待；只有显式`--ocr`才运行基础页和答案行细化OCR |
| CACHED_INPUT | evidence → recover → assemble → recovery_review → quality | 只读导入原始E0.2并应用已有回补，不新建OCR调用 |

不提供`--recovery`时保留前轮阶段。已有E0.3仍可走原导入路径，但不能再叠加恢复包；即使改回schema标签，带有既有恢复应用字段的输入也不能充当原始基底。恢复包不自动开启OCR。

`recover`输出新的来源绑定E0.3，归档旧证据、原回补与来源审核。`assemble`消费这个新E；`recovery_review`从原审核材料和新E派生审核产物，随后`quality`消费该审核。只修改review时，evidence/refine、recover和assemble保持有效，只重做recovery_review及quality。来源、context或回补材料改变时，按实际依赖重算或明确拒绝过期迁移，不能将旧观察无声绑定到新OCR。

`--stop-after recover`和`--stop-after recovery_review`仅在提供恢复包时合法。缓存模式继续拒绝`--ocr`、`--max-items`和`--stop-after refine`；缓存模式的`--stop-after recognition`仍对应evidence导入。`--max-items`只限制live基础识别调用，完整声明范围不缩小，未完成的页和阶段仍在报告中。

## 恢复包与严格迁移

包格式为`b-recovery-package-trial/0.1`，策略`EXACT_PAYLOAD_EQUIVALENCE_ONLY/0.1`。manifest声明book/scope、包身份，以及三个文档：

| 文档 | 内容 |
|---|---|
| base_evidence | 原始b-evidence-trial/0.2，包含完整页描述、原OCR、细分OCR和context |
| recovery | 已有b-recovery-trial/0.1原始假设、预处理/裁片回执和替换方案 |
| source_review | 已有b-source-review-trial/0.1来源审核、选择及独立回归材料 |

每个文档绑定相对路径、规范化UTF-8文本SHA和artifact引用。文档及`recovery.probes[].crop_path`均相对**包manifest所在目录**；原图路径仍相对**source manifest所在目录**。拒绝绝对路径、网络路径、`..`、反斜杠和逃出包目录的符号链接。裁片字节、尺寸、原图SHA、裁片与原图对应像素，以及每个预处理后的像素摘要均需核对。

迁移必须满足当前E0.2与历史base的**完整payload逐字段相同且规范摘要相同**。只匹配页面SHA、OCR文字或少数行不够：原始行、细分行、窗口及payload元数据的单字段差异都会阻止复用。新的base身份可以与旧身份不同，但不能改写旧E、R、source_review的引用、内容或生成时间。

新E的`recovery_migration`分别保存current_base_ref、original_base_ref、原R/source_review引用、旧派生引用、完整payload等价证据及包内容回执。旧原件保留为历史归档，不伪造为“刚针对新base采集”的OCR。公式目视参考仍是MODEL_VISUAL开发材料，原始CPU观察和显式SYNTHETIC_TEST回归来源分开；都不升格为人工标准或业务验收。

## 文件字节回执与语义身份

Git导出或Windows换行转换可能改变JSON文件字节，而当前base的生成时间也可能变化。新迁移将这些执行事实与可重复内容身份分开：

| 信息 | 运行回执/依赖 | 新E及派生审核的内容回执 |
|---|---|---|
| 包manifest及三个JSON文档的原始file_sha256 | 完整保存，用于缓存失效、旧报告复核和运行末尾变化检测 | 仅这组文本文件的raw file SHA不投影入语义内容 |
| UTF-8规范化换行后的text_sha256、文档路径及artifact引用 | 保存 | 保存，策略为NORMALIZED_TEXT_CONTENT/0.1 |
| 二进制裁片SHA、原图SHA、来源描述及像素摘要 | 保存并与实际文件/像素校验 | 全部保留，不按文本换行规则放宽 |
| 本次实际执行时间 | wrapper与SQLite的attempt/事件保留 | 新E与新RecoveryReview不添加新的created_at；历史归档时间不改 |

新E和派生审核使用`REFERENCE_BOUND_EXECUTION_TIME_IN_JOURNAL/0.1`身份策略，以book/scope、输入artifact引用及已有run_id绑定身份，不把整个当前输入的易变生成时间当作身份源。相同引用、payload和运行身份下，仅改变当前base的created_at，或仅将包JSON的LF/CRLF互换，E3、图谱和检查引用应稳定。

这不表示忽略运行中改文件。pipeline仍记录完整原始字节回执；字节变化后旧报告独立复核应拒绝，恢复阶段须按新依赖重新执行。执行途中输入变化记录失败和终止回执，不能沿用旧报告声称READY。历史不可变物件和已保存checks不覆盖。

## 独立检查与状态

`recovery_stage_quality.py`不调用恢复生产者；独立核对实际包/原图/裁片、历史引用、完整payload等价、原件归档、逐行替换/保留投影、派生审核和固定生产者/身份。`pipeline_quality.py`进一步核对阶段实现、实际输入、SQL意图/attempt/事件、当前run与缓存来源、wrapper、图谱和检查依赖。不能通过协调改账本、伪造人工标签或任意artifact ID绕过来源检查。

回归包含明确合成像素/假设的停止续跑、review仅影响两个后继阶段、原始与细分OCR单字段变更、重复回补拒绝、损坏包、途中输入变更、相对目录导出，以及生成时间/文本换行变化下的身份稳定性。合成后端显式标记SYNTHETIC_TEST；缓存恢复在禁止模型运行库导入与网络的进程中验证。真实素材和实际运行证据另行记录。

CLI沿用`b-pipeline-cli-result-trial/0.1`，每次正常生成pipeline报告后保存独立check。完整性审核通过的PARTIAL或READY退出0；阶段FAILED或审核拒绝退出1；参数错误退出2。READY只表示离线阶段完成，accepted只表示所检查的来源/执行一致；decision仍为HOLD，business_acceptance与transcription_verified均为false，platform_actions为空。

## 复现入口

固定包为`tests/fixtures/book46007447/recovery-package.json`，对应裁片随fixture保存；完整原图仍需通过来源包提供。`SOURCE/source.json`为本地原图manifest占位，须包含与固定base精确一致的完整声明范围。

```sh
# 已有原始E0.2，停在回补阶段；不运行模型
python tools/run_pipeline_b.py --source SOURCE/source.json --context tests/fixtures/book46007447/context.json --review tests/fixtures/book46007447/review.json --evidence tests/fixtures/book46007447/ocr-evidence.json --recovery tests/fixtures/book46007447/recovery-package.json --workdir data/runs/pipeline-recovery-cached --stop-after recover

# 保留同一workdir，继续组题、派生审核和质量检查
python tools/run_pipeline_b.py --source SOURCE/source.json --context tests/fixtures/book46007447/context.json --review tests/fixtures/book46007447/review.json --evidence tests/fixtures/book46007447/ocr-evidence.json --recovery tests/fixtures/book46007447/recovery-package.json --workdir data/runs/pipeline-recovery-cached

# 默认live几何识别仍在refine前等待，不因恢复包隐式OCR
python tools/run_pipeline_b.py --source SOURCE/source.json --context tests/fixtures/book46007447/context.json --review tests/fixtures/book46007447/review.json --recovery tests/fixtures/book46007447/recovery-package.json --workdir data/runs/pipeline-recovery-live
```

需要实际CPU基础识别与细化时显式加`--ocr`，并准备对应可选依赖和模型。该路径生成的完整E0.2 payload仍须与包内base精确等价才能复用已有回补；发生差异时应保留失败证据并重新准备来源绑定的恢复材料。

report的`payload.stages[].output.path`指向不可变wrapper，`payload.result`为原业务产物，`result_ref`为其身份。recovery_review的业务结果是RecoveryReviewTrial，其`payload.review`才是后续质检消费的审核文档；外层保留原review与新E的依赖。`checks/`保存每次独立审核，SQLite和objects保留恢复历史。

## 本轮范围与A交接

本轮自动接入的是已有局部OCR回补及其审核迁移，不自动串入专门公式选择，也不自动应用Q9的0.4跨页续接/回滚。数学转写冲突、材料公共身份、整书来源/目录、留出集和A固定消费者仍待继续推进。局部范围、候选数量、恢复成功或结构一致不能代表全书覆盖、内容准确率或平台可提交。

网站标注保持只读，本增量不包含平台写入、保存、识别提交或最终提交。A需按[材料清单](a-side-request.md)核对精确提交、B trial到公共合同的适配、内容身份与字节回执、支持版本及失败路径；A自行记录接收验证，当前仍为PENDING_A。
