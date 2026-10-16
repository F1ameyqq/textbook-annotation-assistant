# A03 独立验收准备

日期：2026-10-17（Asia/Shanghai）。状态：**WAITING_FOR_FROZEN_P1**。

本轮只整理验收方法、证据要求与待核点；未收到主调度正式发送的 P1 冻结提交。P1-01 至 P1-07 均为 **NOT_RUN**，没有设计验收结论。没有读取 A03 执行工作树、浮动分支或未冻结输出，没有运行恢复实现。

## 1. 权限、基线与依据

| 项目 | 本轮记录 |
|---|---|
| 正式标准 | [A03 独立验收](A03-independent-review.md)，以本表 workflow_commit 的 Git 原始内容为准 |
| 执行约束 | [A03 执行任务](A03-runtime-recovery.md)、[项目约定](../../AGENTS.md)、[调度规则](../coordination.md) |
| 技术语义 | [架构](../architecture.md)、[公共合同](../contracts-v1.md) |
| workflow_commit | `a354f95f1d0b40a8f0847b57fa3978cac999e7a2` |
| 代码基线 / A02 集成提交 | `ec1b4defbfa3ec0f181d291106fb53313983e493` |
| A02 接受交付 | `38aca9dcc8d027409b95193e9cc142c2336b76d3`，依据冻结的 [主调度收口](A02-coordinator-acceptance.md) |
| A02 既有集成检查 | 52 项 A02＋70 项 C01＋8 项登录工具检查，主调度记录通过；本轮 **NOT_RUN**，未重新执行 |
| P1 被验提交 / 样例摘要 | 尚未交付，均为空；不以当前 HEAD 或执行分支代填 |
| 准备产物唯一写入者 | 本独立验收对话；只写本报告和 `docs/evidence/A03/review/preparation/` |
| B 接口确认 | 未取得；任何 A 内部设计结论均不代表 B 已接受 |

已按确切 Git 内容读取正式标准、候选边界与 A02 子包入口，原始字节的长度、Git blob ID 和 SHA256 见 [读集清单](../evidence/A03/review/preparation/readset.json)。源码仅作静态接口盘点，未导入或执行。未将 `src/annotation/delivery/__init__.py` 视作入口：该路径不在冻结基线中。

[恢复合同旧准备稿](A03-contract-extension-preparation.md) 和 [S01 候选](S01-eligibility-preparation.md) 仍保留历史 `DRAFT_WAITING_A02` 等表述；旧状态和早期 A02 提交不覆盖正式任务已确认的接受/集成事实。本轮不修改这些原件，也不据其旧状态回退当前依赖。

开始时已有 `docs/coordination-state.json` 修改与 `mermaid-diagram.png` 未跟踪文件。准备期间还观察到 `docs/coordination.md` 相对 workflow_commit 有变动；本对话未写这些路径，也不读取浮动调度内容来替代正式基线。工作区观察见 [本轮检查](../evidence/A03/review/preparation/preparation-checks.json)，不能把共享工作区的其他变动归到本轮或自动清理。

## 2. 收到冻结交付后才执行的入口核对

以下全部 **NOT_RUN**，只是后续设计验收方法，不是向执行者追加派单。

1. 由主调度在本对话发送确切 P1 Git 提交、报告、SHA256 清单和设计/样例路径，核对 base/workflow、交付归属及无活动自有进程声明。缺失时保持等待，不自行轮询执行者。
2. 从该确切 Git 提交导出到主调度指定的独立临时目录，记录导出文件与 Git blob 的一致性；不切换共享目录、不从浮动工作树取样。固定后续检查的 cwd、工具版本和实际读取路径。
3. 只做设计阅读、JSON 语法、Schema/API/引用与正反样例的一致性核对；不运行新恢复代码、模拟效果、崩溃注入或 P2 检查。样例中的 expected 不记为 actual。
4. 独立反例另存 P1 验收目录，保留原件摘要，不覆盖冻结设计或样例。P1 只写 `docs/tasks/A03-P1-review-report.md` 和 `docs/evidence/A03/review/P1/`；本轮尚未创建它们。
5. 结论仅为 `P1_DESIGN_ACCEPTED / REWORK / BLOCKED`。关键语义、四组适配责任或必需样例不明确时不得建议通过；缺材料/无法核对与设计矛盾分别说明。
6. P1 设计建议通过后仍由主调度批准并续派；没有续派就不开始 P2。P1 不等于 A03 功能 ACCEPTED/INTEGRATED，不释放 I01、不集成、不推送、不修改调度状态。

## 3. P1-01 至 P1-07 方法与所需证据

| 编号 / 状态 | 核查方法 | 冻结交付必须提供的证据 | 不能接受的替代说法 |
|---|---|---|---|
| P1-01 / NOT_RUN | 核对 A02 接受/集成版本、base/workflow、唯一写入者及精确文件白名单；逐项定位 D01–D08 的具体决定 | 版本/路径表；候选 `1.1.0-a-recovery-proposal / a03-exchange-1` 完整 Schema；D01–D08 决策索引 | 分支名、旧准备稿状态或“接口后面再补”；提前修改旧实现 |
| P1-02 / NOT_RUN | 逐字段核对 WriteIntent、ExecutionProgress、ReconciliationResult；跟踪身份/摘要/精确引用和迁移前后字节 | 字段必填性、身份键、动作摘要规范、引用规则、生产/验证责任；归档/新解析/转换/拒绝矩阵；旧 UNKNOWN 示例 | 给旧无 intent UNKNOWN 补默认 intent、改版本重封签或删历史后称已保全/解除 |
| P1-03 / NOT_RUN | 按下节四组逐项比对 A02 现有公开入口与 P1 建议签名，检查最小适配与兼容影响 | 每组现有入口、建议签名、责任方、输入输出、失败码、精确文件及兼容说明 | 直接读写私有属性、复制 `_compare`/planner 或让 runtime 包含题型规则 |
| P1-04 / NOT_RUN | 静态走读 APPLIED/UNKNOWN/NOT_ATTEMPTED 多动作样例和恢复观察链，分开调用事实与效果 | 全 action progress；充分/不足 ABSENT 两组；无 receipt 路径；每次实际读回产生的新时间/版本及引用 | 无日志推定未调用；为凑齐报告伪造回执；旧快照只改时间；空列表/响应成功证明 ABSENT |
| P1-05 / NOT_RUN | 分开核对同 scope 公共引用链和当前库跨 run/scope 的书级完整性；审 owner/generation 和 session 边界 | 稳定书键、库身份/注册/扫描/事务规则；同书两 scope 未决样例；固定 SourceBundle/scope 及切换拒绝；过期 owner 的拒绝规则 | caller 自报空账本/旧 JSON 授予许可；放宽普通 ArtifactRef 跨 scope；重新 register 清状态 |
| P1-06 / NOT_RUN | 审整个输入/资产/证据链的全合成拒绝矩阵、S01 依赖和有限核对策略 | 真实/ORIGINAL/OBSERVED 各层拒绝；旧归档可读与新资格分开；S01/I01 边界；每 intent 每次恢复调用最多 3 次只读核对；具体超时与退出码 | 仅检查顶层 SYNTHETIC 标签；恢复成功消除 S01；超限重发保存；预留无限重读 |
| P1-07 / NOT_RUN | 将正反样例逐条映射 Schema/API、校验层、精确错误码与 D 决策；独立静态修改副本核对拒绝设计 | 下节样例覆盖表、相对资源/字节摘要、预期层/码、报告和统一清单；缺口与限制 | 只有作者正常样例、只说“应拒绝”无责任层/错误码、把 expected 当实测 |

本轮只确认方法已列入准备材料；上述 NOT_RUN 不转换为 PASS，也没有对尚未交付的设计给 REWORK/BLOCKED。

## 4. 四组 A02 公开适配待交项

现有入口来自代码基线的 `src/annotation/delivery/mock/__init__.py`；规划/目标检查规则仍以 `delivery/planner/__init__.py` 和 `quality/targetcheck/__init__.py` 为准。下表只盘点当前接口，尚未选定 A03 新签名。

| 组 / 状态 | 已存在的公开入口与静态限制 | P1 需固定的适配及证据 | 责任核对 |
|---|---|---|---|
| G1 会话初始化/恢复 / NOT_RUN | `MockSession()`；`register_target(bundle, snapshot_ref, *, asset_root, source_ref=None)`。内存初始化、固定 source 绑定、拒绝重复注册；无持久 reopen | 公开初始化/恢复签名、独立目标存储格式/位置/版本；固定每书 SourceBundle/scope；切换、损坏、换库和重复注册的精确拒绝；恢复不重建初始目标 | mock 管目标存储；runtime 管库身份/书账本；不通过 `_targets` 等属性搬运对象 |
| G2 单动作 dispatch / NOT_RUN | `execute(bundle, plan_ref, config, *, asset_root, receipt_id, created_at, faults=None)` 为整计划入口；效果 `_write`、相关事实 `_facts` 是私有实现 | 公开单动作接缝与输入输出；持久 intent 提交前/后、调用边界、效果后、读回后、receipt 提交后各注入点；提交失败不得效果；保留 A02 规划/比较规则 | runtime 提交 intent、验证当前 owner/generation 并编排；mock 产生独立效果；标记不证明已/未调用 |
| G3 独立读回/比较 / NOT_RUN | `read_target(book_id)`、`read_snapshot(book_id)` 返回防御性副本；`_compare` 非公开。目标 epoch 不变时 read_snapshot 返回旧快照 | 公开独立读取与比较签名/比较器版本；每次恢复的新观察时间/版本，绑定实际读回；MATCH/ABSENT 的完整范围和身份规则；部分/重复/截断/矛盾/失败读回 | reconciler 只比较，不能改库或发效果；目标/回执不同事务；不复制私有比较或用 expected 生成 actual |
| G4 历史/pending/ID 导入导出 / NOT_RUN | `action_log` 属性、`receipt_history(book_id)`、`is_paused(book_id)` 仅查询；`read_target` 含内部绑定/框投影。无完整公开导入、pending 明细、已用 plan/action 和 serial 的恢复接口 | 完整历史、pending、暂停、ID/去重、证据序号的公开导入导出签名/格式；精确引用/资产摘要；漏项、错版本、错摘要、旧 generation 的拒绝；同书跨 scope 和他书隔离 | runtime 当前库决定完整未决集合；公开 JSON 不授予写许可；导入不能清 UNKNOWN 或使旧动作重新可用 |

每组都需列现有入口、建议签名、输入输出、错误码、生产者/验证者、兼容影响与精确允许文件。没有公共接缝时应提交补充设计，不以 P1 验收者自行选 API 代替执行交付。

## 5. D01–D08 待核点

| 决策 / 状态 | 已由正式任务选定的边界 | 仍待冻结 P1 核对的具体材料 |
|---|---|---|
| D01 / NOT_RUN | A02 已接受/集成；保留已验收规则，公开最小适配，base/workflow 确切 | 四组 API 对照、精确文件白名单、兼容影响和责任；不改根依赖/父入口 |
| D02 / NOT_RUN | 三恢复产物和新版本候选；书账本独立于普通 ArtifactRef | 完整字段/必填性/身份/摘要；新旧解析入口；exchange/recovery/SQLite 格式版本与未知版本拒绝 |
| D03 / NOT_RUN | 旧原字节可归档/复现；新运行需真实本地新 intent；旧无 intent UNKNOWN 为 LEGACY_UNRECORDED 且不可解除 | 版本/迁移/跨版本引用矩阵；新文件/新摘要/映射；不补造历史、不改变旧 schema/封签；旧解析器拒新版本 |
| D04 / NOT_RUN | 事实和效果分开；充分独立 ABSENT 可 NOT_APPLIED＋NOT_ATTEMPTED，证据不足仅 progress | 所有 action 的事实/依赖证据；无 receipt 表示；BatchReport/POST_APPLY 的精确解决链绑定与新报告规则 |
| D05 / NOT_RUN | 当前库扫描同书全部 run/scope；owner/generation；首轮 target session 固定 SourceBundle/scope；每次恢复新观察 | 库身份/注册表/事件连续性/事务或 CAS/回收；效果前代次再核对；切换明确拒绝；新观察版本、时间和读回字节的绑定 |
| D06 / NOT_RUN | 全合成拒绝任何真实/ORIGINAL/OBSERVED 来源及证据；S01 单独阻断并保留 I01 依赖 | 各层准入/拒绝矩阵、归档与资格分离、新旧版本边界；不实现真实完整性生产者、不声称 B 接受 |
| D07 / NOT_RUN | 目标与 runtime 不共事务；跨进程独立读回；不复制 planner 或题型规则 | 公开持久 mock 接口、目标文件位置/格式/版本、逐动作效果日志、故障接缝、比较器版本；支持入口的保证范围 |
| D08 / NOT_RUN | 每 intent 每次恢复调用最多 3 次只读核对，耗尽暂停退出且不重发 | 单次/总超时具体数值、计数单位/失败次数规则、并发屏障、退出码及恢复条件；这些值由 P1 提交、主调度批准，本轮不代定 |

关键联动另核：解决一项不解除其他未决；新 UNKNOWN、目标/政策/能力/授权版本变化使旧许可失效；ABSENT 后旧动作不自动重发，需新快照、两阶段检查和新计划。框 MATCH 不能升级内容，仍为 PENDING / NOT_SUBMITTED，异常/跳过/未入图谱项及未知分母保留。

## 6. P1 样例覆盖与证据索引要求

以下均为待交样例类别，**不是本轮生成或运行的测试输入**。精确错误码和 API 名称须来自冻结 P1，不由本准备稿发明。

| 样例类别 | 应在设计中得到的判断 / 层 | 状态 |
|---|---|---|
| 新版本正常 intent、精确 plan/action/摘要 | 合同/引用闭合；runtime 才判断已提交 intent/资格 | NOT_RUN |
| MATCH＋原 UNKNOWN＋完整新观察 | 精确解决原项；原字节保留；旧动作不重发 | NOT_RUN |
| 完整 ABSENT＋新观察 | RESOLVED_NOT_APPLIED；新快照/检查/计划才可继续 | NOT_RUN |
| intent 无 receipt，效果前/后窗口 | 不捏造 receipt；独立观察可 ABSENT/MATCH | NOT_RUN |
| APPLIED/UNKNOWN/NOT_ATTEMPTED 混合，有/无充分 ABSENT | 分开事实和效果；不足只 progress；完整 action 清单 | NOT_RUN |
| 同书跨 scope 两未决，只解决一项；caller 自报空账本 | 同 scope 链可局部有效，runtime 当前库仍阻断整书 | NOT_RUN |
| 他书 UNKNOWN、合法多书包及两书互换 | 不误停当前书；保留 A02 R1 跨书隔离边界 | NOT_RUN |
| 旧无 intent UNKNOWN；旧样例归档/显式新转换 | LEGACY_UNRECORDED 不解除；归档可读不产生新资格 | NOT_RUN |
| 错书/目标/scope/计划/action/intent/receipt/摘要/版本 | 定位拒绝；普通引用不能任意跨 scope | NOT_RUN |
| 缺 receipt 引用对象、缺证据/资源或字节摘要不符 | 已声明引用必须存在；身份/资源门不得绕过 | NOT_RUN |
| 分叉/循环/矛盾解决链；已解决后新 UNKNOWN | 拒绝挑有利分支；新未决不能复用旧解除证明 | NOT_RUN |
| 部分/重复效果、矛盾/截断/失败读回、空列表 | CONFLICT/INDETERMINATE → STILL_UNKNOWN | NOT_RUN |
| 旧观察复用、只改时间、重复 observed version | 不满足每次恢复真实新观察要求 | NOT_RUN |
| 旧 owner/generation、换空库、遗漏 scope、重新 register | 支持入口失败关闭；不清账本/历史/暂停 | NOT_RUN |
| 真实/ORIGINAL/OBSERVED 混入来源、图像或证据链 | 全合成入口逐层拒绝；顶层换标签无效 | NOT_RUN |
| S01 未解决但恢复成功；直接改 VERIFIED/COMPLETED | S01 继续阻断；报告引用新解决链/新 POST_APPLY；内容/提交独立 | NOT_RUN |
| 核对尝试达到 3 次、单次/总超时 | 有界暂停和具体退出码，reconcile 零效果 | NOT_RUN |
| 异常/跳过/未入图谱、未知/零题分母 | 不丢范围，不把 0/0 写成 100%，不虚构动作 | NOT_RUN |

P1 包须至少含：`docs/a03-recovery-contract-v1-proposal.md`、`examples/a03/P1/` 的 Schema/API/正反 JSON 与资源、`docs/tasks/A03-P1-execution-report.md`、`docs/evidence/A03/execution/P1/` 的静态检查记录和统一 SHA256 清单。每例列文件摘要、适用版本、D/P1 编号、预期校验层及错误码；实际设计检查与预期功能行为分栏。所有资源相对路径可定位，旧样例/旧失败证据不得覆盖。

## 7. 本轮实际检查、未执行项和零操作声明

实际仅完成：正式文档/冻结 A02 接口静态读取；Git 基线与祖先关系核对；本报告及准备证据的 JSON 可解析性、本地链接、字节摘要、行尾空格和限定路径检查。详细结果见 [preparation-checks.json](../evidence/A03/review/preparation/preparation-checks.json) 与 [checks.log](../evidence/A03/review/preparation/checks.log)。复核辅助脚本只处理准备文档和 Git 静态字节，不导入业务模块。

明确未执行：冻结 P1 导出、P1-01–P1-07 设计验收、P1 样例检查/独立反例、全部 P2 R01–R18/V01–V10、A02/C01 测试复跑、历史证据全量逐字节复验、恢复/并发/重启/效果测试，以及真实质量/成本测量。均为 **NOT_RUN**；等待冻结 P1 或另行续派是原因，不计入通过数量。

本轮浏览器、网络、平台读写、凭据/profile 访问、OCR、模型 API、付费调用与书级提交均为 **0**；模型服务花费 **0**，真实质量/实际模型成本 **未测**。没有启动恢复目标/模拟任务、服务或后台进程，没有终止他人进程。Git/PowerShell/文档检查 Python 工具进程同步退出；退出时本轮遗留自有操作系统进程 **0**。仅有一名只读文本复核子代理协助盘点标准/接口，没有模型服务 API 调用，也没有向执行者、B 或其他聊天发消息；其结束记录另存 [范围声明](../evidence/A03/review/preparation/scope-declaration.json)。不把工具进程为零遗留误写成从未运行本地工具。

[摘要清单](../evidence/A03/review/preparation/sha256-manifest.json) 覆盖本报告、准备脚本、JSON 证据及日志，列长度/SHA256，排除清单自身。清单仅证明准备归档的字节一致性，不证明 P1 设计或 A03 功能已通过。准备文件未提交/集成；由主调度读取归档。

本轮到此结束，保持 **WAITING_FOR_FROZEN_P1**。后续等待主调度在本对话发送确切提交；不自行轮询、不启动 P2、不释放 I01。
