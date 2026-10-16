# A01 R1 geometry 独立复验

日期：2026-10-16（Asia/Shanghai）。子结论：**ACCEPTED**，仅覆盖R01–R03与原验收第8/9/10条的列明离线几何检查；不构成整个A01验收、主调度集成、A04释放或B确认。

固定交付 `03c1af41a134945c406a52a48e3d4f6f0da33eb2`，实现 `0ee7e836e3bc1849f91840b4271d233bbd8e72dd`，R1基线 `a8d5e96d128e10d341de935d4856682e50df79d9`。读父验收者已按Git blob校验的隔离副本，不读浮动源工作树。实际几何模块为该副本的 `src/annotation/geometry/__init__.py`，SHA256 `3b707579cd586887da3b5125048b17c5baf548010fccf6cb21cc386baddaacf0`，实现版本 `a01-geometry-1-r1`。Python 3.9.13、Pydantic 2.12.5、Windows；完整环境与真实模块路径在 [summary.json](summary.json)。

## 原7项失败重放

| 既有反例 | 本轮实际结果 | 结论 |
|---|---|---|
| F01：5×1、crop=[2,0,5,1]、scale=[7/3,1]，合法右边界点 | `(5,0)`→`(7,0)` | PASS |
| F01：上述整裁片框 | `[2,0,5,1]`→`[0,0,7,1]` | PASS |
| F02：3×7、crop=[0,1,3,7]、scale=[1/3,1]、90°，逆向合法边界点 | `(6,0)`→`(0,1)` | PASS |
| F02：上述逆向整内容框 | `[0,0,6,1]`→`[0,1,3,7]` | PASS |
| F03：4×1、crop=[1,0,4,1]、scale=[2,1]、左补边1，x=nextafter(1,0)点 | 逆向在算术前报 `GeometryError/BOUNDS` | PASS |
| F03：上述含补边的框 | 报 `GeometryError/BOUNDS` | PASS |
| F04：1×1、左补边2**53+1 | 构造明确报 `GeometryError/REPRESENTATION` | PASS |

F04沿用原任务“明确拒绝或精确保留”的标准；新脚本捕获构造异常，不把旧脚本没有捕获合法拒绝当作实现失败。原准备、正式报告、失败脚本与证据未覆盖。新结果见 [minimal-counterexamples.json](minimal-counterexamples.json)，该文件同时包含原反例重放和下述非阻断数值观察，不表示本轮又有13项失败。

## 独立新增与原条款判断

- 原G01–G08字面手算44项全部通过，包含非方图、非零裁片、不同x/y尺度、非对称补边、0/90/180/270°、像素边界/中心、变换次序，以及点和框从独立字面处理坐标的逆向检查。
- 3组新增复杂配置各做四旋转，共492项检查全部通过。独立期望正向按crop→scale→pad→rotate分阶段计算；逆向对处理字面输入独立按逆旋转→减补边→除配置scale→加crop计算，未调用实现矩阵或用实现逆向生成预期。检查了内容矩形、普通点/框、四边精确边界和 `nextafter` 相邻内/外点与框，以及原图裁片四边的相邻点。普通域没有新增漏拒绝或合法点误拒绝。
- 11项整数边界/总和检查全部通过：图像及画布恰2**53接受，图像超过上限拒绝；1×1配左补边2**53−1接受且精确保留；左右补边总和令画布恰上限接受、超过上限拒绝；float形式上限补边造成画布超限同样拒绝；负超限整数和缩放后超限画布拒绝。常规R01/R02支持域保持可用。
- 原73项常规非法输入及1项数学逆矩阵字面检查全部通过，包含NaN/±Inf、0/负尺度、奇异/不可表示逆、错绑定、越界、不支持变换和非整数缩放后尺寸。差小于1e-9的非整数尺寸仍拒绝，未扩大合法域。
- 几何仍是具名A内部 `a01-geometry-1`；未知spec、未支持matrix/perspective/reflection/nonlinear及C01模糊 `CropTransform` 自动解释均拒绝。R1明确文档化端点插值方法和整数上限，未修改C01或宣称B接受。

验收断言合计 **630 PASS / 0 FAIL**。此外6项数值观察单列为 `OBSERVATION`，未伪装通过或作为新增硬标准，见下节。作者冻结几何8项及R1 `GeometryR1Tests` 6项也同进程重跑全部通过，详见 [author-tests.log](author-tests.log)。

原条款8通过列明独立手算；条款9通过列明严格域及异常检查；条款10具名语义与普通支持域/容差行为符合本次标准。未把数学上正尺度直角变换的可逆性扩张为任意浮点规模下逐位无损保证。

## 6项非阻断数值表示观察

[numerical-observations.json](numerical-observations.json)保留精确输入、数学参照、实际及比较结果。它们不是新增验收失败，也不等于所有浮点输入都已证明无损：

1. **端点归一化与配置binary scale的精确逆有微小差异（点、框2项）**：原图30000000×1、scale=7/3、处理x=35000000。直接按配置浮点尺度的精确有理逆算为`14999999.999999998`，R1按文档化端点归一化为`15000000.0`，相差`1.862645149230957e-9`。这是分数乘法舍入后的区间归一化与原浮点系数逆之间的数值差异。文档明确选择端点插值；1e-9是数值比对/手算测试容差，未建立任意尺寸的绝对误差承诺。本例不足以新增REWORK标准，后续若要求严格binary-coefficient逆须先固定该语义。
2. **邻接可表示端点构成的极窄正面积框可能不能在目标float域保持正面积（正、逆2项）**：4×1原图，crop=[1,0,4,1]、scale=[2,1]、左补边1。原框`[1,0,nextafter(1,4),1]`经180°后两条x边都舍入为6；同样窄的处理框无旋转逆向时两条x边都舍入为1。两例均明确抛出Pydantic `ValidationError`（正面积检查），没有返回成功框或默默裁边。代码位置 `geometry/__init__.py:239`、`:244`、`:249`。这属于未建立最小框分辨率的数值表示限制，不要求任意正面积浮点框都可无损变换；若消费者需要统一GeometryError分类或亚ULP框策略，须另行明确接口要求。
3. **整数上限不保证亚像素信息在极大旋转画布中无损（2项）**：原图宽100000000及2**53、180°，原点x=0.1正向后逆向分别得`0.09999999403953552`与`0.0`。整数上限保护整数配置不会静默改值，不能同时保证所有连续分数坐标的相同绝对精度。没有把这两项差异当成普通R01/R02域失败或强加任意规模1e-9保证。

这些观察限制接受结论的外延；本轮没有请求放宽边界、改公共合同或把浮点限制写成新的支持标准。

## 精确复现

cwd：`D:\1800\.local\stages\A01-review-R1\geometry`。

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B 'D:\1800\docs\evidence\A01\review-R1\geometry\run_geometry_review_r1.py' --snapshot 'D:\1800\.local\stages\A01-review-R1\03c1af41a134945c406a52a48e3d4f6f0da33eb2\snapshot' --out 'D:\1800\docs\evidence\A01\review-R1\geometry' --temp-root 'C:\Users\ASUS\AppData\Local\Temp\A01-review-R1-03c1af41-v5hlrfgb\geometry'
```

最终退出码 **0**。本进程将snapshot/src置于sys.path首位并断言两个模块真实路径，`-B`、`PYTHONDONTWRITEBYTECODE=1`与`sys.dont_write_bytecode=True`同时生效；源几何目录没有生成`__pycache__`。TMP/TEMP均指向授权普通临时root的geometry子目录，没有把来源输出保护规则改掉。本子任务只运行几何类，不运行来源测试或创建来源包。

第一次脚本尝试退出1：我选择的新增配置25×11、scale=[7/25,3]因浮点 `25*(7/25)=7.000000000000001` 不满足已声明的严格整数尺寸而正确拒绝；不是实现缺陷。改用合法复杂配置scale=[3/5,3]完成检查，同时把原输入保留为 `N.preflight.noninteger-exploratory-size` 的明确拒绝检查。两次执行情况见 [reproduction.json](reproduction.json)。

逐项记录见 [inputs-expected-actual.json](inputs-expected-actual.json)，文本日志见 [independent-tests.log](independent-tests.log)，摘要清单见 [sha256-manifest.json](sha256-manifest.json)。

## 未执行与边界

仅离线读取固定副本与准备手算。未改实现、公共合同、依赖、历史/原始/旧准备证据、调度状态或A02/A04；未访问网络、浏览器、凭据、OCR、模型或平台；未推送、合并、集成或释放A04。整个来源R04、S01/D01、Windows来源symlink、全新安装、处理图实际摘要、A04/CSS-DPR和真实平台坐标不在本几何子任务执行范围内。几何ACCEPTED不是这些层面的结论。
