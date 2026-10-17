# A03 P2-R5：登记遍历上下文与 target 绑定局部修复

2026-10-17。继续原执行对话 `01a145aa-2fea-7942-97f9-ad260acf4e30`，保留用户当前思考设置，不修改 thinking/model、不委派或新建任务。工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`，base `e608b54b973b14ff55dd2c4530153f5fe7c931f4`。调度消息给出包含本任务及归档报告的精确 workflow，按 raw Git 读取，不合浮动主树。

## 已确认缺口与输入

依据 [R4 调度决定](A03-P2-R4-bridge-registration-coordinator-decision.md)、[独立报告](A03-P2-R4-bridge-registration-review-report.md)和[R4 调度复现](../evidence/coordinator/heartbeat-20261017-1014/A03-R4-review-check.json)。独立报告 SHA256 `46d2d7aa43eb5a055827ecbacfe9db67ab959575098e52378a1fe9bfa1574049`，审阅清单 SHA256 `311f1fb987c111b21a92ddb7ea00ec36938f6d45be1b1d56dc64a13f59f555ac`；交付接口表 SHA256 `b57d0af5d72a03c4b16e6eeedc267bda50f1dfcf022728b1f107f5b158a22207`，仅有限设计接纳。

`R4-REG-GLOBAL-CONTEXT-01`：固定 R2 全局 evidence 扫描传入 `book=None`，在同一合法登记 prefix 再次执行真实消费者绑定谓词，从而拒绝正包。target 负控在同处被遮蔽，当前登记谓词也未明确比对 Snapshot.target_id 与 canonical target。Source/Snapshot 两个直接负控已在真实消费层拒绝。本轮只修这两项，不扩张 R17、产品 ABI、PRE 原生接纳或其他恢复功能。

唯一新增路径：`examples/a03/P2-R5-registration-context/`、`docs/evidence/A03/execution/P2-R5-registration-context/`、`docs/tasks/A03-P2-R5-registration-context-delivery.md`。旧 R2/R3/R4、src、tests、根依赖、公共合同、调度 state 与任何旧证据保持原字节。通过新覆盖层或明确版本的新静态入口实现最小差异，记录基类及新增源码 pins；不要复制历史全集、重造 profile 或改旧 pins。只读导入所需的固定静态校验器，不导入产品。

## 修复约束

1. 明确分离无消费者上下文的全局遍历与真实 Artifact/typed frame 的消费者绑定检查。全局仍核对所有 Resource 原字节/摘要/正式引用、唯一 EvidenceRecord ID、typed prefix 结构/位置及混合图，不能全局跳过证据，不能把 None 当任意书籍通配符。每个真实消费者必须继续在自己的 book/scope/声明集合下验证；相同资源被不同上下文复用时不能共享过宽的通过缓存。没有绑定依据的上下文不能伪造当前资格。
2. 对 plan_ref=null 的登记 frame，SourceBundle/PlatformSnapshot 保持确切四元组引用、正确 kind、同书/同 scope；已有 canonical target_key 的 platform_namespace/book_id/target_id 与 prefix/event/登记观察中的对应字段一致，Snapshot.payload.target_id 必须对应 target_id。只比较实际存在且有书面语义的字段，不向 Snapshot 捏造不存在的字段。保留独立 frame 声明及 Source 普通消费者闭包，不能把外层 scope A 与合法 frame scope B 强制混为一处。
3. 不修改 Schema、版本白名单或旧样例来制造通过，不删除 UNKNOWN、登记事件、普通 ref、Resource 或错误路径。原 R3 正式 EvidenceRecord 消费者闭包继续生效；静态修复不批准 oracle、1.3 产品接纳、native 或当前写入资格。

## 有界验证

同一个新完整 `Package.validate` 入口消费 R4 冻结四包，原 bundle、case 与资源字节逐项绑定 base，原件只读：

| 包 | 必须观察到的结果 |
|---|---|
| registration-positive | 完整入口接受；不是只验证局部 guard。证明全部后续闭包、DAG、hash 检查也已走到。 |
| source-binding-negative | 实际登记消费者层拒绝 Source 不一致，不能仅因 hash 错误。 |
| snapshot-binding-negative | 实际登记消费者层拒绝 Snapshot 不一致。 |
| target-tuple-negative | 在相应登记 target 绑定层拒绝，不能被无上下文全局故障遮蔽。 |

另只做三个受改动影响的直接防回归控制：原 R3 未声明正式证据 ref 的固定反例保持拒绝；一个全局证据 Resource 摘要损坏保持拒绝；一个 Artifact/Resource/frame 混合环保持拒绝。优先复用已有最小冻结输入，确需构造后二者只修改对应语义并记录变更，其余摘要/引用须自洽，不能靠更早的无关失败冒充目标拒绝。将这些输入固定在新目录，不执行旧 36 条矩阵或生成大候选。总计四个原包与三个防回归控制，不另搜边界。

先完成代码和静态差异检查，再做该七例；若发现局部实现错误，最多一轮针对本任务直接缺口修复并仅重跑受影响用例，分别保留每次结果。若出现新的独立语义矛盾、需扩大合同/产品范围或一轮后仍不能闭合，保留最短失败与具体原因后停止，不自行派生下一轮、不放宽预期。不得针对失败样例硬编码 ID/路径/结果。

## 交付与停止

交付确切提交、简短报告、全部新增文件清单（只排除清单自身）、必要 raw Git 输入索引、旧文件 mode/type/blob 保全证明、最小源码差异及统一入口、七例实际结果和错误层级、可独立只读复现命令。所有输出限新目录；启动前保存脚本/输入 SHA、argv/cwd、限时及 stdout/stderr，启动后记 PID，结束记退出/超时/alive，失败不得覆盖。

交付前核对清单与 Git 原字节、工作树干净、自有运行均结束。状态为 REVIEW，原验收对话随后独立复核；执行者不能自行记为接受。产品/DB/native/planner 运行或改动、网络/浏览器/平台/profile/凭据/OCR/模型/收费 API、安装、推送、联系 B 或验收者均不在范围。I01 仍不释放。字段重置专项保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不复跑、不变形、不委派或建议再测。
