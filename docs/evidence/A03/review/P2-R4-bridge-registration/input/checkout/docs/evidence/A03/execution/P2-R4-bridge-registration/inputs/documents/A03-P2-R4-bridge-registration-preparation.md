# A03 P2-R4：桥接接口与登记分支的最小准备

2026-10-17。继续执行对话 `01a145aa-2fea-7942-97f9-ad260acf4e30`，工作目录 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`，base `87606b73e0754fa670491d9fb958a416c26bfe88`。包含本任务的 workflow 精确提交由派发消息给出，按 raw Git 读取，不合浮动主树。保留用户当前思考设置，不按旧任务单的 xhigh 改档，不中断或委派。

## 目标、输入与边界

依据 [R3 调度收口](A03-P2-R3-evidence-closure-coordinator-decision.md)、[R2 残余说明](A03-P2-R2-proposal-review-report.md) 与 [R1 已选语义](A03-P2-R1-proposal-coordinator-decision.md)，只关闭下一段实现前的两项缺口：R17 版本/资格接口说明，以及无计划登记 scope 的静态正向样例。

R2 profile `a03-p2-r2-static-2-PROPOSAL`、新版本 `1.3.0-a03-static-proposal`、旧版 `1.1.0-a-recovery-proposal` 和 R3 覆盖层原件保持不变。当前 profile、oracle 与原生功能均未采用；本轮不将 STATIC_UNIMPLEMENTED 改成可派发。允许说明所需的最小版本差异，不重新生成整套恢复规范、大候选或历史证据全集。

唯一新增路径：`examples/a03/P2-R4-bridge-registration/`、`docs/evidence/A03/execution/P2-R4-bridge-registration/`、`docs/tasks/A03-P2-R4-bridge-registration-delivery.md`。不得修改旧路径、src、tests、根依赖、公共合同、调度 state。允许只读查阅固定基线相关产品源码，不运行产品/planner/DB/native session。

## 1. 给出可直接评审的接口合同

调度已选择：为新 A03 profile 明确版本接纳与资格检查，保留计划算法和事实比较语义。不得降级/重封签成 1.1，也不得仅把 `==1.1` 改成任意版本白名单就认为兼容。

交付一张机器可读接口表及简短说明，固定每个源文件 blob/SHA；列出精确签名、输入/输出形状或已有类型、版本选择、exact refs、验证责任、拒绝条件，以及后续真正需要改动的文件/函数。至少覆盖：

- contracts 的 validate_bundle、assert_plan_ready、类型/版本选择，以及新 PRE 的私有运行接纳边界；明确静态结构合法、质量 PASS、当前写入资格三者不同。
- targetcheck 的 make_artifact、analyze_target 与其真实报告生产入口；新初始 Source/Graph/Snapshot/PRE 如何进入 TARGET 和 plan，版本由谁选择。
- planner 的 create_plan、verify_generated_plan、bind_plan_observation、snapshot_state_equivalent；生成规则保持不变，明确 observation_binding、prepared_before、progress_refs 及历史重建的完整引用闭包。接纳全包不能靠删 UNKNOWN 或删登记事件，历史派生视图不能成为当前写入资格。
- persistent mock 的 prepare_action、verify_prepared_action、snapshot_from_observation 与观察凭据校验；prepared/verified 身份、源/书/scope/target/session/hash/version 绑定，以及 runtime 对真实登记行、fence、当前头及持久计数的责任分界。

沿固定单题来源给出一条完整的预期调用/产物链：新 INITIAL 实际接纳 → TARGET → 真正 create_plan 的单动作 → intent/UNKNOWN 且原 receipt 尚不存在 → 只读恢复终局 head → 同 intent/fact 的晚到完整 receipt → 新 POST/Batch。当前只记录接口与可达条件，不手写一个 READY 计划充当真实生成，不执行该链。原有多头值模型不冒充可达历史，不扩成跨计划/scope 汇总。

附版本/资格决策表：旧 1.1 只读；新 1.3 静态值仅检查；未来确切采用版本与运行证明才可能派发；错版本/错 profile/无运行证明/旧 hold/错观察均拒绝。未知细节须列成具体阻断与建议，不能捏造当前已有 API。如果需要新的提案文件，使用独立名称并固定相对路径和 SHA，不覆盖旧 pins，不声称已采用。B 的业务合同确认继续未确认，本接口仅为 A 侧合成恢复路径方案。

## 2. 一个登记分支正包和直接控制

新增一份最小完整静态包，经固定 R3 `closure.Package.validate` 总入口消费合法 typed prefix，其中含 `plan_ref=null` 的 TARGET_DRIFT_HOLD 登记事件。SourceBundle 与 PlatformSnapshot 必须 exact refs、同书/同 scope；payload 登记标识、source/snapshot/scope 与 target 元组自洽，frame 自己声明全部所消费引用。保留完整包、资源、Schema/pins、事件链和摘要；不是只调用 scan 小函数或绕过普通消费者闭包。静态事件不伪称真实登记行/数据库事件。

只做三个直接负控制，分别破坏 Source 绑定、Snapshot 绑定、登记 scope/target 元组的一致性，且说明修改的语义和预期层级；需要重算摘要保证不是仅靠坏 hash 拒绝。若既有总入口无法在相应层拒绝，保留最小失败，提出局部规则差异后冻结；不在本轮修改 R3/checker 产品语义以追求全绿。新分支正包必须独立于旧大候选，只复用必要原件，不重跑 36 条旧矩阵。

## 交付、验证与停止

一份确切 commit、执行报告、全新增文件清单（自身除外）、必要 raw Git 输入索引、接口表、最小正包/三个负包及资源、实际结果/错误位置、源码摘要、最短只读复现命令。固定原件只读，所有输出放新目录。启动前保存 argv/cwd、脚本原件/SHA、PID、限时和 stdout/stderr，结束保存退出/alive；失败不可覆盖。只做接口静态检查及上述四个包检查，不重复无关测试。

交付前核对旧文件不变、工作树干净、自有同步运行均结束；交 REVIEW 后停止，由原独立验收对话评审。若正包构造与合同矛盾，或三负控暴露遗漏，报告确切失败与最小选择；一次范围内诊断后冻结，不自行派生下一轮或实现 native。

禁止产品运行/改动、DB 打开或查询、浏览器/平台/profile/凭据/OCR/模型/付费 API、安装依赖、推送、联系 B/验收者、采用 oracle 或解除 I01。既有字段重置专项保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不重跑、不变形、不委派。
