# A03 P1 API / 书级账本静态复核

被验最终提交：`2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9`；设计提交：`6ac0256f05169570605fcb921a773ff2ae0f4aef`。

读取来源仅为指定确切 Git 隔离导出 `D:/1800/.local/stages/A03-review-P1/2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9/`，并读取主目录正式任务、交接及原准备报告作为标准。未读取浮动执行工作树，未导入业务模块，未执行作者 checker。此文件为主验收代理的专项输入，不是正式整体结论。

## 静态明确的设计

- D01–D08 与版本/路径白名单均列出；三个 A02 既有文件及一个新持久适配文件有精确允许/禁止范围。API 的旧入口行号与导出的 A02 源码相符。
- G1 区分 create/open，固定 target/session/source/scope，核对固定 anchor、库身份/格式并拒绝重建；跨 scope 归档未决留在当前库完整账本。
- G2 在每效果前持久提交 intent；书级效果闸、当前事务许可和目标 fence 闭合 owner/generation 检查到目标独立事务 commit 的窗口。正常逐动作事实经 ACTION_RESULT_COMMITTED 收口后才推进游标；只 APPLIED 前序满足依赖。
- G3 独立实际读取产生新 observation_id/read_sequence/实际时间；state hash 可相同但不能复用旧观察。公开纯比较器从 A02 的 _facts/_compare 提取一次。PlanObservationBinding 保持计划构造精确 snapshot 引用，并将新观察与正常合法前序效果的核验限定在未中断调用。
- G4 公开完整历史/pending/pause/去重/ID 的导入导出，导入不清目标或 UNKNOWN。公共同 scope 有效链投影与 runtime 当前全书跨 scope 扫描分工清楚；自报 JSON 不授权；外书 UNKNOWN 按 canonical target key 隔离。
- LEGACY_UNRECORDED 没有解除路径；MATCH/ABSENT 均不自动重发旧动作，旧计划重启即 INTERRUPTED，新流程重新取得实际快照、PRE_APPLY/TARGET、新计划及新动作身份。
- 每 intent 每次显式恢复调用最多 3 次，读前持久登记尝试，失败/崩溃消耗次数；2s/8s/60s monotonic 期限、未访问队列项、有限退出码有定义。全合成来源递归拒绝真实/ORIGINAL/OBSERVED；S01、I01、B 边界保留。

## A03-P1-API-01：未尝试 ABSENT 的已提交事实生产路径未闭合

定位与最小静态状态详见 [not-attempted-fact-commit-gap.json](not-attempted-fact-commit-gap.json)。对应 P1-03 / P1-04 / P1-07、D04。

`A APPLIED → B UNKNOWN → C NOT_ATTEMPTED` 后，原计划按设计为 INTERRUPTED。即使 C 已有充分独立 ABSENT 与完整未调用事实，设计允许的 `intent=null, obligation=null` C fact 也无法进入已列的两个提交入口：正常 commit_action_result 要求真实原 intent、RUNNING 游标；commit_reconciliation 要求真实 intent/义务和 resolution。正例 fact 仍标 EXECUTION/null resolution。没有列出的第三入口或 nullable 分支为它指定事件、权限与事务。

这不是已运行的恢复失败，而是冻结设计的生产者责任缺失。建议要求原执行者补明确公共入口或现有方法的精确空 intent 分支、事件和权限/证据条件，再冻结设计。禁止补造历史 intent、解除其他未决或续发旧 tail。

未发现另一项足够确定的独立关键 API/账本矛盾。方法实现、跨进程持久化、竞争、崩溃窗口、观察新鲜度、实际预算/超时、真实拒绝行为及效果次数仍全部 NOT_RUN / NOT_EXECUTED；以上明确规则只说明设计覆盖。

## 范围与释放

本专项仅同步运行本地 PowerShell 文本读取并写入这两个新证据文件；未运行恢复/目标/功能/模型调用，未启动后台服务或浏览器。网络、平台、凭据/profile、OCR、模型 API 操作均为 0；没有操作其他聊天或向执行者/B发消息。所有自有工具命令退出，遗留自有操作系统进程为 0。仅与当前主验收代理通过 collaboration 同步发现。
