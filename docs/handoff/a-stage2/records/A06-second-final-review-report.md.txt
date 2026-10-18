# A06 第二、最终候选独立差量验收：ACCEPTED

2026-10-18（Asia/Shanghai）。独立验收对话 `01a14e21-162e-7840-9052-501984bc3d75`。

**ACCEPTED，仅限 A06 固定 B 包的只读 HOLD 诊断及明确拒绝边界。** F01 已在第二、最终冻结候选中关闭：14 个 stage 的 `payload.result.kind/schema_version` 独立校验与公共入口接线得到复核；原 ZIP HOLD 与非最终 `inline_apply` 结果未知版本两个完整公共入口各一次，均符合预期。未受影响的坏资源、陈旧 Check、顶层/历史版本矩阵及 C01 三个固定消费者沿用第一独立报告的既定结果，没有重跑首轮全集。

原包继续 `HOLD`、`business_acceptance=false`、`c01_execution_eligible=false`。历史引用与其必要性、共同映射、B 内容和联合业务仍未确认；本结论不授予 B→C01 执行资格，不代替 I01-A 或真实 B 正向链证明。是否集成由调度决定。

## 固定交付、输入及独立副本

| 对象 | 确切身份 |
|---|---|
| 本轮派发工作流 | `5989ef6733064485fee62349be889c58737cbb0d`；[派发单](A06-second-final-review-dispatch.md) |
| 作者最终交付 | `d78737815279965f660057bea0a572b426098aaa` |
| 第二、最终实现冻结 | `43ebdd21f2dc6803ae322b95776806e167884749` |
| 第一交付 / 原公共基线 | `761d9afed8b9d3d33851ad3d79b0bee7c294089d` / `a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8` |
| B 包提交 / 说明代码基线 | `0e5434f0ecf57152ec03f66bd7d0cf48b7c0700f` / `c3cc2df7a0be24c125c83681c0499c0d328d78f6` |
| 固定 ZIP | `D:/1800/.local/stages/coordinator/b-handoff-0e5434f/B-46007447-Q16-offline-HOLD-2026-10-17.zip` |
| ZIP SHA256 / 长度 | `b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d` / 11,681,712 bytes |
| 原 manifest SHA256 | `3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f` |
| run | `pipeline-run-0a2c03e193694ef88953f3ca08b8cde2` |

只读作者仓库的固定 Git 对象，全部 Git 调用均用 `-c core.longpaths=true`、`GIT_NO_LAZY_FETCH=1`、`GIT_OPTIONAL_LOCKS=0`。独立通过 `ls-tree` 和 `cat-file --batch` 导出 raw blob，逐个核对 Git OID、SHA256 和长度，没有 checkout/archive 换行转换，也没有浮动代码取样。

新的代码副本为 `D:/1800/docs/evidence/A06/review/second-final/code/`，115 个文件、6,250,500 bytes，不含 `.git`。输入副本、唯一变体、输出、脚本均在 `docs/evidence/A06/review/second-final/` 的新目录。实际 CPython 3.9.13、Pillow 11.3.0、pydantic 2.12.5；公共模块、reader、CLI 的实际 `__file__` 均指向这份副本。见 [raw-export.json](../evidence/A06/review/second-final/raw-export.json) 与 [imports.stdout.txt](../evidence/A06/review/second-final/run/imports.stdout.txt)。没有安装依赖或声称清洁安装证明。

独立核对同一交付的作者清单 32 个成员、3,843,877 bytes 均匹配。报告、清单、释放原始 SHA 分别为：

- `11fd37526062a92a034a29c5ad591449db5e33388cc16812f49c1757796ff66d`（9,325 bytes）。
- `5e09e958ed0d97ea51b855918a777182278cd9f52c9af98b630a001205e533db`（7,426 bytes）。
- `5cc99900a4195965cfe516f377bb30ed19fcd9e5e9b66ae227c4390209be301b`（4,188 bytes）。

调度预检仅用作交付资格和释放依据，没有用它代替本次公共入口复验。

## F01 静态修复与窄字段检查

第二候选相对第一交付仅一个已有产品文件改变：[reader.py](../evidence/A06/review/second-final/code/src/annotation/source/b_handoff/reader.py)，raw SHA256 `a80acf8a15d7c822c82ef6720a6125e79cfcee0498ac60d3f1c7a80ca030cd61`。其余已有 Git 路径对象全部相同；新增说明、配方、窄测试和新作者证据均在允许范围。第二实现冻结至最终交付的产品、配方、测试字节未改。

结果门第 116–129 行分别校验 kind 和 schema_version；第 340 行在原 wrapper 版本/身份核对后、result_ref 核对前调用它，不以 payload 摘要或引用匹配替代外层版本判断。未知版本为 `UNSUPPORTED_VERSION`，错 kind 为 `UNSUPPORTED_KIND`，均在 VERSION 层定位到相应结果字段。

固定14组规则同时对照原 ZIP 实际 stage result、首轮独立观察和冻结测试中的 OBSERVED 表，全部一致，见 [observed-stage-results.json](../evidence/A06/review/second-final/observed-stage-results.json)。E0.2、G0.3、Check0.3/.4/.5 和独立 trial kind 仅在对应 stage 历史诊断语境核对，不扩展当前顶层版本支持。

仅运行冻结的 `tests/test_a06_stage_results.py -v` 一次：3 个方法覆盖 14 组已观察 kind/schema、原定一个未知版本和一个错 kind；全部符合。没有运行其他 unittest、首轮矩阵或完整错误 kind 包。该窄字段调用不是公共接收证明；下面两个完整公共入口另行实际运行。原始输出见 [narrow-stage-fields.stderr.txt](../evidence/A06/review/second-final/run/narrow-stage-fields.stderr.txt)。

## 唯一变体的独立重建和两个公共入口

使用冻结 `make_stage_result_variant.py` 在自己的原 ZIP 副本上生成一次唯一 `TEST_VARIANT`：只将非最终 `inline_apply` 的结果 schema_version 从 `b-inline-apply-stage-trial/0.1` 改为 `b-inline-apply-stage-trial/9.9`。未运行 B 脚本、生产者或旧三变体配方。

独立静态审计确认：全部外层成员长度/SHA、manifest、对象规范化 payload 自摘要、14 个 wrapper 文件/身份/result_ref、三个当前 final outputs 和真实嵌套结果绑定都正确重封。目标结果 payload 与 `artifact_id/revision/content_hash` 不变；另外 13 个 stage result 不变，当前 E/G/Check 和内层 ZIP 原字节不变。配方的逐成员前后身份与独立比对相同，见 [variant-static-audit.json](../evidence/A06/review/second-final/variant-static-audit.json) 和 [recipe.json](../evidence/A06/review/second-final/variant/recipe.json)。

自己的变体 ZIP 为 12,529,826 bytes，SHA256 `5911f8d572c97027f0ac12a5c1dbe3e190e59a6391904fdd91cef6501bf91af8`；manifest SHA256 `bd0f9a9689dda95da72b4f84b1690830e5ec9b69b20866117f648b944d0b7c85`。它与冻结配方身份相同，仍仅称 TEST_VARIANT，不是 B 的新交付。

从自有 `foreign-cwd/`，通过未改的 `examples/a06/consume.py` → 公共 CLI → `receive_package`，只运行以下两个完整入口，每项一次：

| 完整入口 | 退出码 | 实际结果 |
|---|---:|---|
| 原固定 ZIP 的自有同字节副本 | 0 | HOLD；14 个 `result_version_check` 均准确标明 kind/schema、实际结果路径、validated=true、`FIXED_STAGE_DIAGNOSTIC_ONLY`、`grants_current_top_level_support=false`、business_acceptance=false |
| 非最终结果未知版本 TEST_VARIANT | 2 | REJECTED；`UNSUPPORTED_VERSION / VERSION`，明确给出 stage、预期及实际版本 |

未知结果的实际路径为 `objects/65f2939106f933a90b4be7249f7e447219d736fd878d3cc696e68ac570af282c.json#/payload/result/schema_version`。拒绝到达新结果版本门，没有以外层 SHA 失败代替。两例 stderr 均为空。见 [run-summary.json](../evidence/A06/review/second-final/run-summary.json)、[原包原始输出](../evidence/A06/review/second-final/run/original.stdout.txt)、[未知结果原始输出](../evidence/A06/review/second-final/run/unknown-stage-result.stdout.txt) 和 [14 项结果层回执](../evidence/A06/review/second-final/result-version-checks.json)。

独立脚本只路由输入/输出、保留进程和比较既定预期，没有替换候选业务函数、版本门或守卫。外层命令如下，全部实际子调用 argv/cwd/环境覆盖/PID/时间/退出码/stdout/stderr 均在对应 `run/*.process.json`、`outer/*.process.json` 中保留：

```powershell
python -B D:/1800/docs/evidence/A06/review/second-final/run_outer.py
```

该命令已经运行；输出目录为首次结果，不能覆盖或重跑。脚本、原字节副本、输入及变体均由本次新清单绑定，供只读审计。

## 原事实保持与首轮结果承接

将本次已保存的原包回执仅删除新增的 14 个 `result_version_check` 后，JSON 值与首轮独立原包回执**完全相等**，没有额外接收调用。见 [receipt-delta-check.json](../evidence/A06/review/second-final/receipt-delta-check.json)。因此原34题候选/66答案候选/127问题、身份绑定、五页与相邻前缀 scope、run、资源/内容层、未核准标记和业务资格均保持，READY 也没有提升为业务通过。

固定历史引用 `b-evidence-18e2d1ee2a22288f585513f0` / revision 1 / `a2e53e1fc5ddee5ed0eaa57102af074a9b20b7815aa065116464446b9be7a8da` 的 11 个位置继续返回 `UNRESOLVED_HISTORY_REFERENCE`、`UNCONFIRMED_REQUIREDNESS`，`requiredness=UNCONFIRMED`、`optional=null`。没有补造引用、默认可选或宣称完整语义闭包。

首轮 [A06-review-report.md](A06-review-report.md) 的 REWORK 及 F01 静态发现历史原样保留；不改写成首轮曾动态证明绕过。首轮报告、507成员清单、释放 SHA 仍分别为 `fdefde2e92095b9e922ae264a6b9595af5d93ee4c6dd5f5f980e941a031c0ae4`、`b3842a023b39c1f26ba42db6eab93329adfae4ad084e756b09cb67a780af5624`、`3917bf27b1d013dad625b2bfdb9b779fcc877dabe15380b147f8405399f64ea9`。

本次开始及结束逐个验证首轮清单全部 507 文件、131,413,856 bytes 未变。未改 reader 既有公开版本分派、解码、路径、hash、解析等函数；`_receive_package` 去掉新增门调用和输出字段后，其余函数源码与首候选精确相等；views、CLI、原消费者、配方、既有测试和公共受保护文件 Git 对象相同。证明见 [inheritance-audit.json](../evidence/A06/review/second-final/inheritance-audit.json) 与 [fixed-reader.diff](../evidence/A06/review/second-final/fixed-reader.diff)。

据此承接首轮坏资源 `RESOURCE_INVALID/RESOURCE`、陈旧 Check `STALE_CHECK/CURRENT_BINDING`、原当前未知版本拒绝和既定 Graph/Check0.4/.5/.6/.7 矩阵，以及公共 C01 正常/异常/UNKNOWN 三固定消费者的有限结果。0.4/.5 当前顶层仍拒绝、只在绑定历史中读取；0.6 没有完整正例并明确拒绝；0.7 仍仅只读诊断。C01 三例仍是 SIMULATED 的既有公共消费者结果，没有在本轮重跑或升级为 B 正向业务证明。

## 释放、证据清单和最终边界

本次 driver PID 2156 已由外层同步等待返回 0，5 个同步子调用（导入、窄字段、配方、两个公共入口）均已返回并回收。加 driver 和外层共记录 7 个真实 PID，外层命令完成后用 `Get-Process` 核对全部不存在；raw Git batch 另有同步回收记录。没有后台进程、浏览器或平台会话。见 [release.json](../evidence/A06/review/second-final/release.json) 和 [post-run-process-probe.json](../evidence/A06/review/second-final/post-run-process-probe.json)。

原 ZIP 及自有输入副本结束时摘要不变，raw 导出所有文件结束时再次核对；没有修改产品、作者文件、旧报告/证据、state 或 Git 索引，未提交/合并/推送或联系作者/B。没有网络、安装、模型、平台/profile/凭据访问；没有执行 B 脚本/生产者或打开/查询 SQLite，包内数据库和脚本只作清单字节读取。

新报告、脚本、源码原字节、配方、输入、变体、原始流和释放记录的长度/SHA256 见 [review-manifest.json](../evidence/A06/review/second-final/review-manifest.json)，排除清单自身；首轮证据按既定摘要引用并保留。F01 关闭记录见 [findings.json](../evidence/A06/review/second-final/findings.json)，最终核对见 [finalization.json](../evidence/A06/review/second-final/finalization.json)。

| 项目 | 最终有限结论 |
|---|---|
| F01 结果层版本/kind门 | CLOSED；固定14项与两个差量入口独立符合 |
| 公共 API、包字节与只读接收 | ACCEPTED 于固定包 HOLD/明确拒绝边界；公共 C01 既有结果按原证据承接 |
| 历史引用必要性与完整闭包 | UNCONFIRMED_REQUIREDNESS，未解决 |
| B→C01 正向映射、共同合同、内容及联合业务 | 未确认/未验收；不授予执行资格 |
| 平台/OCR/整章与真实 B 正向链 | 未验收；I01-A 的 synthetic 本地集成不作替代 |

两次实现冻结额度已耗尽，本次未发生失败后修复或重跑，也没有第三候选。现将第二、最终候选的上述有限 ACCEPTED 与完整证据交调度收口。
