# R2-01 范围分区独立复验

日期：2026-10-17（Asia/Shanghai）。子结论：**ACCEPTED**，仅覆盖R2-01范围分区与列明公共引用计数边界。没有发现本范围的真实漏拒绝或合法误拒绝；不代表整个A01、主调度集成、A04释放、全书完整性或B确认。

固定交付 `c3aff9598b6705ab4122062615a13ae3774698b2`，实现 `63ac5a184798326d629a43d1dfed25fa73a1a27e`。只读父验收者已按974 Git blob校验的隔离副本；没有使用浮动工作树。实际导入 importer、consistency、contracts.validation 都位于该snapshot/src，完整路径、摘要、Python/Pydantic环境见 [summary.json](summary.json)。`consistency.py` SHA256 为 `f3225583b2c0871c79e3cef2909870a869a7c0b6e30518be74596f883966aca3`。

## 方法及代码审查

不调用作者cases生成器。独立按照元数据宇宙U={0,…,count−1}建立预期：A为实际mapping来源索引；S=A∪M，A∩M为空；O=U−S。每组索引必须为列表、无重复、精确int（拒绝bool/float）、在U内。公共expected/acquired引用计数分别与S/A一致，expected减acquired的数量对应M。

新 `validate_scope_partition` 在 `src/annotation/source/static/consistency.py:28` 定义；`:34`检查元数据整数及公共一致性；`:38–44`逐列表检查类型、范围、重复；`:50–54`检查集合分区；`:55–60`检查取得数量与公共expected/acquired数量。因索引已在U内且集合无重复，O与S不相交且数量之和为count能够证明O是完整补集，不能用重叠抵消遗漏。公共合同另在 `contracts/validation.py:242–246`验证引用去重、acquired与实际资产集相等且为expected子集；本次分别证明两层边界，不让公共层失败冒充来源层拒绝。

所有改写测试包均在指定普通TEMP下从冻结包完整复制。同步所有 `provenance.json` 公共资源别名摘要，重新seal artifact，将测试producer及相应evidence明确标为SYNTHETIC。合法缺页仅添加expected占位ID `synthetic-missing-<book>-source-<index>`，没有捏造资产/尺寸/摘要，没有移除已有真实图。仍为UNKNOWN、REFERENCE_ONLY、coverage_eligible=false。包内原始图片、历史资料及其他未变资源逐字节保留。

## 结果

最终运行退出码 **0**，共 **86/86符合预期，0失败**。逐项实际输入、期望、公共结果、来源code/location、完整临时包路径和搬运结果见 [results.json](results.json)；原始文本日志见 [run.log](run.log)。

| 场景 | 数量 | 结果 |
|---|---:|---|
| 两书original/R1/R2正常旧、新格式包 | 6 | 公共与来源均接受 |
| 两书合法非零missing：索引0、上界249/213、同时两边界 | 6 | 保留A，仅增SYNTHETIC expected占位，二层接受 |
| 两书S=U、M=U−A、O=[] | 2 | 空outside合法，二层接受；仍未取得244/212张图 |
| 两书合法集合及expected引用顺序倒置 | 2 | 集合关系不依赖列表排序，二层接受 |
| 已取得同时missing/同时outside、A不在S、未选中missing、outside遗漏、selected未声明missing、missing与outside重叠 | 14 | 先公共校验通过，再来源 `SCOPE_PARTITION`定位拒绝 |
| S/M/O分别加入bool、float、负数、count、count+1，重复值或null | 42 | 先公共校验通过，再来源 `SCOPE_INDICES`定位拒绝 |
| 缺页无expected占位、额外expected无对应S、metadata float、acquired_unique_images float、mapping.source_index float | 10 | 先公共校验通过，再来源 `SCOPE_COUNT`/`SCOPE_INDICES`定位拒绝 |
| 公共acquired移除一个资产ID、公共acquired重复ID | 4 | 在公共合同层拒绝，单列控制；不计入来源66例 |

16合法场景均二层接受；66非法分区/计数场景全部先执行 `load_bundle(...,verify_assets=True)`成功，再获有非空location的 `StaticSourceError` 和预期code拒绝。4个公共引用控制在公共层拒绝。这些层级在每行结果中独立保存。

8个合法缺页场景（索引0、上界、两边界及empty outside，各两书）完整复制到 `portable destination with spaces`，切换到无关cwd后重新公共/来源加载，全部通过。没有借助原仓库图像或网络。

### 固定原失败的实际定位

- 旧书source7仍已取得时，`selected_missing_source_indices=[7]`：公共资源校验通过；来源 `SCOPE_PARTITION`，location=`provenance.selected_missing_source_indices`。
- 旧书source7加入outside：公共资源校验通过；来源 `SCOPE_PARTITION`，location=`provenance.outside_selected_scope_unacquired_indices`。
- 新书以已取得source13做同样相交反例，均在同一分区边界定位拒绝；不是固定旧书页号特判。
- 合法源索引0及上界作为未取得的selected intent保留，不要求把已取得原图删除后冒充缺页。它们与已有A互不相交，完整二层消费及搬运证明修复未简化为拒绝非零missing。

对应小输入在 `inputs/<book>.R2.<case>/`，每例保存完整provenance/exchange/limitations及整包逐文件摘要，可按脚本从固定包重建；完整可消费测试包保存在results中的普通TEMP路径。没有新实现失败，故本轮无额外必须返修的最小输入。

## 保全复核

[preservation-audit.json](preservation-audit.json)逐例验证：86个测试包的资产inventory与对应冻结基包完全相同；除有意修改的exchange/provenance外，全部包文件字节与基包相同，86/86通过，退出0。该结论只覆盖这些包文件，不冒充主调度对全部历史仓库输入的保全核对。

几何未修改、未运行、未把R1 630项记成R2新增通过。本子任务不承担R2-02 URL、R2-03观察摘要、完整作者回归、S01、D01、N15、文件symlink、平台或全书质量验收。

## 命令及审查过程

cwd=`D:\1800`，主命令：

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B 'D:\1800\docs\evidence\A01\review-R2\partition\run_partition_review.py' --snapshot 'D:\1800\.local\stages\A01-review-R2\c3aff9598b6705ab4122062615a13ae3774698b2\snapshot' --out 'D:\1800\docs\evidence\A01\review-R2\partition' --temp-root 'C:\Users\ASUS\AppData\Local\Temp\A01-review-R2-c3aff959-__n2y2in\partition'
```

保全审计命令：

```powershell
python -B 'D:\1800\docs\evidence\A01\review-R2\partition\audit_preservation.py' 'D:\1800\.local\stages\A01-review-R2\c3aff9598b6705ab4122062615a13ae3774698b2\snapshot' 'D:\1800\docs\evidence\A01\review-R2\partition'
```

主命令前两次构造预检退出1，均为验收脚本的测试包构造错误：第一次没有同步provenance在history中的另一份资源摘要，第二次将evidence标为SYNTHETIC却漏将引用它的producer同步标记。公共校验正确分别以RESOURCE_HASH、SYNTHETIC_EVIDENCE拒绝。两次summary/results/log及一个完整exchange示例保存在 `attempt-1-resource-hash-preflight/`、`attempt-2-synthetic-producer-preflight/`，临时包路径仍在其结果中；没有当成R2实现失败。修正脚本后最终86例满足真正的公共先通过要求，未改冻结实现或旧证据。详见 [reproduction.json](reproduction.json)。

所有命令固定 `-B`、`PYTHONDONTWRITEBYTECODE=1`、`sys.dont_write_bytecode=True`与本进程sys.path[0]；TMP/TEMP及来源输出都在授权普通临时root的partition子目录。没有凭据、profile、浏览器、网络、OCR、模型或平台动作；没有修改公共合同、实现、状态、旧证据，也未集成或释放A04。

最终证据摘要清单为 [sha256-manifest.json](sha256-manifest.json)，递归覆盖本目录报告、脚本、输入、输出、预检日志，自身明确排除以避免循环摘要。
