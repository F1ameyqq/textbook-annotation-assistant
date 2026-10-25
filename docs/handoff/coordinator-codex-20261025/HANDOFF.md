# A30 新 Codex 协调对话交接

本交接由旧协调对话 `01a166c5-f93f-76e3-baf4-a3545ccddebd` 应用户要求生成。用户要求新建对话继续推进；新协调派发开发与独立验收时，也必须分别新建对话。新协调、开发、验收均沿用用户指定 `gpt-6.1-sol / xhigh`。旧协调从本交接起停止产品、平台及新业务派发，仅完成新对话登记。

## 先读与当前事实

按次序读取本文件、`docs/coordination-state.json` 中 A30 当前状态、`docs/handoff/a30-to-codex-20261025/{HANDOFF.md,STATE.json}`，再读下列两份任务书。旧历史字段可能仍含“4题首次保存”或“构建运行中”；最新 handoff/status 优先，不重跑旧方案。

- 构建任务：`docs/tasks/A30-preexisting-tail-nodes-adoption-and-q12-retained-upgrade-20261025.md`，SHA256 `3132a89043f1dc6c0a9af9036d897d5cdd5ba0924353aafc4d44ab2d876fe5bd`。
- 评审任务：`docs/tasks/A30-adoption-completion-code-review-20261025.md`，SHA256 `1beb9933d9b30d8909d13cb55857a04c647bf5ab45664ad78d928974c1a3a4ff`。

书46007447《名校课堂八年级数学上册》，当前小节“2 一定是直角三角形吗”，总16题：

1. Q1—Q11 已正式/根接受。确切构成为旧4（1/5/10/11）+新增7（2/3/4/6/7/8/9），不是混入前一课时的旧9题。旧9另行保留。
2. Q12 原先一次POST/HTTP200有回执；原save状态UNKNOWN_NO_RETRY，原reconcile FAILED_NO_RETRY。当前保留读回完整，有限离线重建排除四个指定尾节点后严格比较PASS；这不直接替代程序业务接受。
3. Q13—Q16 平台记录已存在（orders39—42），保留数据中的正文、题框身份与候选匹配；无对应保存回执，来源归因UNKNOWN。必须通过ADOPT_EXISTING_MATCH采纳，永不重发、覆盖或删除。
4. 最新launch03-r1实际92.099秒、661GET/0POST，因整书42题vs预期38题停止，书籍身份一致；固定失败及本轮自身释放已正式/根接受，authority已spent1/remaining0。
5. 全16原生导出/展示NOT_RUN；CUSTOMER_READY=false；1800-a保持PAUSED。当前无激活的平台轮次。
6. 后续采纳/保留读回升级构建NOT_STARTED。2026-10-25本次只读核对时，三个计划产物目录均不存在。此前执行者约2小时无产物记录不是开发进度。
7. v1.1.4 ZIP存在且离线接受：`D:/1800/.local/releases/A30-v1.1.4-customer-local-win64.zip`，2724491字节，SHA256 `7344205c2698be60bc11c7bddddb8e9c92d137c4ccc653997ecbf378526972cc`。它基于Union20，尚不含待实现的采纳修复。原普通启动/UI有有限历史证明；不能据包离线通过宣称客户全流程完成。

本轮只读核对旧STATE中13个公开成员sha/bytes全部匹配；未跑业务/模型、未改产品/真实工作区。未知事实及历史失败不回填。

## 新协调需要立即收敛的两个实现/验收问题

这是旧协调代码与任务书分析得出的具体缺口，不是让用户再次决策：

1. 现有 `Union20/app/tools/customer.py:259` 普通“对账”按钮仅调用旧`reconcile`；新任务要求`reconcile_retained`并接入专用冻结launcher，却没有明确普通客户入口如何使用此能力。用户核心要求是客户无外部agent、无需技术JSON或逐课工程输入。请最小接入原UI/程序恢复路径，使程序从本机保留记录建立可验证恢复依据；不能只做本次专用救援脚本就宣称客户可交付，不另起界面/重构。
2. 构建任务第65/149行要求成功时store.resolve原save为COMPLETE；独立评审任务第25行及旧HANDOFF又写原UNKNOWN save op不得改写。先在新的有限任务补充中统一语义：原发送、UNKNOWN与失败对账历史必须不可丢失；当前业务结论可通过有完整历史链接的受控恢复更新。明确哪些原件不可变、当前操作表可怎样转换，执行与验收用同一约定。不要机械把两个互相矛盾的要求同时当门槛，也不要求用户逐项确认。

## 立即继续的工作

你是协调者。先读当前文件，拿到登记的实际新对话ID后更新当前协调归属；然后分别新建开发与独立验收对话（gpt-6.1-sol/xhigh），记录其实际ID，用户已授权你派发及持续跟进这些新对话。不要恢复额度耗尽的旧A30开发/验收对话。可先让验收方确认有限合同口径，正式代码/实际验收只接收固定输入；执行者不得自我接受。

开发应基于固定Union20 `D:/1800-private/a30-integrated-flow-r1-fixed-20261024-20`（manifest `19a3497ef23fa8e128d88b286f65267c5291a674ffe6fa0c68b07e34c6ad817a`），复用已有产品，不在D:/1800历史脏源码树里直接拼接。目标是最小实现绑定尾节点比较、Q12保留读回恢复、候选业务顺序的rect_id比较、ADOPT_EXISTING_MATCH，以及普通客户可用的恢复入口。旧任务中的有效绑定和反例可复用；只做变更必要验证，不重跑已有成功实测/OCR或无关全量矩阵。

可沿用尚不存在的三个新产物目录：
- `D:/1800-private/a30-integrated-flow-r1-fixed-20261025-01`
- `D:/1800-private/a30-adoption-completion-build-20261025-01`
- `D:/1800-private/a30-adoption-completion-launch-fixed-20261025-01`

拿到固定产品立即送新独立验收，打包/说明可并行。通过后由新协调绑定一次新唯一授权，指定一个新执行对话为唯一平台操作者：Q12只用保留读回恢复（0平台调用），普通produce采纳已有四题（0保存POST），然后一次full16原生导出/本地展示。旧失败/授权一律不重置。出现未知先对账，绝不盲目发送。实际成果固定后立即独立验收及协调接收；再交付含实际修复的阶段可运行包、一页说明、真实课时成果、限制及时间/介入指标。

不要等整个任务结束才送验，不停在离线报告，也不问“是否继续”。仅缺少不能取得的材料/身份/权限或真正用户决定时提问，同时推进不依赖它的工作。当前没有已知需用户回答的具体问题。

## 绑定与边界

复用原工作区 `D:/1800-private/a30-continuation-live-20261024-01/workspace`；已记录head `28274dab55969aa33d365ee2e4078c6ad58593929b589aa2a7581a3de20b1abc`，settings `56f07eb98e9712b662a13b016d9758c3d2c12109421a7b1f557a972e2b565f5f`，86操作；保留capture group `native/008bb17292dd4399a4d8e9d3f3351470`，9 runs/302成员。精确node/info/rect_id等见旧STATE与任务书，不猜、不重新取源。

新实际限定：save_posts_max0、retained_reconcile_calls_max1、readonly_reconcile_calls_max0、native_exports_max1、local_display_max1、official_bound_crop_downloads_max11、platform_contexts_max59、business_get_responses_max2997、1800秒+60秒释放。这些是上限不是必须耗尽。无旧成功保存、OCR、公式、付费模型、登录或旧轮次重放；证书/登录沿用既定精确约定。书级送审/对外发布不在本轮。

`.local/stages/`中的旧activation脚本均为历史，尤其旧协调准备过的`activate-full16-reconcile-once.py`绑定旧20/旧四题首存范围，已过时，绝不可直接执行。新授权只能基于这次新代码/新scope独立接受结果。

真实客户全流程耗时/人工数NOT_MEASURED；已有61次为AGENT_UI_TEST_OPERATOR审校事件。约97.87分钟UI服务区间含研发/等待，不是客户操作工时。完整课时阶段成功不能宣称整章/整书或任意书范围完成。

根仓库存在历史A03长路径删除及无关脏文件、.gitattributes修改；不得reset/clean/bulk-add或连带提交。旧文件和旧ZIP保持原样，最终业务接受可用外置sidecar。客户包引用本机venv/base/models/Edge/原workspace，非跨机器安装包。

新对话登记文件为本目录`registration.json`，由旧协调在create_thread成功后写入一次；之后旧协调不再更新共享coordination-state。新协调读取登记后接管它。自动化1800-a已核对PAUSED，不创建重复自动化、不恢复旧自动派发。
