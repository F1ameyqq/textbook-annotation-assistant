# A01 R3 有界复现入口

状态 REVIEW。源码实现 `a01-static-1-r3`；原C01合同、geometry、S01/D01/N15边界不变。`probe.py`使用两份精确冻结输入差分和三个字面变体，所有反例先通过公共资源校验；URL的非空或空query/fragment都明确拒绝，身份只来自完整实际path，不扩主机认证。

在正常受控Windows工作树或按Git原始blob导出的无`.git`副本根目录：

```powershell
python -B examples/a01/R3/verify.py '<不存在的新证据目录>'
```

入口不调用Git、不访问执行者原路径或D盘未入库材料。固定参照在 `tests/fixtures/a01/R3/`，由确切基线/实现Git blob提前生成并提交；运行时只计算实际文件摘要与固定列表比较，绝不重建期望值。

- `preservation-manifest.json`固定基线 `c3aff9598b6705ab4122062615a13ae3774698b2` 的971个不变文件。只有独立报告明确列出的25个Git text文件含固定CRLF候选，其候选由原Git字节转换计算，逐文件列明；混合换行、正文变化及其他文件的换行变化均拒绝。历史证据、书籍原件/交换包和二进制只接受原Git字节。
- `code-reference.json`绑定确切R3实现提交及新脚本/固定输入/样例。仅两个更新的source文件及新测试允许其明确列出的Git text表示；R3脚本强制LF，JSON/资源保持字节。每项分别记录Git blob OID、原始SHA256、允许表示及实际磁盘SHA256。
- 开始、结束各核对固定参照；即使两种表示分别允许，运行中改变磁盘表示仍失败。`--preservation-only`仅运行这套门禁，不能当作全功能结果。

全入口运行A01/C01、原16例、完整R2九例（四个正式输入由已提交差分重建）、R3五例以及四代两书直接/含空格路径搬运消费者。源模块位置、命令、cwd、退出码和完整保全结果写到新目录。TMP/TEMP/TMPDIR使用本任务普通临时目录，所有源数据只读。

`build_references.py`只供作者在指定Git工作树内根据明确提交生成不存在的新参照文件；验证入口不运行它。原R2 verify及其Windows磁盘基线/失败记录未修改。`exercise_exports.py`仅用于作者从确切Git树导出并生成两形态及内容破坏对照证据，不是无Git消费端依赖。

首次/修复前后及旧失败原因保留于 [R3执行报告](../../../docs/tasks/A01-rework-R3-report.md)。支持的是本任务固定受控checkout和精确Git blob导出，不对任意编辑器、任意换行配置或无签名参照替换作认证承诺。
