# A02 portability-R2 有界复验场景（准备，全部 NOT_RUN）

日期：2026-10-17（Asia/Shanghai）。阶段：**WAITING_EXECUTION**。本文件只定义独立检查方法，未运行被验工具、测试或故障注入，未有 R2 验收结论。

规则以[正式派发](../../../tasks/A02-portability-R2-dispatch.md)为准；执行基线为 `38aca9dcc8d027409b95193e9cc142c2336b76d3`，工作流为 `6b77c436742cf2826083b109d8ed86b85539cba6`。冻结补丁/最终提交尚未提供。不得把当前工作树 HEAD、R1 接受或作者将来的自报结果当成本轮接受。

## 隔离及取证方法

正式交付后，先核对确切提交、报告和统一清单，再导出必要的 raw Git blob 到新的正式验收专属目录，逐文件验证 OID/SHA256。只使用确切提交字节；正常 checkout 与无 `.git` 副本分开，并记录有限的 checkout 换行差异。身份工具实际 `__file__`、导入前后源码 SHA256、解释器绝对路径、原始 argv/cwd、子进程 PATH、`shutil.which('git')`、退出码、stdout/stderr 均留证。只有环境探针成功启动且确实调用被验函数，才能将案例记为已运行。

真实无 Git 子进程用明确的 Python 绝对路径启动。子进程 PATH 仅含已核对不含 Git 的系统目录，cwd 和源码目录均不放 git.exe/git.cmd/git.bat 等同名可执行文件；子进程内记录 `shutil.which('git') is None`，并独立尝试真实 OS 启动 `git --version`，预期为无法启动。必要的 GIT_DIR/GIT_WORK_TREE 等 Git 发现覆盖变量仅在该子进程环境移除并记录变量名，不输出其他环境值；不改主进程或全局 PATH。对照进程仅恢复已知本地 Git 路径，源码保持同一字节。仅 mock subprocess 的案例不能代替这些证据。

正常 checkout 使用新的本地、无 remote 的专属仓库或独立 checkout，预先明确 toplevel 与 HEAD；raw 导出嵌套在该测试仓库下以获得真正的父仓库对照。不会改主目录分支/索引、执行者工作树或全局 Git 配置，也不借父 HEAD 声明导出身份。准备/建仓时可使用本地 Git；正式 noGit 测量仅改变独立子进程环境。

## 场景表

表内结果均为预期，全部状态为 **NOT_RUN / 等待冻结交付**。

| ID | 独立输入或故障 | 需要的可观察结果 |
|---|---|---|
| P01 | 基线至冻结补丁/最终交付完整差异 | 唯一可变既有文件为 `examples/a02/R1/identity.py`；新增仅在任务白名单；src、原测试、根依赖、A01 来源/geometry/固定验收材料和旧证据不变。区别补丁与报告/证据提交 |
| P02 | 固定 raw 无 `.git` 副本，真实子进程 PATH 无 Git | OS 实际无法启动 Git；`git_identity` 正常返回明确 UNKNOWN、`checkout_commit=null`，不抛未处理 FileNotFoundError、不伪造验证、不跳过调用 |
| P03 | 原 I1-GIT-01 单例在同一 raw 字节运行，分别有/无 Git PATH | 原精确单例均实际执行、非 skipped、退出 0。修复前失败引用已冻结旧证据或在新输出复现；不得覆盖原失败。两环境只有有界环境差别，不重跑 A01 完整集成入口 |
| P04 | 正常本地 Git checkout，真实 Git 可用 | 先成功核对 toplevel 恰为指定根，再取 HEAD；返回的 commit 等于独立准备记录的真实 HEAD，不能一律 UNKNOWN 或固定字符串 |
| P05 | 同一仓库的子目录/raw 嵌套导出，真实 Git 可用 | 对照 Git 确实能发现父 toplevel/HEAD；被验 helper 仍返回 UNKNOWN/null，未把父 HEAD 当作导出身份 |
| P06 | P05 同一源码改为真实无 Git PATH | 仍为明确 UNKNOWN/null；不借缓存身份、不因无法启动而异常冒出；环境证据独立于 P05 |
| P07 | `source_binding` 要求外部身份仓库，真实 PATH 无 Git | 必须失败关闭，明确错误/非零或被调用方观察到异常；不得返回成功绑定对象、verified、伪源码清单或静默空结果作为成功。与可返回 UNKNOWN 的 `git_identity` 区分 |
| P08 | raw 源码 + 有 Git 的有效外部身份仓库 + 确切 declared_commit | 真正逐文件 blob 校验后方可成功；源码根仍 `checkout_commit=null`，declared_commit/外部仓库角色明确。证明 P07 修复未把成功通路一律关死 |
| P09 | P08 的单字节源码变更、无效 declared_commit、非仓库身份根（分别） | 各自失败关闭，保留实际错误和未返回成功的证据；不得放宽原始字节比较或将所有异常包装成 verified |
| P10 | 第一次 toplevel 真实成功，第二次 HEAD 启动前 Git 失效 | 用独立 wrapper 记录第一次真实 argv/结果，再在本子进程内令 PATH 无 Git，使第二次实际 OS 启动失败；helper 返回 UNKNOWN/null、不可残留 VERIFIED 或已有 HEAD。受控注入明确标记，不冒称 P02 实测的替代 |
| P11 | 第二次调用缺失的有限单元负例 | 可用 mock 定向触发 FileNotFoundError，或与 P10 相同实际第二次启动故障；记录首/次调用次序及参数，仅检查异常路径，不扩大为通用 subprocess 重构。若只有 mock，明确写“未替代真实无 Git P02/P03” |
| P12 | 两次调用返回非零等已声明失败路径 | 只在实现/作者测试显示有相关变化时有界覆盖；不应伪造身份。既有非仓库/子目录路径仍 UNKNOWN，保留具体原因而不抹平 source_binding 资格门 |
| P13 | 受影响 A02 discovery 与新增 portability 专属测试 | 从固定副本分别在有 Git 和真实无 Git 环境运行相关 A02 套件，记录实际数量/失败/skipped，不能吞掉失败或跳过旧原例；不重跑未改 C01、登录、630 几何或完整 A01 入口 |
| P14 | 旧报告/样例/清单/失败日志与新证据闭包 | 用冻结基线及旧固定清单核对原字节，记录任何原始日志格式例外；新清单包括新报告、原始输出、源码身份和实际命令，不能从当前源码重建旧期望来让保全通过 |

P10 的 wrapper 可以暂时替换启动入口来观察第一次真实调用，并在其返回后改变该子进程环境；调用本身须继续走真实 OS。若最终只使用模拟 FileNotFoundError，则仅计 P11，P10 写未运行及原因。`source_binding` 的 Git 在 ls-tree/show 阶段失效时，也不能返回成功；仅在本轮改变相关路径或出现疑点时补一项有限故障，不扩为并发/恢复实现。

## 正式结论与交接边界

正式复验按确切冻结提交给出 ACCEPTED / REWORK / BLOCKED。没有补丁/最终 commit、报告、实际复现命令与清单时不运行浮动实现。关键失败保存最小输入、实际环境和错误，验收者不修作者代码，不自动启动下一轮。

原 A02 R1 功能接受/本地集成保持独立事实。R2 单项通过仅能交主调度决定局部补丁接受/集成；A01 的固定集成父版本 + 冻结 `5f872150a237b195f73c78e02e13a91d2f4f46a7` 双形态入口由原 A01 验收对话另审，不释放 A01/A04/D01。N1/N2、真实来源 S01、内容 PENDING / NOT_SUBMITTED、A03 恢复和 B 接口确认边界不由本轮更改。
