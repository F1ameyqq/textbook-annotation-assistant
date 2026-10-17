# A03 P1 独立设计验收报告

日期：2026-10-17（Asia/Shanghai）。结论：**REWORK**。

冻结设计存在两项必修问题：未尝试动作的充分 ABSENT 事实缺少合法的公开提交路径；正常及部分执行正例未声明其事实资源内部的快照引用。两项均为设计/API/样例不一致，没有运行恢复功能。P1 尚未通过，P2 不启动，不释放 I01。

## 1. 被验版本与权限

| 项目 | 确切值 |
|---|---|
| 最终交付提交 | `2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9` |
| 设计提交 | `6ac0256f05169570605fcb921a773ff2ae0f4aef` |
| workflow_commit | `a354f95f1d0b40a8f0847b57fa3978cac999e7a2` |
| A02 集成代码基线 | `ec1b4defbfa3ec0f181d291106fb53313983e493` |
| A02 已接受交付 | `38aca9dcc8d027409b95193e9cc142c2336b76d3` |
| 交接文件 SHA256 | `cfe84c0b12ded7e957c4b30e0cdcb12108d30ab7c6544f16b25d13da05171ed6` |
| 执行报告 SHA256 | `56f873291d0a60b376327b62eb12d032dc0c671cc55d90ce5582fe74d1724627` |
| 执行清单 SHA256 | `4988c1ce490ef62d0c1a019ac8f746166eb4dc0b595c3b29036bde38a6315950` |
| 提案 SHA256 | `fd1ddbf1d4252df50d7273ccd939e529129755847b3973a1b22938eb9d03e07f` |
| 隔离读取目录 | `D:/1800/.local/stages/A03-review-P1/2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9/` |

正式依据为 [独立验收标准](A03-independent-review.md)、[执行任务](A03-runtime-recovery.md)、[准备报告](A03-review-preparation.md) 和本次 [确切交接副本](../evidence/A03/review/P1/inputs/A03-P1-review-handoff.md)。原工作树只作冻结身份核对，不作为浮动设计输入。本轮只写本报告、`docs/evidence/A03/review/P1/` 和授权临时导出目录；未修改准备报告、设计/实现、旧证据、公共合同、根依赖或调度状态。

本轮从 Git 原始 blob 导出 8,142 个文件并核对每个 blob 身份及字节 SHA256。相对 workflow 基线只有 149 个允许范围内新增文件，7,993 个旧路径没有修改/删除；执行清单的 148 条长度/摘要与隔离 Git 字节全部相符，清单自身另外核对指定摘要。详见 [冻结核对](../evidence/A03/review/P1/freeze-checks.json) 和 [全量导出索引](../evidence/A03/review/P1/export-manifest.json)。149 个 P1 交付文件另保存在 `docs/evidence/A03/review/P1/inputs/frozen-P1/`，便于随验收证据搬运。

首次使用 `git archive` 导出时，一个旧文本成员与其 Git blob 不同，严格校验停止且该差异成员没有写入。原脚本/失败输出保留在 [freeze-attempt-01.log](../evidence/A03/review/P1/freeze-attempt-01.log) 及 `scripts/freeze_delivery.attempt-01.py`；随后使用 `git cat-file --batch` 原始 blob，逐一核对并保留已有正确文件后完成导出。该问题属于验收导出工具，不是 A03 设计缺陷。Windows checkout 与 Git 的换行表示不混算；本报告的被验输入始终为 Git 原始字节。

## 2. 必修问题

### A03-P1-API-01：未尝试 ABSENT 事实没有已定义的合法提交入口

对应 **P1-03 / P1-04 / P1-07、D04**。这是公开 API 生产者责任未闭合。

冻结提案第 74–76、100–108 行允许：`A APPLIED → B UNKNOWN → C NOT_ATTEMPTED` 后，C 若有完整独立 ABSENT 与未调用事实，可生成 `intent_ref=null / obligation_id=null` 的不可变事实，并按事实聚合完整回执。同时 B 的 UNKNOWN 已使原计划 INTERRUPTED，旧 tail 不得续发。

但 [冻结 API 副本](../evidence/A03/review/P1/inputs/frozen-P1/examples/a03/P1/api-proposal.json) 只有以下两条相关提交路径：

- 第 328–348 行 `commit_action_result` 必须有当前真实 committed intent、原 ACTIVE owner 和 RUNNING 游标，明确拒绝 INTERRUPTED / 重启后的正常结果补写。
- 第 1081–1089 行 `commit_reconciliation` 必须核对原 intent/obligation，恢复 fact 还须绑定合法 resolution。

C 没有 intent/obligation，且原计划已中断，两条入口均不符合。已交付 `action-fact-partial-not-attempted-absent.json` 第 4–13 行仍明确为 EXECUTION、空 resolution/intent/obligation。设计没有列出第三个入口或现有方法的精确 nullable 分支，为它指定事件、权限、事务和证据核验。不能由实现者届时补造 intent 或自行选规则。

[最小静态反例](../evidence/A03/review/P1/api-agent/not-attempted-fact-commit-gap.json) 保留上述状态、前提、入口不匹配及逐行依据；假设的 ABSENT 不是实际读回，功能结果 **NOT_RUN**。

返工要求：明确公开的未尝试事实提交入口，或既有入口的精确空 intent 分支；固定事件/事实 origin、计划状态、owner/generation、完整未调用前缀与新独立 ABSENT 的核验、唯一性/CAS 和回执聚合规则。不得补造 intent/obligation/resolution，不得续发旧 tail，不得解除其他未决。正反样例与 API/Schema/说明同步冻结。

### A03-P1-REF-01：正例事实资源的普通引用未由消费产物声明

对应 **P1-02 / P1-07**，并影响 D02/D04 的正例一致性。

提案第 106 行、API 第 984 行明确要求：资源内部普通引用保持同书同 scope、摘要一致并由消费产物声明。现成最小反例来自 `cases/normal.json`：第 3156 行的 `receipt-design.input_refs` 仅声明 plan 和三个 intent；其 `action_fact_refs[0]` 指向的 `assets/action-fact-normal-1.json` 第 27 行含 `snapshot-action-result-1` 的精确引用，回执没有声明它。第二、第三 fact 同样漏掉各自 snapshot。第 3320 行 progress 的 input_refs 也漏三项。

作者 `check_design.py` 第 265–273 行只检查资源内 ref 能找到且四元组相等，没有与消费产物 input_refs 比较，因此同一正例的作者静态函数仍返回 PASS。独立检查读取相同字节得到未声明引用；这不是运行了新 contracts 或恢复功能。

[最小引用对照](../evidence/A03/review/P1/schema-agent/minimal-normal-resource-ref.json) 保存原消费声明、完整第一条 fact 和缺失的确切 ref。[专项审计](../evidence/A03/review/P1/schema-agent/audit-summary.json) 在 normal、partial-without-absent、partial-with-complete-absent、original-unknown-preserved、recovered-report-binding 五个正例确认同类 fact 引用遗漏。[主验收独立审计](../evidence/A03/review/P1/independent-bindings.json) 还展开 observation/prepared JSON 资源，在 13 个代表案例中记录 40 处未声明引用出现，其中包含重复来源引用；这是同类闭包问题的出现次数，不是 40 个功能失败。

返工要求：按冻结声明规则补齐每个消费产物的资源内普通引用，并重新生成受影响内容摘要、下游 refs 与清单；静态一致性检查须比较资源内 ref 的同书/scope、精确四元组和消费声明，加入缺声明/跨范围的反例。原提交及本轮反例保持不变，不能靠豁免资源内引用、删除事实或放宽普通 scope 规则消除问题。

## 3. P1-01 至 P1-07 逐项结果

下表的“静态已核对”只表示设计条款/材料覆盖，不是相应未来行为通过。

| 编号 | 结果 | 依据与限制 |
|---|---|---|
| P1-01 | 静态已核对 | A02/base/workflow、唯一写入者、149 个新增路径、候选版本、完整候选 Schema 和 D01–D08 已列出；旧实现/合同/依赖没有改变。整体设计仍受下列返工项阻断 |
| P1-02 | REWORK | 三产物、精确身份/摘要、旧无 intent UNKNOWN 不解除与归档/转换规则已写；正例资源引用声明不闭合，见 REF-01 |
| P1-03 | REWORK | 四组 API 都有现有入口、建议签名、责任/错误码/兼容范围；未尝试 ABSENT fact 的公共生产/提交责任缺失，见 API-01 |
| P1-04 | REWORK | 无充分 ABSENT 仅 progress、新观察/事实分离与正常逐动作收口明确；充分 ABSENT 的未尝试 tail 缺合法事实提交路径，部分正例引用也须修正 |
| P1-05 | 静态已核对 | 当前唯一库跨所有 run/scope 扫描、书键、owner/generation、效果闸/fence、固定 SourceBundle/scope、切换拒绝与自报 JSON 不授权已具体定义；没有做事务/竞争实测 |
| P1-06 | 静态已核对 | 全链拒真实/ORIGINAL/OBSERVED，S01 单独阻断，I01/B 边界保留；每 intent 每恢复调用最多 3 次、具体期限/计数/退出码已定义，数值仍待主调度批准；准入/超时行为未执行 |
| P1-07 | REWORK | 42 个静态案例及分层预期已交；作者静态预期全部相符，但至少五个正例与自定资源引用规则矛盾，API-01 未有可闭合生产样例；不能据 checker 自洽认定设计通过 |

## 4. D01–D08 与四组适配审查

| 决策 | 独立静态核对结果 |
|---|---|
| D01 | A02 接受/集成基线和三个既有 A02 文件＋`mock/persistent.py` 精确白名单已固定；四组现有入口行范围与源码相符；API-01 修正前不建议批准整组实施 |
| D02 | 新 schema/exchange、runtime/target DB/application_id、ledger/action-fact 格式及三产物完整字段已定义；REF-01 使正例引用闭合不成立，须返工 |
| D03 | 新旧解析隔离、归档原字节、显式新样例转换、不迁移历史结果、旧无 intent UNKNOWN=LEGACY_UNRECORDED 且本版本不可解除均明确；下节列一项身份表述澄清建议 |
| D04 | 正常 ACTION_RESULT_COMMITTED、进度/事实/效果分离及恢复专用提交已定义；API-01 的空 intent tail 生产路径及 REF-01 的报告/事实引用须修正 |
| D05 | 固定 anchor/库身份、当前全书未决扫描、CAS、10s lease/2s续期、闸内 CLAIMING→独立目标 fence→ACTIVE、效果前代次复核及固定 session 范围均具体；实际持久化/锁行为 NOT_RUN |
| D06 | 全合成闭包、资源 origin、fixture proof、归档可读与资格分离、真实 S01/I01/B 未解决层明确；实际门禁 NOT_RUN |
| D07 | 独立 target/runtime 事务、独立效果日志/观察、A02 比较器只提取一次、新观察桥和六个故障注入点已指定；全部效果、重启及进程试验 NOT_RUN |
| D08 | 单读2s、单intent8s、整调用60s、busy1s、闸/屏障5s；读前持久计次，同 call 重启不重置，每 intent 最多3次；0/2/3/4/5/6/7/90退出码明确。仅候选设计数值，待批准、未计时实测 |

四组适配核对分别为：G1 create/open 分离与固定 source/scope；G2 prepare→持久 intent→单次许可→独立 dispatch→逐动作结果；G3 独立新观察、共享比较器与 PlanObservationBinding；G4 完整历史/pending/pause/去重/外部 ID 导入导出及当前库授权。原 UNKNOWN 的 mock、targetcheck、contracts 三处门禁有统一有效链消费安排；不读取私有属性搬运状态，不复制 planner/题型规则。专项结果见 [API/账本审查](../evidence/A03/review/P1/api-agent/static-api-ledger-review.md)。G2/D04 的未尝试事实缺口仍是明确的批准阻断。

## 5. 静态复现、独立方法与限制

作者命令仅在隔离 Git 导出运行，cwd 固定为本报告第 1 节临时目录；`PYTHONPATH` 指向该目录的 `src`，使用 `-B`。实际脚本路径、脚本摘要、Python 版本、完整 argv/cwd/超时/退出码与原始 stdout/stderr 见 [作者复现记录](../evidence/A03/review/P1/author-reproduction/results.json)。两脚本只导入标准库，不导入业务模块。

```powershell
# cwd 为确切隔离导出目录；只读静态检查
python -B examples/a03/P1/check_design.py
python -B docs/evidence/A03/execution/P1/check_api_design.py

# cwd=D:/1800；主验收独立静态公式与引用审计
python -B docs/evidence/A03/review/P1/scripts/audit_static_bindings.py

# 归档完成后的只读字节/路径/清单核对
python -B docs/evidence/A03/review/P1/scripts/finalize_review.py --verify-only
```

| 实际检查 | 结果 |
|---|---|
| 作者设计 checker | 退出0；42个案例静态预期匹配；所有语义 actual=NOT_EXECUTED |
| 作者 API checker | 退出0；94 JSON、4组、14个当前入口、18个组内接口、7个authority方法；errors=[] |
| 执行清单 | 148条长度/摘要与 Git 导出匹配；自身指定 SHA256 匹配 |
| 独立 stdlib 局部 Schema 断言 | 42/42形状预期相符，被引用 fact 形状均接受；不是完整标准认证 |
| 独立身份/摘要公式 | 13个代表案例的 intent action_digest、plan_dependency_digest、obligation 与 observation/snapshot 字段一致；发现资源消费声明遗漏，详见 REF-01 |
| 归档原字节 | normal原归档与指定A02源、旧UNKNOWN与固定旧样例逐字节相同；新旧混合闭包没有获准 |
| API 责任走读 | 确认 API-01，保存独立最小静态状态；未调用任何候选 API |
| 最终归档 | 文件/日志/输入副本/报告纳入统一清单；详情见 [最终核对](../evidence/A03/review/P1/final-verification.json) |

独立局部 Schema 评估不使用作者 SchemaChecker；为验证 checker 的盲点，仅另行调用其已读过的纯静态 `references/design_action_facts`，没有运行生成器或业务模块。完整标准 `jsonschema` 复核为 **NOT_RUN**：三个现有本地 Python 环境均缺包，未安装依赖或联网。该限制独立记录；本轮 REWORK 依据是上述可定位的设计矛盾。

子审查首轮人工查询曾错误假定 `frame_check_status` 字段，产生 KeyError，原输出保存在 [探索日志](../evidence/A03/review/P1/schema-agent/exploration-history.log)；纠正只读字段查询后完成审计。导出工具失败与查询脚本错误均不计入 A03 缺陷或通过数量。

迁移身份澄清建议：API 第702行写“new identities/digests”，提案第26行写不可变 ID/revision 不允许同身份不同摘要，迁移表七对映射却保留同 artifact_id/revision/kind 并改变摘要。请明确新身份的含义、跨版本命名空间及库索引约束，或同步表述/样例。正式任务只明确新文件/摘要/映射，本报告不以跨版本复用 ID 单独推定功能失败，也不把它作为第三项确定缺陷。

所有 P2 R01–R18/V01–V10、SQLite intent/receipt事务、真实目标效果/只读效果计数、重启/并发/崩溃、恢复分类/解除暂停、来源准入与预算超时行为、C01/A02/登录整套回归、真实质量/成本均为 **NOT_RUN / NOT_EXECUTED**。52+70+8只是既有主调度记录。手工 runtime_claim、账本及预期错误码不作为事务事实或实际拒绝结果。

## 6. 归档、范围与释放

[统一 SHA256 清单](../evidence/A03/review/P1/sha256-manifest.json) 覆盖本报告、149个冻结P1输入副本、独立输入/反例、脚本、输出及全部日志；自身排除，Git忽略但已入清单的日志单列。隔离目录全部输入另由 export-manifest 精确绑定，未删除或覆盖原输入/失败现场。没有自行提交、集成、推送、改调度状态或向执行者/B派单；结果仅在本验收对话返回。

执行会话释放依据为冻结报告及主调度提供的完成回合声明；本验收没有扫描执行者的操作系统进程。验收只启动有限同步 Git/PowerShell/Python 静态工具，两个只读文本复核子任务已结束；没有恢复/目标/后台服务、浏览器或长驻进程，未终止他人进程，退出时遗留验收自有操作系统进程/会话 **0**。详细声明见 [scope-declaration.json](../evidence/A03/review/P1/scope-declaration.json)。

浏览器、网络、平台、凭据/profile、OCR、模型服务 API、付费调用、书级提交、B任务及其他聊天操作均为 **0**；模型服务花费 **0**，真实质量/实际模型成本 **未测**。

交回主调度的建议仅为 **REWORK**：由原执行对话修订两项明确问题并冻结新提交，再在本验收对话复审。主调度批准前不进入 P2。S01真实来源完整性、Pillow根依赖、B接口确认及I01依赖均未由本轮解决。
