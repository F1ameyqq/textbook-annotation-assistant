# A11 固定离线内核独立验收：REWORK

2026-10-20（Asia/Shanghai，唯一suite于10月19日完成）。独立验收者 `/root/a11_live_runner_review`，报告分支 `codex/a11-live-pilot-review`。**固定 17 场景唯一一次独立 suite 为 17/17 PASS；原有限离线任务整体仍为 `REWORK_STATIC_GAPS_WITH_FIXED_SUITE_PASS`。** 静态审查确认“仅单选”准入与只读对账释放报告两项范围内缺口。通过的有限行为及作者第一失败原样保留，不因三天期限降低标准，不修改产品、不追加测试、不产生第三候选，也不自行声明 ACCEPTED / INTEGRATED。

## 固定身份、范围与原字节

| 身份 | 固定值 |
| --- | --- |
| 调度工作流 | `6080aa6fea5dc9a9e8397ad97aef099e81848f70` |
| 作者父基线 | `87f55ff636e463053f0b3c3ec97b0692511a06d0` |
| 作者最终交付 | `c580ca63ada9e452fd5ee71e5272cf0d047d4574` |
| 产品及本轮实际运行 HEAD | `ea5b62fd593041c29c00831ddb0eb453b0230307` |
| 报告工作目录 | `D:/1800-worktrees/a11-r`，base 作者 final |
| 独立运行目录 | `D:/1800-worktrees/a11-rr`，detached 产品 HEAD |
| 作者 raw 清单 | `docs/evidence/A11/execution/delivery-raw-manifest.json` |
| 作者 raw 清单 SHA-256 | `161e8493d92f5a86712c60144f2b723d17354330f0f07c90136c071ae8676834` |

两个目录均通过 `git -c core.longpaths=true worktree add --no-checkout` 新建；仅给索引 `read-tree HEAD`，没有全检出约三万条长路径。所有 Git 调用使用 `core.longpaths=true`、`GIT_NO_LAZY_FETCH=1`。运行所需 `src/annotation`（含原 C01 schema/resource）、三个新增 test 文件、六个 fixture、冻结 driver/catalog/fixture 清单共 **111 个文件**直接从产品 Git blob 导出，执行前后按 SHA-256 和字节数核对一致。没有为 CRLF 调整 pins、产品或测试。

独立逐成员核对作者 **442 个 raw 成员、8,905,388 bytes**，清单外加清单本身共 **443 条新增路径**；父基线 **29,968 条旧路径 mode/type/blob 全部保全**，产品和 final 的实际运行文件一致。记录见 [integrity-preflight](../evidence/A11/review/integrity-preflight.json)、[运行导出清单](../evidence/A11/review/run-export-manifest.json)。本报告分支只新增 `docs/evidence/A11/review/` 和本报告；主线既有 M、旧源码/合同/依赖/证据和其他人的文件未修改。

作者第一候选 `f5e3d63e6e31a87eb2b45789dbebadf89b4ac81e` 的6 PASS / 1 ERROR=`CHECK_SUBJECT` / 10 NOT_RUN仍在原位置。第二候选仅把 TARGET subject 由 graph 改为 snapshot；这符合原 C01 `validation.py:409-411` 的阶段绑定，未放宽合同。作者两候选/两 suite/一次成功的额度仍已用尽。

## 本轮唯一执行与静态证据审计

冻结 driver 的实际命令，在运行目录执行：

```powershell
$env:GIT_NO_LAZY_FETCH = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
python docs/evidence/A11/execution/run-suite.py docs/evidence/A11/execution/independent-attempt-1
```

新增 [launch-once.py](../evidence/A11/review/launch-once.py) 只做原字节预检、写一次启动意图、调用上述原驱动和等待自有 Popen；不注入测试、不改 driver、不重试。实际解释器为 `C:/Users/ASUS/AppData/Local/Programs/Python/Python39/python.exe`（3.9.13）。2026-10-19 15:54:54.093418Z 至 15:55:21.592217Z，suite 日志耗时 **27.327 秒**，结果 **17 PASS / 0 failure / 0 error / 0 NOT_RUN**。运行 HEAD 来自 driver 的实际 Git 读取，与报告 HEAD严格区分。

[原始结果](../evidence/A11/review/independent-attempt-1/result.json)及[日志](../evidence/A11/review/independent-attempt-1/suite.log)连同全部运行产物 **412 文件 / 2,556,387 bytes**逐字节复制进 review；[复制清单](../evidence/A11/review/run-archive-copy-manifest.json)保留原运行相对路径和每个摘要。之后只运行不导入产品/测试的归档读取与静态校验，没有第二 suite、新测试、补证场景或旧业务执行。[归档证据审计](../evidence/A11/review/archived-outcome-audit.json)列出所有现有 journal 结果、读回和假发送数。

本轮独立正常 suite 1 次，成功 1 次；本次成功额度耗尽。17/17只代表冻结 case 的实际结果，不能覆盖下列未运行的静态缺口。

## 原规则、实际命中层和有限通过行为

原文 `项目交接说明.md:71-74,97-100`要求题干Q、普通选项各W、答案A；本任务固定四个普通选项、无解析，所以独立推导为 **Q/W/W/W/W/A**。组合题选项归Q是另一题型规则，不能用于本题。原文88-90还明确单选/多选的区别，不能把“一个答案片段”等同于“一个答案字母”。

| 组 | 独立核对的结果及实际命中层 |
| --- | --- |
| T1 来源和批准 | C01先校源资源摘要/原图尺寸/引用闭包，A11再校原图映射、书46007447、1–5题有序清单、每题一次、总额度、批准全文/答案关系及hash。固定变体命中 SOURCE_MAPPING、MANIFEST_IDENTITY_ORDER、APPROVAL_CONTENT_BINDING；0/6题、Q22、已有平台映射与旧Q1批准拒绝。没有把本合成批准当真实业务审批。 |
| T2 角色 | 正例为六角色。陈旧Q选项变体经过合法重封并再次通过C01，随后由 AUTHORITATIVE_OPTION_ROLE拒绝，先于计划/intent。测试中相等的陈旧角色数组只是展示错误计划与错误读回可相等；拒绝依据是独立角色规则。其他题型/角色形状拒绝。 |
| T3 C01和真实门 | 未重封摘要、重封后图像header尺寸、伪OBSERVED链分别由C01拒绝；缺frame/session及旧版本到达A11能力门。**空 evidence_refs 的 VERIFIED 反例在 `reseal` 的模型构造处抛异常，未到达实际 check_target，不能记成一次真实能力取证。** 手填wire标签仍被UsenseTransport读/写方法拒绝。 |
| T4 目标与保全 | fixture两目录local_max=2、全书max=9，实际两题从10/11追加。重复题序、目录prewrite漂移、已存内部绑定拒绝；旧框/旧文字/旧目录/旧顺序变化各UNKNOWN，prewrite漂移在send前HOLD。完整目标、全部旧内容及源映射有显式门；并不证明真实平台全集读取。 |
| T5 一次发送 | 固定当前用户宿主路径的书锁、xb不可覆盖文件、fsync、事件前hash/锚点。INTENT完整落盘后才创建claim，再唯一send调用。同内容文件不恢复权限。五个冻结故障钩子退出73，新进程均BOOK_ALREADY_STARTED，send分别0/0/0/1/1；双worker一claim/0send。after_effect与before_receipt是相邻钩子，中间无独立持久动作，不扩大为五种不同持久化状态证明。 |
| T6 UNKNOWN | 响应丢失/仅HTTP200/部分框/GET失败或截断均停止，后继NOT_RUN。MATCH/ABSENT/CONFLICT只读对账的旧RESULT原bytes/语义保持，未重发，二次对账及重新apply拒绝。 |
| T7 框和全文 | 正常两题各get/refresh/reopen三次读回，原始磁盘backend转成矩形及文字再读取；未直接返回plan.expected_after。独立按原角色和fixture题意1+1=2核六段文字、选项与答案B；读取的框/旧状态逐项核对一致。strict全文/符号/答案/选项顺序、伪计划origin、同session重开均UNKNOWN。 |
| T8 限定行为和释放 | 六种禁止载荷拒绝；五CLI返回，真实apply/reconcile保持BLOCKED。apply关闭异常HOLD_RELEASE，后继NOT_RUN。历史A05形状只得CONTENT_PENDING。该测试没有覆盖reconcile关闭异常，不能据此覆盖A11-R02。 |

正常题的最终实际六框、文字、读回refs/session链及旧状态见归档审计的 `normal`。独立正常读回中会话为第1题session1/1/2、第2题session3/3/4，重开有前会话链；此链为明确的fake标记，未证明真实会话/平台来源鉴别。

现有26个假backend合计 **22次合成send**，是本固定suite各故障/正例的副作用；真实发送0。原C01源码只作为原bytes调用，旧模拟守卫没有改动。`runtime.storage`导入了已有sqlite3类型定义，执行链只用common摘要及BookEffectGate，未创建/打开SQLite账本；这里的“SQLite 0”是数据库操作0，不伪称没有import。

## 阻断整体接受的静态发现

以下仅由固定源码的条件和控制流得到，**未制造或执行新反例**，具体结构记录在 [static-findings.json](../evidence/A11/review/static-findings.json)。两项都在当前有限离线内核范围内；真实接口关闭不能消除它们。

**A11-R01 [P1] 单选范围没有实现。** `quality/live_pilot.py:103-121`只检查 `question_type=ordinary_choice`、六角色、非空文字及一个SELECTED答案fragment。C01 `models.py:226-235`没有独立单选字段；ordinary_choice是一般选择题类型。对于已正确重封、批准全文/hash一致的四选项多选（例如答案文本BC，或题干明确“多选”），六角色/单答案片段/字符串及批准闭包均可满足，余下路径也没有单选判定。原文88-90明确这属于多选，而本任务和runbook仅授权普通单选。现有“错误答案”case改变保存后文字，检查的是保存与批准不一致，不能证明拒绝已批准但越过题型范围的输入。需要未来另行授权的实现将可证明单选资格绑定源和批准，不能只因两端相等便放行。

**A11-R02 [P2] 只读对账的释放失败不进入结果与report。** `runner.py:102-110`在reconcile已得到MATCH/ABSENT后，close抛错或released=false只会追加 `RECONCILE_RELEASE{released:false}`，返回的result不带release/hold。`journal.py:142-145`生成report时只筛选 `RELEASE`，忽略 `RECONCILE_RELEASE`；若此前apply释放成功，后续report仍返回旧 `released:true`。因此操作者从对账结果和标准report看不到本次未证明释放，必须手工翻事件才能发现。原UNKNOWN仍保留、发送仍拒绝，未发现此路径重发；但它违反原任务“分别报告释放”以及T8释放不证明即HOLD。需要未来另行授权的实现单列当前对账释放状态，不回写旧UNKNOWN或恢复发送权。

没有把未执行的推演标为测试FAIL，也没有仅凭17/17把整体判PASS。最终候选现已固定收口，不能为这两项追加第三包、改名重启或恢复耗尽次数；后续取舍由主调度依用户授权确定。

若调度之后另行授权有界纠正，建议仅触及新增A11准入及对账结果/report，保留公共C01、旧业务、冻结suite与全部原证据。R01的最小差量检查可固定为：现有有效单选仍满足六角色/原内容；同结构且来源/批准/摘要均合法重封的答案BC在intent前拒绝；题干明确多选但答案只有B仍拒绝（原文规定明示多选优先）。R02可沿用原UNKNOWN与已有released=true的日志作为起点，分别让本次只读对账close抛异常、返回released=false，确认返回值和标准report均显式暴露当前未证明释放，旧UNKNOWN及后继NOT_RUN原样、send计数不增；正常对账继续单独显示实际释放。建议不扩大为完整历史矩阵或真实平台场景。**这些仅是未来检查建议，本轮没有构造输入、运行故障变体或验证修复；具体冻结候选、次数和case清单须由新派发决定。**

## 三项作者声明缺口的判定

| 作者声明 | 本轮独立判定与依据 |
| --- | --- |
| 真实wire/current facts未闭合、fail-closed | **原离线任务明确要求的接受边界**。quality真实分支无条件在事实注册表缺失处阻断；runtime只接受offline journal/transport；CLI apply/reconcile无发送入口；Usense方法显式拒绝，未依手填VERIFIED/JOINT_CONFIRMED开门。真实首题来源、平台执行政策、当前目标、上传/文字wire及读回codec仍需新任务，不是本轮要求擅自补取的事实。 |
| intent只存code_version，commit靠外清单 | **本固定运行可定位的证据边界**。intent已绑定VERSION、input/approval/policy/plan/baseline/payload；111个运行文件从确切产品commit导出且前后原bytes一致，driver保存实际HEAD，外清单形成运行版本闭包。原任务没有明确要求intent内字段必须是Git commit，因此不单凭这一点判本轮失败；但固定文字VERSION不足以让脱离外清单的单份intent自证代码身份，不能称为通用可迁移运行审计完成。 |
| 未生成C01 PLATFORM_OBSERVED ExecutionReceipt | **真实平台收口的接受边界，当前必须不伪造**。C01 `validation.py:554-555`要求SIMULATED计划对应SIMULATED回执，PLATFORM计划才对应PLATFORM_OBSERVED。本轮计划均SIMULATED，真实门关闭，每题有不可覆盖RESULT及BUSINESS_RECEIPT/READBACK。任务要求复用C01输入/计划验证和纯比较，没有授权伪造真实receipt。A11自有结果不能等同于C01公共ExecutionReceipt；SIMULATED公共receipt互操作及真实receipt都未证明，不释放这些后续依赖。 |

这三项本身不要求降低标准或重跑；整体REWORK依据是上面的A11-R01/R02，而不是因为离线任务没有制造真实证据。

## 自有资源与证据限制

[process-release-audit.json](../evidence/A11/review/process-release-audit.json)同时核对作者和本次的12条worker创建、12条退出，以及每个first/restart/one/two子进程档案。冻结 `tests/test_live_pilot_journal.py:16-32`在Popen返回后记录PID，`communicate`从同一自有对象等待结束后记录returncode；本次没有timeout/terminated_owned，六次73、六次2符合冻结预期。此为自有Popen等待链，**不是通过事后PID查询为空来推断精确身份**，也没有OS创建时间字段。

本轮suite自身PID **46240**，新wrapper通过同一个Popen对象记录创建和 `communicate`完成，退出0；启动wrapper的exec会话也正常返回。5个CLI使用冻结 `subprocess.run(..., timeout=20)`并检查返回码、保留stdout，**没有独立逐个PID创建/退出日志**。因此只声明CLI已同步返回，不声明其精确OS身份全量证明。该限制与12个跨进程故障worker的实际证据分开；未修改冻结驱动补造身份记录。

固定书锁在context退出或worker进程退出时释放OS句柄，锁文件保留，无新增锁探针、无删除或接管其他锁、无终止其他进程。六个崩溃/竞争backend中closed=false为有意保留的磁盘合成状态，实际worker已等待退出，不是活浏览器。资源释放不抹去UNKNOWN、HOLD_RELEASE或静态发现。

本轮0平台/网络/浏览器/profile/凭据访问/真实业务写入/SQLite操作/模型/依赖安装/B脚本/B消息/推送/送审/送交。未调用A07/A08/A09旧业务或A10探针。报告和证据在独立分支保留，实际运行产品目录不改成报告HEAD。最终交付commit和review raw清单摘要由交付消息给出；[review-raw-manifest.json](../evidence/A11/review/review-raw-manifest.json)只排除其自身，commit用于固定该清单本身。主调度决定接收已证明的有限行为、整体处理及后续任务，本验收不自行集成。
