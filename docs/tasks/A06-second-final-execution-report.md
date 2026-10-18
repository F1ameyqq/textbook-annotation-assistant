# A06 F01 第二、最终候选执行交付：REVIEW

2026-10-18（Asia/Shanghai）。第二次且最后一次冻结实现已完成有界纠正；两项完整入口各一次，均符合预期。
**作者状态为 REVIEW，未独立验收、未集成。无第三候选；冻结后没有修后重跑。**

| 对象 | 固定身份 |
|---|---|
| 本次起点 / 第一交付 | `761d9afed8b9d3d33851ad3d79b0bee7c294089d` |
| 第二、最终实现冻结 | `43ebdd21f2dc6803ae322b95776806e167884749` |
| 调度续派工作流 | `aab6a34214ae6b25ff784425e680c8ef4abdcea0` |
| 原公共基线 | `a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8` |
| 分支 / 独立目录 | `codex/a06-b-native-receiver` / `D:/1800-worktrees/a06` |
| B 包提交 / 说明代码基线 | `0e5434f0ecf57152ec03f66bd7d0cf48b7c0700f` / `c3cc2df7a0be24c125c83681c0499c0d328d78f6` |

首候选 F01 是固定源码的静态发现，第一验收没有运行中间结果未知版变体；本报告不声称曾动态证明旧实现绕过。
已只读核对主目录固定第一验收报告、清单、释放，SHA 分别为
`fdefde2e92095b9e922ae264a6b9595af5d93ee4c6dd5f5f980e941a031c0ae4`、
`b3842a023b39c1f26ba42db6eab93329adfae4ad084e756b09cb67a780af5624`、
`3917bf27b1d013dad625b2bfdb9b779fcc877dabe15380b147f8405399f64ea9`；本次结束时三者再次核对不变。
原件位于 `D:/1800/docs/tasks/A06-review-report.md` 与 `D:/1800/docs/evidence/A06/review/candidate1-761d9afe/`。

## 唯一产品纠正

仅修改 [reader.py](../../src/annotation/source/b_handoff/reader.py)：新增固定14项 stage→kind/schema 表、
独立结果校验，并在已有 wrapper 版本/身份校验之后、result_ref 核对之前接入。
回执每个 `pipeline.stages[].result_version_check` 明确给出 kind、schema_version、结果路径、validated=true、
`context=FIXED_STAGE_DIAGNOSTIC_ONLY`、`grants_current_top_level_support=false` 和 business_acceptance=false。

未知版本为 `UNSUPPORTED_VERSION`，错 kind 为 `UNSUPPORTED_KIND`，均在 VERSION 层定位到
`objects/<实际wrapper文件SHA>.json#/payload/result/schema_version` 或 `/kind`。两类门独立于 payload 自摘要和引用。
14组规则逐项对照原 ZIP 与第一独立 `original-inspection.json`，见
[observed-stage-results.json](../evidence/A06/second-final/observed-stage-results.json)。E0.2/G0.3/Check0.3/.4/.5
及独立 trial kinds 仅在其确切 stage 历史诊断语境支持，不增加当前顶层或执行支持。

reader 原 SHA256 为 `241b2de4b82e84e12f5067bb8079d4cad6925339e0f9a343587fff5f2f2428f3`，
第二候选原字节 SHA256 为 `a80acf8a15d7c822c82ef6720a6125e79cfcee0498ac60d3f1c7a80ca030cd61`。
既有公开版本分派及其他 reader 函数原字节不变；资源、内容、历史引用及最终回执主体的尾段原字节不变。
views、CLI、原消费者、原配方、原测试和原 README 均未改。
[pre-freeze-checks.json](../evidence/A06/second-final/pre-freeze-checks.json) 记录逐函数/文件摘要；
[scope-check.json](../evidence/A06/second-final/scope-check.json) 记录公共受保护根相同 Git 对象及79个旧作者证据/报告的原字节保全。
没有改公共 contracts/native/delivery/runtime/pins/根依赖，未合入浮动主线/I01资料。

## 冻结前窄检查与单个差量配方

仅运行 [test_a06_stage_results.py](../../tests/test_a06_stage_results.py)：3个测试方法覆盖14个已观察精确对、
一个未知结果版本、一个错 kind，全部符合。未运行旧版本矩阵、四入口全集或 C01 消费者；冻结前完整接收调用为0。
实际 argv/cwd/PID/退出码/stdout/stderr 见新证据目录的 `pre-freeze/narrow-stage-fields.*`。

新配方 [make_stage_result_variant.py](../../examples/a06/make_stage_result_variant.py) 只生成一个 TEST_VARIANT：
非最终 `inline_apply` 的 result.schema_version 从 `b-inline-apply-stage-trial/0.1` 改为9.9。
目标 result 的 payload、artifact_id/revision/content_hash 不变；wrapper payload 摘要、文件地址、
必要下游引用、pipeline report 和 manifest 重封。其他13个 stage result 不变，当前 E/G/Check 文件原字节不变。
配方在生成时静态核对所有 payload 自摘要、wrapper/result refs 与最终输出，未调用 B 脚本或接收私有 helper。
原配方 [make_variants.py](../../examples/a06/make_variants.py) 未修改、未重跑。

变体身份及逐成员前后长度/SHA 见 [recipe.json](../evidence/A06/second-final/recipe.json)。变体 ZIP SHA256 为
`5911f8d572c97027f0ac12a5c1dbe3e190e59a6391904fdd91cef6501bf91af8`；本地文件在新证据 `local-only/variant/`，
按配方可重建，未作为 B 新交付。原 ZIP 仍为既存本地输入：

```text
D:/1800/.local/stages/coordinator/b-handoff-0e5434f/B-46007447-Q16-offline-HOLD-2026-10-17.zip
11,681,712 bytes
SHA256 b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d
manifest SHA256 3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f
```

## 第二冻结后的两项完整入口（各一次）

从43ebdd21的 raw Git blob导出156个必要文件至新 `local-only/frozen-code/root`，没有 checkout 换行转换或 `.git`。
导出 OID、SHA及长度见 [frozen-export.json](../evidence/A06/second-final/frozen-export.json)。实际 CPython仍为3.9.13，
使用已有依赖，未安装。子进程从新的 `frozen-run/foreign-cwd` 通过原 `examples/a06/consume.py` 和公开 CLI 调用接收入口；
PYTHONPATH 显式指向冻结源码。驱动及源文件位置/摘要见 `frozen-run/driver-metadata.json`。

| 完整入口 | 实测退出码/结果 | 实际门 |
|---|---|---|
| 原固定 ZIP | 0 / HOLD | 14条独立结果 kind/schema 核验全部可定位；34/66/127保持 |
| 非最终 stage 未知 result 版本 TEST_VARIANT | 2 / REJECTED | UNSUPPORTED_VERSION / VERSION；inline_apply 的 result.schema_version |

原始 argv/cwd/PID/时间/退出码/stdout/stderr 在 [frozen-run](../evidence/A06/second-final/frozen-run/summary.json)；两例 stderr 均为空。
实际未知版本错误路径为
`objects/65f2939106f933a90b4be7249f7e447219d736fd878d3cc696e68ac570af282c.json#/payload/result/schema_version`。
该包先通过外层成员、payload、wrapper身份等原门，故拒绝定位到新增结果版本层，未把外层hash失败算作完成。

对两次已经保存的原包回执作静态比较：仅去掉本次14个 `result_version_check` 后，新旧回执 JSON 值完全相等；
证据见 [receipt-delta-check.json](../evidence/A06/second-final/receipt-delta-check.json)。这没有增加接收调用。
因此 HOLD、business_acceptance=false、c01_execution_eligible=false、未核准标记、scope/run、内容层、
UNRESOLVED_HISTORY_REFERENCE、UNCONFIRMED_REQUIREDNESS、optional=null及既有全部绑定保持。

本次未重跑坏资源、陈旧 Check、顶层/档案版本矩阵、C01三个消费者；依据未受影响路径的原字节和固定第一独立报告，
承接其已记录结果，没有把首包 F01 的 REWORK 改成通过。第二候选只修该原要求缺口，未扩展标准。

实际父命令（cwd为本独立目录；独立复现须重新导出自己的固定源码和变体，见 [差量说明](../../examples/a06/SECOND_FINAL.md)）：

```powershell
$env:GIT_NO_LAZY_FETCH = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B docs/evidence/A06/second-final/local-only/frozen-code/root/examples/a06/verify_second_final.py 'D:/1800/.local/stages/coordinator/b-handoff-0e5434f/B-46007447-Q16-offline-HOLD-2026-10-17.zip' docs/evidence/A06/second-final/recipe.json docs/evidence/A06/second-final/frozen-run
```

上述输出目录已存在，复现时改为新目录；冻结 driver 只执行这两个完整入口，不调用原全集 driver。

## 释放、清单与交付状态

冻结 driver PID78412结束并退出0；原包子PID40792、变体子PID75004已同步等待回收。
冻结前窄检查PID52724及配方PID43004也已结束。记录的5个PID在独立进程查询中均不存在，
见 [release.json](../evidence/A06/second-final/release.json) 与 [post-run-process-probe.json](../evidence/A06/second-final/post-run-process-probe.json)。
没有后台、浏览器或平台会话。原 ZIP 结束时SHA未变，旧作者/独立证据均未覆写。

新差量文件原字节 SHA256/长度及本地变体身份见 [manifest.json](../evidence/A06/second-final/manifest.json)；排除自身，
大变体ZIP与raw导出目录只保留在本地ignored目录，分别由配方和frozen-export清单绑定。原清单 `docs/evidence/A06/manifest.json` 未改。
最终证据提交只追加本报告/新证据，不改变43ebdd21冻结的产品、配方或窄测试字节。

所有Git调用均带 `-c core.longpaths=true` 且禁用惰性联网取对象。没有B脚本/生产者/SQLite查询、平台/profile/凭据、
网络/安装/模型/付费、B消息/其他任务消息、push、题22或书级送审；未改主目录state/index。

交付 **REVIEW**，等待调度续派第二候选独立差量验收。历史引用必要性、共同映射、B内容/联合业务、平台和I01仍未确认；
结果版本门补齐不授予可执行接入或联合通过。两次实现冻结额度已用完，作者不再修改后重跑或建立第三候选。
