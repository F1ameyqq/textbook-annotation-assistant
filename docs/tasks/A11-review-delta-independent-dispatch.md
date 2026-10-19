# A11 R01/R02固定差量独立验收派发

2026-10-20。沿用 `/root/a11_live_runner_review`，依据[差量任务](A11-review-findings-correction.md)，本次只验两个静态缺口的固定纠正。原独立17项suite已完成，不复跑。

固定作者final `541d6b76cfa42655a224aeed0aab5a79a0b281aa`，实际运行产品/驱动 `8ff44619b955983cc84041525c7b9176d45660f2`。原作者基线 `c580ca63ada9e452fd5ee71e5272cf0d047d4574`，独立发现 `1522d1b612ba35f441a046706e46eabf97fe4a8d`。调度已核114成员/6,871,732bytes，manifest SHA `dba093ca1a7ea63f75fd6acff59a7e44f1693779cf2f6a72f4958b14de67a7e2`；4条允许修改、111新增、30,407保护路径原bytes保持，运行树至final未变。作者唯一六项PASS并通过原Popen等待退出、管道关闭；不以事后PID空代替自有句柄证据。

报告隔离目录 `D:/1800-worktrees/a11-delta-review`，分支 `codex/a11-delta-independent-review`，HEAD从作者final开始。实际运行隔离目录 `D:/1800-worktrees/a11-delta-run`，detached HEAD固定运行产品。由调度先建立no-checkout工作树，独立按必要路径从raw Git导出并逐bytes核对，避免全量旧长路径；缺少依赖先静态确定，不边跑边修，不安装依赖。报告HEAD和运行HEAD严格区分。

只新增 `docs/evidence/A11/review-delta-independent/` 及 `docs/tasks/A11-review-delta-independent-report.md`，不改产品/driver/fixture/旧报告/主调度JSON。固定driver接受的输出必须在运行目录 `docs/evidence/A11/review-delta-execution/independent-attempt-1`，随后原bytes归档到新review证据并记双边路径/hash。不可覆盖或复用作者输出目录。

独立先核原规则、来源+批准分类绑定、单选标签/明确多选门和新对账report的当前释放语义，再唯一运行原六项差量。D04–D06自行从固定Git归档建隔离副本，只readonly reconcile，核原15成员/UNKNOWN/NOT_RUN及发送占用不变，0新增send。需要区分字段真实算出与driver常量计数，不以计数断言替代源码/日志/产物核对。

本次最多1次六项差量，180秒外层，首意外失败停止并记余项NOT_RUN；不追加反例、不跑原17项、不恢复其他任务额度。固定后发生问题只交REWORK，不改产品或补跑。旧suite已证明且不受此次改动影响的行为可静态保全引用，新增分类导致旧输入缺少资格的有意兼容变化应如实说明，不冒称旧fixture现在仍可直接运行。

交确切最终commit、raw清单、源/输入/复制绑定、六项实际结果、静态判断及自身释放。通过只关闭这两项有限离线缺口，不证明真实wire/文本保存/平台事实/真实receipt。主调度核证与范围集成后另行结论。0平台/网络/浏览器/SQLite/模型/B消息/推送。
