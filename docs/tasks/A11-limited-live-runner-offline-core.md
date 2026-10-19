# A11：限定普通单选真实录入内核，先完成离线实现

2026-10-19。用户要求按三天路线持续推进。当前A10首次平台导航失败且本轮已停止；本任务与网络诊断并行，**不访问平台、不创建会话、不写真实题目**。目标是可运行的最小执行内核及明确关闭的未知平台接口，减少平台恢复后的接线时间。不能把本任务离线通过称为真实录入成功。

## 固定边界

产品基线 `404199fbbd7ef97b5837ba3d0555e91e5175e1cd`；实际含本任务的调度工作流在派发时给出。工程依据为[72小时路线](../delivery-72h-plan-2026-10-19.md)，以及本次固定的[静态接线分析](../evidence/coordinator/72h-live-runner/implementation-scope.md)。静态分析是设计依据，不扩大本任务白名单或运行次数。

首版只支持书46007447、固定清单最多5题普通单选，每题1题干/4选项/1答案，角色Q/W/W/W/W/A。其他题型、缺来源/内容/答案或复杂多片段拒绝。Q22不可重放；Q1/Q4旧离线批准和旧成功额度不复用。真实题清单、当前目标证据及平台执行政策尚未固定，生产apply必须明确BLOCKED；不能手填VERIFIED、JOINT_CONFIRMED或真实PASS。固定B离线采用不能替代平台执行政策。

仅新增以下路径：

- `src/annotation/quality/live_pilot.py`
- `src/annotation/delivery/live_pilot/{__init__.py,plan.py,usense.py}`
- `src/annotation/runtime/live_pilot/{__init__.py,__main__.py,journal.py,runner.py}`
- `tests/test_live_pilot_admission.py`、`tests/test_live_pilot_journal.py`、`tests/test_live_pilot_readback.py`
- `tests/fixtures/live_pilot/`，成员必须预先固定在新增fixture-catalog.json；全部为明确标记的离线测试数据
- `docs/live-pilot-runbook.md`、`docs/tasks/A11-limited-live-runner-execution-report.md`、`docs/evidence/A11/execution/`

不修改任何旧源码、合同/schema、pins、根依赖、A05脚本、旧证据或主调度JSON。独立分支/目录使用raw Git导出，主线既有M保持。无需依赖安装、模型、B脚本或SQLite。所有新模块import不得访问网络或创建会话。

## 必须交付的实际代码

1. 输入和目标纯检查：确切来源/授权/policy/原图摘要，权威六角色、内容与答案，当前完整目标证据；缺字段具体拒绝。独立计算全书追加顺序，不复用旧目录局部max。复用公共C01校验与纯投影比较，不改旧模拟守卫。
2. 单题计划和批次编排：每题独立计划/回执；首失败或UNKNOWN停止，后继NOT_RUN。实现批准文本与实际读回的严格比较、旧框/目录/内容保全检查。计划不能兼作读回。
3. 不可覆盖事件日志：书级固定锁，intent先落盘、独占发送权后最多一次调用；重启、已有同内容文件或ABSENT读回都不能恢复发送权。已未知的旧回执保留，reconcile仅新增只读结果，不隐式恢复后继。
4. 显式transport接口和有限适配：离线fake transport用于新测试。历史A05载荷只作已观察事实，`ocr_submissions=[]`和CONTENT_PENDING不能当真实文字保存证明；没有已验证文本wire/readback profile时真实adapter必须拒绝，禁止猜造字段、安装SDK或访问网站补证。不以可运行假transport冒充真实平台adapter已完成。
5. 可运行CLI：inspect-input / prepare / apply / reconcile-readonly / report，默认本地检查；真实能力和范围缺失时明确BLOCKED，不能用force/assume标签跳过。报告分别列框保存、内容、独立验收、释放和平台事实；真实收口接口保留NOT_SUBMITTED。

平台恢复后的真实接线与当前页面/文字schema取证由另一个明确范围承担，不允许A11作者因缺数据自行连平台。源输入、当前OBSERVED/VERIFIED证据和joint执行政策均缺时不得输出生产READY。

## 本轮有限验证与候选额度

先实现并做语法/静态检查，然后冻结产品和测试驱动。作者最多2冻结候选，每候选一次固定新suite，累计最多2尝试/1成功；首候选失败保留，只能一次针对原失败的纠正，第二失败固定收口。成功后不为补报告重复跑。独立验收在固定交付/清单/释放后另派新agent，最多每候选一次同范围suite，累计2尝试/1成功。不得重跑旧业务CLI、旧23项/五例或A07–A09成功场景。

新suite只覆盖接线分析T1–T8的必要有限组，冻结前把具体case_id和预期落入清单；不为覆盖率扩成通用矩阵：输入/权威六角色（含合法重封陈旧Q选项）、C01及缺失真实能力拒绝、全书local≠global顺序、旧状态保全、intent/发送/回执关键故障点与新进程重启、两进程同书一次发送权、UNKNOWN/后继NOT_RUN、严格内容与非计划读回、释放错误及禁止动作。全部使用新增明确offline fixture/自有临时进程和目录，0真实平台/浏览器/profile。跨进程测试须保留自有PID创建及退出证据，不终止其他进程。

## 交付和接受

交固定运行产品commit、最终commit、raw成员及fixture摘要、唯一实际suite结果、缺失接口/准入清单、入口说明和自有资源释放；旧路径mode/type/blob保全。作者标REVIEW，不能自宣ACCEPTED或INTEGRATED。独立从固定raw隔离检出核权威规则、负例真实命中层和一次发送，不仅比较计划与作者自生成读回。主调度最终只接受已证明的有限离线内核；真实平台试用仍需后续首题业务回执、刷新/重开内容读回及独立验收。
