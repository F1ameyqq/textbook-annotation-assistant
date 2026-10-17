# A03 P1-R1 独立设计复验报告

日期：2026-10-17（Asia/Shanghai）。结论：**REWORK**。

原两项问题的接口规则和资源引用修订已补齐，独立闭包检查未发现原遗漏继续存在。但新增成功例把不完整的事件清单标成“完整未调用前缀”，与该入口自己的准入规则矛盾，尚不能建议 P1 设计通过。此为静态设计/样例结论，没有执行恢复功能，P2 与 I01 均不释放。

## 1. 固定输入和保全

| 项目 | 被验值 |
|---|---|
| 最终交付 | `ca4fba4f505467228a8164c3999e0cecc54ffc4e` |
| 设计提交 | `095ed4aa18a56100ce3aabc4a0d6885ad37ab520` |
| R1 基线 | `2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9` |
| 原 workflow | `a354f95f1d0b40a8f0847b57fa3978cac999e7a2` |
| A02 代码基线 | `ec1b4defbfa3ec0f181d291106fb53313983e493` |
| 执行报告 SHA256 | `5121b6bfecf767ff496ce4a973d81df71ccd308cbebd9057f816d571b54cb301` |
| 执行清单 SHA256 | `c882542e9aefe1f413533b1350f6b81d20202f0bc37dd44b829d1eeb39f946b5` |
| 修订提案 SHA256 | `bec9ad4f89bc5f026d6a71c2214edd8d8d8eacec8a61ec8e3287e9e4b702e23e` |
| 隔离原始 Git 输入 | `D:/1800/.local/stages/A03-review-P1-R1/ca4fba4f505467228a8164c3999e0cecc54ffc4e/` |

正式依据：[R1 交接](A03-P1-R1-review-handoff.md)、[有界返工任务](A03-P1-rework-R1.md)、[独立标准](A03-independent-review.md)、[原执行任务](A03-runtime-recovery.md) 及 [原 P1 REWORK](A03-P1-review-report.md)。本轮只新增本报告、`docs/evidence/A03/review/P1-R1/` 与指定临时导出；没有覆盖旧 P1 的失败、准备或执行材料。

从确切 Git 使用 `cat-file --batch` 导出 8,923 个文件，逐文件核对 blob 身份、字节长度/SHA256；相对 R1 基线新增 781 个允许范围文件，8,142 个旧文件没有修改/删除。执行清单 780 条和清单自身指定摘要均匹配，设计提交后正式提案/样例没有再改。见 [冻结核对](../evidence/A03/review/P1-R1/freeze-checks.json) 和 [导出索引](../evidence/A03/review/P1-R1/export-manifest.json)。主目录旧验收/准备的 185 个文件另作开始/结束字节核对，均保留。原执行工作树仅用 Git 核对最终 HEAD/干净状态，未读取其浮动输出作结论。

781 个新增交付文件原字节另存于 `docs/evidence/A03/review/P1-R1/inputs/frozen-R1/`，包括制作失败现场；正式候选仅为其中 `examples/a03/P1-R1/data/` 和相应 API/说明，`attempts/` 不参与候选选择。[搬运复现](../evidence/A03/review/P1-R1/portable-check.json) 去除 PYTHONPATH 后在该副本独立运行，只读静态检查仍退出0。

## 2. 原两项返工复核

| 原问题 | 本次核对 | 结果 |
|---|---|---|
| A03-P1-API-01：未尝试 ABSENT 无合法提交路径 | 新公开 `commit_unattempted_absence(bundle, request, *, owner_id, generation, asset_root, observer)`；固定 INTERRUPTED、当前 ACTIVE owner/generation、同书效果闸/当前全库前缀、独立两次新读、专用只读 prepared、先文件后事务/CAS/永久唯一键及 UNATTEMPTED_ABSENCE_COMMITTED。原正常/reconcile 入口不放宽 | **接口规则已闭合**；但其新成功例的完整前缀证据不一致，见第3节，整体仍返工 |
| A03-P1-REF-01：资源内引用未由消费者声明 | 按消费者独立展开普通引用、任意层 Resource、正式 evidence_refs；验证字节/精确四元组/namespace/book/scope/自身 input_refs/混合环；同一资源缓存不能给第二消费者授权 | **原引用缺陷修复已静态确认**；原件保留，修前反例仍能被独立检出 |

新 fact 的 `origin_phase=UNATTEMPTED_ABSENCE` 与非空 `unattempted_basis`、空 intent/obligation/resolution/result.intent_ref，以及 NOT_ATTEMPTED/NOT_APPLIED/ABSENT 组合有明确 Schema/语义分支。EXECUTION/RECOVERY 的 basis 必须 null；新路径不使用会拒绝暂停/中断计划的派发 prepare/plan-binding。缺证据保留 progress，不补造 intent 或续发 tail，不解除 B UNKNOWN。单次新入口最多两次读、每读2s、整个入口8s并受父60s期限，原每 intent 每恢复调用最多三次核对保持独立。实际 API、读回和提交行为均未执行。

独立资源审计扫描 69 例，所有作者 `expected_static=PASS` 案例没有闭包违规；另外构造9个可搬运邻近输入，覆盖两消费者分别漏声明、多层正式 evidence Resource 的漏/补声明、错普通引用摘要、错资源字节摘要、跨书、跨 scope 和混合自环。独立判断与已检查过的作者纯静态审计函数相符，未用作者函数生成独立 expected。详见 [资源审计结果](../evidence/A03/review/P1-R1/ref-agent/resource-audit-results.json)。这确认声明和字节关系，不证明未来 contracts/runtime 的实际拒绝。

## 3. A03-P1-R1-PREFIX-01：新成功例的完整前缀与严格准入矛盾

对应 **P1-04 / P1-07、D04**。新入口自身规则没有发现权限放宽；问题在于其成功样例尚不能满足所定义的前提。

冻结 [API 副本](../evidence/A03/review/P1-R1/inputs/frozen-R1/examples/a03/P1-R1/api-proposal.json) 第1278、1295、1367–1370行要求：从不可变 `PLAN_ACCEPTED` 到请求的当前头核对完整连续的已提交事件/hash 前缀，包括身份预留、intent、许可发放/消费、`DISPATCH_STARTED` 和结果事件；不接受过滤的调用方导出或仅有 complete 标志。原许可协议仍明确目标效果前必须消费单次许可并追加 `DISPATCH_STARTED`。

新 `data/cases/unattempted-absence-commit.json` 的语义预期是成功 `UNATTEMPTED_ABSENCE_COMMITTED`。其 C fact→basis→`complete_uncalled_prefix` 指向实际 JSON 资源：

```text
assets/r1/ac54edf82226784e4f40c4fb0fd48de8fc48bd3cbef24423e260f85f8968eb16.json
```

该资源声明 `complete=true, from_sequence=1, through_sequence=5`，事件恰为（原42例映射的 `partial-with-complete-absent` 也复用该C fact/basis/前缀）：

1. `PLAN_REGISTERED`
2. A 的 `WRITE_INTENT_COMMITTED`
3. A 的 `ACTION_RESULT_COMMITTED(APPLIED)`
4. B 的 `WRITE_INTENT_COMMITTED`
5. B 的 `ACTION_RESULT_COMMITTED(UNKNOWN, INTERRUPTED)`

其中没有所要求的 `PLAN_ACCEPTED`，A 已 APPLIED 却没有此前必经的许可消费/`DISPATCH_STARTED`。文件也没有引用另一份完整事件资源或声明这只是摘要、另有严格前缀待核；basis 和 API 都把它绑定为完整 accepted-plan-to-head evidence。只有末项 head_hash，没有逐事件前驱/hash可核对。不能凭 `runtime_claim.complete_uncalled_prefix=true` 或 `design_only` 把这些遗漏当成满足前提。

[独立静态对照](../evidence/A03/review/P1-R1/api-agent/independent-api-static.json) 保存确切 case、fact、basis、前缀、预期码及规则定位；原字节也在冻结输入副本。两次观察/basis/事实字段和空 intent 分支的静态核对本身相符，问题集中在成功前缀，不扩张为两项原返工全部失败。

这是**成功样例与设计自定准入的语义矛盾**，不是运行了新入口后得到拒绝或证明数据库损坏。作者69/69静态通过只检查形状/字节/引用及局部字段，没有执行当前库的完整前缀语义核验，因此不能消除该问题。P1 正反样例必须能表达与规则一致的成功/拒绝前提；本轮不要求真实 SQLite 或实际恢复。

返工范围建议：保留本次版本及失败证据，只在新冻结修订中补足至少一条与严格规则一致的成功事件/hash前缀及其身份预留、许可消费/派发/结果事实，重算受影响的序号、CAS头、basis/事实/下游引用与清单；把缺接受/缺必经派发事件的输入列为明确拒绝邻例。若另有真正完整前缀，应明确资源绑定和摘要边界。不得把当前规则改为信任 `complete=true`、豁免缺失事件或补造 C intent/义务，不运行 P2 来替代设计修正。

## 4. P1、D01–D08 与案例覆盖

| 项目 | 本轮独立结果 |
|---|---|
| P1-01 | 静态核对：确切祖先、唯一修订范围、旧源码/合同/依赖保全、候选 Schema/profile 已绑定 |
| P1-02 | 原资源引用问题已修正；三产物/原UNKNOWN绑定/旧无intent不可解除等边界保持，仍无功能实测 |
| P1-03 | 四组原API签名保留，新未尝试事实入口的生产者、事务和错误责任具体；原入口缺口已补 |
| P1-04 | 两次新观察、无充分ABSENT只progress、B未决保留等规则明确；成功前缀样例未满足规则，**REWORK** |
| P1-05 | 当前唯一库全书跨run/scope扫描、书键/owner/generation/闸/fence、固定SourceBundle/scope、不能重register清状态均保留；仅审设计 |
| P1-06 | 全合成逐层拒真实/ORIGINAL/OBSERVED、S01/I01独立边界与有界核对保持；数值仍待批准，未测实际拒绝/超时 |
| P1-07 | 原42→新69的映射、形状与引用静态结果相符；新成功例前提矛盾尚未闭合，**REWORK** |

D01 的 A02 基线、四组职责和精确路径白名单保持；D02 新 fact origin/basis 及6份Schema摘要固定；D03 跨版本 namespace/索引身份已澄清；D04 新公开提交规则已具体但成功例仍须修正；D05 当前库、固定会话和受控并发门保持；D06 不消除S01；D07 独立目标/运行库事务和共享A02比较器保持；D08 原三次核对及新入口2读/2s/8s/父60s的期限分工明确。以上为设计覆盖，不是P2通过。

[独立映射/profile审计](../evidence/A03/review/P1-R1/mapping-agent/audit-results.json) 逐条核对原42例的旧/新文件SHA、唯一双向映射、预期层/码/静态分类和来源标识。[核心触发对照](../evidence/A03/review/P1-R1/mapping-agent/trigger-retention-results.json) 又直接抽取实际JSON的42项原语义扰动，42/42保留；初筛40项表示差异已归为衍生摘要/义务重算、未尝试事实及新观察、分支元数据、B暂停补齐，零未分类。此结果不消除第3节成功前缀矛盾。新集合为原42＋12个API前提例＋15个闭包/Schema邻例=69。修订选定 `proposal_revision=A03-P1-R1`、确切Git及6个Schema SHA256；不能凭未改变的顶层候选版本字符串猜最新版或混用旧P1形状。局部Schema独立评估覆盖69个包装及引用fact/basis，预期相符，不冒称完整标准验证。

迁移表已明确 namespace=(schema_version,exchange_version)，库身份键含 namespace/book/scope/id/revision，kind/hash为不可变绑定；同本地ID跨旧新namespace可映射，不许可同一身份覆盖，不产生跨版本普通引用或历史intent。原澄清项已回答；旧无intent UNKNOWN仍不可解除。具体差异归类和限制见 [映射审查说明](../evidence/A03/review/P1-R1/mapping-agent/notes.md)。

## 5. 实际复现与未执行项

作者两项静态命令只在第1节确切隔离目录运行，使用 `-B`、固定实际脚本路径和 PYTHONPATH；只导入标准库。完整 argv/cwd、Python版本、超时60s、退出码、摘要和原始 stdout/stderr 见 [作者复现记录](../evidence/A03/review/P1-R1/author-reproduction/results.json)。

```powershell
# cwd 为第1节隔离目录；静态检查
python -B examples/a03/P1-R1/check_design.py --root examples/a03/P1-R1/data
python -B docs/evidence/A03/execution/P1-R1/check_r1_design.py

# cwd=D:/1800；归档后的只读复核
python -B docs/evidence/A03/review/P1-R1/scripts/finalize.py --verify-only
```

| 实际检查 | 结果与边界 |
|---|---|
| 作者69例静态checker | 退出0，69/69静态预期相符，全部semantic_actual=NOT_EXECUTED |
| 作者API/Schema/映射checker | 退出0，165份正式候选JSON可解析，42映射、4组及局部字段相符 |
| 独立映射/profile/局部形状 | 42条字节/预期映射相符，6个Schema摘要匹配，69例及fact/basis形状预期相符 |
| 独立资源闭包＋9个另造输入 | 修前遗漏得到保留；修后应通过案例无闭包违规，邻例静态判定相符 |
| 独立API语义走读 | 原公开入口缺口已补；确认 PREFIX-01，保存静态反例；未调用任何候选API |
| 可搬运包复现 | 原字节复制781个新增文件，去除PYTHONPATH，在复制目录单独运行69例静态checker退出0 |
| 原件与归档 | 8,142旧Git文件及185个旧review/preparation文件保持；最终结果见 [final-verification.json](../evidence/A03/review/P1-R1/final-verification.json) |

完整标准 `jsonschema` 验证为 **NOT_RUN**，本机现有环境缺包，未安装或联网；独立局部评估不能代替完整标准认证。探索时两次错猜候选profile文件位置/工具cwd的只读查询失败已留 [exploration.log](../evidence/A03/review/P1-R1/exploration.log)。映射审计一次字段拼写错误和一次把同SHA资源改路径误判为触发变化的中间结果也原样保留，最终纠正后42/42触发匹配；资源审计首轮未单独固化Python退出码，第二轮用明确记录补齐，退出0。以上为审查工具记录，不计为交付缺陷或恢复结果。其余各子审计日志/脚本/实际输出均入清单。

全部未来恢复分类、新入口提交/拒绝、SQLite intent/事件/唯一CAS、真实新观察、锁竞争、重启/故障、效果/调用计数、全合成实际准入、预算/超时及P2 R01–R18/V01–V10仍 **NOT_RUN / NOT_EXECUTED**；无改动的C01/A02/登录功能套件未重跑。手工账本、gate/complete/observed字段、候选错误码和预期0效果不是实际事务/权限/读回证据。

## 6. 归档、权限与释放

[统一清单](../evidence/A03/review/P1-R1/sha256-manifest.json) 覆盖本报告、冻结输入副本、独立反例、脚本、输出、失败和全部日志；自身排除，实际Git忽略但纳入清单的路径单列，不丢日志。所有原件字节/摘要核对记录在最终核对中，未覆写旧失败现场。

本轮浏览器、网络、平台、凭据/profile、OCR、业务模型服务API、付费调用、书级提交、其他聊天/B任务/执行者或B消息均 **0**；模型服务费用 **0**，真实质量/实际模型成本未测。未修改代码/公共合同/依赖/调度状态，未提交、集成、推送或启动P2，未释放I01，未代表B确认合同。

仅启动有限同步本地Git/PowerShell/Python静态工具，三个静态审查子任务完成；没有恢复/目标/浏览器/服务或后台进程，未终止他人进程，遗留验收自有操作系统进程/会话 **0**。执行会话释放仍依据冻结报告及主调度的完成声明，没有独立扫描执行者系统进程。具体声明见 [scope-declaration.json](../evidence/A03/review/P1-R1/scope-declaration.json)。

建议由主调度将 PREFIX-01 交回原执行对话有界修订，原对话冻结后再复审；本验收不自行派单或轮询。P1设计通过后仍须主调度另行批准P2，S01真实完整性、Pillow根依赖、B确认及真实平台恢复均保持未解决。
