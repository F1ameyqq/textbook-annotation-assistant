# Q16 与三个阅读任务 C01/HOLD 独立质量核查

日期：2026-10-21（Asia/Shanghai）
共享仓库输入 HEAD：`d48b066ad2620d7f1a2e902b2b28e3139390a721`
固定 A 标识：`edf125961be9cdc1642652c038d99872b1c8cdc7`
候选 ZIP：`B-46007447-Q16-reading-C01-HOLD-2026-10-21.zip`
结论：**指定摘要的固定 ZIP 离线重放通过；新增直读/核验工具存在发布阻断，整体继续 HOLD。**

## 发布阻断

### P1：直读消费者接受未审核的额外 artifact

`tools/verify_q16_reading_b.py` 将 `bundle['artifacts']` 按 `kind` 压成字典后仅核对 kind 集合，没有核对 artifact 总数恰好为 4。`tools/consume_q16_reading_a.py` 使用同样的按-kind取值方式。因而可以在原 bundle 后追加一个合法、重新封装、但从未进入内容审核的额外 `SourceBundle`；固定 A C01 校验接受它，B 内容核验也忽略它，最终仍返回：

- `status=A_FIXED_C01_READONLY_CONSUMED_HOLD`
- `producer_vs_consumer_full_object_equal=true`
- `decision=HOLD`

复现变异 bundle SHA-256：`e205878796563b46607ec4551bb3dd2ec62388ebc5c1ceca96781761290d650b`。

这不改变本次指定 ZIP 的判断：其外部 ZIP 摘要、145 成员清单和固定 bundle 摘要已经先验核对，因此当前固定字节没有额外对象。但 README 给出的直接消费者命令自身不校验顶层 manifest 或期望 bundle 摘要，不能独立支撑“仅消费已审核对象”的发布声明。

发布前至少应在独立核验器中强制：

- `len(bundle['artifacts']) == 4`，并且四种 kind 各恰好一个；
- `len(bundle['policies']) == 1`；
- `len(bundle['evidence']) == 2`，且 ID 恰为 `ev-current-review`、`ev-basis`；
- 新增“额外 artifact/evidence/policy 必须拒绝”的回归。

### P2：确定性时间与不可变身份语义未声明

`tools/export_q16_reading_b.py` 对四个 artifact 固定使用：

- `created_at = 2026-10-21T00:00:00+08:00`
- `run_id = b-q16-reading-20261021`
- 固定 artifact ID 与 `revision=1`

ZIP 内全部成员时间也统一为午夜。这适合确定性重放，但当前 README、sidecar 和回执未说明该时间是“确定性快照纪元”，不是实际运行生成时刻。更重要的是，如果以后正文、映射逻辑或内容版本变化而继续复用这些 ID/revision/run_id，只改变 `content_hash`，就会形成同一不可变 artifact revision 的跨包冲突。

发布前应二选一：记录真实首次冻结时刻；或明确标注 `created_at` 为非墙钟的确定性快照时间，并把内容/导出器版本纳入 run_id 与 artifact identity，规定任何输出语义变化必须换 identity 或递增 revision。当前回放时间不得描述成实测生成时刻。

## 已通过的固定候选检查

### 摘要、解包与清单

- ZIP SHA-256 与委托值一致：`f96b59dc0bccb171eb43daa03a47478d44452bc1d8eb3e2fffb4800f517c7a93`。
- `delivery/bundle.json` SHA-256 与委托值一致：`e347e6eef8a87a60bcf314816a0b5ff7a9f3cf24b60109891f844d998fd5e39d`。
- ZIP 共 146 个唯一文件：145 个 manifest 成员加顶层 `manifest.json`。
- 无绝对路径、`..`、反斜杠路径、符号链接、重复名或大小写碰撞。
- 145/145 清单路径、字节数和 SHA-256 全部一致；没有漏列或多余成员。
- 91/91 `consumer-a` 文件路径闭合，逐文件大小和 Git blob OID 全部匹配 `consumer-pins.json`。
- 这 91 个字节也与历史固定接收包 `B-46007447-A08-A09-Q4-B-adoption-2026-10-19.zip`（SHA-256 `6a0ead03c95299049c5f113a1de647ef6c28f72703430b80451ccb93775c535b`）中的 `fixed-source/` 完全一致。
- 本机 Git 对象库不含 `edf125…` commit 对象；因此本轮独立证明的是 91 个固定 Git blob 字节及既有固定包的一致性，不把 commit 标签升级为本机重新解析过的 tree 证明。

### 实际 replay 与固定 A 直读

`replay.py` 实际退出 0，回执为 `OFFLINE_FIXED_DELIVERY_AND_A_READBACK_REPLAYED`：

- 重建 45 个交付文件并逐字节等于包内固定交付；
- 固定 A 91 源文件校验通过；
- A 读回回执逐字节等于参考回执；
- 网络与模型导入禁用；
- 未做干净依赖安装或历史全流水线；
- 决策保持 `HOLD`。

固定 A 消费者另行直接运行也退出 0，并确认：

- 4 个题/任务、1 个共享材料；
- 37 个来源区域、26 个语义片段；
- 11 个 Q16 公式诊断槽；
- 6 个未填题目空保持 `null`；
- 18 个模型来源核对与 18 个独立人工待核项目；
- producer/consumer 全对象相等；
- 未运行计划、模拟、派发、业务入口或网站请求；
- `actual_a_owner_acceptance=false`、`independent_human_acceptance=false`、`business_acceptance=false`。

### 现有与新增对抗检查

共享仓库现有 focused suite 实际运行 15/15 通过。

独立新增的四个协同变异均被固定 A + B 内容链拒绝：

1. 同时改写当前正文、bundle 文字、binding、review subject 和所有相关摘要：`FIXED_SOURCE_REVIEW`；
2. 18 项独立核对 subject 整体重排并重签：`INDEPENDENT_REVIEW_BINDING`；
3. 把 OCR 108 行左右两段在任务 2/3 间同时改绑并重签 graph：`RUN_AND_OWNER_BINDING`；
4. 删除任务 3 整图、相应 region/fragment/relation/clue/binding/proof，并完整重签：`NO_OMITTED_OR_DUPLICATE_REGIONS`。

第五个控制组追加未审核额外 SourceBundle 后被错误接受，形成上面的 P1 阻断。

## 证据类型边界

- **模型目视**：18 项 `MODEL_VISUAL_SOURCE_RECHECK`，不是独立人工 gold。
- **结构/字节检查**：本轮独立通过固定摘要、清单、Git blob、像素、C01、重放和读回。
- **独立人工**：18 项仍全部 pending，0 项 approved。
- **A 自行接收**：本轮只是 B 侧使用固定 A 原字节进行只读消费；不代表 A owner 接收或共同验收。
- **业务状态**：4 个关系仍 `UNRESOLVED`，PRE_APPLY `HOLD`；章节分母未知；不执行 A 业务/目标/计划/派发；网站请求、OCR 和付费模型调用均为 0。

## 实际命令

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\textbook-annotation-assistant\handoffs\b\46007447\B-46007447-Q16-reading-C01-HOLD-2026-10-21.zip

python -X utf8 C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16-reading-handoff-audit-20261021\replay.py --out C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16-reading-replay-audit-20261021

python -X utf8 C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16-reading-handoff-audit-20261021\tools\consume_q16_reading_a.py --a-source C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16-reading-handoff-audit-20261021\consumer-a --pins C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16-reading-handoff-audit-20261021\consumer-pins.json --delivery C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16-reading-handoff-audit-20261021\delivery --out C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16-reading-direct-a-receipt-20261021.json

python -X utf8 -m unittest tests.test_q16_reading_delivery -v

python -X utf8 C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16_reading_adversarial_audit.py --package C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\work\q16-reading-handoff-audit-20261021 --out C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\outputs\q16-reading-independent-adversarial-20261021.json
```

安全解包在 Python `zipfile` 中先逐项拒绝绝对路径、`..`、反斜杠、符号链接和大小写碰撞，再写入本会话新目录；共享仓库未被本会话修改、提交或推送，HEAD 仍为 `d48b066…`。

## 本会话产物

- `work/q16-reading-handoff-audit-20261021/`：安全解包副本。
- `work/q16-reading-replay-audit-20261021/replay-receipt.json`，SHA-256 `c5b8284a396045dc969842ef5cc18bc82872e90e0038b67c5d66a3953e71d61f`。
- `work/q16-reading-direct-a-receipt-20261021.json`，SHA-256 `12d8aaa769d653df891a46816ba089ff5713ebc43a86173a6dab252b66ccd242`。
- `work/q16_reading_adversarial_audit.py`，SHA-256 `64fecfef7a697d41e1b831f96d21bc28f72814e357037a6c41a7c466a7a32a5c`。
- `outputs/q16-reading-independent-adversarial-20261021.json`，SHA-256 `6e8a2414d0c19c4d891ca7337bba040fb5d29b4a9245cb8cac379640f9036370`。

在 P1 精确对象闭包和 P2 时间/身份语义修复并重新冻结 ZIP 摘要前，不建议发布新增消费者/核验器；当前指定摘要候选可保留为已通过的离线固定字节证据，不能升级为业务或 A 接收通过。
