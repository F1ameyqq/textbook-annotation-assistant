# A03 P2-R12-R1：冻结失败现场及 UNKNOWN 引用链独立复核

2026-10-18。复用原独立验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a`，保留用户手动设置，省略 model/thinking。A03 整体仍为 REWORK，I01 未释放。本轮只做一次冻结失败复核，不能将已知失败的 R12-R1 当成功候选重新运行 L1/U1–U5。

## 固定输入

- 作者：`01a145aa-2fea-7942-97f9-ad260acf4e30`；已完成并 idle。
- 产品/旧证据基线：`394fe51f5ed14c5ed312073a20faac0f5cbb9990`。
- 功能开始前代码、驱动及输入提交：`7694490ef25539d131b863bdcb2b21531c69dfae`。
- 唯一冻结交付：`6affc61d2ab0b1f0d96bb2497c5ae969ebaf1df2`；工作树已核对干净。
- 原修复 workflow：`05ba526cbd8575edc778016cf25cee13661a65c6`；[原修复任务](A03-P2-R12-R1-unknown-projection-repair.md) SHA-256 `ec269e977ed67276e5b4d1901c32c28acd75ba44870094fa0eb5fecf0cdc0076`。
- 本轮派发键：`A03:review:P2-R12-R1-failure:6affc61d2ab0b1f0d96bb2497c5ae969ebaf1df2`。本任务自身 workflow 以派发消息的确切提交为准。

下列文件从冻结交付读取 raw Git blob，不运行作者归档脚本、不改作者文件。表中 `E/` 表示 `docs/evidence/A03/execution/P2-R12-R1-unknown-projection/`。

| 文件 | SHA-256 |
| --- | --- |
| `docs/tasks/A03-P2-R12-R1-unknown-projection-report.md` | `457d0f85e491ae9cefa757475918c6766cd527179b99aa3b07de06611db5e133` |
| `E/manifest.json` | `b280ef782ee85f2c7f92485debc316a6bfae0902b078894e555df59afe904867` |
| `E/sealing/process-release-proof.json` | `6dd2da06a5212db39eaac95437dea5f44bc1e07072bbcb8a2ddc22f6cf1eced4` |
| `E/failure-summary.json` | `0c2050da2041d150bbdd871dc4521f322566d0154272f942f2609ff315ab2704` |
| `E/validation/author-01/processes/U1-execute/stderr.txt` | `1ccb41363eafc7980a8f602e084a4fb97519506b138ad0006cb495c859eb6d74` |

[调度冻结交付预检](../evidence/coordinator/heartbeat-20261018-0915/r12-r1-delivery-preflight.json) SHA-256 `92276ac38f2eae814d541e9fdd2680d3f807767d7195365c0d4e68b8c157db5b`。预检确认4个既有文件改动、320个新增文件、33028个受保护树项不变，323个manifest成员加自身raw字节与checkout相符，12份数据库原件的捕获摘要和23条历史进程退出记录对应。它未查询SQL或运行产品，不是独立功能验收。

注意输入边界：`examples/a03/P2-R12-R1-unknown-projection/inputs.json` 的109项索引由 `support.index` 对执行checkout的 `read_bytes()` 生成。其中5个原有源码的checkout CRLF与raw Git LF不同；预检逐项保存了两组摘要及长度，其余字节一致。不要把109项都写成raw Git摘要。独立记录此事实并判断对复核/未来可搬运复现的影响，不改旧索引或源码。本轮无需功能复现，因此不应为换行另开功能轮次。调度首次把索引全当raw Git的断言失败也已保留，随后纠正核对边界。

## 要独立确认的事实

1. 核对冻结身份、树项、4文件差异及pin范围。仅 storage基类和native子类增加窄报告策略；profile仅两项实现摘要变化，adoption仅profile摘要变化。作者称L1兼容对照完成，U1首次建立UNKNOWN失败、U1恢复与U2–U5未运行。核对首错、真实导入路径、start/completion/原始流、两条预期exit1及正常释放，不用当前PID扫描代替历史证明。一次归档元数据纠正及其首错要保留，不能混为产品重跑。
2. 从冻结目标导出12份阶段二进制到自己的新证据目录，先核对原始摘要，再以 `mode=ro&immutable=1` 查询这些自有副本；不对作者原件、运行目录或任何活动数据库连接SQL。核对 schema、事实、intent/permit/attempt、receipt/progress、事件/Resource、owner/lease和实际target效果，关联对应正式JSON与内容摘要。查询前后摘要应一致。分别比较 L1 的 before-build/unknown-established/after-release，U1 的 before-build/first-failure/after-release；这是逐库顺序复制，禁止宣称跨库原子快照。
3. 具体核实U1实际落盘后果：作者称UNKNOWN action fact已提交、intent仍PENDING且receipt为空、permit已CONSUMED、plan为INTERRUPTED，目标有一次效果且仅两片之一，无ExecutionReceipt/Progress/POST/Batch，native_report_reads为0；释放后owner为空且phase为RELEASED。以上均为待核对主张，不是验收预设答案。必须以真实库和文件得出结果，不能因抛异常就推断全部回滚，也不能把缺少正式receipt/progress的状态算作合法UNKNOWN建立。
4. 逐类限定静态检查整条调用链及相关合同，定位真正的引用闭包缺口。已观测栈为 `commit_action_result` → `_project_plan_locked` 的 `_append(receipt)` → native校验/registry context → `recovery._legacy_projection` → `validate_bundle`；错误 `$.artifacts[10].payload.unresolved_issue_ids[0]`，`MISSING_REFERENCE`，问题ID `issue-save-unknown-1c539a7e21cad8405cbf61cb958992af`。此处早于报告策略hook。检查 issue生成与归属、receipt引用、native到legacy投影、progress及正式独立POST发布的完整关系，明确前一轮静态POST格式缺陷与本次更早的receipt缺陷各自成立的条件。没有差异证据，不能声称后一缺陷由本轮代码新引入。

## 输出一个连贯的修复边界

以已有API/schema/语义为依据，提出覆盖上述整条链的最小修复边界，列出具体文件/函数、数据来源与提交顺序、legacy兼容性要求、需要复验的原L1/U1–U5及相关原条目。审查建议是否会把UNKNOWN issue绑定藏到后续才可存在的报告里，或造成receipt/report相互依赖。若现有合同足以决定修复，说明依据；若必须调整内部合同或桥接语义，具体列出需要调度决定的选项和影响，不自行改合同、更不代替B确认。

修复建议必须保留真实UNKNOWN、未决问题、暂停与不可重放、历史链、独立新鲜观察和report-read预算；不得靠删除 unresolved_issue_ids、伪造报告观察、把UNKNOWN改成功、清pending、吞异常或放宽校验来通过。当前只做诊断及建议，不实施下一修复，不发起功能探测；不要以“继续修到通过”为范围。

## 有界执行与交付

只新增 `docs/evidence/A03/review/P2-R12-R1-failure/` 和 `docs/tasks/A03-P2-R12-R1-failure-review-report.md`；不修改产品、schema、pins、旧证据、协调状态或作者报告。可用Python标准库、只读Git、AST/JSON、自己的immutable SQL副本。不得导入/调用产品、init/open runtime、PRE、dispatch、project、reconcile、正式发布或运行作者run/archive；不运行任何功能场景或全套测试。

原始证据只导出本轮必要文件；历史以确切提交/摘要引用，不复制历史大包。所有Git使用 `-c core.longpaths=true`，显式UTF-8。新静态脚本先compile检查；子进程登记命令/时限/退出/自有释放，单子进程最多60秒。首个分析或归档工具失败保留原证据，最多一次静态工具/元数据纠正，随后交付实际结论与未完成项，不通过反复运行扩成新验证任务。

报告给出冻结目标、来源边界、独立SQL结果、完整引用链分析、连贯修复范围、仍未运行项目及限制；附manifest和进程释放记录。结论为“失败及范围确认”或“证据需要补正”，A03整体保持REWORK；不能将L1作者通过或本轮证据核验记成功能ACCEPTED/INTEGRATED。待调度核对后才派下一次有界修复。R11有限通过与F2/F3作者历史原件缺口均保持原记录。

零平台、浏览器、profile、凭据、网络、安装、OCR、付费模型、B联系、推送或A05题22。field reset保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不运行、不变体、不委派、不建议重测。保留用户A03设置；不创建新执行或验收对话。
