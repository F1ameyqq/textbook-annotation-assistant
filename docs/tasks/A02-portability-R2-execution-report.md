# A02 portability-R2 执行报告

日期：2026-10-17（Asia/Shanghai）。状态：**REVIEW**，等待原独立验收对话复验；未集成、未推送、未释放 A01/A04 或后续阶段。原 A02 R1 功能接受与集成记录保持，不以本轮工具修复重新定义。

已修复 I1-GIT-01：raw 导出且 PATH 无 Git 时，身份探测返回 `checkout_commit=null` 和明确 unknown，不再抛出启动错误；需要外部 Git 的源码绑定仍实际非零失败。补丁不跳过测试、不吞入口失败、不借父仓库 HEAD，也不声明未知身份 verified。

## 固定版本与边界

| 项目 | 本轮值 |
|---|---|
| 精确 base | `38aca9dcc8d027409b95193e9cc142c2336b76d3` |
| 工作流 | `6b77c436742cf2826083b109d8ed86b85539cba6` |
| **确切补丁 / 被复现提交** | **`ad71284f3b6ffc8454ee1d1e30933c8e39d7c1d8`** |
| 最终冻结提交 | 包含本报告及本轮摘要清单的后续文档提交，完整 SHA 由最终交付消息明确绑定；实现、测试和复现器均保持上述补丁版本，避免报告摘要自引用 |
| 分支 / 实现与 Git cwd | `codex/a02-planner-mock` / `C:\Users\ASUS\.codex\worktrees\a02-planner-mock\1800` |
| 唯一既有文件修改 | `examples/a02/R1/identity.py` |
| 新增 | `tests/test_a02_portability_r2.py`、`examples/a02/portability-R2/`、`docs/evidence/A02/execution/portability-R2/`、本报告 |
| 公共版本 | `1.0.0-a-proposal` / `c01-exchange-1` / `c01-fixtures-1` / `a02-fixtures-1` 均未修改；R2 未新增公共合同 |

仅在指定工作树操作。未合并浮动主目录、A01 或 A03；未改任何 `src`、旧测试、旧输入/样例、旧报告/清单/日志、根依赖/属性或调度文件。没有触碰 A03 独占恢复接缝。先只读任务与失败证据，必要小型原件复制至 [输入溯源](../evidence/A02/execution/portability-R2/inputs/provenance.json)，任务字节已核对工作流提交的 Git blob；原失败和 A01 I04 等边界没有改写。

## 最小实现

[identity.py](../../examples/a02/R1/identity.py) 保留先查询 top-level、精确等于源码根后再查询 HEAD 的顺序：

- 首次启动 Git 抛出 `OSError`：返回 null / `unknown; Git could not be started`。
- 第二次启动失败或 Git 命令非零：返回 null / `unknown; Git HEAD lookup unavailable`。
- HEAD 为空：返回 null / `unknown; Git HEAD lookup was empty`，不伪造 verified。
- 有 Git 的真实 checkout 继续返回自身 HEAD；子目录/raw export 即使处于仓库内也保持 unknown。

`source_binding` 函数完全未改：外部身份仓库未知时原断言失败；后续 Git blob 命令失效或源码字节不等继续向外传播错误。没有把所有错误包装成成功绑定，也未放宽原字节比较。新增测试将真实子进程与模拟调用故障明确分开。

## 修复前失败与修复后对照

先在 base 的原始 Git blob 副本上复现，然后在冻结补丁上运行；没有改受验源文件来适配 PATH。两个 raw 源码根都无 `.git`，且实际位于本任务仓库的证据目录内，构成“嵌套于外层仓库”的实际对照。外部准备阶段显式使用 Git 导出原字节；子进程运行阶段 PATH 可独立禁用 Git，两者没有混淆。

正式修前证据：[before-frozen-runner/results.json](../evidence/A02/execution/portability-R2/before-frozen-runner/results.json)。修复开始前的一次同输入开发复现另外保存在 `before/`，未覆盖；正式修前使用与补丁相同的冻结复现器，再次导出原 base。

| 实际入口 | base 无 Git | R2 无 Git | 有 Git 对照 |
|---|---:|---:|---|
| 直接 `git_identity(raw_root)` | 退出 **1**，FileNotFoundError | 退出 **0**，null / unknown | base/R2 都退出 0，嵌套 raw 不取父 HEAD |
| 原有 R1 身份测试 | 退出 **1**，1 ERROR | 退出 **0**，1 通过 | base/R2 都退出 0 |
| 实际任务 checkout 身份 | 未重复测 | — | 退出 0，确切 HEAD=`ad71284f...`，top-level verified |
| 需要外部 Git 的 `source_binding` | 未重复测 | 退出 **1**，外部身份断言失败，无 result | 退出 0，实际原始源码摘要校验成功；raw checkout 身份仍 null |
| 完整受影响 A02 discovery | 本轮未重跑旧完整套件 | **62 项通过，0 错误/失败/跳过，退出 0** | **同 62 项通过，退出 0** |

有/无 Git 两形态为同一套验证，不相加为 124 项独立成绩。[修后实际命令](../evidence/A02/execution/portability-R2/after/results.json) 保留每次 argv、cwd、PATH、`git_executable` 或 null、退出码和原始 stdout/stderr。

无 Git PATH 固定为新建的空工具目录，Python 通过绝对路径启动；独立子进程实际 `shutil.which('git')=null`，不是只 mock subprocess。直接探针记录实际 identity 导入文件及 SHA256；[完整无 Git discovery stdout](../evidence/A02/execution/portability-R2/after/a02-discovery-noGit.stdout.txt) 还记录真实 annotation/test/identity 导入及摘要，[stderr](../evidence/A02/execution/portability-R2/after/a02-discovery-noGit.stderr.txt) 保留测试结果。

原有 R1 测试没有修改或跳过，无 Git 也实际执行；需要 Git 的 binding 探针让异常直接传播为进程退出 1，复现器只记录并核对这个明确拒绝，不把失败当成功绑定。[binding 原错误](../evidence/A02/execution/portability-R2/after/source-binding-noGit.stderr.txt)、[原始 stdout（没有 result）](../evidence/A02/execution/portability-R2/after/source-binding-noGit.stdout.txt)。

## 新增有限负例

[R2 测试](../../tests/test_a02_portability_r2.py) 共 10 项。实际 raw 独立子进程验证无 Git 身份返回 unknown，以及 binding 非零；其余有限模拟验证首次启动缺失/拒绝、top-level 已通过而第二次调用缺失、第二次非零/拒绝、空 HEAD、父 top-level 或失败结果不读 HEAD、正常双调用身份顺序、blob 命令失效传播、原字节不等拒绝。第二次调用故障是单独标注的模拟，不冒称真实卸载/移除 Git。

新增 10 项工作树定向回归退出 0；正式冻结补丁的两形态 discovery 都包括这 10 项和原有 52 项，完整记录在上述输出内。一次只读子代理审查未发现必须修问题，但没有运行测试，不作为独立验收；实际证据由本执行对话采集。

## 运行环境与复现命令

Windows / PowerShell；Python 3.9.13，既有 Pydantic 2.12.5，无安装、新依赖或全局环境修改。Python 绝对路径为 `C:\Users\ASUS\AppData\Local\Programs\Python\Python39\python.exe`。Git 仅用于明确的准备和有 Git 对照；所有操作本地离线。

任务工作树根目录实际执行（输出目录现已存在，重跑须改为新的目录）：

```powershell
python -B examples/a02/portability-R2/verify.py --repo "$PWD" `
  --commit 38aca9dcc8d027409b95193e9cc142c2336b76d3 --before `
  --output docs/evidence/A02/execution/portability-R2/before-frozen-runner
python -B examples/a02/portability-R2/verify.py --repo "$PWD" `
  --commit ad71284f3b6ffc8454ee1d1e30933c8e39d7c1d8 `
  --output docs/evidence/A02/execution/portability-R2/after
```

两顶层采集命令均退出 0，表示所有实际退出码符合逐项声明的期望，binding 的无 Git 子命令保持非零。所有原始子命令及输出都独立保存，未吞入口失败。

[复现器说明](../../examples/a02/portability-R2/README.md) 给出最短运行方式。正式源码来源为 [after/source-binding.json](../evidence/A02/execution/portability-R2/after/source-binding.json) 指定提交的 raw blob 和逐文件 SHA；导出目录的 checkout 身份明确 null。导出只包含本轮必要源码/测试/小型样例，没有复制历史归档。实际源码和原始资源字节在运行后再次核对，未用当前结果重建期望。

## 收尾与限制

[sha256-manifest.json](../evidence/A02/execution/portability-R2/sha256-manifest.json) 覆盖本报告、复现器引用、全部新证据/原始日志及代码身份；清单不自引用。最终交付消息补充确切冻结提交与报告 SHA256。旧样例、旧报告、旧清单、旧失败和既有根文件保留，唯一既有文件差异即上述身份探测函数。

首次收尾审计在读取含中文路径的 Git 全树文件名时用了系统默认 GBK 解码，抛出 UnicodeDecodeError；此前实际功能测试已经完成，该审计尚未写出收尾清单。错误按工具回执文本保留，改为显式 UTF-8 解码后只重跑收尾元数据核对，没有重新运行功能或改动原始材料。

本轮仅执行受影响 A02 回归，没有重跑未改 C01、登录、630 几何矩阵或 A01 完整组合入口；A01 固定集成对象的正式复验仍由主调度派发，不能据本补丁测试提前宣称其完整入口通过。旧 A02 R1 功能接受/本地集成不撤销，本轮依赖修复仍只交 REVIEW。

N1/N2、S01、I04 冗余来源标签、有限 LF/CRLF 表示政策、B 确认、内容 PENDING、提交 NOT_SUBMITTED 均未扩张。A03 公共恢复接缝、跨进程恢复和正式解暂停不属于本次。平台/浏览器/网络/凭据/profile/OCR/模型调用与费用均为 0，没有重放 A05 题 22。

全部自有执行子进程已返回，无浏览器或后台 helper；提交报告和必要证据后保持干净冻结工作树，等待独立验收，不自行重试下一轮、不推送或集成。
