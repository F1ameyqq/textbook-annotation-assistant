# A03-T1 独立验收报告

2026-10-18（Asia/Shanghai）。建议 **ACCEPTED，仅限 T1 取证模块及 L1/U1–U5 六场景**。作者原包的归档脚本缺陷保留，但必要原件、Resource、阶段与释放事实已由本次独立只读审计核清，六例也在全新目录各复验一次；不要求作者自选 seal.py 成功来替代这些原标准。工具须经调度接受后才供 T2 消费。A03 整体仍 REWORK，I01、T2/H1、本地产品集成及 B 确认均未释放。

## 固定身份与范围

| 项目 | 确切版本 |
| --- | --- |
| 产品基线 | `1330047dd29890dea0e433ff01b991f615bf78f4` |
| T1代码 | `73f21654adb8ee86e33381a3ff3bf1a179303928` |
| 完整被验收target | `ed90664ab15afd1938725441e2bc86db7884f784` |
| 原拆分/T1规则workflow | `f7084b2e8f2e9a1fcf758f9cba56ec9c9fb1f304` |
| 本次具体交接workflow | `69ef1b3456c7c44c463c4f4fb43b6064b8cf4e09`，其中 `docs/tasks/A03-T1-review-handoff.md` |
| 作者manifest SHA256 | `3fe14986f26b058c200cc75c2922be811dc1d31a98e60fefd9ab986d34036063` |

所有固定文本/源文件均由显式 `git -c core.longpaths=true` 读取。只在 `D:/1800/.local/A03-T1-independent-review` 建立独立副本、运行及审计；没有打开作者业务库、写其worktree、合并浮动分支、修改产品/pins/schema或主目录索引/提交/调度JSON。报告与必要证据写本任务review专属范围，由调度归档。

## 三项分别判断

**取证模块：通过本任务限定消费检查。** 固定 `capture.py` 的 `Boundary`/`LeaseBoundary`/`capture_databases`/`capture` 可供 T2 在相同受控调用边界导入。要求同步业务调用已返回、独占当前case且所有写者均已明确；模块不取得ownership，也不替调用者停止外部写者。LeaseBoundary先停止并join当前keeper，等待在途renew及其事务结束；正常复制后创建相同owner/generation的新keeper，最终必须调用 `boundary.stop()`，不能再停止初始keeper变量。模块不会为T2导入旧产品执行视图。

独立最小SQLite夹具实际经历活动journal → Event请求提交 → commit/close → join → raw复制 → 自有immutable副本SQL，结果value=7、源/副本原字节相同，业务调用0。产品 `ClosingConnection`/transaction finally关闭连接，目标连接同样关闭；native观察子进程由产品wait/reap后同步返回。六例实测捕获时仅主线程存活、keeper已停止且无error，复制前后源摘要一致、无sidecar删除/backup/checkpoint/sleep猜测。独立复制加审计边界最长0.015304秒，stop/join最长0.009924秒；未改变2秒renewal、10秒lease。该结论限已登记写者和同步调用边界，复制仍是逐库顺序，未宣称跨库原子。

**六场景：独立复验通过。** 新运行没有消费作者数据库；冻结输入/预期/驱动保持，L1一次dispatch、无reconcile，U1–U5各一次dispatch并在正常释放后由新进程恰好一次 `reconcile(max_attempts=1)`。下表“通过”表示保持原定义的合法未知/暂停及证据，并非动作效果已被解决。

| 场景 | 真实建立与唯一恢复读回 | 独立结果 | 恢复新增效果 |
| --- | --- | --- | --- |
| L1 | legacy partial + 完整读回，无恢复 | 原合法诊断POST/HOLD；UNKNOWN receipt/progress、pending=1、paused、不可重放；实际1/2片段 | 不适用 |
| U1 | native partial + 完整读回；完整恢复读回 | STILL_UNKNOWN/CONFLICT；实际1/2片段保留 | 0 |
| U2 | applied + unavailable建立；duplicate恢复读回 | STILL_UNKNOWN/CONFLICT；读回确含两条相同题身份，真实目标仍一题两片段 | 0 |
| U3 | 同上建立；contradictory恢复读回 | STILL_UNKNOWN/INDETERMINATE；CONTRADICTORY且范围完整 | 0 |
| U4 | 同上建立；truncated恢复读回 | STILL_UNKNOWN/INDETERMINATE；完整性两标记false | 0 |
| U5 | 同上建立；unavailable恢复读回 | STILL_UNKNOWN/INDETERMINATE；view/state/read_sequence/hash/version均null，不补snapshot | 0 |

五个native场景的原action/intent/permit/fact/receipt保持，原receipt/progress合法，intent仍PENDING、permit仍CONSUMED、plan仍INTERRUPTED，pending=1/paused=true；目标业务状态与效果表在恢复前后不变。新观察与目标持久化观察完全相等，精确核对source/scope/store/session/plan/action/digest/intent/原receipt；可用观察序列递增。native_report_reads=0，无POST/Batch。L1本身无该表，明确为不适用，保留其合法诊断POST。

11个业务子进程最长30.026秒（限45秒），六个父watchdog最长41.936秒（限90秒）；既有观察2秒/屏障5秒/lease10秒及外层540秒上限未变。没有失败、timeout、重跑或独立驱动纠正。冻结驱动输出沿用字符串PASS_AUTHOR_ONLY；本报告的独立结论来自本轮真实调用及随后独立SQL/原件审计，不将该字符串当验收凭据。

**归档缺陷：存在，但未阻挡本任务必要交付。** 作者第二次内联静态汇总及冻结 `examples/a03/T1-capture/seal.py:83` 对legacy L1直接索引native_report_reads，导致前者KeyError，后者未运行。本次没有调用该必错seal、修改原包、伪造其输出或抹去失败。原任务未要求这份自选脚本成功；本次自己的只读审计补足必要语义核查，实际无缺失阶段或Resource。首次静态根失败只有终端返回凭据、没有单独OS raw流的限制继续保留，不追补历史。原报告称67份view文件，而source-view实际列68项；本次68项均以基线blob核对，属于计数说明偏差。

合并的最小后续清单仅一项：**再次使用作者seal/同类汇总前，修正其legacy/native表分支，并相应更正报告的view计数说明；不要求重跑六例。** 这是归档入口的残留缺陷，不影响本次已验的capture模块导入；本报告未实施该修改，也不自行安排下一轮。

## 独立证据、命令与释放

先重新核对作者865个manifest成员的raw Git摘要、允许路径及code→target代码不变；产品相对基线无delta。独立物化957个必要文件，其中68个runtime-view成员与基线blob完全相同。非执行view的继承输入按冻结execution SHA精确还原其checkout表示；两种摘要分别登记，未用改pins迁就CRLF。预检严格UTF-8 compile 88个Python文件、171个冻结输入匹配、native pins通过。环境为既有Windows CPython3.9.13、Pydantic2.12.5，无安装。

作者与独立运行各审计28逻辑阶段/56双库原件、76个唯一Resource路径及全部正式artifact/input_refs/政策引用、fact、事件hash/head、receipt/progress/解决链绑定。SQL只查询本验收自有raw副本且使用 `mode=ro&immutable=1`，前后摘要不变；逐阶段与capture及SQL.json交叉核对，不以作者摘要替代查询，不用最终库重建中间状态。各套38份真实导入记录、1047条源码身份均核对；32个annotation模块全部来自固定raw runtime-view。原作者37个登记Popen单独审计，本轮37个登记自有Popen（5个raw Git、5个review根子进程、27个业务后继）均实际exit=0、无timeout、已wait/reap，六组owner/PID为空、lease=0、phase=RELEASED，所有登记keeper已stop/join且无error。这不是机器全局PID扫描。

以下为本轮实际一次性入口（create-only；现有目录已封存，不在原输出上重跑）：

```powershell
python -X utf8 -B D:/1800/.local/A03-T1-independent-review/bootstrap.py
python -X utf8 -B D:/1800/.local/A03-T1-independent-review/runner.py audit-author
python -X utf8 -B D:/1800/.local/A03-T1-independent-review/runner.py fixture
python -X utf8 -B D:/1800/.local/A03-T1-independent-review/runner.py preflight
python -X utf8 -B D:/1800/.local/A03-T1-independent-review/runner.py business
python -X utf8 -B D:/1800/.local/A03-T1-independent-review/runner.py audit-review
```

business实际调用固定 `run.py --output D:/1800/.local/A03-T1-independent-review/snapshot/docs/evidence/A03/T1/execution/validation/independent-01`，argv/cwd、源码快照、输入摘要、实际导入、raw stdout/stderr及completion均已保存。独立输出raw复制到review证据目录，绝对路径作为原始运行事实保留，不修改数据库内部路径。

| 证据 | SHA256 |
| --- | --- |
| [作者必要语义审计](../evidence/A03/T1/review/independent-01/author-semantic-audit.json) | `70edbdcf9b5d951cb9a267c9d31d8ba8221c9f79ae702e12cafcb5f853db4eca` |
| [独立六例语义审计](../evidence/A03/T1/review/independent-01/independent-semantic-audit.json) | `bc7ddb89fe4dc1641845ed60629e5394393460af4a05fb5c885188091aea782d` |
| [本轮释放证明](../evidence/A03/T1/review/independent-01/release-proof.json) | `93eb9bca3e8adebaba20640cfbc9f5cb9fb8133100f76dff7c545d16efe64a07` |
| [来源物化](../evidence/A03/T1/review/independent-01/source-materialization.json) | `7e926e249f6a98f8548d4e0ae38d6e25838f33f11393263172de25e6dda52203` |

完整新证据及本文由 [review manifest](../evidence/A03/T1/review/independent-01/manifest.json) 绑定，仅排除manifest自身；其摘要在最终交付回复给出，避免自引用。保留所有自有审计/驱动源码，复验原件、Resource、夹具、进程流与导入记录；作者历史仅引用固定target，不复制历史全集。

旧U2两阶段及瞬时journal缺口、R11作者F2/F3缺口、旧失败/未运行事实均原样保留，不由本轮新场景追补。C、H1、R9–R11及原A03全矩阵未运行；field reset=`NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。无网络、平台、browser/profile/凭据、安装、付费模型/OCR、推送、A05题22或书级提交；未联系B/旧A03、未委派、未发消息回调度。本轮结束，没有待本验收继续释放的自有Popen/keeper/owner。
