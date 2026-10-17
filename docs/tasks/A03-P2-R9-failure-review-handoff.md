# A03 P2 R9 正常路径首败：独立故障复核

本轮只确认已冻结的 D1 故障及最小修复范围，不重新执行 D1/D2，不修改产品，不扩大验收标准。沿用原 A03 独立验收对话；保留用户手动设置，派发省略 model/thinking。

## 冻结输入

- 执行基线：`435aaee2d140e82d3237ce8902d594a1aee70aad`。
- 交付提交：`c83f956c5c29c64ab10735ba11c153201d3f3f4b`，分支 `codex/a03-runtime-recovery`。执行目录 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800` 只读。
- 执行任务及先前有限验收位于调度提交 `11300250bef18d4bdf7220111cf82232c7d5e0f3`。取本任务时使用本次消息给出的调度提交；不要合并整条调度分支。
- 执行报告 `docs/tasks/A03-P2-R9-minimal-demos-report.md`，SHA256 `6f68b69ed13cbdc3194346181054eef70b9abc45c1a714ab35b60ab847b3c72d`。
- 证据目录 `docs/evidence/A03/execution/P2-R9-minimal-demos/`；`manifest.json` SHA256 `7712cad90e09e0883dc4dc95d36608a066d76ca62aa10a2664df0b7a48917c86`；`process-release.json` SHA256 `f64486a952a14bf62589f4ae12d63681811bfafdbc6fcaf69d1b81d4f7271273`。
- 调度字节核对 `docs/evidence/coordinator/heartbeat-20261018-0514/delivery-preflight.json`：31482 个基线树条目原样，183 个新增文件与 raw Git blob 相同，182 个 manifest 条目及 5 个任务输入已核对，4 个登记进程均退出。该结果不是产品通过。

## 已观测故障与待核实事项

执行者报告 D1 走正常 PRE/admit/target/planner/record 路径，单个 CREATE_FRAMES 已生效并提交正式 receipt，随后 run_plan 调 publish_quality 时 native 分支再次 claim 同一本书，触发 OWNER_BUSY。首败后按任务约定停机；D1 新进程重开/重复保护及 D2 均未运行。

1. 用固定提交源码及冻结 traceback 独立确认：`recovery/__init__.py` 的 run_plan 在持有 owner/generation 和 LeaseKeeper 时调用 publish_quality；`native_quality.py` 无条件 claim_current；storage.claim 对活跃 owner 拒绝。区别产品控制流缺陷、驱动错误、合同问题；引用实际行号，不仅复述作者结论。
2. 只对自己从 raw Git 提取的 DB 副本用 stdlib SQLite `mode=ro&immutable=1` 读数，禁止连接原执行 DB 或调用候选产品。核对同一 plan/action/intent/receipt、attempt=ATTEMPTED、effect=1、POST/Batch/native_report_reads=0、最后 owner 释放，与原日志一致；报告读取前后摘要。before 两个 DB 是顺序复制，不声称跨库原子快照。完整结果/引用可引用已封存证据，不复制无关历史数据。
3. 核对 D1 父 PID42924/执行子 PID61832 均 exit1，观察子 PID21684 与只读补证 PID22652 均 exit0，退出/超时记录及 stderr 摘要可追踪。保留首次失败以及 metadata 首次封存准备 TypeError；不将静态修正包装成测试重跑。
4. 给出可交原执行者的一次有界修复建议：优先检查显式传递并校验当前 owner/generation、复用现有 lease，与独立 publish 入口自行 claim/release 的生命周期能否分清。不得建议全局放松 OWNER_BUSY、提前释放写入锁、绕过 instance/generation/pending/hold fencing、扩大读预算或隐藏发布失败。若建议其他方案，指出原因及确切必要路径。
5. 只列修复后必须复验的有限项目：原 D1 正常完成/独立重开/不重复效果，独立 publish 入口，借用 ownership 的校验与释放边界，以及原 R9 D2。本轮不执行这些项目；不加入新的整套 P2 回归。原有较广 P2 覆盖缺口继续保留。

## 边界与交付

使用自身独立审查目录；原报告、DB、日志和旧失败证据逐字节保留。无需调用产品、重放失败或另建子智能体；只读静态审计即可。不得执行 field-reset 或其变体/委派；状态继续 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。不访问平台、凭据、B 对话、付费模型，不修改生产者/profile/adoption/schema/pins。

交付简洁报告 `docs/tasks/A03-P2-R9-failure-review-report.md`，审查证据仅放 `docs/evidence/A03/review/P2-R9-failure/`；提供引用、逐文件 SHA256 manifest 和本轮自己创建的进程退出证明（若无进程也如实记录）。记录审查时 exact target、脚本及输入摘要。结论为故障确认/证据不足及最小修复边界；**D1/D2、整个 A03、I01 不得记 ACCEPTED/INTEGRATED**。最终消息给确切文件位置与摘要，留给调度复核并派发修复。不要自行修产品、追加无界重试或给 B 派单。
