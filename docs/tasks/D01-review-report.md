# D01 依赖与清洁安装独立验收

2026-10-17（Asia/Shanghai）。结论：**ACCEPTED（固定交付、CPython 3.9.13 / Windows 的有界离线安装验收）**。独立构建、非 editable 安装、安装字节关联、仓库外隔离导入、两书搬运消费及分层坏资源拒绝均完成。合同回归曾因验收采集器遗漏一个固定 helper 出现失败，补齐确切 Git 原件后仅复跑受影响的一个测试；原失败未覆盖。没有剩余产品必修项。

该结论不代表主调度已经复现或集成；主调度完成必要复现和集成后才能关闭 D01。准备材料、作者历史失败与其他任务的既有边界保留。

## 固定目标与差异

| 身份 | 确切值 |
|---|---|
| 正式 workflow | `2ef3bfda20476dff3bdd23912d5bf2d1e3eb5ce1` |
| 产品 base / tree | `c6bebdf43eb93f7a6ae21e96ec07ed155686777d` / `e6f8d89bceccd639d9d8cf4e5fd2766899dff59b` |
| 实现 / tree | `9a7b9d7e374ee7a3ee124c9ff20e0b4003e57464` / `06ffc28412a7aff9dc16ebb517686fc3046b7814` |
| 冻结交付 / tree | `48accd7d885fbc7ecdd8b438ada33a0eafd5bc55` / `ea3bd81d263642ea256a546aeebc0d73c64571bd` |
| 执行报告 SHA256 | `19c9553422b3d42daa693e22bfaf135272f5ab36837c8180bcaba7b2a1076c8b` |
| 执行清单 SHA256 | `58336c047aa881e16bafff47a90ee9050a1af068bbc4a4065c27e9fc1040b2ad` |
| 实际独立解释器 | `.local/d01-formal-48accd7d/cp39/Scripts/python.exe`；CPython 3.9.13，Windows AMD64 |

首先读取正式 workflow 的[交接原件](../evidence/D01/review/formal/inputs/workflow/docs/tasks/D01-review-handoff.md)、AGENTS、架构、合同、协调文件与 D01 标准。主调度给出的冻结/释放门已核对；作者外层退出 0、同步子进程账本和当时无残留记录只用于移交，不充当本次功能结果。全程未读取执行者浮动实现或借用其 venv。

[静态范围审计](../evidence/D01/review/formal/scope-audit.json)独立核对：实现提交相对 base 只改 `pyproject.toml`，内容严格等于默认依赖增加 `Pillow==11.3.0`；Python `>=3.9`、Pydantic 2.12.5、包名/版本及其余配置保留。冻结交付共189条差异，其余188条均在允许的 D01 辅助范围；12,059份其他 base 文件的模式、类型与 blob OID 保留。原执行清单188项逐项等于冻结 Git blob 的长度及 SHA256。

全部构建/样例/测试输入均由固定 Git 对象的原 stdout 字节流取得，并重算 blob OID；不通过浮动 checkout、文本重定向或换行归一化构造输入。详见[固定输入索引](../evidence/D01/review/formal/static-input-index.json)及原始 Git 回执。

## 新环境、制品及安装来源

在此前不存在的自有 `.local/d01-formal-48accd7d/` 创建新 venv，没有 system-site-packages。保存[pyvenv.cfg](../evidence/D01/review/formal/pyvenv.cfg)、解释器和 site/flags 实际输出。所有构建、安装和 pip 检查通过该环境的 `python -I -m pip` 完成；公开下载显式使用 `https://pypi.org/simple`，不修改全局 Python、pip 或网络设置。

从冻结交付导出14份产品 Python 源码与根配置，共15个原始 Git 输入。先向自有环境安装 pip 25.3、setuptools 80.9.0、wheel 0.45.1，再以 `--no-deps --no-build-isolation --no-index` 构建。实际 [wheel](../evidence/D01/review/formal/artifacts/annotation_contracts-0.1.0-py3-none-any.whl) 为53,422 bytes，SHA256：

```text
7cf800297c53b9e9295d8d19fecbb793659b2bdd886b9f9a7924678fc3c3aaf9
```

[源码→wheel绑定](../evidence/D01/review/formal/wheel-source-binding.json)逐项证明14份产品源码等于冻结 Git 字节；[实际安装报告](../evidence/D01/review/formal/install-report.json)关联本轮 wheel 的 file URL 与同一 archive SHA。[安装来源探针](../evidence/D01/review/formal/installed-provenance.json)又核对 direct_url、METADATA、RECORD及14份已安装源码：wheel字节、安装文件字节与RECORD摘要一致，未发现editable形式。不能仅凭版本或路径认证安装来源，本次已建立完整制品关联。

9份公开制品（pip、构建工具及运行依赖）均记录真实文件名、版本、下载来源、长度与SHA，并独立与各自PyPI发布JSON的文件摘要匹配；公开元数据原始字节也保存在证据中。见[公开依赖清单](../evidence/D01/review/formal/public-dependency-index.json)。安装依赖来自自有已下载wheel目录，未使用作者制品或宿主PIL。

`pip check` 实际退出0，原始stdout为 `No broken requirements found.`。已安装分发 `Requires-Dist` 精确包含 `Pillow==11.3.0` 和 `pydantic==2.12.5`。实际运行依赖为 Pillow 11.3.0、Pydantic 2.12.5、pydantic_core 2.41.5、annotated-types 0.7.0、typing_extensions 4.16.0、typing-inspection 0.4.2。版本pin不等于完整传递依赖锁定。

所有功能cwd均为新建的仓库外普通目录 `C:/Users/ASUS/AppData/Local/Temp/1800 D01 independent 4jfmhfpe/`。`-I` 探针及实际消费进程记录 contracts、source.static、geometry、PIL 和随后加载子模块的真实 `__file__`/SHA，全部归属自有venv的site-packages；没有产品源码sys.path注入、用户包或宿主PIL替代。

## 两书搬运消费与拒绝层级

[30份样例输入](../evidence/D01/review/formal/sample-index.json)包含冻结两书R3的29个文件和原公开consumer，均与产品base的对应blob一致。复制至仓库外另一含空格目录后换cwd执行，复制前后和运行后字节不变。观察器使用 `runpy.run_path` 执行原consumer，只调整其argv，没有向sys.path插入源码或consumer目录；原始和包装argv均保留。

| 书籍 | 实际资源 / 元数据页数 / 参考记录 | 结果 |
|---|---|---|
| 46006966 | 6 / 250 / 14 | 公共资源校验、来源加载和完整JPEG解码成功，退出0 |
| 46007447 | 2 / 214 / 1 | 公共资源校验、来源加载和完整JPEG解码成功，退出0 |

逐次输出、8个图像的真实尺寸/摘要与完整load结果、实际模块路径见[旧书消费](../evidence/D01/review/formal/consumer-46006966.json)和[新书消费](../evidence/D01/review/formal/consumer-46007447.json)。两包仍为 `REFERENCE_ONLY`、`coverage_eligible=false`、独立分母 `UNKNOWN`；250/214不代表已取得页数。[来源最小回归](../evidence/D01/review/formal/source-regression.json)另独立检查两书合法公共/来源消费和两次错误expected_book_id拒绝，均符合预期。

每书分别建立缺失、单字节损坏、截断JPEG三个新副本，共6个真实拒绝子进程，原始退出码均为1：

| 层级 | 两书实际结果 | 独立证据含义 |
|---|---|---|
| 缺失资源 | `RESOURCE_MISSING`，定位资产path | 原exchange不变，只删除副本中的一个资源 |
| 资源摘要损坏 | `RESOURCE_HASH`，定位资产sha256 | 原exchange不变，只翻转副本图像中一个字节 |
| 完整解码 | 公共资源校验通过，Pillow `verify()`通过，`load()`失败，A01返回`IMAGE_DECODE`并定位图像 | 截断后更新资产摘要/身份、provenance及相应资源摘要并重封SourceBundle；先通过公共层，随后明确在完整解码层拒绝 |

详细变更前后清单及可重放差分见[负例输入索引](../evidence/D01/review/formal/negative-input-index.json)、`negative-deltas/`及[旧书解码负例](../evidence/D01/review/formal/negative-46006966-decode.json)、[新书解码负例](../evidence/D01/review/formal/negative-46007447-decode.json)。负例未修改任何冻结原件；预期拒绝分类不改写消费者实际非零。

## 合同回归、采集器缺口与保留失败

第一次合同回归从无 `src/` 的固定副本实际运行70项。一个测试方法中的两条consumer子测试失败，原始异常均为 `ModuleNotFoundError: build_fixtures`；原因是本验收导出consumer时漏带其既有helper，不是产品或依赖声明缺陷。其余测试结果及全部traceback保存在[首次原始回执](../evidence/D01/review/formal/commands/28-contract-regression/stderr.bin)和[首次统计](../evidence/D01/review/formal/contract-regression.json)，外层真实退出1也保留。

补入 `examples/contracts/build_fixtures.py`，独立核对其base/冻结OID相同，再按原始Git字节复制；没有修改源码、断言、依赖或已保存结果。仅复跑原失败的一个测试方法，实际1项、0失败/错误/跳过、退出0，见[单项复跑](../evidence/D01/review/formal/resume01/one-test-result.json)及[更正记录](../evidence/D01/review/formal/resume01/reviewer-correction.json)。没有再次运行其余成功功能、重装环境或重跑全套70项。因此本报告不把首次运行改写成“70项一次全通过”。

固定测试主进程仅加入测试目录，annotation实际导入来自安装包。原测试部分子进程主动设置 `PYTHONPATH=<固定夹具副本>/src`；该src目录不存在，这些子进程也没有逐个加 `-I`，故单列为既有测试的子进程行为，不充当独立隔离安装证明。前述直接安装探针、实际两书消费和拒绝探针均使用 `-I`，补足安装验收边界。

当前`run_review.py`已补齐helper并要求显式不存在的stage/evidence参数；其原实际运行版本及probe/collector原字节保存在`collector-run01/`。更正后的全量重放入口只做语法核对，本次功能结论来自原运行及单项续跑的真实回执，不声称执行过最终重放脚本全量版本。

## 16项对应与证据收口

| 准备项 | 本轮结论 |
|---|---|
| G01、S01、S02 | 固定目标/释放门、唯一根产品差异、原Git输入与旧文件保全通过 |
| E01–E06 | 新CPython3.9 venv、非editable构建安装、制品/安装字节关联、公开来源SHA、pip check及仓库外隔离导入通过 |
| C01–C03 | 冻结样例搬运字节不变、安装代码消费/解码及有限两书边界通过 |
| N01、N02 | 缺失/损坏资源与完整解码层分别拒绝；6个真实非零保留 |
| R01 | 70项首次运行和受影响单项复跑如实分列；采集器缺口闭合，产品无剩余失败 |
| F01 | 清单、链接、范围、原件保全和同步退出完成；详见下述归档 |

[运行结果](../evidence/D01/review/formal/run-result.json)、[原28条同步子命令账本](../evidence/D01/review/formal/commands.json)及[续跑4条账本](../evidence/D01/review/formal/resume01/commands.json)分别保存实际argv/cwd/PID/时间、退出码及原始stdout/stderr。**原账本为28条，续跑4条，合计32条**；包括10条静态Git读取和22条Python环境/功能命令。原账本中的一个未预期回归失败已按上述方式闭合，6条预期拒绝保留为1。两个外层collector分别真实退出1与0，均同步返回。

[运行后保全](../evidence/D01/review/formal/post-run-preservation.json)核对准备目录26份文件及准备报告不变、15份构建输入不变、原68份回归输入及补充helper不变、30份原始/搬运样例各自不变。未覆盖准备的NOT_RUN记录。[进程观察](../evidence/D01/review/formal/process-observation.json)结合所有命令/collector回执和精确任务路径，观察时没有遗留自有进程；只证明该时点和该任务范围，不宣称全机无进程。

[静态收口](../evidence/D01/review/formal/closeout-audit.json)核对文档链接、最终矩阵、完整证据摘要和允许写入范围；[统一SHA256清单](../evidence/D01/review/formal/sha256-manifest.json)包含报告、固定原件索引、执行脚本及其历史快照、实际wheel、原始stdout/stderr、首次失败/续跑和忽略日志，只排除清单自身。不以文档审计替代功能结果。

独立工作树只新增本报告与`docs/evidence/D01/review/formal/`，准备原件保持。未改产品代码、根依赖、主调度state或其他旧证据，未提交/合并/推送，未联系执行者或B。平台、浏览器、profile/凭据及付费模型访问为0；网络仅用于必需公开Python依赖及其公开SHA来源。

## 复现与限制

本次实际命令、输入路径、退出码及原始输出以两份命令账本为准，环境与临时副本仍保留供主调度只读核验。不得原地重跑collector或覆盖本轮证据。若需要从零重放，使用新的、不存在的两个目录：

```powershell
& 'C:/Users/ASUS/AppData/Local/Programs/Python/Python39/python.exe' -I `
  'C:/Users/ASUS/.codex/worktrees/d01-review-preparation/1800/docs/evidence/D01/review/formal/run_review.py' `
  --stage 'C:/Users/ASUS/.codex/worktrees/d01-review-preparation/1800/.local/d01-replay-NEW' `
  --evidence 'C:/Users/ASUS/.codex/worktrees/d01-review-preparation/1800/docs/evidence/D01/review/formal/replays/NEW'
```

上述NEW路径必须不存在；重放会重新下载公开依赖并运行完整检查，本轮没有为重复成绩而执行它。外部公开源不可达时应记录阻塞，不能使用宿主包绕过。

接受范围仅为明确记录的CPython3.9.13 / Windows安装、既有合同/有限来源消费，不泛称所有Python>=3.9、部署全流程、全书完整性或质量通过。S01、B共同确认、A03恢复/平台、OCR/识别配答、独立全书分母和费用评测均未由本轮解决。**D01此固定交付独立ACCEPTED，交回主调度复现/集成；不自行释放其他任务。**
