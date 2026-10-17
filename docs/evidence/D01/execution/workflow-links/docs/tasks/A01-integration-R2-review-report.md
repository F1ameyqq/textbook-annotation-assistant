# A01 integration-R2 组合入口独立复验报告

日期：2026-10-17（Asia/Shanghai）。结论：**ACCEPTED**，仅接受本报告绑定的新固定两父组合的离线常规入口。原 **I1-GIT-01 在本组合中闭合**：默认 checkout 有 Git、raw 无 `.git` 且真实无 Git 程序时，完整入口均实际退出 0；raw 原失败单例实际运行 1 项、无 skip、退出 0。

原 integration-R1 的 REWORK、旧失败日志及原 I04 非阻断标签限制均保留。本结论不是 A01 在实际主分支的集成，也不释放 A04/D01；下一步由主调度复现必要检查并决定真实集成。

## 固定身份与输入

| 身份 | 确切值 |
|---|---|
| 正式工作流 | `fe91c27939d13f9be290f8274a0d46d90f4de2f0` |
| 新集成主父 M | `2d1dc8b97713ee06ec5bf35febe0b894ece584b2` |
| 另一父：冻结 A01 最终交付 | `5f872150a237b195f73c78e02e13a91d2f4f46a7` |
| A01 测试补丁 / 原 R3 发行 | `f8f2981a815f96147144d3747d26752b564cc9f7` / `180bb1e86fb2a7eb1546be85af70f466f069daf5` |
| 独立生成组合树 | `0645ac862f79fb4e232e4cfbd5f6bb5055a68d62`，与主调度预检一致 |
| 本次临时 commit | `169bee8759fb5727f305cb63627a27fdd569d4ca`，父顺序严格为 M、A01 最终交付 |
| M 已包含的 A02 接受交付 / 补丁 | `a1e5be00909172429d792b6c41bdaf384258694e` / `ad71284f3b6ffc8454ee1d1e30933c8e39d7c1d8` |

首先从上述工作流 Git 对象读取[交接原字节](../evidence/A01/review-integration-R2/frozen-handoff.md)，SHA256 为 `a6fe504b8d5bc218505b6102f1b670d1bfe4c3f3ce0af2d13ebf3dd26949ece0`。按其链接读取 A02 独立接受、主调度复现、真实本地集成检查及组合树前检；必要原件和各自 Git OID/SHA 保存在 [static/input-index.json](../evidence/A01/review-integration-R2/static/input-index.json)。未将前检或作者计数当成本轮功能接受。

A01 原执行报告 SHA256 `2789a99a1feb47d924486f28c4d6e83b9f521567897523453ab38ab283053eb0`，执行清单 SHA256 `6616779738c3170c6e600aa0fe80993cba2d3467695df4707a585c071192a6e7` 均从冻结交付核对。旧 R1 报告/清单固定摘要仍分别为 `2aaed84505799509319cab8e99a94eba818b69fd301caf4d3be89fe48c6a3caf`、`a331ad8a039408f2225f9e9842cc0a4d0860af7a0ece67f3fafa527f0c6600ad`。

## 独立组合、来源与文件表示

本轮新建脚本，仅写新 `review-integration-R2/` 和授权隔离目录；没有原地重跑或覆盖写死旧父的 R1 bootstrap/run_forms。继续采用已读的冻结离线独立复验技能核对确切 Git 字节、固定输入及接受层级。

[bootstrap.json](../evidence/A01/review-integration-R2/bootstrap.json) 与 [实际命令](../evidence/A01/review-integration-R2/bootstrap-commands.json) 保存本地 clone、`merge-tree --write-tree M A01`、`commit-tree` 两父顺序和 detached checkout。组合仅存在于 `.local/stages/A01-review-integration-R2/` 的独立对象库；没有更新主目录分支、索引或集成状态。

运行前主目录 live HEAD 是 `ca70961cadd025ab62944b745bb4d1317312b1c7`，单独记在索引中，**未用它或工作流 HEAD 替换固定 M**。Git 对象从主目录仓库只读取得，没有在原执行工作树中运行测试或生成器。

同一组合树以 `ls-tree` / `cat-file --batch` 原字节导出并重算 Git blob OID；没有用 Git archive、文本管道或归一化字节冒充原件：

| 运行副本 | 文件数 | 执行前表示 |
|---|---:|---|
| 默认 Git checkout | 11,894 | 11,823 原 Git 字节；71 个精确 LF→CRLF |
| raw 无 `.git` 副本 | 11,894 | 全部严格等于 Git blob |

逐文件 Git/磁盘摘要、长度、OID 和表示分别见 [checkout 索引](../evidence/A01/review-integration-R2/checkout-input-index.json) 与 [raw 索引](../evidence/A01/review-integration-R2/raw-input-index.json)。两副本运行前后字节均保持不变，不把默认 checkout 的表示记录当作扩大历史允许候选。

环境为 Windows、CPython 3.9.13、Pydantic 2.12.5、既有 Pillow 11.3.0；没有安装或全局设置修改。checkout 的 Git 为 2.53.0.windows.1；raw 子进程 PATH 为 `C:\Windows\System32;C:\Windows`，Python 使用确切绝对路径。TMP/TEMP/TMPDIR 均在普通独占临时目录，消费另换 cwd。

## 范围、旧参照及 A02 来源

[静态子审计](../evidence/A01/review-integration-R2/static/review.md) 最终实际退出 0，1,266 条检查全部通过，36 条只读 Git 命令均退出 0。组合树相对 M 的 464 条差异严格等于冻结 A01 差异；其余 11,430 份 M 文件的模式、类型和 OID 保留。根合同、属性、依赖、调度文档/状态及其他历史材料没有被意外覆盖。

相关 A01 实现、入口、测试、固定样例与夹具在本组合、冻结 A01 最终交付及旧 R1 组合树 `2078731114ad3a07368ca46a2f34c3544af64e2b` 中对应 OID 不变。原 971 项 / 25 个明确 CRLF 候选、62 项代码参照 / 3 个明确候选重新逐项绑定原提交、blob OID、SHA256/长度和有限表示；四份编码原件逐份等于原 Git blob，条目全等原固定清单，未从当前磁盘重建期望，未将旧发行保全政策套用到整个新 root。

组合采用的 A02 identity OID 为 `db0ca76a6a504ebd16e1b6731d104577c36bf0b0`，Git 原件 SHA256 为 `02b51187b4b4f711f0df8ea501201cafe99c078c84351a376a66ae2f892af58e`，与已接受最终交付及补丁相同；没有选用旧失败版本。相关新测试/探针同样来自接受版本，`source_binding` 函数源码不变。详见 [A02 身份](../evidence/A01/review-integration-R2/static/A02-identity.json)。

[188 项表示重核](../evidence/A01/review-integration-R2/static/A02-188-file-representation-audit.json) 独立将历史 index tree、188 条 OID/摘要/长度与冻结 A02/M 核对：原记录为 188/188 暂存区匹配 Git，183/188 磁盘匹配原字节，另外五个 Python 文件严格等于完整 LF→CRLF：identity、portability-R2 的 probe/run_tests/verify，以及 `test_a02_portability_r2.py`。完整双 SHA 和长度在该 JSON 中。此为对历史回执字节关系的重核，不冒称再次观察当时物理暂存区/磁盘；本轮默认 checkout 的实际逐项表示由自己的索引提供。

原 A01 新夹具的清单表示区别继续保留，不能写成清单与 Git 全等：

| `tests/fixtures/a01/integration-R1/reference.json` | 长度 | SHA256 |
|---|---:|---|
| Git LF 原件 | 86,374 | `51e2fd08803cfc918f62a23327da99993bf2a91363ef2ec3960f37765ee241db` |
| 作者清单绑定的精确 64 个 LF→CRLF | 86,438 | `9b979d4b18ffe4db50ad5473c218ba28fdcbed0515d68ce324894be09cc2d0eb` |

独立重算的双摘要/JSON 内容关系与原交接一致。原 **49/50 Git 匹配、50/50 作者磁盘回执匹配**是不同层级的事实，未修改原清单或将新夹具加入旧 25 候选。见 [A01 双表示核对](../evidence/A01/review-integration-R2/static/A01-author-manifest-representation.json)。

## 双形态完整入口的实际执行

每形态完整运行一次未修改的 `examples/a01/integration-R1/verify.py`，均非 `--focused`。为采集真实子进程导入，使用新建外部 `trace_entry.py` / `trace_child.py`：保存原 argv 与实际包装 argv，重建原 sys.argv/sys.path 后用 runpy 执行；不修改源码、测试断言、skip 或返回码。不能将此表述为完全未经观察器的裸入口回执。

[采集器实际回执](../evidence/A01/review-integration-R2/collector-runtime/command.json) 为退出 **0**；启动时原始 stdout/stderr 字节保存在同目录 `stdout.log` / `stderr.log`。每形态的外层命令、cwd、选定环境、原始 stdout/stderr 和完整 11 子命令结果也各自保留。

| 必需检查 | 默认 checkout，有 Git | raw，无 `.git` 且真实无 Git 程序 |
|---|---|---|
| 完整入口 | 实际退出 **0**，11/11 子命令均 0 | 实际退出 **0**，11/11 子命令均 0 |
| A01 | 52 项：51 通过、1 WinError 1314 权限跳过 | 相同 |
| C01 | 70 项通过，无 skip | 相同 |
| A02 | **62 项通过，零 skip** | 相同 |
| 离线登录 | 8 项通过，无 skip | 相同 |
| 固定 R3 URL | 5 例符合预期，退出 0 | 相同 |
| legacy/R3 两书直接及 R3 搬运消费 | 6 次均退出 0 | 相同 |

完整结果见 [运行汇总](../evidence/A01/review-integration-R2/runtime-summary.json)、[checkout 入口结果](../evidence/A01/review-integration-R2/runtime/checkout/entry/results.json)、[raw 入口结果](../evidence/A01/review-integration-R2/runtime/raw/entry/results.json)。两形态为同套条件对照，不相加为独立成绩。文件 symlink 仍因 WinError 1314 未验证，目录 junction 的实际通过不替代它。

消费均完成公共资源校验与完整图像解码；搬运目录含空格，cwd 与源码/包目录不同，引用保持可独立消费。旧书 6 个资源、元数据 250；新书 2 个资源、元数据 214；`coverage_eligible=false` 等既有有限来源边界保留，不扩大为全页/全书覆盖证明。

raw 的 **全部 11 个实际子进程**在测试前分别记录 `shutil.which('git')=null`，并真实请求 OS 启动 `git --version`，得到 `FileNotFoundError` / WinError 2。不是仅设置环境变量或 mock subprocess；该预期 OS 启动失败被观察器记录，不冒称存在 Git 子进程退出码。每条实际 PATH/cwd 和启动结果保存在 `runtime/raw/imports/01.json` 至 `11.json`。

## 原 I1-GIT-01 裸单例与实际导入

raw 的 tests 目录另直接执行以下原命令，**未使用观察器包装**，环境与 raw 完整入口同为真实无 Git PATH、PYTHONPATH 指向该副本 src：

```powershell
& 'C:\Users\ASUS\AppData\Local\Programs\Python\Python39\python.exe' -B -m unittest test_a02_r1.A02R1Tests.test_export_subdirectory_cannot_borrow_enclosing_git_head -v
```

cwd 为 `D:\1800\.local\stages\A01-review-integration-R2\raw no Git\tests`。实际 **退出 0，Ran 1 test，OK，无 skip**。见 [裸命令回执](../evidence/A01/review-integration-R2/bare-case/test/command.json)、[原始 stderr](../evidence/A01/review-integration-R2/bare-case/test/stderr.txt) 与 [汇总](../evidence/A01/review-integration-R2/bare-case/summary.json)。同环境额外独立 OS 探针记录 null、无 `.git`、真实 FileNotFoundError / WinError 2，见 [探针原始输出](../evidence/A01/review-integration-R2/bare-case/environment-probe/stdout.txt)。探针采集命令按预期退出 0，不把 Git 的未成功启动改写为成功。

[checkout 实际导入](../evidence/A01/review-integration-R2/runtime/checkout/actual-imports.json) 和 [raw 实际导入](../evidence/A01/review-integration-R2/runtime/raw/actual-imports.json) 各保存 **196 条观察**，包括执行模块 frame 的真实 `__file__` 和退出时 sys.modules 全部 annotation 模块。实际执行覆盖 A01 全部六个测试文件、C01 两个测试文件、importer/consistency/geometry/contracts，以及新 A02 identity、`test_a02_r1`、`test_a02_portability_r2`，逐项绑定执行前对应 Git/磁盘索引，没有用作者 `source_files` 字段代替真实导入证据。

每形态另记录 10 份新 A02 测试创建的 identity 临时副本，按执行时实际摘要等于该形态冻结 identity；这些路径单列 GENERATED_IDENTITY_COPY，未冒称它们在固定 snapshot 内。其余记录的 annotation 模块全部来自对应固定副本。边界子审计独立关联各形态全部 11 条原参数/包装参数、cwd、OS 探针、实际导入及预执行索引，见 [边界报告](../evidence/A01/review-integration-R2/boundary/review.md)。

## 历史引用、未重跑项目与限制

在相应代码、入口、固定输入和政策 OID 全部核对不变后，引用原 R1 的 I01/I02/I03/I05、F00–F04、原发行 R00–R02及错误传播负例。这些原始非零和成功回执保持原样，旧 R1 清单覆盖的 226 项完整摘要闭包本轮重新核对，见 [收口完整性](../evidence/A01/review-integration-R2/closeout-integrity.json)。不把这些历史回执冒称本轮重新运行。

原 R3 verify 仍只适用其冻结发行；没有在新组合树运行旧发行严格门禁并声称相同身份。没有重跑无改动的 630 项几何矩阵。A02 刚接受的绑定拒绝、第二次真实 Git 启动失败等完整故障复验引用其确切接受报告和调度复现，本轮只在必需的 62 项常规 discovery 内运行既有测试，不重复独立故障全集。

原 I04 标签限制保持：新固定夹具顶层 `reference_commit` 本身未被常规测试二次认证，原初期待拒绝而实际退出 0 的探针不改写。四条真正的内容、OID、摘要、长度、表示和 source_manifest_sha256 绑定依旧；本轮不把该冗余标签扩大为修复任务或宣称已经认证。

本轮静态审计器初稿曾因将 `disk_equal` 与 `exact_lf_to_crlf` 两个历史标志误当互斥而退出 1：七份空 stderr 同时满足两条字节等式。初稿、实际退出、检查与原记录完整保存在 `static/first-attempt/`；修正为真实字节谓词后仅重新检查静态元数据，未改变原回执/候选或重放功能。见 [更正记录](../evidence/A01/review-integration-R2/static/collector-correction.json)。没有因该包装问题覆盖历史失败。

## 验收对应与最终归档

| 交接要求 | 独立结论 |
|---|---|
| 固定 M + A01 最终交付重新构造，组合树和父顺序 | 通过；临时树与预检一致，未采用 live/workflow HEAD |
| 默认 checkout / raw 真无 Git 各一次完整入口 | 通过；各 11 子命令实际均 0 |
| A01/C01/A02 62/登录/URL/消费数量与 skip | 通过；A01 单一权限 skip 如实保留 |
| 原 I1-GIT-01 裸单例 | 通过；真实执行 1 项、0 skip、退出 0 |
| 新实际导入及执行前字节绑定 | 通过；全部必需模块/测试覆盖，临时 identity 副本另列 |
| 旧 971/25、62/3、四份编码与历史负例引用条件 | 通过；无新增容差或期望重建 |
| 历史失败、双表示及 I04 限制 | 保留；未改写原结论或旧材料 |

本次只新增本报告及 `docs/evidence/A01/review-integration-R2/`，临时对象/副本位于授权 `.local` 与独占普通 temp。执行前主目录既有跟踪文件和 A01/A02 旧证据（含忽略日志）建立摘要索引，收口逐项复核；若 live 主目录有其他已提交并发变化，单独与其当前 Git blob 核对，不将其混入固定受验树或误称本次写入。完整分组及当前状态见 closeout-integrity.json。

新统一 [SHA256 清单](../evidence/A01/review-integration-R2/sha256-manifest.json)覆盖本报告、必要输入、独立脚本、原始 stdout/stderr、实际导入、静态初稿失败和所有实际 Git 忽略日志；只排除清单自身并单列忽略项。报告及清单最终摘要随交付给出。文档链接/差异和证据闭包另行核对，不再运行功能入口。

全部自有同步执行会话已返回，两名子审计者声明零待释放会话；另以 [任务路径进程核对](../evidence/A01/review-integration-R2/process-check.json)给出 Python/Git/cmd/浏览器相关自有路径匹配 0 的实际 OS 依据，不宣称普查了其他所有进程，不输出其他命令行。

网络、平台、浏览器、凭据/profile、OCR和外部模型调用及费用均为 0。未代修实现/公共合同/依赖/协调状态，未提交、集成、推送、联系执行者或 B，未释放 A04/D01。S01、N15、D01、B 确认、真实平台、全书质量/成本等既有边界均不由本轮解决。**ACCEPTED 仅绑定本报告固定 M、A01 交付和组合树，交回主调度。**
