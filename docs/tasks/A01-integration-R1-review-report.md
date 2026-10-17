# A01 集成修订 R1 独立复验报告

日期：2026-10-17（Asia/Shanghai）。结论：**REWORK**。本次只验固定交付的有界离线集成测试修订；原 R3 有界接受及首次集成失败均保留。

唯一阻断为 **I1-GIT-01：新完整常规入口仍依赖 Git 可执行程序**。默认 checkout 全入口通过；无 `.git` 的原字节副本在 PATH 有 Git 时也通过，但 PATH 无 Git 时 A02 既有测试抛出 `FileNotFoundError`，新完整入口实际退出 1。执行报告所称“该入口无 Git 依赖”及本轮交接必需第 5 项尚未满足。这是已完成复验发现的失败，非缺环境导致的 BLOCKED；没有修改实现或放宽验收条件。

## 固定版本、规则与环境

| 身份 | 确切值 |
|---|---|
| 唯一最终交付 | `5f872150a237b195f73c78e02e13a91d2f4f46a7` |
| 受验补丁父 | `f8f2981a815f96147144d3747d26752b564cc9f7` |
| 固定临时集成主父 | `4946b8ab307f88bdc25c14ace5ead774e3119fc5` |
| 原 A01/R3 冻结发行 | `180bb1e86fb2a7eb1546be85af70f466f069daf5` |
| 独立生成的集成树 | `2078731114ad3a07368ca46a2f34c3544af64e2b`，与作者合并树一致 |
| 本次临时对象 | `485e0cfd36e1e070b2a083250d1423f0c5b84e52`，父顺序为上述主父、补丁父 |
| 执行报告 SHA256 | `2789a99a1feb47d924486f28c4d6e83b9f521567897523453ab38ab283053eb0` |
| 作者统一清单 SHA256 | `6616779738c3170c6e600aa0fe80993cba2d3467695df4707a585c071192a6e7` |

依据：[复验交接](A01-integration-R1-review-handoff.md)、[有界修订任务](A01-integration-rework-R1.md)、[原独立标准](A01-independent-review.md)、[原 R3 报告](A01-review-R3-report.md)。使用冻结离线独立复验技能进行隔离、精确字节和反例核对，未将作者测试数或主调度前检当成独立通过。

环境为 Windows、CPython 3.9.13、Pydantic 2.12.5、既有 Pillow 11.3.0；无安装、全局设置修改。Git 2.53.0.windows.1 仅用于离线准备和明确的有 Git 对照。无 Git 执行环境 PATH 固定为 `C:\Windows\System32;C:\Windows`，`shutil.which('git')` 为 null，Python 使用确切绝对路径。

## 独立隔离与字节来源

[bootstrap.json](../evidence/A01/review-integration-R1/bootstrap.json) 与 [bootstrap-commands.json](../evidence/A01/review-integration-R1/bootstrap-commands.json) 保存实际命令、退出码、父版本和环境。只在 `.local/stages/A01-review-integration-R1/` 的新本地对象仓库生成临时合并树；未更新主目录分支或主目录索引。临时 commit 的时间/消息不同于作者，树和两父身份严格一致。

用 `git ls-tree` 和 `git cat-file --batch` 读取原件，并重算 Git blob OID。没有使用 Git archive、文本管道或归一化字节冒充原件。独立建立：

| 副本 | 文件数 | 执行前表示 |
|---|---:|---|
| 正常 Git checkout | 9,937 | 9,870 原 Git 字节、67 精确 LF→CRLF |
| 同集成树无 `.git` 原字节副本 | 9,937 | 全部等于 Git blob |
| 原 `180bb1e` 冻结发行 | 1,144 | 全部等于 Git blob |
| 唯一最终交付 | 1,194 | 全部等于 Git blob |

对应 [checkout](../evidence/A01/review-integration-R1/checkout-input-index.json)、[raw](../evidence/A01/review-integration-R1/raw-input-index.json)、[frozen](../evidence/A01/review-integration-R1/frozen-input-index.json)、[delivery](../evidence/A01/review-integration-R1/delivery-input-index.json) 索引保留 OID、摘要、长度和表示。受验测试、固定输入及入口在最终交付和补丁中相同。所有负例只改另建的专用副本；原始输入及四个根副本保持不变。

## 范围、固定参照与历史证据

[静态子审计](../evidence/A01/review-integration-R1/static/review.md) 实际退出 0，1,073 条检查通过；12 条底层只读 Git 命令均为 0。51 项净改动全部在白名单，唯一既有文件修改为 `tests/test_a01_rework_r3.py`。其余 1,143 份旧文件及全部 11 份生产代码未变；根属性/依赖、合同、geometry、调度、原 R3 verify/reference、旧报告与失败证据均未改。补丁到最终交付的 36 项仅为新报告/证据。

原 971 项清单和 25 个明确候选逐项重新绑定原提交、路径、Git OID、SHA256/长度及有限 CRLF 候选；62 项代码参照与 3 个明确候选也逐项核对。新测试仍固定旧清单 SHA256、原提交、971 条唯一性、25 候选和历史资源单表示政策。四份 base64 编码原件逐份等于 `c3aff9598b6705ab4122062615a13ae3774698b2` 原 Git blob，去除编码字段后整个条目严格等于原 971 清单对应项；不是从当前磁盘重建期望。

作者新统一清单对 Git 原字节实际为 **49/50**，不能写成全等。唯一新夹具 `tests/fixtures/a01/integration-R1/reference.json` 独立绑定如下：

| 表示 | 长度 | SHA256 |
|---|---:|---|
| Git LF 原件 | 86,374 | `51e2fd08803cfc918f62a23327da99993bf2a91363ef2ec3960f37765ee241db` |
| 作者清单绑定的精确 64 个 LF→CRLF | 86,438 | `9b979d4b18ffe4db50ad5473c218ba28fdcbed0515d68ce324894be09cc2d0eb` |

两者解析 JSON 相同，第二摘要由本次原 Git 字节独立推导并与交接/清单核对；没有把它冒称为本次再次观察的作者磁盘。该绑定未加入旧 971 允许项。详见 [双表示诊断](../evidence/A01/review-integration-R1/static/author-manifest-representation.json)。

首次集成失败、原 20 项差异诊断、作者首次重现退出 1、编码损坏子入口退出 1、包装自身错误及补证源码均保留。四份旧派单/失败回执与其接单时固定摘要一致，见 [历史保留核对](../evidence/A01/review-integration-R1/static/retained-failures.json)。

## 常规入口与真实导入

第一次双形态入口通过外部 `trace_entry.py` / `trace_child.py` 观察，未改任何受验源文件。观察器保留原 argv 与实际包装 argv、cwd，并在测试子进程记录真实执行模块 frame 的 `__file__` 及退出时 `sys.modules`。因此这是带观察器的实际执行，不能表述成未包装裸命令。

[checkout 实际导入](../evidence/A01/review-integration-R1/runtime/checkout/actual-imports.json) 和 [raw 实际导入](../evidence/A01/review-integration-R1/runtime/raw/actual-imports.json) 各有 185 条观察，关联各自全部 11 个子命令。importer、consistency、geometry、contracts.models 以及修改/新增测试实际来自对应隔离副本，摘要与执行前固定索引一致；记录的 annotation 模块无副本外导入。[边界复核](../evidence/A01/review-integration-R1/boundary/result.json) 又独立核对这一关联。没有把作者 `source_files` 当作导入证明。

| 检查 | 正常 checkout，有 Git | 原字节，无 Git 程序 |
|---|---|---|
| 新完整入口实际退出码 | **0** | **1** |
| A01 52 项 | 51 通过、1 权限跳过，退出 0 | 相同，退出 0 |
| C01 70 项 | 全通过，退出 0 | 全通过，退出 0 |
| A02 52 项 | 全通过，退出 0 | 51 通过、1 ERROR，退出 1 |
| 离线登录 8 项 | 全通过，退出 0 | 全通过，退出 0 |
| 固定 R3 URL 5 例 | 符合预期，退出 0 | 符合预期，退出 0 |
| legacy/R3 两书直接及 R3 搬运消费 6 次 | 全部退出 0 | 全部退出 0 |

每次消费均进行公共资源验证和完整图像解码，保留 `coverage_eligible=false`；旧书 6 个资源/元数据 250、新书 2 个资源/元数据 214未混用。搬运目录含空格、cwd 不同。A01 文件 symlink 跳过仍是 WinError 1314，目录 junction 测试实际通过，但不能替代文件 symlink 证明。两形态不相加为独立成绩，未重跑无改动的 630 项几何矩阵。

完整 argv、cwd、环境、原始 stdout/stderr 和每条子命令退出码见 [执行汇总](../evidence/A01/review-integration-R1/runtime-observed-summary.json) 及各形态 `command.json`、`entry/results.json`、`imports/launches.json`。原字节无 Git 全入口保留了非零；入口没有吞错，后续其他检查仍实际运行。

## 必须修复项 I1-GIT-01

触发条件为无 `.git` 原字节副本且系统 PATH 不含 Git 程序。调用链是：新 `integration-R1/verify.py` 无条件运行 A02 discovery → `test_a02_r1.A02R1Tests.test_export_subdirectory_cannot_borrow_enclosing_git_head` → `examples/a02/R1/identity.py:9` 启动 `git rev-parse --show-toplevel` → 未捕获 `FileNotFoundError: [WinError 2]`。

最小无观察器复现（使用上述固定 raw 集成副本；下列修改只作用于该 PowerShell 会话）：

```powershell
$env:PATH = 'C:\Windows\System32;C:\Windows'
$env:PYTHONPATH = 'D:\1800\.local\stages\A01-review-integration-R1\raw integrated no Git\src'
Set-Location 'D:\1800\.local\stages\A01-review-integration-R1\raw integrated no Git\tests'
& 'C:\Users\ASUS\AppData\Local\Programs\Python\Python39\python.exe' -B -m unittest test_a02_r1.A02R1Tests.test_export_subdirectory_cannot_borrow_enclosing_git_head -v
```

实际退出 **1**，1 项 ERROR，见 [最小命令回执](../evidence/A01/review-integration-R1/git-availability/minimal-without-git/command.json) 及 [原始错误](../evidence/A01/review-integration-R1/git-availability/minimal-without-git/stderr.txt)。同一字节、同一用例、同一无 `.git` 副本，仅恢复包含 Git 的 PATH 后实际退出 **0**。另在有 Git PATH 下未经观察器直接重跑该 raw 副本完整常规入口，11 条子命令全为 0，见 [完整有 Git 对照](../evidence/A01/review-integration-R1/git-availability/raw-full-with-git/command.json) 与 [全部对照](../evidence/A01/review-integration-R1/git-availability/summary.json)。观察器并非失败原因。

因此当前证据只支持“无仓库元数据，但运行环境有 Git 的完整入口”。失败代码来自固定主父的既有 A02，未在本轮补丁修改；新组合入口把它纳入了运行依赖，故不能依据来源归属忽略入口失败。本报告不要求执行者越界修改 A02，也不提供跳过或吞错补丁。主调度需明确解决该无 Git 环境依赖，或正式修订并说明入口适用条件；当前指定要求下不接受，不集成、不释放 A04。

## 独立损坏对照与原冻结门禁

[负例汇总](../evidence/A01/review-integration-R1/negative/summary.json)、[负例说明](../evidence/A01/review-integration-R1/negative/notes.md) 保存每例前后字节、摘要、命令、cwd、退出码和原始子入口输出。仅物化 508 项必要集成输入及单独 1,144 项原发行副本；原件未被修改。负例是代码/夹具保全检查，不伪称为经过 `load_bundle` 的来源语义反例。

| 独立对照 | 实际结果 |
|---|---|
| I00：原件新入口 `--focused` | 外层及 A01 均 0；只算聚焦对照 |
| I01：生产 `url_index` 功能真实 +1 | 外层及 A01 均 1；实际 import 指向变异副本且固定 URL 13 返回 14 |
| I02：编码内容单字节破坏、期望 SHA 不变 | 外层及 A01 均 1，`fixed Git original digest mismatch` |
| I03：固定条目的 Git blob OID 单独破坏 | 外层及 A01 均 1，旧清单条目全等断言失败 |
| I05：`source_manifest_sha256` 单独破坏 | 外层及 A01 均 1，原参照绑定断言失败 |
| F00/F01：原件和原列明的均匀 CRLF | 均接受 |
| F02/F03/F04：混合换行、未允许的历史 CRLF、PGM 破坏 | 均被 `CONTENT_MISMATCH` 拒绝 |
| R00：原 `180bb1e` 未改 R3 verify `--preservation-only` | 实际 0，971 项原字节保全通过，功能子命令 0 条 |
| R01/R02：同原发行的源码/JPG 真实破坏 | 各实际 1，分别由 implementation/preservation `CONTENT_MISMATCH` 定位拒绝 |

没有声称原 R3 verify 接受改过测试的新集成树；原发行此次只重跑保全入口，不冒称全功能复验。该入口完整冻结验证先前 R3 接受历史仍保留。

另有独立探针 **I04**：只将新夹具顶层 `reference_commit` 改为 40 个 0，原初期待拒绝，实际聚焦入口及 A01 均 **0**。此失败期望和成功返回原样保留，未改写成通过。该标签经 helper 返回后只被回显；四条内容/OID/摘要/长度/有限表示仍逐条等于固定旧清单，`source_manifest_sha256` 也实际校验，所以单改标签不能让另一内容或另一 blob 通过。本报告将其记录为非阻断的冗余来源标签完整性遗漏，不宣称该标签已认证，也不把 helper 当作通用来源认证工具。详见 [独立证明](../evidence/A01/review-integration-R1/negative/root-reference-proof.json) 及 [边界分析](../evidence/A01/review-integration-R1/boundary/review.md)。

负例采集脚本顶层实际退出 0，但 I04 的原始 `expected_matched=false` 保留；顶层采集完成不代表每个原初期待都通过。其顶层 stdout 由工具回执观察，未另存启动时原始字节流，此限制见 collection-receipts.json；各被测子进程原 stdout/stderr 均已保存。

## 验收条目与收口

| 本轮交接必需项 | 独立结论 |
|---|---|
| 1：净范围、旧实现/清单/属性/候选保留 | 通过 |
| 2：新旧验证适用对象、4 份固定原件及原 971/25 政策 | 通过；I04 冗余标签限制另列 |
| 3：两形态常规入口、相关回归/URL/消费 | 有 Git 两形态通过；无 Git 程序完整入口失败，I1-GIT-01 |
| 4：小规模源码/编码/身份/换行/二进制损坏和原发行保全 | 实际门禁对照符合；I04 原初期待不符已披露 |
| 5：错误传播、历史失败、搬运/换 cwd/实际导入、无 Git | 错误传播和导入等已证实；无 Git 全入口失败，I1-GIT-01 |

本次仅新增本报告和 `docs/evidence/A01/review-integration-R1/`；临时副本位于授权 `.local` 与普通独占 temp。旧 A01 报告/证据（含忽略日志）2,032 份按执行前补充索引逐项复核，全部不变。主目录期间发生独立的已提交 A03 调度更新：共享 `docs/coordination.md`、`docs/coordination-state.json` 改变，另新增 A03 前检/交接；两份现有文件的差异已与当前 HEAD blob 精确核对，未冒称主目录全程字节不变。起始主目录 HEAD 由隔离 clone 保留的未修改分支取证为 `27109c9ad77de34f8c8434c1e20086a49ac62223`，收口观察为 `a699a52c5b52d9c20918831e3632314df0c76649`。受验两父和所有隔离输入未跟随该浮动 HEAD，见 [收口完整性](../evidence/A01/review-integration-R1/closeout-integrity.json)。其他任务并发产生的未跟踪资料也不属于本次写入；未触碰或清理。

本次 reviewer 的第一次 bootstrap 因 Python 3.9 不支持 `Path.write_text(newline=...)` 退出 1，发生于导出/功能执行之前；保留初稿与错误，改用 `open(newline=...)` 后实际退出 0。双形态采集包装因真实 raw 入口非零而自身退出 1，其全部输入/原始子输出和后续只读整理均保留，未覆盖失败。收口脚本第一次误将当前主目录 HEAD 与固定集成主父等同，断言退出 1；已保留原脚本/错误并改为对并发主目录提交单独核对，不重新执行功能测试。见 bootstrap-first-attempt.json、run_forms-launch.json、closeout-first-attempt.json、实际命令回执。静态子报告尚在生成时一次读取路径不存在的查阅错误未触发执行或改动，不作为功能结果。

统一 [SHA256 清单](../evidence/A01/review-integration-R1/sha256-manifest.json) 覆盖本报告、独立脚本、必要输入、原始输出、失败、日志及实际 Git 忽略项；只排除清单自身并单列忽略项。收口第二次的链接检查提前检查其尚未写出的自身结果，第三次又因创建已存在的最小输入索引退出 1；原脚本/部分结果/错误均保留。最终包装对既有结果只比较、不覆盖，并在创建后核对自身输出链接，未重跑功能。最终摘要随交付消息给出，未在报告内构造自身摘要循环。

全部自有工具会话已返回；[任务路径进程核对](../evidence/A01/review-integration-R1/process-check.json) 保存当前 Python/Git/浏览器相关任务路径匹配数为 0 的依据，未输出其他进程命令行。不把作者“零会话”声明冒充本次 OS 核对，也不宣称扫描了所有非目标进程。无待释放自有会话。

网络、平台、浏览器、凭据/profile、OCR、模型调用及费用为 0；未改状态、未提交/推送/集成、未释放 A04。D01、S01、N15、B 确认、文件 symlink 权限、平台/全书覆盖等原限制不变；630 几何矩阵本轮未重跑。**当前最终结论仍为 REWORK，主调度集成与 A04 释放条件未成立。**
