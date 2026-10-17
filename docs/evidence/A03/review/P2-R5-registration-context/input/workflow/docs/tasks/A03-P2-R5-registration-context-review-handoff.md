# A03 P2-R5：登记上下文修复独立复核

2026-10-17。继续原验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a`，保留用户当前思考强度；续发省略 thinking/model，不改档、不委派。包含本任务的精确 workflow 由派发消息给出，按 raw Git 读取，不合浮动主树。

## 冻结边界

- 只读执行工作树：`C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`。
- base：`e608b54b973b14ff55dd2c4530153f5fe7c931f4`；交付：`323013c4f0dbae75368e56db60147a8057368d1f`；执行 workflow：`5fcb2e0084c92c20092cac19e33619128ad86d54`。
- 交付报告 `docs/tasks/A03-P2-R5-registration-context-delivery.md`，SHA256 `86dd088bc109bf1243cd015d3c2f0dde9c52e2c01397574845766c7bb8208389`。
- 清单 `docs/evidence/A03/execution/P2-R5-registration-context/sha256-manifest.json`，SHA256 `2bb118b00b61f1c22109e3eed37777ee5c77cf88acc9c62911e515fac65dd2f7`。
- 新覆盖层 `examples/a03/P2-R5-registration-context/registration.py`，SHA256 `3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba`。
- [R5 执行任务](A03-P2-R5-registration-context-rework.md)、[R4 调度决定](A03-P2-R4-bridge-registration-coordinator-decision.md)、[本次调度前检](../evidence/coordinator/heartbeat-20261017-1044/A03-R5-delivery-preflight.json)。

调度已核对 204 清单项及清单自身共 205 新文件、70 份 raw Git 输入（含 9 份 workflow 文档）、28,113 旧路径 mode/type/blob 保持、干净工作树与 13 个自有运行退出记录及流摘要。完成 turn `01a1495e-bc63-7683-8f22-974e010c447a`；首轮混合环 case-07 退出 1 原样保留。前检仅字节/范围/释放检查，未导入执行校验器，不是功能验收。

## 本轮只复核三个结论

1. **上下文修复及 target 拒绝。** 审阅新层与固定 R2/R3 加载方式、源码差异和任务边界。独立确认全局无上下文遍历没有创建 book=None 的消费者、没有把 None 当通配符，仍读取全部 Resource、正式证据 ID、exact refs、typed frame 声明及图边；实际消费者继续按各自 book/scope/声明闭包检查，共享资源不能沿用过宽缓存。确认 Source/Snapshot 的实际绑定、已有 canonical target 字段、观察对应字段的比较，不把合成字段当 native 资格。R4 四个完整原包必须原字节消费同一新入口；原正包需完整返回，Source/Snapshot/target 三负控分别在对应语义层拒绝，不能只看作者错误码。
2. **两个直接防回归。** 固定原 R3 正式证据未声明反例仍在原消费者闭包拒绝；global-resource-hash-corruption 确实在无真实消费者的全局读取层拒绝。核对到达层与输入语义，保留原接受范围，不重跑旧矩阵。
3. **混合环控制残余。** 作者首版向封闭 legacy PLAN_ACCEPTED payload 增加 evidence，在 SHAPE_oneOf 提前拒绝；唯一修正版实际到 MIXED_CYCLE，但其 READONLY_ABSENCE_STARTED.sequence=8 的 initial_event_head 仍指旧 sequence=7 hash。独立检查修正版完整输入、重链/资源/Artifact 摘要、引用声明与该内部头差异，区分“混合环拒绝已观察”与“其余输入自洽的单故障控制尚未闭合”。不能只凭退出 0 消除残余，也不能将作者遵守一次修正停止条件写成越权。说明这是测试输入缺口还是直接证明了实现缺陷，给最小剩余范围。

允许对必要输入做 raw Git 隔离。先读加载器/入口源码；只定向输出目录或用只读模式，不改变 Package/Schema/判定/期望。独立重现七个冻结场景各一次：R4 四包、两个防回归、混合环的 repair-01；首版无效混合环以原始输入/日志静态核对，不重复运行。允许记录非修改式 trace 证明实际检查层，不引入新候选或修后测试。不得运行 prepare/repair 生成器、旧 36 矩阵、oracle 比较、session/conversion 或产品。加载源码与定向方式必须固定摘要。

本轮禁止修正 mixed-cycle 输入或 checker、重算并运行“修正版”、增加其他边界或自行启动下一阶段。判断不能由固定材料支持时写明具体缺口并停止。代码检查若发现与本任务直接相关的其他确定问题，只给源码与现有输入依据，不进行范围外试探。

## 输出、判定与释放

分别列出登记上下文/target、正式证据闭包/全局摘要、混合环控制的结论。可以对已证实项给有限静态结论；完整 R5 是否满足全部任务条件必须单独给 ACCEPTED_STATIC_LIMITED / REWORK / BLOCKED 及依据，不能把仍不自洽的控制计为合格七例，也不把前六项的证据作废。保留 R4 有限接口设计接受和此前 R3/SESSION-02/CONVERSION-07 有限静态接受；不重审无变化的 19 个接口，不批准产品 ABI、oracle/native/公共或 B 采用。

只新增 `D:/1800/docs/tasks/A03-P2-R5-registration-context-review-report.md` 与 `D:/1800/docs/evidence/A03/review/P2-R5-registration-context/`。保存必要原始输入索引、源码 pins、七次实际结果、argv/cwd/限时/PID/原始流/退出，以及覆盖报告和所有新文件的清单（仅排除自身）。不复制旧全集，旧归档字节不变。完成后给最短只读复现、限制及自有运行释放证明并冻结，等待调度决定；不提交/推送、改 state 或联系其他对话。

本轮无产品/planner/DB/native、网络/浏览器/平台/profile/凭据/OCR/模型/付费 API 或安装。A03 功能与 I01 不释放。字段重置专项保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不复跑、不变形、不委派、不建议再测。
