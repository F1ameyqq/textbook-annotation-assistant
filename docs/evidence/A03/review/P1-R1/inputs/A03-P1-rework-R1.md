# A03 P1：R1 有界设计修订

日期：2026-10-17。状态：READY_FOR_REWORK。只由原 A03 执行对话修订设计；P1 未通过，P2 不授权，I01 不释放。

基线为 `2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9`，原设计 `6ac0256f05169570605fcb921a773ff2ae0f4aef`，原 workflow `a354f95f1d0b40a8f0847b57fa3978cac999e7a2`，A02 代码基线 `ec1b4defbfa3ec0f181d291106fb53313983e493` 不变。工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`、分支 `codex/a03-runtime-recovery`；不合并浮动主分支。

依据 [P1 独立 REWORK](A03-P1-review-report.md)，报告 SHA256 `df3faccf4be93335517a3f319fc356f3d568db44202e56a6a35e5153f54f2b8b`，清单 SHA256 `77c1eb16fbe362d41d21fe8f58ab57bc1d1caae3f9f376c36946cba10e1df92c`。主调度 [静态复核](../evidence/A03/coordinator/P1-R1/coordinator-check.json)核对 5 个确切 Git/归档输入，确认两项设计问题；没有运行恢复功能。[原执行任务](A03-runtime-recovery.md)和[独立验收标准](A03-independent-review.md)的全部 P1 边界继续生效。

## 仅修两项已确认问题

### P1-R1-01：给未尝试动作的充分 ABSENT 事实定义合法公开提交路径

最小状态为 A APPLIED、B UNKNOWN、C NOT_ATTEMPTED，旧计划已 INTERRUPTED。C 没有 intent/obligation；现有 `commit_action_result` 要求原 committed intent 与 RUNNING 游标，而 `commit_reconciliation` 要求原 intent/obligation。当前设计允许的 C 事实因此没有合法提交入口。

在新提案中选择一个明确公开入口或既有入口的严格分支，列出完整签名、责任、输入输出、失败码与事件。必须固定：允许的计划状态、当前 owner/generation、完整未调用事件前缀、真实新观察/独立充分 ABSENT 的核验、事实 origin、唯一性/CAS、不可变事实与索引的提交顺序，以及进度/完整回执聚合规则。

不得补造 intent、obligation 或 resolution，不续发旧 tail，不解除其他未决，不用调用方自报 JSON 取得权限。缺 ABSENT、证据陈旧、非完整未调用前缀、错误计划/动作、旧代次、重复或冲突事实都应有具体设计拒绝；状态不足时只保留 progress。新入口仅生产/提交核对事实，不能调用目标效果。

### P1-R1-02：修复资源内普通引用与消费声明的闭包

旧 `normal.json` 中 `receipt-design` 和 `progress-design` 未声明 fact 内的 `snapshot-action-result-1` 等引用；独立审查在其他正例以及 observation/prepared JSON 资源也发现同类遗漏。

逐项审计新修订案例中被消费资源的普通引用，按既有规则核对同书/scope、精确四元组与消费产物 input_refs；补齐声明，并沿依赖重新生成内容摘要、下游 refs 和清单。检查要覆盖嵌套资源，明确遍历/去重/循环拒绝规则；避免把仅能找到目标误作已经声明依赖。

新静态检查器加入缺声明、错摘要、跨书/scope 等邻近反例，分别记录形状、引用和预期语义层。不能删除事实、豁免资源内引用或放宽普通 scope 来让正例通过。保留修前固定反例，展示修前/修后静态差异；所有未来恢复行为仍为 EXPECTED_NOT_EXECUTED。

附带澄清独立报告指出的迁移身份表述：明确“new identities/digests”、跨版本命名空间和未来库索引键的准确含义，并与新映射样例一致。它目前是澄清项，不冒称第三项已证实功能缺陷；不扩展旧无 intent UNKNOWN 的解除权限。

## 新路径、原件保全与范围

只新增以下修订产物，原 P1 提案、样例、脚本、报告、执行/验收证据逐字节保留：

- `docs/a03-recovery-contract-v1-r1-proposal.md`。
- `examples/a03/P1-R1/`：独立可搬运的修订 Schema/API、静态检查器、正反案例及资源；显式标注 P1-R1 修订和未实施状态。
- `docs/evidence/A03/execution/P1-R1/`：修前反例副本、实际静态检查输出、命令和字节清单。
- `docs/tasks/A03-P1-R1-execution-report.md`。

原 `examples/a03/P1/` 和原归档只是历史输入，不能重写以消除本轮失败；新的最短检查命令应消费修订目录。候选合同版本仍是 A 内部未确认提案，需要版本或身份规则调整时在新提案明列兼容影响，不修改公共合同实现。A02 既有源码、所有 `src/`、`tests/`、根依赖、调度状态、A01/A04/B 范围保持只读。

零浏览器、网络、平台、凭据/profile、OCR、模型、数据库/恢复实现或功能执行；不跑 P2 的崩溃/并发测试，不把静态样例改名为运行证据，不推送或集成。

## 交付与终止条件

1. 冻结两项修订的准确设计选择、接口与正反案例；原 42 例的覆盖保留并在新修订集合明确映射，必要新增反例单列。
2. 记录最短静态复现命令、输入版本、输出层次、原失败及限制；作者自报检查不作为独立通过。无改动的整套 C01/A02 功能测试不必重复。
3. 提供干净冻结提交、设计提交、报告与全量 SHA256 清单，包含日志及实际忽略项；核对原文件字节及无待释放自有进程/会话。
4. 停在 P1 REVIEW，由原独立验收对话复审，再由主调度决定是否批准 P2。若不能在上述路径与边界内闭合，给出最小缺口和有界选项，不自行循环扩修或降低标准。

S01 真实来源完整性、根 Pillow 依赖、B 确认和真实平台恢复继续未解决。设计修订及通过均不等于 A03 功能 ACCEPTED/INTEGRATED。
