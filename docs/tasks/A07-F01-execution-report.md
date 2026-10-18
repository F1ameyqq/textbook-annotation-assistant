# A07-F01 选项角色差量执行交付

2026-10-18，**READY_FOR_REVIEW**。唯一获准的新增离线差量尝试成功：固定 Q1 实际读回 `Q/W/W/W/W/A`，六框数量、内容、原图身份、坐标及顺序保持。作者已释放，等待主调度核验后续派原独立验收；不自行关闭 F01 或声明 ACCEPTED/INTEGRATED。

## 固定版本与授权

- 工作树：`D:/1800-worktrees/a07-q1`，分支 `codex/a07-q1-offline`。起始干净 HEAD 为原作者交付 `d2e710c817cf85505ac4fad4919dd51d1062d33a`，按授权只做 fast-forward 至 workflow `ca1fb902c2228579cd2d0c84d81fc72cd0643796`；未清理、重置或修改主目录。
- 协调基线 `f0ff0fae1cc58e35187877d1dfdee674c979892c`；唯一新产品冻结提交 **`3d22524ff626fc7b0376b7312be6fe75f2e73aab`**。原 `run_once.py` 实际运行的 HEAD 和 `--expected-candidate` 均为该产品提交。
- 本报告所在最终交付提交只新增本轮报告/证据；确切最终 SHA 在交付回复中给出，产品原 blob 与上述冻结提交相同。
- 原业务授权 raw Git SHA256：`cf6f675cfd98d438d7d465fc553e0ebbf1bfff71bd62f8453854f8527015cb6c`；新增 F01 授权 raw Git SHA256：`7c6c2e9ceaa2abfb5d6379498d859c3411d13f60e89fed2914e999788fa32b8e`。两份原字节及取自 workflow 的绑定记录在[授权目录](../evidence/A07/F01/execution/authorizations/binding.json)。新授权是本轮执行依据，不替换原内容/范围批准，也不恢复旧额度。

## 修改与窄门

仅修改两条获准旧路径：`source/b_q1/reader.py` 的 `option: Q → W`，以及 `quality/q1_offline.py` PRE_APPLY policy 中本题的 `ordinary_choice` 和六个实际 fragment 经映射后严格为 `Q/W/W/W/W/A` 的检查。其他角色（包括本题未触发的 shared_material）、旧测试、delivery、运行器、配置政策、原授权、C01/schema、根依赖和旧 pins 均不改。只新增获准的 `tests/test_a07_role_delta.py`、`examples/a07/role_delta_check.py` 及本轮报告/证据。

期望独立取自 `项目交接说明.md:72/98` 与既有 `usense-v1-proposal.json / synthetic-choice-separate.json`，没有从旧错误读回复制。[原规则绑定和两次窄门结果](../evidence/A07/F01/execution/pre-freeze/role-gate-calls.json)包含原文行、raw 摘要和实际判定：

| 调用 | 到达层 | 实际结果 | 目标/dispatch |
|---|---|---|---|
| 正确 W 映射 | PRE_APPLY.policy.ordinary_choice_role_mapping | 五项 PASS，decision PASS | 0/0 |
| 旧错误 Q 映射，有效重封政策及依赖对象 | 同一语义角色门 | 其他四项 PASS，policy FAIL，decision HOLD，阻断 PLAN/APPLY | 0/0 |

只运行这两个窄检查各一次，[测试输出](../evidence/A07/F01/execution/pre-freeze/role-gate-output.txt)为2 tests/OK。错误映射先通过 C01 资源、引用和重封摘要验证，拒绝并非旧 hash 不匹配。未运行旧9项负控全集。

## 唯一正常差量结果

[监督记录](../evidence/A07/F01/execution/normal/supervisor.json)绑定实际产品提交及命令；本体5.86秒，外层6.391秒，180/240秒看门狗与内部规则未调整。仅创建1个全新内存目标，1次正常尝试、1个 CREATE_FRAMES dispatch、1次成功。[摘要](../evidence/A07/F01/execution/normal/run/summary.json)为 `SIMULATED / APPLIED / NOT_SUBMITTED / PENDING`。旧作者1次完整尝试/1次成功保持，本轮是另行授权的新增1次；累计作者2次完整尝试/2次成功，未清零历史。

[新 C01 exchange](../evidence/A07/F01/execution/normal/run/exchange.json)实际重算五项 PRE_APPLY 和四项 TARGET，均 PASS；原写前重新计算、C01 `assert_plan_ready`、内存变更与公共效果比较路径保持。[回执](../evidence/A07/F01/execution/normal/run/receipt.json)为 `APPLIED / MATCH / POSTCHECK / replay_allowed=false`：

- plan hash：`003e4789f766becc14b0cf625237635d4ff16826c52647be124599f36459ceba`
- receipt hash：`05673b6489d7dc991ddd36269f0828f3ed6cb26bc63c29dec91e7da36d7762a9`
- 新 C01 policy hash：`98694c6a054b5557353e080b9bbb20f00e81b445c31583eb80e115fcff0bcde2`
- [实际读回](../evidence/A07/F01/execution/normal/run/assets/readback.json) raw SHA256：`aa5747b9f892e3b2f682382b3288e88006e90009205f1307d0080b0c59a57d08`

写前/写后是同一目标两次实际读取，序号1/2；实际状态从0框变成6框，状态 hash 从 `a0d98e5b89efec908033b39fb0561e7ecd3ee0e5d4e17fe686213ca3b23911e1` 变为 `45a7e4e247f04323c50b5be2ad9b91d415cc2b4cd3016619929b337c6a447bd5`。读回读取目标自身状态，未把计划复制为读回。

| 组 | 原角色 → 本轮实际角色 | 原图 | bbox，保持 |
|---|---|---|---|
| stem | Q → Q | viewer-10 | [70,332,590,445] |
| option A | Q → W | viewer-10 | [96,453,153,486] |
| option B | Q → W | viewer-10 | [207,453,262,486] |
| option C | Q → W | viewer-10 | [320,453,374,486] |
| option D | Q → W | viewer-10 | [430,453,486,486] |
| answer D | A → A | viewer-173 | [72,239,88,258] |

原 CLI 自带的[一次重放拒绝](../evidence/A07/F01/execution/normal/run/replay-rejection.json)为 `EXECUTION / PLAN_REPLAY`，零目标变更/零新增 dispatch。此次共有两个窄门调用及正常运行内一次重放拒绝；未另跑旧拒绝矩阵，成功后未再跑正常业务，无失败重试。

## 归档差量与保全

[归档核对](../evidence/A07/F01/execution/archive-delta-check.json)只读取本轮产物和原独立提交 `efe440d07d3600ee9755f1709778a2a742bb2f52` 的 Git blobs，新增业务运行数0。旧独立读回 raw SHA256 `df3c33600ca7c08b873b756466a1a269643263559439d50047fa536edcdac019` 保持。逐框比较实际 frame 与 projection 的所有非角色字段、6个 Evidence regions 的正文/尺寸/原图SHA/坐标/组身份、Source payload、Graph非引用语义均相同，只有索引1–4的实际角色发生 Q→W。原图、辅助裁片、括号、答案D及无解析状态保持。

允许且实际重算的派生变化：新 run/artifact/目标实例/时间；四项 frame/projection 的 platform_role；新 C01 policy 全对象 hash 和依赖信封/hash/ref；新增角色门的 PRE_APPLY 计算；目标状态、读回、比较及回执资源摘要。原输入摘要、空目标业务状态摘要等应保持的值保持，没有手工沿用旧成功 hash。

workflow 29,428条既有路径只有两条获准源码路径变化，其余旧 blob 保持，包含28,363条旧证据路径。原作者/独立报告、失败记录、回执、清单、A03/A06/I01 与 B 原件均保全。产品清单见[候选 raw 成员](../evidence/A07/F01/execution/candidate-raw-manifest.json)，最终清单见[交付 raw 成员](../evidence/A07/F01/execution/delivery-raw-manifest.json)，后者仅排除自身以避免自引用摘要；以最终交付提交核对全部成员。

固定输入/原政策保持的 SHA256：

| 输入 | SHA256 |
|---|---|
| 原 B ZIP | b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d |
| 新 Q1 ZIP | 3039645ca69c2604f542c479cb180049604788a3ca28ffac1b5063dee533afac |
| candidate.json | 0ce9ffb0f468ba0cc07f37978121e7f9b991b07b94335d117da3e8ea241aea5c |
| manifest | 240622443df3c1f31cf76dc490fb7b2cedb9cecb09f47f086909cbe9e9fbd345 |
| scope proposal | 289269e3e2ea3961d565c49f9078a5e273fe2517356832bcbdc3fe8636fc3019 |
| E0.1 | a763af50c0515f863eeb6dbaf533f4215535591096dd06b81632cec4acbb4493 |
| 原 A07 单题配置政策 | 1954726fa502b0a7c0a8d5705a3ca1ecfe35bd94e67a2131dc9b707115ad745b |

## 精确命令和释放

```powershell
$env:GIT_NO_LAZY_FETCH='1'
$env:PYTHONPATH='src'
$env:PYTHONIOENCODING='utf-8'
$env:A07_ROLE_GATE_EVIDENCE='docs/evidence/A07/F01/execution/pre-freeze/role-gate-calls.json'
python -m unittest discover -s tests -p test_a07_role_delta.py -v
python examples/a07/run_once.py --input-dir .local/a07/inputs --output docs/evidence/A07/F01/execution/normal --run-id a07-f01-author-1 --expected-candidate 3d22524ff626fc7b0376b7312be6fe75f2e73aab
python examples/a07/role_delta_check.py --new-run docs/evidence/A07/F01/execution/normal/run --product-candidate 3d22524ff626fc7b0376b7312be6fe75f2e73aab --output docs/evidence/A07/F01/execution/archive-delta-check.json
```

上述为作者已执行的命令记录，成功后不得再次执行正常试验。独立验收按调度续派，必须检出本次**产品提交**，使用自己的新输入/输出目录与run_id，保持 HEAD/expected-candidate 守卫，不能以最后报告提交冒充运行产品。自有原始输入目录是原任务只读复制的固定材料；新目录可沿用未改的 `examples/a07/stage_inputs.py` 从本机固定原件与 raw Git 原授权建立。

[释放证明](../evidence/A07/F01/execution/process-release.json)：窄门监督/子进程PID15584/23244、正常监督/子进程PID41800/26240均已退出，两个子进程exit0且reap；归档核对工具exit0（其PID未保留），进程查询无匹配的A07 Python进程。服务/浏览器/平台/模型调用均为0；最终提交后工作树干净，作者停止修改与运行。

仍仅为 A 本地固定 Q1 离线模拟。来源/PRE保持OBSERVED，目标/TARGET/计划/回执保持SYNTHETIC/SIMULATED；A_INTERNAL_PROPOSAL/PROPOSAL_ONLY、NOT_SUBMITTED/PENDING及原B HOLD/31项/78依据/19未归属账本保持。shared_material未触发且不在本轮修复范围。未推送、未联系B/独立或其他对话、未连接平台、未改主线调度状态；A04真实平台阻断与B共同采用边界不变。独立差量验收及调度收口仍待完成。
