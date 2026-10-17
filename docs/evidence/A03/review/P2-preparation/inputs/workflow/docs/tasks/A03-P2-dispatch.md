# A03 P2：按已接受设计实现离线持久化与恢复

日期：2026-10-17。**主调度批准 P2 实现**。延续原执行对话 `01a145aa-2fea-7942-97f9-ad260acf4e30` 和独立验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a`，不新建重复阶段。

执行 base=`940a5de33a24b1a3a9ded6e69ade1dd0609ed83a`，在原 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800` / `codex/a03-runtime-recovery` 继续。工作流提交是包含本任务的调度归档提交，派发消息给出其确切值。不要合并浮动主目录；A02 代码依赖仍为已接受 `ec1b4defbfa3ec0f181d291106fb53313983e493`。并行的 A02 Git 可用性修复仅改示例身份工具，不是本 P2 的依赖或允许改动范围。

## 采用的设计

采用 base 内原 P1 决策表、P1-R1 API/闭包修订及 P1-R2 提案和完整正式包 `examples/a03/P1-R2/`。API SHA256=`e2b0865fc1a25206181f3094155b059a6d34eb851afc750e813f0c2e89960f85`；R2提案 SHA256=`acd67720e905a45b85c0943648b239b2dfd1fdb36eaf3095e56803c1de564f9d`。冻结设计里的 REVIEW/UNIMPLEMENTED 标签作为历史保留；本文件是后续实现授权，不回写旧设计标签。

[P1 主调度收口](A03-P1-coordinator-acceptance.md)批准 D01–D08 及具体期限。必须完整实现接受事务的动作预留、intent→permit发放→单次消费→派发→结果链；无 intent 的未尝试事实走专用只读事务，不能伪造调用。逐消费者声明递归引用、精确普通四元组、资源字节/身份/混合环以及跨scope当前全书账本职责不得合并成自报布尔值。

## 唯一写入者与范围

原执行者是以下路径唯一实现写入者；[原任务](A03-runtime-recovery.md)第4–6节所有不变量及 V01–V10、[独立验收标准](A03-independent-review.md)R01–R18原样适用。

- `src/annotation/runtime/storage/`、`src/annotation/runtime/recovery/`：SQLite、不可变产物、事件/占有权/恢复编排及局部CLI。
- `src/annotation/delivery/reconciler/`：只读比较及解决证据，不直接改库或发效果。
- `src/annotation/contracts/`：仅批准的恢复版本、严格验证、全合成准入、公共入口、归档和显式转换，单独实现提交；不实现真实 S01。
- A02 既有文件仅 `src/annotation/delivery/mock/__init__.py`、`src/annotation/delivery/planner/__init__.py`、`src/annotation/quality/targetcheck/__init__.py`；新增持久目标只允许 `src/annotation/delivery/mock/persistent.py`。职责和签名按冻结API，不复制既有业务规则。
- 新增 `tests/test_a03*.py`、`tests/fixtures/a03/P2/`、`examples/a03/P2/`、`docs/a03-runtime-recovery.md`、`docs/evidence/A03/execution/P2/`、`docs/tasks/A03-execution-report.md`。

禁止改父目录公共入口、根依赖/属性/政策、source/geometry/浏览器、A02身份示例工具、调度文件及任何旧样例/报告/失败证据。现有目录内新增局部入口即可；确有缺失先给最小失败和精确路径补充提案，不能越界实现。只用标准库 sqlite3 和已有依赖，不安装新包。

## 交付和正式验收门

全部来源、资产、证据及目标效果为 SYNTHETIC / SIMULATED。拒绝真实/ORIGINAL/OBSERVED，S01保持单独阻断。runtime与target必须是不同SQLite文件和事务，使用真实独立Python进程、明确屏障与故障注入证明效果后崩溃、读回恢复、两进程owner fencing；不以同进程异常替代。

交付正常、效果后丢响应/退出、明确未生效三条可搬运最短演示；同书跨scope/run未决、另书隔离、部分计划充分/不足ABSENT、旧无intent UNKNOWN、损坏/版本/目录替换、次数与期限边界按V01–V10实测。reconcile只有读效果，不自动重发旧动作；后续模拟执行必须另走当前快照/检查/新规划。

先单独提交合同版本/验证扩展，再提交runtime及公开接缝实现；报告和证据另可定位。报告逐项区分通过/失败/未运行，记录真实导入路径、Python/SQLite/依赖、argv/cwd、退出码、输入输出、独立目标效果次数和自有进程释放。统一清单覆盖实际必要证据和日志，排除自身并说明忽略项；保留失败，不复制无关旧历史全集。

独立验收对话现在仅可在 `docs/tasks/A03-P2-review-preparation.md`、`docs/evidence/A03/review/P2-preparation/` 做一次准备并结束等待。正式功能验收须执行者冻结干净提交、报告、清单和释放声明，主调度前检后再续派；届时输出仍为原标准指定 `docs/tasks/A03-review-report.md` 与 `docs/evidence/A03/review/P2/`。不提前读取浮动实现作为被验版本。

禁止浏览器、网络、平台、凭据/profile、OCR、模型调用、A05题22重放和书级提交。执行者只交 REVIEW，不自行 ACCEPTED/INTEGRATED；本次批准不释放 I01，不表示真实应用已完成。结束所有自有测试进程，不动他人进程/数据；本地交付不推送、不向B发消息。
