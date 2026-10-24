# A24 最小只读适配 frozen-v2 独立复验

日期：2026-10-22

## 结论

- **离线历史真实样本：PASS。** frozen-v2 补丁能在已采用历史保真层的基线上独立应用；一条 CLI 命令处理真实 19 条 JSONL，输出与内容侧 final 产物逐字同哈希。
- **身份与写入边界：PASS。** `canonical_question_id` 始终为 `null`，`write_allowed=false`；行号、`importShitiID`、内容哈希和伪造的 `canonical_question_id` 字段均未被提升为平台身份。
- **现行题体闭环：HOLD / NOT RUN。** v4 仍为 `NOT_OBTAINED`；本轮只绑定 v3 的 9 条可见 DOM 校验错误，所有底层字段状态保持 `UNOBSERVED`。没有真实 current body 输入，也没有浏览器或平台写入。
- **发现 1 个上线前工程缺口。** 错误的 precheck 会正确失败，但在失败前已经写出两个私有半成品文件。它不推翻本次成功样本的 PASS，但应在作为稳定单命令入口前修复。

## 冻结输入与补丁

- 基线：`source-historical-preservation-reviewed-20261022`；本机 `rg --files` 实测 522 个文件。
- frozen-v2 补丁：19,157 bytes；SHA-256 `3fb2cbcfbed76a4f4c7b29eb0761d37a2ff8a9a7de6c00fce1ee5113454d654b`。
- 使用 `git -c core.autocrlf=false apply --check` 与 `apply` 均成功。
- 应用后 `readonly_trial.py`：12,642 bytes；SHA-256 `1ead1518959897529eb0ae6ea2a8c0f946158c6d299875d35204024117908fa4`。
- 应用后 `test_readonly_trial.py`：5,604 bytes；SHA-256 `ea3a84ad8978d6e048cde0a2277cf010b8cd1705de6d53900191a3d1e9b8a727`。
- 目标树实测 524 个文件，仅比基线新增上述两个文件；历史保真层未改。

## 真实样本运行

输入 `46007447_paper_questions.jsonl`：11,625 bytes；SHA-256 `02a8aaae2bc907649a03f3676806a02da103e0b487fb43f7e187b29a67fc7a8c`。

CLI 返回：

```json
{"status":"READ_ONLY_LOCAL_ROUNDTRIP_COMPLETE_IDENTITY_UNBOUND","source_type":"HISTORICAL_EXPORT","record_count":19,"write_allowed":false,"readback":"PASS_EXACT_LOCAL_READBACK"}
```

独立 frozen-v2 产物：

| 文件 | bytes | SHA-256 |
|---|---:|---|
| `private/records.full.jsonl` | 11625 | `02a8aaae2bc907649a03f3676806a02da103e0b487fb43f7e187b29a67fc7a8c` |
| `private/records.adapted.json` | 29497 | `50107c9153df3ae77e75bef10aef4478dd44c5381bf161099843afe0bd547576` |
| `public-summary.json` | 35400 | `de13b0ef2cbcbc1aad71b8ba702bf915a5eb3ed85e41eb962152ca788fb9b4d5` |
| `readback-receipt.json` | 492 | `52ac92a936c669fb4fdf8e48b16965030cc5c2c28af7d539c0bdee77bcbabe38` |

四个哈希与内容侧 `historical-19-final` 完全一致。

## 独立读回

独立检查器不导入被测模块，直接从磁盘解析源文件与四个产物。结果：

- 19 条 `records.full.jsonl` 与原输入逐字节相等。
- 每条 mapped value、extra value、空值和原字段顺序均可无损重建。
- `MISSING / NULL / EMPTY / PRESENT` 独立重算一致；空白字符串、`0`、`false` 不被错判为 EMPTY。
- 所有历史 adapted record 均保持 `HISTORICAL_EXPORT`，v3 `CURRENT_DOM` 诊断作为独立对象存在，没有自动 join。
- v3 的 9 条错误顺序和值完全一致；`importShitiID` 保持字符串，底层 missing/null/empty 均为 `null`，状态为 `UNOBSERVED`。
- public record 只含行号、哈希/字节引用、字段名和字段证据摘要，不含 question/option/answer/extra 的业务值。
- receipt 中三个输出哈希与磁盘文件一致。

独立读回结果文件 SHA-256：`d9b79bbd840e052c5cbea6556740a2361501468f8b6401a2087a995379e8a7c6`。

## 测试与最小负例

- frozen-v2 新测试：5/5 PASS。
- 历史保真测试：7/7 PASS，真实 19 条回归已启用、未跳过。
- 错误源 SHA：拒绝，`HISTORICAL_SOURCE_BYTES`。
- `CURRENT_RAW_RECORD` 多记录输入：拒绝，`CURRENT_RECORD_CARDINALITY`。
- 同号 `importShitiID="1"` 与伪造 `canonical_question_id="forged"`：只按 extra data 原样保留；输出 canonical 仍为 `null`，写入仍为 false。
- v3 错误顺序被交换：拒绝，`PRECHECK_ERROR_LEDGER`。
- 分别篡改 full、adapted、public summary 的副本：独立读回均检出，错误分别为 `FULL_BYTES_NOT_SOURCE_EXACT`、`PUBLIC_ADAPTED_REF`、`RECEIPT_PUBLIC_HASH`。

## 唯一修复建议

`run_readonly_trial()` 当前先创建输出目录并写入 `records.full.jsonl`、`records.adapted.json`，然后才调用 `load_precheck_diagnosis()`。当 precheck 无效时，命令失败但遗留这两个私有文件，且原输出目录无法直接重跑。

最小修复：把 precheck 的读取与全部校验移到 `_prepare_output_dir()` 之前；增加一条测试，断言 `PRECHECK_ERROR_LEDGER` 后目标输出目录不存在。成功路径和产物格式无需改动。

## 接受边界

本报告只接受“冻结历史输入的本地只读适配与独立读回”。它不接受或暗示：现行题体已取得、19 条是现行分母、DOM 号是平台题 ID、网页已写入，或业务验收已经完成。
