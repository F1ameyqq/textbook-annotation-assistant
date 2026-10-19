# A08 执行交付报告

2026-10-19，Asia/Shanghai。作者状态 **FIXED_DELIVERY / REVIEW_READY**，尚未独立验收或调度接受。

## 固定交付与运行边界

- 唯一写入目录：`C:/Users/ASUS/.codex/worktrees/a08-batch-readonly/1800`；分支 `codex/a08-batch-readonly`。未写入主线或旧工作树、未修改调度状态、未向独立对话发信。
- 执行起点 `6fac939cf6cae0df88fab12d9669090c325897fc`，产品原基线 `e37606d74d7e538052c563d02df11c6c961b742f`。
- **第 1 且唯一冻结产品候选** `04762d78eae18449d7fcf3c0de20aec23b1f6881`。先冻结，后运行一次 R0–R7；冻结后没有产品、驱动或使用说明改动。最多两候选中的第 2 候选未使用，不恢复旧业务额度。
- 本报告、结果和清单在后续交付提交中归档；其确切完整提交 ID 在最终回复登记，可用 `git -c core.longpaths=true rev-parse HEAD` 核对。本报告不自包含自身提交哈希。
- 产品 raw Git 清单：[candidate-1-raw-git.json](../evidence/A08/execution/candidate-1-raw-git.json)。最终交付新增路径的 raw Git bytes/SHA 清单：[delivery-raw-manifest.json](../evidence/A08/execution/delivery-raw-manifest.json)（自身显式排除）。

新增可导入 API `annotation.source.b_batch.receive_package`、`BatchReceptionError` 和公共 CLI `python -m annotation.source.b_batch`。只使用标准库及已存在 Pillow 11.3.0；Python 3.9.13。支持范围、调用和退出码见[使用说明](../a08-batch-readonly-reception.md)。不导入 delivery/runtime，不构造新 C01/目标/计划/模拟回执。

## 输入与来源

只消费调度提供的 `D:/1800/.local/stages/a08-inputs/B-46007447-Q4-Q9-Q16-next-batch-HOLD-2026-10-19.zip`：1,440,149 bytes，SHA256 `b646fad9008e03e79a3dddfb4ead912d7ceadefbcee331c2e2af2415abf6f673`。从其原字节计算 Git blob SHA1 `4f49f37d81427e9aa8d2acf1c1919c1df8f10ce2`，与[输入登记](A08-inputs.json)匹配。B 固定提交 `a76e5a925fec76f20818dfdefa4145aa132ec8a8` 的来源绑定沿用调度冻结登记；作者未遍历 B 仓库或联网取件。

**实际 ZIP 为 24 成员，外层 manifest 列出 23 个非自身成员，内层列出 9 个非自身成员。** 任务正文“23成员”少计清单自身；登记 raw 列表、实际 ZIP、外层覆盖三者一致。完整成员 bytes/SHA 在 [R0 报告 input.raw_members](../evidence/A08/execution/candidate-1/R0-original.json)。3 张 JPEG 原图分别完整解码，SHA 和尺寸均按固定资产核对。

外层 `b-complex-batch-evidence-package/0.1`，batch kind `ComplexCaseBatchProposal`，schema `b-complex-batch-proposal/0.1`；batch 无 payload 包装、case 无独立 schema。`b-content-projection-trial/0.3` 只作为内嵌快照字段消费。完整 G0.8/Check0.8/plan0.3 不在输入，保持 `DECLARED_ONLY_EXTERNAL_NOT_LOADED`；图谱/计划/续接/Check/图形引用都没有被当作已读取完整对象。不取得 Q15 包、不执行包内 Python、SQLite、B 回归或模型记录，不借用 B 历史通过作为 A 验证。

准备阶段曾发生一次只读 JSON 控制台输出的 `UnicodeEncodeError (gbk)`；当时未调用接收器、未冻结候选。随后显式 UTF-8 完成数据阅读。冻结后的所有 CLI stdout/stderr 与退出码均已归档，无产品失败或额外重跑。

## 逐例结果

| 案例 | 固定身份与来源 | A 只读结果 |
|---|---|---|
| 第一课时 Q4（优先） | `q-260d10c51f2b7c16fb6fefb5` / `a-92c4d2164ab878c8e6d4c88d`；第一章→1探索勾股定理→第1课时；viewer-10 题干4片段、viewer-173答案1片段 | `QUESTION_ANSWER_CANDIDATE/HOLD`；B `selected_answer_id` 只显示为 `B_DECLARED_CANDIDATE_ONLY`，`a_selected_relation_created=false` |
| 小专题 Q4 | `a-35b5bc7421c65d9fcaa47e33`；第一章→小专题1方程思想；viewer-173 | `ANSWER_EVIDENCE_ONLY/HOLD`；question_id、question_snapshot、A候选关系均 null |
| Q9 反思 | `a-9a6c21dd0fe88b1059b7919e`；第一章→问题解决策略反思；viewer-173→resource-173 | `ANSWER_EVIDENCE_ONLY/HOLD`；无题实体/关系，后页 viewer 仍 null |
| Q16 第二单元 | `a-7302d4870826c53aea0bcd16`；第一章→2一定是直角三角形吗；viewer-173 | `ANSWER_EVIDENCE_ONLY/HOLD`；无题实体/关系 |

Q4 保留原题干逐行文本、4个片段框（含图题文字）、答案 `13`、`raw_text=4.13`、`text_span=[2,4)`、原坐标 `[308.667,241.667,340.0,254.333)` 与来源 `viewer-173/ocr/10/detail/5`。答案 0 个 render_regions 是合法原结构。`UNVERIFIED`、`FIGURE_EXTENT_UNVERIFIED` 保持；13 正确性、实际图形边界及内容/区域/逐题政策均未批准，不修 OCR、不画新框。

小专题 Q4 的 3 原片段、1 LaTeX run、两条裁边的原框/新框、阈值、B 像素摘要/计数与冲突名单完整保留。作者未重新裁图、重算 B 暗像素声明或批准几何。

Q9 保留 33 原片段、15 呈现区、完整跨页快照、图3–7记录及 `ANSWER_SPATIAL_GAP_UNRESOLVED`。`source_fragment_order` 只列 10 个文字片段；其余 23 个是图区覆盖片段，不要求顺序数组等于33。结构化 runs 指标0不表示没有行内数学，原 `pieces` 等内容全部保存。

Q16 保留 17 原片段、3行 `content_fragments`、11个结构化 LaTeX runs（含原 run 索引及快照路径）、`60 61` 及外围幂次/因果符号。没有新增公式解析或正确性判断。

`viewer-173` 独立绑定 resource index172、1148×1621、SHA `a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be`；`resource-173` 独立绑定 resource index173、1145×1620、SHA `8380f9a1872c830b1cf4fba12fa00e3b6d9c50ddaed357587de7333086e9cdbf`、printed_page26、viewer_page null。未别名合并或推算页码。完整原图不扩大已提供内容前缀范围。

## 有限检查与实际命中层

总入口：[finite-results.json](../evidence/A08/execution/candidate-1/finite-results.json)。共 8 组、12 次公共 CLI 调用：原包 1 次 exit0、11 负例各 1 次 exit2；stderr 全为空。驱动实际调用公开 `-m` 入口，入口调用公开 `receive_package` API；无第二次额外原包/API重跑。驱动总 exit0，结论仅 `PASS_AUTHOR_FINITE_CHECKS_ONLY`。

| 组 | 固定变体/原件 | 实际结果 |
|---|---|---|
| R0 | 原包、优先第一课时 Q4 | 4案例/3资产；1题答候选+3答案证据；4 HOLD；完整外部对象未加载 |
| R1 | 未知 batch schema、未知 kind | 各 `VERSION / UNSUPPORTED_BATCH_VERSION`，分别定位 `/schema_version`、`/kind` |
| R2 | viewer-173资源1 byte损坏，保留错误摘要 | `MANIFEST / MEMBER_DIGEST`，定位实际资源成员 |
| R3 | 同号小专题答案替换第一课时Q4，并同步候选声明 | `IDENTITY / CROSS_SCOPE_OR_CASE_IDENTITY`，定位 cases/0/answer_id |
| R4 | 给原无题ID的Q9补题及模式/关系 | `IDENTITY / FABRICATED_QUESTION_OR_RELATION`，定位 cases/2 |
| R5 | resource-173改为viewer-173；未知viewer填174 | 各 `SOURCE / ASSET_IDENTITY_CONFLICT`，定位 assets/2 及其 external_refs |
| R6 | 删Q9后页一个呈现区；删Q16一个LaTeX run，并同步声明计数 | 各 `STRUCTURE / FIXED_COUNT_MISMATCH`，定位 observed_counts/render_regions 与 latex_runs |
| R7 | Q1审批+30项排除附到Q16；外加Q4已批准标记 | 各 `AUTHORIZATION / CASE_APPROVAL_ESCALATION`，定位 approval_ref 与 business_approved |

变体由[冻结驱动](../../tests/test_a08_reception.py)每次从原件独立生成，更新单例/批次、receipt的batch SHA和两层清单的大小/摘要。R2故意在重封后损坏资源。产品 pins 从未改写。命令/退出码/变体 bytes/SHA、stdout、stderr 和 JSON 都在证据目录；临时副本成功后删除，配方可独立复现，不能直接重放已删除的绝对临时路径。

R1/R3/R4/R5/R7 实际命中明确版本/身份/授权门，均未被外层整包 SHA 提前截获。R6 只证明结构库存减少被拒绝，未声称公式/跨页语义门通过。所有其他无法匹配固定快照或原件的变化仍受完整快照/成员/ZIP绑定门约束，未逐helper额外扩展矩阵。

复现须使用固定产品并采用新证据目录：

```powershell
# cwd = C:/Users/ASUS/.codex/worktrees/a08-batch-readonly/1800
$env:GIT_NO_LAZY_FETCH='1'
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
python tests/test_a08_reception.py --package D:/1800/.local/stages/a08-inputs/B-46007447-Q4-Q9-Q16-next-batch-HOLD-2026-10-19.zip --candidate 1 --evidence-dir docs/evidence/A08/execution/new-independent-output
```

此命令用于获派的独立固定检出；作者已运行额度不再重跑。独立人员使用自己的路径和报告，不覆盖本作者证据。驱动设置当前检出 `src` 的 PYTHONPATH、UTF-8、禁写pyc和 `GIT_NO_LAZY_FETCH=1`；每个进程30秒上限，超时会kill并join且保留首次失败、后续NOT_RUN。本轮无超时。

## N01–N08范围矩阵

| 编号 | 本次交付 | 保留 PENDING |
|---|---|---|
| N01 | PARTIAL：固定stage case路由、schema/kind拒绝、来源摘要 | 完整G0.8/Check0.8/plan0.3及新C01 |
| N02 | SUPPORTED_FIXED_STAGE_READONLY：答案证据模式与Q4候选分开 | 另外三例题身份/关系 |
| N03 | PARTIAL：原文字顺序、图区覆盖、逐资产几何及未知映射保留 | 内容/续接核准、非前缀覆盖 |
| N04 | PARTIAL：plain/LaTeX runs、原片段和图形数据完整保留 | 公式解析、内容/图形/角色政策 |
| N05 | PARTIAL：原始/修订几何与B像素声明保留 | 新裁图、像素重算、变换/几何政策核准 |
| N06 | PENDING | 完整Check、逐题问题适用性与政策/内容核准 |
| N07 | PENDING | 五项PRE_APPLY/TARGET/计划/模拟及其授权 |
| N08 | PARTIAL：有限拒绝与独立HOLD诊断 | 执行读回、逐框业务比较 |

## 保全、释放及限制

[原件/环境保全](../evidence/A08/execution/preservation-and-environment.json)确认：执行起点全部 12,491 路径的 raw Git blob 不变；390,354,044 bytes 的旧工作树文件按“排序路径+NUL+文件SHA256+LF”汇总，前后摘要均为 `1d920b417d7361e22ff5b22fe41fc0c81e9f53a89c1886efc98243954c137d1d`。旧源码、schema、pins、合同、根依赖、Q1授权和旧证据全部包含在该范围，工作树原字节未变。输入前后SHA保持，未修改B原件。

[进程释放](../evidence/A08/execution/process-release.json)：12个接收子进程均 communicate/wait 完成，释放核对无存活PID；驱动已退出，0服务，临时变体目录已删除，未终止其他进程。无SQLite、浏览器、平台、付费模型、远端推送或B消息；未联网补依赖/外部对象、未读取凭据。所有报告的 plans/targets/new_c01_execution_objects/simulation_dispatches/platform_calls/paid_model_calls/b_messages/pushes 均为0。

文档相对链接及 Git whitespace 检查另在交付检查中记录。没有运行旧A07/A06/A03/I01或全仓库测试。交付仅固定stage的有限结构接收与拒绝边界，不代表业务正确、B共同新批次采用、完整G/Check/plan消费者或平台接受；A04真实平台阻断保持。请主调度核对固定交付/释放后，续派既有新独立验收对话。作者不宣告独立通过。
