# A03 P2-R7 只读产品 codec 独立验收

结论：**ACCEPTED，范围仅为 R7 新增 `annotation.contracts.a03_bridge` 的 `STATIC_INSPECTION` / `A_INTERNAL_READONLY` 只读产品入口。** 未发现本轮范围内的产品功能缺陷。七个冻结样例经公开产品 API 各执行一次，全部在约定语义层得到预期结果；冻结 wheel 在仓库外导入并完成正包、target 负控各一次。

C01 的原始完整一轮并非全绿：70 项运行留下 2 个子测试失败、1 个错误，原因均在审阅隔离和日志适配。仅补齐受影响的两个原始方法，结果 2/2 通过。原失败、补充输入及定点补测均完整保留；不能将这些记录改写成“70 项首轮全部通过”。这一审阅过程偏差在下文单独说明。

本报告不登记 INTEGRATED，不释放 A03 持久化、UNKNOWN 恢复、原生 PRE 或 I01。旧 profile 仍是 `STATIC_UNIMPLEMENTED`、`implementation_authorized=false`；1.3 proposal、Schema、API 保持冻结原字节。跨侧合同未共同确认。

## 冻结身份与核对方式

2026-10-17，原独立验收对话。未委派、未联系执行者或 B，未修改执行工作树、冻结输入、调度 state，未提交或推送。仅新增本报告和 [R7 审阅证据目录](../evidence/A03/review/P2-R7-readonly-codec/)。

| 输入 | 确切提交或 SHA256 |
| --- | --- |
| 审阅 workflow | `5cb696378f8c53a7720a5b775b3188012bf5626b` |
| 审阅交接单 raw SHA256 | `4f8f16072268d38b9e2a1f5313f4e0d72b2f85a6214e6e5b3d35970b654eed89` |
| base | `81d3ec7e42e0a1a76ad744bf59536fc5f68adee4` |
| target | `8ad45dd07214ae406a3fab28d76a4b5abd6eef03` |
| 执行 workflow | `5a69df310517f0ca22708262c737db9a5676be32` |
| 执行任务 raw SHA256 | `fc32fe579d2131cb38a9682b6497060cc3469b604507a9dde9bb145919d7766c` |
| 执行报告 raw SHA256 | `24ae0a28230da26458d6dc6427587e932788d7b8d71e1eceded771001028b2ad` |
| 执行清单 raw SHA256 | `92361002a2fad609255a7954fabef9f0ffa45082962811ca41b27aaf43a5c8d3` |
| 固定七例及源规则 pins raw SHA256 | `4ba6e0a646f403f552d71c091b62d0a53623f5ea90728ffea7dd2bab8ec172b1` |
| 调度前检 raw SHA256 | `e6ef6a6b8334974e4075047c9ecfa8f96651962dbe3df0bea3df584804f23788` |
| 冻结 wheel raw SHA256 | `c22c1bcae684d36bf0d39c1fd4c357409e093648157e8132f7b305245b7d02c7` |

采用 `git ls-tree` 和二进制 `git cat-file --batch`，逐体核对 Git blob SHA1、长度及 SHA256，不经 checkout 换行转换。见 [交付字节索引](../evidence/A03/review/P2-R7-readonly-codec/delivery-byte-index.json)、[原输入索引](../evidence/A03/review/P2-R7-readonly-codec/raw-source-index.json) 和 [隔离导出索引](../evidence/A03/review/P2-R7-readonly-codec/input-index.json)。独立验收导入本次导出的源文件，未导入执行工作树浮动内容。

核对结果为 340 个改动路径：339 个新增、1 个已有 `pyproject.toml` 附加 package-data；28,410 个其余旧路径的 mode/type/blob 均未变。pyproject 只增加 `annotation.contracts.a03_bridge` 的 JSON/schema 数据打包声明，依赖、版本和旧入口未改。作者清单 339 条加清单自身全部吻合。170 项原输入和 1 项原 C01 兼容输入，共 171 项 raw Git pins 全部核对。

最初只导出必要的 442 个文件。C01 定点补充另导出 1 个 base/target 字节相同的 `build_fixtures.py`，由独立的 [补充输入索引](../evidence/A03/review/P2-R7-readonly-codec/compatibility-input-supplement.json) 记录；原 442 项索引未重写。它是审阅环境补充，不能混记为作者原输入第 172 项。历史 3,267 个审阅/报告文件按原字节摘要保全，最终再次核对。

## 独立代码与内置数据判断

逐一阅读新增七个 Python 模块及冻结 R2/R3/R5 规则，检查逻辑迁移，未以作者映射表或测试通过数代替代码判断。产品使用正常 import；产品源码没有执行 examples、AST/exec、旧 main/session/conversion/oracle、数据库或原生 ABI，也没有源码路径 fallback 或按样例 ID 返回答案。审阅脚本的 AST 读取仅用于不执行代码的静态核对。

| 规则来源 | 本次产品实现及判断 |
| --- | --- |
| R2 完整 Package | `_rules.StaticPackage.validate` 先验证完整 exchange，再建立 Artifact 注册表、索引和 refs，扫描真实消费者及独立全局图，检查混合 DAG、声明闭包、book/scope、Artifact canonical hash 和静态 PRE 尾部，最后返回完整包。没有缩成少数预期答案检查。 |
| R3 正式 EvidenceRecord 闭包 | `catalog/slots/consumer/scan` 按冻结 schema 的正式槽位区分引用与普通字段，EvidenceRecord ID 由注册表解析；每个真实消费者独立计算 found/declared 和 book/scope，正式未声明证据不能借其他消费者声明获得资格。 |
| R5 登记上下文 | `scan_prefix` 区分真实消费与全局图扫描；`registration_binding` 核对 Source/Snapshot 种类、book/scope 和 canonical target 元组。真实 Artifact/frame 形成实际消费者，全局扫描不制造 None-book 消费者。 |
| Resource 与缓存 | `ResourceReader` 缓存原始读取字节，并核对实际 raw SHA；各消费者仍分别解析、建立上下文与闭包。全局 Resource 也实际读取并校验 hash，缓存命中不替代消费者验证。 |
| Schema 与数据 | `_builtin` 从分发内资源读取九个确切 pins；`_schema` 只解释冻结有限方言，未知断言拒绝。profile、API、六个 schema 的八个历史数据文件与原 pins 逐字节相同。 |

新采用记录 `readonly-adoption.json` 的 raw SHA256 为 `41f50606ad8b2283acad08ae5d63e0c40681ec424c83c026fe654d3c3734880c`。它仅采用 `a03-static-readonly-v1`、`a03-r2-r3-r5-r6-static-closure` 的内部只读检查，明确保留原 profile 的未实施状态及无 CURRENT/native/write 权限。详见 [独立静态核对](../evidence/A03/review/P2-R7-readonly-codec/source-data-wheel-audit.json)。

## 七个冻结包的实际入口结果

直接调用 `open_static_context(asset_root=...)` 和 `validate_static_bundle(..., context=...)`。七例每例恰好一次，输入 bundle 和资源由原 pins 逐字节核对；未改包、未生成新候选。只读 trace 观察真实 `StaticPackage.validate` 实例，不替换产品判断或返回值。结果和原始输出见 [产品 API 结果](../evidence/A03/review/P2-R7-readonly-codec/product-api-results.json) 与 [实际运行记录](../evidence/A03/review/P2-R7-readonly-codec/runs/product-api-01/completion.json)。

| 冻结样例 | 实际结果及接受边界 |
| --- | --- |
| registration-positive | `STATIC_ACCEPTED`；依次完成 `MIXED_DAG`、`CONSUMER_DECLARATIONS_BOOK_SCOPE`、`ARTIFACT_HASH_AND_PRE_STATIC_TAIL`、`COMPLETE_STATIC_RETURN`。16 个真实消费者，无 None-book；完整 model_dump 与原包相等。 |
| source-binding-negative | `FRAME_REGISTRATION_BINDING`，路径 `r4-static/source-binding-negative/prefix.json`；真实登记的 scope 绑定失败。 |
| snapshot-binding-negative | `FRAME_REGISTRATION_BINDING`，路径 `r4-static/snapshot-binding-negative/prefix.json`；真实登记的 scope 绑定失败。 |
| target-tuple-negative | `FRAME_REGISTRATION_TARGET`，路径 `r4-static/target-tuple-negative/prefix.json/registration/target`；前置种类/book/scope 均通过，实际 `snapshot_target_id` 检查失败。 |
| r3-original-undeclared-evidence | `UNDECLARED_REFERENCE`，路径 `origin-a-SourceBundle`；到达混合 DAG 后的真实消费者声明闭包层。 |
| global-resource-hash-corruption | `RESOURCE_HASH`，路径 `r5-static/global-only-proof.txt`；全局读取阶段拒绝，此时尚无真实消费上下文，未由早期其他异常冒充。 |
| R6-single-mixed-control-head-correction | `MIXED_CYCLE`，路径 `A:760b541bec881e9d98abb75f38bc7e34a75d2ed047edbc8ac657091c70fdc320`；到达混合 DAG。修正后 prefix 的事件、prev、内部 H0/expected/accepted heads 已独立核对，未命中旧 head 干扰。 |

所有负控路径和到达阶段都核对，未把“任意拒绝”算作通过。正包独立重算 canonical SHA、检查返回 Resource 与实际字节一致，完整数据保留包含 UNKNOWN/登记历史在内的全部原字段；这里只证明静态历史保留，不执行 UNKNOWN 恢复流程。各冻结 Artifact 的 canonical hash、refs、普通资源及 prefix 内部 hash 亦已独立核对。唯一有意的资源 hash 不符仍为原全局 hash 负控。

源导入实际 `__file__`：

`D:/1800/docs/evidence/A03/review/P2-R7-readonly-codec/input/checkout/src/annotation/contracts/a03_bridge/__init__.py`

其 raw SHA256 为 `db432039b784c0b9e2311eb9510b966448b9265f14b2ad718de41b7053a36bba`。

## 有限 API、路径与快照检查

同一产品运行中记录 27 项有限断言，均符合预期：CURRENT/未知角色拒绝；其余九个选择字段的错误值分别被 exact pins 检查拒绝；非具体 selection/context 类型、缺失或 None asset_root、未知 exchange、NaN/±Inf 均拒绝。未知 schema 断言 `allOf` 得到 `SCHEMA_KEYWORDS`。这些是 R7 只读选择描述检查，没有运行字段重置专项或原 P2 变体矩阵。

返回对象由 frozen/slots 描述、canonical bytes、递归只读数据及独立 model_dump 副本组成。普通赋值不能改选择、资源或快照；修改原输入和 model_dump 副本后，已验证快照及 canonical hash 均不变。

普通临时文件验证相对 `../`、绝对路径分别得到 `RESOURCE_PATH`。本机真实 symlink 创建失败：Windows 1314、errno 22，保留为 `SKIPPED_PRIVILEGE_OR_HOST_LIMIT`，不声称该分支已执行。随后只创建一个普通临时目录 junction，核对其实际目标确在 asset_root 外，经公开 API 得到 `RESOURCE_ESCAPE`。自有 mklink 子进程 exit 0，目录已按实际目标核对后清理。未访问凭据、profile 或 .local。

## 冻结 wheel 的仓库外验证

读取确切冻结 wheel，未重建或安装。ZIP 名称、唯一性、路径边界、RECORD hash/长度均核对；七个 codec 源文件和九个内置数据文件共 16 个 wheel 项与 raw 源字节完全相同。

在仓库外普通临时目录仅解压该 wheel，清除 PYTHONPATH，复制两例确切输入及资源，再启动独立 Python 子进程。正包得到 `STATIC_ACCEPTED`，target 负控得到确切 `FRAME_REGISTRATION_TARGET` 与 `/registration/target` 路径；各一次。九项内置数据 pins 正确，实际 distribution 版本 0.1.0，未从原仓库 examples/docs/Git 回退。

真实 `__file__`：

`C:/Users/ASUS/AppData/Local/Temp/a03-r7-review-wheel-nbn5o4kn/unpacked/annotation/contracts/a03_bridge/__init__.py`

见 [仓库外实际结果](../evidence/A03/review/P2-R7-readonly-codec/wheel-outside-results.json)、[启动 pins](../evidence/A03/review/P2-R7-readonly-codec/wheel-launch.json)、[子进程记录](../evidence/A03/review/P2-R7-readonly-codec/nested/wheel-outside/child-01/completion.json) 及 [清理记录](../evidence/A03/review/P2-R7-readonly-codec/wheel-cleanup.json)。记录中的临时目录现已移除。

## C01 兼容性与审阅环境偏差

旧 C01 默认入口、产品、两个原 `test_contracts*.py` 和旧 fixtures 的 raw Git 字节未改。使用现有 Python 3.9 环境及已安装 Pydantic 2.12.5，未安装依赖。原始入口 `unittest.defaultTestLoader.discover(..., pattern='test_contracts*.py')` 完整运行一轮，共 70 项。

[原轮结果](../evidence/A03/review/P2-R7-readonly-codec/c01-compatibility-results.json) 保持 `status=REWORK`：2 个子测试失败、1 个错误，无 skip。两个失败同属 `test_copied_sample_cli_and_public_consumer_work_from_another_cwd`：审阅副本漏导出 `consume.py` 的未改动兄弟依赖 `build_fixtures.py`，报 `ModuleNotFoundError`。一个错误来自 `test_relative_symlink_may_not_escape_the_sample_root`：symlink 权限失败后 native mklink 已 exit 0，审阅记录器却按 UTF-8 解码 OEM 中文输出，出现 `UnicodeDecodeError`，尚未到达原路径断言。它们不能归因于 codec 产品语义。

保留全部失败源快照、原 stdout/stderr、八个原嵌套进程及退出后，仅补足 raw Git 字节相同的 `build_fixtures.py`（仅正常 import `summary`，未运行其生成器 main），为未显式指定编码的 cmd 日志解码采用 OEM；原始字节仍原样记录。随后只执行上述两个原方法，2/2 通过、无 skip，四个嵌套进程均 exit 0。见 [定点补测结果](../evidence/A03/review/P2-R7-readonly-codec/c01-affected-completion-results.json) 和 [原始补测输出](../evidence/A03/review/P2-R7-readonly-codec/runs/c01-affected-completion-01/stderr.log)。

没有重跑整轮 70 项或其他已通过的方法；受影响的 copied-sample 方法内部包含一个原轮已通过的 CLI 子调用，定点补测保留了原方法全部步骤，故该子调用随方法再次执行。没有改测试、codec、wheel、原样例或判定标准。兼容判断基于完整一轮其余通过项、两个受环境中断方法的定点补齐及旧产品 raw diff 一致性；这不等价于一个独立完整全绿轮。此项过程偏差据实冻结，不安排追加复跑。

## 作者过程与审阅侧失败分别保留

[作者过程独立核对](../evidence/A03/review/P2-R7-readonly-codec/author-evidence-audit.json) 对 13 个父进程和 10 个嵌套进程的登记、argv/cwd、限时、PID、退出、原日志摘要逐一核对。13 个登记脚本的原始 Git blob 摘要吻合。所有自有历史记录均表明已 wait/退出，无 timeout/alive；没有以系统进程扫描证明释放。

- 作者 `freeze-01` exit 1：预备脚本直接比较 raw Git 与 CRLF checkout 的 pyproject；原脚本快照与 `AssertionError: pyproject.toml` 保留。
- 作者 `prepare-01` exit 1：预备脚本 tuple/list 拼接 TypeError；原脚本快照及 stderr 保留。两者未由审阅者重跑。
- 作者 product 首轮 13 项中 12 通过、1 因 Windows 1314 跳过；单独 path-01 只用目录 junction 补证通过。后来的最终测试源码不覆盖原 skip 事实。
- 作者 wheel stderr 原本带 EOF 空白行；原 bytes、首次清单/释放快照和 seal-adjustment 保留。只对 raw stdout/stderr 加 `-whitespace` 属性；未裁剪日志、改产品或重跑 codec/wheel。
- 审阅侧 C01 隔离/编码失败如上，原轮和定点补测分开保留。另一次纯元数据审计 `author-evidence-audit-01` 错把 wheel CRLF 空白行限定为 LF，exit 1；改为识别 LF/CRLF 后 `author-evidence-audit-02` 通过。两个脚本快照及原日志均保留，未变更作者原日志或执行任何作者命令。

## 冻结交付与后续边界

自有运行使用同步有界记录器；子进程启动前打开原始 stdout/stderr，保存脚本快照、输入摘要、argv/cwd、限时、PID、timeout/alive 和 wait 后退出。轮次与全部失败均保留，详见 [审阅进程释放记录](../evidence/A03/review/P2-R7-readonly-codec/process-release.json)。该记录只涵盖本审阅启动的检查及嵌套进程，不作系统或 profile 无进程的推断。

[最终核对](../evidence/A03/review/P2-R7-readonly-codec/final-verification.json) 再验隔离输入和补充输入全部原字节、3,267 个历史保全文件、报告链接及必要运行记录；[完整 SHA256 清单](../evidence/A03/review/P2-R7-readonly-codec/sha256-manifest.json) 收录证据目录全部文件和本报告，仅排除清单自身。封存脚本在清单写出后再次逐文件核对摘要和目录集合，不再运行产品测试。目录中的脚本保留确切复现材料，不要求在本轮追加执行。

保留此前 R2/R3/R4/R5/R6 及 session/conversion 的既有限定结论和历史 REWORK 边界，不升级为原生或端到端接受。原 A03 P2 持久化与 UNKNOWN 恢复、R4 原生 PRE producer、INITIAL/POST_HOLD 生命周期、creation-input anchor、单动作 UNKNOWN→只读对账→迟到回执→新 POST/Batch 真链路仍未验收，I01 不释放。

字段重置专项：`NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。

本轮未运行旧 36 矩阵、旧 A03 main/session/conversion/oracle、DB/native/PRE ABI/planner，未进行网络、浏览器、平台、OCR、模型、付费 API 或线上写入。ACCEPTED 只指本报告固定 target 的 R7 内部只读产品 codec，由调度后续核对并登记；本报告不自行改变调度状态。
