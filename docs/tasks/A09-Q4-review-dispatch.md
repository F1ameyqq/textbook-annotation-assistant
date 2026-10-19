# A09 第4题固定候选独立验收派发

2026-10-19。用户已批准本题内容、关系、四框政策和离线模拟。沿用 [A09执行单](A09-Q4-offline-simulation.md)、[独立标准](A09-Q4-independent-review.md)、[输入登记](A09-inputs.json)；不重问批准、不扩大范围。

## 固定版本与交付预检

- 原派发工作流：`0a9c634d160ac7b39f68a1fb3555f409dd408f49`。
- 唯一产品/实际运行候选：`29c82b0997be3080f53dfde2afbb1d7457b04197`。
- 作者最终交付：`439423ebf4277e3825aba24fed6f56546ef66a2b`。
- 作者对话：`01a153b4-0943-7dd0-92e2-859d26e49934`，已固定并释放。本轮1候选、1正常尝试/成功/dispatch、10拒绝零新增变更；成功额度已用完，不再向作者派业务。
- 原独立对话：`01a153af-3a4c-7a80-bb57-2e98af01dcd2`，准备已释放，本次仅续派固定候选，不新建重复对话。

[调度预检](../evidence/coordinator/a09-preflight-20261019/preflight.json)核对95清单成员/3,350,434 bytes及清单自身（SHA `5dae17727efd65e98ef9df94ab34abdc95c6faee1caa6b4bd3fc5156bd9eb541`）；新增共96路径，29,721条工作流旧路径mode/type/blob保持，运行候选29,737条路径在最终交付保持。102运行依赖成员与固定产品吻合。输入原ZIP、proposal、新A授权及原件引用均核对。两个原进程句柄退出记录有效，当前PID27428/38360均不存在。另有静态辅助范围检查PASS_TO_DISPATCH。预检不是独立验收或调度接受，调度0产品试验/0业务。

首次调度清单检查把第六项Git原件引用当磁盘副本，发生KeyError，已按两种明确记录类型纠正并保留[检查器记录](../evidence/coordinator/a09-preflight-20261019/checker-correction.json)。没有改产品、重新运行作者业务或消耗实现候选。

## 独立目录与运行身份

最终验收报告/证据目录为 `D:/1800-worktrees/a09-q4-review`，分支 `codex/a09-q4-review`，初始HEAD为作者最终交付439423eb。独立实际运行目录为 `D:/1800-worktrees/a09-q4-review-run`，detached HEAD固定产品29c82b09。两处均为新隔离稀疏检出并核对实际文件raw Git bytes，见[检出记录](../evidence/coordinator/a09-preflight-20261019/review-checkouts.json)。不得把最终交付或调度派发提交替代ExpectedHead，也不能改守卫放行。

运行目录可使用自己的 `.local/a09-review/inputs`、输出、budget和launch record。只读使用输入登记的原ZIP；从固定Git原件建立自己的输入副本，目标、负例、消费记录、PID及输出均归独立验收。不得复用作者目标/预算/输出作为自己的运行结果。作者固定报告和证据可从最终交付Git blob或独立报告检出中读取，不读取作者浮动工作树。

复现入口：在运行目录按作者固定报告执行 `examples/a09/stage_inputs.py`，然后调用 `examples/a09/launch.ps1`，ExpectedHead必须为29c82b0997be3080f53dfde2afbb1d7457b04197，Inputs/Output/BudgetDir/LaunchRecord全部使用独立新路径。原输入复制是A09必需只读准备，不运行A08接收CLI或旧完整矩阵。已有Python/Pydantic/Pillow够用，不联网安装。

## 本次允许的复验

只复验原单题四框正常一次，以及任务单原10次有限拒绝：缺授权、改授权、错Q1授权、替换ZIP、替换proposal、合法重封image→text、平台模式、错目标、陈旧目标、同计划重放。检查真实命中层和每次零新增变更；合法重封须证明通过C01后的类型语义门，不能用外hash拒绝替代。当前仅候选1一次正常试验；累计上限2正常尝试/1成功只在首失败、作者有界纠正、调度明确续派后才可进入第二候选。失败固定保留，成功不重跑补证、不改实现或追加矩阵。180秒/回收240秒外层，原内层不变。

结果必须与用户批准表逐项比较：Q/image viewer-10 [334,975,581,1077]；Q/text viewer-10 [100,1118,592,1193]；Q/text viewer-10 [99,1202,220,1235]；A/text viewer-173 [324,239,342,257]。恰好一题四框，答案13，无W/E。真实内存frame_projections读回image/text类型和文本，基础frame读回角色/坐标；不能只比实现计划与自己的输出。free_response保留fill_blank来源，题干同页cross_page=false。新A授权与B原HOLD、proposal false、未加载外部G/Check/plan同时保留，其他三例无题关系且HOLD。

独立确认完整新C01、五项实算PRE_APPLY、显式模拟TARGET、锁内写前复算、真实内存变更、独立读回和C01回执。来源OBSERVED，目标/计划SYNTHETIC、执行SIMULATED、A_INTERNAL_PROPOSAL/PROPOSAL_ONLY、NOT_SUBMITTED/PENDING保持，不声称B共同合同、平台OCR或复杂题型全覆盖。

只在报告检出新增 `docs/tasks/A09-Q4-review-report.md`、`docs/evidence/A09/review/`。输出固定独立提交、raw成员清单、输入/授权/运行身份、实际结果、各次消耗及原句柄进程释放。PID重用按对应进程创建和逐子进程结束时间区分，不终止无关进程。固定完成后仅建议PASS/REWORK并释放，主调度核证后才决定ACCEPTED和范围集成。

不改旧src/合同/schema/pins/根依赖/证据，不重跑A07/A08，不调用B脚本/SQLite/生产者、平台、付费模型或网络补件，不推送、不发送B消息、不处理题22。调度JSON与后续派发回执由主调度维护。
