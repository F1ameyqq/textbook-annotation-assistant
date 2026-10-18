# A03-R1 最终固定候选：差量独立验收

2026-10-18。沿用用户已批准的等价替代与独立验收，以及[最终有界纠正](A03-R1-final-bounded-correction.md)。只向已登记验收对话 `01a14da3-e8f3-7991-9b05-4a3fc38e2362` 续派一次，不创建新的修复任务，不再唤醒作者或旧 A03/T3。

## 固定对象和已有接受

- 最终交付：`19ab03c849bfab3dcde2dc86be37c59f3add1ebe`；唯一最终业务冻结包：`9992cd8aba10987d25dd0dc0d0874abec02b27ef`。
- 产品 `src/` 原 bytes 保持 `6097a06de937fee8876feccedf46920510850b83`；首包固定交付 `54e86adfaf144093a688b62fe0dad5190ceb2fa6`。
- 作者报告：`docs/tasks/A03-R1-final-correction-report.md`，raw SHA256 `40f030a5c4a1f538c35dcd196b7375f8b8f86d5029a59be41b8bb19d1dc0659e`。
- 作者新索引：`docs/evidence/A03/R1/final-correction/manifest.json`，raw SHA256 `22614eaeeaeb6ae6a14e9846e4ab552d3b9eed0ce5602c9dcbb044044e4ee405`；release-audit SHA256 `a8d71d2264f931225752dff017dff63e647fdd9109be291ceadb13fea3c89163`。
- 作者 completed、报告自有进程/keeper/owner 已释放；调度预检见 `docs/evidence/coordinator/heartbeat-20261018-0729/delivery-preflight.json`。原件、实际完成记录及释放仍须独立核对。
- [首包独立验收](A03-R1-review-report.md)和[调度有限接受](A03-R1-coordinator-acceptance.md)原样保留：M 五例、L1、实测依赖拒绝，以及 T1/T2 的原确切有限接受。本次不重跑 M/L1/G4、旧切点/owner 全集，不重新生成 legacy。

作者本轮是最终第二整包，不因仍有引用层限制而自动新增第三候选。原 L 两次驱动失败、旧原件和实际消耗保留。此次独立验收有自己的既定差量额度，不能将独立运行算成作者再试，也不能以验收名义修作者产品或候选后重跑。

## 本次判断与边界

核对原 V01–V10/R01–R18 的同一有限 coverage key。将已有接受、本次独立复现、作者固定证据、静态继承、结构/引用层拒绝和确切缺证分别列明。不能因某项早拒就声称后层已通过，也不能不对照原条款就把早拒本身升级为新缺陷；若原条款的必要行为尚无证据，准确定位该条，不扩大标准。

重点核对以下差量，全部只一次且以必要项为准，上限不要求跑满：

| 范围 | 本次独立验收上限和判断 |
|---|---|
| L2 | 自己先前已释放且身份仍匹配的 L1 continuation 承接另书 B，最多1新目标/1dispatch；A.pending=2、B.pending=0，A未决和目标不变。固定 B 单书与合法 B＋H-A1 多书表示各一次只读检查。不要求将冲突的 H-A1/H-A2 evidence ID 重封为同一个 registry，不把多书表示当 mixed-native 执行证明。 |
| L3 | 最多1新目标/2dispatch：首 UNKNOWN、一次 max_attempts=1 的 ABSENT、真新 INITIAL/PRE/TARGET/plan 后第二 UNKNOWN，旧解决与旧报告不能解除新未决。 |
| G6 | 按固定包复用 L3 第二 intent；同 intent/call 最多2次有效恢复、累计最多3实际读尝试，下一进程耗尽后0补读。不能以原通用上界尚有余量另建目标；不得重置期限/计数或借用 M2 entry 次数。 |
| L4 | 实际产物上的分叉、环、错原 receipt 三个既定差量，最多6门、0新业务。复核作者 fork 到 RESOLUTION_FORK、环/错 receipt 仅精确引用层的真实性与原要求是否已满足；不为追求更深拒绝无限变异输入。 |
| G1 | 只审本轮15个既定差量及其采用层，按原20差量/40门上限与已有 key 去重。缺 PRE/TARGET 等结构拒绝、能力 pure check_target、实际登记门分开，未变的依赖拒绝不重复。 |
| G2/G3 | 本轮最多7存储/格式负控、4角色/原转换中断调用；审真实 transaction wrapper 回滚、文件冲突、未知格式/目录绑定与 INCOMPLETE 拒绝。仅自有新负控副本，不能以此扩大为任意 I/O 原子性或 DB迁移验证。 |
| G5 | 仅本轮2个旧读/错误 head 的值层负控，零新业务。保留原正式报告和纯诊断的区别，不新增多书多头聚合要求。 |
| F | 新业务0，继承 M1/M3/L1 同 bytes 与实际消费者；只读 query/export 的双库前后摘要、采用链和28行映射。不得借 F 再 reconcile/publish/dispatch。 |

本次独立按已交付方案最多2新目标、3次dispatch，不为凑原通用上限追加场景。子阶段180秒/父240秒，原内层安全期限不变。读 timeout 是故障尝试，不作成功观察；动作调用、目标变更、回执状态分别计数。若有失败，保留现场并停止依赖它的后继，不静默延长或改后再跑；可完成不依赖失败项的静态收口。最终 REWORK/BLOCKED 交调度报告用户，没有自动修复续派。

## 隔离运行与原件保留

使用固定 raw Git bytes（`git -c core.longpaths=true`），不在作者或主目录产品上运行。保留自己此前独立目录 `D:/1800-worktrees/a03-r1-review-54e86adf` 的原固定导出、报告及静止 captures；仅将新候选代码/输入导出到新的隔离执行视图。

L2 只允许自己的已释放 L1 活源按原绝对身份合法承接，先核对其状态与最后固定 capture。不能借作者活源、重建 M/L1、清锁、迁移或复制后伪造身份。新输出使用新目录，旧证据不能覆写；可以在新验收包装中仅调整代码/输入/自有 continuation 的路径路由，并在运行前固定包装及真实依赖摘要，不能改产品、守卫、预期、计数或业务顺序来掩盖失败。若合法路由不成立，记录具体缺证而不造替代历史。

作者工作树的旧 M2 runtime 已作为获准 L1 live continuation 承接 B，因此 dirty 不能直接判未释放；其当前 live 文件不作为冻结首包证据。核对旧 Git blobs/静止 captures 未变，以及新 `continuation-files/` 与本轮 L2 最终 capture 的绑定。独立验收不访问或修复作者活源，旧 A03/T3/pending 库不打开、不恢复。

静止库复核只限新验收自有不可变副本，沿用 T1 capture 及 `mode=ro&immutable=1`，前后 hash 相同；不得修改正向历史或伪造中间时点。所有自有子进程等待回收、keeper stop/join、owner释放；pending/hold作为业务状态保留。

## 一次合并输出

只向主目录新增 `docs/tasks/A03-R1-final-delta-review-report.md` 与 `docs/evidence/A03/R1/final-review/`，不改旧报告/索引、调度 JSON 或 Git 索引，不提交。报告包含确切交付/驱动/产品/执行依赖、原28行结论、每族实际次数与到达层、失败/未运行理由、原始证据索引和自有释放。

结论可为既定离线范围 ACCEPTED，或准确的有限接受加 REWORK/BLOCKED。没有发现已运行路径的缺陷不能替代剩余必要证据；同时不追加平台/OCR/S01/B共同合同、任意规模性能、DB迁移或新标准。整体接受、本地集成、I01-A释放由调度核对后决定。禁止平台/profile/凭据/网络模型/付费/推送/B消息/书级送审/A05题22。
