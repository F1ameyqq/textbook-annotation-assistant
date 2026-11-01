# Q16与三个阅读任务的固定离线输出

B侧，2026-10-21，Asia/Shanghai。输入基线 `d48b066ad2620d7f1a2e902b2b28e3139390a721`；A只读消费者固定 `edf125961be9cdc1642652c038d99872b1c8cdc7`，现场核对远端仍为该提交。本轮停止扩展辅助工具。

## 内容变化

- Q16重新对照题页、三答行及放大原像素。11处分式、外围∵/∴、括号/平方、奇数且a≥3、60和61与当前版本一致。F5、F9及F10/F11分别核对自己的位置，不用相邻公式或模型多数票补写。三个小问绑定两数、第三数表达式、三行证明的原字符跨度；三空仍null。
- Q16本题完整位于viewer-15/印刷7，不是viewer-14→15跨页；答案位于viewer-173/印刷25。题与答分在两页不能当题干跨页。
- 阅读材料补全标题分隔线、S₁/S₂及图1/2的完整来源窗口，保留标签、剪开和翻转箭头。没有主印刷题号，不另造一个。
- 阅读任务1补齐旧OCR漏失的等号、三角符号、∵/∴、整行面积展开式及三个空。顺序为同页左下→右上，非跨页；答案顺序为a−b、ab/2、(a−b)²，题空仍null。
- 阅读任务2完整保留S₁/S₂面积推导、相等关系、消去ab及勾股恒等式。原104仅是分子；原108在x=228分接任务2/3，不能整行归入一题。
- 阅读任务3保留(a+b)²=a²+2ab+b²、“答案不唯一”括注续文及完整四区正方形图；原112只是b标签，不冒充整图。

18项来源核图已形成当前模型记录，独立人工内容核对仍待实施。原生G0.8/G0.9、旧Check、原始观察/错误候选及19条UNASSIGNED历史账本保留；没有新OCR推理、收费调用或网站请求。

## A实际读取入口

[固定ZIP](../handoffs/b/46007447/B-46007447-Q16-reading-C01-v2-HOLD-2026-10-21.zip)，SHA256 `4725523ec499a3074b268b12f0282ca795c13ddd98e97350078a50db89f7dc93`；146清单成员及manifest本身。解压后运行：

```powershell
python -X utf8 tools/consume_q16_reading_a.py --a-source consumer-a --pins consumer-pins.json --delivery delivery --out a-readback.json
```

此B核查入口实际调用未改写的A `annotation.contracts.load_bundle(..., verify_assets=True)`。91份A源码逐Git blob及大小固定；读取原图资源与全部Source/Evidence/QuestionGraph/CheckReport，输出完整正文、共享材料、候选答案、坐标和身份读回。

|包内入口|用途及固定摘要|
|---|---|
|`delivery/bundle.json`|C01入口，SHA `95488a276535a7bee7094238b02c6b41574e37df19d7b946830c6c07f9a824d6`|
|`delivery/delivery.json`|富文本runs、原图裁片、三小问跨度、11公式槽及当前C01引用|
|`delivery/current-review.json`|本轮来源核图与正文，SHA `4dd4425140620ef37a289df29206c2f04734c082badd2c73b238851d8031cada`|
|`delivery/basis.json`|前版原生对象/账本/输入引用，SHA `ad8795629c41b67908ba21d0d8039f7a3b5bdbd1eb0155cf75dc375922744a46`|
|`delivery/pending-review.json`|18项精确subject与当前C01绑定，人工审核字段全空|
|`delivery/assets/`、`delivery/crops/`|三原图及37原像素窗口，携带原图SHA/尺寸、裁片字节/RGB摘要|
|`SOURCE-REVIEW.md`|题干/解析/公式与来源裁片逐项对照|
|`reference/a-consumer-receipt.json`|B本机调用固定A代码的完整读回，不是A所有者接收回执|

实际C01读回：4题/任务、1组共享材料、37来源区域、26语义片段、11公式诊断槽及6个未填题空；诊断槽不重复成为答案。阅读任务沿用已有稳定本地ID，平台题ID/顺序不虚构。四关系UNRESOLVED、零selected，PRE_APPLY五项诊断保持HOLD；来源窗口不直接当平台精框，公共合同和角色映射仍为提案，不转移Q1/Q4授权。

## 验证

实际相关回归143项：21项新交付/真实A消费者测试、45项章节/来源/内容回归、77项数学角色/公式及质量回归。不是全仓库全套或准确率验收。

```powershell
python -X utf8 -m unittest tests.test_q16_reading_delivery -v
python -X utf8 -m unittest tests.test_remaining_sources tests.test_chapter_workspace tests.test_chapter_source_reconciliation tests.test_question_content -v
python -X utf8 -m unittest tests.test_b_math_reading tests.test_b_math_reading_quality tests.test_b_inline_formula tests.test_b_inline_formula_quality -v
```

新增负例包括错公式/互抄像素、任务2/3错配、漏整图/整行展开式、原图篡改、陈旧引用、C01坐标类型摘要差异、题空回填、假人工核准及重签错误审核subject。独立内容读回不调用新生产者生成预期。

最终ZIP安全解包后，两次不同新输出目录运行：

```powershell
python -X utf8 replay.py --out ../q16-reading-replay-new
```

146成员校验、46文件重建及完整A读回均与参考字节一致，网络和OCR/付费模型导入禁用。复用本机Pillow 12.2.0、Pydantic 2.13.4；未干净安装依赖、重验未携带父ZIP容器或重跑历史全流水线。第一版整数坐标经A浮点规范化后出现HASH_MISMATCH，已修正；后续额外绑定审核subject实际内容，拒绝只重算摘要的对象替换。团队质量审计另发现额外合法SourceBundle可混入直读、固定午夜时间/身份来源不明，两项均在v2修复：严格只收4 artifact/1 policy/2 evidence；`generation.json`固定首次构建实际UTC时间`2026-10-21T03:25:12+00:00`和配置/A-B输入摘要，run/artifact身份绑定该上下文，同一冻结输入重放身份不变，时间/配置变化会产生新身份，语义ID保持。额外对象、虚假时间、阅读顺序和错误消费者版本均有负例。早期包/失败记录留在本机历史。

## 团队与剩余边界

已恢复三个原成员会话：**B第一章｜Q16公式与内容修订**做第二模型来源核查，**B第一章｜来源与页码核查**核来源与范围，**B第一章｜独立质量与回归审计**独立解包/消费重放及对抗检查。成员只在各自目录产出，主会话唯一集成/推送。[第二模型来源复核](reviews/q16-reading-content-source-recheck-20261021.md)已完成，未见实质正文差异，34窗口从原JPEG重裁像素一致；该报告绑定旧候选f96b59dc，不冒充直接验过v2生成身份。v2内容来源未变的适用性以包差量及质量成员最终复核为准。第二模型不是人工验收。

B已自行完成现有原图核对、正文修补、C01适配和本机消费验证。A实际收到固定包后，只需分别记录消费结果、复杂公式/共享材料的精框与分组政策、独立人工内容处置及后续有限模拟准入，不再要求A替B补现有正文。

独立章节分母、完整目录及全部题答页仍未知；Q9反思题页和其余8份答案证据的真实题页身份不属于本包。第一章尚未验收。不调用A业务、目标或派发，不接网站、不修改标注、不送审，不替A填写共同采用或接收通过。

## 最终团队复核与A接收注意事项

- [来源核查](reviews/q16-reading-source-audit-20261021.md)：三图与八来源原件逐字节一致；37窗口全部核实。7个历史PNG与本包PNG只有编码字节差异，像素相同。交付PNG字节以`delivery.json.source_proofs.sha256`为准，旧几何对象`png_sha256`保留其历史原件口径；不能互换摘要。
- 正文2与图1来源窗口在一列、162像素重叠。当前窗口不声明平台精框，故不阻断来源证明；将来若要求互斥框，应人工核查后另出修订，不静默改本包。
- [v1质量报告](reviews/q16-reading-independent-quality-v1-20261021.md)保留两个真实阻断及反例；[v2最终差量复核](reviews/q16-reading-independent-quality-v2-20261021.md)确认关闭，允许发布固定离线HOLD包。146清单成员、91 A源码、46文件重放/读回通过。42个内容文件原字节不变，37区域/26片段/4题任务及配答语义相同；只新增生成上下文并更换身份/引用/诊断声明。
- 质量成员最终跑20项测试通过；主会话之后补了额外policy/evidence拒绝的两个子用例，最终21项通过，代码及固定包未再次改变。加上45章节来源和77数学质量回归，共143项相关测试。
- A接收时读取QuestionGraph的26个语义片段，不应把Evidence中11个公式诊断窗口另当11份答案。`chapter1-local`为本包本地目录，真实章节路径保留在basis，不冒充平台目录ID。请A只确认该固定输入的读取、分框/共享材料分组政策、人工内容处置及后续有限模拟准入，不重复补B现有正文或Q1/Q4旧样例。

以上成员报告中的v1摘要只证明其原始核查对象；适用于v2的内容范围由独立差量证明承接，不改写历史报告。发布副本只做Markdown行末空格/换行规范化，原件与发布件摘要分别存入机器记录；原报告保留在成员目录。网站标注保持不动，人工/章节/A所有者验收均未新增。
