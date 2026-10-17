# A01 integration-R2 边界与实际导入子复核

子审结论：**ACCEPTED，仅限固定组合入口和 I1-GIT-01 闭合**。本子审不代替根复验正式结论或主调度集成，不释放 A04/D01。

依据 workflow `fe91c27939d13f9be290f8274a0d46d90f4de2f0` 的完整交接，固定主父为 `2d1dc8b97713ee06ec5bf35febe0b894ece584b2`，A01 最终交付为 `5f872150a237b195f73c78e02e13a91d2f4f46a7`，组合树为 `0645ac862f79fb4e232e4cfbd5f6bb5055a68d62`。独立读取本地临时 commit `169bee8759fb5727f305cb63627a27fdd569d4ca`，确认父顺序及 tree 正确；临时对象不代表已集成 A01。

## 范围和既有保证

179 个 A01 来源/geometry/入口/测试/夹具路径与冻结交付逐项 OID 相同。新 A02 identity、test_a02_r1、test_a02_portability_r2 来自固定新主父；根属性和依赖也与主父对应。旧 971 条/25 个有限候选、62 条/3 个有限候选及四份编码原件重新核对固定摘要与 Git blob；四份编码实际字节/OID 与旧参照 `c3aff9598b6705ab4122062615a13ae3774698b2` 一致。没有把历史保全政策套到当前整个 root，也没有新增表示候选。

新夹具的 Git 原字节 86,374 bytes / SHA256 `51e2fd08803cfc918f62a23327da99993bf2a91363ef2ec3960f37765ee241db` 与作者原清单 CRLF 表示 86,438 bytes / SHA256 `9b979d4b18ffe4db50ad5473c218ba28fdcbed0515d68ce324894be09cc2d0eb` 的区别保留。原 I04 顶层 reference_commit 标签未认证仍是已披露的非阻断限制；内容和 entry 身份仍由固定旧清单摘要、entry 全等和编码 SHA 绑定。本轮不扩大修复范围，也未重跑已接受的 A02 故障全集或 630 项几何矩阵。

## 运行回执与原阻断闭合

独立读取根复验这次从新组合树取得的原始命令/结果，两个完整入口均实际 exit0、11 个子入口全部 exit0。每种形态 A01 实际运行52项（原文件 symlink 权限跳过1项）、C01 70项、A02 62项、离线登录8项；URL五例及两书直接/搬运消费六次通过。重复形态不相加。

raw 无 `.git`，实际 PATH 为 `C:/Windows/System32;C:/Windows`。11 个测试/消费子进程各自在启动原代码前独立保存 `which=null` 和真实 OS 执行 `git --version` 的 FileNotFoundError/errno2/WinError2，排除了仅移走仓库元数据但仍保留 Git 程序的解释。checkout 的对应探测能找到并启动 Git。

另核对未经观察器包装的原单例 `python -B -m unittest test_a02_r1.A02R1Tests.test_export_subdirectory_cannot_borrow_enclosing_git_head -v`：cwd 为 raw/tests，PYTHONPATH 指向该副本 src，实际 exit0、运行1项、无skip；同环境独立 OS 探测也确认 Git 不可启动。它直接关闭原 I1-GIT-01；原 R1 REWORK 和失败证据不改写。

## 实际导入与观察器边界

独立审查新建 trace_entry/trace_child/run_forms：读取本轮 bootstrap，没有运行写死旧父的旧脚本。完整入口通过 runpy 执行受审源码；外部观察器为每个原 Python 子命令保存原 argv、实际包装 argv、cwd、实际 module frame 的 `__file__`，并保存在 sys.modules 中实际加载的 annotation 模块。原脚本/-m 的 sys.argv 和 sys.path[0] 按相应执行方式重建；观察器增加 Git 可用性探测及导入记录，没有改测试断言、skip 或退出码。报告应明确这些完整入口是带观察器的实际执行，裸单例另有无观察器回执。

两形态各11次 launch 与 trace 的原参数/cwd已逐条对应。所有实际观察到的 annotation 模块，以及 A01/合同测试、新 A02 identity/test_a02_r1/test_a02_portability_r2，均通过实际 `__file__` 和发生时摘要绑定执行前输入索引及组合树原 blob；未使用作者 source_files 字段冒充导入证明。checkout 的原字节/精确 CRLF 表示只作为本次磁盘字节记录，不放宽旧参照。A02 测试生成的临时 identity 副本单独记录为 GENERATED_IDENTITY_COPY，发生时摘要与冻结 identity 相同，不把临时路径冒称为 snapshot 路径。

## 本子审实际命令与限制

静态阶段 `python -B boundary/audit.py --phase static` 实际 exit0，12条只读 Git 命令全部0；保留为 static.json。最终通过 `launch_final.py` 启动 `audit.py --phase final`，实际 exit0，48条只读 Git 命令全部0，重新核对上述静态边界和运行回执。本子审没有重新运行功能测试。

最终结构为 `final.json` 顶层 passed=true；`runtime.forms` 保存两形态，`runtime.bare_original_I1_GIT_01` 保存裸单例闭合。`command.json` 保存最终实际 argv/exit0，stdout.log/stderr.log 保存原始输出，audit.executed.py 保存实际运行源码副本；执行前后审计源码 SHA256 均为 `f2ffffe8b9dc5fe7bc46b535e26ed8d204ddaa28226a3971896449348291f1f3`。

零网络、平台、浏览器、凭据/profile、OCR或模型调用；未改实现、旧报告、状态或分支。短时只读子进程均已同步返回，自有运行进程/会话为零；这是本子审启动记录/声明层级，不冒充全系统进程普查。D01、S01、N15、B确认、平台和全书质量/成本仍按原边界处理。
