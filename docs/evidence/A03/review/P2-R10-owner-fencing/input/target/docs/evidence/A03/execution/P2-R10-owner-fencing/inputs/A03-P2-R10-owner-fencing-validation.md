# A03 P2-R10：双进程占有权与旧代次有界验证

2026-10-18（Asia/Shanghai）。原A03执行对话 `01a145aa-2fea-7942-97f9-ad260acf4e30` 续接，原独立验收对话待冻结交付后续接。保留用户当前model/thinking，不委派。唯一base `bfd7fe896a7eee663ea8e0b6cf967548d8dd8f39`，执行目录 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800` / `codex/a03-runtime-recovery`；workflow以派发消息确切提交为准，不合并浮动主目录。

## 原要求与此次范围

[原任务](A03-runtime-recovery.md)V06及[原验收](A03-independent-review.md)R09要求两个真实进程竞争、owner/generation fencing。R9-R1已接受正常/重启/报告租约及D2明确未生效，见[收口](A03-P2-R9-R1-owner-lifecycle-coordinator-decision.md)。本轮只补下述两例，各一次；不重复四组、不重跑旧P2测试全集、不把整个V06/R09记为通过。

产品、schema、profile/adoption/pins、oracle/producer/verifier、依赖全部只读。沿用固定32×32单题两片段SYNTHETIC语言、同一书和注册scope。独立新路径双库，禁止复制旧成功/失败数据库为种子；必要helper正常import并记录实际路径/raw SHA，不做AST/exec裁剪、产品monkeypatch或SQL写业务状态。

## 两个案例

1. **C1 两个同时存活进程争抢同书。** 从正常创建的固定合成runtime/target开始，两个独立进程都完成初始化并到达显式ready/BEFORE_CLAIM屏障，再由父进程一次放行。使用既有claim接口及原屏障机制，不改5秒屏障期限、10秒lease、观察期限。成功者保持存活和合法租约直到另一个进程的结果已保存，不能因成功者提前退出而把串行接管误当竞争。要求只有一个当前ACTIVE owner，竞争失败具体受拒，记录双方PID、instance、owner/generation、事件、target fence和目标效果。双方完成竞争观察后才让持有者正常release。此子例可以没有业务效果；必须准确称为claim互斥证明，不据此冒称效果提交竞争全部覆盖。
2. **C2 实际换代后旧持有者从效果入口被拒。** 另一个全新固定单题case，进程A正常建立owner、合法PRE/目标检查/计划，并记录真实旧claim；尚未accept/intent/dispatch。A按支持接口正常停止自己的keeper并release，但保持进程与原store对象存活。收到释放屏障后，进程B正常open/claim同书、保持ACTIVE及keeper；明确记录generation已增加、target fence同步。然后通知原进程A使用原owner/generation向正常 `run_plan` 入口尝试一次。要求在新增intent/permit/效果前拒绝，B的owner/generation/ACTIVE仍有效；原A不能renew/release或覆盖B状态。记录实际包装错误和根因，避免把一个额外猜测的外层错误码当业务标准。B最后正常停止keeper/release。此例证明存活旧进程的过时资格无效；不宣称死进程租约回收、所有崩溃点或pending清除完成。

C1和C2都是新并发案例，不复用R9-R1数据库。C2旧计划必须由真实支持流程形成，不用手写计划或仅传一个随意generation来代替实际换代。进程间可用新驱动自己的文件/管道屏障；屏障必须先记录参与者已就绪，再释放，不能只sleep后假设交错成立。正常等待只允许有界轮询，不能更改产品时钟、PID判断、租约参数或直接私有字段伪造authority。

## 执行纪律与写入范围

先静态确认当前入口、helper及错误包装，再冻结本轮驱动/输入/预期。准备发现不可执行的前提时，给出确切路径和最小所需范围，停止该子项；不偷改产品。父进程上限90秒、每个业务子进程45秒，产品原2秒观察与5秒屏障上限保持。C1首个功能失败/超时后停止C2，保留现场。不得修改驱动后重跑功能组；单纯元数据/归档断言最多一次静态纠正并保留首错，不能借此调用产品。

仅新增：

- `tests/test_a03_p2_r10_owner_fencing.py`
- `examples/a03/P2-R10-owner-fencing/`
- `docs/evidence/A03/execution/P2-R10-owner-fencing/`
- `docs/tasks/A03-P2-R10-owner-fencing-report.md`

不改旧驱动、失败记录、报告或调度state。统一manifest覆盖报告、必要输入、完整驱动、真实导入、每个子进程登记/argv/cwd/timeout、raw stdout/stderr、退出/marker、状态/目标双库和正式资源；只排除清单自身。对os._exit等路径只记录实际存在的导入证据，不凭预设文件数量强行制造退出记录。只释放自有进程，保留他人文件。交付确切干净提交及复现入口，只记REVIEW，不能自记ACCEPTED/INTEGRATED。

## 独立验收门与后续

执行冻结后，由原独立验收对话在固定target的隔离目录复验这两个新案例各一次：核对真实同时存活与屏障、owner实例/PID/generation/target fence、失败方无效果、旧持有者实际换代和支持入口拒绝；核对正式SQL及事件、进程退出和原字节保全。主调度核验后只关闭上述两个子项。

全A03其他原覆盖缺口和I01仍待完成；本次不做多动作语言扩展、新计划执行、其他崩溃点或B版本映射。字段重置保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不运行、变体、委派或建议重测。禁止平台/浏览器/profile/凭据、网络、OCR、付费模型、安装、推送、A05题22和书级提交，不联系B。
