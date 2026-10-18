# A03-T3：固定 K 后续派 D-M 完整实现包

2026-10-18，A 侧调度正式采用 D-M 并续派现有执行对话。**本轮只做 M1–M3 完整包，交冻结候选和释放证明后结束；独立验收再由调度续派。** 不新建对话，不把每个 helper 拆单，不进入 L/G/F 或平台。

## 固定依据与责任

- 执行：`01a14ccf-afa4-7260-a2a2-a47633772ae5`；独立验收保留：`01a14ccf-b8c3-7941-a80f-73594e7859a5`。续派明确 xhigh，model 沿用；旧 A03 两对话保持退役。
- 唯一工作目录 `D:/1800-worktrees/a03-t3`，分支 `codex/a03-t3-closure`，起点 **K=`62a023a1c88c20d884a61f38d1ad995b0908b74c`**。开始先核对 HEAD/clean；不得 reset、覆盖他人变化或切到浮动根目录。
- 计划 target=`765aef597a93fe36060fce65e17b22fe1c3408b8` 中 `docs/tasks/A03-T3-integration-plan.md` 与 `A03-T3-remaining-matrix.md` 为已接受的 C1–C4 及原 28 项映射；[调度计划接受](A03-T3-plan-R1-coordinator-acceptance.md)保留。计划里的“等待 T2/K/D-M”由本次决定解除，其余范围、计数与停止条件继续适用。
- T2 target=`699f748a124162b3118e3996c03757725daac363` 的固定 C12/H1 已由[调度接受](A03-T2-coordinator-acceptance.md)。T2 源代码与产品基线 P=`1330047dd29890dea0e433ff01b991f615bf78f4` 无差异；执行/验收均结束释放。旧缺失元数据和失败记录不是新的 T3 返工项。
- K 是上述已审计划分支加 **唯一** `examples/a03/T1-capture/capture.py`，来自 T1 `ed90664ab15afd1938725441e2bc86db7884f784`，raw SHA256=`3e07d56f409d8203c42f252f7a2900e902e31f56e1ff5fc7475335d33d0b042b`。[K 集成检查](../evidence/coordinator/heartbeat-20261018-0352/K-integration.json)证明仅该路径、raw index 一致、compile 通过、产品树不变及干净释放。仅这个依赖是 INTEGRATED，A03 整体没有集成。
- T3 执行者现为下列 M 范围的唯一产品及 A 侧私有合同/oracle/pins 整合者。公共 C01 行为仍严格，不能称 B 已确认。根依赖、其他执行者、B 排期不在权限内。

## 本次采用决定

**D-CONV=LEGACY_INITIAL_ONLY、fresh-native-only**。不新增 COMMITTED converter，不做 DB 迁移；R15 未证部分继续列明，不用它阻断 fresh M，也不标成通过。

**D-M=ADOPTED_FOR_IMPLEMENTATION**：采用已审计划 C2 的完整设计。确切 API 参数、事件枚举、schema 字段和实际摘要由本执行者在同一包中落实；在首次验证前以 `docs/tasks/A03-T3-M-adoption.md` 和候选提交固定。这是本任务内的技术实施权限，无需为每个字段再等调度采用。该记录不是验收结论；不放宽下述不变量。

1. 保留单题，扩大到最多三题、每题一张 32×32 PGM、stem/answer 两框；正常 planner 产生动作，不手写裁剪计划。五项真实比较、独立 oracle、原始图像/身份绑定保留。
2. 未尝试动作实现独立 logical readonly entry，绑定 book/ledger/registration、plan/action/digest、source/scope、store/session、owner/generation、H0、开始/截止、持久 read_count/state。没有 intent 就不借用 intent 预算；每 entry 最多三次真实读（含最后 currentness），读前耗次，失败/崩溃耗次、重开不复位。每读 2 秒、entry 8 秒、parent 60 秒和现有 gate/lease 上限不变。第三读在 gate 内，随后本地验证/CAS，不增加第四读或换 entry 循环。
3. journal 保留书级全局 sequence/prev 和期间其他 scope/plan 的合法控制事件；每个 scope frame 自有声明，普通引用仍同 scope。所有受控 dispatch/claim/takeover 尊重活动 readonly entry；超时/死亡只关闭 entry，不删除 UNKNOWN/hold。充分 ABSENT 才添加 NOT_ATTEMPTED+NOT_APPLIED 专用事实；不足只 progress/暂停，不能凑 receipt/Batch。
4. 活动 hold 下新增专用 `record_hold_candidate(...)`（签名按已审计划），使用实际 POST_HOLD 私有 PRE proof、creation anchor、完整前缀/依赖/授权/能力/政策、owner/generation/head、全书 pending=0，在 gate/事务中登记只读候选及资源。不得写 plans/actions、intent/permit，不动书 head、不清 hold、不 dispatch；普通 `_lease` 的 hold 禁令不变。
5. clear 只消费精确候选，在独立最终实际读之后核对 target hash/version，并在提交事务重查 owner/generation、hold、pending、expected head/CAS、fence/期限。失败保留 hold；成功仅 HOLD_CLEARED 与 verification_snapshot，效果为零。
6. clear 后旧 POST_HOLD/head 资格失效，不把它转封为执行资格。必须新 INITIAL PRE 的真实观察/五检查/admit、新 TARGET、planner、新 plan ID/creation anchor，普通 record_native_plan/run_plan 只消费该新资格；旧候选和旧尾不能执行。

上述 hold 登记矛盾与 unattempted stub 已有静态证据，直接在此包修复；不额外跑失败业务证明已知缺口。

## 唯一产品白名单

以下均相对本工作目录；新增支持文件只能在所列新目录。

- `src/annotation/quality/synthetic_precheck.py`
- `src/annotation/runtime/storage/__init__.py`、`native.py`、`holds.py`
- `src/annotation/contracts/a03_native/__init__.py`、`_closure.py`
- `src/annotation/contracts/a03_native/data/oracle.json`、`api.json`、`profile.json`、`adoption.json`
- `src/annotation/contracts/a03_native/data/schemas/prefix.json`、`basis.json`、`fact.json`
- 必要的 `src/annotation/contracts/recovery.py`，只为 M 的角色/闭包接缝，保留公共旧格式拒绝边界。
- 新 `examples/a03/T3-closure/`（唯一驱动 `run.py`、固定输入和必要 raw runtime-view）、`tests/test_a03_t3_closure.py`。
- 新 `docs/tasks/A03-T3-M-adoption.md`、`A03-T3-M-execution-report.md`、专属 `docs/evidence/A03/T3/execution/M/`。

planner/mock/targetcheck/native_quality、legacy CLI、根依赖与已接受 capture 工具只读。pins 只记录实际 bytes，不猜摘要、不覆盖旧 pin/history。若静态证据证明白名单不足，给出最小额外路径、具体接口和原因后停止依赖部分；不能以全局放松守卫代替。

## 固定验证上限和交付

一个 native 离线样例编排入口，不建通用 CLI/服务/UI。先做好静态自检、输入/资源/运行字节索引和进程记录器，再冻结候选启动以下命名场景：

| 场景 | 一次预期与预算 |
| --- | --- |
| M1 | 正常三动作一次；查询/重开/旧动作拒绝复用该起点，dispatch≤3。 |
| M2-sufficient / M2-insufficient | 各一次：A=APPLIED、B=UNKNOWN、C=NOT_ATTEMPTED；C 无 intent/permit/dispatch。充分/不足各独立目标，dispatch 各≤2，不足保留 progress/暂停。 |
| M3-new-plan / M3-final-drift | 各保留单题：首动作 not_applied 效果+unavailable 观察产生 UNKNOWN，一次完整 ABSENT；前支真实 hold→只读候选→final read/CAS 清除→新 INITIAL/planner 后有限继续；后支最后再变保持 hold，各 dispatch≤2。 |

总计最多 **5 个 fresh native 目标/业务起点、11 次 dispatch**；是上限，不为凑数执行。门调用/独立只读观察单列，不能遗漏预算。必要 guard 负控用同场景的真实产物做有限差量，不增加业务起点；原 T1 六例、T2 C12/H1、旧全集不重跑。报告列清原矩阵的 INHERIT / RUN_DELTA / WAIT，不把本包标为 28 项全过。

具名新场景只一次；新驱动出现错误最多一次有界纠正，只重跑失败项及未运行后继；第二次失败停止并保存全部证据，不换名字/阶段/委派继续。发现产品缺陷交确切反例，不改预期、不用 checker PASS 顶替业务事实。field reset=`NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。

使用已接受 capture 的同步边界，在适用的执行前、UNKNOWN 建立、释放、reconcile 前后、候选登记/清除前后、重新 INITIAL/执行及报告前后保留有因果意义的原件。具体阶段围绕本包不变量列入首次验证前清单，不机械复制无意义阶段；保留 DB/SQL、实际 receipt/fact/progress、effects、read_count、owner/keeper 及进程退出证据。禁止后台复制可变 DB。每次子进程登记 argv/cwd/输入/代码摘要、PID/start、实际退出/timeout、流或明确缺口；原失败不可抹去。

驱动从固定候选的 raw Git bytes 构建运行视图时，记录输入与实际 import 文件摘要，并核对 pins；不改 pin 来迁就 CRLF，不把复制当已验功能。所有 Git 调用显式 `-c core.longpaths=true`，Python `-X utf8`。无安装、网络、平台/browser/profile/凭据、付费模型/OCR、原视频、推送、书级提交或 A05 题22。

交付：精确候选和最终提交、只含白名单的差异、采用记录、复现命令与计数、完整证据 manifest（避免自引用/写前检查）、原件保全及限制、全自有进程/keeper/owner 释放、工作树状态。执行只能报 REVIEW/REWORK；本轮交付后等待调度，不自动跑 L/G/F、不管理 B、不唤醒旧对话、不委派。

## 已登记的独立验收门

现有 T3 验收对话先保持等待；执行完成、固定候选/证据及释放经调度核对后才续派。验收只审 M 差异和实际影响的旧 guard，沿用不受影响的有限证据；在自己的隔离固定环境复现上述命名场景（每方独立预算相同），核对 raw 版本/实际 imports、原件链、count/timeout/owner/currentness 和无额外效果。不得审浮动代码、代执行者修产品或扩增标准。通过后调度接受 M，再依依赖续派 L/G/F；本次不宣称 A03/I01 完成。
