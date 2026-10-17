# A01 integration-R2 组合入口独立复验

2026-10-17。原A01交付保持冻结；本轮没有新的A01实现任务。A02身份工具修复已获独立接受、主调度复现和真实本地集成，现续派原验收对话 `01a144cb-69e8-7981-a8d5-8832eae61829`，只复验新固定组合能否关闭 I1-GIT-01。A01尚未集成，A04/D01尚不释放。

## 固定输入

| 身份 | 确切值 |
|---|---|
| 新主父 M，已集成A02修复 | `2d1dc8b97713ee06ec5bf35febe0b894ece584b2` |
| A01最终冻结交付 | `5f872150a237b195f73c78e02e13a91d2f4f46a7` |
| A01受验测试补丁 / 原R3基线 | `f8f2981a815f96147144d3747d26752b564cc9f7` / `180bb1e86fb2a7eb1546be85af70f466f069daf5` |
| 主调度两父merge-tree预检树 | `0645ac862f79fb4e232e4cfbd5f6bb5055a68d62` |
| A02修复最终交付 / 补丁 | `a1e5be00909172429d792b6c41bdaf384258694e` / `ad71284f3b6ffc8454ee1d1e30933c8e39d7c1d8` |

正式工作流是包含本文件的调度提交，消息给出确切SHA。M包含A02补丁但不包含随后新归档的集成检查文件；这些检查绑定M，读取工作流提交中的证据，不把工作流HEAD当作组合父。

A01执行报告 `docs/tasks/A01-integration-R1-execution-report.md` SHA256 `2789a99a1feb47d924486f28c4d6e83b9f521567897523453ab38ab283053eb0`；执行清单 `docs/evidence/A01/execution/integration-R1/archive-manifest.json` SHA256 `6616779738c3170c6e600aa0fe80993cba2d3467695df4707a585c071192a6e7`，均取最终交付对象。原工作树 `C:/Users/ASUS/.codex/worktrees/a01-source-geometry/1800` 只作Git对象来源，不在其中执行或修改。

[A02调度收口](A02-portability-R2-coordinator-acceptance.md)、[实际集成检查](../evidence/A02/coordinator/portability-R2-integration/checks.json)与[组合树前检](../evidence/A01/coordinator/integration-R2-handoff/preflight.json)构成本轮前置证据。原A01[集成R1报告](A01-integration-R1-review-report.md) SHA256 `2aaed84505799509319cab8e99a94eba818b69fd301caf4d3be89fe48c6a3caf`、[旧清单](../evidence/A01/review-integration-R1/sha256-manifest.json) SHA256 `a331ad8a039408f2225f9e9842cc0a4d0860af7a0ece67f3fafa527f0c6600ad`、原失败回执均保留。

## 有界复验

1. 用 M 和A01最终交付在独立本地对象库重新构造合并，记录两父顺序、tree OID及临时commit，确认等于预检树。该临时对象不代表主分支已集成A01。核对合并没有采用旧A02 identity，相关A01实现、入口、测试、原971/25政策与原冻结参照保持对应OID。根合同/属性/依赖及历史证据没有意外覆盖。
2. 从同一固定树建立默认checkout与原始Git blob副本。checkout有Git；raw无`.git`且在实际子进程无Git PATH，另记录 `which`及真实OS启动失败。各执行一次完整 `examples/a01/integration-R1/verify.py <新输出目录>/entry`，不能用 `--focused`代替完整入口。
3. 每形态核对11条实际子入口与退出码：A01 52项（原文件symlink权限跳过如实记录）、合同70、A02 **62**、登录8、URL五例、两书直接和搬运消费六次。重复形态不相加为独立成绩；不重跑无改动的630几何矩阵。失败顶层必须保留实际非零，不能只看包装器 `passed`。
4. raw副本的tests目录中另直接运行 `python -B -m unittest test_a02_r1.A02R1Tests.test_export_subdirectory_cannot_borrow_enclosing_git_head -v`，使用该副本src及真实无Git PATH，须退出0、实际运行1项、无skip。这是原I1-GIT-01的裸单例闭合证据。
5. 两形态重取实际导入路径与摘要，绑定执行前索引。包含全部annotation模块、A01/合同测试及新A02 identity、test_a02_r1、test_a02_portability_r2。可新建观察器参考原trace工具，保留原argv、包装argv、cwd与实际执行记录，明确包装方式；不覆盖或原样运行写死旧父的原bootstrap/run_forms。

原已通过的I01/I02/I03/I05、F00–F04、原发行R00–R02和错误传播负例可引用。前提是本轮核对对应生产代码、测试、入口、固定输入及政策OID未变；只要相关输入发生实质变化，就明确指出并做必要的最小复验。原971/25、62/3及四个编码输入重新核对固定摘要/OID，常规入口仍运行政策断言。不要将历史971保全政策套到整个新root。

A02刚接受的绑定拒绝、第二次真实spawn失败与其他独立负例可引用其[复验报告](A02-portability-R2-review-report.md)和本轮主调度复现，不在A01重复整套测试。原I04冗余 `reference_commit` 标签未认证仍是已披露非阻断限制，不把它扩大为新修复任务。

## 字节表示与接受边界

原A01新夹具 `tests/fixtures/a01/integration-R1/reference.json` 的Git LF为86,374字节、SHA256 `51e2fd08803cfc918f62a23327da99993bf2a91363ef2ec3960f37765ee241db`；作者清单精确64个LF→CRLF为86,438字节、SHA256 `9b979d4b18ffe4db50ad5473c218ba28fdcbed0515d68ce324894be09cc2d0eb`。保留原49/50 Git与50/50作者磁盘的区别，不修改旧清单或扩大原25候选。

A02此次实际默认checkout还有5个Python文件为完整LF→CRLF，183/188磁盘与Git相同，188/188暂存区与冻结Git相同；[逐文件双摘要](../evidence/A02/coordinator/portability-R2-integration/merge-index-check.json)列出准确范围。没有改全局设置、根属性或受验代码。独立复验自行记录两形态字节，不用CRLF例外掩盖别的内容变化。

仅新增 `D:/1800/docs/tasks/A01-integration-R2-review-report.md` 与 `D:/1800/docs/evidence/A01/review-integration-R2/`。隔离目录用 `.local/stages/A01-review-integration-R2/` 和独占普通临时目录。保留必要固定输入、脚本、实际argv/cwd/退出码/原输出、索引、失败与日志；统一清单包含忽略日志并单列自身排除。只复制必要证据，不复制全部历史归档。

结论 ACCEPTED / REWORK / BLOCKED 必须绑定上述M、A01交付及合并树；原REWORK不改写。无新实施代码授权，不修代码/合同/依赖/协调状态、不提交/合并/推送、不联系执行者或B。零网络、平台、浏览器、凭据/profile、OCR和模型。结束前核对自有进程/会话释放并注明声明或实际扫描的证据层级。

验收通过后仍由主调度复现必要检查并真实集成A01，才释放A04；D01、S01、N15、B确认、平台、全书质量/成本仍按原边界处理。
