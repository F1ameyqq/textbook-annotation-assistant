# I01-A 独立验收报告

2026-10-18（Asia/Shanghai）。结论：**ACCEPTED，仅限固定组合上的 A01 公共离线消费和 N/E/U 三条 A 内部 synthetic 路径**。独立业务一次完成，累计 **3 fresh targets / 3 dispatch / 3 题目效果**，E 另有 1 次 operator 目录变更。没有业务失败、超时或业务重跑。作者仍是交付方；本报告不代表调度已接受 I01 整体、完成集成或关闭 B 接收与联合业务。

## 固定对象与原字节核对

| 对象 | 固定身份 |
| --- | --- |
| 本次派发工作流 | `1534616372e977ddadb2918fbd29044290c263cf`；[原任务及派发原件](../evidence/I01-A/review/rules/) |
| 组合基线 | `a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8` |
| 作者最终交付 | `3fdc5d37e221fc73410f197605f5d7b8878182d5` |
| 实际运行候选 | `be68b8d7c645de556d601458d1d493258f063721` |
| A03 产品 | `6097a06de937fee8876feccedf46920510850b83`；旧最终交付 `19ab03c849bfab3dcde2dc86be37c59f3add1ebe` 仅引用 |
| 独立目录 | `D:/1800-i01-review-01a14e1c`，新建独立本地 Git 视图，HEAD 为运行候选，未建立或操作作者业务状态 |

从作者仓库只取固定 Git 对象，不读作者工作树或 primary 数据库，不复制作者数据库作为起点。独立核对最终 manifest 的 **665 成员**，每个长度/SHA256 均匹配，无重复；666 个新增路径全部在作者白名单内。`src/`、根依赖/包配置和既有 A01/A02 路径与组合基线无差异；A03 runtime/native/delivery/quality 的 Git 对象与固定产品一致。

固定报告 SHA256：`59a3d4990162ba4ea798cafb2989e2df2714a757a637eb3d7bc2192f0569b3d9`；作者 manifest：`e55f241b6e1c85eec5ed4c09d50361ef7a9a4f1db8aa7bed9045f87d67a187aa`；作者 release：`cdb007faa3653719ec058c41a7d209fe98b3437f9d8b52b762841667d4eb685e`。三者均按最终交付 raw blobs 复算。

[静态准备](../evidence/I01-A/review/static-preparation.json)逐字核对 91 个组合基线原件、24 个固定输入成员及 30 implementation pins，并核对 schema、api/interface/oracle、profile/adoption 链。独立实际导入的 **140 记录**均指向自有 raw-view，并与组合基线 raw blobs 一致；作者固定证据中的 140 导入摘要也与相同原件一致。运行候选的冻结导出成员再次与候选 raw blobs 比较，无改动。未修改产品、pins、驱动、故障语义、预期或守卫。

独立目录直接使用固定候选已有准备视图，未再次派生或修补夹具。冻结夹具中的 `book-I01-* / ledger-I01-* / target-I01-* / store-I01-* / session-I01-*` 文本标签保留。独立状态身份由全新 anchor、runtime/target 绝对目录及正常 API 新生成的 process/journal/owner 绑定；三路的实例和事件 head 均与作者不同。这里不宣称文本标签被重命名，也没有把作者状态改标为独立起点。完整路由和输入摘要在业务前已保存于[独立冻结调用](../evidence/I01-A/review/independent-invocation.json)。

## 实际独立运行

在上述全新目录执行原入口，HEAD 和产品路径守卫正常通过：

```powershell
# 本次已执行；该目录输出已存在，禁止原地重跑。
Set-Location D:/1800-i01-review-01a14e1c
python -X utf8 -B examples/i01/run.py --candidate be68b8d7c645de556d601458d1d493258f063721
```

外部记录脚本为 [run_review.py](../evidence/I01-A/review/run_review.py)，仅负责隔离路由、事前记录及子进程原始流/wait。实际顶层 PID **32552**，exit=0，wall=42.781 秒，进程自身 CPU=0.296875 秒；子 worker CPU另列，不能把顶层 CPU当全流程 CPU。[顶层原始流与生命周期](../evidence/I01-A/review/top-level/)及[六阶段 matrix](../evidence/I01-A/review/independent/run/matrix.json)均保留。环境为现有 Windows CPython 3.9.13、pydantic 2.12.5、Pillow 11.3.0；没有安装依赖，此处不新增 D01 清洁安装结论。

| 阶段 | worker PID | wall / CPU 秒 | 独立结果 |
| --- | --- | --- | --- |
| A01-C01 | 公共进程 42176 | 父记录 wall 0.734 | 真实公共 CLI 一次；valid=true、resources_verified=true，无 structure-only |
| A01-consume | 公共进程 58704 | 父记录 wall 0.719 | 现有消费者一次；公共/A01一致、完整图像解码与页绑定通过 |
| N | 72672 | 9.781 / 7.687500 | 真实五检查/PRE、TARGET、planner、持久 intent/permit、独立效果/读回；APPLIED，pending=0 |
| E | 77940 | 15.016 / 12.109375 | 旧真实候选 TARGET_CHANGED 且 0 dispatch；正常释放/reclaim后新 INITIAL/PRE/TARGET/plan，执行一次 APPLIED |
| U-execute | 48748 | 6.719 / 5.609375 | 一次真实效果后执行读回 UNAVAILABLE；正式 UNKNOWN、pending=1、暂停持久化；0次报告 |
| U-recover | 37908 | 7.594 / 6.031250 | 原进程退出后同身份重开；一个冻结 call/max_attempts=1，MATCH/RESOLVED_APPLIED；0重发，pending=0 |

全部 worker 的180秒、阶段父240秒和原 read2/entry8/gate5/lease10/renew2 内层期限保持。以上是本次有限功能结果和实际耗时，不构成 SLA 或其他矩阵覆盖。

## 两个来源边界

**A01 公共消费接受。** 同一整书离线包来自组合基线 `examples/a01/R3/bundles/46007447/` 的12个原文件，24项固定输入清单包含该包和三个 native 夹具。两个公共入口均真实在自有子进程运行，并各只运行一次。C01 为 `1.0.0-a-proposal`；A01 输出 book=`46007447`、asset_count=2、metadata_page_count=214、reference_records=1、完整图像解码 OK、`coverage_eligible=false`，SourceBundle hash=`308c9a22e4743ed12d2161a81a2e9a7618cbf53139ba76ba40cd66105fa03add`。未重新导入来源，也未运行 build/verify 全套。

**Native 固定桩接受。** 各一路一题、一张32×32 PGM、stem/answer两框，SourceBundle/EvidenceBundle/QuestionGraph和政策均来自候选原件；origin/provenance明确 SYNTHETIC。格式为 `a03-exchange-4-proposal` / `1.4.0-a03-native-proposal`，资格仍是 `A_INTERNAL_FIXED_SYNTHETIC_ONLY`、fresh-native-only、LEGACY_INITIAL_ONLY。正常调用现有 init/register、真实 PRE 五检查/admission、TARGET/planner、intent/permit、持久目标、receipt/progress、reconcile与publisher。未拼接成真实 A01→native 闭环。

作者提供的 `annotation.contracts` 公共类型、`load_bundle(path, verify_assets=True)`、`validate_bundle`、C01 CLI、`annotation.source.static.load_static_bundle(path, expected_book_id)` 和现有 `examples/a01/consume.py` 调用方式与组合实现一致。native selector及1.4内部资格入口实际正常导入，30 pins不变。这里没有推断 B 内部0.4/0.5/0.6/0.7的适配语义；B接收及联合业务仍由A06/调度按实际证据另行处理。

## 次数、E纠正与U历史

| 路径 | 作者 target/dispatch/effect/operator | 独立 target/dispatch/effect/operator | 独立 PRE / 执行准备读 / 执行结果读 / reconcile读 / report读 |
| --- | --- | --- | --- |
| N | 1 / 1 / 1 / 0 | 1 / 1 / 1 / 0 | 1 / 1 / 1 OK / 0 / 1 |
| E | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 | 2 / 2 / 1 OK / 0 / 1 |
| U全路径 | 1 / 1 / 1 / 0 | 1 / 1 / 1 / 0 | 1 / 1 / 1 UNAVAILABLE / 1 MATCH / 1 |
| 各自累计 | 3 / 3 / 3 / 1 | 3 / 3 / 3 / 1 | 4 / 4 / 3 / 1 / 3 |

作者次数属于已哈希固定证据的静态复核；独立次数另由自有执行及静止副本核实，额度不互借。独立终局持久 observations 为 N/E/U=4/6/5，共15，含U的一次UNAVAILABLE；另外8个有界只读子进程为4次PRE、1次恢复、3次报告。没有把未成功观察记作完整成功读。

E 的[旧拒绝](../evidence/I01-A/review/independent/run/cases/E/old-candidate-refusal.json)和[旧链静止双库](../evidence/I01-A/review/independent/run/cases/E/captures/old-candidate-refused-released/)显示：plans/intents/permits/dispatch/effects/题/框均0，native_pre_runs=1，operator epoch=1。新链 PRE、snapshot、action及plan均与旧候选不同；最终只接受新计划，plans/intents/permits/effects各1、1题2框、epoch=2、PRE累计2。此路径没有进入hold，不额外制造hold或复验其恢复。

U 原 UNKNOWN receipt：`executionreceipt-5e6999ccfe62402d80ea7cb1931befcb`，hash=`12c4e1c33f29f4bc43351b170ead395399fd85ef31735b0d488b4e45d30170d4`。解决记录：`resolution-93c97cd560294a4baf67cbd18032b7d3`，hash=`a9f3d976fda8536d7fa8f9618d046d61b05de3d128bfff0d0debb42d44193896`，明确引用原receipt及intent。PID48748完成/wait早于PID37908启动；`I01-U-one-MATCH-call`只有1个call/1个attempt，target_effects_during_reconcile=0。恢复前后effects逐字相等，前11条runtime事件完全保留，原bundle全部artifact仍在；新增解决链和新APPLIED回执，attempt_fact仍为MAY_HAVE_BEEN_ATTEMPTED。没有改写原UNKNOWN或再次dispatch。

## 报告、静止双库与释放

独立保留5组/10份固定T1 capture双库：N终局、E旧拒绝、E终局、U原UNKNOWN、U恢复终局。沿用原capture代码及协作静止边界；SQL只对自己的`mode=ro&immutable=1`留存副本查询。再次独立查询与每份SQL.json一致，原件复制前后及审计前后摘要一致，未出现sidecar；顺序双库复制不称原子快照。runtime事件hash/前缀/head完整，intent→permit发放→permit消费→dispatch→结果提交的顺序成立。每条终局1题2框与计划一致，不能仅以effects行数代替题数。

N/E各一次正式POST及BatchReport；U UNKNOWN阶段均0，恢复后各一次。三份POST均frame_structure=PASS，decision=HOLD保留内容未核验语义；三份BatchReport的total_expected/scope_manifest/questions均为1、state=CONTENT_PENDING、content_check_status=PENDING、submission_status=NOT_SUBMITTED。原失败和未决历史没有从分母或报告引用中删除。没有为取证重复publish。

[audit.json](../evidence/I01-A/review/audit.json)列完整断言结果、源字节、逐进程、静止库摘要及原UNKNOWN解决链。[release.json](../evidence/I01-A/review/release.json)登记19个业务运行进程：顶层1、公共入口2、阶段watcher4、worker4、独立native reader8；均有真实完成记录，当前原进程均已退出。worker结束只剩MainThread、keeper已stop/join；owner/PID为空、lease=0、phase=RELEASED，终局pending=0。自有6份primary仅按bytes与最后capture比较，未用SQL打开；U旧UNKNOWN副本保持历史，没有回滚。未操作作者的复用PID36852或其他进程。

## 首次错误、限制及交付边界

作者首次冻结 `3a7b5430659918d015a23fa2da722bfe3cec44af` 的5项历史JSON换行差异、一次包纠正、中间未执行打包提交、一次归档重复计数错误和PID复用误判都保留。独立核对首/末run/driver/support/public原字节相同；业务实际只运行be68b8d7。作者已耗纠正次数不恢复，没有第三包或旧A03补跑。

独立发生两项纯静态工具错误：一次猜测`contracts/io.py`和`source/static.py`导致rg exit1，随后在固定包目录定位真实实现；一次收口脚本错误假设共享主目录索引始终不变，在最后的索引摘要断言处失败。后者的[首次脚本及错误](../evidence/I01-A/review/static-closure/)保留，仅修正静态记录工具后完成收口，业务没有重跑。这些静态错误只有工具回执，没有单独OS PID/raw stderr，不补造。所有实际业务阶段、worker及native reader有独立原始流，顶层亦有独立OS原始流。

[主目录索引观察](../evidence/I01-A/review/main-index-observation.json)显示验收前后摘要确实不同。本验收对主仓库仅执行读取固定对象/路径的Git命令，没有写索引、提交或还原它；不把共享目录并发变化改记为“索引未变”。隔离目录固定HEAD、运行字节和验收结果不依赖该索引。保留他人状态，不以还原主目录获得表面一致。

本次没有额外单元测试或旧M/L/G/F矩阵。零平台/browser/profile/凭据/网络模型/付费/安装/push/B消息/题22/旧pending恢复；没有修改产品、作者文件、调度state或主目录索引，没有提交。旧A03内部有限接受仅继承；真实来源、真实A01→native、B共同合同/原生接收与联合联调、OCR/内容、S01、A04真实平台及DB迁移仍未在本次验证。

本次交付仅新增本报告及`docs/evidence/I01-A/review/`；[manifest.json](../evidence/I01-A/review/manifest.json)记录全部发布文件长度/SHA256，自身排除。独立运行目录保留原现场，不可原地重跑；任何新业务执行都需要调度重新明确范围，不能换目录重置本次额度。I01整体调度接受、主目录集成及对外表述仍由调度决定，B的PENDING_A不因本报告关闭。
