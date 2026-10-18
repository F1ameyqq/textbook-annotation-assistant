# A03-R1 最终整合纠正与既定余量

2026-10-18。用户已授权等价替代实施、必要有界修复与独立验收，现由调度依据[首包独立验收](A03-R1-review-report.md)和[有限接受](A03-R1-coordinator-acceptance.md)向现有 R1 作者一次续派。不是设计评审，不按 helper 派单。

## 调度裁定与不可重置的消耗

本次**明确分配 A03-R1 的第二次、最终整包候选**：首个完整交付为 `54e86adfaf144093a688b62fe0dad5190ceb2fa6`，这次仅修确定的输入接缝并完成其未闭合的原 L/G/F 范围。此分配依据用户给调度的有界修复授权，是本次整包收口决定；不以“只有一个 src 版本”推导自动剩余额度。

首包内 L 驱动 `d0438c998c9e161ae7d919e2ac83ce9075a56751`、纠正 `456740b4360c408efdc3165e6e98b136770613ab` 的两次冻结和实际失败全部保留。已经用过的驱动纠正额度不恢复；**不第三次从 legacy→L1 重跑 L 整包**，不重新生成历史。已耗作者 M=5起点/10 dispatch、legacy=首次失败1次+纠正2次、L1一次 reconcile/零dispatch逐项保留；独立验收5/10及L1另列，不冲销作者消耗。

这次只有一次最终冻结运行包。先完成普通静态准备、输入 bytes 检查和无业务预检，再固定 driver/input/执行依赖/预算；各新场景只一次。发生业务/驱动失败即停止依赖它的后继，不再改后重跑；仍可做无依赖冲突的静态和独立负控。无第三个整包候选、无新的自动纠正名额，不换名、重封同内容或换目录绕过。第二包失败或缺证即固定、释放、交 REWORK；调度再向用户交代实际结果。

## 固定起点、写入者和文件

- 唯一作者：`01a14da3-8798-75c0-af50-ca8fec19b48c`，沿用 `D:/1800-worktrees/a03-r1`、`codex/a03-equivalent-runtime`，从最终 `54e86adf...` 继续，不更换已验产品。
- 产品 `src/` 保持 `6097a06de937fee8876feccedf46920510850b83` 的原 bytes。当前没有已确认产品语义缺陷，不为 docstring、pins 或泛化重构改产品，免使已接受路径失效。若后续负控发现产品反例，保留准确输入/边界后交接，不自加第三轮产品修复。
- 写入仅原允许的 `examples/a03/R1/`、必要 `tests/test_a03_r1*.py`/`tests/fixtures/a03/R1/`，新报告 `docs/tasks/A03-R1-final-correction-report.md`，新证据 `docs/evidence/A03/R1/final-correction/`。旧执行/验收证据、报告、调度 JSON 不改写。
- 修 `deltas.py::setup` 选取冻结 raw-view 的同一输入。正确 PGM 是3579 bytes、SHA256 `1f82898615c67c676c532b17a8bd8e801c73eb6e7e2ba5a7f685bf1c3582cc7a`；不得改声明摘要去迁就 checkout CRLF。冻结前在无DB/目标的检查中验证完整输入资源路径/bytes与声明一致。
- 原 A03/T3 退役及失败 pending 库不打开恢复、清锁或迁移；独立验收目录不操作。只允许本轮 R1 作者自己已释放、身份不变的 L1 continuation 承接 L2，冻结证据副本保持原字节。若此 continuation 不再匹配最后固定状态，不重建 M/L1 绕过，交具体差异。

## 一份有限执行清单

先随本候选一次登记原 coverage key：原V/R子要求、输入族/预期、实际guard/consumer层、consumer与递归依赖执行bytes+pins、已有证据确切版本。逐行用 INHERIT、RUN_DELTA、WAIT_TARGET_OR_ADOPTION 或 REJECTED_AT_STRUCTURE；附于实现/报告，不另等设计审批。上界不是必须跑满的数量。

| 范围 | 本轮允许工作和上限 |
|---|---|
| M、L1 | 新业务运行0。沿用首包独立/调度接受；不得重造两份 legacy 或重做 L1，不重跑旧崩溃/owner全集。 |
| L2 | 采用 raw 输入后，在作者自己的合法 L1 continuation 同账本增加 B；A.pending=2保持，B.pending=0。B单书/合法多书两种表示各一次只读检查，B最多1新目标/注册、1 dispatch。若mixed-native消费未证明就保留该缺口，不给第二B或第二action凑数。 |
| L3 | 最多1新账本/目标、2动作、2dispatch。首 not_applied+unavailable得UNKNOWN，首intent一次reconcile(max_attempts=1)得ABSENT；真正新PRE/TARGET/plan产生第二UNKNOWN，旧resolution/报告不能解除新未决。 |
| L4 | L1/L3真实产物上的分叉、环、错原receipt三差量，最多6次门调用，0新业务起点，不SQL制造正向历史。 |
| G1 | 只补原plan/action/question/run/漏登记、graph/snapshot/policy/授权/能力和缺前置中未闭合的实际门。按同key扣已接受项，保留原20差量/40门调用上界，不重复bytes/pins/root/registry/consumer与旧proof。结构早拒绝不能计作runtime通过。 |
| G2 | 原族最多11副本/调用；已有错ledger/store、缺库/坏库四项先扣，本轮最多7且继续按key减少。仅自有新负控副本内必要的文件/SQL失败、未知runtime/target/交换格式和目录绑定；不重做旧N7/其变体或补旧缺件，不扩大DB接纳。 |
| G3 | 原四角色最多8读/门；只补尚缺角色/相关原转换中断。相同旧converter正支优先继承；确有影响才正支最多1，原中断最多1。零legacy新生成，保持LEGACY_INITIAL_ONLY、fresh-native-only和迁移BLOCKED，不新增COMMITTED格式。 |
| G4 | 新运行0。继承已核六槽和独立控制，receipt仅结构拒绝的限制保留；不补真实来源或S01。 |
| G5 | 原族最多7值/诊断调用，逐key扣已留存的分母/VERIFIED/denominator控制，不凭摘要猜剩余次数。只补旧报告消费、多头不同snapshot的既定值层，零dispatch；纯诊断和正式报告区分，PENDING/NOT_SUBMITTED保持。 |
| G6 | 优先复用本轮L3第二UNKNOWN；否则最多1新起点/1dispatch。同intent同call有效恢复最多2、实际读累计最多3；耗尽后新进程不补读，先到deadline如实停。非法0/4不重复，不借M2 entry的计数。 |
| F | 新业务起点0：正常=M1、新规划=M3、UNKNOWN恢复=L1。核对同bytes/消费者/依赖及原运行/核对/查询/导出入口，完成采用与28行映射；查询/导出只能只读，不补发reconcile/publish/dispatch。不能用F把缺证写成通过。 |

因此 L2+L3+G6 新native目标最多3、dispatch最多4；G6合法复用L3则2目标/3dispatch。与已耗历史分别累计，不重置总消耗。无未授权第二B、legacy再生成或M/F再跑。

## 期限、交付与验收

保留180秒子/240秒父外层预算，原read/entry/gate/lease/renew/PRE/currentness和核对次数均不变。静止取证沿用T1，SQL仅自有静止不可变副本。不要为了封存不足增加业务运行。

交确切最终提交、产品bytes未变证明、raw输入与实际导入、每族原消耗/本次增量、结果与完整V01–V10/R01–R18映射、失败/未执行原因、进程/keeper/owner释放和SHA索引。作者只交REVIEW/REWORK；冻结释放后，调度向现有独立验收仅续派本次差量，不重验未影响M/L1。整体接受与集成后才释放I01-A。

零平台/profile/凭据/网络模型/OCR/付费/推送/B消息/书级送审/A05题22。已有授权无需再次请求普通内部实现选择。
