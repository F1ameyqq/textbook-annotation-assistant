# A02 portability-R2 正式独立复验交接

日期：2026-10-17。原执行对话已完成并冻结；主调度完成交付身份/范围前检，现正式续派原独立验收对话 `01a144cc-2eae-7a23-b299-03f533e30951`。尚未接受或集成本补丁，A01/A04/D01 不释放。

## 确切输入

| 输入 | 固定值 |
|---|---|
| base | `38aca9dcc8d027409b95193e9cc142c2336b76d3` |
| 补丁 / 作者实测代码 | `ad71284f3b6ffc8454ee1d1e30933c8e39d7c1d8` |
| 最终冻结交付 | `a1e5be00909172429d792b6c41bdaf384258694e` |
| 原派发工作流 | `6b77c436742cf2826083b109d8ed86b85539cba6` |
| 执行报告 | 该提交的 `docs/tasks/A02-portability-R2-execution-report.md` |
| 报告 SHA256 | `afb339fda44156cbb2ba1aaf4589b65e0746afedc3b2f3aa2a88403eae9b1a34` |
| 执行清单 | 该提交的 `docs/evidence/A02/execution/portability-R2/sha256-manifest.json` |
| 清单 SHA256 | `6a1c4fd174d4f2a44ae975da0995bfca0fae4b6c853406343ab98d9036b529e9` |

执行工作树 `C:/Users/ASUS/.codex/worktrees/a02-planner-mock/1800` / `codex/a02-planner-mock` 已核对 HEAD 与干净状态。只将其作为确切 Git 对象来源；不在执行目录跑生成器/测试或修改交付。正式交接的工作流为包含本文件的调度提交，由消息给出确切 SHA。

[主调度前检](../evidence/A02/coordinator/portability-R2-delivery-preflight/audit.json)确认：188项净改动覆盖完整，187项清单摘要与磁盘/Git原字节相同；2,084个既有Git文件不变，唯一既有修改为 `examples/a02/R1/identity.py`，其中 `source_binding` 函数字节未改。补丁至最终只加报告/证据。完成回合与冻结报告声明所有自有同步子进程已返回，无浏览器/后台 helper；没有独立系统进程扫描。

## 复验范围

执行[限定任务](A02-portability-R2-dispatch.md)和[已准备的14项检查](../evidence/A02/review-portability-R2-preparation/scenario-matrix.md)。准备记录不算功能结果。重点核对：

1. 从确切 Git blob 建立隔离副本；输入/SHA、环境及真正导入路径留证。常规 checkout 和 raw 无Git副本身份分开。
2. 真实子进程的无Git PATH、无 `.git`、`which('git')=null` 及实际 OS 启动失败。原 I1-GIT-01 单例须实际运行且无skip；helper返回明确unknown/null。真实有Git checkout验证自身HEAD，嵌套导出不能借父HEAD。
3. 第一次toplevel成功后第二次启动失败的有界独立注入、第二次非零/空HEAD等相关变化，不伪造verified。作者第二次故障是mock，不能冒充真实noGit测量。
4. `source_binding` 的外部Git不可用、无效身份/commit/源字节损坏仍拒绝；真实有Git合法绑定仍可通过，raw身份仍unknown。不要把外层采集器退出0当作每条子命令都成功。
5. 复跑受影响A02回归，原52项及新10项的实际结果与导入分别记录；只读确认旧src、旧测试、旧固定样例/报告/证据不变。缺项给最小反例，禁止代作者修复。

保留作者修前失败、收尾编码错误和修后对照。旧A01完整入口的REWORK、I04非阻断标签限制和LF/CRLF双摘要不改写。本轮不重跑A01完整集成入口、C01/登录/630几何矩阵；A02补丁单独接受后仍须主调度局部集成，再由原A01验收者针对新固定集成父版本做组合复验。

## 输出与权限

仅新增 `D:/1800/docs/tasks/A02-portability-R2-review-report.md` 与 `D:/1800/docs/evidence/A02/review-portability-R2/`；临时副本仅用 `.local/stages/A02-review-portability-R2/a1e5be00909172429d792b6c41bdaf384258694e/` 或自己的有限测试临时目录。别覆盖准备材料、原失败或旧验收。绑定必要输入、脚本、每条实际argv/cwd/退出码/stdout/stderr、真实导入、归档清单（含忽略日志）和自有进程释放。

结论限定 ACCEPTED / REWORK / BLOCKED，并注明这只是示例身份工具修复，既有A02业务接受不扩张。禁止改代码/合同/依赖/状态，不提交、推送、集成、释放A01/A04/D01或联系执行者/B；零网络/平台/浏览器/凭据/profile/OCR/模型。正式报告冻结后结束，交回主调度复现和集成。
