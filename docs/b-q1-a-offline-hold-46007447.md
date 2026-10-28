# 第1题 A/B 离线阻断诊断与待 A 确认事项

2026-10-18，Asia/Shanghai。B 输入基线 `ef6ba4dd083e7fd5378e80123b2b038dd11d7052`；A 远端仍为 `37089f9e0229da76ae1c45461b7e63929590be56`，未修改 A 源码。只处理书46007447第1课时第1题 `q-e92a499995ca1bbd570a2a09`，答案候选 `a-b22c88c763b7dfb917d02d18`（D）。

**已实际跑通“真实候选读取 → C01 映射候选 → 当前 HOLD 诊断 → A TARGET → A 阻断计划 → 未执行回执”。这是阻断诊断闭环，正向模拟尚未完成；业务保持 HOLD。**

## 本轮实际输出

| 步骤 | 结果与边界 |
|---|---|
| 原候选复核 | 固定 ZIP 全新解包，原24成员、两原图、13裁片像素/回投、7原片段及31项问题依据通过静态复核 |
| 显式映射 | A C01 消费者读取3个新对象；全部 OBSERVED、两资产 ORIGINAL，6区域/6片段，题答 UNRESOLVED、selected=[] |
| 当前 PRE_APPLY 形状诊断 | B 新生成 HOLD；五项为 PASS / UNAVAILABLE / UNAVAILABLE / UNAVAILABLE / FAIL。第一项仅核对来源资源字节/尺寸，不等于内容核准；不是 A 正式真实题检查验收 |
| A `check_target` | 实际返回 EXCEPTION，保留4项阻断；不改为 HOLD 或 PASS |
| A `create_plan` | 实际生成 BLOCKED ApplyPlan，8项阻断 ID、0动作 |
| A `MockSession.execute` | 实际生成 ExecutionReceipt，NOT_EXECUTED、results=[]、write_disposition=NOT_EXECUTED |
| 独立目标读回 | 同一内存会话前后值相同，动作日志为空，0派发/0平台请求/0模型调用 |

新对象各自重新封签，B payload 摘要不冒充 C01 全对象摘要。精确引用、文件摘要、环境与交付包清单见 [机器回执](../evaluation/book-46007447-q1-a-offline-hold.json)。

实际链运行于 `2026-10-18T12:08:20+00:00`（北京时间20:08:20）。映射产物时间固定为 `2026-10-18T12:05:44Z`，同一时间重放才得到本次固定字节。另一次新时间应生成新 run/artifact 身份；固定候选下的区域、片段、关系及未改政策身份保持稳定。

## 映射表达与限制

题ID原样保留；C01 Source/Evidence/Graph 使用独立派生身份。题干框包含括号，四选项各一组，答案D一组。括号独立裁片和其余上下文共7个辅助区域不转成语义框；不生成解析框。6组仍是来源区域候选，不能称为已经核准的6个平台框。

`Region.text`保留带印刷题号和来源换行的文本视图，独立 `printed_number=1`。去题号、连行和全角括号/空格的规范化建议保留在原候选与映射旁文件，尚未选为平台正文。plain/LaTeX、原字符跨度、原片段ID、13裁片和31项适用性依据保持可追溯；没有把字符跨度推断为字框。

C01 `ArtifactRef`只接受自己的kind，不能直接装入B trial引用；原B信封/载荷引用、run/scope、摘要算法及依赖保存在带摘要的旁文件和原候选中。C01没有MODEL_VISUAL来源枚举，本轮建议以 `HISTORICAL/UNCERTAIN` 表示已存候选，并在旁文件说明真实方法；不是 HUMAN 或新OCR。以上都是B适配提案，未获A确认。

固定输入 JSON SHA `09f9937a411a5ed5a7003019306a456937a422fc874a9baaae52817f02ccf06a`；映射清单 SHA `a831da5d89f2620220cff19565c5aff1825e47c5b0d900f7e269c61dbd590e2f`。驱动先核对这两项及清单内全部成员，再由A重新验证资源、引用和几何。76个A源码成员均与固定提交ZIP原字节相同。

## 为什么仍不能正向模拟

固定 A `quality/targetcheck` 明确要求 graph/source/evidence/snapshot 全部 SYNTHETIC；普通选择题还要求 SYNTHETIC_ASSUMPTION、SYNTHETIC_ONLY、SEPARATE。真实Q1保留 OBSERVED，实际政策错误包含 `A02 only supports SYNTHETIC inputs`、未确认政策及未选定答案。

`quality/synthetic_precheck`目前仅比较32×32 PGM及固定free_response结构，不是通用真实题五项检查入口。不能将实际书页重标SYNTHETIC，或借合成PASS给真实Q1放行。

本轮仅为调用A诊断接口提供一个明确标注的空本地目标夹具：没有真实平台观察、没有已验证能力、allowed_operations=[]，不代表A授予许可。它导致授权、能力检查失败；答案仍未选定也使覆盖不闭合。这些失败和上述源码支持限制分别记录，没有拿空目标制造的失败代替真实内容判断。

最小失败证据在交付包 `minimal-rejection.json`、`run/targetchecked.json`；输入和政策变化后的旧检查拒绝证据在独立审核材料。旧A06回执、原127问题、19条未归属账本及生产图谱均未改。外部合成控制不并入本题结果。

## 六项需要 A 明确回复

| 编号 | 已提供 | A 需明确确认或补交 |
|---|---|---|
| A-Q1-01 | 原包、来源候选与新C01映射/旁文件，各自ID、revision、摘要及依赖 | 候选旁文件接收白名单/入口；B trial引用、HISTORICAL/UNCERTAIN和旁文件保留方式是否接受。旧A06回执不覆盖 |
| A-Q1-02 | 来源行文本与去题号规范化正文并存，括号已补回 | 题号由谁添加；连行、括号及空格序列化的准确规则和版本，避免重复题号或丢括号 |
| A-Q1-03 | 6语义组、13裁片、同章节/课时题1→1.D依据，无原书解析 | 区域与题答准入；选项Q/W及答案A映射，哪些仍需独立人工核准；不能把证据裁片都变成框 |
| A-Q1-04 | 全31项原issue逐条追溯，30项范围排除建议+1项持续业务阻断 | 单题政策ID/revision/hash；逐项APPLICABLE/NOT_APPLICABLE/UNKNOWN及依据，不直接用空间不相交豁免覆盖 |
| A-Q1-05 | 固定A消费者实际EXCEPTION/BLOCKED/NOT_EXECUTED、新摘要引用和最小失败 | **保留真实OBSERVED来源、仅目标SIMULATED的有版本入口**；真实题五项PRE_APPLY生产者、当前模拟TARGET政策/配置/能力依据和运行命令。接口支持与内容/关系核准均须解决 |
| A-Q1-06 | 4bb0a00已补历史 `b-evidence-18e2d1ee2a22288f585513f0` revision1原件 | 确认直接消费冻结快照无需重执行它；重建早期链/谱系审计时的必要性。给新处置记录，不篡改旧A06历史结论 |

历史原件路径：`handoffs/b/46007447/single-question-q1/historical-evidence-revision1.json`；文件SHA `a763af50c0515f863eeb6dbaf533f4215535591096dd06b81632cec4acbb4493`。详细依据沿用 [单题交接](b-a-single-real-question-46007447.md) 与 [来源修订](b-q1-source-candidate-46007447.md)。

## 复现

使用A固定提交独立源码目录及当前Python/Pydantic/Pillow环境。本轮为源码验证，未做清洁安装或wheel验收。所有输出必须是新目录。

```powershell
python -X utf8 tools/build_q1_c01_mapping.py --a-source <A固定目录> --b-candidate-dir <来源候选解包目录> --output-dir <新mapping目录> --created-at 2026-10-18T12:05:44Z
python -X utf8 tools/probe_q1_a_hold_b.py --a-root <A固定目录> --mapping <新mapping目录>/c01-candidate-bundle.json --output <新run目录> --created-at 2026-10-18T12:08:20+00:00
```

输入或政策修订后须重新固定映射和生成检查；上述探针故意只接受本次固定映射，不能靠更换参数把任意输入称为本题已验证。无平台、浏览器、付费模型或题22执行；预框工具和DeepSeek保持暂停且不纳入本次提交。
