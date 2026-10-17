# 行内数学接入当前图谱与持久质检

2026-10-17，基线 `79bfff626f01215dd53ab11758b06dbb33524e8f`。本增量继续长期L1内容组装、L2可恢复处理和L5交接；完整终点仍见 [长期路线](b-long-term-goal.md)。公共合同尚未冻结，A接收和联调为PENDING_A，网站标注保持只读。

## 新的处理链

在原识别、细化、回补、组题配答、跨页续接及当前质检后，显式 `--inline` 和 `--inline-source` 追加三个独立缓存阶段。无这些参数时保留原链；缓存导入不加载模型。无跨页包也能对当前基础图谱附加补读；有跨页包时必须取实际扩展E6/G4/Check04，不能使用先前基础图谱或旧检查冒充最终结果。

| 阶段 | 产物及完成条件 |
|---|---|
| inline_prepare | 核对明确声明的全部行、普通OCR、公式结果及真实journal；保存原始档案、当前片段/呈现区绑定、跨行关系与独立检查。调用尚未完成时保留PARTIAL及完整范围，执行失败或审计拒绝保留FAILED |
| inline_apply | 仅在准备READY时生成b-graph-trial/0.5；原题目、答案、片段、呈现区、配答、来源账本和旧问题逐字段不变，只新增inline_content。全部数学单元、调用、候选、未推理单元、当前绑定及关系保留，未选文字 |
| inline_quality | 为实际E/G05生成b-check-trial/0.5。显式证明原业务core相同后复用当前基础检查，归档完整原检查；保留全部原问题，追加转写未核准、未知语法及跨行/模型闭合冲突的分组问题 |

原有当前业务core的核对与新附件审计分别记录。新检查不是重新认证了全部文字正确，也不把原检查的旧图谱引用换名后直接使用。Check05明确列出当前G05、原G/Check、准备及应用引用、原core摘要和复用依据。无论运行READY或来源检查accepted，业务始终HOLD、complete=false、transcription_verified=false。

## 旧模型记录与当前来源

通用本地包声明一个来源资产、完整行列表、五份精确文档和journal的全部文件。旧观察仍引用当时的E、布局、调用和模型；不重签旧CPU记录。只有当前与原E的书/范围、完整context及所选整页对象严格相同时，才能把旧观察绑定到当前片段；其他页的变化不需要重跑这页模型。比较按规范JSON摘要进行，不能将布尔值与整数视为相同。

每份文档及journal文件都核对完整字节、SHA、相对路径和范围；外部原JPG还核对文件SHA、尺寸及RGB像素。准备和运行结束再次读取全部输入以发现途中变化。当前片段的父行必须由实际evidence_refs证明，原文、跨度和几何也须一致；不能改parent_line_id把另一行的片段伪装成所选行。未归属行显式标记，不能通过补读包替它确定题目身份。

新工具 `prepare_inline_package_b.py` 把此前冻结观察包解到一个新的本地目录并生成清单，不复制新模型记录。先校验外部包SHA、内部manifest和每个ZIP成员，拒绝路径越界、重复、符号链接、额外成员及变更字节。保留所有旧partial/resume/warm和探索回执；不能覆盖旧输出目录或重写原SQL。

## 跨行关系与冲突

关系模块仅从当前原始OCR的字面跨度构造候选：行尾明确运算符接下一行数学前缀，或下一行明确继续比较链。它核对已知栏目/窗口/章节、阅读顺序、垂直间距、水平重叠和所有原始中间行；跨度必须由同一答案、同一角色下的已消费片段无缝、无重叠地覆盖。新题号、选项号、子问/方案号、图片诊断文字、未归属或缺口均不能据此拼接。

46007447的旧CPU第3行本来含 `AB²=10²+25²=`，下一行以`725`开始；来源关系可以保留为 `AB²=10²+25²=725`。与此同时，公式模型紧裁片四个候选在等号后多生成`1`，这些原始字符串及冲突诊断完整保留，未删除`1`再与下一行混拼。

另一条比较链保持原OCR的 `AB²=30²+5=925.625<725<925`；漏上标、标点/小数歧义仍在，不能为了数学成立把它自动改成干净表达式。关系只能证明符合本规则的来源衔接，不证明公式内容正确；它当前只支持同一来源资产的行关系。真正跨页的来源关系仍依赖此前独立续接证明，不能由相邻资源号推断。

## 复现与交接

```powershell
python tools/prepare_inline_package_b.py --bundle tests/fixtures/book46007447/inline-observed.zip --manifest tests/fixtures/book46007447/inline-observed-manifest.json --out data/runs/inline-package --formula-run formal-warm
python tools/run_pipeline_b.py --source C:/sources/source.json --context tests/fixtures/book46007447/context.json --review tests/fixtures/book46007447/review.json --evidence tests/fixtures/book46007447/ocr-evidence.json --recovery tests/fixtures/book46007447/recovery-package.json --continuation tests/fixtures/book46007447/continuation-package.json --adjacent-source C:/sources/46007447_resource_173.jpg --inline data/runs/inline-package/inline-package.json --inline-source C:/sources/46007447_resource_173.jpg --workdir data/runs/inline-pipeline
python -m unittest discover -s tests -v
```

`source.json`声明原5张来源，路径按原清单相对规则解析。相邻原图SHA为`8380f9a1872c830b1cf4fba12fa00e3b6d9c50ddaed357587de7333086e9cdbf`。观察包已在仓库，原图和模型不另上传；打包/导入/重放不运行新OCR。可用 `--stop-after inline_prepare|inline_apply|inline_quality`，重复同一运行目录可恢复。准备包可显式选择`partial8`、`resumed`或`formal-warm`，不能用限量观察缩小原84次范围。

最终回执只有全部声明阶段完成才给出当前E/G05/Check05；停止、待补读、失败或输入变化时为null。来源与结果不变时命中缓存；只改业务review仅重派生审核及相关质检；坏应用物件先被独立拒绝，再重建它与依赖它的检查。真实进程发布物件但SQL未提交后，恢复必须标记旧attempt为INTERRUPTED并重新构建，孤立文件不能冒充成功。

无跨页模式的回归还发现新基础质检顶层生成时间会使Check05在两个fresh目录漂移。现仅对inline开启时、本次尚未发布的新quality产物采用明确时间策略；真实执行时间留在stage journal，历史观察及检查档案不改写。未开启inline的旧链行为保留。这项fresh目录回归与含续接模式分别验证，不以含续接的稳定结果代替基础模式。

最终补齐`formula_backend`及`batch`的缓存依赖版本；任一变化会主动失效三个inline阶段，独立消费者使用相同依赖集合核对。补丁仅改变流水线缓存指纹，不改业务产物。真实故障控制保留补丁前的确切pipeline源码摘要；最终干净导出另在两个环境重放完整12阶段并比较相同业务引用，范围和版本不混记。

本轮独立审计不调用阶段生产者、模型或解析器；分别重建包、来源等价、片段归属、全部附件、关系与拒绝对、风险及当前检查引用。确切实际运行、故障控制、源码摘要、最终完整回归和Git导出重放见 `evaluation/book-46007447-pipeline-inline.json`。交付版本以本文所在提交/PR head为准，A须自行记录接收验证。

最终干净Git导出908项完整回归通过（此前807、新增101）；两套依赖环境均在禁止模型导入和网络的条件下实际重放完整12阶段，最终E/G05/Check05引用相同。完整测试套件只在基础环境执行，不把第二环境的实际流程重放称为第二次全套测试。全部180个受版本管理的源码、工具和测试/固定输入文件与导出核对相同；文档及本轮评估在验证后补录。

## 后续仍需完成

内容尚未选择或核准，19条数学来源仍未取得公共身份；当前仍只有原5页及相邻页前缀。接下来要验证选择/人工修订如何重建正文、受影响组装/配答及再质检，处理CTC分段漏项、混排和二维公式；并行补齐整书来源、独立人工留出样本及A公共消费者。可恢复候选附件不是完整转写、整书验收或平台可提交结果。
