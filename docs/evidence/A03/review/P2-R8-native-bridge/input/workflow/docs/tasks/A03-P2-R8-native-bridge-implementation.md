# A03 P2-R8：原生 PRE 与单题恢复桥接实施

2026-10-17。继续原执行对话 `01a145aa-2fea-7942-97f9-ad260acf4e30`，原工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`。唯一 base 为 `8ad45dd07214ae406a3fab28d76a4b5abd6eef03`。保留用户手动设置，消息省略 thinking/model，不委派、不合浮动主树。

R7 已独立接受、经调度复现并局部集成，见[R7 调度决定](A03-P2-R7-readonly-codec-coordinator-decision.md)。本任务实际实现 A 内部合成原生桥接，目标是首次跑通一个真实生成的单动作 UNKNOWN 恢复链。不是再做一轮静态设计。成功仍须原独立验收，不能自行接受整个 A03 或释放 I01。

## 固定依据与本轮采用决定

固定输入索引为 [R8-input-pins.json](../evidence/coordinator/heartbeat-20261017-1329/R8-input-pins.json)。R4 接口表 SHA256 `b57d0af5d72a03c4b16e6eeedc267bda50f1dfcf022728b1f107f5b158a22207`；其中 19 个 proposed_signature 及责任分界作为本轮桥接签名，bridge_context 是显式 keyword-only 参数，省略时旧 C01 行为保持。新原生版本在无合格 context 时拒绝。允许必要的局部 helper，交付列出实际签名，不复制 planner/targetcheck 算法另造替代入口。

主调度作为 A 内部合同负责人选定以下实现边界；新实现最终 exact pins 随冻结交付由独立验收确认。B 业务合同继续未确认，下面的采用仅限合成测试。

1. 新版使用 `1.4.0-a03-native-proposal` / `a03-exchange-4-proposal`，profile `a03-native-synthetic-1-PROPOSAL`，单独存放于 `annotation.contracts.a03_native`。原 1.3、R7 只读 API/数据和所有旧 profile/schema/API 原字节保留。1.1/1.3 仅作显式历史读取，不能通过改版本、重封签或版本白名单取得 CURRENT 资格。新 schema 的变化限版本、实际 PRE 运行、creation-input anchor 和必要原生绑定；旧闭包/证据/业务不变量不得删除。新内置 profile 固定 schema/API/接口/实现摘要及采用范围，未知组合 fail closed。
2. 采用固定合成 oracle 的五项判据作为本轮产品 producer 的唯一测试语言：R2 `oracle.json` SHA256 `659a715bd293026e28ec50f6bccbe1cecdf6511d168afc9f98d9ab05f6e8efb9`，纯比较 verifier SHA256 `6667659ccc71cf1c0769d2ca7c684021140046a71a2ca73e40699aa354afac2d`。保留两份历史原件的 CANDIDATE/false 标记；另加新采用记录说明迁移，不执行旧 examples 模块。产品实际读取完整资源、解析 32×32 PGM 并计算源完整性、结构、答案关系、覆盖分母、policy 五项；不能读预期答案后直接返回 PASS，不能以 Graph hash 相等替代比较。输入明确唯一 Source/Evidence/Graph/Policy，不能用最后一个同 kind 节点覆盖歧义。只证明这个固定合成语言，不能代表 OCR、B 质量或真实内容检查。
3. `BridgeSelection` 是 immutable 的 exact codec/profile/schema/API/interface/oracle/verifier pins 和 role 描述，无 authority。`BridgeContext` 绑定显式资产根、已验证完整输入与受控 native registry 回调；JSON 或普通描述对象不能构造回调资格。`STATIC_INSPECTION` 仍走 R7；`CURRENT` 只在本轮新的合成 native API、实际 PRE 与运行时检查齐备时使用，不开放真实来源。

## PRE、历史与运行时 ABI

新增 `src/annotation/quality/synthetic_precheck.py`。保留 R4 私有接纳形状：

`admit_a03_pre_run(bundle, pre_ref, *, bridge_context, registered_run_handle, actual_snapshot_ref, asset_root)`

quality 负责实际五项检查和不可变检查产物；runtime 独占登记、持久事务、当前状态及唯一签发/验证。质量模块不直接更新数据库或签发写 permit。允许在该模块另设明确 producer 入口，输出新 PRE、run resource 和完整 bundle；报告列精确签名、结构与数据流。

- **INITIAL**：从全新、没有 hold/pending 的实际登记开始，context 的 hold_id/head/ref 全为 null；基于当前登记、真实目标观察和新五项运行生成 PRE。不得复制旧 PRE stub 改 ID/时间，旧 fixture plan 不作为新计划。
- **POST_HOLD**：由正常受控操作产生真实 hold，再绑定确切 hold id/head、registration/source/book/scope/target/store/session、当前 owner/generation、重新读取的 snapshot/observation 和 exact 输入 refs。旧 run 或旧 snapshot 不能清除新 hold。只读原观察行的验证不暗加业务目标读。
- `AdmittedPreRun` 是私有、不可由 JSON 重建的本进程凭据，绑定真实持久 run 行、完整输入 canonical/raw 摘要、PRE 四元组、五项结果及观察身份。实际准入时再次核对原生行和当前状态；重开不能由自报 PASS 恢复旧凭据，只能按显式流程重新核验或生成新运行。它不是 dispatch permit。
- `CurrentWriteEligibility` 留在 runtime 私有路径；每次实际派发仍需完整登记、owner/generation/fence、当前全书 head/pending/hold、期限/持久预算、确切 intent 和单次 permit。不能仅凭 `assert_plan_ready`、PRE PASS、PreparedAction 或 context 通过。
- **creation-input anchor**：生成计划时保存当时完整 bundle 的不可变 canonical bytes 和已消费 Resource 原始字节清单，绑定 exact source/graph/PRE/TARGET/snapshot/policy/config 及输入摘要。后续先验证原始完整历史，再按这个 anchor 重算同一计划。私有 HistoricalDerivationView 不导出为当前准入包；不得过滤 UNKNOWN、登记事件或 EvidenceRecord 来使 planner 通过。完整正式引用、typed frame 和混合 DAG 规则沿用已审语义。
- planner 的投影、目录/题序、action-id、依赖、policy 和事实比较算法保持；通过上述真实 PRE/TARGET 调用现有 create_plan，固定单题应生成一个 CREATE_FRAMES。PreparedAction 必须来自实际 session；observation binding 保留 R4 全部 19 字段及同计划 progress，新增 snapshot/resources 在持久消费者提交前进入完整闭包。

本轮只创建新的合成 runtime/target 两个独立 SQLite 库。为新格式增加明确 meta/profile/adoption 记录及严格 open 检查；原默认入口拒绝新格式，新入口拒绝不匹配/中断的格式。未知库、既有旧库接纳与旧连接迁移保持阻断，不能隐式迁移或重置。实际 read budget/期限/lease 继续采用 P1/R1 已选值，读前计数、崩溃耗次、retries=0；不能通过新 call/重开刷新预算。原 A03 更广泛数据库迁移与故障矩阵不是本轮接受范围。

## 唯一写入者与允许范围

新增 `src/annotation/contracts/a03_native/`、`src/annotation/quality/synthetic_precheck.py`；允许在原 `src/annotation/runtime/storage/`、`src/annotation/runtime/recovery/`、`src/annotation/delivery/reconciler/` 内实施原生桥接。

已有共享文件仅限：`src/annotation/contracts/__init__.py`、`validation.py`、`recovery.py`，`src/annotation/quality/targetcheck/__init__.py`，`src/annotation/delivery/planner/__init__.py`，`src/annotation/delivery/mock/__init__.py`、`persistent.py`。只加明确版本/角色分发及必要 native binding，保留旧默认行为；不改 C01 类型、policy、业务规则或其他 source/geometry/浏览器文件。`pyproject.toml` 仅可新增 a03_native 的 package-data 声明，不改依赖/版本/已有条目。

新增 `tests/test_a03_r8_native_bridge.py`、`tests/fixtures/a03/P2-R8-native-bridge/`、`examples/a03/P2-R8-native-bridge/`、`docs/evidence/A03/execution/P2-R8-native-bridge/`、`docs/tasks/A03-P2-R8-native-bridge-delivery.md`。不改旧 tests/examples/证据/任务/state/AGENTS。禁止改 R7 产品与冻结数据；如必须改出界代码才能闭合，给一个精确最小失败与路径后停止，不越界绕开。

## 有界执行与验收标准

先完成实现和静态检查，再执行以下固定组。使用新目录、新合成 ID；实际链路产物必须由产品产生，测试驱动只能安排输入和受控故障，不直接插入成功业务行。

| 组 | 必须证明 |
|---|---|
| N1 单动作端到端 | 新 INITIAL 实际五检查与接纳 → 真 TARGET → 真 create_plan 单动作 → 原生 prepare/intent/permit → 独立目标效果后进程退出或丢响应 → UNKNOWN 且原 receipt 不存在 → 只读恢复终局 head、original_receipt_ref=null → 同 intent/fact 的晚到完整 receipt → 独立报告读生成新 POST/Batch。目标效果次数恰好一次；原 UNKNOWN 不删，内容 PENDING、NOT_SUBMITTED。必须实际子进程及明确屏障，不能用同进程异常替代崩溃。 |
| N2 POST_HOLD 生命周期 | 正常操作产生 hold；旧 INITIAL/旧 hold run 拒绝；真实新观察与新五检查被当前 hold 接纳；头已正常推进后的旧证明失效。保留过程，不直接 SQL 改资格/头做通过样例。 |
| N3 五检查直接控制 | 固定合成正例外，五个各自 schema 合法的局部语义不匹配分别到达 source_integrity、structure、answer_matching、coverage、policy 比较层，不能仅靠坏 hash 拒绝。每项至多一个负控；原件不变。失败无接纳或效果。 |
| N4 缺少/他属运行 | 序列化 PRE/PASS 不能代替真实 run；两个正常创建的独立 registry/session 不能互用运行证明或观察。验证失败无 permit/效果。 |
| N5 旧版本与角色 | 旧 1.1/1.3 和 R7 静态对象只能历史/静态读取，不能进入新 CURRENT。新版本未知 pins 或无 native context 明确拒绝；不重放旧效果。 |
| N6 创建输入与历史 | N1 后原 creation anchor 可重算同一计划；同一完整历史仍保留 UNKNOWN。一个缺失正式依赖/资源的 anchor 控制拒绝，不能回退到裁剪当前包或重封签旧版。 |
| N7 新库生命周期 | 全新双库版本/profile/adoption 元数据严格绑定，重开身份一致；一项不完整初始化在正式完成点前拒绝且无效果。旧库接纳保持 NOT_IMPLEMENTED/BLOCKED，不伪称完成。 |

兼容性仅运行本 base 的 C01 `test_contracts*.py`、A02 `test_a02*.py`、R7 `test_a03_r7_readonly_codec.py` 各一轮。不同于新 R8 的这些旧测试不扩张为原 P2 全矩阵。不得执行旧 36 静态矩阵、旧 examples main/session/conversion/oracle 驱动或 field-reset 专项。字段重置专项仍为 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，上述正常生命周期控制不许可重新设计该专项或其变体。

最多一次本轮局部修复，仅复跑实际受影响组，保留首次失败；超出范围或出现新的独立语义阻断后交付具体残余，不扩大矩阵、换大量候选或无限返工。N1 不能闭合时交真实最短失败位置和其余已完成实现，不补造后续成功值。原 P2 V01–V10/R01–R18 未被豁免；本轮审阅后再核定剩余明确项目，不能把这一条单动作链等同于全功能验收。

## 冻结交付

交付确切提交、可复现命令、产品实际导入路径、新 API/profile/schema/源码 pins、迁移差异、单动作完整产物与拒绝层级、独立目标效果次数、原始进程证据及限制。先提交合同/显式桥接，再提交 runtime/producer/链路；报告可单独提交，最终 target 必须覆盖全部。

每个实际父/子进程预登记脚本与输入摘要、argv/cwd、限时，保存原 stdout/stderr、PID、退出/timeout/alive；以不可覆盖的 run id 保留失败。所有自有进程结束、工作树干净后交 REVIEW。清单覆盖本轮新增/修改文件及日志，排除自身；旧文件保全用 Git blob 差分，不重复复制历史全集。产品正常 import，不依赖 examples/docs/Git 或 AST/exec 加载候选。

零网络、浏览器、真实平台、凭据/profile、OCR、模型、付费 API、A05 题22重放或书级提交。不推送、不联系 B/验收者、不更改调度 state。冻结后由调度核对再向原独立验收对话正式交接；I01 和真实平台恢复继续未释放。
