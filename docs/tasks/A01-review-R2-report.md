# A01 R2 独立复验报告

日期：2026-10-17（Asia/Shanghai）。结论：**REWORK**。

指定的直接路径反例均已修复；范围分区和观察索引绑定通过本轮有界独立检查。R2-02仍有一个最小解析缺口：加载器在整个URL字符串尾部寻找书籍/页索引，query或fragment中的路径文本可以掩盖真正URL path的矛盾。本报告将剩余修复收敛到这一关系，不扩展主机认证、N15、S01或D01。

## 固定版本与隔离

| 项目 | 确切值 |
|---|---|
| 被验交付 | `c3aff9598b6705ab4122062615a13ae3774698b2` |
| 实现 | `63ac5a184798326d629a43d1dfed25fa73a1a27e` |
| R2基线 | `03c1af41a134945c406a52a48e3d4f6f0da33eb2` |
| 原base / workflow | `39341c98d73c354d639f3beeb55429f55d0e9be5` |
| C01接受版本 | `4e42668ab28eda37a37285285d2f6c595d3bba12`，祖先关系已核对 |
| 执行报告SHA256 | `3aeaaf40e55163541921ec5915995cc9d01b878bb6843f76fb9f048d5dba8d50` |
| 归档manifest SHA256 | `ed4aee2d5aaf4b71f5eee6c60c90c0b58c1672a4803507bb03d1056c00000576` |
| 来源 / 合同 | `a01-static-1-r2` / `1.0.0-a-proposal`，仍为A内部提案，B未确认 |
| 环境 | Windows，CPython3.9.13、Pydantic2.12.5、已安装Pillow11.3.0；未安装依赖或修改全局设置 |

依据[本轮交接](A01-review-R2-handoff.md)、[R2有界任务](A01-rework-R2.md)、[原独立标准](A01-independent-review.md)和[R1失败报告](A01-review-R1-report.md)。

源码导出到 `D:/1800/.local/stages/A01-review-R2/c3aff9598b6705ab4122062615a13ae3774698b2/snapshot/`，974个提交文件逐一核对Git blob，88个变更路径在允许范围；没有使用浮动工作树。见[导出记录](../evidence/A01/review-R2/bootstrap.json)。

任务普通临时根为 `C:/Users/ASUS/AppData/Local/Temp/A01-review-R2-c3aff959-__n2y2in/`，来源包、TMP/TEMP/TMPDIR和搬运使用各自新子目录，不放受保护`.local`。作者`verify.py`会自行将临时目录设在其ROOT/examples下，因此作者命令另在该普通临时根内的`verified author source/`运行；该副本全部974文件也先与同一冻结Git字节核对。见[第二源码副本核验](../evidence/A01/review-R2/reproduction/source-copy-verification.json)。未修改代码或保护规则，实际模块路径和摘要均记录。

## 作者命令复现

[真实命令清单](../evidence/A01/review-R2/reproduction/commands.json)保存13条顶层命令的argv、cwd、环境、退出码和完整日志：**12条退出0，`examples/a01/R2/verify.py`退出1**。不能按执行者自报记为全部成功。

实际功能结果：

- A01 41项：40通过、1文件symlink权限跳过；C01 70项通过。
- 原16反例入口16/16符合预期；R2入口含4个正式冻结输入与5个便携反例，9/9符合预期。
- legacy/R1/R2三代两书共6包直接消费成功，`build.py`实际生成新包。
- `verify.py`内部15条功能子命令均退出0，含上述套件、原16例和12次直接/搬运消费；**随后最终保全assert失败**，详见下一节。

作者入口实际输出已原字节保存：[原16例](../evidence/A01/review-R2/reproduction/original16-results.json)、[R2九例](../evidence/A01/review-R2/reproduction/R2-nine-results.json)、[verify完整结果](../evidence/A01/review-R2/reproduction/author-verify-results.json)和[失败stderr](../evidence/A01/review-R2/reproduction/13-verify.stderr.txt)。

最短功能命令（在已核验副本cwd；TMP/TEMP使用上述普通临时根，输出选不存在的新目录）：

```powershell
$env:PYTHONPATH = '<副本>/src'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:TMP = '<任务普通临时根>/author-temp'
$env:TEMP = $env:TMP
$env:TMPDIR = $env:TMP
python -B -m unittest discover -s tests -p 'test_a01_*.py' -v
python -B -m unittest discover -s tests -p 'test_contracts*.py' -v
python -B examples/a01/R1/probe.py '<新的原16例输出>'
python -B examples/a01/R2/probe.py '<新的R2输出>' --official-inputs D:/1800/docs/evidence/A01/review-R1/primary-source-confirmation
python -B examples/a01/R2/verify.py '<新的verify输出>'
```

## 保全、搬运及verify保全断言的限制

本验收者[独立保全与搬运检查](../evidence/A01/review-R2/preservation-relocation/results.json)1162项断言通过，覆盖：

- 886个受保全旧文件的当前原始Git blob与R2基线一致；31份原输入前后摘要一致；7份主目录只读输入与交付时声明摘要一致。
- 87项R2归档清单与实际冻结文件摘要一致。
- 六个旧/R1/R2两书包逐图完整解码、尺寸/摘要、历史原件字节、UNVERIFIED质量及REFERENCE_ONLY/UNKNOWN限制保持；六包完整复制到含空格目录、不同cwd再次消费，全部退出0。
- R1旧测试差异仅导入当前VERSION并调整生成器版本断言；原反例及拒绝期望未降低，补丁随证据保存。

`verify.py`的保全基线使用原Windows工作树磁盘摘要；其中25项与Git blob的换行格式不同。独立检查确认，**这25项全部仅为统一LF/CRLF差异**，原始Git文件未被本轮修改。其余功能子命令、geometry摘要及31份原输入均通过。相关逐文件磁盘预期、Git摘要、LF/CRLF候选摘要见独立结果的`author_disk_baseline_EOL_differences`。

因此该入口在确切Git原字节导出上的最终退出1是**保全基线不可直接跨换行格式复现的限制**，不是发现旧资料被篡改；也不能删掉assert或修改副本字节来制造退出0。本报告如实保留失败。后续若要求该公开入口在Git原字节导出上全通过，应由执行者对其保全基线/复现约定作明确处理；本验收未修脚本或放宽校验。

642份旧准备/首轮/R1验收材料及报告在本轮前后摘要一致。最终两个源码副本、旧证据和新证据清单核对见[最终完整性记录](../evidence/A01/review-R2/final-integrity.json)。

## 三项修复的独立结论

| 项目 | 本轮结论 | 证据 |
|---|---|---|
| R2-01 范围分区 | ACCEPTED（有界检查） | 86项符合预期：16合法、66来源语义拒绝、4公共层控制；8个合法非零missing/空outside包搬运成功 |
| R2-02 历史URL绑定 | REWORK | 固定跨书/错页直接路径已拒绝，query/fragment掩盖实际path仍接受；子检查3变体，主验收者另确认2变体 |
| R2-03 观察索引路径/摘要 | ACCEPTED（有界检查） | P04及15项邻近检查符合预期；同路径摘要、错绑定、缺失/错类型/越界路径均在公共资源通过后定位拒绝 |

[分区子报告](../evidence/A01/review-R2/partition/REVIEW.md)独立构造两书源索引0/上界、非零缺页、selected覆盖全集且outside为空、乱序集合的合法输入；未生成缺失原图/尺寸/摘要，构造意图显式SYNTHETIC，完整性仍UNKNOWN。重复、bool/float/负值/越界、交叠、遗漏及公共数量矛盾均按预期处理。66个来源拒绝均先实际通过公共资源校验；4个公共控制明确单列，未拿它们冒充来源语义拒绝。未发现本范围残余。

[来源子报告](../evidence/A01/review-R2/source/REPORT.md)50项全部先通过公共`verify_assets=True`：47符合预期、3错误接受。原R1 P01–P04按确切整包复制重放，4/4定位拒绝；三代两书六包正常；URL25例中22符合预期、3失败；观察索引15例均符合预期。HTTP(S)、合法主机文本、第二页响应和原查看器映射保持；没有硬编码统一页偏移或把主机字符串当来源认证。

## 剩余最小缺口：URL path被query/fragment文本替代（P2）

固定提交 `src/annotation/source/static/importer.py:102-107`先用`urlsplit`检查scheme/主机，**第108行仍对整个原始url做尾部正则匹配**。`consistency.py:240-243`消费这个错误解析的源索引，导致query/fragment尾部覆盖真正路径身份。

最小例：新书历史页14响应保持`file_id=46007447`、`page_index=13`和保留source13映射，仅把image设为：

```text
https://archive.example.invalid/upload_images/46007447/46007447_page_172.jpg#/upload_images/46007447/46007447_page_13.jpg
```

标准解析得到的实际path是source172；fragment中的source13不会改变实际资源路径。预期应拒绝实际path与响应/映射13冲突，当前公共/A01均接受。另一个例子实际path两处book为46006966，但query尾部放入46007447/source13路径，也被接受。

所有例子同步历史文件input-integrity before/after、公共资源摘要和artifact seal，**先实际通过公共资源校验，再观察来源语义错误接受**。它们是新内容身份，不冒认冻结原包；矛盾保留于同一URL的不同组件与响应字段，不需要访问网络或外部信任锚。

子检查U23/U24/U25保存3个变体；主验收者另用[独立脚本](../evidence/A01/review-R2/primary-url-path.py)确认Q01/Q02，脚本退出1表示两个拒绝要求失败，非环境问题。[主验收者结果](../evidence/A01/review-R2/primary-url-path/results.json)含实际parsed.path、原/新URL、预期、实际和内容摘要，同目录保存两个完整可搬运失败包。

恢复条件只限R2-02：从真正URL path核对两个书籍标识和source index，query/fragment不得提供或覆盖路径身份；也可明确拒绝超出当前格式的query/fragment，而须保持原合法直接JPEG地址及两书兼容。不要求新增主机认证、签名URL、网络信任或其他一般URL功能。本轮不自行修改实现或循环扩修。

## 引用的几何证据与未验证边界

geometry SHA256仍为 `3b707579cd586887da3b5125048b17c5baf548010fccf6cb21cc386baddaacf0`，模块、合同依赖字节及运行环境与R1相符。**本轮没有重跑R1的630项独立几何矩阵**，只引用已冻结[R1矩阵结果](../evidence/A01/review-R1/geometry/summary.json)及其数值表示限制；作者A01总套件中的几何单元检查随套件运行，但不记成新的630项成绩。

S01公共完整性/PRE_APPLY资格、D01根Pillow依赖和N15非认证precision标签按原边界保留，均未在本轮解决或扩展。来源包仍不提供全页/全书独立分母或coverage PASS；未进行全新安装、文件symlink权限分支、A04/CSS-DPR、平台、浏览器、OCR/识别配答、外部来源真实性或B确认。

## 证据与结束状态

确切命令、退出码、逐例输入/输出、摘要及限制见[运行摘要](../evidence/A01/review-R2/review-summary.json)和[统一SHA256清单](../evidence/A01/review-R2/sha256-manifest.json)。清单覆盖本报告、脚本、输入、日志及结果，清单自身明确排除，避免自引用。

子脚本证据目录绑定脚本位置，重放须先复制到review-R2下新的子目录，并使用新的普通临时stage，不能直接覆盖已冻结证据。原失败材料全部保留。

结束状态：**REWORK；未集成；未释放A04。** 剩余来源问题为上述一个有界URL解析缺口；verify入口保全格式限制单列，不自行扩成下一任务。由主调度决定停止、拆分或下一有限修复。本轮未改源码、合同、根依赖、A03、调度状态或旧原件；无平台/浏览器/凭据/网络/OCR/模型工具调用，费用0，无推送、合并或自行派发。
