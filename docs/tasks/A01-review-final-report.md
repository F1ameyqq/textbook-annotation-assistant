# A01 正式独立验收报告

日期：2026-10-16（Asia/Shanghai）。结论：**REWORK**。

冻结交付的正常样例和作者测试均可复现，但独立反例暴露了几何边界/可逆性缺陷，以及静态来源加载器未拒绝的内部来源矛盾。当前不能接受本次 A01 交付。S01 公共完整性门禁仍未实现；它是作者已说明的后续集成缺口，不能把说明文字当作机器检查。

## 固定版本与运行边界

| 项目 | 确切值 |
|---|---|
| 被验交付 | `a8d5e96d128e10d341de935d4856682e50df79d9` |
| 实现提交 | `c8b8c6e158547954c59017211507755f67eda0e8` |
| base_commit / workflow_commit | `39341c98d73c354d639f3beeb55429f55d0e9be5` |
| C01 接受版本 | `4e42668ab28eda37a37285285d2f6c595d3bba12`，已核对为交付祖先 |
| 冻结执行报告 SHA256 | `df8b5c0123cdb9f75146c345ae2301a83dfad0efdf93fd6db5f0672f0a260ae2` |
| 合同 / source / geometry | `1.0.0-a-proposal` / `a01-static-1` / `a01-geometry-1`，均保留 A 内部提案状态，B 未确认 |
| 环境 | Windows，CPython 3.9.13，Pydantic 2.12.5，Pillow 11.3.0；未安装新依赖或修改全局配置 |

依据[正式交接](A01-review-handoff.md)、[独立验收任务](A01-independent-review.md)和[执行任务](A01-source-geometry.md)。被验代码从确切提交导出到 `.local/stages/A01-review/a8d5e96d128e10d341de935d4856682e50df79d9/snapshot-verified/`，不依赖源分支浮动 HEAD。57 个交付变更文件均在授权范围；整个导出787个 Git 文件逐一核对 blob OID/摘要。执行报告及原准备证据字节核对通过，见[隔离导出记录](../evidence/A01/review/formal/bootstrap.json)和[最终完整性记录](../evidence/A01/review/formal/final-integrity.json)。

首次 `git archive` 受主机换行与文件属性影响，未通过字节校验；正式使用副本已从确切 Git blob 校正并核验全部文件。没有用失败导出运行验收。几何探索首次漏设禁写字节码，临时副本产生非 Git `__pycache__`；最终将这些派生文件单列，787份提交文件保持原字节。正式命令固定 `-B` / `PYTHONDONTWRITEBYTECODE=1`、临时导入路径及本任务 TMP/TEMP，不修改源工作树或安装包。

## 作者命令复现与独立核验

冻结副本 cwd，Python 显式导入该副本 `src`。真实 `contracts`、`source.static`、`geometry` 的模块路径见[导入记录](../evidence/A01/review/formal/reproduction/01-import-paths.stdout.txt)。以下命令的退出码、cwd、环境、完整 stdout/stderr 见[命令清单](../evidence/A01/review/formal/reproduction/commands.json)。

```powershell
$env:PYTHONPATH = '<冻结副本>/src'
python -B -m unittest discover -s tests -p 'test_a01_*.py' -v
python -B -m unittest discover -s tests -p 'test_contracts*.py'
python -B examples/a01/consume.py examples/a01/bundles/46006966/exchange.json --book-id 46006966
python -B examples/a01/consume.py examples/a01/bundles/46007447/exchange.json --book-id 46007447
python -B examples/a01/build.py '<本任务临时新目录>/independent built bundles'
python -B examples/a01/verify.py '<本任务临时新目录>/independent author evidence'
```

上述6条功能命令及1条导入定位命令均退出0。A01 23项：22通过、1跳过；C01 70项全部通过。`build.py` 实际重建两书；`verify.py` 实际重跑对应套件和两书搬运消费，其重复运行是为复现该交付命令，不增加独立成绩。Windows 文件符号链接测试仍因 WinError1314 跳过；目录联接逃逸已真实创建并拒绝，不能互相替代。

独立核验分三组，成绩不与作者测试相加为覆盖率：

- [来源、原件和搬运核验](../evidence/A01/review/formal/inventory-relocation/run-02/results.json)：66项通过。旧归档4图与 raw6图共10条关系去重为6张原图，新书两组副本共4条关系去重为2张；逐图完整解码、尺寸和 SHA256 相符。250/214是元数据总量，范围外未取得244/212个源索引分列；映射只限有证据页面，未知印刷页不补猜。两包完整复制到含空格目录，从另一 cwd 消费成功，原包及27份准备基线输入字节不变。
- [几何独立核验](../evidence/A01/review/formal/geometry-independent/review.md)：126项，119通过、7失败。8组手算中44项点/框、尺寸和独立逆向检查全通过；失败是新增的4类数值反例，不是依赖或导入失败。
- [来源独立反例](../evidence/A01/review/formal/source-independent/REPORT.md)：28项，16项正确拒绝、1项正常加载、10项非预期接受、1项symlink跳过。10项包括9个重新封装后的内部来源矛盾及1个已知S01门禁缺口。未发现 `import_book` 直接生成这些错误产物，缺陷发生在公开加载边界。

本验收者另外用独立脚本确认7个几何失败和2个来源失败，见[主验收者复现](../evidence/A01/review/formal/primary-confirmation/results.json)。错误输入只改临时副本，已存在旧产物保持原字节。

## 原10条标准的逐项结果

| 条款 | 结论 | 证据及实际边界 |
|---|---|---|
| 1 确切提交、范围、C01、规则和环境 | PASS | 固定上述版本；57文件无越界；787个blob一致；报告摘要相符；不用界面completed作为接受依据 |
| 2 重跑作者测试/消费者、定位实际代码 | PASS（复现） | 7条命令退出0，A01 22+1跳过、C01 70通过；这不覆盖新增反例 |
| 3 两书字节、解码、页映射、取得数量 | PASS（固定交付） | 66项独立核验含完整解码；旧6图/新2图、源索引/viewer/印刷页分开；不把元数据当采集数 |
| 4 原件保全、历史质量、缺失来源 | PASS（固定输出）；加载边界有缺口 | 逐历史资源对原件字节一致；越界x2=1181.0944752623527保留，历史全UNVERIFIED；四份JSON缺失/五条外机原位置限制均保留。重封装矛盾见R04 |
| 5 整包搬运、不同cwd、包内引用 | PASS；文件symlink未执行 | 两书完整复制后消费退出0；可执行引用均包内、无个人绝对路径；目录联接逃逸拒绝。文件symlink权限不足未验证 |
| 6 独立来源反例及不覆盖旧产物 | FAIL | 常规错摘要/尺寸、缺图、损坏像素、已知映射冲突、串书、路径逃逸、重复导入均拒绝；9类重新摘要封装后的内部矛盾仍加载，见R04 |
| 7 scope_manifest来源和完整性 | 有限范围表达PASS；机器门禁未实现 | 固定包如实标REFERENCE_ONLY/UNKNOWN，A01消费者输出false，无作者伪造CheckReport/PASS；确切原SourceBundle接入公共组合后仍可接受合成PRE_APPLY PASS，见S01，不记成完整性通过 |
| 8 独立手算非方图/组合点框 | PASS（列明样例） | G01–G08共44断言全部通过，独立字面预期且从手算处理坐标逆向，非仅正逆相消 |
| 9 额外方向/中心/边界/非法/容差反例 | FAIL | 常规73拒绝检查通过；R01–R03违反合法支持域、严格补边域和整数输入保真，7个失败断言 |
| 10 具名规范/消费/支持域一致 | 部分PASS，整体FAIL | G01具名提案、模糊C01变换显式拒绝；支持域的可逆性/严格边界/不静默改值声明被R01–R03反例否定 |

## 必须修复的最小反例

以下代码行均指本报告固定的交付提交。输入、期望、实际错误及可运行脚本见[几何最小输入输出](../evidence/A01/review/formal/geometry-independent/minimal-counterexamples.json)、[来源逐例证据](../evidence/A01/review/formal/source-independent/results.json)和主验收者复现。各变异来源包是**新的内容摘要**，不声称它们仍与冻结交付同一内容身份；检查的是包内保留记录的相互矛盾，不要求无签名包独立证明所有外部来源真实。

### R01（P1）：合法边界的正向/逆向变换误拒绝

1. 原图5×1，crop `[2,0,5,1]`，scale `[7/3,1]`，无补边/旋转。输出尺寸合法为7×1。规范分阶段计算 `(5-2)*(7/3)=7.0`，点 `(5,0)` 应为 `(7,0)`，整裁片框应为 `[0,0,7,1]`；实现展开矩阵算成 `7.000000000000001`，点和框均报 `processed_point: [BOUNDS]`。
2. 原图3×7，crop `[0,1,3,7]`，scale `[1/3,1]`，顺时针90°。处理尺寸6×1；合法处理边界点 `(6,0)` 应逆向为 `(0,1)`，处理整内容框 `[0,0,6,1]` 应为 `[0,1,3,7]`。逆矩阵常数变为 `6.999999999999999`，结果y落成 `0.9999999999999991`，点和框均报 `original_point: [BOUNDS]`。

位置：`geometry/__init__.py:60`、`:70`、`:152`、`:177`、`:183`。这是普通小尺寸、正有限尺度和整数输出尺寸，不能以“极端数值不支持”排除。修复须维持输入域严格拒绝，同时正确处理声明支持的合法边界，不能直接扩大合法域或静默裁边。

### R02（P2）：严格落在补边区的点/框漏拒绝

原图4×1，crop `[1,0,4,1]`，scale `[2,1]`，padding `[1,0,0,0]`。处理内容左界恰为1。输入 `x=math.nextafter(1.0,0.0)=0.9999999999999999` 严格小于1，点 `(x,0)` 与框 `[x,0,3,1]` 均应拒绝；实际逆向分别接受为 `(1,0)`、`[1,0,2,1]`。

位置：`geometry/__init__.py:182-183`。先逆映射再检查原域时，舍入已丢失输入位于补边的信息。此例按已声明的“无容差接纳越界”要求失败，不将其夸大为可见的大幅坐标偏移。

### R03（P2）：大整数补边静默改变输入

原图1×1，padding左值为精确整数 `2**53+1=9007199254740993`。应精确保留或显式拒绝不能精确表示的值；实际构造成功后 padding变成9007199254740992，输出宽度比精确保留时少1。

位置：`geometry/__init__.py:29`、`:112-120`。该例补充验证极端数值限制；即使单独明确拒绝此数值范围，R01/R02仍须修复。

### R04（P2）：重新摘要封装后，内部来源/历史矛盾未拒绝

最小优先例：将旧书 `provenance.origins[0].manifest_sha256` 改为全零，包内对应 `original_manifests` 与 `input-integrity` 仍保留正确原清单摘要。经公共seal更新资源及artifact摘要后，公共加载器和 `load_static_bundle` 均接受。将 `origins=[]` 也接受，六个资产的逐图来源关系可全部缺失。主验收者分别复现，完整失败包存于 `formal/primary-confirmation/S-origin-manifest-digest-conflict/` 与 `S-origins-empty/`。

同组扩展输入还包括：`input-integrity.unchanged=false`且before/after不等；历史标注改为另一本书、其原件摘要仍未改；历史quality升REVIEWED而没有核准证据；删除已知missing_sources；无依据印刷页999；scope状态与UNKNOWN矛盾；参考ID与公共清单矛盾。均见S12–S20逐例。固定导入器实际输出没有这些问题，不能写成“作者直接生成了假数据”。

位置：`source/static/importer.py:401-405`仅要求完整性资源存在；`:438-444`未要求origins覆盖资产，也未交叉核对清单摘要；`:449-450`只核对参考条数和basis文本。恢复条件为在A01加载边界验证所声明的内部来源/历史一致性并给出定位拒绝，或由主调度明确调整受保证的接口边界；本验收不替作者修实现，不自行降低原标准。

## 已知合同与环境缺口

**S01：后续自动放行门禁缺口已实证。** [主验收者固定交付反例](../evidence/A01/review/formal/primary-confirmation/S01-fixed-delivery-gate.json)严格保留冻结样例的SourceBundle对象及其 `content_hash=1b662ac5c9ac56b4a0c2e9826ff4cc2c512365c58ca2fafda36df110f9cfc32d`，limitations仍为 `coverage_eligible=false`、denominator UNKNOWN；仅追加显式SYNTHETIC EvidenceBundle/QuestionGraph/CheckReport。公共 `load_bundle(..., verify_assets=True)` 仍接受PRE_APPLY PASS。完整合成反例包保存在同目录 `S01-fixed-delivery-input/`。

这证明说明文本不是公共机器门禁；不是真实质量PASS，也没有PlatformSnapshot、ApplyPlan或平台写入。A01 source-only加载器仍拒绝多工件，示例消费者仍输出false。作者已提出S01且无权改公共合同，故将其列为**主调度/合同负责人必须解决的后续集成限制**，不假装已经实现，也不因本验收擅自扩权修改合同。

来源子报告S23的“原SourceBundle未改”比较对象是用冻结实现重建的基准包，和冻结交付样例仅created_at及随之变化的content_hash不同；不能作为原交付对象原字节证明。本报告采用主验收者另造的确切冻结样例反例，旧证据原样保留。

**D01：Pillow依赖未列根声明。** 冻结 `pyproject.toml` 仅声明Pydantic；source模块实际导入Pillow。本机已有Pillow11.3.0，本轮成功复现不等于全新安装通过。执行者按范围提交了D01提案，由共享依赖负责人在集成时处理；本验收未安装环境、未改根配置，清洁安装未执行。

**未验证项：** Windows文件symlink分支（WinError1314）；全新依赖安装；A04/浏览器CSS-DPR；真实平台；识别配答、独立整页分母与全书覆盖；B确认。不能将目录联接测试或本机既有依赖替代这些证据。

## 证据复现、摘要和结束状态

独立脚本均位于[正式证据目录](../evidence/A01/review/formal/)。最短入口：

```powershell
python -B D:/1800/docs/evidence/A01/review/formal/geometry-independent/run_geometry_review.py --snapshot '<冻结副本>' --out '<新的正式证据子目录>'
python -B D:/1800/docs/evidence/A01/review/formal/replay-source.py --snapshot '<冻结副本>' --out '<formal下新的证据子目录>' --stage D:/1800/.local/stages/A01-review/source-probes/run-reproduce
```

几何脚本退出1表示检测到7个失败，非环境失败；来源脚本退出0只表示完成取证，结果须读`matches_expectation`。来源子报告原直接运行命令会写脚本所在目录，复现时采用这里的wrapper复制脚本到新证据目录，不直接重跑覆盖已冻结的来源证据。主验收者确认脚本路径及命令见[运行摘要](../evidence/A01/review/formal/review-summary.json)。有排他新建保护的脚本重跑需新目录，不覆盖既有证据。

验收脚本的准备错误已区分：初次路径扫描把HTTPS中的` s:/ `子串误判为本地盘符，修正验收正则后66项全通过，旧run保留；S23初次合成探针漏声明policy曾被拒，修正探针后才有有效门禁反例；未把这些验收脚本问题记为A01实现失败。

报告与全部正式证据的逐文件SHA256见[统一摘要清单](../evidence/A01/review/formal/sha256-manifest.json)，确切代码/输入/输出、命令、退出码和限制均保留。准备报告及既有准备证据未覆盖。

**结束状态：REWORK；未集成；未释放A04。** 下一步仅由主调度安排执行者修复并交付新的冻结版本，再开展复验。本轮只写授权正式报告/证据和任务临时目录，没有改实现、公共合同、历史资料、政策、父入口、调度状态或其他任务；没有推送、合并、平台动作、浏览器、凭据读取、网络、OCR或付费模型调用，模型工具费用0。本报告不宣称B接受、真实保存、算法质量或全书完整性。
