# A09 固定第4题离线入口

只消费已接收 B stage 原 ZIP、固定 proposal 和独立的新 A 用户核准，建立新的 OBSERVED C01 Source/Evidence/Graph 和五项计算 PRE_APPLY。目标、TARGET、计划及回执为 SYNTHETIC，执行为 SIMULATED。入口不连接平台，不调用 A07 准备/执行、A08 接收、B 生产者或持久化 runtime。

范围仅书46007447第一课时第4题。一个逻辑题对应 Q/image、Q/text、Q/text、A/text 四框。fill_blank 在 C01 中映射 free_response，原类型和旧 OCR 几何在 provenance 保留。三个题干片段均在 viewer-10，cross_page=false；答案在 viewer-173。原 B HOLD/UNVERIFIED 与 proposal false 字段保持，新 A 授权仅处置这次单题离线准入。

`source.b_q4.reader.build_source` 验证 raw ZIP、所需成员、两原图摘要/尺寸、raw proposal/授权/任务清单和单题关系，保留原始快照及旧 OCR → A 四区域映射。`quality.q4_offline.pre_apply` 逐字段计算 source_integrity、structure、answer_matching、coverage、policy。coverage 仅本题四个批准组，其他三例仍 HOLD，不建立它们的题关系。

`delivery.q4_offline.engine.prepare` 创建明确的内存快照和 TARGET，通过 C01 assert_plan_ready 后生成 CREATE_FRAMES。`execute` 在同一目标锁内重新验证授权、来源、五项检查、当前目标、计划和 C01 准入；通过公开 apply_synthetic_action 实际改变内存。observe 无计划参数，独立读取真实内存状态。frame_projections 保留实际类型及文本，分别与批准表和基础目标框比较；C01 基础目标框只有角色/坐标，不用于冒充图片控件内容核验。

首次固定候选的复现命令在执行报告中给出确切 SHA。独立验收应使用自己的固定 raw 检出、输入目录、输出及 budget-dir。最终证据提交不能冒充运行候选。

```powershell
$env:GIT_NO_LAZY_FETCH='1'
python -B examples/a09/stage_inputs.py --stage <original-stage.zip> --destination <own-input-dir>
& examples/a09/launch.ps1 -ExpectedHead <frozen-product-SHA> -Inputs <own-input-dir> -Output <fresh-output-dir> -BudgetDir <own-budget-dir> -LaunchRecord <fresh-launch-record.json>
```

`bounded.py` 先核对运行项目源码、驱动、授权/任务和配置的 raw Git 成员，使用180秒试验、240秒回收外层；原内层门保持。消费记录最多两个冻结候选，每候选一次正常尝试，累计一次成功。成功后拒绝任何新正常试验。失败保留包和 NOT_RUN 后继，只有一次有界修正额度；无自动重试。进程结束凭原进程句柄 wait 和创建/结束时间判定，避免 PID 复用误判。

固定有限拒绝共十次：缺授权、改授权、Q1授权；替换输入、替换 proposal；一个合法重封 image→text 语义反例；平台模式；错目标；陈旧目标；同计划重放。语义反例先由 C01 真实校验，再到 PRE_APPLY 类型门，记录其实际达到层；不拿外层摘要拒绝冒充语义检查。所有拒绝目标新增题/框均为0。正常与拒绝目标均为进程内对象，退出后释放。

本交付仅作者 READY_FOR_REVIEW。回执保持 NOT_SUBMITTED/PENDING；不宣称 B 联合采用、完整外部 G0.8/Check0.8/plan0.3、OCR/平台图片控件、真实平台或公共合同冻结已通过。
