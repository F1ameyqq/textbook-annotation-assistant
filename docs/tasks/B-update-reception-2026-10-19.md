# B新推送接收：Q1共同采用已确认，下一批仍为HOLD提案

2026-10-19，Asia/Shanghai。用户要求“B侧推送了你看一下”。本次只做新材料接收、摘要核对和A侧兼容性判断，未启动产品实施或新的模拟。

## 确切版本

- PR [#3](https://github.com/F1ameyqq/textbook-annotation-assistant/pull/3) 与 `b-side/readonly-book-46007447` 本次实际查询均为 `a76e5a925fec76f20818dfdefa4145aa132ec8a8`。
- 相比A发布时记录的B `c44f0e08d394647fb685a85f397f4b65dcf8137d`，新增两次提交：`5970f15a9921af424d55b662eefed4b28aa01c52`（Q1限定采用）和 `a76e5a925fec76f20818dfdefa4145aa132ec8a8`（Q4/Q9/Q16暂存及扩展请求）。
- A已发布版本仍为 `e37606d74d7e538052c563d02df11c6c961b742f`；本地产品与冻结证据不改。本次只获取固定Git对象，未切换分支、合并B或推送。

## Q1：可以关闭的等待项

B的[明确采用确认](https://github.com/F1ameyqq/textbook-annotation-assistant/blob/5970f15a9921af424d55b662eefed4b28aa01c52/docs/reviews/a07-q1-e37606d-b-adoption.md)与[机器记录](https://github.com/F1ameyqq/textbook-annotation-assistant/blob/5970f15a9921af424d55b662eefed4b28aa01c52/evaluation/book-46007447-a07-q1-b-adoption.json)同意A已提出的三项固定第1题离线技术口径：

1. 原包与旁文件独立版本/摘要、题1→原答案1.D、六组 **Q/W/W/W/W/A**，无额外辅助框或解析框。
2. 独立题号、中文连行、全角括号及两个U+3000，以及30项只限本题的逐项范围排除。
3. 新C01、计划、独立读回和模拟回执引用绑定，以及E0.1直接冻结消费/早期重建的不同用途。

三项采用字段均为true，未决字段差异为空。当前独立回执为 `a07-receipt-a07-f01-review-1` revision1，摘要 `6eef5b12bbc20b61f3d1cbb37f28fce4f184e6c72416c5edcf50f4d0e9b2325f`，与A固定归档一致。

A本次实际静态核对：B接收ZIP SHA256 `41ebfa94ea9d880d375f8428d054f8da857e7a5587b52d2734ef8a47d6287dbe`，10,950,040 bytes；366清单成员长度/摘要一致，无重复或不安全路径；其中357个A归档文件与A发布Git blob一致，3个B记录摘要及两份归档回执/读回引用绑定一致。详见[接收核对](../evidence/coordinator/b-reception-20261019/adoption-archive-check.json)和[检查源码](../evidence/coordinator/b-reception-20261019/check_adoption_archive.py)。

因此当前可记 **FIXED_Q1_OFFLINE_TECHNICAL_ADOPTION_CONFIRMED**。只关闭固定Q1的共同技术口径等待，不回写旧归档的 `B_joint_adoption=false`、原政策或历史HOLD。B自述的187项检查、消费者重读和51项下一批回归作为其报告保留；A未运行B检查脚本，也未重新执行这些测试。

## 下一批：实际为4个案例

请求见[B八项扩展说明](https://github.com/F1ameyqq/textbook-annotation-assistant/blob/a76e5a925fec76f20818dfdefa4145aa132ec8a8/docs/b-q4-q9-q16-a-extension.md)。输入来自固定Q15 revision9来源包，涉及G0.8、Check0.8、内容计划trial0.3；不属于原A06 G0.7接收或A07固定Q1支持范围。

| 案例 | 收到的材料性质 | 仍需解决 |
|---|---|---|
| 第一课时Q4 | 题 `q-260d10c51f2b7c16fb6fefb5` 与答案 `a-92c4d2164ab878c8e6d4c88d` 的完整题答案例候选 | 仍UNVERIFIED，含FIGURE_EXTENT_UNVERIFIED；新内容/区域/题答关系和单题政策核准，不能借Q1授权 |
| 小专题“方程思想”Q4 | 答案 `a-35b5bc7421c65d9fcaa47e33` 的证据 | 无题ID；分式、裁边及内容仍待核准 |
| 反思跨页Q9 | 答案 `a-9a6c21dd0fe88b1059b7919e` 的证据 | 无题ID；后页viewer映射未知，来源前缀范围有限 |
| 第二单元Q16 | 答案 `a-7302d4870826c53aea0bcd16` 的证据 | 无题ID；三行、11个分式及符号/幂次需逐项核准 |

新包SHA256 `b646fad9008e03e79a3dddfb4ead912d7ceadefbcee331c2e2af2415abf6f673`。后3例保持 **ANSWER_EVIDENCE_ONLY/HOLD**；不能凭答案号推造题实体、题答关系或模拟计划。原图已随包收到不等于内容正确性或整页验收。

A辅助只读检查核对新ZIP 1,440,149 bytes、顶层23成员和内层9成员的长度/摘要、4案例一致性与3张原图SHA/JPEG尺寸，未发现包装完整性差异。Q9实有33原片段/15呈现区，Q16有17片段/3呈现区/11 LaTeX runs；仍保留未完成和阅读顺序问题。详见[辅助接收记录](../evidence/coordinator/b-reception-20261019/next-batch-static-audit.json)。本次未遍历Q15完整来源包或重建快照，包装完整性不能代替内容来源链的全量验收。

## N01–N08的当前A侧处置

以下是对现有支持范围的判断，不是新实现派发或新验收标准。

| 项 | 当前处置 | 理由 |
|---|---|---|
| N01 案例路由与G0.8/Check0.8/计划0.3接收 | PENDING | A07明确绑定固定Q1与输入摘要；新批未有已验收消费者 |
| N02 答案证据与完整题答案例分离 | PENDING | 认可应保留HOLD的接收原则；这批格式的实际消费者尚未实施 |
| N03 多页顺序及逐图坐标 | PENDING | 新案例未验证；viewer-173与resource-173不能视为同一图或推算未知页码 |
| N04 公式/图形内容与角色政策 | PENDING | Q1六框规则不适用于这些题型；分式槽、图区和解析须有独立语义 |
| N05 原始/有效几何与双向变换 | PENDING | Q1变换方向已确认；新裁边证据和有效范围未获本批核准 |
| N06 逐案例政策与问题适用性 | PENDING | 每例需新清单与核准；Q1的30项排除和授权不转移 |
| N07 新PRE_APPLY/TARGET及计划/回执 | PENDING | 仅固定Q1实现已接受；不凭旧检查或B的拒绝报告放行新题 |
| N08 案例读回与错误隔离 | PENDING | 固定Q1已证明；新批次、多页/分式错误隔离尚未实现验收 |

“PENDING”指这次新案例支持未交付，不否定已有C01、Q1和其他模块的有限成果。B回执的旧Q1授权转移拒绝只证明该固定绑定门；不证明A已有通用批次消费者。

建议后续先固定G0.8新批的只读证据接收范围，以第一课时Q4作为下一道完整题候选，其他3例只做证据接收和具体拒绝；具体实施、验证额度与正向模拟须按新范围决定。本次用户仅要求查看，没有把B文件内的工作请求当作A新增执行或费用授权。

## 不变边界

本次0产品测试、0新正常业务、0模拟派发、0平台调用、0向B发送消息、0推送。没有运行B代码/生产者/SQLite，也不使用B文件内提到的DeepSeek预算或凭据。作者/独立的旧A07验证额度不恢复。A04真实平台阻断保持；本次不是公共合同冻结、人工视觉验收、章节验收或平台执行资格。项目整体未完成。
