# A01 有界 R2 执行交付报告

日期：2026-10-17（Asia/Shanghai）。状态：**REVIEW**。R1独立复验整体为REWORK；本轮仅修指定的三类静态来源内部一致性缺口，等待独立复验，不自行接受、集成或释放A04。

## 固定版本与范围

- 工作树：`C:/Users/ASUS/.codex/worktrees/a01-source-geometry/1800`；分支：`codex/a01-source-geometry`。接单时HEAD为 `03c1af41a134945c406a52a48e3d4f6f0da33eb2`，工作树干净。
- R2 base_commit：`03c1af41a134945c406a52a48e3d4f6f0da33eb2`。原 base/workflow：`39341c98d73c354d639f3beeb55429f55d0e9be5`。R2规则通过主目录任务单只读核对并记录摘要，见 [baseline.json](../evidence/A01/execution/R2/baseline.json)；未合并浮动主分支。
- **确切实现提交：`63ac5a184798326d629a43d1dfed25fa73a1a27e`**，含源码、回归、新样例及前后运行证据。随后仅追加本报告与统一摘要清单；最终含报告的冻结提交完整SHA在交付消息中给出，代码保持本实现提交。
- R1独立复验报告已核对SHA256：`394001a09bb61565816c2a06dc3e8f478e4cb3e295d221cc4563aad1a3bb36cf`。旧R1规则、原独立标准、四个正式输入结果、来源子报告、调度复现均只读，未运行会覆盖其输出的原脚本。
- 来源实现：`a01-static-1-r2`，兼容旧 `a01-static-1` / `a01-static-1-r1`；C01合同仍 `1.0.0-a-proposal`。来源版本仍为A内部提案，B未确认。
- **geometry保持原字节**，SHA256=`3b707579cd586887da3b5125048b17c5baf548010fccf6cb21cc386baddaacf0`。本轮不重做几何实现，也不把前轮630项独立检查计作本轮成绩。
- 环境：Windows、CPython3.9.13、Pydantic2.12.5、已安装Pillow11.3.0。未安装依赖、未改全局设置；实际导入路径/摘要及真实命令见 [regression/results.json](../evidence/A01/execution/R2/regression/results.json)。
- 仅改source/static、必要测试、A01说明和R2专属样例/证据/报告。旧R1测试仅将“当前生成器版本”的硬编码断言改为当前VERSION，原16个反例及期望未变。未改geometry、contracts、父入口、根依赖/配置、其他任务、B模块或主目录调度文件。

## 三项修复与实际对照

修复前在03c1af4模块上，4个正式冻结包及5个便携重封装反例全部被错误接受（0/9符合预期）；修复后9/9给出定位拒绝。便携5例包含正式四类和N14范围外未取得集合与已取得相交。所有包均先实际通过公共 `load_bundle(..., verify_assets=True)`，再检查A01加载边界，没有用资源摘要失败冒充语义拒绝。

完整输入/预期/实际、源代码路径/摘要、正式输入路径及便携变化文件见 [before/results.json](../evidence/A01/execution/R2/before/results.json)、[after/results.json](../evidence/A01/execution/R2/after/results.json)。这是执行者复放，非独立接受结论。

| 项目 | 修复与最终结果 |
|---|---|
| R2-01 范围分区 | 以实际资产/映射取得集A、selected集S、selected_missing集M、outside-unacquired集O，核对 `S=A∪M`、`A∩M=∅`、元数据全集=`S∪O`且`S∩O=∅`，并核对索引整数/唯一/上下界和公共expected/acquired数量。P01和N14均报SCOPE_PARTITION，定位到各自缺失/范围外字段 |
| R2-02 历史URL绑定 | 复用导入器的纯字符串URL索引规则；绝对HTTP(S)路径中的两个书籍标识须与响应file_id/本包书籍一致，URL源索引须与响应page_index及保留映射一致。查看器页通过归档身份查保留映射，不推导固定偏移。跨书例报BOOK_CONFLICT，同书错页例报MAPPING_CONFLICT，定位到历史响应的image字段 |
| R2-03 观察索引摘要 | 核对归档source身份、观察索引路径及其SHA256与同路径输入清单before/after摘要；不以当前改写内容重算来替换保留摘要。全零冲突例报OBSERVATION_SOURCE，定位 `provenance.observation.observation_index_source.sha256` |

范围语义没有缩成“所有缺页都拒绝”：两书分别验证合法的非零M（包含源索引0和元数据上界），以及S覆盖全部元数据索引、O为空、未取得部分完整保留于M的情形。构造包标SYNTHETIC，expected未取得标识只表示意图，不生成资产、尺寸、摘要或框；实际图像仍6/2，完整性UNKNOWN、coverage_eligible=false。

新增10项测试含重复、负值、上界外、float/bool/非列表索引、空集合含义、交叠/遗漏、公共数量矛盾、URL字段邻近冲突及合法主机文本、观察索引路径/摘要邻近矛盾。正常旧格式和R1两书均继续加载；详情见 [R2回归](../../tests/test_a01_rework_r2.py)。URL仅解析归档文本，原主机文本不改写，不作网络信任认证或实时观测推断。

## 真实命令、结果及复现

全部操作显式在上述固定工作树。实际执行如下：

| 实际命令/入口 | 退出码与结果 |
|---|---|
| `python -B examples/a01/R2/probe.py docs/evidence/A01/execution/R2/before --official-inputs D:/1800/docs/evidence/A01/review-R1/primary-source-confirmation` | 1；修复前9个拒绝要求全部失败，保留错误接受证据 |
| 同一入口输出到 `docs/evidence/A01/execution/R2/after` | 0；9项符合预期；四个正式输入只读重放，未复制运行原取证脚本 |
| `python -B -m unittest discover -s tests -p 'test_a01_rework_r2.py' -v` | 0；新增10项通过 |
| `python -B examples/a01/build.py examples/a01/R2/bundles` | 0；实际生成两书R2新包，不覆盖旧包 |
| `python -B examples/a01/R2/verify.py docs/evidence/A01/execution/R2/regression` | 0；15条真实子命令全部0，包含以下套件/原例/消费者 |

最终总回归：**A01 41项，40通过、1跳过；C01 70项全通过；原16例仍16/16符合预期。** 跳过项仍为Windows文件符号链接创建权限不足（WinError1314）；目录联接逃逸分支实际通过。旧/R1/R2三代两书共6个正常包直接消费成功；六包完整复制到含空格目录后，换cwd再次消费成功，合计12条消费者子命令均0。具体argv、cwd、Python解释器、导入位置、stdout/stderr、退出码逐条保留于regression记录。

最短复现（根目录、已有安装环境；输出必须为不存在的新目录）：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B -m unittest discover -s tests -p 'test_a01_*.py' -v
python -B -m unittest discover -s tests -p 'test_contracts*.py' -v
python -B examples/a01/R2/probe.py '<新的R2证据目录>'
python -B examples/a01/R2/verify.py '<另一个新的R2证据目录>'
```

可选 `--official-inputs` 使用上表正式冻结输入目录；没有该目录的消费端仍可重建并验证5个便携反例。`verify.py`将TMP/TEMP/TMPDIR限定到本任务普通临时目录，未使用受保护`.local`作为来源输出位置。

## 样例、保全与限制

新正常样例：[46006966](../../examples/a01/R2/bundles/46006966/exchange.json)、[46007447](../../examples/a01/R2/bundles/46007447/exchange.json)。仍分别6/2原图、10/4来源关系、250/214元数据页、14/1历史参考；没有独立全页/全书题目分母或覆盖PASS。图像完整解码和资源摘要通过，历史原件保持UNVERIFIED。

- 本轮基线中886个受保全旧Git文件及31份原输入摘要全不变，包含旧样例、首轮/R1报告及执行/失败证据；geometry摘要和Git差异核对均确认无改动。源码改动仅source/static；旧测试的版本断言调整单列为允许变化。
- 7份主目录只读派单/验收/调度输入摘要仍与接单时一致，见 [pre-freeze.json](../evidence/A01/execution/R2/pre-freeze.json)。本执行未写D:/1800，没有改动冻结正式输入。
- 新包29个文件的Git暂存字节与运行文件一致；局部属性保留摘要绑定原件，不改旧属性。全部改动路径在R2范围内，`git diff --cached --check`通过。
- **S01公共资格/PRE_APPLY门禁、D01根Pillow依赖声明继续由主调度处理，本轮未解决。** 不将本机已安装依赖当作清洁安装验证，不将来源一致性检查当公共完整性门禁。
- N15 precision标签仍不是认证门禁，本轮不扩成观测认证或网络信任系统；它不能证明实时PlatformSnapshot。无签名材料全部被一致替换时，本加载器也不能独立证明外部真实性。
- 未做全新安装、文件symlink分支、A04/CSS-DPR、平台、OCR/识别配答、全页/全书覆盖或B确认。未重放A05，未推送或集成。
- 浏览器/profile/凭据/网络/平台/OCR/模型工具均未使用，费用0；未打开浏览器会话，待释放会话0。

统一摘要清单随本报告归档，含确切实现提交、源文件/新样例/运行证据及本报告摘要。最终交付SHA、报告SHA256和干净状态在交付消息中给出。状态仅 **REVIEW**；若复验仍有残余，由主调度按新的最小证据决定停止、拆分或下一有限任务，本执行不自行循环扩修。
