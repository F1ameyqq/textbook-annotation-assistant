# A01 集成修订 R1 执行交付

日期：2026-10-17（Asia/Shanghai）。状态：**REVIEW**。原R3有界离线独立验收与主调度复现通过仍是历史事实；本报告只交付一次有界集成测试修订的执行证据，不自行记INTEGRATED或释放A04。

## 版本与范围

- 原工作树：`C:/Users/ASUS/.codex/worktrees/a01-source-geometry/1800`；分支：`codex/a01-source-geometry`。接单时干净HEAD=`180bb1e86fb2a7eb1546be85af70f466f069daf5`。
- 固定主目录集成父版本：`4946b8ab307f88bdc25c14ace5ead774e3119fc5`。规则来自主目录只读 `docs/tasks/A01-integration-rework-R1.md`，其摘要及三个原失败回执摘要见 [baseline.json](../evidence/A01/execution/integration-R1/baseline.json)。没有合并浮动主分支或在D:/1800实施。
- **确切补丁提交：`f8f2981a815f96147144d3747d26752b564cc9f7`**，包含其父 `5c83af7827e31e86ae44edbcb1262e11f8bd407a`；相对180bb1e的最终净差异是指定旧测试、新固定输入、新测试/验证脚本和本任务证据。属性试作未保留：最终净差异无任何.gitattributes、实现、公共合同、依赖或其他任务修改。
- 本报告及其后的运行证据/统一清单单独归档。最终冻结提交完整SHA随交付消息给出；受验补丁及实际测试代码保持上述版本。
- 环境：Windows、CPython3.9.13、Pydantic2.12.5、已安装Pillow11.3.0；无安装和全局设置修改。

## 原失败独立复现与最小调整

在原工作树通过明确Git父版本构造临时合并对象，默认checkout到新的隔离工作树，复现旧 `test_a01_rework_r3.py`：8项中7通过、1失败。失败正是历史971文件审计错误应用于当前整个ROOT。2份调度文档来自固定主目录的合法变化，另18项是Git默认checkout的精确LF→CRLF表示；原始数据未规范化、参照未放宽。命令、退出1、全部诊断及分类见 [before/](../evidence/A01/execution/integration-R1/before/command.json)。主目录原49项集成失败回执只读保留，未被新结果覆盖。

唯一既有测试修改是 `PreservationR3Tests.test_fixed_baseline_has_only_explicit_twenty_five_variants` 的适用输入：

1. 保留且加强对原参照的政策检查：固定SHA256=`9ea7a71204c0417b16b232511010a781ad5a9c001287cc89c059b87a2b6ec795`、确切基线c3aff959、971条且唯一、25个明确候选、历史资源只能一种字节表示。
2. 实际字节审计改用 [reference.json](../../tests/fixtures/a01/integration-R1/reference.json) 中4份固定Git原件：历史调度文档、只有LF被允许的build.py、具有原明确LF/CRLF候选的contracts测试、PGM二进制。原件从旧参照绑定的Git blob提取、编码保存；测试在新临时目录解码并核对固定SHA及原参照条目，不从当前ROOT生成期望，也不修改checkout属性。
3. 新增3个回归保留严格负例：正文损坏、混合换行、未列明的冻结文件CRLF、固定历史文档/二进制损坏均拒绝。当前调度文档与新合入文本按当前版本运行，不要求它们保持历史发行版字节。

没有跳过旧失败、吞掉assert、修改原参照、给一般checkout追加候选或规范化输入。原R3 `verify.py`和固定清单全保留；它仍只检查自己的冻结发行版，不能用于声称改过测试的新集成树等于原发行版。

## 精确临时集成及两形态结果

实际集成对象的两个父版本为：

- 主父：`4946b8ab307f88bdc25c14ace5ead774e3119fc5`。
- 补丁父：`f8f2981a815f96147144d3747d26752b564cc9f7`，祖先包含原A01 `180bb1e86fb2a7eb1546be85af70f466f069daf5`。

合并树：`2078731114ad3a07368ca46a2f34c3544af64e2b`；本次临时Git对象：`3bda6c2307e93601a574c9979c35fd1b25da3f58`。只创建本地对象用于副本验证，没有更新主分支或产品集成状态。实际父版本、checkout命令、9937个文件的Git原件与磁盘摘要/表示见 [after/snapshots.json](../evidence/A01/execution/integration-R1/after/snapshots.json)。

| 副本形态 | 常规入口实际退出码 | 回归与消费 |
|---|---|---|
| 默认Git checkout | 0 | A01 52项：51通过、1文件symlink权限跳过；C01 70、A02 52、离线登录8项通过；固定URL5例通过；旧/R3两书直接及搬运消费6次通过 |
| 同一集成树的无Git原字节副本 | 0 | 相同套件及6次消费者全部通过，11条实际子命令均0 |

默认checkout的9937文件中9870匹配Git原字节，67为精确checkout CRLF表示；原字节副本9937项全部匹配Git blob。这些是文件表示记录，不作为新增历史参照候选。两副本运行前后实际磁盘摘要逐项相同，真实模块文件位置和摘要、argv、cwd、stdout/stderr与退出码完整保留于 [checkout/results.json](../evidence/A01/execution/integration-R1/after/checkout/results.json)、[raw/results.json](../evidence/A01/execution/integration-R1/after/raw/results.json)。

原权限跳过为WinError1314，目录联接逃逸仍实际通过；没有把它记成文件symlink已验证。两形态是本任务要求的复现，不相加为独立成绩；未重跑旧630项几何矩阵或重建无关来源证据全集。

## 损坏对照与原冻结门禁

所有变异只发生于新的临时副本，随后恢复其原字节；没有改原工作树或旧期望。

| 对照 | 实际退出码与边界 |
|---|---|
| 新集成副本源码插入显式RuntimeError | 新常规入口退出1，A01导入错误明确失败；这是负对照，非完整正常套件成绩 |
| 新集成副本固定输入的来源摘要身份破坏 | 新常规入口退出1，52项中该固定参照断言失败，非吞错/跳过 |
| 固定编码原件的真实内容追加，保留原期望SHA不动 | 新常规入口退出1，`fixed Git original digest mismatch`；元数据中的原期望摘要未改，临时输入已恢复 |
| 原180bb1e冻结发行版，原R3 verify `--preservation-only` | 退出0，971项原Git字节门禁保留；不声称是新集成树或全功能验收 |
| 同一原冻结副本的源码/JPG真实损坏 | 原R3门禁分别退出1，implementation/preservation的CONTENT_MISMATCH定位拒绝 |

命令及输入前后SHA见 [after/results.json](../evidence/A01/execution/integration-R1/after/results.json) 与 [payload-damage/results.json](../evidence/A01/execution/integration-R1/payload-damage/results.json)。附加payload取证包装脚本首次错误地在顶层stderr查找已封装的单测日志，因此包装自身退出1；被测子入口实际正确退出1且拒绝损坏。原包装/结果均保留，按已有嵌套results日志补正核对，没有重跑或覆盖功能结果，详见 [包装记录](../evidence/A01/execution/integration-R1/payload-wrapper-correction.json)。

## 复现命令

作者在原A01工作树运行（输出必须新建）：

```powershell
python -B examples/a01/integration-R1/exercise.py --patch f8f2981a815f96147144d3747d26752b564cc9f7 --out '<新证据目录>'
```

脚本使用固定主父版本与指定补丁生成临时合并、默认checkout及原字节副本；Git命令均从原任务工作树显式调用。临时合并commit包含创建时间，其树与上述固定父版本可复现。正常checkout测试完后已正常移除临时工作树，清理回执见after/results。

在上述完整集成副本根目录（包含固定主父版本的A02及离线登录测试）：

```powershell
python -B examples/a01/integration-R1/verify.py '<新证据目录>'
```

该入口无Git依赖，适用于常规持续集成；`--focused`仅用于A01负对照。只拥有原A01分支时缺A02，不宣称全入口可运行。验证原发行版时，应另导出180bb1e后使用其未改的R3 verify；新提交不能复用旧code-reference声称身份不变。

## 保全、限制与停止状态

- 原任务工作树1143份旧文件磁盘摘要不变，唯一既有变化为受审旧测试；四份原派单/失败回执摘要未变。来源、geometry、contracts、根依赖、属性、调度、A02/A03/A04代码、旧报告/证据/固定清单均保持原样，见 [preservation.json](../evidence/A01/execution/integration-R1/preservation.json)。
- 最终净差异仅白名单路径，未留下属性修改或新换行容差。新夹具编码原字节以避免依赖磁盘换行，不把解码视作重新生成期望。
- D01仍由主调度另管；S01、N15、B确认及平台/OCR/独立覆盖限制不变。没有清洁依赖安装、线上写入或最终提交验收。
- 浏览器/profile/凭据/平台/网络/OCR/付费模型调用0，费用0，无待释放会话；无推送、主目录合并或自行集成。临时本地合并对象不代表INTEGRATED。

统一SHA256清单含报告、修订脚本/固定输入、命令/日志/原失败和新结果，自身排除。最终提交、报告摘要与干净工作树状态在交付消息给出。交付仅 **REVIEW**，到此停止，等待原独立验收与主调度收口。
