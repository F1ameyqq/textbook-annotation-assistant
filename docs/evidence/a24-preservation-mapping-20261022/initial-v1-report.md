# A24 历史旧题原件保全候选 v1

## 结论

**OFFLINE_HISTORICAL_ORIGINAL_PRESERVATION_IMPLEMENTED / CURRENT_CODEC_UNCHANGED / HOLD**

本候选在 `source-readiness-v2` 的独立副本中只新增两个文件：

- `src/annotation/runtime/live_pilot/historical_preservation.py`
- `tests/a24_historical_preservation/test_historical_preservation.py`

没有修改现有 natural/complete codec、profile、准入门或写入路径。它解决的是“历史原件字节与完整记录如何独立保全”的旁路证据层，不代表现有 natural codec 的完整 raw/extra 保全缺口已经修复。

保持：

- `schema_profile=None`
- `canonical_question_id=null`
- `write_allowed=false`
- 当前完整性与写入资格：HOLD
- 共享 B 基线 `16b2c6b`：未修改、未 commit

## 固定输入

只读历史原件：

`C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\a24-takeover-20261022\historical-download-export-20261022\46007447_paper_questions.jsonl`

- 11625 bytes
- SHA-256 `02a8aaae2bc907649a03f3676806a02da103e0b487fb43f7e187b29a67fc7a8c`
- 19 条真实历史记录
- 每条 19 个原字段
- `doc_id/tihao` 均为空，不能提供 canonical ID

## 实现的保全层

### 字节与结构

读取器要求调用方同时给出期望 SHA-256 和字节数，并在读正文前拒绝：

- 非普通文件；
- 软链接或 Windows reparse point；
- 非小写 64 位十六进制 SHA；
- 字节数或 SHA 不一致；
- UTF-8 BOM、非法 UTF-8；
- 空行/非 object 行；
- 重复 JSON key；
- NaN/Infinity。

每条记录保留：

- 完整解析后的 dict，不做字段投影；
- 原始行跨度 `raw_span`，包含原换行；
- 不含换行的原始 record bytes；
- source SHA、行号、byte offset、span/record length；
- span SHA 和 record SHA；
- 原始换行类型；
- 基于 source/行号/offset/span SHA 的 `line_identity`；
- 基于完整 dict（包括 unknown extra）的 `content_fingerprint`。

`reconstruct_bytes()` 必须逐字节重建源文件。所有字段、未知字段、嵌套 null/空值、HTML/TeX 字符串和 option 数组顺序均通过完整记录副本保留。

### 公开保全清单

公开清单仅含：

- 文件 SHA/长度/表示；
- 行号、byte offset/length、逐行哈希；
- 行身份、内容指纹；
- 字段名。

不含题文、答案、选项内容、账号或本机私有源路径。

### 有证据类型的身份候选账本

每条历史记录只生成两种基础局部候选：

- `SOURCE_LINE_LOCAL_CANDIDATE`
- `CONTENT_FINGERPRINT_LOCAL_CANDIDATE`

可选 DOM 关系只接受 `DOM_DATA_KEY_LOCAL_CANDIDATE`，并要求来源行、候选值和证据 SHA。输出始终：

- `canonical_question_id=null`
- `selected_candidate=null`
- `write_allowed=false`

一行对应多个 DOM key，或一个 DOM key 对应多行时，状态为 `HOLD_AMBIGUOUS_LOCAL_MAPPING`，不会自动选择。带 `canonical_question_id` 等越权字段的“身份伪装”输入因 schema 不精确而拒绝。

当前实际 19 条没有逐题 DOM join 证据，因此账本只有行号/内容指纹局部候选：

- 19 个不同 line identity；
- 19 个不同 content fingerprint；
- 19 条均为 `HOLD_LOCAL_CANDIDATES_ONLY`；
- canonical 非空数量 0。

行号与内容指纹均不是平台身份：换一个 export 排序或正文变化都可能改变它们。

## 聚焦回归

执行命令：

```powershell
$root='C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-content-sol56\work\a24-schema-readiness-20261022\a24-source'
$env:PYTHONPATH="$root\src"
$env:PYTHONDONTWRITEBYTECODE='1'
$env:A24_HISTORICAL_EXPORT_PATH='C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\a24-takeover-20261022\historical-download-export-20261022\46007447_paper_questions.jsonl'
& 'C:\Users\LIHAOYANG\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s "$root\tests\a24_historical_preservation" -p 'test_historical_preservation.py' -v
```

结果：`Ran 5 tests in 0.034s`，`OK`，退出码 0。

| 回归 | 结果 |
|---|---|
| 真实 19 条逐字节重建 | PASS |
| 真实 19 条独立 JSON 解析值逐条相等 | PASS |
| 全字段/unknown extra/嵌套 null/HTML/TeX/option 顺序 | PASS |
| 错误 SHA | 拒绝 `HISTORICAL_SOURCE_BYTES` |
| 文件字节篡改 | 拒绝 `HISTORICAL_SOURCE_BYTES` |
| 重复 JSON key | 拒绝 `HISTORICAL_JSON_DUPLICATE_KEY` |
| identity 输入夹带 canonical 字段 | 拒绝 `IDENTITY_EVIDENCE_SCHEMA` |
| 多对多 DOM 候选 | HOLD，canonical/selection 均为 null |

未重跑旧 suite 或 activation。

## 补丁与制品

固定补丁：

`C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-content-sol56\outputs\a24-historical-preservation-20261022\a24-historical-preservation.patch`

- 15895 bytes
- SHA-256 `d9ade078140df02a7da3473e3031cc7c801474b17dba5c0d1561cd04d1c73bdf`
- 对 `source-readiness-v2` 执行 `git apply --check --whitespace=error-all`：退出码 0

新增源码：

- `historical_preservation.py`：8500 bytes，SHA-256 `6d2327a4a570e65666ae159d1196f9d0ec2643f9e07dbd0e8abab65098653c0a`
- `test_historical_preservation.py`：6477 bytes，SHA-256 `6f314550f01fd29211f1a905bc29a602b2ded0c1f0bbe9089ad69c4855a5ba94`

公开制品：

- `a24-historical-original-preservation-manifest-20261022.json`
  - SHA-256 `47b4917e909abaa690d2cc7f80574369c905b6de001136f8e469edc131f22293`
- `a24-historical-identity-candidates-20261022.json`
  - SHA-256 `1905f6367813ed714a18fc0a8bf0153b8f33a814c2a53fe1ae0608a2e3cc2276`

质量会话 `01a148fa-5879-7720-8246-267025b6be31` 已收到固定补丁路径、哈希、运行命令和独立复验边界。

## 明确保留的限制

1. 这是独立历史原件保全层；现有 natural codec 仍只输出其现有 raw hash/投影，未自动改用本层。
2. 没有当前 fresh export、权威 catalog 或完整性证明。
3. 没有 canonical question/frame/rect ID。
4. 没有把 `tixu`、行号、内容指纹或 DOM key 晋升为权威身份。
5. 没有五区语义映射、metadata/profile 合成或保存授权。
6. 当前实际账本没有 DOM 逐题候选；即使未来加入，局部候选仍不会自动成为 canonical。
7. 私有正文仅在运行时内存中用于校验，未进入补丁、公开清单或报告。
