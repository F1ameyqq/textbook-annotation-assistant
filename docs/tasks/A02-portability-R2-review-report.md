# A02 portability-R2 独立复验报告

日期：2026-10-17（Asia/Shanghai）。结论：**ACCEPTED**，仅接受本轮来源身份示例工具的无 Git 环境处理；既有 A02 R1 业务接受与集成事实保持原范围。

| 身份 | 确切值 |
|---|---|
| base | `38aca9dcc8d027409b95193e9cc142c2336b76d3` |
| 补丁 | `ad71284f3b6ffc8454ee1d1e30933c8e39d7c1d8` |
| 最终冻结交付 | **`a1e5be00909172429d792b6c41bdaf384258694e`** |
| 原派发 / 正式交接工作流 | `6b77c436742cf2826083b109d8ed86b85539cba6` / `3ed8dcba2f921c7a89b7f1d2ef9f6ace40aed583` |
| 冻结执行报告 SHA256 | `afb339fda44156cbb2ba1aaf4589b65e0746afedc3b2f3aa2a88403eae9b1a34` |
| 执行清单 SHA256 | `6a1c4fd174d4f2a44ae975da0995bfca0fae4b6c853406343ab98d9036b529e9` |

已先读取确切工作流的[正式交接原字节](../evidence/A02/review-portability-R2/frozen-handoff.md)、限定派发及原准备矩阵。主调度交付前检仅作为输入身份依据；以下功能结论来自本轮独立执行，不以作者返回值或准备阶段的 NOT_RUN 计为通过。

## 核心结果

同一固定旧基线在真实无 Git 子进程中，直接身份探测及原 I1-GIT-01 单例均实际退出 **1**；原单例 1 ERROR、无 skip。同一单例恢复有 Git PATH 后退出 0。候选 raw 副本无 `.git`，在真实无 Git PATH 下直接探测正常返回 **`checkout_commit=null` / unknown**，原单例实际执行并退出 0、无 skip。子进程内 `shutil.which('git')=null`，额外真实 OS 启动 `git --version` 得到 FileNotFoundError；不是只模拟 subprocess。

受影响 A02 discovery 在候选的有 Git、真实无 Git 两环境中均为 **62 项通过，零 failure / error / skip**：原 `test_a02` 44、`test_a02_r1` 8、新 portability 测试 10。两环境为同套对照，不相加为 124 项独立成绩。实际测试模块及原 identity 模块导入路径与摘要均指向冻结隔离副本；新测试创建的 identity 临时副本由未修改测试从固定源文件复制，原始模块/源字节关系已留证。[无 Git 结果](../evidence/A02/review-portability-R2/a02-discovery-real-noGit-test-result.json)、[有 Git 结果](../evidence/A02/review-portability-R2/a02-discovery-withGit-test-result.json)。

正常本地 Git fixture checkout 返回自身真实 HEAD `25fa65364d33c55d8127194ce9eb2bf1a0aeed2d`。这是专属测试仓库中包含候选原字节子集的 fixture commit，**不是交付提交身份**。同一仓库下的嵌套 raw 副本经真实 Git 对照确能发现该父 HEAD，但 helper 仍返回 unknown/null；无 Git 对照同样 unknown。[fixture 及父身份对照](../evidence/A02/review-portability-R2/fixture-checkout.json)。

第二次调用另做两类证据：独立 wrapper 先执行真实 `git rev-parse --show-toplevel` 并取得正确结果，再仅改变本子进程 PATH；随后的真实 HEAD OS 启动失败，helper 返回 unknown/null，未复用已有 HEAD。没有制造 subprocess 成功结果或卸载系统 Git。[真实调用轨迹](../evidence/A02/review-portability-R2/runtime-final/second-real-path-disappears/command.json)。另行标注 mock 的缺失、权限、非零、空 HEAD、首次非零五项有限负例均符合预期；这些 mock 不代替真实无 Git 证据。

`source_binding` 在真实无 Git、外部身份仓库无效、declared commit 无效、源码单字节损坏，以及真实通过仓库身份后 Git 在 blob 查询前消失时，均实际退出 **1**，没有成功 result。正常有 Git 外部仓库绑定则实际比对 10 个生产文件摘要成功，raw 根的 checkout 身份仍 null。[实际绑定成功](../evidence/A02/review-portability-R2/runtime-final/binding-positive/command.json)、[无 Git 拒绝](../evidence/A02/review-portability-R2/runtime-final/binding-noGit/command.json)、[身份通过后 Git 消失](../evidence/A02/review-portability-R2/runtime-final/binding-git-disappears/command.json)。源码损坏例明确定位 `src/annotation/__init__.py`。

## 14 项独立检查

| 项目 | 结果与观察 |
|---|---|
| P01 范围与版本 | 通过。唯一既有改动为 `examples/a02/R1/identity.py`；`source_binding` 函数字节未改；新路径均在白名单 |
| P02 raw 真实无 Git | 通过。OS 无法启动 Git，helper 明确 unknown/null，未冒出未处理启动错误 |
| P03 原失败单例对照 | 通过。旧版无 Git 退出 1，新版有/无 Git 均退出 0；实际运行、无 skip |
| P04 正常 Git checkout | 通过。返回本地 fixture 的真实 HEAD，不能以一律 unknown 替代 |
| P05 嵌套副本不借父 HEAD | 通过。独立父 Git 对照存在；helper 不采用父 HEAD |
| P06 嵌套副本真实无 Git | 通过。unknown/null；OS 无法启动事实另存 |
| P07 需要 Git 的绑定失败关闭 | 通过。真实无 Git 退出 1，无成功绑定 result |
| P08 有 Git 合法绑定 | 通过。10 个生产文件逐 blob 核验，导出 checkout 身份仍 null |
| P09 非法绑定/字节损坏 | 通过。单字节损坏、无效 commit、非仓库根均拒绝；身份后 Git 消失也非零 |
| P10 第二次真实启动缺失 | 通过。第一次真实成功后改变子进程 PATH，第二次真实启动失败，返回 unknown |
| P11 第二次调用有限模拟 | 通过，MOCK_ONLY 单列，不作为真实无 Git 证据 |
| P12 非零/空 HEAD 等有限路径 | 通过，MOCK_ONLY 单列；未伪造 verified |
| P13 受影响 A02 回归 | 通过。两环境各 62，原 52 + 新 10，零 failure/error/skip |
| P14 旧材料与证据闭包 | 通过。旧 Git 文件及旧验收/准备文件保全，新输入/原始日志/报告纳入统一清单 |

[矩阵与逐项证据索引](../evidence/A02/review-portability-R2/matrix-results.json)绑定全部 14 行。总计 **20 条实际子命令**，其中 **7 条预期非零**全部保留非零：旧版两个失败对照及五个非法绑定/失效场景。采集器最终退出 0 仅表示逐项实际退出码符合预期，不表示这七条命令成功绑定。

## 隔离、完整性与实际命令

只从执行者仓库读取确切 Git 对象，在授权 `.local/stages/A02-review-portability-R2/a1e5be00909172429d792b6c41bdaf384258694e/` 下导出 base 87、candidate 92 个必要文件，全部按 raw blob OID/SHA256 核验。未在执行者目录运行测试或生成器；外部身份绑定只对该仓库运行只读 Git 查询。正常 checkout 与嵌套副本另建，无 remote，不改主目录分支、索引或全局 Git/PATH 设置。

188 个改动路径完整落在白名单，补丁至最终仅报告/证据；**2,084 个既有 Git 文件**的 OID 保留，仅 identity 这一既有文件改变。执行清单逐项验证 **181 项报告/证据 + 6 项补丁源码引用 = 187 项**，与清单自身合计恰好覆盖全部 188 路径。[完整清单核对](../evidence/A02/review-portability-R2/delivery-manifest-complete.json)。测试后 179 个 base/candidate raw 文件、两份额外副本的各 92 文件再验相同；单独损坏例确实仅改一个字节。

原准备、首轮 REWORK、R1 接受及其清单涵盖的 **4,920 个唯一旧验收文件**运行前后 SHA256 不变。作者修前失败与收尾编码错误仍保留在确切交付对象中；另只归档必要小型原件，没有复制大型历史归档。[输入/原失败溯源](../evidence/A02/review-portability-R2/input-provenance.json)、[运行后身份和实际导入核对](../evidence/A02/review-portability-R2/integrity-and-imports.json)。

环境为 Windows / PowerShell、Python 3.9.13、Git 2.53.0.windows.1（只在明确有 Git/准备阶段可用）。解释器为 `C:/Users/ASUS/AppData/Local/Programs/Python/Python39/python.exe`；使用既有依赖，无安装。无 Git 子进程 PATH 只含专属空工具目录，Python 用绝对路径启动。每条记录保存 argv/cwd/PATH、Git 查找与 OS 启动结果、实际导入和源码摘要、stdout/stderr、退出码。只移除子进程内的 Git 发现覆盖变量，未输出其他环境值。

实际顶层命令（cwd `D:/1800`）：

```powershell
python -B docs/evidence/A02/review-portability-R2/bootstrap.py
python -B docs/evidence/A02/review-portability-R2/run_checks.py
python -B docs/evidence/A02/review-portability-R2/run_checks.py --resume
python -B docs/evidence/A02/review-portability-R2/run_checks.py --resume --finish
python -B docs/evidence/A02/review-portability-R2/consolidate.py
python -B docs/evidence/A02/review-portability-R2/archive_inputs.py
```

两次采集器错误分别为：首次旧版预期失败的 WinError 中文文本编码被按 UTF-8 解码；之后 62 项无 Git 测试已通过，但测试 stdout 的其他 JSON 没有 event 键，采集器索引错误。只修正本轮采集器的子进程编码及事件筛选，原始输出/初始脚本保留，没有代修被验代码。最终从已有 19 条收据核对无 Git 通过事实，只补运行尚未执行的有 Git discovery，没有重跑成功功能场景。[采集器事件与真实退出码](../evidence/A02/review-portability-R2/collector-incidents.json)、[20 条最终子命令收据](../evidence/A02/review-portability-R2/commands.json)。旧版错误对照为预期失败，不计为候选缺陷。

归档与最终文档核验另外只检查元数据/摘要，不重新运行功能。统一 [SHA256 清单](../evidence/A02/review-portability-R2/sha256-manifest.json)包含本报告、必要输入、原始 stdout/stderr（包括可能被 Git ignore 的日志）、脚本和收据；清单自身不自引用。全部自有同步子进程已返回，cat-file helper 已关闭并等待退出，没有启动后台 helper 或浏览器；这不是系统级进程普查。[自有进程释放记录](../evidence/A02/review-portability-R2/process-release.json)。

## 接受边界与交回

本轮未重跑 A01 完整集成入口、未改 C01/登录/630 几何矩阵，也未修改任何实现、合同、依赖、调度状态、旧证据或 A01 固定材料。零平台、网络、浏览器、凭据/profile、OCR和外部模型调用；未提交、推送、集成或释放依赖，未联系执行者或 B。

ACCEPTED 仅说明这份确切身份工具补丁满足有界要求。旧 A02 R1 业务接受不扩张；N1/N2、真实来源 S01、A01 integration-R1 原 REWORK、I04 标签限制和既有 LF/CRLF 双摘要保留，内容仍 PENDING、提交 NOT_SUBMITTED。A03 恢复、B 确认、真实平台、算法/内容质量不由本轮证明。

由主调度复现并决定局部集成本补丁，再交原 A01 验收对话以新固定集成父版本及冻结 A01 交付做双形态组合复验。本报告不释放 A01/A04/D01；验收者到此结束本轮，等待调度。
