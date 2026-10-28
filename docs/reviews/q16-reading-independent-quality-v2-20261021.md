# Q16 与三个阅读任务 C01 v2/HOLD 独立差量复核

日期：2026-10-21（Asia/Shanghai）
共享仓库输入 HEAD：`d48b066ad2620d7f1a2e902b2b28e3139390a721`
固定 A 标识：`edf125961be9cdc1642652c038d99872b1c8cdc7`
v2 ZIP：`B-46007447-Q16-reading-C01-v2-HOLD-2026-10-21.zip`
最终结论：**PASS — v2 固定离线 HOLD 包可发布；旧版两项发布阻断已关闭。**

该结论只覆盖固定摘要的离线包、只读 C01 消费和内容/来源闭包，不升级为独立人工验收、A owner 接收、A 业务执行或业务通过。

## 摘要与安全解包

- v2 ZIP SHA-256：`4725523ec499a3074b268b12f0282ca795c13ddd98e97350078a50db89f7dc93`，与委托值一致。
- `delivery/bundle.json` SHA-256：`95488a276535a7bee7094238b02c6b41574e37df19d7b946830c6c07f9a824d6`，与委托值一致。
- ZIP 共 147 个唯一文件：146 个 manifest 成员加顶层 `manifest.json`。
- 安全预检未发现绝对路径、`..`、反斜杠路径、符号链接、重复名或大小写碰撞。
- 146/146 manifest 路径、字节数和 SHA-256 精确匹配，无漏列或额外成员。
- 91/91 固定 A 源文件的大小和 Git blob OID 全部匹配 pins；与 v1 包的 91 个 A 文件逐字节一致。

## v2 实际重放与读回

包内 `replay.py` 实际退出 0：

- 重建 46 个交付文件；
- 重建字节与包内固定 delivery 完全一致；
- 固定 A 读回与参考读回字节完全一致；
- 网络和模型导入禁用；
- `decision=HOLD`。

固定 A 消费者另行直接运行退出 0，确认：

- 4 个题/任务、1 个共享材料；
- 37 个来源窗口、26 个语义片段；
- 11 个 Q16 公式槽；
- 6 个未填题目空保持 `null`；
- 18 个模型来源核对、18 个独立人工待核项目；
- producer/consumer 全对象相等；
- 未执行计划、模拟、派发、A 业务或网站请求；
- A owner、独立人工和业务验收均为 false。

共享仓库 focused suite 实际运行 20/20 通过。

## 旧阻断关闭情况

### 1. 精确对象闭包：已关闭

v2 强制恰好 4 个 artifact、1 个 policy、2 个 evidence，并校验 evidence ID。独立追加一个合法、重新封装的额外 `SourceBundle` 后，固定 A + B 只读链以 `READONLY_ARTIFACTS` 拒绝，不再产生 v1 的错误成功结果。

### 2. 时间与不可变身份：已关闭

新增 `delivery/generation.json`：

- 首次实际构建 UTC 时间：`2026-10-21T03:25:12+00:00`；
- 配置：`q16-reading-20261021.2`；
- B 输入：`d48b066ad2620d7f1a2e902b2b28e3139390a721`；
- A 输入：`edf125961be9cdc1642652c038d99872b1c8cdc7`；
- basis：`ad8795629c41b67908ba21d0d8039f7a3b5bdbd1eb0155cf75dc375922744a46`；
- current review：`4dd4425140620ef37a289df29206c2f04734c082badd2c73b238851d8031cada`。

run/artifact identity 由 generation 全对象摘要派生；四个 artifact 的时间、配置、实现版本、run ID、artifact ID 和 revision 均被独立消费者绑定。以下两种完整重签变异均被 `IMMUTABLE_GENERATION_IDENTITIES` 拒绝：

- 把四个 artifact 时间改回旧午夜 `2026-10-21T00:00:00+08:00`；
- 改写 SourceBundle artifact identity，并协调重签下游引用。

README 已明确旧固定午夜候选只是历史记录，不能作为实际生成时间。

## v1→v2 内容不变证明

v1 delivery 为 45 个文件，v2 为 46 个文件。

- 42 个内容文件逐字节完全不变：3 张原图、37 张裁片、`current-review.json`、`basis.json`。
- v2 唯一新增文件：`generation.json`。
- 仅有三个既有文件改变：`bundle.json`、`delivery.json`、`pending-review.json`。
- `delivery.json` 的变化仅为 generation 摘要和新 graph 引用及其派生 pending 摘要。
- `pending-review.json` 的变化仅为新 graph 引用。
- `bundle.json` 在规范化 generation 派生的 artifact/run/time/hash/ref 和 producer 版本字段后，SourceBundle、EvidenceBundle、QuestionGraph、CheckReport 的业务语义完全一致。
- 37 个 region、26 个 fragment、4 个 question/task、4 个 answer relation 均逐对象相等；题目、任务、配答、坐标、文字、角色、reading order、共享材料、11 公式槽和 6 个 null 空均未改变。
- bundle evidence 与 policy 逐对象未变。

因此 v2 是时间/身份、精确闭包和 reading-order 诊断的受控修复，没有借修复改写内容候选或来源。

## 独立对抗结果

1. 额外合法 SourceBundle：`READONLY_ARTIFACTS`，拒绝。
2. 重签后的旧午夜 artifact 时间：`IMMUTABLE_GENERATION_IDENTITIES`，拒绝。
3. 重签后的不匹配 artifact identity：`IMMUTABLE_GENERATION_IDENTITIES`，拒绝。

三项均实际通过固定 A C01 加 v2 B 独立核验链，不是只调用生产者自检。

## 证据边界

- 模型目视：18 项 source recheck，仍不是人工 gold。
- 结构/字节：v2 摘要、清单、A blob、像素、C01、重放、读回和差量均独立通过。
- 独立人工：18 项仍 pending，0 项 approved。
- A 自行接收：本轮使用固定 A 原字节只读消费，不代表 A owner 接收或共同验收。
- 业务：4 个关系继续 `UNRESOLVED`，PRE_APPLY 继续 `HOLD`；章节分母未知。
- 网站请求、标注写入、OCR、付费模型、计划、目标、派发和历史成功模拟均为 0。

## 实际命令

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\textbook-annotation-assistant\handoffs\b\46007447\B-46007447-Q16-reading-C01-v2-HOLD-2026-10-21.zip

python -X utf8 C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16-reading-handoff-v2-audit-20261021\replay.py --out C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16-reading-v2-replay-audit-20261021

python -X utf8 C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16-reading-handoff-v2-audit-20261021\tools\consume_q16_reading_a.py --a-source C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16-reading-handoff-v2-audit-20261021\consumer-a --pins C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16-reading-handoff-v2-audit-20261021\consumer-pins.json --delivery C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16-reading-handoff-v2-audit-20261021\delivery --out C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16-reading-v2-direct-a-receipt-20261021.json

python -X utf8 -m unittest tests.test_q16_reading_delivery -v

python -X utf8 C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16_reading_v2_delta_audit.py --old-package C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16-reading-handoff-audit-20261021 --new-package C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16-reading-handoff-v2-audit-20261021 --out C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\outputs\q16-reading-v2-independent-delta-20261021.json
```

## 本会话 v2 产物

- `work/q16-reading-handoff-v2-audit-20261021/`：安全解包副本。
- `work/q16-reading-v2-replay-audit-20261021/replay-receipt.json`，SHA-256 `95c00652af35df08fe18bbc474c7a5516731640216cdce5d4e38a3d5e1e081e4`。
- `work/q16-reading-v2-direct-a-receipt-20261021.json`，SHA-256 `db420de86d113bf1a86f14522a87eefe59b465d845f91750a2b93e32b5fd5f71`。
- `work/q16_reading_v2_delta_audit.py`，SHA-256 `a3053ad60803e680c61e0693b544d528dfc34e7ebf28710dc419740fde2acd9e`。
- `outputs/q16-reading-v2-independent-delta-20261021.json`，SHA-256 `04c0a3b705b56ae9532ffc50228e26228046e3a0d80d33ab417c1e150b8d561a`。

旧版阻断报告继续保留，不被 v2 覆盖。v2 当前未发现剩余技术发布阻断，可按固定离线 HOLD 包发布；任何后续字节变化必须重新冻结 ZIP、bundle 与 generation 摘要并重新接收。
