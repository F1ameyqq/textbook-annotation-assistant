# A07-F01 四选项 W：独立单次差量验收

2026-10-18（Asia/Shanghai）。结论建议 **PASS，仅限本轮固定 Q1 角色纠正的 A 本地离线差量**。原首轮独立验收将错误 Q 读回作为期望，漏检了原书面普通选择题规则；本轮以原规则重新确定期望，保留旧报告/回执/分支及历史消耗，不回写旧结论或证据。等待主调度核证后有限接受及范围集成，不自行关闭 F01 或声明 ACCEPTED/INTEGRATED。

## 固定版本、原字节与授权

- 正式派发工作流：`53d1249887eabf9ee77fde6b0edf0f4d279016bd`；作者冻结工作流：`ca1fb902c2228579cd2d0c84d81fc72cd0643796`。
- **唯一实际运行产品 HEAD 和 expected-candidate：`3d22524ff626fc7b0376b7312be6fe75f2e73aab`**。
- 被审作者最终交付：`6f8f1d6fa4c8db9678738673a54fa862df9a666e`，仅通过 raw Git blobs 读取固定报告/清单，未作为运行 HEAD。
- 旧独立交付：`efe440d07d3600ee9755f1709778a2a742bb2f52`；原分支 `codex/a07-q1-review` 仍指向该提交。新分支 `codex/a07-f01-review` 从本轮产品创建，复用独立目录 `D:/1800-worktrees/a07-q1-review`；没有 reset、清理旧目录或写入作者/主线目录。
- 原业务授权 raw SHA256：`cf6f675cfd98d438d7d465fc553e0ebbf1bfff71bd62f8453854f8527015cb6c`；[新增 F01 授权](../evidence/A07/F01/review/A07-F01-role-correction-approval.json) raw SHA256：`7c6c2e9ceaa2abfb5d6379498d859c3411d13f60e89fed2914e999788fa32b8e`。新增授权未替换原授权，也未恢复旧额度。
- 本报告所在验收交付只新增报告和 `docs/evidence/A07/F01/review/`；确切提交 SHA 在最终交付回复提供。[验收 raw Git 成员清单](../evidence/A07/F01/review/raw-git-manifest.json)排除自身以避免自引用，提交后从实际 Git blob 再核对。

[独立静态核对](../evidence/A07/F01/review/static-review.json)以 `ls-tree -rz` 比较 mode/type/blob，用 `cat-file --batch` 读取原字节。作者工作流29,428条既有路径仅两条获准源码修改，其余29,426条原字节保持；9条新增为两个获准检查文件及7条冻结前授权/检查证据。产品全部29,437条路径在作者最终交付保全，旧28,363条证据路径、旧独立报告和所有旧独立证据保持。

作者58成员/10,200,306bytes清单逐项 OID/字节数/SHA256独立复算通过，见[被审 raw 成员](../evidence/A07/F01/review/reviewed-author-raw-members.json)。作者清单 raw SHA256为 `afb1c565ba4619c3cdc075a97ee0fbe2cca9d2613a3ee376ddcd43aef538a9ee`；作者报告 raw SHA256为 `2652db7d1feb595ba8b2a51e6e7e187e860a8f2d0c2258a063bce37924567e0f`。这不是仅引用调度预检结果。

仅有的产品改动为 reader 的 `option: Q→W` 和 PRE_APPLY policy 增加 `ordinary_choice`、实际六fragment映射严格为 `Q/W/W/W/W/A` 两项检查。delivery、运行器、旧测试、原配置政策/业务授权、C01/schema、根依赖、A03 pins、A06/I01及其他路径原字节保持。本题未触发的 shared_material 映射未修、未测试，不扩大为其他题型支持。

## 期望来自原书面规则及两项语义门

本轮直接读取[原项目交接说明](../../项目交接说明.md)第71–74、98行：题干Q，普通选项W、每项独立且字母在框内，答案A，无解析不画E；第99行组合题小题归Q是不同题型规则。固定题 `ordinary_choice` 使用 `Q/W/W/W/W/A`。两个既有普通选项政策也映射W。[原规则绑定](../evidence/A07/F01/review/original-rule-basis.json)保留原文行及raw摘要，期望没有从旧错误计划、旧读回或作者结果提取。

独立实现的[核对脚本](../evidence/A07/F01/review/review_f01.py)只运行下列两项角色门各一次，没有创建 MemoryTarget、计划或正常 dispatch，也未运行作者测试套件或旧9项负控矩阵。

| 调用 | C01/资源/摘要 | 到达层和结果 | 目标/dispatch |
|---|---|---|---|
| 正确 W | 有效 | PRE_APPLY.policy.ordinary_choice_role_mapping=True，五项PASS、decision PASS | 0/0 |
| 旧错误 Q | 政策与依赖信封逐项有效重封，C01验证通过 | 同一角色语义门=False；其他四项PASS、policy FAIL、decision HOLD，单项issue阻断PLAN/APPLY | 0/0 |

[两项实际记录](../evidence/A07/F01/review/role-gate-calls.json)和[输出](../evidence/A07/F01/review/role-gate-output.txt)保留。错误 Q 的拒绝发生在语义角色门，不是旧摘要/引用失配。

## 唯一独立正常差量

新输入目录 `.local/a07/f01-review-inputs` 由未修改的 `stage_inputs.py` 从固定本机原件和 raw Git 原授权只读复制。输入摘要保持原批准值：原ZIP `b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d`、新ZIP `3039645ca69c2604f542c479cb180049604788a3ca28ffac1b5063dee533afac`、候选 `0ce9ffb0f468ba0cc07f37978121e7f9b991b07b94335d117da3e8ea241aea5c`、历史E0.1 `a763af50c0515f863eeb6dbaf533f4215535591096dd06b81632cec4acbb4493`；原单题政策raw摘要仍为 `1954726fa502b0a7c0a8d5705a3ca1ecfe35bd94e67a2131dc9b707115ad745b`。运行后逐字节比较原件和复制件一致，见[输入保全](../evidence/A07/F01/review/input-preservation-after-run.json)。

run_id `a07-f01-review-1`，仅创建一个全新内存目标，正常尝试1次/CREATE_FRAMES dispatch 1次/成功1次。自己的[正常摘要](../evidence/A07/F01/review/normal/run/summary.json)、[C01 exchange](../evidence/A07/F01/review/normal/run/exchange.json)、[写前exchange](../evidence/A07/F01/review/normal/run/pre-execution.json)、[模拟回执](../evidence/A07/F01/review/normal/run/receipt.json)及[归档差量核对](../evidence/A07/F01/review/archive-delta-review.json)均来自本目录的实际运行。

- 五项 PRE_APPLY、四项 TARGET 的实际计算全部PASS；本次新增普通题角色门为true，C01资源、全信封hash、引用和 `assert_plan_ready` 通过。写前完整重新计算及执行锁路径与已验代码原字节一致，未改守卫。
- Source/Evidence/Graph仍OBSERVED；目标/计划/回执SYNTHETIC，执行SIMULATED。政策A_INTERNAL_PROPOSAL/PROPOSAL_ONLY、NOT_SUBMITTED/PENDING保持。
- [写前](../evidence/A07/F01/review/normal/run/assets/before.json)与[实际读回](../evidence/A07/F01/review/normal/run/assets/readback.json)为同一独立目标实例，读取序号1/2，目标0框→6框；读回读取目标自身状态。自己的实例 `memory-051e9b0a69cf4f5ba80abf3be411fa5a` 与旧独立实例不同，没有复制作者输出作为独立证据。
- 计划、实际frame及实际frame_projections三处角色均严格为 `Q/W/W/W/W/A`。回执为APPLIED/MATCH/POSTCHECK，replay_allowed=false。

| 组 | 旧角色→本轮实际角色 | 原图和 bbox，保持 |
|---|---|---|
| stem | Q→Q | viewer-10 `[70,332,590,445]` |
| option A | Q→W | viewer-10 `[96,453,153,486]` |
| option B | Q→W | viewer-10 `[207,453,262,486]` |
| option C | Q→W | viewer-10 `[320,453,374,486]` |
| option D | Q→W | viewer-10 `[430,453,486,486]` |
| answer D | A→A | viewer-173 `[72,239,88,258]` |

原始候选六组与自己的新读回逐框比较原图身份/尺寸/SHA、坐标、组ID及fragment顺序；再与 `efe440d0` 旧独立frame/projection所有非角色字段比较，均完全相同。实际角色变化索引仅 `[1,2,3,4]`。Source payload相同；Evidence regions/coverage及Graph非引用语义payload相同，正文、`A.2/B.3/C.4/D.5`、答案D、无解析、辅助图不成框保持。旧独立读回raw SHA256 `df3c33600ca7c08b873b756466a1a269643263559439d50047fa536edcdac019` 未变。

合法重算的派生变化包括本轮run/artifact/目标实例/时间、四项角色、新C01 policy及其依赖全信封hash/ref、角色门计算记录、状态/读回/比较/回执摘要；未手工沿用旧hash。本轮实际值：

- plan hash `c96984cc82a568d02fb39ccfc8a775b306b810e5d9756c80ff299d810169a9c3`。
- receipt hash `6eef5b12bbc20b61f3d1cbb37f28fce4f184e6c72416c5edcf50f4d0e9b2325f`。
- C01 policy hash `98694c6a054b5557353e080b9bbb20f00e81b445c31583eb80e115fcff0bcde2`。
- 实际读回raw SHA256 `5c1b51f0c5fd01c65876fe9904f08664f0598887a4614f4411b9e8619d7d0cd0`。
- 空目标业务状态hash保持 `a0d98e5b89efec908033b39fb0561e7ecd3ee0e5d4e17fe686213ca3b23911e1`；新六框状态hash为 `45a7e4e247f04323c50b5be2ad9b91d415cc2b4cd3016619929b337c6a447bd5`。业务状态hash与作者相同是相同固定效果，独立运行身份和回执另行生成。

## 消耗、命令与释放

本轮新增独立额度已用：1/1正常尝试、1/1新目标、1/1dispatch、1/1成功；正确W和错误Q门各一次、零写入。正常CLI自带的[一次实际已消费计划重放](../evidence/A07/F01/review/normal/run/replay-rejection.json)为 EXECUTION/PLAN_REPLAY、零变更/零新增dispatch。旧9项拒绝矩阵未重跑，唯一正常成功后没有再跑；无本轮失败或补改重试。

历史独立1次正常尝试/1dispatch/1成功及10次拒绝调用保持；累计独立正常尝试2、dispatch 2、成功2，其中第二次来自新增明确F01授权。本轮两项角色门和一次CLI重放单独计数，不恢复或清零旧额度。

本轮现成环境仍为CPython3.9.13/Pydantic2.12.5/Pillow11.3.0，未安装依赖。实际命令如下，正常命令仅已执行一次，记录不构成再次执行授权：

```powershell
$env:GIT_NO_LAZY_FETCH='1'
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH='src'
python docs/evidence/A07/F01/review/review_f01.py static
python examples/a07/stage_inputs.py --destination .local/a07/f01-review-inputs
python docs/evidence/A07/F01/review/review_f01.py gates
python examples/a07/run_once.py --input-dir .local/a07/f01-review-inputs --output docs/evidence/A07/F01/review/normal --run-id a07-f01-review-1 --expected-candidate 3d22524ff626fc7b0376b7312be6fe75f2e73aab
python docs/evidence/A07/F01/review/review_f01.py archive
```

[正常监督](../evidence/A07/F01/review/normal/supervisor.json)记录监督PID70696、子PID81440，exit0/reaped，本体5.968秒、监督6.563秒，180/240外层未触发，原内部守卫保持；耗时不构成业务SLA。[释放证明](../evidence/A07/F01/review/process-release.json)确认上述PID及语义门PID29108均已退出，查询无本目录自有A07 Python进程；辅助归档/保全命令均已exit0，其PID未保留。零长期服务、浏览器、平台及模型调用。业务完成后、报告提交前 `git diff --quiet HEAD --` 返回0，产品工作区无修改。

## 限制与交接

本轮修复普通选择题四选项Q→W；六框数量、内容、原图/坐标及单题授权保持。旧首轮PASS不能证明原业务角色符合规则的推断在F01发现后已撤回，本报告只建议本轮独立差量PASS，不改写历史。shared_material未触发且不在本轮范围。原B HOLD/非人工字段/账本、B共同采用边界、NOT_SUBMITTED/PENDING及A04真实平台阻断保持；无推送、平台连接、B或其他对话消息，未写主线调度状态。已释放，等待主调度只读核证、有限接受及范围集成，不能据此追加正常业务。
