# A01 R1 独立复验报告

日期：2026-10-16（Asia/Shanghai）。结论：**REWORK**。

原 R01–R03 的7个几何反例及 R04 的9个来源反例均已修复。独立邻近来源检查仍发现明确的包内矛盾被加载器接受：已取得页同时记为缺失、历史响应的书籍/页索引与 image URL 冲突、观察索引摘要与保留输入摘要冲突。因此本次 R1 整体不予接受；不能把“原16例通过”推广为来源一致性全部通过。

## 确切版本、隔离与环境

| 项目 | 固定值 |
|---|---|
| 被验 R1 交付 | `03c1af41a134945c406a52a48e3d4f6f0da33eb2` |
| R1 实现 | `0ee7e836e3bc1849f91840b4271d233bbd8e72dd` |
| R1 基线 | `a8d5e96d128e10d341de935d4856682e50df79d9` |
| 原 base / workflow | `39341c98d73c354d639f3beeb55429f55d0e9be5` |
| C01 接受版本 | `4e42668ab28eda37a37285285d2f6c595d3bba12`，祖先关系已核对 |
| R1 执行报告 SHA256 | `61eb2ec6c666d112caf7eb07367f5d35d48ce596453215d92001614000bf2b40` |
| 合同 / 来源 / 几何实现 | `1.0.0-a-proposal` / `a01-static-1-r1` / `a01-geometry-1-r1` |
| 几何具名语义 | `a01-geometry-1`，仍为A内部提案；B未确认 |
| 环境 | Windows，CPython3.9.13，Pydantic2.12.5，已安装Pillow11.3.0；没有安装依赖或改全局设置 |

依据[本轮交接](A01-review-R1-handoff.md)、[R1修复任务](A01-rework-R1.md)、[首轮REWORK](A01-review-final-report.md)和[原独立标准](A01-independent-review.md)。

确切提交导出到 `D:/1800/.local/stages/A01-review-R1/03c1af41a134945c406a52a48e3d4f6f0da33eb2/snapshot/`。890个提交文件逐一核对Git blob，106个改动路径均在R1允许范围；归档及回归清单71项摘要独立核对通过，见[导出记录](../evidence/A01/review-R1/bootstrap.json)和[执行清单复核](../evidence/A01/review-R1/execution-manifests-verified.json)。本轮未运行源工作树浮动HEAD。

实际普通临时根为 `C:/Users/ASUS/AppData/Local/Temp/A01-review-R1-03c1af41-v5hlrfgb/`；作者命令、独立来源包、搬运和子检查均使用各自新子目录，TMP/TEMP/TMPDIR一并固定。源码可在`.local`隔离，但没有在`.local`创建来源输出，也没有修改保护规则。所有导入固定为该副本`src`，记录真实模块路径，使用`-B`/禁写字节码。

## 复现结果与保全

[作者命令清单](../evidence/A01/review-R1/reproduction/commands.json)记录11条真实命令的完整argv、cwd、环境、退出码和stdout/stderr，**全部退出0**：

- A01 31项：30通过、1跳过；C01 70项通过。
- 作者R1反例入口：7个几何+9个来源，共16项符合预期。
- 旧格式两书、新R1两书4次固定消费成功；`build.py`实际创建新来源包。
- `validate_delivery.py`实际执行6个消费者，含搬运；`verify.py`重跑其声明的相关套件和两书搬运。
- 真实导入路径指向隔离副本，没有误用其他editable安装。

最短作者命令（在上述副本cwd，输出均选不存在的新目录）：

```powershell
$env:PYTHONPATH = '<副本>/src'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:TMP = '<本任务普通临时根>/author-temp'
$env:TEMP = $env:TMP
$env:TMPDIR = $env:TMP
python -B -m unittest discover -s tests -p 'test_a01_*.py' -v
python -B -m unittest discover -s tests -p 'test_contracts*.py'
python -B examples/a01/R1/probe.py '<新的临时证据目录>'
python -B examples/a01/consume.py examples/a01/R1/bundles/46006966/exchange.json --book-id 46006966
python -B examples/a01/consume.py examples/a01/R1/bundles/46007447/exchange.json --book-id 46007447
```

[本验收者保全和搬运检查](../evidence/A01/review-R1/preservation-relocation/results.json)223项断言通过：45份既有产物逐字节对R1基线、31份原输入对基线及前后摘要；4个旧/新包完整复制到含空格目录，从不同cwd消费均成功。四包原图实际解码、尺寸/摘要和历史原件字节检查通过，保持旧书6图/10来源、新书2图/4来源、250/214元数据、14/1参考记录及UNKNOWN/UNVERIFIED边界。本223项为独立断言数，不与调度预检的223项Git核对混算。

372份原准备/正式报告及证据在本轮前后摘要一致；890个隔离提交文件保持原字节。统一结束核对见[最终完整性记录](../evidence/A01/review-R1/final-integrity.json)。未覆盖旧失败材料或旧报告。

## 原修复项的逐条结论

| 修复项 | 本次结论 | 独立证据 |
|---|---|---|
| R01 合法点/框正向、逆向误拒绝 | ACCEPTED（原反例及列明邻近范围） | 原4例全部通过；独立组合、分数裁片和精确端点检查通过 |
| R02 严格补边域漏拒绝 | ACCEPTED（列明检查） | 原2例拒绝；四旋转下边界内/边/外相邻点和框检查通过；输入先检查content_bounds |
| R03 大整数静默改变 | ACCEPTED（明确限界） | 原F04明确REPRESENTATION拒绝；整数上限和画布总和检查通过，与文档2**53限界一致 |
| R04 原S12–S20内部矛盾 | 原9例ACCEPTED；整体来源一致性仍REWORK | 原9例全部先通过公共资源校验，再被A01定位拒绝；新邻近反例仍接受，详见下一节 |

[几何子报告](../evidence/A01/review-R1/geometry/review.md)：630个验收断言通过、0失败，含原7例、8组手算、3组非方/分数裁片组合×四旋转、相邻内外点/框、11项整数上限/画布总和；作者旧几何8项及R1几何6项也通过。点/框预期由独立字面值、分阶段公式和端点模型计算，不仅正逆相消。按原标准，F04构造时的明确拒绝是通过；没有修改旧脚本或把其未捕获异常误计实现失败。

R1逆向按文档使用已验证区间端点和Fraction插值；Fraction本身没有被当作正确性证明。另6项浮点表示观察单列于[数值观察](../evidence/A01/review-R1/geometry/numerical-observations.json)：配置尺度精确逆与端点归一化的差异、极窄框不能表示、超大画布子像素丢失。它们不表示全域无损精度已证，也不把文档用于手算比对的1e-9泛化为任意规模的绝对误差承诺。本轮几何接受限于已声明语义和列明检查；未给A04释放信号。

[来源子报告](../evidence/A01/review-R1/source/REPORT.md)：32项中4个正常旧/新包接受、22个非法包拒绝、6个邻近矛盾仍接受。原9例及13个其他邻近拒绝检查符合预期。全部变异从确切交付的固定包复制，未将重建包当作原冻结样例。所有新变异包重新计算公开资源和artifact摘要，属于新的内容身份；检查的是互相保留记录的矛盾，不要求无签名包自证全部外部真实性。

## 尚未通过的最小反例

本验收者另用[独立确认脚本](../evidence/A01/review-R1/primary-source-confirmation.py)确认以下4个失败，实际退出**1**表示检测到未满足的拒绝要求，不是环境失败。每例都先通过公共`load_bundle(..., verify_assets=True)`，R1的`load_static_bundle`仍接受。精确输入、期望、实际、模块路径、内容摘要及完整可搬运反例包在[主验收者结果](../evidence/A01/review-R1/primary-source-confirmation/results.json)及同目录P01–P04。

### R1-F01（P2）：已取得/缺失范围记录相互矛盾仍接受

旧书R1包保持source7资产、映射、selected_source_indices及6张实际原图，单独设置 `provenance.selected_missing_source_indices=[7]`。该页同时声明已取得和缺失，应定位拒绝，实际接受为book46006966。

来源子检查N14还把已选择/取得的source7追加到 `outside_selected_scope_unacquired_indices`，结果已取得6+外部未取得245=251，超过元数据250且集合相交，仍接受。此例不需要外部证据即可判断矛盾。

位置：固定提交 `source/static/importer.py:445-448` 只核对取得数和selected集合；`consistency.py`未核对两类缺失字段与选择/取得范围的分区关系。必须保持范围记录内部一致，不能仅依靠正常导入器刚好生成正确侧车。

### R1-F02（P2）：历史响应的image URL与书籍/页索引冲突仍接受

新书R1包的 `history/00-independent-source-page14.json`：

1. 保持 `data.file_id=46007447`、`pages[0].page_index=13`，将image URL路径中的书籍改为46006966，应拒绝跨书矛盾，实际接受。
2. 保持同书及page_index13，只将原URL末尾 `_page_13.jpg` 改为 `_page_172.jpg`，应拒绝同一响应的索引矛盾，实际接受。来源子检查另做了保持原主机名的最小化复跑，结果一致，见[最小URL反例](../evidence/A01/review-R1/source/minimal-url/result.json)。

两例同时更新被改历史文件在input-integrity中的before/after摘要及资源引用，确保字节一致性检查不先挡住；其余资产/映射/响应业务字段保留。矛盾存在于响应自身或与保留映射之间，不是无外部信任锚的自洽伪造。

位置：`source/static/consistency.py:175-179`检查file_id及page_index，但没有核对image字符串的书籍和源索引。首次导入已有纯字符串 `url_index` 校验；本例仅离线解析归档文本，没有网络请求。

### R1-F03（P2）：观察索引来源摘要与保留清单冲突仍接受

新书R1包单独将 `provenance.observation.observation_index_source.sha256` 改全零；同archive_path在 `input-integrity.inputs` 的before/after仍保留正确原摘要。资源和artifact重封装后，A01继续接受。

位置：`source/static/consistency.py:186`核对archive boundary，但未将观察索引来源摘要与同路径输入清单交叉核对。本例是一个摘要字段与包内保留摘要直接矛盾，不要求访问原网络索引或外部源。

来源N15把历史precision标签升为LIVE_OBSERVATION也被接受；作为较低风险元数据观察列明，不单独支撑本REWORK，也不声称生成了实时PlatformSnapshot。

恢复条件：执行者对上述明确范围分区、历史URL绑定及观察索引摘要补足定位拒绝，同时保持原16例、旧/新四包和搬运消费通过。是否安排下一轮由主调度决定；本验收不修实现、不自行派发或反复自动重试。

## 未解决限制及证据复现

- **S01未解决**：公共合同仍可接受基于参考清单构造的合成PRE_APPLY PASS。本轮用未改的公共合同重读首轮固定反例仍通过；A01消费者仍输出coverage_eligible=false。来源一致性修复不等于公共资格门禁实现，不是实际质量PASS。
- **D01未解决**：冻结根依赖仍仅声明Pydantic，本机已有Pillow不能证明全新安装完整。没有安装环境或修改根依赖。
- Windows文件symlink分支仍WinError1314跳过；目录联接测试实际通过。全新安装、A04/CSS-DPR、浏览器/真实平台、OCR/识别配答、独立全页/全书分母及B确认均未验证。

独立几何复现可给`run_geometry_review_r1.py`新的`--out`；来源脚本的证据目录绑定脚本位置，**重跑须先复制脚本到review-R1下新的子目录**，不能直接覆盖已冻结来源证据。各实际命令/退出码见[运行摘要](../evidence/A01/review-R1/review-summary.json)、作者命令清单及子报告。任务临时目录均使用本轮已记录普通系统临时根。

全部新证据和本报告的SHA256见[统一清单](../evidence/A01/review-R1/sha256-manifest.json)。本轮结束状态：**REWORK；未集成；未释放A04。** 未修改源码、公共合同、历史/旧失败证据、政策、根配置、调度状态或其他任务；无浏览器、凭据、平台、网络、OCR或模型工具调用，费用0，无推送或合并。结论仅覆盖A01有界离线来源与声明的几何能力。
