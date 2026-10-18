# A06 执行交付：REVIEW

2026-10-18（Asia/Shanghai）。作者交付第一个冻结实现候选；**未独立验收、未集成、未发送 B**。
冻结后的四个完整入口均符合任务预期。作者不把执行完成记为 ACCEPTED。

## 版本、范围与输入

| 对象 | 固定身份 |
|---|---|
| A 集成基线 | `a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8` |
| 调度任务工作流 | `83e69beb9fb261676c8d012127e5b73e1f770261` |
| 实现冻结（唯一候选） | `9076d35e81678cdba8ad8651e95a44265fdc345c` |
| 独立分支/目录 | `codex/a06-b-native-receiver`；`D:/1800-worktrees/a06` |
| B 包提交 | `0e5434f0ecf57152ec03f66bd7d0cf48b7c0700f` |
| 包说明代码基线 | `c3cc2df7a0be24c125c83681c0499c0d328d78f6` |
| ZIP SHA256 | `b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d` |
| ZIP 大小 | 11,681,712 bytes |
| manifest SHA256 | `3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f` |

原 ZIP 只读引用：`D:/1800/.local/stages/coordinator/b-handoff-0e5434f/B-46007447-Q16-offline-HOLD-2026-10-17.zip`。
run 为 `pipeline-run-0a2c03e193694ef88953f3ca08b8cde2`；包格式 `b-handoff-package-trial/0.1`。
原包 SHA 在验证结束后再次核对一致。未重建 B 流水线、未补取 Git 对象或借浮动 HEAD。

实现、消费者、配方、测试都只新增于任务白名单；产品冻结后仅追加说明、报告和证据。
公共 contracts/native/delivery/runtime/pins/根依赖均与 A 基线相同。未修改主目录 state 或索引，
所有 Git 调用均加 `-c core.longpaths=true` 并设置 `GIT_NO_LAZY_FETCH=1`。
范围核对见[scope-check.json](../evidence/A06/author/scope-check.json)。

## 可导入交付

公共入口为 `annotation.source.b_handoff`：`receive_package`、`HandoffError`、`version_policy`。
固定消费者为 [consume.py](../../examples/a06/consume.py)，完整参数/API/输出字段/版本矩阵及公共
C01 说明见 [README](../../examples/a06/README.md)。没有改父包入口或依赖文件。

`receive_package(package_path, expected_sha256=..., expected_manifest_sha256=...)` 必须显式固定 ZIP，
返回 `ReceivedHandoff(receipt, documents)`；documents 是未删字段的原生 JSON 值。
正常诊断是 HOLD/退出0；拒绝是可定位的错误码、路径、层/退出2。API 和 CLI 都拒绝未注册形状。
本入口不生成 C01 交换包或执行计划，不授予 PASS 或平台资格。

冻结验证使用 `git cat-file --batch` 原始字节导出152个必要文件至
`tests/fixtures/a06/generated/frozen-01/root`，没有 `.git`、旧 editable 路径或 B UI 依赖。
导出清单记录 Git blob OID、SHA256、长度，见 [frozen-export.json](../evidence/A06/author/frozen-export.json)。
从另一个 cwd `.../frozen-01/variants/foreign-cwd` 启动实际消费者。
CPython 3.9.13、Pillow 11.3.0、pydantic 2.12.5；未安装依赖。
实际 `__file__`/源码摘要/公开入口见 [imports.stdout.txt](../evidence/A06/author/frozen-01/imports.stdout.txt)。
这是固定源码消费证明，未声称新的 wheel 清洁安装验收。

## 冻结后的四个完整入口

每个样例一次，由 A 公共入口执行；没有调用 B helper 或替换业务函数。

| 样例 | 实测退出码/结果 | 定位 |
|---|---|---|
| 原 ZIP | 0 / HOLD；34题候选、66答案候选、127当前问题 | `business_acceptance=false`、`c01_execution_eligible=false` |
| 坏资源 TEST_VARIANT | 2 / RESOURCE_INVALID，RESOURCE 层 | `supporting-fixtures/q4-stem.jpg` |
| 陈旧 Check TEST_VARIANT | 2 / STALE_CHECK，CURRENT_BINDING 层 | `artifacts/check.json#/payload/graph_ref` |
| 未知版本 TEST_VARIANT | 2 / UNSUPPORTED_VERSION，VERSION 层 | `artifacts/graph.json#/schema_version`，`b-graph-trial/9.9` |

原始 argv/cwd/环境覆盖/退出码/开始结束时间、stdout、stderr 均在
[frozen-01](../evidence/A06/author/frozen-01/summary.json) 同目录的 `*.process.json`、
`*.stdout.txt`、`*.stderr.txt`。四例 stderr 均为空。资源错误信息含 Pillow 生成的内存地址；
复现应对照稳定的 code/path/layer，不要求地址字符串一致。

三份 `*-recipe.json` 保留每个修改成员的前后 SHA/长度及变动字段。变体 ZIP SHA 分别为：

```text
bad-resource    b759b87bbe13646f23519a6f8a7ba49554ee3c5aa56f885431846eca2df2ccf1
stale-check     f7bb2786a9700169d8df31766c62ee8c94ada6fe3ea6efb7dc2dd5e76d9c0414
unknown-version 777287ec0bf0d4fed591e9a5b7af5c0bf3f1a994b8c32dfaabcaf89d2b3afd84
```

[make_variants.py](../../examples/a06/make_variants.py) 固定成员顺序/时间/压缩，在新目录生成。
它重算非破坏点的 payload 自摘要、内嵌对象、wrapper 引用及文件地址、下游依赖、report 和 manifest；
陈旧变体仅故意让当前 Check.graph_ref 指向真实历史 Graph，未知变体将当前 G 版本改为9.9。
三个样例分别到达目标层，没有把同一种外层 hash 错误计成三类拒绝。开发与冻结两次配方产物 SHA 相同。
大 ZIP 留在本地 ignored `tests/fixtures/a06/generated/`，不重复入库；原件从未改写。

复现命令（新目录名必须未存在；参见 README 的可移植参数形式）：

```powershell
$env:GIT_NO_LAZY_FETCH = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
python tests/fixtures/a06/generated/frozen-01/root/examples/a06/verify.py 'D:/1800/.local/stages/coordinator/b-handoff-0e5434f/B-46007447-Q16-offline-HOLD-2026-10-17.zip' docs/evidence/A06/author/independent-new-run tests/fixtures/a06/generated/independent-new-variants
```

该命令记录的是作者本机路径，独立验收必须从同一冻结提交重新导出自己的代码及目录，不追作者可变工作树。
直接导入和 `python -m annotation.source.b_handoff` 形式见 README；调用参数只用显式本地输入及包内相对路径。

## 实际消费关系与限制

外层104成员（103清单文件+manifest），内层118成员，其中95为 inline-package 声明的消费子集。
38张图片完成解码，27组不同裁片声明核对 SHA/尺寸/来源裁切 RGB 摘要；PNG 另外核对 chunk CRC、
完整 zlib 流和全部 scanlines。165个不同 payload 身份完成 B 规范化 payload SHA 核对；本次数量包括
扫描全部内层 JSON，和旧包前检采用不同扫描范围，不是功能测试数。

当前 E0.3/G0.7/Check0.7、manifest final outputs、pipeline report 精确绑定。
14个 DONE stage 分别核对 wrapper 文件 SHA/版本/身份、`payload.result` 版本/身份和当前运行回执。
最终 E 在 continuation_prepare.result.payload.evidence，G 在 content_apply.result.payload.graph，
Check 为 content_quality.result；三者与 artifacts 文件的整个原生 envelope 精确相等。
Evidence 自有 continuation run，Graph/Check 缺顶层 run_id，均保留原值；真实 pipeline 运行通过
current_run_receipt 和精确结果绑定，没有补造 run_id。五页包/source范围与相邻答案前缀范围分别记录。

来源 fragments、活动 content_fragments、plain/LaTeX runs、typed regions/render_regions、
content_fragment_ids 分别核对并原样提供。读取3个当前 REGION_DRAFT 和20个 pieces 输出码点区间；
有 source_region 时不要求旧 source_fragment_ids 非空。原始候选、历史区域、候选/风险、core/检查复用
依据及未知字段完整保留在 documents；档案视图只提供引用与指针，不宣称所有旧字段已共同定稿。
Q9仍是15个呈现区域，不按33个来源片段推框；viewer-173 与 resource-173 独立核对。
来源层证明和旧 core 复用依据不能覆盖当前0.7活动修订或消除HOLD。

1797个 input_refs 出现位置按真实形状分类：1702原生产物、62原生文档、11资产字节、9裁片字节、
2嵌入 acquisition receipt、11已知未解析历史引用。分类未伪造 C01 kind/revision。
固定历史引用的身份、11个位置以及两个状态均在原始回执中明确保留：

```text
b-evidence-18e2d1ee2a22288f585513f0 / revision 1
a2e53e1fc5ddee5ed0eaa57102af074a9b20b7815aa065116464446b9be7a8da
UNRESOLVED_HISTORY_REFERENCE + UNCONFIRMED_REQUIREDNESS
optional = null
```

本轮未核准内容、未确认该历史对象的必要性、未宣称完整语义闭包或公共格式资格。
SQLITE_AND_SCRIPTS_BYTES_ONLY：包内数据库与脚本只读作成员字节，没有导入/执行 B 脚本或打开/查询数据库。

## 有限版本与公共 API 核对

实际14条公开分派结果见 [versions.stdout.txt](../evidence/A06/author/frozen-01/versions.stdout.txt)：
Graph/Check0.4/0.5 当前顶层均 ARCHIVE_ONLY_NOT_CURRENT，已绑定档案均 ARCHIVE_ONLY；
0.6及9.9均 UNSUPPORTED_VERSION；0.7仅 READ_ONLY_HOLD。包内17个绑定 archive 出现位置覆盖
G0.4/G0.5/Check0.4/Check0.5，原生值可通过 documents 指针读取。没有造0.6正样例或声称支持它。
2项 unittest 覆盖上述有限矩阵及未注册入口形状，记录在 version-tests 原始输出；不把矩阵数量当业务验收分。

已实际导入 `annotation.contracts` 的 `load_bundle/validate_bundle/schema/ContractError`，
`schema()` 实际返回 ExchangeBundle schema；已有固定消费者 normal/exception/unknown 均退出0并 EXACT_MATCH。
它们分别产生合成 READY_FOR_SUBMISSION、NEEDS_REVIEW、NEEDS_RECONCILIATION，execution_mode 均 SIMULATED。
C01固定样例是 `1.0.0-a-proposal`/`c01-exchange-1` 公共消费者，和本次 B 原生诊断消费者分开；
没有把合成 APPLIED/UNKNOWN 当作真实 B 的执行证据。公共源码/样例未修改。

## 开发历史、冻结额度与释放

冻结前 development-01 的原包及坏资源样例误停在 UNBOUND_FINAL_OUTPUT；development-02 原包误停在
UNBOUND_ARCHIVE。原因分别是将最终对象假设为 stage 直接结果、只识别 archive 相邻直接 ref。
已按原包真实嵌套路径及 inline_basis+input_refs 精确绑定纠正，未改原输入或预期。
development-01/02/03 的原始输出全部保留；development-03 原包首次返回 HOLD。
后来增加了来源文本 SHA/码点区间核对，并冻结为9076d35e；冻结后的四例全部符合预期。
这些是冻结前开发记录，未作为独立验收。只有**一个**实现候选被冻结；冻结后未再修改实现或测试配方。
没有使用第二候选额度，也没有向调度索取纠正续派。

正式 driver 父进程结束、退出0，10个同步子进程全部由 subprocess.run 等待并回收；未启动后台进程、
浏览器或服务。释放证明见 [release.json](../evidence/A06/author/release.json)。
未平台/profile/凭据/模型/付费/网络/push/B消息/其他任务消息/题22/书级送审；未占用线上会话。
完整新增文件 SHA256/长度清单见 [manifest.json](../evidence/A06/manifest.json)，该文件按明示规则排除自身。

| PENDING_A 分项 | 本次作者事实 |
|---|---|
| 公共 API/固定 C01 消费者 | 已提供说明并实际调用；仍是 A 提案 |
| 固定包字节 | 已核对且原件未变 |
| 原生 HOLD 诊断实现 | 冻结执行符合预期；独立验收待定 |
| 版本显式拒绝 | 本次有限矩阵及完整未知版样例已验证 |
| 历史引用必要性/语义闭包 | UNCONFIRMED_REQUIREDNESS，未解决 |
| 共同映射与材料发送 | 未确认、未发送 B |
| 联合业务/内容/平台/I01 | 未验收；本任务不替代 I01-A 或 A03 |

交付状态为 **REVIEW**；后续独立验收和是否集成由调度决定。
