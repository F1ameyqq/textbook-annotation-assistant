# A11独立审查后的两项差量纠正

2026-10-20。依据用户“规划一下接下来的路线并继续按路线持续推进”，主调度对原任务范围内两个可逆代码缺口安排一次明确增量。原A11任务的两个作者冻结候选由调度设定，已全部使用；本文件是调度主动修订自己的工程计划，不宣称用户另行回复过额度批准，不重置旧计数、不改名重开任务。平台连接既有许可仍有效；本轮只离线修正，0平台、0真实写入。

## 固定依据及范围

- 原产品 `ea5b62fd593041c29c00831ddb0eb453b0230307`，作者final `c580ca63ada9e452fd5ee71e5272cf0d047d4574`。
- 独立final `1522d1b612ba35f441a046706e46eabf97fe4a8d`；17/17原suite通过，静态整体REWORK。431成员/2,849,691bytes的raw清单已由调度核对；旧30,411路径保留。
- R01：ordinary_choice、六角色和一个答案片段不证明单选；合法重封且批准一致的BC或明示多选尚未被范围门拒绝。
- R02：对账RECONCILE_RELEASE失败没有进入返回结果及标准report，旧apply released=true掩盖当前释放失败；旧UNKNOWN和禁重发仍有效。本轮未动态证明反例，保留该证据边界。

只允许修改A11自己的 `src/annotation/quality/live_pilot.py`、`src/annotation/runtime/live_pilot/runner.py`、`src/annotation/runtime/live_pilot/journal.py`；新增 `tests/test_live_pilot_review_delta.py`、`tests/fixtures/live_pilot/review_delta/`、`docs/evidence/A11/review-delta-execution/` 及 `docs/tasks/A11-review-findings-correction-report.md`。允许更新新A11 runbook说明本次输入限制。旧suite、fixture、作者/独立证据、合同/schema、pins、根依赖和其他源码保持原bytes。主调度JSON仅主调度写。

R01必须用来源及本次批准共同绑定的明确单选分类或同等保守资格检查；答案只接受四选项中一个明确标签，未知/多答案/明确多选拒绝于计划和intent前。不能仅靠一个答案片段、把所有ordinary_choice默认为单选，或只增加未经来源/批准绑定的自报布尔值。保留六框Q/W/W/W/W/A、已有内容/坐标/关系要求。真实入口仍BLOCKED，不将离线fixture分类变成真实事实。

R02在对账返回值和标准report分别显露当前对账释放、原apply释放及保守的当前HOLD；不能改写旧UNKNOWN/NOT_RUN、删除失败事件、恢复发送或对账次数。成功释放也不授予重发资格。异常和released=false均保留，避免拿早先成功覆盖后续失败。

## 唯一有限差量

沿用原作者 `/root/a11_live_runner_execution` 和原独立 `/root/a11_live_runner_review`。作者新增最多1冻结候选、1次六项差量；原两次正常suite和原一次成功保留。因此作者候选总上限明确变为3，其中第三次仅本差量；不是第三次原suite。独立固定交付后最多1次同范围差量，原17项suite不重跑。先静态/语法准备，再冻结产品和驱动；冻结后失败固定报告，不边跑边改，不自动追加候选或案例。

1. 明确来源/批准绑定的有效单选通过，六角色/内容/坐标不改变，0send。
2. 六角色一致、内容/摘要/批准合法重封的BC被单选语义门拒绝；记录真实命中层，0plan/intent/send。
3. 明确多选但答案只有B仍被拒绝；不能用错误摘要或批准不匹配代替语义拒绝。
4. 用原固定UNKNOWN、后继NOT_RUN且apply释放成功的归档日志/假backend作为只读起点，对账close抛异常：返回值及report均显示本次释放未证明/HOLD，旧结果逐bytes不变、0新增send。
5. 同一起点的独立副本，对账close返回released=false，同样核对。
6. 同一起点的独立副本，正常只读对账释放如实显示；旧UNKNOWN/NOT_RUN保持、resend_allowed=false、0新增send。

第4–6项只能在新增隔离副本上调用只读对账，不先重跑成功apply或旧suite制造日志；记录来源commit/path/hash及复制检查。允许本轮新合成故障transport，不能修改公共旧fake或monkeypatch产品掩盖行为。固定180秒外层，首意外失败停止，余项NOT_RUN；只回收自有进程并记录原Popen/句柄等待退出，不重开任何旧库/profile。

## 交付与独立

作者在原独立目录从固定作者final另建有界增量分支，保留旧分支和全部失败/成功证据；交产品commit、最终commit、六项实际结果、raw清单、逐项输入/语义拒绝/日志delta及自有资源释放。作者只记REVIEW。调度预检后给原独立agent固定运行目录及报告目录，独立自建本轮输入副本，唯一六项差量后固定交付；不能审浮动代码。

调度核证之后才决定有限ACCEPTED及范围集成。本轮不处理真实wire、平台源数据、公共执行政策、安装发布或其他题型；不借本轮恢复A07–A10旧成功/探测额度。
