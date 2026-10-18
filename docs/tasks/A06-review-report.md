# A06 第一冻结候选独立验收：REWORK

2026-10-18（Asia/Shanghai）。独立验收对话 `01a14e21-162e-7840-9052-501984bc3d75`。

**结论：REWORK。** 本轮四个公共入口各运行一次，14 条既定版本分派和 C01 三个固定消费者均符合预期；原包的有限 HOLD 诊断与原生值保留得到独立复现。但静态核查发现原任务“wrapper 与 payload.result 各自的版本和身份”尚未完整落实：stage wrapper 有版本检查，stage result 只有引用/摘要绑定，没有独立结果版本检查。此项阻止 A06 整体有限接收验收通过，不否定以下已记录的具体运行结果。

未修改候选、生成额外负例或重跑业务。第一候选现场已固定交调度；没有自行启用第二候选。

## 固定身份与独立环境

| 对象 | 确切身份 |
|---|---|
| A 组合基线 | `a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8` |
| 第一实现候选 | `9076d35e81678cdba8ad8651e95a44265fdc345c` |
| 最终交付 | `761d9afed8b9d3d33851ad3d79b0bee7c294089d` |
| 本轮派发工作流 | `d956b3138c28e82dec05573003d5e95fde72989f`；[派发单](A06-review-dispatch.md) |
| B 包提交 / 包说明代码基线 | `0e5434f0ecf57152ec03f66bd7d0cf48b7c0700f` / `c3cc2df7a0be24c125c83681c0499c0d328d78f6` |
| 原 ZIP | `D:/1800/.local/stages/coordinator/b-handoff-0e5434f/B-46007447-Q16-offline-HOLD-2026-10-17.zip` |
| ZIP SHA256 / 长度 | `b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d` / 11,681,712 bytes |
| 原 manifest SHA256 | `3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f` |
| 固定 run | `pipeline-run-0a2c03e193694ef88953f3ca08b8cde2` |

从作者仓库只读固定 Git 对象，以 `git -c core.longpaths=true`、`GIT_NO_LAZY_FETCH=1` 和 `GIT_OPTIONAL_LOCKS=0` 执行 `ls-tree`/`cat-file --batch`，没有读取浮动产品代码。导出文件逐个核对 raw blob OID、SHA256 和长度；不经过 checkout/archive 的换行转换。自有隔离代码为 `D:/1800/docs/evidence/A06/review/candidate1-761d9afe/code/`，448 个文件、26,700,167 bytes，包含实现、必要既有消费者/样例及固定作者交付资料；不含 `.git`。

最终交付相对组合基线的 90 个路径全部为白名单内新增；公共 contracts/native/delivery/runtime/pins/根依赖未变。实现、消费者、配方和测试从实现候选到最终交付均无差异。独立复核作者清单 89 个成员、7,418,666 bytes 的长度和 SHA 全部一致。三个派发指定文件的实际 SHA 分别为：

- 作者报告：`deba7a12f2b74b9261a8404ce19885fcea3c574d68f8e1bbd9761a8c2e7df0bb`。
- 作者清单：`e37efb2ba44b6005cb4c15e095ab22e00d804c4884ce988d6b613cb8b5189d33`。
- 作者释放记录：`2f7eb5d6203ae7e7c441170c03ef17d012e7139df64423635c38ada30120283c`。

实际 Python 为 CPython 3.9.13，既有 Pillow 11.3.0、pydantic 2.12.5；未安装依赖。实际 `__file__`、源码 SHA 和入口签名见 [imports.stdout.txt](../evidence/A06/review/candidate1-761d9afe/run/imports.stdout.txt)。b_handoff、reader、views、CLI、contracts 均从本次 raw 导出导入，调用 cwd 使用两个新建外部目录，不依赖作者目录、B UI 或旧 editable 路径。这是固定源码消费证明，不是清洁安装验收。

## 唯一静态缺口 F01（P2）

原要求见 [执行任务“主入口必须实际核对的内容”第 2 项](A06-b-native-receiver.md)。固定 [reader.py](../evidence/A06/review/candidate1-761d9afe/code/src/annotation/source/b_handoff/reader.py) SHA256 为 `241b2de4b82e84e12f5067bb8079d4cad6925339e0f9a343587fff5f2f2428f3`。

- 第 303–304 行实际检查 wrapper 的 `schema_version` 与 `kind`。
- 第 306–307 行取得 `payload.result` 后，只调用 `exact(stage['result_ref'], result, ...)`。`ref()` 第 48–49 行只取 `artifact_id/revision/content_hash`，不包含结果层版本或 kind。前面的规范化 hash 检查只覆盖 `payload`，不覆盖外层 `schema_version`。
- 三个最终 E/G/Check 有顶层版本门及精确 envelope 绑定；其他 stage result 不会经过独立结果层版本门。`views.archive_views()` 只分派以 `_archive` 结尾的四种历史 archive，不能替代对这些 stage result 的检查。
- 实际固定包确有不同结果版本，如 `evidence` 的 E0.2、`assemble` 的 G0.3、`quality` 的 Check0.3，以及多个独立 trial kind。原始 JSON 值完整保留，但接收器没有对这些结果层版本逐一核对或明确给出未确认的分派状态。实际 14 个 wrapper/result 版本已独立列在 [original-inspection.json](../evidence/A06/review/candidate1-761d9afe/original-inspection.json) 的 `wrapper_result_versions`。

因此，不能把已验证 wrapper 版本和结果引用摘要表述为 wrapper/result 两层版本均已核验。这是原条款内的静态实现缺口；**没有追加未知中间结果变体，也没有实测声称该额外变体已被接受**。四个允许样例的运行结果保持。调度可据此决定是否使用尚未启用的第二候选作有界纠正；不要求 B 重建包，不增加业务质量、平台或任意版本兼容标准。

机器可读定位见 [static-findings.json](../evidence/A06/review/candidate1-761d9afe/static-findings.json)。

## 四个公共入口与既定分派

先静态审配方，再在自有新目录生成三份 `TEST_VARIANT`。独立审计所有变体的 ZIP/manifest、成员长度/SHA、对象规范化自摘要、wrapper 文件及其 result_ref、pipeline final outputs 和实际最终 envelope。非破坏层全部重封有效；陈旧 Check 的唯一故意关系缺口确为当前 `graph_ref` 指向原有历史 Graph。坏资源仅改目标 JPEG 字节与 manifest。三份 ZIP 摘要与冻结配方一致，逐成员前后身份已保留，见 [static-audit.json](../evidence/A06/review/candidate1-761d9afe/static-audit.json) 和 [variants.json](../evidence/A06/review/candidate1-761d9afe/variants/variants.json)。

每例均由冻结的 `examples/a06/consume.py` 经公共 CLI 调用 `receive_package`，没有以私有 helper 或 B verifier 代替接收入口。原包调用加 `--documents`，便于对实际返回的原生值作独立比对；未增加第二次接收调用。

| 样例（各一次） | 退出码 | 实际结果与到达层 |
|---|---:|---|
| 原 ZIP 的自有同字节副本 | 0 | HOLD；34 题候选、66 答案候选、127 当前问题；业务及 C01 执行资格均 false |
| 坏资源 TEST_VARIANT | 2 | `RESOURCE_INVALID` / `RESOURCE`；`supporting-fixtures/q4-stem.jpg` |
| 陈旧 Check TEST_VARIANT | 2 | `STALE_CHECK` / `CURRENT_BINDING`；`artifacts/check.json#/payload/graph_ref` |
| 未知版本 TEST_VARIANT | 2 | `UNSUPPORTED_VERSION` / `VERSION`；`artifacts/graph.json#/schema_version`，G9.9 |

四例 stderr 均为空；错误中的 BytesIO 内存地址不作稳定字符串比较。三份变体 SHA 分别为 `b759b87bbe13646f23519a6f8a7ba49554ee3c5aa56f885431846eca2df2ccf1`、`f7bb2786a9700169d8df31766c62ee8c94ada6fe3ea6efb7dc2dd5e76d9c0414`、`777287ec0bf0d4fed591e9a5b7af5c0bf3f1a994b8c32dfaabcaf89d2b3afd84`。原件及自己的输入副本在结束时 SHA 均不变。

Graph/Check 合计 14 条既定公开分派全部符合：0.4/0.5 绑定历史为 `ARCHIVE_ONLY`、当前顶层为 `ARCHIVE_ONLY_NOT_CURRENT`；0.6/9.9 为 `UNSUPPORTED_VERSION`；0.7 为 `READ_ONLY_HOLD`。包内 17 处绑定 archive 覆盖 G0.4/G0.5/Check0.4/Check0.5，原生档案值保留。未造 0.6 正包、未跑旧 B 流水线。见 [version-matrix.json](../evidence/A06/review/candidate1-761d9afe/version-matrix.json)。

## 实际诊断内容与公共 API

对唯一原包公共入口的返回值逐项比对：所有外层/内层原生 JSON 文档与固定输入值相等；100 个当前题答实体的 native 值保持。资源回执为 104 外层成员、103 清单文件、118 内层成员、95 声明消费成员、38 个解码图像、27 组裁片核对、165 个不同 payload 身份。这些是固定输入完整性数量，不是测试成绩或内容正确率。

当前 E/G/Check 与 manifest/report 的 final outputs 和三个真实嵌套 stage 路径精确绑定，14 个 wrapper 文件身份和 result_ref 均正确。五页 package/source scope 与相邻答案前缀 scope 分别保留；Evidence 自有 run，Graph/Check 缺失的顶层 run_id 保留 null，不补造同 run。完整结果版本核对的 F01 仍单独阻断。

来源 fragments、当前 content_fragments、plain/LaTeX runs、typed regions/render_regions、内容片段引用及未知字段没有被删改。3 个 REGION_DRAFT 及其 source_region 保留，包括旧 source_fragment_ids 为空的情况；20 个字符 pieces 用 Unicode 码点半开区间比对实际文字。固定答案实体仍保留 33 个来源片段、15 个 typed/render regions，不推导平台框数；`platform_box_count=null`。viewer-173/resource-173 保留不同摘要。档案候选、风险和 core/basis 原生值保留，未授予当前检查资格。

固定历史引用 `b-evidence-18e2d1ee2a22288f585513f0` / revision 1 / `a2e53e1fc5ddee5ed0eaa57102af074a9b20b7815aa065116464446b9be7a8da` 的 11 个位置及两个状态均实际返回：`UNRESOLVED_HISTORY_REFERENCE`、`UNCONFIRMED_REQUIREDNESS`，`optional=null`。没有伪造闭合或默认可选。

实际导入 `annotation.contracts` 的 `load_bundle/validate_bundle/schema/ContractError`；schema 为 ExchangeBundle、`1.0.0-a-proposal`，固定交换消费者仍是 `c01-exchange-1`。已有 normal/exception/unknown 各调用一次，均退出 0、EXACT_MATCH，状态分别为 READY_FOR_SUBMISSION、NEEDS_REVIEW、NEEDS_RECONCILIATION；execution_mode 均 SIMULATED。未重跑 C01/A02 全套回归，也未把这些合成结果当作 B 草稿执行证据。

## 原始记录、释放和交接边界

独立运行的外层命令如下；实际全部子调用 argv、cwd、环境覆盖、PID、开始/结束时间、退出码与原始 stdout/stderr 保存在 [run/](../evidence/A06/review/candidate1-761d9afe/run-summary.json) 对应文件；所有调用均使用显式自有输入与冻结源码路径。

```powershell
python -B D:/1800/docs/evidence/A06/review/candidate1-761d9afe/run_outer.py
```

运行脚本只路由输入/输出、记录进程和比较任务既定预期，不替换候选业务函数或守卫。`run-summary.json` 的 `all_expectations_met=true` 只表示本轮限定动态检查符合预期，不是整体验收结论。原始 `original.stdout.txt` 为 56,516,541 bytes，包含完整回执和 native documents，保留于本地证据目录。

独立 driver PID 78152 已由外层等待返回 0；其 9 个同步子调用均已等待回收。加变体生成器与 driver，共 11 条真实同步进程记录；外层自身也在命令返回后另行检查，所记录的 12 个 PID 均已不存在。见 [release.json](../evidence/A06/review/candidate1-761d9afe/release.json) 和 [post-run-process-probe.json](../evidence/A06/review/candidate1-761d9afe/post-run-process-probe.json)。没有后台/浏览器/平台会话；作者缺失的子 PID 未补造。复验后 raw 导出全部 bytes 再次核对，见 [finalization.json](../evidence/A06/review/candidate1-761d9afe/finalization.json)。

全部新增验收文件及本报告的 SHA256/长度见 [review-manifest.json](../evidence/A06/review/candidate1-761d9afe/review-manifest.json)，清单明确排除自身。不写 state/Git 索引，不提交/合并/推送，不联系作者或 B。没有网络、模型、依赖安装、平台/profile/凭据访问，没有导入或执行 B 脚本/生产者，没有打开或查询 SQLite；包内数据库和脚本仅核对成员字节。

| PENDING_A 分项 | 本次独立事实 |
|---|---|
| 公共 API / 固定 C01 消费者 | 可导入且固定消费符合预期；仍是 A 提案 |
| 包字节与原件保全 | 独立核对完成，原件未变 |
| 原生 HOLD 诊断 | 四入口动态结果符合；完整有限验收因 F01 为 REWORK |
| 既定版本显式拒绝 | 当前顶层与绑定 archive 的既定矩阵符合；stage result 独立版本核对仍缺 |
| 历史引用必要性与完整语义闭包 | UNCONFIRMED_REQUIREDNESS，未解决 |
| B→C01 可执行映射 / 双方确认 | 未取得；不授予执行资格 |
| B 内容、共同业务、平台 / OCR / 整章 / I01 | 未验收；本轮不作替代 |

本次在第一候选上收口，等待调度对 F01 与是否使用第二、最终候选作决定。无第三包，不因四个动态入口符合就放宽原任务条款。
