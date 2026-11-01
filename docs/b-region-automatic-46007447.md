# Q16 来源区域自动草稿

2026-10-17，Asia/Shanghai；B 负责。开发基线 `7eecd46259a04b16368e4be3115c23a7ff2d1854`，交付版本以本文所在提交和 PR #2 head 为准。公共合同仍为草案，A 接收 `PENDING_A`。这是长期 G1 完整答案关口的一项实现，尚未完成正确转写或内容验收；网站标注没有修改。

## 本次改变

此前 Q16 的三行正文依赖显式 MODEL_DRAFT 转写。本次从固定原图和已有分式布局规划正文区域，实际补读正文，再把正文和已有公式观察组装成单独的自动首稿。它沿用区域计划0.2进入既有 G07/Check07及14阶段链，保留此前显式开发草稿和全部原始观察。没有另起公共合同或平台执行器。

- `region_runs.py`：按来源像素与布局生成行、分式槽、正文核心及带上下文的补读范围。不是根据参考答案预设三行或11分式。四个阈值保留所有连通分量，包括单像素、跨槽和未覆盖墨迹；像素账目闭合不代表字形归属或内容完整。
- `region_ocr.py`：正文采用核心裁片6倍缩放与上下文8倍缩放/1.5倍对比度两种固定处理，整行保留后备结果。原始调用返回值、候选、空文字、错误、耗时和变换摘要完整保存。显式 `--collect` 才运行本地 CPU；缓存重放禁止模型及网络仍可完成。
- `region_draft.py`：保存所有整式原始 LaTeX，并从同一分式有来源的分子/分母生成显式 `DERIVED_ROLE_COMPOSITION`。这不是一次完整模型输出，也不代表组合正确。固定首选规则不读取既有 Q16 开发转写；生成计划时才归档并替换该题的旧区域操作，其余 Q9 七项操作保留。
- `region_report.py`：生成无脚本、无外部资源的 HTML，嵌入原裁片，展示三行首稿、正文补读、全部整式/派生候选与风险。可复制 LaTeX 到既有离线复核界面，报告本身不修改计划。它尚不是自动候选选择与复核界面的一体化入口。

三个新 B 内部附件格式为 `b-region-runs-trial/0.1`、`b-region-ocr-observation-trial/0.1`、`b-region-draft-trial/0.1`，不要求 A 直接消费内部附件。最终区域计划、图谱及当前检查的消费边界仍见[区域重建](b-content-region-46007447.md)与[A清单](a-side-request.md)。

## 实际来源和运行

Q16 绑定 `viewer-173`（1148×1621），原图 SHA256 `a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be`，裁片 `[579,263,1084,367]`；与固定 `unit2-q16.png` 的 RGB 像素相同。它与 Q9 的 `resource-173` 是不同资产，不能按数字173混用。

实际产生3行、11分式槽、14正文槽及3整行后备。17单元各两种预处理，共 **34次新增普通 CPU OCR**；本次没有新增专门公式推理。原有44整式观察及角色观察复用，生成298个有来源的派生组合。数量是观察/备选口径，不是正确率。四个阈值的49项像素风险及1项上下文符号归属风险均保留。

固定实际观察位于 `tests/fixtures/book46007447/region-ocr-observations.json`，Git中的LF文件为801789 bytes，SHA256 `88eff1fd3e374061813bddd2521628113df4e8ec0587c71c10691b8701b35c7b`；本机原始CRLF文件为825633 bytes，SHA256 `30fe1be46ea280fad050a23913654705aafa9aa1866cc1c52a762e5a2c176022`。两者仅JSON换行不同，对象及内容引用相同，不声称原文件字节相同。其中归档当次像素计划，保留真实后端的 `[rec_elapsed]` 列表，不重签为新模型结果。它是实际观察，不是人工标准。首次采集的旧组装结果、改规则后的第二版及最终重放均另存目录；没有用最终代码重新冒充采集时版本。

首版因一个小括号核心结果为空而退到整行普通 OCR，丢失 typed 分式。修正为：只有短、无字母数字的上下文符号可进入未核准首稿，并显式保留 `CONTEXT_SYMBOL_OWNERSHIP_UNVERIFIED`；上下文中的相邻分式文字不能静默重复加入正文。最终三行均保留分式结构，不使用整行后备，但原后备结果没有删除。

CLI同时校验原图字节、尺寸、裁片像素，以及显式布局与缓存计划的完整布局/引用。初次 JSON 读取摘要、原图 manifest 声明摘要和裁片摘要在补读前及结束时复查，不能把加载后变化作为新基线；两个独立生成图像回归覆盖“同裁片混资产”和“加载后只改原图尾字节”。

## 当前结果与限制

最终计划 `content-revision-plan-e65910ac6f28ddbb7b4f6d14`（revision4）生成 G07 `content-graph-7d7b2e5b6c5c10085ce0c6dd` 和 Check07 `content-check-a78afd423edbc897cef11d4f`；完整引用及摘要见 `evaluation/book-46007447-region-automatic.json`。基础及隔离依赖环境的实际缓存重放得到相同三个引用。

真实输出仍34题/66答案候选/34唯一同范围候选链接，来源账本202=154归属+29排除+19未归属，5图形。Q16的17个原片段按7/3/7映射为三行活动正文；原 fragments、图片、来源账本及 Q9 操作保留。没有对应题页时不新增 Q16 配答。

当前仍 **127问题/HOLD**。既有独立应用/质检审计验证投影与当前引用，不能核准文字正确。新增50项像素/组装风险保留在自动草稿与 HTML 中；没有声称现有 Check07 为每项新增风险生成独立 finding。当前通用草稿/二维未核准状态继续阻止把结果视为业务通过。

已观察的真实错误包括：首行 `6061` 缺间隔、第三行 `a≥3,ira,` 杂字、第二行 `.a+(` 拼接不完整、∵/∴与外围括号/平方漏读，F2把幂读成t，F3/F5和F11仍有幂或符号错误。旧两遍一致仍漏平方的 F9、重复整个分式的模型结果，以及 F5 与开发目视转写相符的结构备选未被默认选择等负例均保留。找回“都是正整数”不等于整答已读对；没有准确率、人工核准或 G1 通过声明。

## 重放入口

先取得原图 manifest 及对应原图。固定派生输入包 `content-revision-inputs.zip` 可按 `tests/content_revision_observed.py` 校验并导出为 plain `evidence.json`、`graph.json`、`base-check.json`、`review.json`。包和固定裁片不含完整原图或人工标准；缺原图时不能声称已重新验证原图像素。

在仓库根目录使用本地路径，输出目录必须尚不存在：

```sh
python tools/prepare_region_draft_b.py --layout tests/fixtures/book46007447/formula-layout.json --crop tests/fixtures/book46007447/recovery-assets/unit2-q16.png --legacy tests/fixtures/book46007447/formula-observations.json --canvas tests/fixtures/book46007447/formula-canvas-observations.json --roles tests/fixtures/book46007447/math-role-evidence.json --observations tests/fixtures/book46007447/region-ocr-observations.json --evidence <inputs>/evidence.json --graph <inputs>/graph.json --base-check <inputs>/base-check.json --review <inputs>/review.json --previous tests/fixtures/book46007447/content-region-plan-v1.json --source <source-manifest.json> --answer-id a-7302d4870826c53aea0bcd16 --out data/runs/region-automatic-replay
```

该命令复用观察，无新模型调用。只有要另做本地补读时，把 `--observations ...` 换成 `--collect`；新观察另存，不能覆盖旧目录。产物包含 `runs.json`、原始 `observations.json`、检查、自动 `draft.json`、`report.html`、当前区域计划、应用/图谱/检查及摘要。后续使用现有 `run_pipeline_b.py --content-revision <content-plan.json>`，其余来源/恢复/续接/inline参数沿用已有14阶段说明；复核界面可用新计划初始化独立工作区。

干净Git导出首轮1083项运行1147.758秒：1076通过，7项均在旧HTTP测试setUp创建端口时遭Windows10013。只读查看发现连续60个保留端口，旧自动分配最多重试8次，失败时系统选中的端口不可见，保留范围只是诊断线索；最终改为128次有界重试，不改变系统设置，显式端口或其他错误仍直接失败。补丁后10项真实HTTP复跑通过（32.223秒），另有4项独立绑定回归；原完整失败保留，没有把最终全套声称为重跑通过。除server补丁及新增绑定测试外，其余源码/固定输入与首轮快照闭合。两套依赖环境分别重放真实样本且禁止模型导入及网络。14阶段实际消费者的首次干净导出运行0缓存、全部完成，随后14缓存；最终引用与直接CLI一致。复制的历史缓存未在首跑命中，不把它报告成12缓存。六个来源和原包95成员不变。完整数量、耗时、逐文件闭包和真实运行回执见评估文件；完整套件只在基础环境执行。

Edge实际打开本机报告，原裁片与三行首稿可见，F9可展开查看旧一致错误、重复整式及派生组合。没有对网站标注发请求。HTML仅用于候选对照，没有公式排版引擎、编辑/保存或人工内容签核功能。

## 接下来及长期关口

先处理外围符号、幂次、字间关系和候选选择，把自动草稿与离线编辑/当前重检连成易操作入口；不靠更多备选数宣称识别完成。再以独立核对的完整答案验收 G1。并行请 A 分批补完整章节题页/答案页/目录，优先19条材料身份；共同冻结小批未调参材料、核对者、指标分母及验收门槛。之后推进完整章节、整本46007447、A/B固定消费者及获授权的平台读回、跨书留出与维护发布，具体退出条件见[长期路线](b-long-term-goal.md)。

本次新增普通CPU34次，缓存重放及消费者0次；标注网站请求/动作、原图上传、模型下载和额外付费调用均0。长期目标继续进行，A的接收由A自行记录。
