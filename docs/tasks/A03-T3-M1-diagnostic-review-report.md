# A03-T3 M1 诊断独立复核

2026-10-18（Asia/Shanghai）。**ACCEPTED_DIAGNOSTIC_ONLY。** 固定诊断的探针、主要计时/栈结论、计数与释放足以支持调度采用下述最小修复。无需补一次诊断、基准或独占profile；优化尚未实施，性能收益未经验证。M1/M/A03仍REWORK，I01未释放。

## 固定依据与范围

| 身份 | 确切提交 |
| --- | --- |
| 本次复核workflow | `d6357927b004ca6287e169d3efb208859ad731c9` |
| 诊断采用workflow | `c077c2c77901d1df754ffeee4a0004162323a579` |
| 最终交付F | `7b9245eaa55bad1699ee40baf71be09dd6df8371` |
| 业务前诊断候选D | `ae2e71f9262dd7654d99ad11f916b71b2461bf58` |
| 前版T / 产品C | `3f39a117b1b98e85c5a449a07f13b3490ef77e18` / `c73070884476dc2edcb952d88e4f6ed356b74ae8` |

已核本次交接raw SHA256 `29d9ab54a9da175d8851ac8da829fec18cdea5d832454c9dae27d1e1c2cff49d`；F执行报告 `27441a9b7059bb5f4f9d29f7abfa70e6093f983e756f69c1e8d13cdaa707b5f3`；新index `33fe3cbb728089abbddc3e7914fb985cb7581f460770e0017b8e8ff20565c79c`。index的233成员已由调度入审，本轮不逐项重哈希或复制；只读取必要日志/JSON/固定源码。独立复算与引用见[小型记录](../evidence/A03/T3/review-M1-diagnostic/recalculation.json)。

产品/输入/capture/根依赖从C到F无差异；D后产品、诊断驱动/辅助及输入未变；T的旧M证据目录无差异。原263成员未重封。所有数据读取来自Git blobs或既有SQL.json，产品导入、SQLite连接、新诊断/业务运行均为0。

## 探针、期限与现场

T→D的run.py变化以计时包装原调用，实参、顺序、M1故障选项和异常重抛保持。DiagnosticTrace仅读时钟、线程标识和LeaseBoundary.snapshot内存；已读snapshot原文，它不check/renew或访问目标。未monkeypatch产品，未增加目标观察、重试或跳过校验。diagnostic分支在before-execute capture之后启用5秒faulthandler，退出先cancel；无新增Python计时线程。publisher/finish后继明确禁用，与本次诊断授权一致。

子仍45秒、父仍90秒：worker PID4444实际45.016秒超时，kill/wait、exit1、alive=false；父PID9920为54.797秒、exit0，含准备/释放，表示诊断流程结束，不是业务成功。日志kill前是明确非原子活动读取，kill/wait后长度与摘要吻合保留原件：calls 43236B、stacks 32878B，没有等待补齐日志的循环。日志读取/调度有开销，实际45.016不是获准延长业务期限。

由清理后SQL导出及前后public JSON独立核对：

- 新起点1；dispatch方法ENTER为3，实际DISPATCH_STARTED=2、effect=2、观察=6、PRE=1。
- intent=3；permit为CONSUMED、CONSUMED、ISSUED。第三intent仍PENDING，没有第三实际dispatch/effect；不能把ENTER算成第三次已派发。
- publisher/report-read、reconcile/calls/resolution、finish及M2/M3均为0。before/after动作及effect_log一致；清理事件头17→20，只增加正常owner生命周期，计划INTERRUPTED/cursor2。
- 先保留终止DB/当时存在sidecar再正常open，未声称双库原子快照或终止瞬间SQL；随后一次既有lease剩余等待8.671850秒，不延长lease、不循环，一次claim/release。最终owner=null、lease=0、RELEASED，**pending=1、paused=true保留**，只余辅助MainThread。

四个登记Python过程完成记录吻合：父、worker、观察子PID13968、释放辅助PID43780。观察子的完成文件未单列waited字段，不补称有该字段；本轮不因此另开包装日志补证。旧诊断DB永远保留证据用途，不能在其PENDING上继续验证修复。

## 原始调用与栈复算

逐行配对79行calls.jsonl，得到**38个完成区间、3个未完成区间**，完成区间的原始行号及wall/process/thread纳秒差与作者call-summary逐项一致；无ERROR。未结束者是worker（行1）、execute_api（行24）和第三dispatch（行79）。外层区间不能与内层相加冒充独占耗时。

| 第三动作边界 | 相对worker首行的单调时钟 |
| --- | --- |
| prepare返回 | +37.468秒 |
| commit_intent返回 | +41.500秒 |
| permit返回、dispatch ENTER | +44.015秒 |

首行至末次ENTER：wall=44.015秒，process CPU=42.265625秒，主线程CPU=42.234375秒，主线程约占wall的**95.95%**。这是最后日志点累计，不是kill瞬间CPU，也不是某函数独占占比。探针和JSON日志开销未单独隔离，不用旧M1进度差反推加速/探针成本。

从原始stacks.txt独立识别七组、每组两个线程；218个已输出帧的行号/函数与stack-map一致，关键产品/驱动帧与固定C/D原文和摘要相符。raw组起始行为1、36、75、99、130、173、207：

- 第1、5、7组命中_issue_context→_validate_value及资源/恢复/C01投影；第7组明确在storage._validate→native._append→commit_intent内。
- 第2组命中validate_native_bundle→_validate_value及prepared/计划绑定；第4组命中select_native_codec读取实现pin，并在prepared验证/dispatch祖先下。
- 第3组为schema方言/deepcopy，第6组为资源递归/copy_json；原栈没有输出业务API祖先，未补造。
- keeper第4、7组在gate获取中，其余在2秒事件等待；没有主线程gate/SQLite等待采样。可存在短时等待，但不能据keeper等待宣布主线程死锁。

arm在+5.922秒，七组名义偏移为+10.922至+40.922秒；没有真实dump wall时间。最后一组仍在第三intent，此后intent/permit均有EXIT。第三dispatch ENTER后无新栈，不能指定kill时内部行号；也不把本轮位置倒填成旧M1的位置。周期采样不是独占profile。

高主线程CPU、持续完成的调用和重复校验栈，足以将**首个最小修复范围**收敛到同次重复完整验证；不足以断言它是唯一热点或保证修复后45秒通过。这个限制不要求再运行诊断或基准。

## 最小修复边界

重复链在C中成立：`runtime/storage/__init__.py:109–111`先bridge_for，经过 `storage/native.py:68–71,251–252` 到 `contracts/a03_native/__init__.py::_issue_context:111–118`，执行一次_validate_value；随后 `contracts/recovery.py:1011–1015` 分派validate_native_bundle，在native合同的170–176行又完整_validate_value。不是把每消费者闭包当作重复而删除，也不是删掉native._append的验证。

推荐调度一次采用以下**四个最小文件**，不改公共C01、planner/mock/targetcheck、schema/oracle、输入、capture、legacy CLI或根依赖：

| 文件 | 最小变化 |
| --- | --- |
| `src/annotation/contracts/a03_native/__init__.py` | 提取私有“完整验证一次并签发context/NativeBundle”路径。内部返回此次已验证data、实际manifest与真实context；可由共用私有发行逻辑承载，不能开放already_validated/skip_validation参数。保留现有bridge/context及公开消费者重验语义。 |
| `src/annotation/runtime/storage/native.py` | 增加NativeRuntimeStore._validate专用覆盖，只消费上述同次私有结果；保留NativeRegistry的root登记和实际registry身份。不要修改基类_validate而影响legacy，也不从传入NativeBundle直接继承一次旧通过。 |
| `src/annotation/contracts/a03_native/data/profile.json` | 仅同步这两个实现的实际implementation pins。 |
| 同目录`adoption.json` | 同步实际profile摘要，不改采用范围/版本或借此迁移旧DB。 |

建议私有接口契约可表述为 `_validate_native_for_registry(registry, bundle, asset_root, ...) -> NativeBundle`（名字为建议，当前不存在），但必须满足：

1. **每次调用重新验证**：从当前输入生成稳定数据副本，用新的reader执行原_validate_value完整函数一次；实际资源字节/摘要、StaticPackage、恢复闭包、scope/时间、intent/resolution、issue归属、receipt/progress、C01私有投影及reports均保留，不能仅取旧manifest或先前PASS。
2. **发行仍有真实身份**：沿用_REGISTRIES/_CONTEXTS的本进程身份关系、显式root严格解析/一致性和当前select_native_codec真实pins核对。data的canonical摘要、reader实际manifest、context、NativeBundle必须来自这同一次结果，不能接收caller自报的“已验证元组”。发行/返回时保留_registry/require_context应有的root/registry/pins/包身份检查，不能让检查只在进程启动发生。
3. **不跨调用复用资格**：即使输入是已有NativeBundle或相同hash，下次仍重新读实际bytes/pins；不得全局缓存通过、共用别的consumer声明集合或把JSON/context描述当回调能力。binding/historical语义与旧入口一致，不把静态context升级成dispatch资格。
4. **运行守卫仍在原时点**：公开validate_native_bundle、derive/bridge和prepared/计划消费者继续重验；NativeRegistry._current/_pre_lease、owner/generation/head/pending/hold/fence、intent/permit、期限和实际效果前检查保持。native._append:518–525仍调用完整的self._validate；父类_append只保存，不能代替它验证。

这允许消除RuntimeStore._validate中的确定双遍，却不顺带删issue_first_dispatch/dispatch等公开消费者的校验。其他重复路径和pin读取仍可能有成本；本轮不扩大优化范围、不许诺加速比例，也不代执行者实现上述路径。

## 有限验证建议与下一步

**诊断材料必要修订：无。** 推荐调度固定上述有界修复提交，并把验证放在同一修复包内，不逐helper开任务：

- 用既有合格native值/registry夹具检查新私有返回的data、manifest、context/root与旧严格入口一致；公开入口仍能重新核对。静态确认每次新路径只有一次完整_validate_value，实际pins与文件匹配。
- 从既有门禁控制中最多选择8个具名单差量：缺嵌套正式引用、第二consumer借用声明、错书、错scope、成功调用后实际资源字节变化、成功调用后实施pin变化、错误root、伪造/未登记registry/context。资源变化项同时检查新私有入口再次调用及旧context公开消费仍拒绝。它们是已有拒绝边界在新路径的回归，不增业务题型/标准；允许按相同consumer合并，不能只用旧公开入口的早拒代替新路径闭包验证。前置控制不dispatch，不新开目标业务。
- 再用**全新现场**验证原M1三动作正常执行、正式receipt/progress/单次新鲜报告及重开/旧计划拒绝；保持子45/父90秒、gate/lease/PRE上限，新增1起点、dispatch≤3，不继续本次PENDING现场。是否达标由真实结果决定；仍超时就冻结现有结果，不自动追加诊断/基准或第二起点。
- 若调度在同一次任务中继续安排尚未运行的M2/M3四例，各仍一次、各dispatch≤2；M1失败则后继NOT_RUN。该建议修复轮新业务上限合计5起点/11dispatch，应由调度明确，不能默认为本轮已授权。历史两起点及实际4dispatch/4effect不核销；不复跑T1/T2、旧矩阵、L/G/F。

本次只接受诊断及最小修复建议可供采用，不接受未来修复代码、性能或M功能。当前没有缺少外部信息造成的BLOCKED，也不需要为旧包装日志/旧journal无SQL再开补证循环。

## 退出与权限

本轮只写此新报告及一个小型复算/引用JSON，未运行作者脚本、产品、SQL或目标；未改变原233/263成员、产品、执行树、协调JSON、Git索引/提交。记录中的只读Git进程均已communicate/wait结束；无自有业务进程、owner、keeper、后台或profile会话待释放，不作全机PID扫描。

field reset=`NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。无网络、平台、凭据、安装、费用模型、OCR、推送、A05题22或书级提交；不联系B/退役A03、不委派。结论为ACCEPTED_DIAGNOSTIC_ONLY；M/A03仍REWORK，I01未释放，等待调度固定产品修复任务。
