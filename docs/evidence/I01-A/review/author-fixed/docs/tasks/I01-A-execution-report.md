# I01-A 执行交付

2026-10-18（Asia/Shanghai）。作者状态 **REVIEW**。A01 公共离线消费及 N/E/U 三条固定 synthetic 编排均完成首轮业务；累计 **3 fresh native targets / 3 dispatch / 3 题目效果**，E 另有 1 次 operator 目录变更。业务无失败、超时或重跑。独立验收、调度接受与集成待定。

## 固定身份与范围

| 对象 | 确切提交或路径 |
| --- | --- |
| 组合基线 | `a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8`，已按本次派发释放 |
| 工作流 | `8b0fe38b3b520f0ff80801c98121acd3f335a1fc`；[任务原件](../evidence/I01-A/execution/preparation/rules/docs/tasks/I01-A-minimal-integration.md) |
| A03 产品 | `6097a06de937fee8876feccedf46920510850b83`；既有最终交付 `19ab03c849bfab3dcde2dc86be37c59f3add1ebe` |
| 首次冻结 | `3a7b5430659918d015a23fa2da722bfe3cec44af`；仅静态字节检查，0 公共消费 / 0 target / 0 dispatch |
| 唯一纠正后的实际运行候选 | `be68b8d7c645de556d601458d1d493258f063721` |
| 首轮业务和审计证据提交 | `be6dd893d796e298dda9799ac486a5c27c776f3d` |
| 释放证据提交 | 见本报告附带 manifest 的 `evidence_payload_commit`；报告/manifest 的外层最终交付提交由本次最终回执给出，避免提交内自引用 |
| 独立执行目录 / 分支 | `D:/1800-worktrees/i01-a` / `codex/i01-a` |

全部写入均在任务白名单。`src/`、根依赖/包配置、pins、旧 A01/A02/A03 示例/测试/证据、主目录调度状态和索引均未改。A03 既有有限接受只引用[最终差量独立报告](A03-R1-final-delta-review-report.md)，没有重跑 M/L/G/F、旧 T3 或旧 pending。

## 实际字节、输入和环境

[preparation/identity.json](../evidence/I01-A/execution/preparation/identity.json) 记录基线 raw Git 导出的 91 个原件（含共同 src、包配置、A01 整包、T1 capture 及 synthetic seed）、输入长度/SHA256、源提交/Git blob。实际执行使用 `preparation/raw-view/src`，未使用 CRLF checkout 的产品；[audit.json](../evidence/I01-A/execution/audit.json) 重新逐个与固定 Git 对象及实际导入文件核对，140 个导入记录一致。30 implementation pins、schema pins、api/interface/oracle、profile/adoption 链均一致，没有修改 pins。

[frozen/invocation.json](../evidence/I01-A/execution/frozen/invocation.json) 在业务前固定实际候选、驱动/输入成员摘要、顺序、故障和限额。驱动与夹具从该候选 raw blobs 导出到 `frozen/candidate-view` 后执行；[最终字节检查](../evidence/I01-A/execution/final-freeze-byte-check.json) 无差异。3 项[预检](../evidence/I01-A/execution/preflight/process/stderr.txt)验证正常导入/30 pins、三组输入的引用/资源/PGM与隔离身份、A01 全包复制；不创建账本或 target。

环境为现有 Windows CPython 3.9.13、pydantic 2.12.5、Pillow 11.3.0，未安装依赖或联网；详见 [environment.json](../evidence/I01-A/execution/environment.json)。本任务不增加 D01 清洁安装证明。

## A01 公共消费边界

完整单书包源为组合基线的 `examples/a01/R3/bundles/46007447/`，共 12 个文件，逐字复制到 `tests/fixtures/i01/source-copy/`；从固定候选导出的同名包实际供子进程读取。公共 C01 CLI、现有 `examples/a01/consume.py` 各调用一次，无 `--structure-only`、无 build/verify 全套、无重新导入来源。

实际包装 [public.py](../../examples/i01/public.py) 只设置原入口 argv、通过 runpy 调用未改的 CLI/消费者并在 finally 记录真实导入，不替换业务函数。C01 子进程回执为 valid=true、resources_verified=true、schema_version=`1.0.0-a-proposal`、artifacts=1；A01 消费者确认公共/A01 结果相等、全部资源摘要与完整图像解码、书籍和映射一致。实际输出：book=`46007447`、2 张取得原图、metadata_page_count=214、reference_records=1、coverage_eligible=false，SourceBundle hash=`308c9a22e4743ed12d2161a81a2e9a7618cbf53139ba76ba40cd66105fa03add`。

公共 C01 入口 PID=62088，A01 消费者 PID 及全部 argv/cwd/raw stdout/stderr/exit/wait 见 [run/processes](../evidence/I01-A/execution/run/processes/)；真实导入见 [run/public-imports](../evidence/I01-A/execution/run/public-imports/)。后续静态检查发现原预检 PID=36852 已被另一个更晚创建的 conhost 复用；它不属于原预检进程，未操作该进程。

## Native 固定桩边界与实际结果

三个输入分别为 [N](../../tests/fixtures/i01/N/initial.json)、[E](../../tests/fixtures/i01/E/initial.json)、[U](../../tests/fixtures/i01/U/initial.json)。均从已接受单题 synthetic 语言派生，独立 book/scope/target/ledger/store/session；各 1 题、1 张 32×32 PGM、stem/answer 两框。图像 bytes 与原政策不变；派生身份及 inventory 更新后依赖引用逐级重封。SYNTHETIC SourceBundle/EvidenceBundle/QuestionGraph 明确独立于 A01 真实档案。

版本为 `a03-exchange-4-proposal` / `1.4.0-a03-native-proposal`，资格仍为 `A_INTERNAL_FIXED_SYNTHETIC_ONLY`、fresh-native-only、LEGACY_INITIAL_ONLY。现有 `init_native_state/register_book`、真实五检查/PRE admission、`check_target/create_plan/record_native_plan`、intent/permit、native target、正式 receipt/progress/publisher 正常导入并实际调用。

| 阶段 | worker PID | wall / CPU 秒 | 实际事实 |
| --- | --- | --- | --- |
| N | 16952 | 8.844 / 6.859375 | 真实五检查/PRE→TARGET→planner；正常 run_plan 一次。1 target / 1 dispatch / 1 题 2 框，APPLIED，pending=0，正式独立 report read=1。 |
| E | 13852 | 12.313 / 9.546875 | 旧真实候选→operator 目录增加一次→prepare_action 的 TARGET_CHANGED 拒绝；旧候选 0 accept/intent/permit/dispatch。正常释放/重新 claim 后全新 INITIAL/PRE/TARGET/plan；新计划 1 dispatch，APPLIED，1 题 2 框，pending=0，report read=1。 |
| U-execute | 74876 | 8.578 / 7.343750 | 1 target / 1 真实 dispatch 已产生 1 题 2 框效果；执行读回 unavailable，正式 UNKNOWN receipt/progress 与 pending=1/暂停持久化；未发布报告。 |
| U-recover | 58992 | 11.156 / 8.781250 | 原进程已退出后正常打开同一 anchor/ledger/target；固定 call `I01-U-one-MATCH-call`，max_attempts=1、一次独立完整读，MATCH/RESOLVED_APPLIED；0 dispatch，pending=0；一次最终新鲜 report read。 |

E 在首次冻结前根据源码选择允许的等价前置纠正入口。`detect_target_drift` 需要终局基线，新目标未执行任何动作时只能得到 NO_TERMINAL_BASELINE；本任务未调用它伪造 hold，也未进入 hold。旧候选准备失败的事实和[静止双库](../evidence/I01-A/execution/run/cases/E/captures/old-candidate-refused-released/)证明 plans/intents/permits/effects=0、题/框=0、operator epoch=1。正常 release/claim 推进真实 owner/history，原 PRE 预算/旧候选继续保留；新 PRE/snapshot/action/plan 均不同，最终仅新计划在 plans 表接受。没有人为清锁、直接 SQL 修状态或修改旧证明。

U 原 UNKNOWN receipt=`executionreceipt-9d40e3112a374babba8a455eb45c6d25`，hash=`6535fee8a6e08daddd4a737c16bcab536f1cfb5a93fbe6c02cf6fa856b401937`；最终 resolution=`resolution-7be05f3b8306477fbe6af722348aa2e7`，hash=`63d62b2fb28771ab4f6393a516b27a8060749f67153f8a2d168a3ed0ac881441`，明确绑定原 receipt 和原 intent。原件在[UNKNOWN 现场](../evidence/I01-A/execution/run/cases/U-execute/result.json)与[恢复结果](../evidence/I01-A/execution/run/cases/U-recover/result.json)均保留；新 APPLIED 回执引用解决链，attempt_fact 仍为 MAY_HAVE_BEEN_ATTEMPTED，没有改写成最初成功。

## 次数、报告和释放

| 路径/边界 | fresh target | dispatch | 实际 annotation effect | operator | INITIAL/PRE | 执行准备读 | 执行结果读 | reconcile read | report read |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N | 1 | 1 | 1 | 0 | 1 | 1 | 1 OK | 0 | 1 |
| E | 1 | 1 | 1 | 1 | 2 | 2（旧拒绝＋新准备） | 1 OK | 0 | 1 |
| U 全路径 | 1 | 1 | 1 | 0 | 1 | 1 | 1 UNAVAILABLE | 1 MATCH | 1 |
| 累计 | 3 | 3 | 3 | 1 | 4 | 4 | 3 | 1 | 3 |

目标持久 observations 行终局 N/E/U 分别为 4/6/5；U 执行阶段为3。它们包含故障 unavailable 观察，不能全部叫完整成功读。另有8个真正有界 native 只读子进程（4 PRE＋1恢复＋3报告），均保留实际 PID/输入/脚本/raw流/exit/timeout。effects 每路径1行且 mutated=1；题数另以独立 target state 的 questions=1、frames=2 核对，不拿 effects 行数充当题数。

N/E 正常 run_plan 各自动 publish 一次；U UNKNOWN 阶段0次 publish，MATCH后1次。三份正式 POST 的 frame_structure=PASS；三份 BatchReport 均 total_expected=1、scope_manifest=1、questions=1、state=CONTENT_PENDING、content_check_status=PENDING、submission_status=NOT_SUBMITTED。没有把框结果升级为内容核验或完成。

子worker180秒、每阶段父240秒，read2秒、entry8秒、gate5秒、lease10秒/renew2秒及 PRE/currentness/恢复期限全部保持。六个父阶段累计 wall 43.735秒，无业务超时；不作性能或SLA结论。

固定 T1 capture 的 SHA256 为 `3e07d56f409d8203c42f252f7a2900e902e31f56e1ff5fc7475335d33d0b042b`。自有 keeper 全部真实 stop/join、同步业务结束和 owner 释放后共保留5组/10份 raw SQLite，顺序双库复制不称原子快照。SQL只对自有静止副本以 `mode=ro&immutable=1` 打开；重新查询与 SQL.json 完全一致，事件hash/head、意图/许可、实际目标变化及读取计数核清。当前6份 released primary 与各自最后 capture 相等；U旧UNKNOWN capture保持历史原件，没有回滚活源。

[release.json](../evidence/I01-A/execution/release.json)列21个已结束的登记PID（19个预检/阶段/worker/native-read进程、顶层runner、最终静态审计），原进程退出经wait核实；复用PID按创建时间与原完成时间区分。所有业务worker结束只剩MainThread；runtime owner/PID为空、lease=0、phase=RELEASED。没有为释放删 pending/hold。工具层顶层调用的回执见 [top-level-tool-receipt.json](../evidence/I01-A/execution/top-level-tool-receipt.json)：顶层stdout由exec工具捕获，无独立OS raw流；所有业务阶段及worker/native-read有独立原始流，不补造顶层流。

## 首次静态失败及纠正

1. 首冻结5个A01历史JSON被Git的 `*.json text eol=lf` 转换。固定[差异原件](../evidence/I01-A/execution/first-freeze-byte-mismatch.json)后，唯一包纠正在任务夹具目录加入 `.gitattributes` 的 `* -text`。普通add未重存既有文件，静态检查仍5差异，保留[staging记录](../evidence/I01-A/execution/correction-staging-check.json)；显式 `add --renormalize` 后修正本次尚未运行的纠正提交。中间打包提交`81f94c8b07337bffe7508b8b5923a84c31d5e6a2`未执行，最终纠正为be68b8d7。首/末冻结业务驱动 bytes相同；0公共消费/target/dispatch消耗，无第三业务候选。
2. 全部业务结束后的首次静态审计用正斜杠排除Windows路径，重复计入U旧capture而触发汇总断言；保留[first-audit-source.py](../evidence/I01-A/execution/static-closure/first-audit-source.py)及[first-tool-failure.json](../evidence/I01-A/execution/static-closure/first-tool-failure.json)。只改静态路径匹配，最终审计真实子进程exit0。未改产品/业务驱动/预期，未重跑业务。
3. 静态释放探针最初将复用PID36852误视为原进程仍活；保留[错误记录](../evidence/I01-A/execution/static-closure/release-first-tool-failure.json)，改为核对进程创建时间。当前复用者在原预检结束后创建，未被终止。两次初始静态工具失败只有工具返回trace，无单独捕获的PID/raw stderr，未伪造缺件。

## 实际命令与当前A接口资料

实际执行（原目录输出已存在，不得原地重跑）：

```powershell
Set-Location D:/1800-worktrees/i01-a
python -X utf8 -B examples/i01/prepare.py
python -X utf8 -B examples/i01/preflight.py
# 冻结最终候选后，HEAD当时必须等于此候选：
python -X utf8 -B examples/i01/run.py --candidate be68b8d7c645de556d601458d1d493258f063721
```

最短业务复现是在自己的全新隔离目录取得上述固定候选原字节（其已含准备视图），然后运行最后一条；不能使用最终交付HEAD去通过候选HEAD守卫，不能复制本次业务数据库。独立验收应按自身任务先固定隔离路由/身份和计数，使用自己的新状态、自己的有限三路径，不在作者目录运行。

| 可导入A接口/消费者 | 组合中的适用范围与实际调用 |
| --- | --- |
| `annotation.contracts` 的 SourceBundle/EvidenceBundle/QuestionGraph/CheckReport/ApplyPlan/ExecutionReceipt/BatchReport、schema、load_bundle、validate_bundle | 当前 C01 `1.0.0-a-proposal` 类型及资源/引用校验；`python -X utf8 -B -m annotation.contracts.cli validate <exchange.json>` 为公共消费方式；本次由public.py真正调用一次CLI。`load_bundle(path, verify_assets=True)`验证资源，不能以JSON合法替代业务正确。 |
| `annotation.source.static.load_static_bundle(path, expected_book_id='46007447')`；`examples/a01/consume.py` | 本组合的既有A01归档消费者，公共/A01一致、完整图像解码、限定书籍与页映射；等价直接命令 `python -X utf8 -B examples/a01/consume.py <exchange.json> --book-id 46007447`。本次实际执行脚本为基线raw-view下该文件。保留coverage_eligible=false。 |
| `annotation.quality.targetcheck.SimulationConfig/check_target`；`annotation.delivery.planner.create_plan` | 已集成A02的synthetic目标检查和规划，不是B真实候选/平台许可。 |
| `annotation.contracts.a03_native.select_native_codec`；native PRE/runtime/receipt/reconcile/publisher | 本次实际1.4内部固定synthetic入口，需要正常持久registry和真实process-private资格；串行化PASS/外来context不授资格。fresh-native-only，LEGACY_INITIAL_ONLY，不支持旧库迁移。 |

`PYTHONPATH`须指向组合基线的固定raw `src`，`PYTHONDONTWRITEBYTECODE=1`；本次真正调用的完整argv/cwd和导入摘要在process/import记录，不把上表示例命令补记为额外执行。

B内部0.4/0.5/0.6/0.7的接收适配/拒绝及公共消费联调仍为 **PENDING_A**，由A06另行处理。本次未读取B包或猜测这些版本语义，也未联系B；此表仅提供当前A可用入口和版本资料。

## 限制和交付

本交付分别证明A01真实离线档案的公共消费与A内部native固定桩集成。真实 A01→native 闭环、B共同合同/联合联调、S01、真实平台/A04、OCR/内容、DB迁移、题22/书级送审均不在本次结果中。零网络/浏览器/profile/凭据/模型/付费/push/外部消息；没有访问旧A03/T3/L1状态。

[manifest.json](../evidence/I01-A/execution/manifest.json)对本报告、驱动、夹具、原始流、执行字节、静止双库与资源提供长度/SHA256，明确自身排除和交付提交定位方式。作者只交 **REVIEW**，独立验收和调度另行决定有限接受及集成。
