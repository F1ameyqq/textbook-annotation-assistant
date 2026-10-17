# A01 integration-R2 独立静态与参照子审计

静态结论：**身份、固定字节及历史证据引用条件符合本轮要求，未发现静态阻断**。本子审计不作整轮 ACCEPTED；根验收者负责独立构造两父对象、双形态真实入口、无 Git 裸单例及实际导入取证。

| 固定身份 | 值 |
|---|---|
| 工作流 | `fe91c27939d13f9be290f8274a0d46d90f4de2f0` |
| 主父 M | `2d1dc8b97713ee06ec5bf35febe0b894ece584b2` |
| A01 最终交付 | `5f872150a237b195f73c78e02e13a91d2f4f46a7` |
| A01 测试补丁 | `f8f2981a815f96147144d3747d26752b564cc9f7` |
| 组合树 | `0645ac862f79fb4e232e4cfbd5f6bb5055a68d62` |
| A02 已接受最终交付 | `a1e5be00909172429d792b6c41bdaf384258694e` |
| A02 已接受补丁 | `ad71284f3b6ffc8454ee1d1e30933c8e39d7c1d8` |

先从确切工作流 Git 读取交接及链接的 A02 独立接受、主调度复现、真实集成检查和原 A01 R1 报告。输入原字节及其来源 OID/SHA/长度保存于 [inputs](inputs/) 与 [input-index.json](input-index.json)，没有复制整个历史归档。

复现命令：

```powershell
python -B 'D:\1800\docs\evidence\A01\review-integration-R2\static\audit.py'
```

最终实际退出 **0**，共 **1,266 条检查全部通过**、36 条只读 Git 命令均退出 0。[实际启动回执](launch.json)、[逐条检查](checks.json)、[Git 命令与退出码](commands.json)、[汇总](summary.json)完整保留。本脚本专为本轮固定身份编写，仅写新 `review-integration-R2/static/`，没有运行写死旧父的 R1 脚本，没有 Git 写操作。

## 组合身份与参照

[组合身份核对](combination-identities.json)确认组合树相对 M 的 464 条差异严格等于冻结 A01 相对共同祖先的差异，全部采用 A01 最终交付对应 OID；其余 11,430 份 M 文件的模式、类型、OID 完全保留。根属性、依赖、公共合同、调度文档/状态均保持固定 M；没有意外覆盖其他历史证据。本子审计读取既有固定树，不将这项核对冒称本子审计新执行了 merge-tree；根验收者另行独立构造。

全部相关 A01 生产源码、入口、测试、原夹具与新编码夹具，在本组合树、冻结最终交付及原 R1 组合树 `2078731114ad3a07368ca46a2f34c3544af64e2b` 中对应 OID 相同，包含全部 11 份生产源码。

[固定参照重核](fixed-reference-audit.json)逐项重新绑定原 **971 条 / 25 个明确 CRLF 候选**及 **62 条 / 3 个明确候选**的原声明提交、路径、blob OID、SHA256/长度和有限表示；清单本身 OID 不变。常规入口的政策测试保持不变，没有在新 root 上应用旧 971 项发行版保全，也没有放宽候选。

[四份编码原件](encoded-originals.json)的内容逐份严格等于原 Git blob，去除 base64 后的元数据逐条严格等于原 971 清单对应项；来源清单 SHA 固定。旧 I04 非阻断限制仍在：夹具顶层 `reference_commit` 的冻结值正确，但该冗余标签本身没有被常规测试二次认证，不能声称已修复。

## 新 A02 身份与五份 CRLF

[A02 身份核对](A02-identity.json)确认 M 及组合树采用已接受 A02 最终交付和补丁中的新 identity：OID `db0ca76a6a504ebd16e1b6731d104577c36bf0b0`，SHA256 `02b51187b4b4f711f0df8ea501201cafe99c078c84351a376a66ae2f892af58e`，没有采用旧失败版本。相关新测试/探针同样对应接受版本；`source_binding` 函数原始源码与 A02 修订前相同。

[188 项逐文件重核](A02-188-file-representation-audit.json)独立确认历史 index tree 即 M 的实际 tree `995c7ca0c925ebed7100cfcb589c2a45af40c671`，188 条对应 OID/SHA/长度均等于冻结 A02，且完整保留于组合树。历史记录中 183 条磁盘摘要匹配 Git 原字节，另外 5 条逐份用 Git 原字节计算完整 LF→CRLF，严格匹配原磁盘摘要及长度：

| 文件 | Git 字节 | CRLF 字节 |
|---|---:|---:|
| `examples/a02/R1/identity.py` | 2354 | 2396 |
| `examples/a02/portability-R2/probe.py` | 1581 | 1611 |
| `examples/a02/portability-R2/run_tests.py` | 2126 | 2166 |
| `examples/a02/portability-R2/verify.py` | 7056 | 7169 |
| `tests/test_a02_portability_r2.py` | 7481 | 7613 |

每份完整双 SHA 均在上述逐文件 JSON 中。这是对历史磁盘回执的独立 Git 字节一致性核验，不是再次观察其当时物理 index 或磁盘；本轮实际两形态表示由根验收者另记，没有改全局设置/根属性或源码。

[A02 前置接受核对](A02-prior-acceptance-scope.json)确认独立报告固定 SHA `92217848c055e133e2b79b4318027e1185105e8a75e5fc14531a7f1fda937d77`，主调度实际集成回执绑定 M、62 项通过无 skip，以及有界复现三条命令退出 0/1/0。按交接可引用其绑定拒绝和第二次真实 OS 启动失败等已接受负例，不在本子审计重放或将 mock 当真实无 Git。

## 历史可引用和不可替代项

[R1 引用范围](R1-reuse-scope.json)核对相关 A01 对应 OID 全部不变，因此可引用 I01/I02/I03/I05、F00–F04、原发行 R00–R02及入口错误传播实际回执。没有重跑这些负例或 630 项几何矩阵。原 R1 报告和清单分别固定为交接给出的 SHA `2aaed84505799509319cab8e99a94eba818b69fd301caf4d3be89fe48c6a3caf` / `a331ad8a039408f2225f9e9842cc0a4d0860af7a0ece67f3fafa527f0c6600ad`，其 REWORK 和 I04 原失配结果未改写。

不可用历史结果替代本轮的项目：

- 原 R1 raw 全入口的 I1-GIT-01 失败，不能变成 R2 成功；必须实测新组合的完整入口。
- 原 A02 为 52 项，本轮应实际观察新 62 项；两形态不相加为独立成绩。
- 原 R1 的导入路径、checkout、无 Git 环境观察，不能证明本轮实际导入或 OS 启动失败。
- 作者 `source_files` 不是 `__file__` 导入证据；本轮仍须根验收者重新采集。
- 平台、全书覆盖、B 确认、A04/D01 释放及其他原限制不由本子审计证明。

原 A01 新夹具清单表示区别仍为 **49/50 Git、原作者磁盘回执 50/50**：[独立双表示核对](A01-author-manifest-representation.json)证明 Git LF 86,374 字节 / SHA `51e2fd08803cfc918f62a23327da99993bf2a91363ef2ec3960f37765ee241db`，严格 64 个 LF→CRLF 为 86,438 字节 / SHA `9b979d4b18ffe4db50ad5473c218ba28fdcbed0515d68ce324894be09cc2d0eb`。没有更改旧清单或把这项加入原 25 候选。

## 审计器初稿与会话

首次静态脚本实际退出 1：初稿错误地假设历史 `disk_equal` 和 `exact_lf_to_crlf` 两个标志互斥；七份零字节 stderr 同时满足两条字节等式。原 SHA/长度没有不等，也不涉及五份非空 Python 差异。初稿、首轮检查/摘要/退出码和相关结果已完整保存于 [first-attempt](first-attempt/)，修正说明见 [collector-correction.json](collector-correction.json)。仅改本轮审计器的判断为实际 LF→CRLF 字节谓词后重核静态元数据；未改原回执、未重跑功能或负例。

本子审计所有同步 Python/Git 子进程已返回，待释放会话 0；这是同步进程完成依据，不是系统全进程普查。零网络、平台、浏览器、凭据/profile、OCR 或模型调用；没有实现修改、集成、提交、推送、其他 chat 联系或依赖释放。
