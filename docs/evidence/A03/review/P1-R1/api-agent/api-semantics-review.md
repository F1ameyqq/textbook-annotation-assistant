# A03 P1-R1 API 独立静态审查

被验最终提交 `ca4fba4f505467228a8164c3999e0cecc54ffc4e`；设计提交 `095ed4aa18a56100ce3aabc4a0d6885ad37ab520`。只读取主验收提供的 Git 导出目录，未读取执行工作树。此文件是子审查意见，正式结论由主验收报告给出。

## 新 API 责任核对

`commit_unattempted_absence` 已为原 API-01 缺口定义独立公开路径。新 API `api-proposal.json:351-410` 给出签名、runtime.storage/公共比较器/受控 observer 责任、输入输出、失败码及原两条提交入口的兼容约束；`1275-1396` 给出完整协议。以下设计责任闭合，均只为静态核对，未来行为 `NOT_RUN / EXPECTED_NOT_EXECUTED`：

- 仅当前已接受、永久预留的 `INTERRUPTED` 计划/动作；不可由迁移、归档、caller JSON 或未使用槽位证明未调用。使用当前 `ACTIVE` owner/generation、固定 anchor/ledger/store/session/source/scope 和同书效果闸，允许保留无关 B UNKNOWN 时做只读事实采集。
- 完整当前库/跨 run 与 scope 的未调用前缀、固定当前头、禁止任意 intent/obligation/permit/dispatch 历史缺口；前后事务重核及唯一键，不因重提交获得幂等成功。文件先持久化，再同一 runtime 事务提交事件和索引；目标观察与 runtime 未宣称跨库原子提交。
- 两次受控实际新读，第一次产生专用只读 prepared_before，第二次独立比较；不经过要求 RUNNING/可写状态的 dispatch 准备入口。不删 `next_order` 或忽略合法前序变化。原每 intent/每恢复调用 3 次规则保留；本入口单独固定 2 读/无重试/单读 2s/入口 8s/父调用 60s，统一绝对期限。
- `UNATTEMPTED_ABSENCE`、非空 basis、全部 intent/obligation/resolution 引用 null；结果为 NOT_ATTEMPTED/NOT_APPLIED/ABSENT、RECHECK_TARGET、不可 replay。唯一键 `(journal_id,canonical_target_key,action_id)` 不含 owner/generation/registration；CAS 使用原请求头，发生漂移不换头重试。
- 只给 C 增加不可变事实，保留原 A/B、B UNKNOWN/pending/书暂停、原 INTERRUPTED 和旧 tail 不派发。所有动作有充分事实才聚合新完整 receipt；否则只 progress。不解除旧无 intent UNKNOWN。

四组 A02 适配仍完整列出现有入口、建议签名、生产者/验证者责任、输入输出、错误码和兼容影响：G1 会话及固定绑定、G2 intent/单动作/正常结果/新未尝试事实、G3 新观察与唯一公共事实比较器、G4 当前完整书账本和公开导入导出。D01-D08 原边界未被 R1 放宽；尤其保留原合成门、固定 session/scope、独立目标事务和有限核对。S01、根 Pillow、B 确认和 I01 继续未证明。

候选 profile 明确以最终 Git 和 Schema SHA256 固定，不靠不变版本字符串选最新 (`api-proposal.json:1240-1272`)。迁移 namespace=(schema_version,exchange_version)，未来索引含 namespace/book/scope/id/revision，kind/hash 为不可变唯一绑定 (`1427-1457`)；不把迁移当历史执行或解除 LEGACY_UNRECORDED 的权限。

## 唯一阻断：A03-P1-R1-PREFIX-01

分类为 **P1-07 成功样例与新准入语义不一致**，建议有界 `REWORK`。此项不否定公开入口已补齐，也不是 P2 运行失败。

`data/case-manifest.json:441-447` 将 `unattempted-absence-commit` 标为静态 PASS，并预期未来 `UNATTEMPTED_ABSENCE_COMMITTED`。成功例 `data/cases/unattempted-absence-commit.json:2988-2991` 声称完整未调用前缀并期望提交。该 C fact 使用 basis `data/assets/r1/73fc09e816fdca46c7873949ed5b0f56644d172012c763808d2a556f9dbfa31a.json:37-42`，正式指向完整 prefix 资源。

prefix `data/assets/r1/ac54edf82226784e4f40c4fb0fd48de8fc48bd3cbef24423e260f85f8968eb16.json:13-70` 自称 `from_sequence=1,through_sequence=5,complete=true`，但事件只有：

1. seq1 `PLAN_REGISTERED`；
2. seq2 A `WRITE_INTENT_COMMITTED`；
3. seq3 A `ACTION_RESULT_COMMITTED/APPLIED`；
4. seq4 B `WRITE_INTENT_COMMITTED`；
5. seq5 B `ACTION_RESULT_COMMITTED/UNKNOWN/INTERRUPTED`。

这份被标为完整的列表没有新协议必需的 `PLAN_ACCEPTED`、动作永久预留，也没有 A 已 APPLIED 前必经的 `DISPATCH_STARTED`/派发授权事件。`api-proposal.json:1278,1295` 明确要求真正 PLAN_ACCEPTED 至当前头的完整已提交事件前缀，包括授权与 DISPATCH_STARTED；`1041,1089-1090` 固定正常效果必须先消费 permit 并提交 DISPATCH_STARTED。

静态资源中没有 summary/节选标记，也没有指向另外完整事件记录的 Resource；basis 协议 `1346` 要求其绑定完整前缀。所有合成材料均非真实权限的声明，不能解释为可以从成功样例中省略其所声称已经完整的必要事件。12 个前提案例可分别假设未来受控当前库，但它们共享同一 C fact/basis 图，未另给能补足该成功前缀的完整库输入。`unattempted-incomplete-prefix` 只从这份列表删首事件，不能覆盖“保留序号范围和 complete=true、删去必经派发事件”的邻近情形。

原 42 例映射的 `partial-with-complete-absent` 也直接复用同一 C fact/basis/prefix；其 `NOT_ATTEMPTED_NOT_APPLIED_BOOK_PENDING` 正例同受影响。其他负例共享拟议输出事实图并不构成它们已成功提交；不将这种共享另算缺陷。

修复要求仅补齐成功例的完整合成事件/哈希前缀与必要预留/派发事实，连同 seq/hash/CAS/下游引用一致更新，并保留缺必经事件的独立拒绝邻近例。不得把“完整”改为 caller 自报、豁免真实库扫描、跳过派发接缝或扩大本轮权限。没有要求 P1 建库或产生真实事务证据。

## 独立实测和限制

独立脚本 `review_api_static.py` 不导入作者 checker 或 src，仅使用标准库读取 JSON/字节；16 项正例字段/摘要/profile 检查全部通过，核对 12 个 API 前提例的设计标记。已保存成功例、C fact、basis 和 prefix 原字节副本与摘要至 `counterexample/`，完整结果见 `independent-api-static.json`。这些是语法/字节/字段/设计语义定位，非任何恢复动作、拒绝、锁或事务的功能实测。

未调用模型 API、网络、浏览器、平台、凭据/profile 或 OCR；未实现或执行数据库/恢复/目标效果；未启动 P2、未修改设计实现或旧证据/调度状态。只启动同步有限 Python 检查进程，已退出，遗留自有进程 0。
