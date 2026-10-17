# A01 集成修订 R1：独立静态与固定参照子审计

本子审计结论：**静态范围与固定字节来源符合本轮要求**。这不是整轮最终 ACCEPTED；实际导入、双形态常规回归及独立损坏对照由根验收者合并判断。本次只读本地 Git 和派单指定的原失败文件，仅写本目录，没有运行全功能回归或改实现。

- 最终交付：`5f872150a237b195f73c78e02e13a91d2f4f46a7`。
- 受验补丁：`f8f2981a815f96147144d3747d26752b564cc9f7`。
- A01 基线：`180bb1e86fb2a7eb1546be85af70f466f069daf5`。
- 固定主父：`4946b8ab307f88bdc25c14ace5ead774e3119fc5`。

可复现命令：

```powershell
python -B 'D:\1800\docs\evidence\A01\review-integration-R1\static\audit.py'
```

最终审计实际退出 **0**，1,073 条检查无失败；12 条底层只读 Git 命令均退出 0。完整 argv/cwd/退出码及输出摘要见 [commands.json](commands.json)，实际顶层 stdout/stderr/退出码见 [launch.json](launch.json)。此前同一静态脚本运行一次亦退出 0；最终运行仅补保存已审读的旧 preservation helper，未进行功能重放。所有原件经 `git cat-file --batch` 按 OID 取字节，未把 PowerShell 文本、Git archive 或 checkout 表示冒充原 Git。

## 范围和旧材料

[scope.json](scope.json) 独立确认 51 条净改动均在白名单，唯一旧文件改动为 `tests/test_a01_rework_r3.py`。1,143 份其余旧文件的模式、类型、OID 均不变，包含全部 11 份生产源码、原 R3 入口及夹具、旧报告/证据、根属性及依赖。补丁至最终交付的 36 条变化仅为新报告/证据；最终测试与脚本和受验补丁一致。

[references.json](references.json) 逐项将原 971 条保全和 62 条代码参照重新绑定其声明 Git 提交、路径、blob OID、原 SHA256/长度，及仅列明的精确 CRLF 字节。971 条的 25 个候选和 62 条的 3 个候选均保留；新交付没有扩大任何列表。原清单字节本身与基线相同。没有从当前磁盘重建期望。

[fixed-originals.json](fixed-originals.json) 独立解码并逐份核对 4 份固定输入：旧 `docs/coordination.md`、仅允许原字节的 `examples/a01/build.py`、有原 LF/CRLF 候选的 `tests/test_contracts.py`、PGM 资源。每份编码内容均严格等于原 `c3aff9598b6705ab4122062615a13ae3774698b2` 中对应 Git blob；去除 base64 字段后整个条目严格等于原 971 清单对应项。解码原字节保存于 [decoded-Git-originals](decoded-Git-originals/)。

## 清单双表示

[author-manifest-representation.json](author-manifest-representation.json) 独立得到作者新清单对 Git 原字节 **49/50** 匹配。唯一不等是新 `tests/fixtures/a01/integration-R1/reference.json`：

| 表示 | 长度 | SHA256 |
|---|---:|---|
| Git LF 原字节 | 86374 | `51e2fd08803cfc918f62a23327da99993bf2a91363ef2ec3960f37765ee241db` |
| 其严格 64 个 LF→CRLF | 86438 | `9b979d4b18ffe4db50ad5473c218ba28fdcbed0515d68ce324894be09cc2d0eb` |

第二行由本次读取的 Git 原字节独立计算，严格匹配交接及原清单，解析 JSON 内容相同。本子审计没有把计算所得 CRLF 写回原件，也没有声称这是对执行工作树磁盘的再次观察，更没有把该新夹具表示加入旧 971 清单。

## 测试适用边界与取证限制

AST 比较确认唯一旧方法修改是目标 preservation 测试；其余方法内容及所有旧 skip 行相同。调整保留原固定清单 SHA、原提交、971 条唯一性、25 候选及历史资源单表示政策；实际字节审计使用 4 个固定样本。新增 3 个测试仍覆盖原件/CRLF、混合换行、正文损坏、未列明表示、旧文档/二进制损坏；没有增加 skip 或异常吞错。新 verify 将子进程结果累积为 `all_ok` 并据此退出；`--focused` 明确限于负对照，不能当全套成绩。完整旧 R3 入口和清单没有改，其历史发行版身份没有被放宽到新集成树。详见 [static-code-review.json](static-code-review.json)。

作者 `source_files` 字段仅使用 `Path.read_bytes()` 读取所写路径与摘要，不是实际 `sys.modules` 或导入 `__file__` 证据；根验收者仍须独立取证。

有一个不影响本冻结输入正确性的元数据限制：新夹具顶层 `reference_commit` 的冻结值已经本次独立核对正确；常规测试在 materialize 返回后没有再次断言此顶层标签，只在 audit 输出中回显它。条目的路径/OID/SHA/表示及 `source_manifest_sha256` 则实际参与断言。本子审计不宣称每个冗余顶层标签损坏都会触发失败，根验收者据本轮身份负例范围判定。

## 历史失败与会话

[retained-failures.json](retained-failures.json) 确认原派单及三份主调度失败回执当前 SHA 与作者接单时固定值相同；作者自己的首次集成重现退出 1 仍保存。编码损坏子入口退出 1、原包装错误退出 1、原包装和补正包装两份源码及摘要都保留；补正读取既有嵌套结果，未将其当成功回放。没有覆盖这些历史失败。

本子审计仅同步启动短生命周期 Python/Git 只读子进程；已全部返回，待释放子进程/会话 0。没有网络、平台、浏览器、凭据/profile、OCR 或模型调用，没有 Git 写操作、推送、实现修改、集成或释放 A04。
