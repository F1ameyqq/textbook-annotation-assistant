# A01 有界 R3 执行交付

日期：2026-10-17（Asia/Shanghai）。状态：**REVIEW**。R2独立结论仍为REWORK；本轮只修URL实际path身份与跨导出表示的新复现入口，不自行接受、集成、推送或释放A04。

## 固定版本与工作边界

- 原工作树：`C:/Users/ASUS/.codex/worktrees/a01-source-geometry/1800`；分支：`codex/a01-source-geometry`。接单时干净HEAD=`c3aff9598b6705ab4122062615a13ae3774698b2`，即R3基线。原workflow=`39341c98d73c354d639f3beeb55429f55d0e9be5`；本轮只读派单摘要见 [baseline.json](../evidence/A01/execution/R3/baseline.json)，未合并浮动主分支。
- **实现提交：`31d715a5f2e6435af3a7e98a6c19b41b72d883bd`**，含URL修复、新入口、固定基线Git参照、测试和样例。
- **固定代码参照及导出提交：`aeb7ca306b3dba9d51740071f96592d8e677ec66`**，仅追加从上述实现Git blob生成的code-reference；代码未变。两种形态运行均绑定该提交中的文件，代码参照明确指向31d715a。
- 最终交付提交随后只归档本报告/新运行证据/统一摘要，完整SHA在最终交付消息中提供。
- 已核对R2独立报告SHA256=`6b8480431074529ae1c4579da9683b4779b5065c06111278e2f659e142d6eb77`；主调度复现及正式反例只读，未运行会覆盖它们的旧脚本。
- 来源实现=`a01-static-1-r3`，公共C01仍`1.0.0-a-proposal`，B未确认。geometry、contracts、根依赖、父入口、A02/A03/A04均未改；R2分区和观察索引逻辑只增加新来源版本兼容项，没有重构。
- Windows、CPython3.9.13、Pydantic2.12.5、已安装Pillow11.3.0；没有安装依赖或修改全局换行设置。

## R3-01：实际path身份

`url_index`现在只对 `urlsplit(url).path` 作完整直接JPEG路径匹配，书籍目录标识、文件名前缀和源索引来自该实际path。query/fragment包括空分隔符均明确报 `SOURCE_URL_COMPONENT`，不能提供或覆盖身份；不扩主机认证、签名URL或一般URL功能，合法直接HTTP(S)地址及两书保持兼容。

修复前：Q01/Q02精确冻结包及U23/U24/U25字面重封装变体5/5被错误接受。修复后：公共资源校验仍实际通过，5/5由来源语义定位拒绝。输入URL、实际parsed.path、内容身份、模块路径/源码SHA和预期/实际见 [before/results.json](../evidence/A01/execution/R3/before/results.json)、[after/results.json](../evidence/A01/execution/R3/after/results.json)。

新增回归包含query/fragment对调、两个path书籍标识分别错误、错误源索引、实际匹配路径缺失、组件内容与实际路径正反混合、正确直接路径及空组件策略。正式反例由已提交差分重建并核对每个文件摘要，不依赖D盘未入库目录。新测试入口见 [test_a01_rework_r3.py](../../tests/test_a01_rework_r3.py)。本轮自测不是独立接受结论。

## R3-02：固定Git参照与磁盘表示

旧R2 `verify.py`及原Windows磁盘基线/成功记录均不改。其在Git原字节导出末尾因25项LF/CRLF差异退出1的失败没有抹去：独立诊断保存在 [历史限制](../evidence/A01/execution/R3/R2-verify-historical-limit.json)，原失败stderr和完整结果逐字节复制为 [旧失败日志](../evidence/A01/execution/R3/old-R2-verify-failure.stderr.txt)、[旧失败结果](../evidence/A01/execution/R3/old-R2-verify-results.json)。这项历史退出1不被改写成通过。

新入口为 `examples/a01/R3/verify.py`，只读取已提交参照，不调用Git、不在检查时生成期望值，也不依赖执行者原路径或主目录未入库材料：

1. [preservation-manifest.json](../../tests/fixtures/a01/R3/preservation-manifest.json)从确切c3aff959 Git blob生成971项固定参照，每项记录Git blob OID、原始SHA256和有限允许表示。只对独立报告明确列出的25个Git text文件，事先从原Git字节计算统一CRLF候选；其余文件只接受原Git字节。运行时不归一化实际文件，不用当前文件重建期望。
2. [code-reference.json](../../tests/fixtures/a01/R3/code-reference.json)从确切31d715a Git blob绑定62项R3代码/固定输入/样例。只有两个更新的source文件及新测试有明确的Git text表示候选，R3脚本固定LF，JSON及资源保持字节。
3. 每项输出实际磁盘SHA、匹配表示与固定Git原件SHA。开始/结束分别核对同一固定参照，并严格检查运行中的实际磁盘摘要不变；即使LF/CRLF分别允许，中途转换也失败。
4. 历史证据、书籍原件/交换包及二进制没有隐式文本容差；混合换行、正文变化、未列明换行变化均失败。25项明确兼容列表含旧Git text研究输出route_c_dump.txt，保持其原磁盘字节且单列Git原件，不改写该文件。

无`.git`副本所需的R2正式四包和R3正式两包都使用已提交固定差分重建，全部文件与原冻结输入摘要一致；不把重建的任意新包冒充旧包原件。完整运行重新验证原16例、R2九例、R3五例及四代两书，不依赖旧原路径才能通过。

## 两形态与真实损坏对照

作者命令在原指定工作树执行：

```powershell
python -B examples/a01/R3/exercise_exports.py --commit aeb7ca306b3dba9d51740071f96592d8e677ec66 --out docs/evidence/A01/execution/R3/two-forms
```

该作者侧导出工具的Git操作全部显式在原工作树；运行时验证入口不使用它。1040个文件从明确Git blob逐项导出/核对到新普通临时目录，副本没有`.git`。源清单见 [export.json](../evidence/A01/execution/R3/two-forms/export.json)。原工作树与副本各完整运行一次新入口，真实命令/cwd/退出码/完整日志见 [两形态结果](../evidence/A01/execution/R3/two-forms/results.json)。

| 形态 | 新入口退出码 | 完整功能与保全结果 |
|---|---|---|
| 受控Windows工作树 | 0 | 21条子命令全部0；971项中946为Git原字节、25为固定CRLF表示；运行中磁盘变化0 |
| 精确Git原字节无Git导出 | 0 | 21条子命令全部0；971项全部匹配Git原字节；运行中磁盘变化0 |

两种形态分别实际运行：**A01 49项（48通过、1文件symlink权限跳过）；C01 70项通过；原16例16/16；R2九例9/9；R3五例5/5**。四代两书8包直接消费和完整复制到含空格目录后换cwd消费，合计16次消费者子命令全部0。两形态重复运行是指定复现要求，不相加为独立覆盖成绩；未重跑R1的630项独立矩阵。

完整命令/模块路径/实际磁盘摘要及保全记录分别见 [normal/results.json](../evidence/A01/execution/R3/two-forms/normal/results.json)、[raw/results.json](../evidence/A01/execution/R3/two-forms/raw/results.json)，对应code/preservation begin/end文件保留全部逐文件结果。

另外在新副本改动固定参照文件，实际调用同一个新入口，结果如下：

| 新副本变异 | 预期/实际退出码 | 结果 |
|---|---|---|
| 明确允许文件的固定CRLF表示 | 0 / 0（preservation-only） | 有限候选有效，单列为保全正对照，非完整功能成绩 |
| tests/test_contracts.py追加真实正文 | 1 / 1 | CONTENT_MISMATCH，入口在保全门拒绝 |
| 同一允许文件仅首行变CRLF形成混合表示 | 1 / 1 | CONTENT_MISMATCH，无泛化归一化 |
| 历史verification.json仅LF→CRLF | 1 / 1 | CONTENT_MISMATCH，历史字节仍严格 |
| 原JPG追加损坏内容 | 1 / 1 | CONTENT_MISMATCH，二进制仍严格 |

各变异的输入前后SHA、精确字段路径、命令与实际拒绝输出均在two-forms目录。损坏对照使用完整新入口，未通过改旧基线、删assert或当前文件重算期望制造成功。

## 最短复现与保全边界

在受控checkout或上述完整Git原字节导出根目录，已有依赖环境：

```powershell
python -B examples/a01/R3/verify.py '<不存在的新证据目录>'
```

`--preservation-only`仅检查固定参照门禁，不代表功能全通过。导出消费端不需Git；`build_references.py`是作者侧从明确Git提交生成不存在参照文件的工具，验证时不会调用。新旧样例均保持两书隔离，6/2原图、10/4来源关系、250/214元数据页、14/1参考记录，UNVERIFIED/UNKNOWN及coverage_eligible=false不变。

- 971项旧磁盘文件与接单时逐字节一致，旧R1/R2脚本、基线、报告和失败输出未改；固定Git参照另行记录，不混同磁盘表示。主目录6份只读材料摘要亦未变，见 [final-preservation.json](../evidence/A01/execution/R3/final-preservation.json)。
- geometry SHA256仍 `3b707579cd586887da3b5125048b17c5baf548010fccf6cb21cc386baddaacf0`。contracts、根依赖、A03/A04及调度状态未改。
- S01公共资格门禁、D01根Pillow依赖、N15非认证precision标签、B确认及文件symlink权限限制照旧。本轮不进行清洁安装、真实平台、OCR/识别配答、全页/全书独立分母或外部来源认证。
- 允许的是逐文件固定的受控表示，不能推广为任意编辑器/任意文本差异可忽略；完整替换无签名参照仍需外部确切Git版本核验，本入口不建立新的信任认证系统。
- 浏览器/profile/凭据/网络/平台/OCR/模型工具调用0，费用0；未打开浏览器会话，待释放会话0；未重放A05、未推送或集成。

统一SHA256清单包含本报告、新脚本/固定输入/样例、两形态输出及完整日志，清单自身排除。最终冻结提交、报告SHA256和干净状态随交付消息提供。交付仅 **REVIEW**，停止在本轮，后续由原独立验收及主调度决定。
