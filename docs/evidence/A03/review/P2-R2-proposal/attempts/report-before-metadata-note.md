# A03 P2-R2 提案独立静态复验报告

日期：2026-10-17（Asia/Shanghai）。整体结论：**REWORK**。按xhigh续派做一次有界复验；未派发智能体或其他对话。

三个指定缺口中：SESSION-02与CONVERSION-07的本轮值级修复可作**有限静态接受**；typed frame的双scope正包已成立，但完整SCOPE-01仍有一条正式EvidenceRecord消费者链漏检。本轮冻结一个最小反例后收口。R17版本桥接和登记推导scope独立正包另列 **BLOCKED**，不把它们伪装成已发生的运行失败，也不把局部静态结果升级为native实现获准。A03功能仍未接受，oracle未采用，I01不释放。

## 1. 固定输入、字节和真实运行目录

| 项目 | 精确值 |
|---|---|
| 本次复验workflow | `0a668650f3dfdc00898032fb9c89e96694260d23` |
| 被验交付 | `526d264284f36f856c306db88c1d7e71c04152e1` |
| base | `7fdbde8f16569fd3bc399013115e13269d5d33fa` |
| 执行workflow | `d834bf531f95abac7ed30b89b3ca55105fa6f491` |
| 执行报告SHA256 | `e6df1732e7a3623047a4ed02457a1d5b453cb2aae3253a3913426a00fcf5b218` |
| 作者清单SHA256 | `75f158577e48f029e542674ad5216df0b41ea02df69e76cf646cd35f4a83ed64` |
| 唯一候选 | `examples/a03/P2-R2-proposal/candidate-final/` |
| profile / raw SHA256 | `a03-p2-r2-static-2-PROPOSAL` / `f7385ba20090b5df8aa062c417e3d5c66a889a30f464facff994d9929b94f9ea` |
| API SHA256 | `b5210ab175ccfd3f1f8f6baf0da07a3757dac732decf3bfa3de0b65354b0eba8` |
| oracle / verifier SHA256 | `659a715bd293026e28ec50f6bccbe1cecdf6511d168afc9f98d9ab05f6e8efb9` / `6667659ccc71cf1c0769d2ca7c684021140046a71a2ca73e40699aa354afac2d` |

先读取固定workflow的 [handoff](../evidence/A03/review/P2-R2-proposal/input/workflow/docs/tasks/A03-P2-R2-proposal-review-handoff.md)、[原任务](../evidence/A03/review/P2-R2-proposal/input/workflow/docs/tasks/A03-P2-R2-static-rework.md)、[调度决定](../evidence/A03/review/P2-R2-proposal/input/workflow/docs/tasks/A03-P2-R1-proposal-coordinator-decision.md) 和 [前检](../evidence/A03/review/P2-R2-proposal/input/workflow/docs/evidence/coordinator/heartbeat-20261017-0734/A03-R2-delivery-preflight.json)，未合浮动主树。

[交付字节索引](../evidence/A03/review/P2-R2-proposal/delivery-byte-index.json) 独立核对205项清单及清单自身，共206新路径，全部raw Git blob长度/SHA1/SHA256一致且在三处授权范围；base的27,670个旧路径/blob未改。没有使用git archive断言原字节。工作树干净及执行完成/10个静态run退出来自冻结预检和执行记录，不冒充本轮OS/profile扫描。

[输入索引](../evidence/A03/review/P2-R2-proposal/input-index.json) 最终隔离122份必要输入：初次121份，加profile明确指向的一份历史前缀Schema，见 [source-pin-export](../evidence/A03/review/P2-R2-proposal/source-pin-export.json)。当前候选45文件；六份Schema、API/oracle/verifier及来源pin均按精确集合核对。原R1 candidate-v2及失败candidate不作别名，不复制309份历史全集。

真实目录 `D:/1800/docs/evidence/A03/review/P2-R2-proposal/input/checkout/`，候选与检查器逐字节匹配固定提交。产品planner只是冻结文本输入，已与该交付原Git源码逐字节比较，**从未import或调用**。检查器及两个依赖完整读过：只用stdlib/本地有限Schema与固定oracle比较，没有产品、DB/native或网络调用。PYTHONPATH移除，-B/PYTHONDONTWRITEBYTECODE=1。有限Schema解释器不构成完整JSON Schema认证。

## 2. 局部结论及残余阻断

“有限静态接受”只覆盖指定值和字段修复，不代表公共合同采用、12类Artifact全部业务规则或通用准入验证已通过。详表及最小后续选择在 [local-conclusions.json](../evidence/A03/review/P2-R2-proposal/local-conclusions.json) 与 [residual-assessment.json](../evidence/A03/review/P2-R2-proposal/residual-assessment.json)。

| 项目 | 本次结论 | 已证实部分 | 缺口/阻断入口 |
|---|---|---|---|
| SCOPE-01 | REWORK | 15 Artifact、同书original-a/original-b、不同计划、嵌套Resource及typed frame经Package.validate总入口通过；直接frame负例和混合环按指定层拒绝。 | 正式evidence_refs→EvidenceRecord→嵌套JSON Resource未按消费Artifact/frame的上下文展开；一个非frame的未声明/跨scope普通ref仍被完整入口接受。 阻止完整消费者闭包和通用新包准入被接受；不能以typed frame局部成功替代。 |
| SESSION-02 | STATIC_ACCEPTED_LIMITED | 当前正值H0=7、Hfinal=14；三次读的绑定/次序/角色/时间和fact=Hfinal+1自洽。旧损坏会话字段与旧损坏H0字段投影到新basis后分别SESSION_BINDING/H0_CHAIN拒绝，不靠版本差异。 | 真实锁/fence/read/计数持久化/lease/唯一索引/事务CAS均NOT_EXECUTED；共享总入口仍有SCOPE-01缺口。 仅认可本轮指定字段和值级案例修复；不批准native只读事务。 |
| CONVERSION-07 | STATIC_ACCEPTED_LIMITED | 完整目标5节点（Source/Evidence/Graph/Snapshot/PRE）经同一入口；原7节点中4转换、3旧派生只归档、1新INITIAL PRE另列来源；资源/分母/映射闭合，INITIAL/POST_HOLD与COMMITTED唯一点明确。 | 仅静态COMMITTED，实际转换/重开未运行；PRE仍HOLD/UNAVAILABLE，无oracle/registry/native采用；通用消费者准入仍受SCOPE缺口影响。 原新Source unregistered类型矛盾在所列初始包中已修复；不授执行资格。 |
| R17 version bridge | BLOCKED | 冻结planner255–287行在真实检查通过时每Graph question生成一个动作；308–309行的observation bridge明确只接受1.1计划。新初始/PRE为1.3，旧版只读。 | 没有获准的1.1/1.3输入、输出与资格桥接；条件动作数1不等于完整原生路径可达。 阻断新INITIAL/PRE→TARGET→planner→UNKNOWN→晚到receipt/新POST原生全链；不妨碍只读静态模型分析。 |
| registration-derived scope | BLOCKED_NOT_POSITIVELY_VERIFIED | Package.scan68–71行有planless TARGET_DRIFT_HOLD登记/Source/Snapshot同scope推导分支；当前正包只用exact plan推导。 | 无该分支的独立完整正包，不得记为已验证；实际registration行等值另属native证据。 涉及这种planless登记事件的全书前缀尚不能按已验证入口放行；不是已实测的确定反例。 |

## 3. 唯一新增最小反例：正式EvidenceRecord路径漏检

编号 **R2-SCOPE-EVIDENCE-ID-01**。这不是新native能力或字段重置实验，只是两个新JSON Resource、一份隔离Source叶节点和一个完整静态包。候选文件/旧数据均未改。

继承的冻结普通引用规则明确要求：按每个消费Artifact自己的正式evidence_refs ID，经所属唯一EvidenceRecord表解析Resource，再递归检查JSON普通refs、自己的input_refs、同书scope和混合DAG。规范来源及原API SHA存于 [ordinary-reference-authority.json](../evidence/A03/review/P2-R2-proposal/ordinary-reference-authority.json)。本次调度只批准typed prefix.frames子消费者例外，没有豁免普通EvidenceRecord路径。

反例沿原来就存在的正式字段：

`1.3 receipt(original-a).results[0].before_evidence_refs=[proof] → EvidenceRecord(proof).resource → outer JSON → inner JSON → SourceBundle(original-b)`

目标Source是新隔离叶节点，使用另一份中性的text proof，避免依赖环干扰。所有16个Artifact的canonical content_hash、两个Resource的raw SHA和精确四元组均正确。1.3 receipt没有声明该Source四元组，scope也不同；路径不含typed frame。因此应在普通消费声明/scope层拒绝。相同反例也影响旧Source消费者，但 [current-consumer-confirmation](../evidence/A03/review/P2-R2-proposal/counterexample/evidence-id-consumer/current-consumer-confirmation.json) 明确显示新的1.3 receipt同样被影响，不能仅归为旧版本归档问题。

| 证据 | 实际结果 |
|---|---|
| [完整新静态包](../evidence/A03/review/P2-R2-proposal/counterexample/evidence-id-consumer/bundle.json) | 仅本反例数据，不是第二候选或native历史 |
| [结果/资源差量](../evidence/A03/review/P2-R2-proposal/counterexample/evidence-id-consumer/result.json) | Package.validate完整入口及随后session字段校验仍STATIC_ACCEPTED；非只调用prefix子检查 |
| [独立最短命令](../evidence/A03/review/P2-R2-proposal/counterexample-command/completion.json) | 退出1，FAIL_EXPECTED_REJECTION，actual=STATIC_ACCEPTED；原始stdout/stderr保留 |

源码位置为 [check.py](../evidence/A03/review/P2-R2-proposal/input/checkout/examples/a03/P2-R2-proposal/check.py)：scan 50–79行识别ordinary ref/Resource/typed frame，却不解析正式EvidenceRecord ID；validate 87行只以book/scope=None扫描全局evidence Resource，丢弃这次found集合，没有将它绑定回每个实际消费者。因此既无该消费者的声明检查，也无其scope检查/Artifact→证据资源依赖边。

最小修复范围：在唯一总入口中建立唯一EvidenceRecord ID表，只解析合同正式字段，不把任意同名字符串当证据；在Artifact/frame各自上下文递归消费Resource并检查自己的声明、同书scope，连接同一全局DAG。资源字节可以缓存，消费者检查不能被全局缓存跳过。保留已修复typed frame边界，不用禁用全部合法JSON evidence来缩窄合同。只需用此反例应拒绝及既有全包/普通合法证据控制收口，不要求重造大候选、产品或新oracle。本轮按handoff在明确缺口处停止边界搜索。

## 4. SESSION与转换的有限静态证据

作者36条已复现：7个STATIC_ACCEPTED、23个预期拒绝、1组含五项STATIC_MATCH、5个逐项STATIC_MISMATCH；不是36项功能通过，不能将同一组五比较另加成通过总数。见 [author-reproduction/static-results.json](../evidence/A03/review/P2-R2-proposal/author-reproduction/static-results.json)。

[独立结果](../evidence/A03/review/P2-R2-proposal/independent-static-results.json) 额外重算14条事件hash/前驱/序号，H0确为seq7、STARTED前头，Hfinal为seq14；相同binding/gate/session、三读次序/角色及fact seq15自洽。原会话和H0诊断损坏字段投影后由SESSION_BINDING/H0_CHAIN拒绝，没有仅靠1.2/1.3版本差异。多个消费者复用同一不可变fact允许，另一不同fact占同永久key的控制拒绝。三次是静态值里的读记录，实际目标读取0；未测试真实期限、锁、fence、持久计数、lease、唯一索引或CAS事务。

完整转换静态值包含旧7节点的完整处置：4个初始节点映射到1.3，旧PRE/TARGET/plan仅归档有理由，1个新INITIAL PRE另列派生来源；新目标5种初始类型经过同一Package入口，不再出现旧新Source类型不一致。新旧payload/嵌套资源重写、raw复制、摘要与完整分母在该值包中一致；COMMITTED独立指向已落盘manifest，manifest不回指COMMITTED；rename后未COMMITTED及其他五类非完成状态拒绝接纳。INITIAL无hold、POST_HOLD绑定确切hold/head/新观察均有静态正/反值。

这确认了本轮指定会话字段及初始类型/映射/完成点修复；共享总入口的SCOPE-01缺口仍阻止把这些结果当作通用准入通过。COMMITTED是作者构造的协议值，实际转换器/重开/故障没有运行；PRE保持HOLD、五项UNAVAILABLE，无native registry/run。

固定oracle为32×32 PGM的两个矩形和一个stem/answer关系。已读纯静态verifier：分别比较像素/尺寸/raw SHA/页清单、几何/角色/结构、答案关系、覆盖分母和policy；没有用graph hash相等替代五项比较。五项match/mismatch仅对这份固定合成语言成立。oracle及verifier exact SHA可审阅，但本轮**不批准oracle采用、不形成B质量或真实完整性验收**。

## 5. 两个残余的入口影响与最小范围选择

### R17版本桥接：BLOCKED

冻结planner文本SHA=`451796d91b8d6d5da7e077ee8ee73405cf8522abe78b2b45a86faed0fb23fc88`，与交付中的原Git文件一致。255–287行在真实PRE/TARGET=PASS、配置/快照及投影条件满足时每question构造一个CREATE_FRAMES；本fixture单题使条件动作数为1。308–309行observation bridge却明确只接受1.1计划；本提案新初始/PRE为1.3，1.1节点又只读。因此没有证明完整原生链可达，也没有可采用的版本投影/兼容合同。没有执行planner、手写新权限计划、改版本重封签或续旧尾。

供调度选择的最小范围：

1. 暂缓native R17及新初始dispatch；只保留获准后的非派发/只读静态模块工作，完整R17仍待完成，不能记A03通过。
2. 单独明确contracts版本/资格与A02 bridge兼容范围，界定verify_generated_plan/bind_plan_observation及相关mock准备、targetcheck消费者的精确输入输出refs和验证责任，再派有界实现。本文不发明adapter实现或自动授予文件改动权限；公共消费影响仍须双方确认。

两种选择都不剪裁旧计划、不复用旧PRE stub、不续UNKNOWN尾部、不扩成跨计划/scope报告聚合。单头正向流程与多头值层分工按调度决定保留，未豁免R17。

### 登记推导scope分支：BLOCKED_NOT_POSITIVELY_VERIFIED

Package.scan68–71行定义了plan_ref=null、严格TARGET_DRIFT_HOLD登记元组，由exact Source/Snapshot共同scope推导frame scope；但当前唯一正包只有plan推导。分支源码存在不是正向验证，也不证明原生registration行等值。此项是缺独立正包，**没有把它写成已观察到的确定失败**。

调度可选择只暂缓该分支：下一段限明确plan推导和null控制事件；若全书历史包含这个未验证登记事件，则整入口保持阻断，不能删事件或投影账本。另一个最小选择是只补一份小的完整planless登记正包及Source/Snapshot/tuple不一致的定位控制；原生行等值仍须功能阶段。本文没有创建该新包、追加大候选或自动安排下一轮。

SCOPE-01已存在更早的确定漏检；建议首先只收口正式EvidenceRecord消费者，再由调度在上述残余处选定范围。没有把本轮两个有限静态通过自动转换为native启动授权。

## 6. 原件、命令、释放与停止

check-01原READ_TIME失败、退出1和原始stdout/stderr完整保留于本次必要输入；失败candidate全量仍在确切Git及205项字节索引，未用candidate-final覆盖。早期wrapper没有entry源码快照的限制保持，不能用当前check.py重建冒称当时源码。历史NOT_RETAINED按已选调度决定保留为不可修复限制，不改成通过。

本轮静态驱动读过checker/schema_check/oracle_verifier后才import，EVID重定向本轮新目录，原候选/输入不写。父命令 [static-command](../evidence/A03/review/P2-R2-proposal/static-command/completion.json) 退出0仅表示复现和诊断记录完成；SCOPE反例的 [最短命令](../evidence/A03/review/P2-R2-proposal/counterexample-command/completion.json) 退出1是期待拒绝却被接受的实际失败。每条argv/cwd/PID/超时、原始两流和退出均归档，两进程均已结束，无自建子进程、后台worker或native session。Git及文档工具均同步结束；没有全系统进程/profile扫描或终止他人进程。

```powershell
# 只读重现这个冻结静态反例；当前应退出1，不调用产品/DB
python -B D:/1800/docs/evidence/A03/review/P2-R2-proposal/scripts/reproduce_counterexample.py

# 仅核对归档字节及记录，不运行上述反例或产品
python -B D:/1800/docs/evidence/A03/review/P2-R2-proposal/scripts/verify_archive.py
```

旧审查/准备文件2167项长度/SHA在结束核对保持，205项交付及206新路径raw Git核对通过。全部本轮输入、脚本、最小反例、日志、退出/释放和报告列 [统一清单](../evidence/A03/review/P2-R2-proposal/sha256-manifest.json)，仅排除清单自身，Git忽略项明确列入；[final-verification.json](../evidence/A03/review/P2-R2-proposal/final-verification.json)保存终检。

产品planner/任何产品模块执行、DB查询、native session、网络、浏览器、平台、profile、凭据、OCR、模型/收费API、依赖安装和真实书籍动作均0。旧DB文件仅作历史字节SHA保全，没有打开SQLite。未改产品/state/依赖或旧材料，未提交/推送/集成，未联系执行者/B/其他任务，未建轮询或自动化。真实质量与成本未测。

既有字段重置专项保持 **NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION**，未重跑、变形、委派或建议再测。本轮反例只处理正式EvidenceRecord普通引用的静态值，不调用原生授权验证器。

最终为 **REWORK**，保留SESSION-02和CONVERSION-07的有限静态接受；R17版本桥接和登记scope分支分别BLOCKED。合同/实现及oracle采用未获本轮批准，A03功能未接受，I01不释放。报告、反例及释放冻结后结束，等待主调度决定最小后续范围。
