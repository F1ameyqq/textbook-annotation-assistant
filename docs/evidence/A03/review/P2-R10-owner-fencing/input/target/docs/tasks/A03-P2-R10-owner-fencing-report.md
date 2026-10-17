# A03 P2-R10 双进程 owner/fencing 验证交付

2026-10-18（Asia/Shanghai）。状态：**REVIEW**。C1 同书真实进程 claim 竞争和 C2 实际换代后存活旧进程的 run_plan 拒绝，各首轮一次通过。产品、pins 与历史原件未改；本报告只交执行结果，不自行接受整个 V06/R09、A03 或释放 I01。

## 固定身份与输入

- 唯一 base：`bfd7fe896a7eee663ea8e0b6cf967548d8dd8f39`，接单时 clean HEAD 精确一致。
- workflow：`2d8357e040ee5c54494882bc175baf2579d07aed`；工作树：`C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`；分支：`codex/a03-runtime-recovery`。
- [任务原件](../evidence/A03/execution/P2-R10-owner-fencing/inputs/A03-P2-R10-owner-fencing-validation.md) raw SHA256：`5314105f2b1c8b773c4ceda21ed82904ea210258ecbb2406ce6cd29490c1510a`；[R9-R1 调度收口](../evidence/A03/execution/P2-R10-owner-fencing/inputs/A03-P2-R9-R1-owner-lifecycle-coordinator-decision.md) 从同一 workflow raw Git 取得。
- [输入登记](../evidence/A03/execution/P2-R10-owner-fencing/inputs.json) 保存4份必要原文、11份 base helper/产品/固定输入引用的路径、长度及 raw SHA。未合并浮动调度分支、复制历史全集或成功库。
- 最终交付提交为本报告与 R10 新增文件所在 clean HEAD，确切 SHA 由交付消息和 Git 日志提供，避免文档自引用提交哈希。

仅新增 [验证入口](../../tests/test_a03_p2_r10_owner_fencing.py)、[R10 驱动/归档目录](../../examples/a03/P2-R10-owner-fencing)、R10 execution 证据和本报告。沿用固定32×32、单题、两片段的 SYNTHETIC 语言。C1 从正常 init/register/create 建立新双库，不建立业务计划；C2 正常 import R3 setup helper，真实 begin/produce/admit PRE、targetcheck、planner、record_native_plan。所有旧 helper/fixture/证据未改，无 AST/exec 裁剪、产品 monkeypatch 或 SQL 写业务状态。

## 启动前冻结与过程界限

[驱动/预期冻结](../evidence/A03/execution/P2-R10-owner-fencing/driver-preregistered.json) 在功能进程启动前记录语法检查、屏障/身份预期和期限：

| 文件 | 实际执行/最终 SHA256 |
| --- | --- |
| `tests/test_a03_p2_r10_owner_fencing.py` | `da15d84be77fb9be7b718ff28721647a6b3c4052b32531cae45768394c798a82` |
| `examples/a03/P2-R10-owner-fencing/audit_a03_p2_r10.py` | `e1ef857ce0ab86e20a9196d6aacb329b9293db65c110d1e359ff257d5a8e885b` |
| `examples/a03/P2-R10-owner-fencing/prepare_a03_p2_r10.py` | `277689dd01e6fc7bdefe692cf597f5a3562b300c5e0710cdaaf7f64ee02dc7b6` |

功能父 watchdog90秒；每个业务 child 从实际启动计45秒。原产品 BEFORE_CLAIM 屏障5秒、lease10秒、观察2秒均未改；driver 文件信号等待也有明确期限。没有 sleep 后假设时序：每一步先保存 ready/marker/结果，再由父进程发下一屏障，使用真实 Popen.poll 检查参与者仍存活。

| 组 | 父 PID / exit | A PID / exit | B PID / exit |
| --- | --- | --- | --- |
| C1 | 68864 / 0 | 58044 / 0 | 54768 / 0 |
| C2 | 8636 / 0 | 64532 / 0 | 30244 / 0 |

原始 argv/cwd、脚本/输入摘要、source/fixture index、PID、stdout/stderr、exit/timeout/alive 均逐级保存；所有已登记业务进程 timeout=false、alive=false。两组均首轮成功，无功能修正、重跑或扩大范围。

## C1：同时存活的同书竞争

两个 child 正常打开同一个新 runtime/target，分别得到不同的 store instance；在 claim 内使用既有 FaultController 的 BEFORE_CLAIM 原屏障，各写入真实 PID/时间 marker。父进程核对两个 ready 和 marker 的 PID 与实际 child 一致，确认双方未退出后，一次写入共同放行文件。

[共同放行前记录](../evidence/A03/execution/P2-R10-owner-fencing/validation/r10-01/control/C1/before-common-release.json)、[共同放行信号](../evidence/A03/execution/P2-R10-owner-fencing/validation/r10-01/control/C1/claim-go.barrier) 和 [双方仍存活的竞争观察](../evidence/A03/execution/P2-R10-owner-fencing/validation/r10-01/control/C1/simultaneous-competition.json) 保留完整时序：

- common release at_ns=`1792275882655666000`，两份产品 BEFORE_CLAIM marker 均在它之前。
- B（PID54768，instance/owner=`process-ad51e6a832484ca9bb25794dc342cc47`）成功，generation=1；结果 at_ns=`1792275882708158400`。
- A（PID58044，instance=`process-74b42104d0d74b6b885f0e98f3b20695`）被现有 busy-owner guard 拒绝，实际 RuntimeFailure/OWNER_BUSY，消息 `lease expired AND previous process exited required`；结果 at_ns=`1792275882716377900`。实际根栈保留，没有只以任意异常算作竞争失败。
- 父进程在 at_ns=`1792275882734379100` 保存观察；此时双方 Popen.poll 均未退出，只有 B 是 ACTIVE owner，runtime PID/process_id/generation 与 B 一致，lease 有效；target fence 同步为 B/generation1。OWNER_CLAIM_RESERVED/OWNER_ACTIVE 各一次，目标 effects=0。

B 成功后启动自己的正常 LeaseKeeper，直到父进程保存双方结果和同时存活观察后才收到 finish 信号。随后停止 keeper 并正常 release；A 也在观察完成后才退出。双方实际退出时间均晚于上述 live observation，未把成功者退出后的串行接管当竞争。最终 runtime 为 RELEASED、generation1；target 保留最后合法 fence，未声称 release 会清空 fence。

本例没有 PRE/计划、intent/permit 或业务效果，准确范围是同书 claim 互斥；不证明效果提交竞争、死进程回收或完整并发矩阵。

## C2：实际换代后的存活旧持有者

另一个全新 case 中，A（PID64532）保留同一个真实 store 对象及 process-private PRE 资格：

| 正式对象 | revision / content_hash |
| --- | --- |
| ApplyPlan `plan-r10-C2` | 1 / `0d198aecd07811436f600857b2628e6f1fe4036d5f6206e55ae9e52f6495d183` |
| CheckReport `pre-r8-r3-C2` | 1 / `188fa0e7c21e4cb25b50e8cdc444b3d0f89cc69b677a13cd356f75c46d5e5cd0` |

实际 native PRE run=`native-pre-21c853507ff4455cb3c34fb3840df553`，SQL 为 ADMITTED；创建输入 anchor 和计划实体已正式记录，但没有 accept_plan：plans/actions/intents/permits 表均0，effects=0。真实四元组、观察/源/目标及完整初始状态见 [A 资格记录](../evidence/A03/execution/P2-R10-owner-fencing/validation/r10-01/control/C2/A-qualified.json)。没有手写计划或随意 generation 代替资格。

A 的原 instance/owner=`process-73c08347e45c46c985e61bc09e9457d4`、generation1。父进程发 release 信号后，A 正常 stop 自己的 keeper 并 release，写 [A 已释放记录](../evidence/A03/execution/P2-R10-owner-fencing/validation/r10-01/control/C2/A-released.json)，随后保持进程、store 和原 claim 存活。

B（PID30244）收到该释放信号后正常 open/claim，instance/owner=`process-4f7815867fdd4ceea891f653fe086290`、generation2，启动自己的 keeper。runtime ACTIVE 和 target fence 均匹配 B/2，见 [B ACTIVE 记录](../evidence/A03/execution/P2-R10-owner-fencing/validation/r10-01/control/C2/B-active.json)。

父进程确认 A/B 都仍存活、实际代次增加且 fence 同步后，才通知原 A 从正常 run_plan 入口传入原 owner/generation。A 仅尝试一次；实际 RuntimeFailure/OWNER_GENERATION_STALE，消息 `current ACTIVE lease required`。保存的 traceback 明确到达既有 `_lease`，不是在资格读取前遇到无关错误后冒称 fencing，见 [旧资格调用原记录](../evidence/A03/execution/P2-R10-owner-fencing/validation/r10-01/control/C2/A-stale-result.json)。没有额外猜测或限定新的包装错误码。

调用前后 plans/intents/permits 和 effects 均0，B 的 owner/generation/ACTIVE/PID/instance 与 target fence 不变。A 在移交后没有 renew/release 或覆盖 B。父进程再次保存 [双方存活且 B 仍 ACTIVE 的观察](../evidence/A03/execution/P2-R10-owner-fencing/validation/r10-01/control/C2/after-stale-live-observation.json)，然后才允许 B 正常 stop/release，A 退出；最终 runtime 为 RELEASED/generation2。

这证明实际正常 release/claim 换代后，仍存活原进程的旧资格在效果入口失效；不声称死进程回收、pending 清除、崩溃点或其他身份矩阵完成。

## 冻结双库、时序及正式 Resource 回查

[文件/SQL-only 交叉回查](../evidence/A03/execution/P2-R10-owner-fencing/database-and-timeline-readback.json) 使用标准库 SQLite `mode=ro&immutable=1`、query_only；没有导入或调用产品。四份最终库 quick_check=ok，读取前后字节相同；当前 bundle refs 全部在 SQL artifacts 登记，C2 plan/PRE refs 与 A 资格记录相符，原 package 的正式输入、PRE 运行、图像及递归 Resource 均保留于清单。

| case | runtime raw SHA256 | target raw SHA256 |
| --- | --- | --- |
| C1 | `14f7008bf84c8fe0ed0b42193ed86f47eb25db5b3ba19951a3721fb294c16ada` | `38eeba5336d71ff06d44119489864761caf68eab2c465138e7df8d0073821265` |
| C2 | `9709c69a9c1e7dcc843e53c4661c919dd825480319ddf4e15bd7b8bab783167e` | `7555093a48a3339f885c97555fc9bf1cbe93d0d05ac64b53ef6408a2c84c4878` |

C1 runtime 有4个 artifacts、3个事件，无 PRE/创建锚/计划接纳；target observations=0、effects=0。C2 runtime 有8个 artifacts、6个事件、1个 ADMITTED PRE/创建锚；plan 虽正式记录但未接纳，plans/actions/intents/permits 均0；target observations=1、effects=0。没有回执、解决结果或 POST/Batch，不以缺失产物补造业务成功。

live 阶段的每份 SQLite 读取各用自己的只读事务，两个库及 raw-byte 读取按顺序进行，**不声称跨库原子快照**。并发到达依据是实际屏障、Popen 存活检查、产品 claim/lease/fence 和完整时序。冻结回查另核对：C1 两份 marker 先于共同放行、两份结果晚于放行、双方退出晚于 live observation；C2 资格→A release→B ACTIVE→旧调用→拒绝→live observation→B release 有序。

## 可搬运入口、导入与保全

在仓库根目录实际执行：

```powershell
python -X utf8 -B examples/a03/P2-R10-owner-fencing/prepare_a03_p2_r10.py
python -X utf8 -B examples/a03/P2-R10-owner-fencing/audit_a03_p2_r10.py run C1 python -X utf8 -B tests/test_a03_p2_r10_owner_fencing.py C1
python -X utf8 -B examples/a03/P2-R10-owner-fencing/audit_a03_p2_r10.py run C2 python -X utf8 -B tests/test_a03_p2_r10_owner_fencing.py C2
```

默认输出根 `docs/evidence/A03/execution/P2-R10-owner-fencing/validation/r10-01`；driver 可通过 `--output-root` 指定该 R10 evidence 下新的相对路径。已有输出 exclusive，不覆盖重跑。prepare 只适用于指定 clean base/空输出准备；独立复验应在隔离目录使用确切交付字节、新的输出根。

真实 executable=`C:/Users/ASUS/AppData/Local/Programs/Python/Python39/python.exe`。四份 worker imports、C1 ready 及 C2 资格/接管记录均保存实际 module.__file__/raw SHA；产品路径在本工作树 src，正常 helper 在本工作树 tests。全程产品 source index 与 base 相同；具体摘要见 final-file-audit 与逐组 preregistered.json。这是源码运行记录，不是安装验收。

功能结束后的唯一附加进程化回查是 `readback_a03_p2_r10.py`，PID55388/exit0，不调用产品。文件复核入口为 `python -X utf8 -B examples/a03/P2-R10-owner-fencing/seal_a03_p2_r10.py check`，只校验冻结文件、raw Git 与清单。

[进程释放清单](../evidence/A03/execution/P2-R10-owner-fencing/process-release.json) 记录全部已登记自有父子进程已 wait/退出；[系统 PID 只读回查](../evidence/A03/execution/P2-R10-owner-fencing/process-os-readback.json) 只检查本轮已登记 PID，不终止其他任务。最终与 base 的32152个 raw Git mode/type/blob 逐项比较，所有旧条目无例外保留；[范围/清洁门禁](../evidence/A03/execution/P2-R10-owner-fencing/scope-state.json) 记录旧 tracked 状态和最终 empty-status 要求。manifest 包含报告、完整驱动、必要输入、真实导入/原输出/marker、双库/正式资源和释放证明，仅排除自身；入库后再核对全部 raw blobs，clean commit 冻结。

[本轮结果](../evidence/A03/execution/P2-R10-owner-fencing/bounded-outcome.json) 和 [覆盖边界](../evidence/A03/execution/P2-R10-owner-fencing/coverage-map.json) 只对应原 V06/R09 的这两个子项。R9-R1 独立四组有限接受仅引用确切调度结论；作者原 borrow FAILED、D2 NOT_RUN 及原 R3 N7 失败均原样保留，没有重跑旧组或整套测试。

字段重置持续 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。未改用户 model/thinking、调度 state、产品/schema/profile/pins/oracle/依赖或他人文件；无子代理、网络、平台/浏览器/profile/凭据/OCR/模型、安装、推送、B联系、A05题22或书级送交。仅交 REVIEW，整体 A03/I01 与其他 P2 缺口不自动关闭。
