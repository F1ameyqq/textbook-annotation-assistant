# A01 执行交付报告

日期：2026-10-16（Asia/Shanghai）。任务：A01 静态来源与公共几何。状态：**REVIEW / 实现冻结，等待独立验收**。执行自测不等于 ACCEPTED 或 INTEGRATED；未推送、未自行集成、未向其他对话发消息、未创建后续任务。

## 版本、环境及范围

- 实际工作树：`C:/Users/ASUS/.codex/worktrees/a01-source-geometry/1800`；分支：`codex/a01-source-geometry`。
- base_commit / workflow_commit：`39341c98d73c354d639f3beeb55429f55d0e9be5`。接单时 HEAD 一致且工作树干净；C01 R1 已在此基线集成，未按旧摘要等待。
- head_commit（实现、固定样例与运行证据的冻结提交）：`c8b8c6e158547954c59017211507755f67eda0e8`。本报告随后以独立文档提交归档；最终交付 HEAD 的完整 SHA 在交付消息中给出，实现保持本冻结提交不变。
- 合同：C01 `1.0.0-a-proposal` / `c01-exchange-1`；C01 R1 接受提交 `4e42668ab28eda37a37285285d2f6c595d3bba12`，基线中的本地集成提交 `223b0b3d9ae0bd50ef2ac045219a41ad41611856`。
- 实现/样例版本：`a01-static-1`；几何语义：`a01-geometry-1`。两者是 A 内部具名提案，未取得 B 确认。
- 环境：Windows、CPython 3.9.13、Pydantic 2.12.5、Pillow 11.3.0（已安装；未安装依赖或修改根依赖）。
- 仅改 `src/annotation/source/static/`、`src/annotation/geometry/`、A01 专属测试、样例、说明、execution 证据和本报告。目录内 `.gitattributes` 也限于 A01 样例/证据，用于保留摘要绑定字节。
- 没有改 contracts、C01 样例/公共政策、父包入口、根打包配置、delivery/runtime/B 模块、调度状态或 `D:/1800` 主工作区。没有读取凭据/profile。

## 输入与固定输出

| 书籍 | 来源/已取得 | 处理范围与限制 | 固定交换文件 |
|---|---|---|---|
| 46006966 | 四图归档 + 六图来源，按 SHA256 去重为6个页图资产，保留10条来源关系 | 仅选 source 7/8/9/10/233/234；250是元数据页数，另244个源索引未取得。仅 viewer 8/9/10/234→source 7/8/9/233 有证据；source10/234的 viewer 和所有印刷页码未知 | [exchange.json](../../examples/a01/bundles/46006966/exchange.json) |
| 46007447 | review 两图与 execution 两图副本去重为2个资产，保留4条来源关系 | 仅 source13/172，viewer14/173；214是元数据页数，另212个源索引未取得；未重放 A05题22 | [exchange.json](../../examples/a01/bundles/46007447/exchange.json) |

两包各含独立资产、实际目录树、书级容器、相对来源投影、历史原件、观察时间、限制和导入前后摘要。书级容器不是章节映射断言。源索引和 viewer/印刷页码分列；不外推固定偏移。

- 旧书 SourceBundle content_hash：`ff80470b7daf3a30d1d6c7a010dc600bbcf506fcf7e520bc1b1d57973a9118de`。
- 新书 SourceBundle content_hash：`1b662ac5c9ac56b4a0c2e9826ff4cc2c512365c58ca2fafda36df110f9cfc32d`。
- 原图逐张完整解码、核对尺寸和 SHA256。原始清单的个人绝对路径不进入可执行引用；脱敏投影绑定原清单摘要，原件留原仓库。安全的目录、标注和导出历史资源逐字节保留。
- 历史标注/答案均 UNVERIFIED。旧书1条越界框的原 `x2=1181.0944752623527` 原样保留，相对正确1178px原图越界约3.094px；未裁边、未转换为合法 OriginalBox。
- 五条外机来源位置不可用；四份原始 JSON 缺失，未拿现存 redacted JSON 冒充。第五条 `workspace1.jpg` 的仓库本地副本与原清单摘要相同，作为历史截图单独保留，不计为页图。
- 旧书观察日期只精确到 `2026-10-15`；新书保留 A05 归档边界及原网络索引中的历史响应时间，不为无精确时间的别名补造时间。不生成 PlatformSnapshot 或伪实时状态。
- 原件/派生文件明细见 [资源清单](../evidence/A01/execution/final/resources.json)；两包合计29文件，约3.99MB。该数量包含交换描述及历史资源，不能当页数。

## 最短复现

在上述冻结工作树运行；使用已有安装环境，无网络或浏览器：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m unittest discover -s tests -p 'test_a01_*.py' -v
python -m unittest discover -s tests -p 'test_contracts*.py'
python examples/a01/consume.py examples/a01/bundles/46006966/exchange.json --book-id 46006966
python examples/a01/consume.py examples/a01/bundles/46007447/exchange.json --book-id 46007447
```

需要重新导入或重建证据时，输出必须是**不存在的新目录**：

```powershell
python examples/a01/build.py '<新的任务独立目录>/a01 bundles'
python examples/a01/verify.py '<新的任务独立目录>/a01 evidence'
```

搬运复现：完整复制单本 `examples/a01/bundles/<book_id>/` 到含空格目录；从另一 cwd 使用 `consume.py` 的绝对路径、原 PYTHONPATH 和该目录的 exchange.json 运行。脚本内部实际调用公共 `load_bundle(verify_assets=True)`，然后完整解码并交叉核对来源。现有产物和原资料目录均拒绝作为新导入目标。

## 实际执行结果

最终自测证据以 [final/verification.json](../evidence/A01/execution/final/verification.json) 为准；execution 根的首次记录保留作过程证据。23项 A01 测试：**22通过、1跳过，0失败、0错误**。其中几何8项含12行独立手算表及多组失败反例；来源15项。C01回归70项全部通过。测试数不表示业务覆盖率。

| 执行条款 | 自测结果与证据 |
|---|---|
| 公共类型及 load/validate/seal/write API | 通过；沿用唯一 C01 类型，无另一套合同；两包公共消费者实际成功 |
| 完整解码、摘要、尺寸、缺图及映射冲突 | 通过；损坏 JPEG 使用正确重算摘要仍被拒绝；错误尺寸/摘要、缺图、两书串用及冲突映射均拒绝 |
| expected/acquired/元数据/缺页分开 | 通过；显式六页/两页范围，范围内缺页0，范围外244/212未取得索引单列 |
| 历史及原件保留 | 通过；导入前后摘要相同，字节拷贝一致，越界不裁剪，历史数据不升级真值 |
| 输出可搬运 | 通过；两书完整复制至含空格路径，换 cwd 运行公共/A01消费者，退出码均0；[搬运证据](../evidence/A01/execution/final/relocation.json) |
| Git存储后仍保持原字节 | 通过；29个包文件均设置任务目录内 `-text`；暂存区42个包/证据文件摘要匹配；两书从Git暂存字节重建并换cwd消费成功，见 [字节核对](../evidence/A01/execution/repository-bytes.json)、[Git字节重建](../evidence/A01/execution/repository-roundtrip.json) |
| 路径逃逸/外部链接 | 相对路径逃逸及Windows目录联接逃逸明确拒绝。文件符号链接分支因 WinError1314 无创建权限跳过；不宣称已执行该分支，也未改权限或全局设置 |
| 重复导入/新修订 | 通过；已有目标一律拒绝且旧产物摘要不变；显式前版和revision2产生新根，前版引用/摘要保存在provenance；C01根 input_refs 仍为空 |
| scope_manifest及覆盖限制 | 限制已如实交付；两包只有14条历史导出参考/1条A05归档参考，不是独立分母，coverage_eligible始终false，无覆盖PASS；公共合同空分母失败保留于 [反例](../evidence/A01/execution/final/negative-cases.json) |
| 几何点/框正反 | 通过；非方图、非零裁片、独立x/y尺度、非对称补边、90/180/270°及组合。预期是字面手算值，逆向直接消费手算处理坐标，非仅正逆相消；[手算表](../../tests/fixtures/a01/geometry-hand-calculated.json) |
| 方向/原点/中心/顺序反例 | 通过；原图100×60，90°点(20,10)→(50,20)，边界(0,0)→(60,0)，像素中心(0.5,0.5)→(59.5,0.5)；crop后scale点(12,8)→(4,9)，区别于错误顺序(14,19) |
| 不合法/未支持几何 | 通过；NaN/Inf、零/负尺度、不可逆矩阵、负/零面积、越界、错asset/尺寸/摘要、任意角度/反射/透视/未知矩阵输入及模糊CropTransform均拒绝。非整数输出尺寸即使差值小于1e-9也拒绝，未隐式取整 |
| 改动范围/差异 | 所有Git及实现操作显式在指定工作树；暂存差异 `git diff --cached --check` 通过。历史原件CRLF用专属属性保留，不修改原始内容 |

原输入实际摘要见 [final/input-integrity.json](../evidence/A01/execution/final/input-integrity.json)，逐测试名称与跳过理由见最终验证记录。合法样例是两个固定包；非法输入是测试中的固定输入变更与反例JSON，均可在对应基线上复现。

## 公共 API、提案和未验证项

实现入口及语义详见 [A01说明](../a01-source-geometry.md)。`Transform` 直接重用 C01 ImageBinding/OriginalBox，正向/逆向处理点和四角框；不产生处理图，实际处理图摘要由调用者提供。支持恒等、原图裁片、正x/y缩放、四边整数补边、90°整数倍顺时针旋转及其组合；不涉及CSS/DPR、任意角度或透视/非线性。

1. **G01（待主调度/跨侧确认）**：`a01-geometry-1` 固定 crop→scale→pad→clockwise rotation；C01模糊CropTransform不自动解释。A04正式消费须等待独立验收和主调度释放确切版本，不能把此执行报告当接受信号。
2. **S01（公共合同最小提案，未实施）**：增加结构化 `scope_manifest_status=UNKNOWN|REFERENCE_ONLY|INDEPENDENT_COMPLETE`、UNKNOWN允许空清单及missing_sources；PRE_APPLY PASS需INDEPENDENT_COMPLETE。当前文本限制和A01消费者可以说明未知，C01下游缺少机器门禁，因此两包不能直接用于自动放行。没有编造题或修改合同解锁。
3. **D01（集成者处理）**：源模块需要已安装Pillow；本次未改根依赖或父入口。主调度可在指定共享提交中声明/锁定该依赖。现有根项目只声明Pydantic，不能据本机测试宣称全新环境安装完整。

未执行真实平台、浏览器、OCR、识别/配答、全书采集或业务正确性验证；未验收B、未取得B确认、未提交送审/送交。A05旧资料仅引用为历史参考。本任务独立验收和集成均待主调度安排。

模型/OCR/网络/浏览器调用：**0**；模型费用：**0**。识别成本、准确率及生产费用未测，不用本任务零调用推断生产成本。

后续仅需在本冻结交付上独立复验，给出ACCEPTED/REWORK/BLOCKED，再由主调度决定是否集成。本执行者状态保持REVIEW。
