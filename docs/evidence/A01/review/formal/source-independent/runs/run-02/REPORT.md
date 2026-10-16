# A01 来源独立反例子报告

被验提交：`a8d5e96d128e10d341de935d4856682e50df79d9`。实现提交：`c8b8c6e158547954c59017211507755f67eda0e8`。本报告只交付来源检查事实，由正式验收父代理决定 A01 总结论。

使用父代理已按 Git blob 校验的隔离副本 `D:/1800/.local/stages/A01-review/a8d5e96d128e10d341de935d4856682e50df79d9/snapshot-verified`；`sys.path[0]` 与 `PYTHONPATH` 都是该副本的 `src`，实际 importer/contracts `__file__`、源码摘要、Python/Pillow/Pydantic 版本见 [environment.json](environment.json)。全程离线；未调用浏览器、凭据、平台、OCR 或模型。未修改源码或原输入。

最终复现命令（stage 必须尚不存在，可更换最后目录名）：

```powershell
python -B D:/1800/docs/evidence/A01/review/formal/source-independent/probe.py --snapshot D:/1800/.local/stages/A01-review/a8d5e96d128e10d341de935d4856682e50df79d9/snapshot-verified --stage D:/1800/.local/stages/A01-review/source-probes/run-reproduce
```

最终有效运行是 `run-03`（以 `-B` 运行并保留 stdout/退出码）：退出码 0 表示取证脚本完成，**不是被验功能全通过**。28 项包括原样两书的 1 项合法加载、16 项按预期拒绝、10 项非预期接受和 1 项 SKIP。结果、每例输入变化、异常栈、摘要与保留情况见 [results.json](results.json) 及 `cases/<id>/`。793 份冻结副本文件、两份基准产物均前后摘要不变，见 [snapshot-and-baseline-integrity.json](snapshot-and-baseline-integrity.json)。全部输出和变异工作副本都位于本任务授权的证据/临时目录中。

## 已实际拒绝的独立反例

| ID | 输入/期望 | 实际证据 |
| --- | --- | --- |
| S01 三项 | 旧书清单的 SHA256 全零、width=1、height=1，分别应拒绝 | `IMAGE_HASH` / `IMAGE_DIMENSIONS`，新目标未创建、旧产物未改 |
| S02 | 删除已选择的 viewer8 原图 | `INPUT_MISSING`，新目标未创建 |
| S03 | 在 JPEG SOS 后截断像素流，重算原清单摘要 | C01 仍可读出头尺寸 1178×1673；Pillow 完整解码报 `IMAGE_DECODE: image file is truncated`，新目标未创建 |
| S04 | viewer8/source7 改成 source8 | `MAPPING_CONFLICT` |
| S05/S06 | 新书页响应写旧书 ID；加载旧书时 expected 指新书 | `BOOK_CONFLICT` |
| S07 | 重复导入到已存在基准输出 | `OUTPUT_EXISTS`，旧目录所有文件字节不变 |
| S08 三项 | `../escape.jpg`、`C:/Users/escape.jpg`、`assets/../../escape.jpg` | 公共 Resource/合同拒绝非便携路径 |
| S09 | 导入后删除已取得资产 | `RESOURCE_MISSING` |
| S10 | 重新摘要保护的 provenance viewer=999 | A01 `MAPPING_CONFLICT`，公共加载器本身不能看侧车语义 |
| S11 | 重新摘要保护的 `coverage_eligible=true` | A01 `DENOMINATOR_UNKNOWN` |
| S22 | 资源路径经 Windows 目录联接指向本任务临时外部哨兵目录 | 实际创建联接成功；公共加载器 `PATH_ESCAPE`，未触及任务外目标 |

S21 尝试真实 Windows 文件符号链接，得到 `WinError 1314`，因此 **SKIP**。没有提权或改系统设置；不能将 S22 的目录联接成功拒绝外推成文件符号链接分支已验证。

## 已复现的来源交叉校验缺口

以下并非 `import_book` 直接生成错误产物。首先用冻结实现导出正确基准包，再完整复制到临时目录，仅修改指定内部记录，通过公开 `seal_artifact` 更新资源摘要和 artifact 内容摘要；其余保留记录仍在包中。公共加载器和 A01 加载器均接受。当前 `load_static_bundle(path, expected_book_id)` 只固定书籍 ID，没有调用方提供的可信期望内容摘要；这里检验的是保留记录之间的矛盾，**不要求无外部信任锚的 unsigned bundle 自证整个来源真实**。

| ID | 最小内部变化与保留的矛盾 | 实际 | 对应被验代码 |
| --- | --- | --- | --- |
| S12 | `provenance.origins=[]`，仍声称六个原图、保留两份清单声明和资源 | 两加载器 ACCEPT；全部逐图来源关系可丢失 | importer.py:438 只遍历已有 origins，不要求覆盖资产或十条关系 |
| S13 | `origins[0].manifest_sha256=00…00`，对应 `original_manifests` 和 `input-integrity` 仍保留真实原清单摘要 | 两加载器 ACCEPT | importer.py:438-444 不核对 manifest_path/manifest_sha256 与清单记录 |
| S14 | 在一张图的 provenance/public mapping 同时声明 `printed_page=999`；历史资料未变、原规范明确所有印刷页未知 | 两加载器 ACCEPT | importer.py:416-418 固定的 assigned 表只包含 source/viewer；431-433 只比较两处同值，未验证印刷映射依据 |
| S15 | `limitations.missing_sources=[]`，旧书已知五条不可用来源的原声明和摘要未变 | 两加载器 ACCEPT | importer.py:408-409 只核对 eligible 和 denominator，未保留缺失来源约束 |
| S16 | `input-integrity.unchanged=false`，首条 `after_sha256=00…00` 与 before 不同 | 两加载器 ACCEPT | importer.py:401-405 只要求 integrity 资源存在且摘要正确，从未解析其声明 |
| S17 | 旧书 `history/*manual-annotations.json` 的 `bookId` 改成新书，更新资源摘要；`input-integrity` 中原旧书文件摘要仍未变，reason 仍宣称 byte-preserved old-book reference | 两加载器 ACCEPT | importer.py:395 公共校验只看各资源自身摘要；A01 未把 history 对回 input-integrity/来源身份 |
| S18 | 将历史资源的 `quality` 全部升为 `REVIEWED`；没有新增业务核准证据 | 两加载器 ACCEPT | importer.py:350 创建时 UNVERIFIED，但 load_static_bundle 不维持该 A01 限制；通用合同允许 REVIEWED |
| S19 | `scope_manifest_status=INDEPENDENT_COMPLETE`，同侧车仍 `independent_denominator_status=UNKNOWN`、`coverage_eligible=false` | 两加载器 ACCEPT；A01 示例消费者仍输出 false | importer.py:408-409 未核对 scope_manifest_status；不是消费者已经自动放行的证据 |
| S20 | `provenance.reference_records[0].reference_id=reference-unrelated`，公共 scope_manifest 的原 reference ID 和归档记录未变、条数未变 | 两加载器 ACCEPT | importer.py:449-450 只核对条数和 basis 含 REFERENCE_ONLY，不核对 reference 身份与来源位置 |

最小优先复现为 S13（一个声明摘要与包内保留的对应原清单摘要相矛盾）和 S16（强制完整性资源明确自报未保持不变但仍加载成功）。S17 将该问题延伸到实际历史文件字节及书籍身份；S18 是 A01 文档声明的“历史始终 UNVERIFIED”未在加载边界维持。S19 只作为较低风险的元数据自相矛盾，不能表述成 A01 消费者已输出 coverage PASS。

预期依据来自原任务条款 4/6/7：历史原件字节保留且不得升格业务真值，来源交叉核对及书籍隔离，未知映射不得补猜，缺失来源不能消失，历史范围不得升级为独立分母。作者测试覆盖“重封装后 viewer=999”和“coverage_eligible=true”，没有覆盖上述保留记录互相矛盾的路径。恢复条件是由 A01 执行者明确其加载边界并补足对应记录间的一致性校验/明确拒绝；这里没有改实现或公共合同。

## S01 公共合同机器门禁的已知缺口

S23 保留 **原 A01 新书 SourceBundle 完全不变**，`limitations.json` 仍明确 `coverage_eligible=false` 与 denominator `UNKNOWN`；只在复制包内追加显式 `SYNTHETIC` 的 EvidenceBundle、QuestionGraph 和 PRE_APPLY CheckReport。两个页面各用 1×1 的合成区域/线索，问题身份使用唯一历史 reference，五项检查人为构造为 PASS。公共 `load_bundle(..., verify_assets=True)` 接受 `PRE_APPLY decision=PASS`。

这是离线机器校验的最小风险演示，**没有真实质量结论、平台快照、ApplyPlan 或写入动作**。`SOURCE_ONLY` 的 A01 加载器仍只允许一个来源工件，示例消费者仍硬编码 false；风险发生在后续通过通用合同组合工件时。C01 `validation.py:387-398` 以 `scope_manifest` 相等和页面线索完备为 PASS 条件，`401-416` 未检查 A01 侧车的 denominator 限制。因此说明文字本身不能构成 PRE_APPLY 机器门禁。

作者已明确提出 S01 且未获准修改公共合同。此例应列为**已验证的后续集成/自动放行缺口**，不误记为作者隐瞒、已发布虚假报告或要求本验收者修合同。是否通过结构化合同演进、由主调度整合的强制门禁或限制消费范围解决，需主调度与合同负责人决定。

## 取证边界

首轮 run-01 中 S23 合成探针漏列 `producer.policy_versions`，公共合同以 `UNDECLARED_POLICY` 拒绝；这不是 S01 门禁通过。该轮输入/输出和脚本已原字节归档于 `runs/run-01/`。修正的只是验收合成输入，未改被验源码；run-02 已复现 S23 门禁缺口。run-03 对修正后的全部输入再跑一次，固定最终脚本摘要、清单生成规则和输出日志；结论与 run-02 一致。

本子任务不代替两书原图/历史原件独立核验、搬运消费者、几何手算和主调度的正式结论；这些由父代理负责。没有新环境安装证明，也未验证文件 symlink 分支。每个变异包具有新的内容摘要，不能宣称其仍是原冻结交付的同一内容身份。
