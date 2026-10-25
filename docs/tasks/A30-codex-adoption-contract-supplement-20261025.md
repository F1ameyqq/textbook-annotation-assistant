# A30 Codex 接任：恢复历史与普通客户入口统一合同

协调对话：`01a171f5-e73e-7452-982b-1885115e96ff`。本补充适用于本轮新建的开发、独立验收对话，均按用户指定 `gpt-6.1-sol / xhigh`。用户已授权创建、派发及持续跟进，协调独占修改 `docs/coordination-state.json`。

本补充优先于旧构建任务 `A30-preexisting-tail-nodes-adoption-and-q12-retained-upgrade-20261025.md`、旧评审任务 `A30-adoption-completion-code-review-20261025.md` 中冲突的状态、身份、范围和测试文字。两份旧任务原件不修改；精确绑定、零 POST、一次性、释放、独立验收要求继续有效。

## 1. 历史不可变与当前业务状态

原发送 intent、writer/receipt、UNKNOWN 输出 blob、原失败 reconcile 输出 blob、原捕获、历史 job head/event、固定失败报告和 spent authority 必须逐字节保留。原 `reconcile` 操作行保持 `FAILED_NO_RETRY` 且 output 不变。历史 UNKNOWN 不能被改写成当时已经成功。

成功恢复时允许使用已有 `store.resolve` 的 compare-and-set 机制，将当前 save 操作行从精确绑定的 `{state: UNKNOWN_NO_RETRY, output: 原输出}` 更新为 `COMPLETE`。新的接受 blob 必须包含 `previous_state: UNKNOWN_NO_RETRY`、`previous_output`，以及完整的 `retained_reconcile_provenance` 和原失败 reconcile 的 key/state/output。恢复有独立 `reconcile-retained` 操作与 job event，不创造新发送或新平台回执。这是当前结论更新，原发送和失败历史仍可重建。

因此旧评审第3项的“原 UNKNOWN save op 均不被改写”解释为原始 UNKNOWN 证据不得丢失，不能禁止上述有历史链接的当前操作表转换。恢复失败时原 save 行保持原 state/output；新恢复操作若已开始则记为 FAILED_NO_RETRY；前置链未通过不产生操作。重复调用不得重放，不能重新开放原 reconcile 或保存额度。

验证须同时比较原始 blob 字节、失败 reconcile 行、历史 head/event，及新接受记录的完整引用链。不得仅凭最终 COMPLETE 断言保留历史。

## 2. 普通客户恢复入口

在 Union20 既有 `app/tools/customer.py` 的“未知保存只读对账”与相应 CLI/共享程序入口做最小接线。普通客户只选择现有任务并执行正常对账，不输入技术 JSON、capture group、node IDs 或冻结 scope，不依赖外部 agent 逐课准备文件。

程序从本机已保留且可验证的任务/操作/捕获记录建立恢复依据。发现旧 reconcile 已失败且满足本轮 retained-upgrade 条件时，进入零平台调用的 `reconcile_retained`；共享程序逻辑与冻结 launcher 使用同一验证核心。不得仅让专用 launcher 可恢复，也不得在恢复材料缺失、歧义、hash 错误或已有恢复 intent 时隐式联网、重读、重发或回退到旧 reconcile。

自动建立 scope 仍须完整验证原 save/失败 reconcile、来源/书籍/候选身份、9 runs/302成员的摘要与成员 hash、重复成员相等、精确尾节点和候选全文/几何/分区/rect_id 绑定、发送窗口外时间规则；不能将任意额外尾题自动视为可剪除。实际运行仍使用本次独立接受的冻结精确绑定；普通入口能力用工作区副本离线验证，不触碰真实工作区。

新增允许变更：普通入口接线、最小共享恢复路由/本机依据解析、必要状态提示及对应离线测试/说明。不得另起 UI、大重构或诊断项目。独立验收的“仅六项变更”据此扩展到这项必要接线。

最低新增验证：普通入口在真实工作区副本完成 Q12 恢复且 transport 构造/平台调用均为0；缺失/篡改/歧义材料拒绝且0平台调用；重复动作保持一次性；原发送/失败证据可追溯。GUI 路由与 CLI 须调用同一经验证的恢复程序路径。现有未发生失败的普通 reconcile 行为须保持。

## 3. 冻结、评审与交付

开发从固定 Union20 私有目录复制到新目录；冻结后不得再原位修改，返工使用新后缀。开发不得自我接受。验收现在可检查本补充和固定历史依据，只在协调送达精确 manifest 后读取/执行新产品，不观察浮动作者树。

验证以本次差量、关键反例、真实副本及受影响 customer 测试为中心；复用字节未变部分既有接受，不重跑历史成功实测、OCR、公式或无关全量矩阵。记录实际命令、通过/失败/跳过及耗时，不用历史条数充当本轮通过。

开发可准备打包脚本、运行引用及一页客户说明；固定源码即交协调送验。代码独立接受后才制作含修复的新阶段包并单独送验，旧 ZIP 不改。真实 actual 未接受前 customer_ready=false。发布包是当前机器引用已有 runtime/profile/workspace 的阶段交付，不能声称跨机器或任意书范围验证。

## 4. 业务范围与后续顺序

本课已接受打印1—11；旧九题属于另一已交付范围。本课 Q12 原发送 UNKNOWN、原 reconcile FAILED；Q13—16 平台存在且来源 UNKNOWN，只读采纳，不保存/覆盖/删除。全16导出/展示仍 NOT_RUN。

离线固定成果 → 独立代码/冻结包接受 → 协调核验及一条新唯一 authority → 单一新开发对话执行一次 Q12 retained恢复(0平台调用) → produce采纳13—16(0保存POST) → full16原生导出/本地展示 → 固定实际独立验收 → 协调接受与阶段包/一页说明/真实成果和指标交付。

新实际上限维持 save_posts_max=0、retained_reconcile_calls_max=1、readonly_reconcile_calls_max=0、contexts=59、GET=2997、bound crops=11、export=1、display=1、1800秒+60秒释放；均为上限而非目标。现阶段未激活实际，所有旧 authority 继续 spent。不得运行历史四题首存 activation。1800-a 保持 PAUSED，书级送审和对外发布不在范围。
