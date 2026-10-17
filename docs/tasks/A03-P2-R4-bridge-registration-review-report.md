# A03 P2-R4 桥接接口与登记分支独立复核

2026-10-17，Asia/Shanghai。**整体 REWORK**。两项分别为：**接口方案 ACCEPTED_DESIGN_LIMITED**（仅限19个现有入口盘点、一个拟议PRE边界和版本/资格责任设计，可用于制定有界实现任务）；**登记分支 REWORK**（冻结正包被无消费者上下文的全局证据遍历错误拒绝）。target负控仍是被遮蔽的BLOCKED项，不能记为有效拒绝。原R3、SESSION-02、CONVERSION-07有限静态接受保留；A03功能、oracle、公共/B采用与I01均未通过。

## 冻结版本与输入

| 项目 | 精确值 |
| --- | --- |
| 审阅workflow | `cb6b8336555e52deaf129c0c1eccf27ea830d098` |
| 任务单SHA256 | `454388a8db52bc8eb65c62ef3eb637f0a68a03deab4e508b4c005854ebf5a7db` |
| base | `87606b73e0754fa670491d9fb958a416c26bfe88` |
| target | `e608b54b973b14ff55dd2c4530153f5fe7c931f4` |
| 执行workflow | `ef1d2f4a20971b416afae500889aa5c090dfe89b` |
| 执行报告SHA256 | `95cf2746bb9ceb5a1857f3e8babca04892d8481c74c11d3ee256d5eeb26055f9` |
| 作者清单SHA256 | `5c5823f1b146574202fbfd00e066aafc1697d017e40c12cab66b9330cb75d28e` |
| 接口提案SHA256 | `b57d0af5d72a03c4b16e6eeedc267bda50f1dfcf022728b1f107f5b158a22207` |

从精确workflow raw Git读取[复验任务](../evidence/A03/review/P2-R4-bridge-registration/input/workflow/docs/tasks/A03-P2-R4-bridge-registration-review-handoff.md)、执行任务、R3调度收口、AGENTS/coordination及前检；架构/公共合同与上轮已读字节相同，SHA分别为c2b5dce8b862d6d274d87ce75cbbb844d75b12e6c3e6885884984b0b5c321b5f、8fdc31e5b6671f4995ea95b3271b916d784c300336a9ee1420e79dfb3ccfcaae。保留用户当前思考设置，未改档、委派、合浮动主树或联系其他对话。

[交付字节索引](../evidence/A03/review/P2-R4-bridge-registration/delivery-byte-index.json)独立核对110清单项及清单自身共111新文件，raw Git长度/SHA1/SHA256一致且只在授权范围；28,002旧Git路径/mode/type/blob不变。38份来源输入逐项核对：6 workflow文档、12产品文本、15静态输入、5资源；复制副本与各自确切原Git字节相同。

[输入索引](../evidence/A03/review/P2-R4-bridge-registration/input-index.json)隔离133份必要文件到本轮input目录，排除7MB旧baseline，未复制历史全集。产品源码仅留在inputs/product-text供AST/文本读取，未加入产品导入路径。执行工作树保持只读；其干净/完成状态来自冻结前检和7个退出记录，不冒充本轮OS或profile扫描。

## 1. 接口方案：有限设计接纳

[AST审计](../evidence/A03/review/P2-R4-bridge-registration/interface-ast-audit.json)对12份原始产品文本解析，不import产品。19个现有入口的qualified name、精确签名、起止行、source blob/SHA及函数片段SHA均与机器表一致。拟议 `src/annotation/quality/synthetic_precheck.py::admit_a03_pre_run` 在base指定路径尚不存在；BridgeSelection、BridgeContext、ValidatedA03Bundle、AdmittedPreRun、HistoricalDerivationView、CurrentWriteEligibility明确是提案，不能假称已有API或证明。

| 现有入口组 | 独立源码核对及方案边界 |
| --- | --- |
| contracts 6入口 | dispatch/seal/readiness与C01、1.1 recovery validator/readiness分支一致；现有产品无1.3接纳。新方案要求独立typed codec及完整业务/字节/ref规则，保留1.1历史读，不能只加版本白名单或改标重封签。 |
| targetcheck 3入口 | make_artifact继承anchor版本，当前依赖按id/revision去重；analyze_target真正计算状态/授权/能力/政策/覆盖；check_target生产报告。提案要求确切四元组冲突拒绝、新1.3 factory、真实TARGET计算与PRE证明，保持原业务判断。 |
| planner 4入口 | create_plan按question生成动作并重算TARGET；verify_generated_plan完整包校验后作历史重建；observation/state桥接当前仅1.1。新方案保留生成/事实比较，历史派生视图不能删改已接纳UNKNOWN/登记历史或获得当前资格。 |
| persistent mock 6入口 | create/open绑定descriptor，_verify_observation读取独立持久行并校验资源，snapshot由该观察产生；prepare签发真实对象，verify核验对象身份/摘要/实际行及binding。提案保留能力身份，runtime另管登记/fence/head/预算/permit。 |

细节见[函数原文及提案对照](../evidence/A03/review/P2-R4-bridge-registration/interface-source-excerpts.json)。源码中observation bridge返回的19个字段与提案 `binding_fields` 精确相同，包括prepared_before、完整applied_prefix、effect_log_delta、两个snapshot refs和hash/version；book由target_key绑定。PreparedAction/VerifiedPreparedAction的身份、持久观察凭据与当前写入permit明确分层，未把JSON、PASS或重开句柄视为新能力。

方案把结构合法、质量PASS/实际PRE接纳、runtime当前写入资格分开；旧1.1只读、当前1.3静态profile不可派发、未来确切采用记录及native证明齐备才可能CURRENT。错版本/profile/pins、缺运行证明、旧hold、错观察及历史视图冒用均拒绝。此设计足以编制下一份有界实现任务，**不等于已冻结可执行ABI或批准当前profile/oracle采用**。

下一份产品实现任务须先固定三处接口选择，详见[设计判断](../evidence/A03/review/P2-R4-bridge-registration/design-and-residual-assessment.json)：

1. BridgeSelection/BridgeContext的具体字段、角色、确切采用记录及codec/pins，不能仅保留概念字符串；contracts管codec/ref，quality管PRE run proof，runtime管当前资格。
2. AdmittedPreRun的唯一签发/校验回调、输入摘要与INITIAL/POST_HOLD绑定及生命周期；当前oracle尚未采用，不能通过该类型名解锁。
3. 历史creation-input anchor及非导出派生视图的精确闭包契约；原完整历史始终保留，当前头/提交前缀/fence/持久预算由runtime认证。

这些是后续任务需冻结的有限接口决定，本轮没有实现新类型、修改产品或发明可调用API。

单题链的方向一致：真实新INITIAL/PRE接纳→实际TARGET→真正create_plan→同intent的UNKNOWN且原receipt不存在→只读终局head、original_receipt_ref=null→同intent/fact晚到完整receipt→独立报告读取与新POST/Batch，保持PENDING/NOT_SUBMITTED及旧UNKNOWN。固定初始Graph确有一题，现有create_plan每题生成一动作；这只是条件可达设计，**整条链NOT_EXECUTED**，没有手写READY计划替代生成、恢复旧尾或扩成跨scope聚合。

## 2. 登记分支：REWORK，target控制被遮蔽

四包各在独立进程调用冻结 `closure.Package.validate` 一次，总计4次。未执行prepare.py生成器、R2/R3 main或旧36矩阵，未修改Package/Schema、修规则后重试、换Resource放置或增新候选。

| 冻结完整包 | 实际拒绝与路径 | 真实消费上下文→全局上下文 | 结论／进程退出 |
| --- | --- | --- | --- |
| registration-positive | FRAME_REGISTRATION_BINDING，r4-static/registration-positive/prefix.json | 登记谓词True→全局book=None时False | REWORK_FALSE_REJECTION／1 |
| source-binding-negative | 同码，r4-static/source-binding-negative/prefix.json | Source A与Snapshot/scope B不一致，实际消费路径即False | 预期登记绑定拒绝／0 |
| snapshot-binding-negative | 同码，r4-static/snapshot-binding-negative/prefix.json | Snapshot A与Source/scope B不一致，实际消费路径即False | 预期登记绑定拒绝／0 |
| target-tuple-negative | 同码，r4-static/target-tuple-negative/prefix.json | scope/book谓词True→全局book=None时False | BLOCKED_TARGET_CONTROL_MASKED／1 |

每份完整bundle、资源、case原件在input/checkout固定目录，实际独立结果在[cases](../evidence/A03/review/P2-R4-bridge-registration/cases/registration-positive/result.json)。退出0只表示两个直接负控在期待层拒绝；两个退出1保留正包缺口及target控制遮蔽，不算审阅工具失败，也不把相同错误码都记为语义通过。

独立重算每包10个Artifact、8个Resource和6事件的原字节/内容hash，核对所有普通exact refs、从sequence1/zero前驱至head6的完整链、journal/target key、accepted anchor及plan action digest；均无摘要损坏。六个frame各自声明了所消费全部普通ref，外层Source仅声明subject plan A，合法typed frame在同书scope B使用自己的声明。Source/Snapshot负控故意拥有异scope引用；正包及target负控则没有这种声明/scope问题。

[冻结值核对](../evidence/A03/review/P2-R4-bridge-registration/frozen-value-audit.json)进一步确认：正包的Source/Snapshot exact refs同书同scope B，登记payload/frame scope、Snapshot授权scope、canonical target、观察及Snapshot state hash/version自洽。正式路径是 `1.3 Source.external_page_mappings[].evidence_refs → EvidenceRecord(proof-r4-registration).resource → 完整typed prefix`；固定Schema的正式ID/Resource定义没有禁止该JSON证据放置，prefix确在Resource根。不能仅把它换位置绕过当前失败。

这些核对证明本轮指定字节、引用和登记元组没有导致正包拒绝的自身矛盾；完整入口仍在后续混合DAG、消费者统一声明和最终hash阶段前停止，不能据此声称整包全部业务规则或native历史已通过。journal、registration和观察均为明确的合成值，不代表真实登记行、会话或可达运行。

### 最短实际失败路径

本轮确定缺口编号 **R4-REG-GLOBAL-CONTEXT-01**，直接使用冻结正包，不另造反例：

`Package.validate → 1.3 Source消费者 → 正式EvidenceRecord → prefix.frames[5]登记谓词（book=synthetic-r2-book，通过） → 返回实际消费扫描 → R2 validate:87全局evidence扫描（book=None） → 同prefix.frames[5] → R2 scan:70 FRAME_REGISTRATION_BINDING`。

证据不是作者诊断复述：在四次真实完整入口运行中，用只读sys.settrace记录继承guard行的实际locals、活动上下文、谓词输入及异常。正包第一次guard有真实book，第二次活动上下文为空、book/scope均None；失败严格来自这里。Source和Snapshot负控只到第一次guard就拒绝，尚未进入全局扫描；target负控则与正包一样在第二次guard失败。

继承R2的登记谓词要求Source.book_id==Snapshot.book_id==book及共同scope；全局扫描人为传None使合法book不可能相等。不是版本或摘要错误，也不是R3覆盖层没有正式解析证据。当前登记谓词文本未比较Snapshot.target_id与canonical target；但target负包未被完整入口接受，只能记为**控制被遮蔽／拒绝责任未证实**，不能捏造已成功绕过的target反例。

最小后续范围建议：由调度另派，将全局无上下文的字节/图遍历与真实Artifact/frame消费者绑定检查分开，继续核验全部Resource/正式ID、自己的声明及混合DAG；不能把None当通配符、全局跳过证据或删事件。之后才在同一有限四包范围证明正包接受、Source/Snapshot定位拒绝，并独立落实target元组拒绝。若改成放置限制，须先单独确认正式字段合同，不能当本轮补丁。本轮没有实施或修后复测。

## 实际加载、定向、原始流与释放

| 静态加载输入 | SHA256 |
| --- | --- |
| R4 fixed_entry.py | `a1a7903079f36e45e57a879ac83e16b83c92ed97d5700a489b493d5407476f62` |
| R3 closure.py | `ff650507bca971f8c9418a09e6e4f8df7c7691016841ffe7bd15ff66382579a5` |
| R2 check.py | `7bf3ea27424f7afaf3d3b264d2ab3d0bfa0fdc8bba1c178e6f488bef09e6257b` |
| R2 schema_check.py | `9630d7e2e0d3700080f7a97a9c883877acf27929be82a41ed5a8f041240ccf7c` |
| R2 oracle_verifier.py | `6667659ccc71cf1c0769d2ca7c684021140046a71a2ca73e40699aa354afac2d` |

加载器和依赖均先读再运行，只做静态值校验；oracle模块虽为固定依赖加载，未调用比较或采用。独立加载器仅将R4 fixed_entry模块的OUT赋值定向本轮目录，输入ROOT不改；原固定加载器再仅定向R3的base.EVID。Package类AST前后相同（含位置），摘要 `df0133704f9cb876a1d530d629a8a65a1f5ff45bf86129a4d68612e66f8085e4`。没有更改Package、Schema、predicate、lookup或判定分支。sys.settrace只观察，不改变返回或异常。

七条自有记录运行依次为freeze、接口AST、四包、冻结值核对，退出0/0/1/0/0/1/0；全部wait结束、未超时，无后台worker或native session。每条run在启动前打开stdout/stderr并保存argv/cwd、源码快照/SHA，随后保存PID与结束记录。PYTHONPATH移除，-X utf8 -B/PYTHONDONTWRITEBYTECODE=1；四个包校验子进程没有启动其他进程，导出/AST脚本的只读Git调用均同步返回。见[释放记录](../evidence/A03/review/P2-R4-bridge-registration/process-release.json)及runs原始流/退出。四包及AST/值核对没有审阅驱动错误或重跑；其后的封存入口错误单列如下。

作者7次运行退出0/1/1/0/0/1/0及失败材料保持：prepare-01的正包残余是语义失败；assess-01定位错源文件是作者诊断工具错误；verify-01封存前自链接检查失败是作者归档工具错误。assess-02/verify-02修正的是诊断定位/待生成链接边界，未产生第五次Package调用。本轮不将这些错误改写为产品通过；作者另一次未封装读取失败仅有工具轨迹，未重建冒充文件证据。

四包完成后的首次未封装封存命令退出1，工具返回Non-UTF-8源码SyntaxError；[错误记录](../evidence/A03/review/P2-R4-bridge-registration/archive-entry-error.json)保存工具原返回及证据限制。事后复制的源码可完整UTF-8解码，[快照](../evidence/A03/review/P2-R4-bridge-registration/scripts/archive.attempt-01.py)不能冒称失败时字节；编码状态原因未确认。随后仅补显式UTF-8声明及本说明继续封存，没有修改验证语义或重跑四包。这个错误属于审阅归档入口，不归为交付或产品缺陷，也不伪造为启动前持久化日志。

只读复现入口（本轮没有再执行；抑制mkdir并丢弃结果文件写入，Package/guard不变）：

```powershell
# 正包应再次报告FRAME_REGISTRATION_BINDING并退出1
python -X utf8 -B D:/1800/docs/evidence/A03/review/P2-R4-bridge-registration/scripts/read_only_replay.py registration-positive

# 只核对归档字节、输入及退出记录，不调用Package或产品
python -X utf8 -B D:/1800/docs/evidence/A03/review/P2-R4-bridge-registration/scripts/archive.py
```

## 冻结与限制

只新增本报告及本轮审阅目录。结束核对133份输入及2,597份旧审阅文件字节不变；完整[SHA256清单](../evidence/A03/review/P2-R4-bridge-registration/sha256-manifest.json)覆盖所有新增输入、脚本、样例、结果、原始流/退出和报告，仅排除清单自身；[终检记录](../evidence/A03/review/P2-R4-bridge-registration/final-verification.json)记录核对结果。没有提交、推送、集成、改state或联系执行者/B/其他任务。

未执行产品/planner、DB打开或查询、native session、网络/浏览器/平台/profile/凭据/OCR/模型/收费API或安装依赖。旧DB仅原字节保全，未打开数据库。R3及SESSION-02/CONVERSION-07的有限静态结论不扩大为登记分支或整体恢复通过。R17真实链仍BLOCKED，oracle/原生profile/跨侧合同未采用，I01不释放。

字段重置专项保持 **NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION**，未复跑、变形、委派或建议再测。确认上述直接缺口后到此冻结，由主调度另定最小后续范围。
