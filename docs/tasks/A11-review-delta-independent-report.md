# A11 R01/R02 独立差量：有限离线 PASS

2026-10-20（Asia/Shanghai）。结论 **`PASS_R01_R02_LIMITED_OFFLINE_DELTA`**：固定六项唯一一次独立执行6/6 PASS，R01单选资格和R02当前对账释放报告的两项缺口在本任务范围内得到关闭。实际运行与静态证据区分如下；本结论待主调度核证和接受，不自行声明INTEGRATED，不代表真实平台试用通过。

## 固定版本与原字节

| 对象 | 固定身份 |
| --- | --- |
| 独立派发 | `088cc790:docs/tasks/A11-review-delta-independent-dispatch.md`，原字节副本见[派发](../evidence/A11/review-delta-independent/dispatch-A11-review-delta-independent-dispatch.md) |
| 有界纠正任务 | `73ded1672682c7660ce46afcb6d2387803a40272:docs/tasks/A11-review-findings-correction.md`，见[任务副本](../evidence/A11/review-delta-independent/dispatch-A11-review-findings-correction.md) |
| 原作者final / 本轮作者基线 | `c580ca63ada9e452fd5ee71e5272cf0d047d4574` |
| 原独立发现 | `1522d1b612ba35f441a046706e46eabf97fe4a8d`，原17/17和静态REWORK保留 |
| 本轮作者final | `541d6b76cfa42655a224aeed0aab5a79a0b281aa` |
| 本轮产品及实际运行HEAD | `8ff44619b955983cc84041525c7b9176d45660f2` |
| 报告目录 / 分支 | `D:/1800-worktrees/a11-delta-review` / `codex/a11-delta-independent-review`，base作者final |
| 运行目录 | `D:/1800-worktrees/a11-delta-run`，detached固定产品 |
| 作者raw清单SHA-256 | `dba093ca1a7ea63f75fd6acff59a7e44f1693779cf2f6a72f4958b14de67a7e2` |

先核两个no-checkout工作树的HEAD与空目录，再用Git原blob导出。没有全检出旧长路径、读取浮动作者目录、安装依赖或修改pins。所有Git使用 `-c core.longpaths=true` 和 `GIT_NO_LAZY_FETCH=1`。独立确认作者清单 **114成员 / 6,871,732 bytes**；仅允许的3个A11模块与runbook共 **4条修改**，**111条新增**，其余 **30,407条保护路径 mode/type/blob 保全**，无删除。产品到作者final的代码、driver、test、fixture原bytes一致。

运行导出包含 `src/annotation`及原合同资源、新差量test、原及新增fixture、冻结driver/catalog等 **121文件**，执行前后逐成员SHA和字节数一致。见[完整性预检](../evidence/A11/review-delta-independent/integrity-preflight.json)、[运行导出清单](../evidence/A11/review-delta-independent/run-export-manifest.json)。只新增本报告与 `docs/evidence/A11/review-delta-independent/`，不修改产品、driver、fixture、作者/旧独立报告或主调度状态。

## 唯一实际六项

固定driver的实际命令在独立运行目录执行：

```powershell
$env:GIT_NO_LAZY_FETCH = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
python docs/evidence/A11/review-delta-execution/run-delta.py docs/evidence/A11/review-delta-execution/independent-attempt-1
```

[外层启动器](../evidence/A11/review-delta-independent/launch-once.py)仅预检原bytes、落一次启动意图并调用原driver。未修改其180秒边界、fail-fast或NOT_RUN机制。实际worker执行UTC `2026-10-19T16:24:32.508139+00:00` 至 `16:24:36.155430+00:00`，**3.647秒，6 PASS / 0 FAIL / 0 ERROR / 0 NOT_RUN**；未超时。见[结果](../evidence/A11/review-delta-independent/independent-attempt-1/result.json)及[原日志](../evidence/A11/review-delta-independent/independent-attempt-1/suite.log)。本轮独立差量次数1/1，成功后不再运行任何case；原17项未跑。

| 项 | 实际结果及证明层 |
| --- | --- |
| D01 | 来源资源和本次批准均明确SINGLE_CHOICE的两个合成输入通过check_input。六框Q/W/W/W/W/A、原内容与坐标保持；只做输入检查，未生成plan/intent或send。 |
| D02 | C01及批准全文/关系/hash均有效的BC输入，实际拒绝码 **SINGLE_ANSWER_LABEL_REQUIRED**，到达新单选语义门；不是摘要错误、批准不匹配或角色错误造成的拒绝。 |
| D03 | 来源和批准共同绑定 **MULTIPLE_CHOICE**、答案仍为B，实际拒绝码 **SINGLE_CHOICE_REQUIRED**。这是明确分类门的动态证据；fixture题干仍是原文，未动态覆盖“题干正则发现多选”分支。 |
| D04 | 固定UNKNOWN归档副本只读MATCH后close抛OSError。返回值和标准report均HOLD、当前对账释放false，原apply释放true单列；旧结果、NOT_RUN及发送占用保全。 |
| D05 | 独立副本close返回released=false。返回值和report均HOLD，保留原false原因 `synthetic returned false` 与会话字段；原apply成功没有遮蔽本次失败。 |
| D06 | 独立副本正常只读MATCH和释放，返回值/report如实显示当前true，状态REVIEW；原UNKNOWN/NOT_RUN仍保持，`resend_allowed=false`，返回 `write_disposition=HOLD`。REVIEW不等于恢复写入许可。 |

全部运行输出 **90文件 / 382,678 bytes** 已原bytes复制到新独立证据目录，双边路径/hash见[复制清单](../evidence/A11/review-delta-independent/run-archive-copy-manifest.json)。后续只读取现有输出和固定Git对象进行静态审计，没有导入/调用产品或执行新的反例；见[审计汇总](../evidence/A11/review-delta-independent/audit-summary.json)。

文档链接检查通过。`git diff --check`仅对保留的原始supervisor stdout之CR及尾部空行给出空白警告；排除这一个raw日志后其余暂存路径检查通过。没有为消除警告改写原进程输出，见[文档检查记录](../evidence/A11/review-delta-independent/documentation-validation.json)。

## R01 独立语义判断

原规则 `项目交接说明.md:71-74,88-90,97-100`要求普通四选项各W、答案A；明确多选优先，BC等多答案属于多选，不能因只有一个答案片段就成为单选。本任务固定普通单选，因此六角色与批准内容相等仍必须另有单选资格。

新增 `quality/live_pilot.py:58-98`读取SourceBundle.history确切JSON资源，要求其已标REVIEWED、类型正确，并再次核原文件SHA和目录包含性；分类绑定书、内部题ID、六框事实与六段文本摘要，且与本题 `approval.choice_qualification` 的同一资源及分类一致。C01仍校资源闭包；随后只接受SINGLE_CHOICE、显式按A/B/C/D排序的选项标签及恰好一个答案标签。该门由check_input在原批准内容绑定后、计划或intent前调用（同文件169行）。

独立对现有三个冻结输入从graph/evidence原数据重建六框和六段文字，核其资源SHA、source_frames_hash、source_parts_hash及批准对应；见[来源与批准审计](../evidence/A11/review-delta-independent/source-approval-semantic-audit.json)。D02资源故意仍标SINGLE_CHOICE但全文是BC，实际被答案门拒绝；D03明确标MULTIPLE_CHOICE，即使答案B仍被分类门拒绝。两者都已先通过C01及精确批准校验，故能证明本次原R01缺口的语义纠正。

缺分类、资源错绑、未知分类、非显式选项标签、题干正则发现“多选”属于已静态核到的守卫，**未新增动态case，也不宣称覆盖其全部拼写和语言形式**。来源REVIEWED、SINGLE_CHOICE等均为明确合成fixture，不证明真实人工分类、当前平台事实或真实准入；不能由这些字样绕过仍缺失的真实事实注册表。

## R02 旧状态、0重发与当前释放

D04–D06均由本次固定driver在独立运行目录从 `c580ca63:docs/evidence/A11/execution/attempt-2/runtime/test_T6_response_frame_and_read_failure/http_only`读取Git原blob，各新建自己的隔离副本。未复制浮动作者工作区，未先运行apply或旧成功题制造UNKNOWN。独立再核每个副本原 **15成员**（合计45次raw核对），包括原RESULT、BATCH、intent、claim、backend全部逐bytes不变；原backend sends=1只是历史计数，本次未增加。

每副本只新增 `RECONCILE_CLAIM`、`RECONCILE_RELEASE`、`RECONCILIATION`三事件及三锚点，共6文件。原UNKNOWN与NOT_RUN结果字节不变，未新增intent或发送claim，没有删除或改写旧事件。[来源复制审计](../evidence/A11/review-delta-independent/source-copy-audit.json)含确切commit/path/blob/SHA、三副本新增路径和结果。

`runner.py:102-120`把对账关闭异常/false规范为明确失败并保留原原因，返回值单列apply_release、reconcile_release、当前release、status和不可重发处置；`journal.py:142-163`从两类释放事件计算当前保守状态，失败列表保留原事件，因此旧apply成功不再遮蔽对账失败。正常释放也不改变原RESULT或恢复次数。尚无释放的对账claim与更早未闭合释放失败的保守HOLD是静态可见实现，未追加故障case。

driver结果中的 `new_*_calls=0` 是**常量声明，不能独立作为行为计数器**。本次0新增plan/intent/apply/send的依据还包括：前三项test调用链只有C01/事实检查/check_input；后三项仅导入并调用reconcile_readonly，新增transport不导入旧fake发送实现，send_once若被调用会自增计数并抛错；测试实际断言reads=1、sends=0；三个backend原bytes及旧claim/intent不变；新增日志仅有上述三种只读事件。静态调用链与归档产物共同支持该有限结论，没有仅接受常量标签。

## 兼容变化、释放与接受边界

原 `tests/fixtures/live_pilot/request.json`和原17项suite完全保全，但旧request缺单选分类，**不再是当前版本可直接运行的准入正例**；runbook已改指新valid输入。旧17/17是原产品ea5b62fd的历史证据，不能说成新版本全回归已通过。旧C01/纯投影/计划/真实适配器/CLI及旧测试原bytes未改；本次仅静态沿用其未受影响部分，新输入资格和对账报告影响由本六项验证，未重新验证完整apply链。

worker PID **48008**由supervisor **71948**持有原Popen并 `communicate(timeout=180)`等待退出0，未触发terminate；stdout/stderr管道均关闭。新增外层启动器也通过原Popen等待supervisor退出0并关闭管道，其exec会话正常返回。见[释放审计](../evidence/A11/review-delta-independent/release-audit.json)及运行目录原创建/释放记录。没有事后PID查询、进程名匹配或“PID为空即释放”推断。三次Journal作用域都在返回后 `_gate is None`，旧BookEffectGate的退出路径释放句柄；没有追加锁探针、删锁或终止其他进程。close异常/false是合成transport行为，已保留为失败证据，不是活浏览器。

作者本轮worker的同类原Popen释放记录也随固定final存在；本次结论以本次自有运行独立证明。0平台/网络/浏览器/profile/SQLite操作/模型/依赖安装/B消息/推送/真实业务写入/送审/送交；未调用旧17项、A07–A09成功业务或A10探针。已有storage导入sqlite3定义不等于数据库操作，本次活动调用链未打开SQLite。

真实source/target/policy/wire、文字保存和刷新重开平台读回、平台C01 ExecutionReceipt仍未证明。CLI与Usense真实入口及runtime offline守卫原bytes/语义保持BLOCKED；本次未连平台补取事实，也未动态重跑真实门case。intent内VERSION文字/外清单绑定的原边界仍在。`NOT_SUBMITTED`和人工最终提交边界保持。

本报告仅关闭R01/R02有限离线差量，后续范围集成及整体接受由主调度决定。最终报告commit与[review-raw-manifest.json](../evidence/A11/review-delta-independent/review-raw-manifest.json)摘要由交付消息给出；清单仅排除自身，报告HEAD与实际运行HEAD严格分开。
