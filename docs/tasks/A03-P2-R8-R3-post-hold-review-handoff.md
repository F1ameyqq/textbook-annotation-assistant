# A03 P2-R8-R3：POST_HOLD 修复与有限负例独立验收

2026-10-18（Asia/Shanghai）。继续原独立验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a`，保留用户当前 model/thinking。不委派、不联系 B 或执行者，不改执行工作树。固定 base `58d8a64734271d15654bb00b03d760f0f3eccd10`，产品/驱动提交 `13c8a766124ac45a91fa3edfa22de7df1e033c3e`，最终 target `d9ed692db9ab8e9277f8ffd09e040451e8b8f65f`。

本轮核定 POST_HOLD 启动、当前性和事务接纳的同一修复，以及执行者已完成的有限 N1–N5。N7 已保留首次失败：旧入口确实拒绝 native target，但 VERSION_UNSUPPORTED 被包装为 CORRUPT，导致驱动的精确 code 断言失败。先判断该断言是否有合同依据，不预设必须修改产品，也不把失败改称通过。N6 与 N7 中断初始化分支未执行；本轮不补跑。

## 固定输入与交付前检

- workflow `b79b12fe6a82f9d88b6533b54aea016c4f67f60b` 的 [执行任务](A03-P2-R8-R3-post-hold-rework.md)，SHA256 `8bb76c2cd713ec9af5386f3dcd547f443bbef42d6d4d19fc603ef0fcf5bd6a29`。
- target 中 `docs/tasks/A03-P2-R8-R3-post-hold-report.md`，SHA256 `472ad5c6bdd2068ee178a36566d4d321aa4af0d9fe9fb7216ca26019c8182099`。
- target 中 `docs/evidence/A03/execution/P2-R8-R3-post-hold/manifest.json`，SHA256 `a094d8a73d68273afd58afe0f6d4f4b7ffb4e1a0be3e5721dfef803cf181f91c`；同目录 `process-release.json`，SHA256 `4d9b305aef3a5429005d496af68f36bf268d9ac4b68495c40e89b3e55c941dcf`。
- 同目录 `runs/N7/stderr.txt`，SHA256 `0c5670e4e345ad9c55020d83851ea971c0dbc4a865899b425c15241847706fc5`；`bounded-outcome.json`、`database-readback.json`、`control-database-readback.json`、`p2-coverage-map.json` 及各组原件均由 manifest 绑定。
- [调度交付前检](../evidence/coordinator/heartbeat-20261018-0242/A03-R8-R3-delivery-preflight.json)，SHA256 `86b34c1c0cf0cee47744710b9ebab89cc6b65e9ee6136af5a2122de0ee77df7c`：884 条清单加自身、885 个确切变化路径与磁盘/raw Git 一致；30,285 个 base 条目中 30,282 个原样保留，只有 native.py 和 profile/adoption pins 三个旧产品文件改变；34 组登记/启动/退出/输出核对完成，工作树干净，执行 turn completed。此为交付前检，未做功能验收。

产品来自 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800` 的上述固定 Git 对象。只导出必要产品、Schema/pins、固定输入和驱动原始 blob 到自己的隔离目录；旧历史用 mode/type/blob 差分保全。不要复制历史全集，不从执行树 import，不使用作者已运行的库作为独立成功前序。

## 有界核验

1. **静态修复与守卫。** 核对 native.py 的 `_pre_lease` 及三个衔接点，shared `_lease` 未改变。POST_HOLD 例外保留 ACTIVE/PID/instance/owner/generation、全书 pending、exact hold/head、注册/session/源/目标/观察、五项检查、预算/时限及提交前复查。INITIAL 和普通写入仍被 hold 拒绝，不清 hold、不产生 permit 或目标效果。检查 pins 只随源码摘要更新；禁止放宽合同、Schema 或版本语义。
2. **独立正链与有限负例各一次。** 静审 target 驱动后，在全新双库与新 run id 上按依赖运行 `R8R3LocalControls.test_no_hold_owner_and_pending`、`R8R3NativeBridgeTests.test_N1`、`test_N2`；前三项通过后再分别运行 `test_N3`、`test_N4`、`test_N5` 各一次。N2 必须承接本轮独立 N1 新库，不能借旧成功库。每组独立登记/限时，产品首个失败即保留并停止依赖组；不要修改候选、重跑失败路径或扩张控制矩阵。
3. **N1/N2 正式边界独立读回。** 用自己的 immutable SQLite 副本与 Artifact/Resource 原件核对 PRE ADMITTED、一次 permit/效果、真实子 exit87/屏障、原 UNKNOWN 和 null 原回执、终局 head 与晚到正式 receipt/progress 的绑定、独立新 POST/Batch；状态仍 PENDING/NOT_SUBMITTED。N2 两个真实 POST_HOLD 接纳须绑定同一当前 hold 和各自精确 head/观察；正常 release/claim 推进后的旧 generation/proof、真实 60 秒过期均拒绝，普通写入仍禁止、hold 未清、总效果仍一次。可以沿用驱动 120 秒父 watchdog 以容纳真实到期，不能改变产品 2 秒读取预算、deadline 或时钟。明确同一 hold 的两次接纳不证明不同 hold-id 替换或合格清 hold 已覆盖。
4. **N3–N5 实际拒绝语义。** N3 五个 schema-valid 且重算摘要的语义不匹配须检查具体 code；N4 缺少/序列化/他属运行/观察不产生 permit 或效果；N5 区分 1.1 历史 JSON 可读、R7 static 1.3 通过校验与拒绝 CURRENT native authority，不能写成旧 archive-validator 已通过。保留每组实际运行的资源/来源身份、确切拒绝和边界。
5. **N7 只读归因，不重演。** 对照原栈、persistent.py:335/342、ContractError 继承及既有书面合同/错误码测试，分别回答：实际是否拒绝了不兼容 target、是否改变原库或接纳旧身份、外层精确 code 是否已约定、包装是否有实际调用方错误分类影响。若只有新增驱动过精确，明确测试断言问题及合同依据，不臆造产品阻断；若确为产品缺口，列最小原因、影响和有界修复范围，不自行修复。保留原失败为 FAILED；严格区分已到达的 reopen/旧入口拒绝、未到达的初始化中断、未运行 N6。已在 N7 失败前启动的 N4 后完成，不误报为失败后重跑。此处不运行 N7 或变体。
6. **兼容、覆盖与释放。** 读取最终候选 C01 70、A02 52、R7 13 原始日志和相同源码摘要，不重跑兼容全套。对齐 34 组进程及 N1 预期 exit87、C01 预期拒绝、N7 真失败。逐项审查 p2-coverage-map 对原 P2 V01–V10/R01–R18 的已到达与未覆盖映射：本轮结论限已证事实，不把 N1–N5 自动等价为整个 P2。指出后续最小联调必要缺口和它们的既有标准来源，区分未来广覆盖项，不自行新增无限任务。

父/子进程先记录 argv/cwd、脚本/输入/产品摘要、PID、限时；保留原始 stdout/stderr、退出/timeout/alive 并全部 wait。检查数据库只读自己的副本（`mode=ro&immutable=1`、query_only），前后摘要核对，不打开执行原库。实际 import 路径和 raw 源码索引必须绑定 target；源码隔离复现不等同 wheel 安装证明。

## 交付

新增 `docs/tasks/A03-P2-R8-R3-post-hold-review-report.md` 与 `docs/evidence/A03/review/P2-R8-R3-post-hold/`。不要改旧报告/证据或根 state。提供输入版本/摘要、静审与独立各组实际结果、必要正式 SQL/Resource 绑定、N7 分类及依据、未覆盖映射、进程释放、只排除自身的 manifest。有限通过可以逐项注明；整个 A03 尚未接受/集成，不自行释放 I01。是否后续修产品或修驱动由调度据证据决定。

字段重置专项始终 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，禁止复跑、变形、委派或建议重测。零网络、真实平台、浏览器、凭据/profile、OCR、模型/付费 API、A05 题22重放、推送或 B 消息；书级送交仍人工。保留用户 A03 思考设置。
