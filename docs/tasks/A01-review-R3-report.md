# A01 R3 独立复验报告

日期：2026-10-17（Asia/Shanghai）。结论：**ACCEPTED（本任务有界离线复验）**。

R3-01实际URL path身份和R3-02固定参照验证入口均通过本轮独立正反例及完整复现。在本次规定范围内没有剩余必修项。该结论绑定下面的确切交付；不代表主调度已接受/集成，不释放A04，也不表示公共自动放行资格、全书完整性、B确认或真实平台通过。

## 版本和复验边界

| 项目 | 确切值 |
|---|---|
| 最终交付 | `180bb1e86fb2a7eb1546be85af70f466f069daf5` |
| 实现提交 | `31d715a5f2e6435af3a7e98a6c19b41b72d883bd` |
| 两形态运行/代码参照提交 | `aeb7ca306b3dba9d51740071f96592d8e677ec66` |
| R3基线 | `c3aff9598b6705ab4122062615a13ae3774698b2` |
| 原workflow | `39341c98d73c354d639f3beeb55429f55d0e9be5` |
| 执行报告SHA256 | `e8218a0083029ffe3e14bf0dfa29db33e0f049e77241c89fced5a84ccabe9472` |
| 交付archive-manifest SHA256 | `1798832a3fe194b0b5e9751dd42b99ff5788b85a774eae6d88a4436aef928084` |
| 来源 / 合同 | `a01-static-1-r3` / `1.0.0-a-proposal`，A内部提案，B未确认 |
| 环境 | Windows；CPython3.9.13、Pydantic2.12.5、已安装Pillow11.3.0；未安装依赖或修改全局配置 |

依据[本轮交接](A01-review-R3-handoff.md)、[R3有界任务](A01-rework-R3.md)、[原独立标准](A01-independent-review.md)及[R2失败报告](A01-review-R2-report.md)。交接摘要已核对为 `b5bf336ced03fff3a3ca975cae8188691a2a4b6526fa3affd59d5399e02b0581`。

确切最终交付导出到 `D:/1800/.local/stages/A01-review-R3/180bb1e86fb2a7eb1546be85af70f466f069daf5/snapshot/`，1144个Git文件逐一校验blob；173个变更路径均在允许范围。见[导出记录](../evidence/A01/review-R3/bootstrap.json)。实际运行模块均位于已核对副本，固定`-B`/禁写字节码，不依赖其他editable安装。

普通临时根为 `C:/Users/ASUS/AppData/Local/Temp/A01-review-R3-180bb1e8-mfi1e3_v/`。来源输出、TMP/TEMP/TMPDIR均在任务独占子目录，不修改`.local`保护规则。执行者原工作树没有被本验收写入。

## 有界续跑及已有证据保全

上次复验因用量限制中断时，功能检查已完成，但未形成正式报告和统一清单。本次先对已有**527个文件**记录SHA256，再核对完成项；没有无理由重跑两形态、61项URL或损坏门禁。

[续跑清单](../evidence/A01/review-R3/resume-inventory.json)保存中断后原527份文件的字节身份；[只读收口审计](../evidence/A01/review-R3/resume-closeout-audit.json)5406项检查通过、退出0，核对其全部原字节、1402份旧准备/首轮/R1/R2验收材料、冻结源码、31份原输入、6份主目录只读输入及172项交付清单。5406是证据/完整性断言数，不是新的功能覆盖成绩。

历史URL、固定参照采集器的外层进程退出码未单独保存；本报告没有补造历史回执。它们的完成结果、脚本/模块摘要、逐项输入输出，以及所有实际verify子进程退出码仍在。两形态完整入口的顶层退出0已明确落盘。本次只读审计命令和退出0另行记录，未用审计替代功能运行。

## R3-01：实际path身份与组件策略

[独立URL结果](../evidence/A01/review-R3/source/results.json)共61项，**61项符合预期：15接受、46拒绝，0意外结果**。每例均先通过公共`load_bundle(..., verify_assets=True)`；来源拒绝保留具体code/location，未拿资源摘要失败冒充语义拒绝。[实际环境与命令](../evidence/A01/review-R3/source/environment.json)、[原始输出](../evidence/A01/review-R3/source/stdout.txt)及逐例`cases/`均保留。

- 原Q01/Q02冻结完整包按原字节复制重放；U23/U24/U25由原字节校验的R2包与已保存差分重建。重建及原Q/U现场前后摘要一致，完整可搬运重放包保存在`source/replay-inputs/`。
- 五个历史错误接受均变为`SOURCE_URL_COMPONENT`，定位历史响应`pages[0].image`。这是交付明确选择的严格策略：**存在字面`?`或`#`（包括空分隔符）即拒绝**，因此query/fragment不能提供或覆盖身份。
- 另外检验query/fragment对调、同时出现、空组件、缺失实际path、两个书籍标识分别/同时错误、源索引左右邻页/另一已取得页、第二份答案页及合法直接HTTP(S)地址。实际path直接错书/错页分别定位拒绝；正常两书与四代八个包接受。
- 两项旧书合法直接URL额外检查使用纯字符串helper，且已验证对应旧书包公共/A01加载；不将helper检查冒称新的平台采集。

实现只对`urlsplit(url).path`作完整格式匹配，query/fragment策略有明确文档和负例。没有增加主机认证、签名URL或一般URL支持；主机文本不是来源真实性证据。现有范围内未发现新的可搬运失败反例。

## R3-02：固定Git参照和真实损坏门禁

[独立Git参照审计](../evidence/A01/review-R3/preservation/reference-blob-audit.json)实际通过**1033/1033条目及6/6元检查**：971项旧文件参照逐一对应确切R3基线blob；62项代码参照对应实现提交，并确认与参照/最终交付相同。25个旧文本CRLF候选恰为R2已独立证明的清单，没有扩大；代码参照只对两个更新source文件及新测试允许其3个预定CRLF表示。

期望摘要由固定Git原件预先确定，运行时只计算实际磁盘摘要与固定候选比较，不归一化实际输入、不从当前文件生成期望。审计时使用Git绑定外部版本；**被验verify运行不调用Git**。完整替换无签名源码和参照的外部真实性不属于本任务认证承诺。

[8个真实门禁子进程](../evidence/A01/review-R3/preservation/corruption-cases.json)均符合预期，实际argv/cwd、输入前后摘要、stdout/stderr及退出码保存于`preservation/cases/`：

| 新副本对照 | 实际退出码 | 结果 |
|---|---:|---|
| 原Git字节 | 0 | 固定门禁通过 |
| 全25个允许文件的固定CRLF | 0 | 有限候选通过 |
| 允许旧文本追加真实正文 | 1 | preservation / CONTENT_MISMATCH |
| 允许旧文本形成混合换行 | 1 | preservation / CONTENT_MISMATCH |
| 未允许历史JSON改CRLF | 1 | preservation / CONTENT_MISMATCH |
| JPG中间字节翻转 | 1 | preservation / CONTENT_MISMATCH |
| 当前consistency代码正文改变 | 1 | implementation / CONTENT_MISMATCH |
| 不允许的R3脚本改CRLF | 1 | implementation / CONTENT_MISMATCH |

这些对照运行的是新入口`--preservation-only`，功能子命令数0；六个损坏输入在门禁即被拒绝，没有重复整套功能测试。[4个磁盘转换检查](../evidence/A01/review-R3/preservation/disk-transition-tests.json)独立调用确切helper：LF/CRLF各自允许，但运行中互换仍报告`DISK_CHANGED_DURING_RUN`，未变化则无变化。它们是helper层检查，不冒称在完整verify运行中注入并发修改。

## 两种形态完整入口的实际结果

[导出与逐文件表示记录](../evidence/A01/review-R3/two-forms/source-exports.json)将运行源码固定于`aeb7ca3`，其1040个文件均核对确切blob。参照提交到最终交付仅追加104个报告/证据文件，代码参照覆盖的实现不变。受控checkout是本地共享clone的detached版本，显式使用预定固定表示；不是任意Windows换行设置都受支持的结论。无Git副本没有`.git`，运行PATH中也没有Git。

| 形态 | 顶层退出码 | 保全971项表示 | 代码62项表示 | 子命令 |
|---|---:|---|---|---|
| 受控checkout | 0 | 946原Git + 25固定CRLF | 59原Git + 3固定CRLF | 21条全0 |
| 原始Git字节、无Git导出 | 0 | 971原Git | 62原Git | 21条全0 |

每种形态均实际完成：**A01 49项（48通过、1权限跳过），C01 70通过；原16例、R2九例、R3五例全部符合预期；legacy/R1/R2/R3四代两书共8包直接消费及完整复制至含空格目录后换cwd消费，16次消费者全0。** 两形态是规定的重复复现，不相加为独立覆盖成绩。开始/结束固定参照均通过，运行中磁盘变化0。

真实顶层argv/环境/耗时/退出码见[命令清单](../evidence/A01/review-R3/two-forms/commands.json)，完整子命令、模块实际路径、stdout/stderr和保全前后结果分别在[checkout结果](../evidence/A01/review-R3/two-forms/controlled-checkout/results.json)与[无Git结果](../evidence/A01/review-R3/two-forms/raw-Git-no-git/results.json)。本轮没有重跑或改写旧R2 verify；其退出1和换行诊断仍是原历史事实，新入口通过不抹去旧失败。

最短被验入口（在上述确切源码副本根目录；输出目录必须新建）：

```powershell
python -B examples/a01/R3/verify.py '<不存在的新证据目录>'
```

独立采集器`source/probe.py`和`preservation/run_preservation_review.py`的证据写入位置必须指向新子目录，不能直接重跑覆盖本次527份现场。重放命令参数见已保存环境/脚本及门禁逐例命令；本次续跑只新增收口材料。

## 原标准覆盖及保留限制

| 原标准 | 本次覆盖 |
|---|---|
| 1 固定版本/环境/范围 | 1144个最终blob、173路径、报告/清单摘要核对；实际导入副本记录 |
| 2 作者测试和消费者 | 两种形态均实际复现，全部指定子命令通过；跳过如实保留 |
| 3 两书原图/映射/数量 | 八个包完整资源加载/解码和来源一致性检查；31份原输入字节不变。原独立图像/去重清单引用已冻结R2证据，不将250/214元数据当取得数 |
| 4 原件/历史质量 | 971项固定旧文件门禁及31原输入核对；旧历史UNVERIFIED、越界和缺失来源限制保留 |
| 5 搬运、不同cwd及包内资源 | 八包在两形态实际搬运消费；无Git入口不依赖主目录未入库文件 |
| 6 来源正反例及旧产物保全 | 原16/R2九例回归及61个独立URL场景通过；旧Q/U及1402份旧验收材料不变 |
| 7 有限scope及完整性 | 仍是14/1条历史参考、REFERENCE_ONLY/UNKNOWN、coverage_eligible=false；S01公共资格缺口没有被本轮宣称解决 |
| 8/9 几何手算/边界 | geometry原字节未变；引用R1独立630项结果及其数值表示限制，**本轮未重跑630矩阵**。作者套件内几何单元测试实际随总套件运行 |
| 10 具名语义/支持域 | 保持`a01-geometry-1` A内部提案；本轮只按已声明直接URL/固定表示范围验收，不扩大跨侧合同 |

仍未解决/未验证：S01公共PRE_APPLY完整性资格门禁、D01根Pillow依赖、N15非认证precision标签；Windows文件symlink因WinError1314跳过，不能用目录联接通过代替；全新安装、A04/CSS-DPR、真实平台、OCR/识别配答、全页/全书独立分母、外部来源认证、B确认均不在本结论内。

## 归档和退出状态

[统一SHA256清单](../evidence/A01/review-R3/sha256-manifest.json)覆盖报告、脚本、固定/可搬运输入、输出及全部已保存日志，明确自身排除和实际Git忽略项；被Git忽略的日志仍在清单，不静默省略。续跑首个读取命令误用不存在的子报告文件名，已有结果文件并未缺失；该查找错误退出1单列于收口元数据，不作为被验实现失败。

[任务路径进程核查](../evidence/A01/review-R3/resume-process-check.json)没有匹配的遗留自有Python/Git/浏览器进程；本验收从未打开浏览器或profile，无待释放自有会话。核查只记录任务路径匹配结果，不读取他人命令内容，也不声称扫描证明其他任务状态。

正式独立结论为 **ACCEPTED（确切交付的A01有界离线来源/声明能力）**，主调度复现和集成决定仍待执行。未改实现、合同、根依赖、调度状态或其他任务，不自行集成、推送、释放A04或派发后续。平台、浏览器、网络、凭据/profile、OCR和模型工具调用0，费用0。所有旧失败证据与历史结论保留原字节。
