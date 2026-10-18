# A03-T2 固定 C12/H1 独立验收

2026-10-18（Asia/Shanghai）。最终结论：**REWORK，限本验收交付的静态封存缺口**。固定C12和唯一H1独立实测通过，未发生业务失败、超时或重跑，归属/历史/报告的实际证据如下；但本验收工具先后发生两次静态错误，最终manifest未生成，按交接的第二次失败停止规则不交正式ACCEPTED。未发现本轮产品反例，不授权重跑业务。A03整体仍REWORK，T3组合与I01未放行；本轮未作产品集成或B共同确认。

| 身份 | 固定值 |
| --- | --- |
| 验收workflow | `0beba0d0c82376b119c46b1d35a137fde541113c`，其中`docs/tasks/A03-T2-review-handoff.md` |
| 完整target | `699f748a124162b3118e3996c03757725daac363` |
| 执行前候选 | `f111eb609d065a2506da52007c3b283928d537aa` |
| 产品基线 | `1330047dd29890dea0e433ff01b991f615bf78f4` |
| 已接受工具集成 | `86ae44b27e7d4825bd05d54701072f4068151bb9`，仅`examples/a03/T1-capture/capture.py` |
| 工具raw SHA256 | `3e07d56f409d8203c42f252f7a2900e902e31f56e1ff5fc7475335d33d0b042b` |
| 固定inputs SHA256 | `c11c2a39a5a420f873181b2445eace8dbf101fae6f85c428eae6f88a0223dcad` |
| 作者manifest SHA256 | `a64c32a7607d86eab259540e31e061c200c4db4e10a13db4d62b234fa60cf08e`，317项raw成员独立核对一致 |
| 独立目录 | `D:/1800/.local/A03-T2-independent-review/r1`；执行副本为其`c/` |

[准备报告](A03-T2-review-preparation.md)保持原样。原任务/拆分规则相对准备workflow未变，新交接提供正式启动所需固定target、依赖和释放条件。未读取浮动执行工作树、联系作者/旧A03/B或委派。

## 字节与四文件审查

从target的raw Git对象create-only物化独立副本，自己的Git HEAD绑定完整target；本地对象来源只读，不借父仓库身份。263项冻结执行/输入SHA全部符合`inputs.json`；68项runtime-view与产品raw blobs逐字节相同，48份Python仅编译的前置检查通过。两份继承测试文件按索引明确的CRLF SHA物化，其余固定文件使用raw bytes；未改pins迁就换行。9份正常退出导入记录的实际annotation模块均来自该固定runtime-view，文件摘要一致。

target的src及根依赖相对1330047d无改动，候选到target的产品/执行文件无改动。23项implementation pins、schema pins及adoption/profile均匹配。四文件修复来自`6affc61d...→1330047d`，本轮新增产品diff为0，审查该已有修复与受影响消费者；不把未改代码当作免验理由。

| 四文件及沿用pin | 独立检查结论 |
| --- | --- |
| `runtime/storage/__init__.py` — `d5edd3e106e161f24bf1c8def72321492c7b8f31b72c44771ac5f5f31fa6d445` | fact/事件先于receipt/progress；UNKNOWN Issue使用共享纯派生规则；原intent.receipt仅NULL时设置。native投影不生成legacy诊断POST、不消费正式报告读回。 |
| `contracts/recovery.py` — `0aee20dcc74fa38493cff2a3322f09603557d60cb29a36754ee25b7f369a4c31` | receipt自己的不可变fact、Resource字节及声明闭包、source/scope/plan/action/intent/obligation和实际观察共同证明Issue归属；未决ID精确匹配，不从未来head回填历史。 |
| `contracts/a03_native/__init__.py` — `e4ce9aa0631c662d4f9264bbf2f6e851e8e4555542f14844f49c1b5d4a124ec4` | 原始闭包→intent/resolution→receipt归属→receipt/progress→私有C01→正式报告；报告当前fact/head与原UNKNOWN receipt/intent的绑定保留。 |
| `contracts/validation.py` — `6b98eefe7c1a308f3846ba2f3acce1ffae5c64ec0b5c4d3675ee5872f055a0f7` | 私有上下文重新派生完整证明并比较确切语义投影，只授权对应receipt的未决ID；公开C01及其他artifact问题引用仍走原声明规则。 |

profile/adoption.profile_sha256为`7b819c77fb90565845c178fee6ca7e860255f7a5209efe765ac835be2df7d594`。历史consumer覆盖`_resolutions`、`_fact`、`_receipts_progress`、`_consumer_resolution_head`、`_legacy_projection_value`、`_outcomes`、native/legacy `_reports`及公开effective入口；另读未改的native terminal reconciliation与publisher确认实际消费边界。完整源码差异/入口说明见[静态审查记录](../evidence/A03/T2/review/independent-01/static-review.md)。本结论不覆盖多书、多scope、分叉变体或其他T3动态余量。

## 独立实测

使用未修改的冻结驱动及预期。以下是本轮已执行命令的记录，输出create-only且现已存在，不自动再次执行：

```powershell
python -X utf8 -B D:/1800/.local/A03-T2-independent-review/r1/launch.py validation 220 D:/1800/.local/A03-T2-independent-review/r1/c python -X utf8 -B D:/1800/.local/A03-T2-independent-review/r1/c/examples/a03/T2-history/run.py --output D:/1800/.local/A03-T2-independent-review/r1/c/docs/evidence/A03/T2/execution/validation/independent-01
```

Windows CPython 3.9.13、Pydantic 2.12.5，未安装依赖。外层220秒只用于整体记录器；内部C60秒、H1父90秒、业务子45秒、观察2秒、屏障5秒、lease10秒保持。C一批2.814秒；H1父36.388秒，建立/恢复/报告分别17.102/8.817/10.221秒，三次观察最长0.625秒；均在原上限内。

| C（恰12项，一次批次） | 实际结果 |
| --- | --- |
| C01 合法native归属 | 无错误 |
| C02缺ID / C03额外ID / C04重复ID | 各`NATIVE_ISSUE_OWNERSHIP` |
| C05错action digest | `ACTION_DIGEST_MISMATCH` |
| C06错intent obligation | `RECOVERY_CHAIN_INVALID` |
| C07跨scope consumer | `ORDINARY_SCOPE` |
| C08借另一consumer的Issue | `NATIVE_ISSUE_OWNERSHIP` |
| C09缺Resource / C10篡改Resource | `RESOURCE_READ` / `RESOURCE_HASH` |
| C11仅ID白名单 | `NATIVE_ISSUE_PROOF_REQUIRED` |
| C12公开C01悬空引用 | `MISSING_REFERENCE` |

[C原始结果](../evidence/A03/T2/review/independent-01/independent-run/C-result.json)逐项命中冻结目标错误层；不是无关schema失败。C无运行数据库、dispatch或观察。

H1仅一次：全新单题两片段，实际planner单动作，一次正常applied dispatch加unavailable执行观察，形成真实UNKNOWN receipt/progress、PENDING intent、CONSUMED permit及暂停；keeper/owner正常释放，建立进程wait后新进程一次`max_attempts=1`完整reconcile，得到MATCH/RESOLVED_APPLIED、pending=0。再由另一正常进程从合法late receipt显式调用现有publish入口一次。

原UNKNOWN fact的raw Resource、原receipt及稳定Issue `issue-save-unknown-`加canonical fact摘要前32位始终可验证；原intent.receipt没有被late receipt覆盖。终态resolution绑定原receipt/intent/action/obligation；late fact保留原attempt provenance。正式POST/Batch绑定当前receipt、原intent、当前resolution和head_original_receipt_ref。完整历史经本次真实validator消费，再以原始artifact/Resource和阶段库交叉核对。

恢复观察read_sequence=3，正式报告为4；ID、时间与快照均不同且更新鲜，两份观察原文分别与目标库持久化observations一致。报告前所有阶段`native_report_reads=0`，报告后唯一一行reads=1。UNKNOWN建立后目标始终为一个效果、一题两片段；恢复/报告均无新增效果、补片或重发。POST frame_structure=PASS、decision=HOLD；Batch CONTENT_PENDING、内容PENDING、提交NOT_SUBMITTED。

## 阶段原件与独立复核

| H1阶段 | 正式artifact / 事件 | 效果 | owner状态 |
| --- | --- | --- | --- |
| before-build | 8 / 5 | 0 | ACTIVE；capture时keeper已join |
| unknown-established | 12 / 10 | 1 | ACTIVE；capture时keeper已join |
| after-release | 12 / 11 | 1 | RELEASED，owner/PID空，lease=0 |
| before-reconcile | 12 / 11 | 1 | 同上，新进程重开 |
| after-reconcile | 17 / 15 | 1 | RELEASED，generation=2 |
| before-report | 17 / 15 | 1 | RELEASED，无正式报告读取 |
| after-report | 20 / 18 | 1 | RELEASED，generation=3 |

[七阶段14份raw双库及capture](../evidence/A03/T2/review/independent-01/independent-run/cases/H1/captures/after-report/capture.json)保留于同级各阶段目录。逐库复制前同步业务已返回、keeper已stop/join，记录MainThread及零异步写者；顺序复制不称跨库原子快照，未删除sidecar。所有SQL只读自有retained immutable副本，独立查询与封存SQL逐项一致，读取前后raw SHA不变。最终库没有用于重建中间阶段。

[独立字节/SQL审计](../evidence/A03/T2/review/independent-01/audit.json)对作者固定14份及本轮14份阶段原件、正式artifact/Resource、input_refs、事件hash/head、真实效果和历史/报告绑定作5118项静态对照，无未解决不一致；这不是5118个业务用例。作者317项manifest按target raw Git逐项复核，执行263项SHA在独立运行后仍相符。作者旧准备manifest只绑定其历史准备版本，不拿旧报告SHA要求新报告相同。

## 首错、元数据限制与释放

作者三次静态Git元数据/流缺口继续保留：首次`diff --cached --check`实际exit=2，仅合并输出；后两项exit=0但未独立保存raw流；三项均无历史PID/start/预登记记录。本轮未伪造补证。[限制评估](../evidence/A03/T2/review/independent-01/audit.json)将其作为作者静态流程的审计限制：独立raw对象/实际执行字节、阶段原件、真实导入和本次完整业务退出证据已支持当前C12/H1结论，该缺口不阻断此有限接受；不能据此声称作者全轮所有静态子进程完整登记。

本验收首次静态封存审计器将`files.path`的runtime相对路径误作绝对路径，实际exit=1，首错及stderr保留。唯一一次静态纠正以新`audit-r1.py`锚定case/runtime，并按已有观察器的elapsed_seconds/原始流格式读取记录；不补造缺失时间字段或历史摘要。旧审计器/首错保持，[纠正说明](../evidence/A03/T2/review/independent-01/static-audit-correction.json)明确业务调用/重跑=0。纠正后仅重做未完成的静态审计，沿用已成功的raw manifest检查；C/H1、产品、工具、输入、pins和预期从未修改。

后续`seal.py`已复制本轮必要证据并生成final-release.json，但在生成manifest之前，把报告中的manifest自链接作为必须已存在文件检查，触发`AssertionError: ['../evidence/A03/T2/review/independent-01/manifest.json']`，实际exit=1。这是第二次静态工具错误，不是产品/数据库/业务失败；不再修正或重跑封存器，不以手工生成manifest绕过停止规则。[封存失败记录](../evidence/A03/T2/review/independent-01/sealing-failure.json)保留命令、退出码及工具返回的解码trace边界；该次没有单独raw stderr文件，不伪称已保存。封存前报告保存在同目录`review-report-before-seal.md`，原`audit.json`中`FINITE_T2_ACCEPTED`仅是封存前的局部检查器状态，由本最终REWORK结论覆盖；中间原件均不改写。

本次验证链11个登记Popen（1 Git、10 Python，包含两个外层记录进程和三个观察子进程）均实际exit=0、无timeout、已wait/reap，原始流和导入原件齐全。已有观察子进程completion用真实elapsed_seconds，不补时间戳。三个keeper全部stop/join、无error；最终owner/PID空、lease=0、phase=RELEASED、generation=3，源库raw摘要仍等于after-report捕获原件。[最终释放证明](../evidence/A03/T2/review/independent-01/final-release.json)另列短命静态子进程，保留首次静态审计exit=1；不是机器全局PID扫描。

## 交付与范围

最终`docs/evidence/A03/T2/review/independent-01/manifest.json`未生成，不能声称本轮证据已完整封存。已落盘的本轮证据、原件、实际命令/源码记录、第一次首错及释放证明保留在review专属目录；静态Git raw大流仍在自有隔离目录，由[外部静态记录索引](../evidence/A03/T2/review/independent-01/external-static-records.json)绑定，不复制旧历史全集。证据内绝对路径保留实际来源，不改写SQLite、日志或回执来迁就展示路径。调度可据已有固定原件判断后续归档处置，本对话不自行开启新轮或增加业务。

本轮固定归属/历史报告链取得独立通过的实测证据，但因上述封存失败不正式关闭T2。未重跑T1六例、旧全套、多书/多scope或T3余量；产品diff=0，无新增产品影响项由本轮另测。原C/L1/U1作者检查、原U2采集失败与U2恢复/U3–U5/H1当时未运行、U2阶段/瞬时journal及F2/F3历史缺件保持历史事实，不因本次新H1而回填。未重启原库或触及执行者worktree。

仅写本报告及review专属证据、自有`.local`目录；未操作主目录Git索引/提交、协调JSON、公共任务单。全部离线，零网络/平台/browser/profile/凭据/安装/付费模型/OCR/推送/书级送审/A05题22；未联系作者/旧A03/B或委派。每条Git及Git子进程显式`-c core.longpaths=true`，Python使用`-X utf8`。field reset=`NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。无自有业务进程、keeper、owner或后台服务待释放；交调度核对并决定后续范围，完成后结束等待。
