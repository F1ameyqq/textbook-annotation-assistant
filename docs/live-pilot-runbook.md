# A11 限定普通单选内核

本交付是新有限离线内核。真实 `apply` 与真实 `reconcile-readonly` 明确 `BLOCKED`，真实文本提交、上传裁片、W/choice wire、独立内容查询和当前平台证据均未实现或未取得。离线 `VERIFIED` 只描述合成后端严格文本比较，不是平台事实。最终提交始终 `NOT_SUBMITTED`，作者交付状态 `REVIEW`。

入口（Windows PowerShell，已有 Python 3.9+、Pydantic 2、Pillow，不安装依赖）：

```powershell
$env:PYTHONPATH = 'D:/1800-worktrees/a11-live-pilot/src'
$env:PYTHONDONTWRITEBYTECODE = '1'
python -m annotation.runtime.live_pilot inspect-input --input tests/fixtures/live_pilot/review_delta/valid.json --asset-root tests/fixtures/live_pilot --offline-fixture
python -m annotation.runtime.live_pilot prepare --input tests/fixtures/live_pilot/review_delta/valid.json --asset-root tests/fixtures/live_pilot --offline-fixture
python -m annotation.runtime.live_pilot apply
python -m annotation.runtime.live_pilot reconcile-readonly
python -m annotation.runtime.live_pilot report --offline-fixture --journal <existing-offline-journal>
```

前两条只作本地检查和首题计划预览。`apply` / `reconcile-readonly` CLI 不加载任意 transport，也没有 force 或 assume 参数。离线执行是测试中显式调用 `runner.apply`，transport 的协议为 `observe(phase) / send_once(payload) / close()`。真实 `UsenseTransport` 不创建或操作 session；传入 `VERIFIED` 标签不能开启它。

输入格式见新增合成 [request.json](../tests/fixtures/live_pilot/request.json)。它包含完整 C01 bundle，graph/precheck/snapshot/policy 精确引用，原图摘要、尺寸、resource/viewer/source/save 映射，明确目录映射，以及本轮独立 approval。批准项绑定 question_id、输入 facts 摘要、六段全文和答案关系；清单有序、1–5 题、每题最多一次、总限额、时间窗、policy 和 evidence refs。只接收普通单选、文本、独立六框 Q/W/W/W/W/A；公式编码与其他类型拒绝。Q22、已有平台题映射以及 A07/Q1、A09/Q4 旧批准不能沿用。

2026-10-20 R01 差量收紧：原 request.json 原bytes保留，因缺明确单选分类，它不再是当前准入正例。新 [valid.json](../tests/fixtures/live_pilot/review_delta/valid.json) 通过 SourceBundle.history 引用 `a11-choice-classification-1` JSON（资源摘要由C01核实），绑定本题身份、六框事实摘要、六段全文摘要和 `SINGLE_CHOICE` 分类；每题 approval.choice_qualification 同时批准该确切资源与分类。未知/明确多选拒绝，题干明示多选也拒绝。四选项必须有按 A/B/C/D 顺序的明确标签，答案全文必须恰为其中一个标签，不将 BC 或一个答案片段误当单选。这只是离线来源闭包，真实事实注册表与真实adapter仍关闭。

每题流程为完整基线 → 全书 max+1 → C01 单 action 计划 → 新 prewrite 读回与基线逐字段比较 → intent 落盘 → 独占发送占用 → 一次调用 → 原业务回执落盘 → get/refresh/reopen 三次独立读回 → 释放 → 本题回执。后继只在本题严格内容/框/旧状态/释放全满足后开始；第一次失败或 UNKNOWN 留后继 NOT_RUN。

生产账本固定在当前用户 `.annotation/a11-live-pilot/usense/46007447`，锁为独立固定宿主路径 `.annotation/a11-live-pilot-locks/usense-46007447.lock`；离线使用单独固定 offline 锁与明确测试目录。它只排除使用此宿主协议的进程，不能证明远端排他或人工无并发。生产发送仍被静态阻断。日志事件与锚点均 xb/fsync，事件绑定前哈希、PID owner、版本、输入、批准、policy、plan、baseline、payload；存在同内容文件也不能获得新许可。事件/锚点/intent/claim 缺失或冲突关闭执行。当前一个账本只接收一次批次，重启不自动恢复任何发送。

只读对账调用只接收原 intent，最多一次读回；MATCH、ABSENT、CONFLICT 或 INDETERMINATE 只新增 reconciliation，不改旧 UNKNOWN，不恢复发送权，不启动后继。新批准/新计划/后续额度由调度另定。保存未知时保留整套账本，禁止删除 claim、改 run_id、换目录或重发“验证”。

R02 差量：对账返回及标准report分别给出 apply_release、reconcile_release 与当前 release；关闭异常或 released=false 会显示 HOLD，保留失败原因和原事件。早先 apply 的 released=true 不能掩盖对账释放失败。report也保守显示尚无释放的对账claim及未闭合的失败释放。正常对账释放保持 resend_allowed=false、write_disposition=HOLD，旧UNKNOWN/NOT_RUN不会被改写。

内容比较为严格字符串/列表相等，不自动去空格、换行归一化、四舍五入或数学等价。旧框所有业务字段、旧题序、已有文字/题型、目录名称/层级/同级顺序和源映射必须保全；完整旧内容读取不到即拒绝声明保全。重开必须是新 session，并绑定释放的前 session。框结果、内容结果、独立验收、释放和平台事实分别输出。

验收只运行预冻结 [suite-catalog.json](evidence/A11/execution/suite-catalog.json) 指定的新三个 test 文件；不复跑历史矩阵。实际作者候选、运行次数、原字节清单、suite 和资源释放见 [执行报告](tasks/A11-limited-live-runner-execution-report.md)。历史 A05 decoder 仅显示 `CONTENT_PENDING`，不能证明文本持久化。

上述17项是原冻结产品的历史suite，R01/R02不复跑它。当前仅按[六项差量清单](evidence/A11/review-delta-execution/case-catalog.json)执行一次；前三项只检查输入，后三项从固定归档UNKNOWN日志与假backend作独立raw副本后仅readonly reconcile。当前结果见[差量报告](tasks/A11-review-findings-correction-report.md)。

真实接线后仍缺：本轮业务清单与次数、当前完整 OBSERVED 源/目标、双方平台执行 policy 的确切采用证据、实际会话排他、上传权限/签名/wire、普通 W 与文本/公式字段、非空文字回执和独立刷新/重开内容读回 codec。当前实现不会将手填来源、能力或 policy 标记升级成生产 READY。
