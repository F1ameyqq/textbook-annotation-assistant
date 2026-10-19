# A08 固定候选1独立验收派发

2026-10-19。按既定A08任务续派登记独立对话；本轮不增加矩阵、业务授权或候选额度。

- 执行对话已固定交付并释放：`01a1527e-9649-7e53-8ee5-d25c06ce1683`。
- 唯一产品候选：`04762d78eae18449d7fcf3c0de20aec23b1f6881`；最终交付：`83f119fae8e84b30332ac50288b74049514c9b4e`。
- 独立对话：`01a1527d-a541-76c2-949a-00818e322499`。
- 独立目录：`C:/Users/ASUS/.codex/worktrees/a08-readonly-review/1800`；分支`codex/a08-readonly-review`；起始HEAD为上述最终交付。产品/驱动/说明原bytes已核对，不用主线HEAD冒充运行产品。
- 原执行任务：[A08-batch-readonly-reception.md](A08-batch-readonly-reception.md)；独立任务：[A08-independent-review.md](A08-independent-review.md)；固定输入：[A08-inputs.json](A08-inputs.json)。输入原件只读，SHA `b646fad9008e03e79a3dddfb4ead912d7ceadefbcee331c2e2af2415abf6f673`。
- 调度预检：[preflight.json](../evidence/coordinator/a08-preflight-20261019/preflight.json)。51成员525774bytes raw清单核对，另有清单自身；仅52新增路径，12491旧路径原对象保持，产品到交付不改代码/驱动/说明。12个子进程已join、作者对话完成释放；当前同号PID属于完成后新启动的其他进程，未终止他人进程。预检不是独立验收。

现在可开始原R0–R7独立验证。静态核对作者固定报告和清单后，使用自己的输出目录和独立构造负例，实际调用公共CLI/API。每固定候选原包完整接收一次，原有限11负例各一次；不复制作者结果当独立结果。可参考冻结配方，但必须独立核对原包输出、身份/HOLD/来源以及负例实际命中层。只新增`docs/tasks/A08-review-report.md`与`docs/evidence/A08/review/`（独立驱动可放该证据目录），不改产品或作者证据，不扩大随机矩阵。保留失败并标后续NOT_RUN；不擅自修产品重跑。原最多两产品候选中的第二候选未使用，只有原要求缺口才交调度有界处置。

ZIP实际24成员，23是外清单不含自身的条数，内清单9条。R6作者只观察结构计数层拒绝，独立判断是否满足原R6，不冒称已验证公式/续接内容语义，也不新增业务正确性要求。Q4有4个题片段含图题文字、1个答案来源区域；这些是接收坐标，不是获准执行框数。答案13、图形边界、题干/关系及逐题政策均未批准，B关系只作候选声明。其他3例无题对象仍HOLD。完整外部G/Check/plan未加载，Q1审批不转移。

始终0目标/计划/新C01执行对象/模拟派发/平台/付费模型/推送/B消息。不运行旧A07/A06/I01/A03或B脚本/SQLite，不联网取Q15或装依赖。Git始终`GIT_NO_LAZY_FETCH=1`与`core.longpaths=true`，不输出认证URL。

交付固定独立提交、报告、raw成员清单、输入/产品摘要、逐项结果及自有进程释放。主调度核证后才接受、集成；作者通过和本派发均不代表独立通过。
