# A01 有界 R1 执行交付

状态：**REVIEW**。首次独立验收结论为 REWORK；本轮仅修 R01–R04并提交执行者复现证据，等待原独立验收对话复验。本报告不作 ACCEPTED/INTEGRATED 结论，不释放 A04 依赖。

## 固定版本与范围

- 工作树：`C:/Users/ASUS/.codex/worktrees/a01-source-geometry/1800`；分支：`codex/a01-source-geometry`。开工时 HEAD=`a8d5e96d128e10d341de935d4856682e50df79d9`，工作树干净。
- R1 base_commit：`a8d5e96d128e10d341de935d4856682e50df79d9`。原 base/workflow_commit：`39341c98d73c354d639f3beeb55429f55d0e9be5`。没有合并浮动主分支。
- **R1确切实现提交：`0ee7e836e3bc1849f91840b4271d233bbd8e72dd`**，含修复、测试、新样例与运行证据。随后只追加本报告及归档清单；包含报告的最终交付提交完整SHA随最终交付消息提供，代码仍为上述冻结实现。
- 规则是主工作目录只读任务 `D:/1800/docs/tasks/A01-rework-R1.md`。正式验收报告SHA256=`157dddf56287a1a3b3d1fd2714d63e8a068fb34b052fe949eb06b75c9901a8a3`，已核对；主目录文件未复制或写回。
- 环境：Windows / CPython3.9.13 / Pydantic2.12.5 / 已安装Pillow11.3.0；无依赖安装。实际模块路径和摘要见 [delivery/results.json](../evidence/A01/execution/R1/delivery/results.json)，全部导入指定工作树的 `src`。
- C01合同仍 `1.0.0-a-proposal`。来源实现为 `a01-static-1-r1`，继续兼容旧 `a01-static-1` 包；几何规范仍 `a01-geometry-1`，数值实现版本 `a01-geometry-1-r1`。都是 A 内部提案，不宣称 B 已确认。
- 只改原授权 source/static、geometry、A01测试/说明及R1专属样例/证据/报告。没有改 contracts、父入口、根依赖/配置、delivery/runtime/B模块或调度状态；没有向其他对话派单、推送或集成。

## 逐项修复与前后证据

修复前使用未改动的a8d5e96模块重放：7个几何和9个来源反例全部不符合预期（0/16）。最终重放16/16符合预期，退出0。源码路径及摘要、输入、预期和实际都保留于 [before/results.json](../evidence/A01/execution/R1/before/results.json)、[after/results.json](../evidence/A01/execution/R1/after/results.json)。这16项是执行者对正式反例的复放，不是新的独立验收成绩。

| 条款 | 修复前 | R1实现与实际结果 |
|---|---|---|
| R01 合法边界误拒绝 | 正向点/整框报BOUNDS；90°逆向点/整框报BOUNDS | 正向按crop→scale→pad→rotate逐阶段运算；逆向不展开逆矩阵，以已验证区间端点作等价逆缩放插值，Fraction精确计算后一次转float。5×1例得到点[7,0]/框[0,0,7,1]，3×7例得到点[0,1]/框[0,1,3,7]；均与字面预期一致。没有扩大epsilon或裁边 |
| R02 严格补边域漏拒绝 | nextafter(1,0)点/框接受成原图合法边界 | 先在最终处理图 `content_bounds` 检查输入，再逆旋转/逆缩放。该点与框均报BOUNDS，精确x=1边界接受；四种旋转的相邻内/外点、外框均有回归 |
| R03 整数输入改变 | 2**53+1补边被改成2**53后接受 | 整数转float前限界；图像/画布像素整数上限为2**53，补边总和也核对。2**53+1明确报REPRESENTATION；1×1图配2**53-1左补边原值保留、宽度为2**53；配2**53补边因画布超限也拒绝。普通R01/R02支持域未缩小 |
| R04 内部来源矛盾 | 9个重新摘要/seal后仍有效的C01包被A01加载器接受 | 新的包内一致性检查将原输入摘要、历史原件、来源覆盖、清单、映射、缺失来源、质量及参考身份交叉核对。9例仍先经公共C01资源加载成功，然后A01逐例给出定位拒绝，见下表 |

R01相邻测试还暴露过分数裁片逆缩放的除加舍入误拒绝；输入和当时实际错误保留于 [adjacent-before.json](../evidence/A01/execution/R1/adjacent-before.json)。对应两组固定输入已加入 [R1回归](../../tests/test_a01_rework_r1.py)，最终通过。`after-first/` 是中间版本对原16例的记录；最终证据以 `after/` 和 `regression-final/` 为准，不覆盖中间记录。

| R04反例 | 最终code | 最终location |
|---|---|---|
| S12 origins为空 | SOURCE_ORIGINS | provenance.origins |
| S13 origin清单摘要冲突 | SOURCE_MANIFEST | provenance.origins[0].manifest_sha256 |
| S14 无依据printed_page | MAPPING_EVIDENCE | provenance.mappings[0].printed_page |
| S15 删除已知缺失来源 | MISSING_SOURCES | limitations.missing_sources |
| S16 unchanged=false/前后摘要不同 | INPUT_CHANGED | input-integrity.unchanged |
| S17 历史书籍/原件字节矛盾 | HISTORY_BYTES | history/01-manual-annotations.json |
| S18 无证据升REVIEWED | HISTORY_QUALITY | history[0].quality |
| S19 scope状态与UNKNOWN矛盾 | DENOMINATOR_UNKNOWN | limitations.scope_manifest_status |
| S20 参考ID与公共清单不一致 | REFERENCE_RECORDS | provenance.reference_records |

来源变异是新内容身份，非对冻结包原摘要的冒认。加载边界保证包内保留记录不矛盾；不要求、也不声称无签名包可在全部记录被一致替换时独立证明外部真实性。固定导入器未被发现直接生成这些坏包。

## 实际命令与结果

全部cwd为上述指定工作树。新证据/样例均使用不存在的新目录。实际执行结果：

| 实际入口 | 退出码/结果 |
|---|---|
| `python -B examples/a01/R1/probe.py docs/evidence/A01/execution/R1/before` | 1；原16项反例全部失败，按预期留存修复前证据 |
| `python -B -m unittest discover -s tests -p 'test_a01_rework_r1.py' -v` | 最终0；新增8项通过，含16例及相邻合法/非法组合、旧/新两书兼容 |
| `python -B examples/a01/R1/probe.py docs/evidence/A01/execution/R1/after` | 0；7个几何+9个来源具体反例符合预期 |
| `python -B examples/a01/verify.py docs/evidence/A01/execution/R1/regression-final` | 0；实际运行A01 31项：30通过、1跳过；C01 70项全通过；旧包两书搬运消费成功 |
| `python -B examples/a01/build.py examples/a01/R1/bundles` | 0；实际生成两个R1来源包，不覆盖旧包 |
| `python -B examples/a01/R1/validate_delivery.py docs/evidence/A01/execution/R1/delivery` | 0；旧包两书、新包两书、新包两书复制至含空格目录/换cwd共6条消费者子命令全部0；保全检查全部通过 |

最终套件与逐测试结果见 [regression-final/verification.json](../evidence/A01/execution/R1/regression-final/verification.json)；消费者实际argv、cwd、退出码、stdout/stderr及Python导入路径见delivery记录。一次总回归把TMP/TEMP误设在受保护`.local`内，来源输出被OUTPUT_LOCATION拒绝；失败和修正记录见 [environment-correction.json](../evidence/A01/execution/R1/environment-correction.json)。改为A01专属普通临时目录后完成上述最终回归，未放宽保护规则。

最短重现（固定工作树根目录；不要重用冻结证据目录）：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B -m unittest discover -s tests -p 'test_a01_*.py' -v
python -B -m unittest discover -s tests -p 'test_contracts*.py'
python -B examples/a01/R1/probe.py '<新的R1证据目录>'
python -B examples/a01/consume.py examples/a01/R1/bundles/46006966/exchange.json --book-id 46006966
python -B examples/a01/consume.py examples/a01/R1/bundles/46007447/exchange.json --book-id 46007447
```

原正式几何脚本F04构造未捕获异常；本轮按R1任务允许条件采用显式拒绝。因此复验须按“明确拒绝或精确保留”判断该例，不能把旧脚本在合法拒绝处的未捕获异常当作反例仍被错误接受。原脚本及正式证据均未改写。

## 样例、保全与结束边界

新固定样例为 [旧书R1包](../../examples/a01/R1/bundles/46006966/exchange.json)、[新书R1包](../../examples/a01/R1/bundles/46007447/exchange.json)。分别保持6/2原图资产、10/4来源关系、250/214元数据页数、14/1参考记录；完整性仍UNKNOWN且coverage_eligible=false，历史全部UNVERIFIED。没有补造独立分母、覆盖PASS或实时PlatformSnapshot。

- 45个既有执行产物/报告/样例及31个原输入文件的字节摘要保持不变；原执行报告SHA256仍 `df8b5c0123cdb9f75146c345ae2301a83dfad0efdf93fd6db5f0672f0a260ae2`。
- 正式验收报告、摘要、反例、来源结果、调度复现5份只读冻结证据摘要均保持不变。派单任务文件的外部摘要变动另记于 [pre-freeze.json](../evidence/A01/execution/R1/pre-freeze.json)；复读仍为R01–R04，本执行未写主目录。
- 新包29文件的Git暂存字节与实际文件一致，R1局部属性关闭这些资源的换行转换；不修改旧属性或原件。差异检查通过、改动路径均在R1授权范围。
- **S01公共完整性/PRE_APPLY门禁及D01根Pillow依赖声明仍未解决，由主调度负责。** 本地一致性检查不替代公共门禁，本机已安装Pillow不等于清洁安装验证。
- Windows文件符号链接分支仍因WinError1314跳过；目录联接逃逸实际测试通过。未做全新依赖安装、A04/CSS-DPR、真实平台、识别/配答、全页/全书独立分母或B确认。
- 浏览器、profile、凭据、网络、OCR、模型工具均未使用，费用0。未打开浏览器会话，待释放会话数0；不重放A05、不推送、不合并或自行集成。

实现冻结后仅追加本报告和归档摘要，最终Git HEAD、报告SHA256及干净状态在交付消息中记录。状态保持 **REVIEW**，等待原独立验收复验。
