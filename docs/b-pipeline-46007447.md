# B侧离线多阶段恢复

2026-10-17，基线`9533cb7ebc23bcb594e870921f1adb0f1db9f6a6`。本增量推进长期L2/L5，将已有逐资产批次接到答案细化、组题配答和质量检查；不接管A的平台执行器，未修改网站。

## 两条实际运行路径

| 模式 | 阶段 | 模型调用边界 |
|---|---|---|
| LIVE_BATCH | recognition → refine → assemble → quality | 默认几何模式在refine前以OCR_REQUIRED等待；显式`--ocr`才允许基础页OCR和答案行细化OCR |
| CACHED_INPUT | evidence → assemble → quality | 导入已有b-evidence-trial/0.2或0.3，不重新识别，不把缓存重放称为新CPU推理 |

两条路径均先核对完整manifest内的原图SHA、尺寸和范围，以及context/review来源。已有E的全页描述、顺序和context须与当前输入一致；不能在旧OCR上无声套用新章节窗口。缓存模式不接受`--ocr`、`--max-items`或`--stop-after refine`；其`--stop-after recognition`对应完成evidence导入。

`--max-items`只限制本次基础页识别调用，不缩小声明页数；部分页成功时不进入后继阶段。`--stop-after`允许主动保存阶段检查点。PARTIAL表示尚有阶段待处理；READY仅表示这些离线阶段执行完毕，内容和业务结果始终HOLD、未核准、无平台动作。

## 持久记录与依赖

`pipeline.sqlite3`保存stage_attempts、stage_events和stage_cache。执行前记录意图，阶段原结果放入b-pipeline-stage-trial/0.1 wrapper，再按内容地址不可覆盖发布；成功提交后才可以缓存。wrapper保留原EvidenceBundle/QuestionGraph/CheckReport的内容与身份，并绑定依赖、实现指纹和实际attempt。

每个阶段绑定实际输入文件/产物、相关函数和helpers、schema/regex等全局配置、影响结果的模块和依赖版本。真实refine另绑定当前CPU后端配置、包与模型SHA；仅明确替换为测试refiner且使用测试worker的路径可标SYNTHETIC_TEST_OVERRIDE，不能借此省略真实OCR依赖。修改review只使quality失效；live context变化从refine重算。缓存命中还要核对成功attempt/事件、当前run的CACHE_HIT和不可变文件，不能仅相信SQL状态或自签摘要。

真正进程退出后，OS锁自动释放；下次执行将RUNNING改记INTERRUPTED，保留旧attempt与孤儿物件，重做未完成阶段及依赖它的后继。损坏旧对象不在原地址覆盖。指纹/依赖设置失败也保存STAGE_SETUP_FAILED、明确失败报告及终止事件，不伪造未能构造的key/attempt；运行期间输入变化保存run_error/RUN_INPUT_CHANGED，不误报READY。

独立`pipeline_quality.py`不导入或重跑pipeline、refine、assemble或业务质检生产函数。它核对实际输入/完整范围、静态实现/配置、SQL与物件、图谱逐片段/账本来源和题答关系，以及质量报告的输入引用、统计与页清点。真实refine模型回执独立重算；协调重签假模型SHA仍拒绝。它证明的是执行与来源依赖一致，不是OCR文字正确、业务验收、签名或万能防篡改。

## 真实5页结果

相同5张本地原图分别运行两条路径，SHA前后不变，网络连接被禁止：

| 验证 | 结果 |
|---|---|
| 默认几何模式 | 识别5/5页，后继OCR_REQUIRED，1/4阶段完成、PARTIAL；禁止模型运行库导入，0 OCR |
| 显式CPU分段运行 | 先保存2/5页，再恢复余下3页并完成refine，最后继续assemble/quality至4/4 READY；再次运行命中4阶段，0新OCR |
| 原始CPU结果 | 424原OCR+82细分行；refine payload与旧冻结E0.2逐字段相同。基础组装34题/56答案/27唯一候选链接、38未归属，134个质检问题、HOLD |
| 已回补E0.3导入 | evidence后1/3、assemble后2/3、quality后3/3；重跑命中3阶段，均禁止模型导入、0新OCR。保留34题/66答案/34候选链接、19未归属和110个问题、HOLD |
| review元数据单独变化 | 仅重做quality，evidence/assemble命中2阶段；未改源事实或业务预期 |
| 控制组损坏assemble wrapper | 独立审计先拒绝；随后只重做assemble/quality、保留evidence缓存，下一遍3阶段全命中；故意损坏的旧字节保留在独立控制目录 |

候选链接数不是准确率。LIVE当前是基础识别链，尚未自动纳入既有局部OCR回补、公式后端和Q9的0.4续接/回滚；这些旧产物继续保留。CACHED_INPUT可以消费已有回补结果，但不能把基础链的38未归属说成已自动解决，下一步需接入有版本约束的补救阶段。当前5页也不是全书214页或独立留出评测。

本轮实际普通OCR入口调用为37：前2页各1次，续跑3页各1次、答案行细化32次。外部cProfile原始code-object计数确认续跑35次，缓存/几何为0；首轮使用的扁平pstats会把动态加载的同文件同名函数合并覆盖，只留下1次，是不完整计数，未改写该旧回执。首轮2次由两项真实成功页产物、每页1个OCR裁片及固定代码路径交叉核对；校准与明细见evaluation。耗时受profiling及并行回归影响，不作为独立性能基准。无新专门公式调用、网站请求/标注动作、样本上传或额外付费请求。

## 运行与交接

```sh
python tools/run_pipeline_b.py --source SOURCE/source.json --context CONTEXT.json --review REVIEW.json --workdir data/runs/pipeline
python tools/run_pipeline_b.py --source SOURCE/source.json --context CONTEXT.json --review REVIEW.json --workdir data/runs/pipeline-cpu --ocr --max-items 2 --stop-after recognition
python tools/run_pipeline_b.py --source SOURCE/source.json --context CONTEXT.json --review REVIEW.json --workdir data/runs/pipeline-cpu --ocr
python tools/run_pipeline_b.py --source SOURCE/source.json --context CONTEXT.json --review RECOVERED_REVIEW.json --evidence RECOVERED_EVIDENCE.json --workdir data/runs/pipeline-cached
```

保留workdir用于恢复。CLI每次输出JSON结果，并在checks中保存独立审计回执；report和stage物件在objects中按内容地址保存。根据report.payload.stages[].output.path读取wrapper，其payload.result是对应原始业务产物，result_ref给出原artifact身份。不要仅按pipeline_state或完整阶段数量执行平台操作。

492项回归通过（此前435+新增57：生产者16、独立审计25、CLI16）。覆盖真正执行中死亡和物件已发布/SQL未提交的两次os._exit、依赖失效、缺页/串页、假来源、模型回执篡改、setup失败和运行时输入变化；这些进程死亡场景用明确合成输入，不冒充真实整书事故。最终Git导出和重放证据见`evaluation/book-46007447-pipeline.json`。

公共合同仍是草案，所有新增schema为B trial/0.1，A接收验证仍PENDING_A。下一步将补救证据的版本迁移及重检纳入阶段依赖，继续四次幂/整式、材料公共身份、整书来源、独立留出集与固定A消费者；长期目标继续进行。
