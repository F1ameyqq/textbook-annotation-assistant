# D01 执行报告：Pillow 依赖与 CPython 3.9 清洁安装

2026-10-17（Asia/Shanghai）。状态：**REVIEW**。本报告是执行交付，不是独立验收或主调度集成结论。完整运行 `run03` 已结束；前两次采集器失败及所有原始输出保留。

## 接单与固定版本

| 项目 | 确切身份 |
|---|---|
| 任务及请求强度 | D01；派发明确指定 xhigh |
| 独立工作树 | `C:/Users/ASUS/.codex/worktrees/d01-clean-install/1800` |
| 分支 | `codex/d01-clean-install` |
| 正式 base | `c6bebdf43eb93f7a6ae21e96ec07ed155686777d` |
| workflow | `f15f7bc03fac8994ade1642fa7547cbd823c6d43` |
| 唯一产品实现提交 | `9a7b9d7e374ee7a3ee124c9ff20e0b4003e57464` |
| 实现 Git tree | `06ffc28412a7aff9dc16ebb517686fc3046b7814` |
| 冻结交付身份 | 本报告、脚本和 SHA 清单所在的最终提交；确切 commit 与清单 SHA 在交付回执中一并提供，避免报告自引用 |

初始核对工作树干净、分支及 HEAD 与派发一致，未在 `D:/1800` 主目录写产品代码。先从 workflow Git 对象读取 AGENTS、协调规则、D01 执行/独立验收/准备单、架构和合同及相关 A01/S01 链接；没有把任务单不在 base 中误判为缺失。固定任务原件见 [workflow 索引](../evidence/D01/execution/run03/workflow-index.json) 和[补充链接索引](../evidence/D01/execution/workflow-links-index.json)，接单回执见 [receipt.json](../evidence/D01/execution/run03/receipt.json)。A01 已集成事实按当前 workflow 核对，未沿用历史“等待 R3 接受”的状态。

唯一产品差异为根 `pyproject.toml` 默认 dependencies 增加 `Pillow==11.3.0`。保留 `pydantic==2.12.5`、Python `>=3.9`、包名、版本、发现规则及其他配置；没有修改源码、合同、算法或其他模块。辅助范围仅 `examples/d01/`、`docs/evidence/D01/execution/`、本报告。环境、构建源码及受控副本在本工作树被忽略的独占 `.local/d01/` 下；实际功能 cwd 是工作树之外的新普通临时目录。

## 清洁环境、构建与安装

正式完成证据只绑定 `run03`。解释器为 CPython **3.9.13，Windows AMD64**，由现有 `Python39/python.exe -I -m venv` 创建此前不存在的 `.local/d01/run03/clean cp39`。没有 `--system-site-packages`，配置为 `include-system-site-packages = false`，用户 site 未启用。环境记录见 [pyvenv.cfg](../evidence/D01/execution/run03/pyvenv.cfg) 和[新环境原始输出](../evidence/D01/execution/run03/commands/02-new-environment/stdout.txt)。不依赖宿主已安装 Pillow，也未改变现有环境或全局 Python、pip、网络配置。

从实现提交原始 Git blob 导出全部 `src/**` 和 `pyproject.toml`，共 **15** 个固定构建输入，逐项校验 Git blob OID、SHA256 和长度。[源码索引](../evidence/D01/execution/run03/source-index.json) 保存 commit/tree 和全部输入；构建过程没有读取浮动工作树源码。使用 `SOURCE_DATE_EPOCH=1792212649`、任务环境内的 setuptools **80.9.0** 与 wheel **0.45.1**，执行 `python -I -m pip --isolated ... wheel --no-deps --no-build-isolation --no-index`。

实际构建并保留的 [annotation_contracts-0.1.0-py3-none-any.whl](../evidence/D01/execution/run03/artifacts/annotation_contracts-0.1.0-py3-none-any.whl) 为 **53,422 bytes**，SHA256：

```text
7cf800297c53b9e9295d8d19fecbb793659b2bdd886b9f9a7924678fc3c3aaf9
```

[制品绑定](../evidence/D01/execution/run03/wheel-binding.json) 逐项核对 wheel 内 **14** 个产品 Python 文件与固定 Git 源码字节一致；最终静态收口再次核对 15 个固定源码文件未被构建修改。随后仅用新环境 `python -I -m pip --isolated ... install` 安装该 wheel，非 editable。实际安装回执见 [install-report.json](../evidence/D01/execution/run03/install-report.json)，[pip check 原始输出](../evidence/D01/execution/run03/commands/08-pip-check/stdout.txt) 为 `No broken requirements found.`。

所有公开索引显式指定 `https://pypi.org/simple`；没有输出含凭据的镜像来源。新 venv 自带 pip 首先下载并安装 pip **25.3**，该首次 bootstrap 没有强求旧 pip 的 `--report`；下载 wheel 的实际 SHA 又与 PyPI 公开发布元数据核对。此后构建工具和产品依赖均保存安装报告，公开来源、版本及制品 SHA 汇总于 [public-dependencies.json](../evidence/D01/execution/run03/public-dependencies.json)，含 pip、setuptools、wheel 和以下运行依赖：

| 安装分发 | 实际版本 |
|---|---|
| pillow | 11.3.0 |
| pydantic | 2.12.5 |
| pydantic_core | 2.41.5 |
| annotated-types | 0.7.0 |
| typing_extensions | 4.16.0 |
| typing-inspection | 0.4.2 |

允许正常缓存；本轮没有新增传递依赖锁定策略。构建工具安装报告单列于 [build-tools-install-report.json](../evidence/D01/execution/run03/build-tools-install-report.json)。

## 安装来源与仓库外消费

[实际安装探针](../evidence/D01/execution/run03/installed-provenance.json) 保存解释器、隔离 flags、sys.path、分发元数据、完整 METADATA/RECORD、direct_url.json 和模块 `__file__`/SHA。`Requires-Dist` 精确包含 `pydantic==2.12.5`、`Pillow==11.3.0`。direct_url 的 archive SHA 等于上述实际 wheel；14 个已安装产品 Python 文件也逐项等于 wheel。contracts、source.static、geometry、PIL 以及实际加载的 annotation/PIL 子模块均来自新 venv 的 `Lib/site-packages`，未借用源码、editable 或宿主包。

全部正式功能命令使用 `-I`，cwd 为 `C:/Users/ASUS/AppData/Local/Temp/1800 D01 outside cwd 57519f972e34443eb8768900c518873c`，物理位置在工作树及构建源码之外，见 [cwd 核对](../evidence/D01/execution/run03/outside-cwd.json)。原 argv/cwd/退出码、时间、同步子进程 PID、脱敏原始 stdout/stderr 保存在 [18 条命令总表](../evidence/D01/execution/run03/commands.json) 及其各自 commands 子目录。

两书冻结 R3 包和公开 `examples/a01/consume.py` 均从正式 base 提取，总计 **30** 份 Git 输入。先核对原始字节，再复制到独立的 `relocated packages with spaces` 目录，复制前后及运行后摘要不变，见[样例索引](../evidence/D01/execution/run03/sample-index.json) 和[运行后核对](../evidence/D01/execution/run03/post-run-input-integrity.json)。没有重建或改写冻结样例。

`probe.py consumer` 预先核对真实安装导入，以 `runpy.run_path` 执行未修改的公开 consumer，运行前后均记录实际模块路径；不是未经观察器的裸命令。没有插入源码或 consumer 目录，`-I` 忽略外部 PYTHONPATH 和用户包。consumer 实际执行公共资源校验和 A01 完整 JPEG 解码，两者产物相等：

| 冻结书籍 | 资源 | 元数据页数 | 参考记录 | 本轮结果 |
|---|---:|---:|---:|---|
| 46006966 | 6 | 250 | 14 | 公共资源及完整图像解码成功，退出 0 |
| 46007447 | 2 | 214 | 1 | 公共资源及完整图像解码成功，退出 0 |

逐次证据见 [旧书导入/消费](../evidence/D01/execution/run03/consumer-46006966.json)、[新书导入/消费](../evidence/D01/execution/run03/consumer-46007447.json) 和[消费汇总](../evidence/D01/execution/run03/consumption-summary.json)。两书仍为 **REFERENCE_ONLY**、`coverage_eligible=false`、独立分母 `UNKNOWN`；250/214 是元数据页数，不是本轮已取得页数或全书质量证明。

## 相关回归与坏资源

固定 base 的两份 C01 测试和所需夹具、公开示例被导出到没有 `src/` 的独立副本，输入见 [regression-input-index.json](../evidence/D01/execution/run03/regression-input-index.json)。用同一安装环境的 `python -I` 从仓库外 cwd 执行，**70 项通过，0 失败，0 错误，0 跳过**，见 [原始 unittest 终局](../evidence/D01/execution/run03/commands/14-contract-regression/stderr.txt) 和[真实导入/统计](../evidence/D01/execution/run03/contract-regression.json)。

回归启动器仅把固定测试目录加入 sys.path，不加入产品源码。部分原合同测试的子进程会设置 `PYTHONPATH=<夹具副本>/src`；该目录不存在，未放入任何产品代码。这些原子进程不是逐个另加 `-I` 的独立安装证明。前述直接隔离探针和两书消费均无此注入，独立补足安装来源证明；没有将这两类证据混称。

同一安装环境额外执行 2 条合法两书 URL、5 条 query/fragment 拒绝及 1 个直接坏 JPEG 解码拒绝，均符合预期，见 [source-regression.json](../evidence/D01/execution/run03/source-regression.json)。这属于有界来源最小回归，未重跑完整 A01/几何/集成矩阵。

另为每书创建缺失、损坏两个受控副本，只改变各自首个图像资源，原包保持不变：

| 书籍 | 受控故障 | 实际结果 |
|---|---|---|
| 46006966 | 删除生成副本中的单个资源 | `RESOURCE_MISSING`，`$.artifacts[0].payload.assets[0].path`，退出 1 |
| 46006966 | 替换生成副本中的单个资源字节 | `RESOURCE_HASH`，`$.artifacts[0].payload.assets[0].sha256`，退出 1 |
| 46007447 | 删除生成副本中的单个资源 | `RESOURCE_MISSING`，相同资产字段位置，退出 1 |
| 46007447 | 替换生成副本中的单个资源字节 | `RESOURCE_HASH`，相同摘要字段位置，退出 1 |

四次实际非零及原始 traceback 均保留，未改写成进程成功；采集器只按预期拒绝判断本检查成功。完整受控副本逐文件 SHA/缺失状态见 [negative-input-index.json](../evidence/D01/execution/negative-input-index.json)。资源坏副本在公共校验层拒绝；另外的直接 IMAGE_DECODE 反例单独证明解码层，未将两者混称。

## 保留的失败、结束证明与复现

[采集器更正记录](../evidence/D01/execution/collector-corrections.json) 保留三个不同问题：实现提交后 PowerShell 未引用 `^{tree}` 的只读查询退出 1；run01 在创建环境前被不存在相对路径的 guard 拒绝；run02 在旧书 consumer 已成功后，以默认 GBK 读取 UTF-8 说明失败。run02 的 cwd 还在工作树内，不用于满足仓库外 cwd 要求。两次旧运行未删除或覆盖，原脚本、安装/构建产物、回执及原始日志全部保留；没有产品源码问题被顺带修补。run03 使用新的独占环境和目录完整执行。

首次静态收口在报告链接检查中提前要求尚待自身生成的 closeout-audit.json 存在而退出 1；随后清单验证因清单未生成也退出 1。该复合 PowerShell 的最后一个 `git diff --check` 为 0，不能将外层 0 当作前两条成功。[失败记录和初稿](../evidence/D01/execution/closeout-first-attempt/observed-failure.json) 保留工具返回的错误与来源说明；修正只涉及两个生成链接的检查顺序，已存在的部分静态输出逐字节保留。修正后单独检查静态收口与清单验证，不重跑产品测试。

第二次静态尝试的保全 guard 因新序列化 LF 与首次 Windows `write_text` 的 CRLF 不同而退出 1，见[第二次记录](../evidence/D01/execution/closeout-second-attempt/observed-failure.json)。修正为按首次实际使用的精确平台换行序列化后再比较；没有改写已有索引、归一化归档文件或扩大原 A01 的字节候选集合。

[run03 外层回执](../evidence/D01/execution/collector-run03/command.json) 确认 runner PID 60156 同步退出 **0**，原始 stderr 为空；[子进程账本](../evidence/D01/execution/run03/process-ledger.json) 的 18 条功能命令全部 communicate/wait 返回，未启动后台子进程。工具外层会话 64272 也已返回退出 0。两次只读进程观察均未发现已知 PID 或精确任务运行路径残留；[最终观察](../evidence/D01/execution/process-observation-final.json) 为 **2026-10-17 12:59:54 +08:00**。这是该观察时点的有界结果，不声称全机或永久无进程。

复现入口、目录要求和最短命令见 [examples/d01/README.md](../../examples/d01/README.md)。`run.py` 只接受不存在的新目标，避免覆盖旧证据；源提交必须在本地对象库。最终[静态收口](../evidence/D01/execution/closeout-audit.json) 核对输入、脚本快照、原始日志摘要、链接和返回码；[完整 SHA 清单](../evidence/D01/execution/SHA256SUMS.json) 覆盖产品依赖、所有 D01 脚本、报告及执行证据，只排除清单自身。源文件、两书样例、回归夹具、公开下载制品和受控副本分别有完整嵌套索引，输入与输出均可追溯。用 `python -I examples/d01/verify.py` 只读核对交付闭包。

本轮只证明上述 CPython 3.9.13 / Windows 环境。没有泛称所有 Python>=3.9、全书来源或部署流程已验证；版本 pin 不等于全传递依赖锁定。S01、B 接口共同确认、平台/OCR/识别质量和模型费用评测均不在此接受范围。平台、浏览器、凭据读取、付费模型调用均为 0，未下载浏览器，未联系 B，未修改调度 state，未集成或推送。独立验收与主调度收口仍待后续，执行停在 **REVIEW**。
