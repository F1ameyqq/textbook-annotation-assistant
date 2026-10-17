# A01 integration R1：边界与入口独立复核

仅针对 `5f872150a237b195f73c78e02e13a91d2f4f46a7` 的受审变更；不替代根复验者的功能/损坏实测及最终结论。证据脚本为 `audit.py`，结果为 `result.json`。本子任务不运行功能回归，不改实现、不修改受验副本、不调用网络/平台/凭据/模型。

## reference_commit 未断言的实际影响

新 fixture 的顶层 `reference_commit` 当前正确为 `c3aff9598b6705ab4122062615a13ae3774698b2`。`fixed_inputs.materialize()` 仅转发该值，常规测试没有把它与旧参照的顶层值比较；`preservation.audit()` 也只把它抄入结果。这是一个确实存在的来源标签完整性遗漏，不能声称单改此标签会被常规测试拒绝。

但该标签不是本入口选择内容/候选的输入。常规测试独立锁定旧清单 SHA256 `9ea7a71204c0417b16b232511010a781ad5a9c001287cc89c059b87a2b6ec795`，检查旧清单的真实 `reference_commit`、971 条、25 个明确候选；再要求返回的 `source_manifest_sha256` 等于这个固定摘要，四个 entry 与固定旧清单的 entry **全等**（包含 path、Git blob OID、git_sha256、所有有限表示及长度）。materialize 同时严格解码 base64 并校验原件 SHA。四份编码字节分别与旧参照提交的真实 Git blob 全等，脚本也独立重算 Git blob OID 与 SHA256。

这意味着只改顶层标签不会让另一份内容、另一 blob OID 或额外换行表示通过；如果把编码内容与其自报摘要一起改掉，entry 全等仍失败。如果保持相同四份字节却把顶层标签写成另一提交，返回的标签会失真，但这四份原件的实际原参照身份仍由被固定摘要保护的旧清单决定。新测试中的四个指定路径访问加上选中数量四/重复路径拒绝，也没有给替换为另一组条目的空间。

因此，本子复核将它认定为**需如实披露的非阻断冗余标签遗漏**。本轮“固定编码内容/身份”必需对照应至少证明改编码/entry 身份和改 `source_manifest_sha256` 被拒绝；它们才是实际门禁。不能将该判断扩张成“来源标签已认证”，也不能将新 helper 当成独立的通用来源认证工具。若验收方另要求这个展示标签自身也必须具备篡改拒绝能力，那属于更强的独立元数据完整性要求；当前任务/交接没有把该字段单独列为必需门禁。

## 入口行为与适用对象

常规入口的 11 个子入口为 A01、C01、A02、离线登录、固定 URL、legacy 两书直接消费、R3 两书直接及搬运消费。每次赋值均是 `run(...) and all_ok`，左侧 run 总会执行，旧失败状态不会恢复成真；最终仅 all_ok 真才 exit 0。子进程非零不是 skip。异常未被捕获为成功，启动/输出异常会使外层非零。`--focused` 明确仅运行 A01 损坏对照，不能冒称 11 个入口通过。

新入口适用于演进中的固定两父集成树；仅 A01 分支缺 A02 时不能声称全套可运行。原 R3 verify 的971/62严格字节门禁保持原件，不适用于已经修改旧测试的新集成树；需对 `180bb1e86fb2a7eb1546be85af70f466f069daf5` 原冻结发行单独运行。常规测试不再把当前调度文档当旧发行字节，也不声称对当前每份源码提供旧发行完整哈希门禁。

运行期 fixed_inputs、A01 新测试、常规 verify 自身和消费程序不直接调用 Git，也不从当前磁盘重建期望；但不能据此推断整个子入口调用链无 Git 依赖。verify 用 ROOT 定位源码，设置 PYTHONPATH 后在独立 cwd 运行搬运包，包通过公共 load_bundle 与 A01 完整图像校验。

## 完整入口的 Git 可执行程序依赖是本轮阻断

根复验的 raw 输入没有 `.git`，PATH 为 `C:/Windows/System32;C:/Windows` 且找不到 Git 可执行程序。11 个子入口均实际运行，但 A02 子入口退出 1，完整入口退出 1；A01/C01/登录/URL/六次消费均退出 0。错误来自固定主父中既有 `tests/test_a02_r1.py` 的 `test_export_subdirectory_cannot_borrow_enclosing_git_head`，它调用 `examples/a02/R1/identity.py:git_identity()`。该函数无条件 `subprocess.run(["git", "rev-parse", "--show-toplevel"], ...)`，只处理命令运行后的非零状态，不处理程序不存在时的 FileNotFoundError/WinError2。完整入口没有吞掉该失败，错误传播正确。

这不是本次 A01 改坏 A02 的证据，但新入口无条件纳入 A02 后就继承了这个运行依赖。最终交付执行报告明确写“该入口无Git依赖”，独立交接必需项5要求“搬运后无Git运行”；仅移走 `.git` 而保留 PATH 中的 Git，只证明无仓库元数据运行。这个实际失败因而阻断本轮**完整入口无 Git 适用性**接受，不能改称完整通过，也不能用 focused 模式、略去 A02、作者全零或有 Git 的成功对照来抵消。

该缺口不授权复验者修改 A02。适当结果是保留最小失败与有 Git 对照并交主调度决定后续有界修订；不能自行扩大白名单或放宽本轮必需检查。它与上面的非阻断标签遗漏是两件独立事实。

## 实际导入证据

作者 `source_files` 只读了路径字节，不证明测试进程导入位置。根复验使用外部 trace_entry/trace_child 运行受审原入口并剖析实际模块 frame 的 `__file__`，同时保存退出时 sys.modules 的 annotation 模块。该证据应逐子入口关联原 argv、实际观察器 argv、cwd、__file__ 与预执行固定输入 SHA；不能只列文件存在。

`audit.py` 读取已完成的两种 runtime 结果，每种均独立核对 11 次 launch 与 child 的原参数/cwd 对应、记录的 annotation 模块全在相应固定副本内、字节与预执行输入索引相同，且实际覆盖 importer、consistency、geometry、contracts.models 和两个受改/新增测试。raw 的实际导入证明成立，但完整运行结果仍为 A02/外层退出1。初次只完成 checkout、raw 尚 pending 的检查结果另保留为 `result.initial.json`。系统 sys.path 中仍有既存 editable 路径，但真实模块记录能证明本次受验模块使用本隔离副本。该证据是带外部观察器的真实执行，不应在报告中写成未经观察器包装的裸命令回执。

另外核对根复验的 `git-availability/minimal-with-git/command.json` 与 `minimal-without-git/command.json`：同一原字节输入、同一 A02 单测、都无 `.git`，未经观察器包装，分别 exit0/exit1；无 Git stderr 定位原始 identity.py 的 WinError2。它排除了观察器造成失败及“借用父仓库 HEAD”造成失败的解释。完整有 Git 对照由根复验另收口，不是本子审查自行执行。

本子复核建议最终结论为 **REWORK**，阻断点只有这里证实的完整无 Git 入口依赖；标签遗漏作为非阻断限制独立披露。

本子任务只启动已退出的短时 Git/Python 命令，无浏览器或持续会话，待释放自有会话为零。根任务的完整进程/会话收口由根复验者另行记录。
