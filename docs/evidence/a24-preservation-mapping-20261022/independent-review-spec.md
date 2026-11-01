# A24 原件保全与稳定 ID 映射：独立复验规格

## 当前结论

`REVIEW_SPEC_READY_PATCH_PENDING`

内容成员补丁尚未交付，因此当前只封存独立验收标准、反例和基线结果，不对未见补丁作接受判断。

用户给定 B 基线为 `16b2c6b`，但本环境中的 `source-readiness-v2` 是无 `.git` 的抽取目录，且本机不存在 `D:/1800`，所以该 commit 目前只能标为用户声明、不能标为本机已验证。归档校验器因没有 Git 对象与根 `manifest.json` 退出1；这是输入形态限制。隔离树当前 `wire.py` SHA-256 为 `64885d7ac5d91d5351231a803ffeab4badb1b55528057a6abde1c03ac6131116`。

只运行了有限相关的 `tests/a24_schema_readiness/test_schema_readiness.py`：14项通过、0失败、0错误，退出码0。没有扩跑旧套件。

## 最小无损保全完成标准

1. 解析前先核对历史 JSONL 的11,625 bytes与 SHA-256 `02a8aaae2bc907649a03f3676806a02da103e0b487fb43f7e187b29a67fc7a8c`。
2. 保留整文件原始字节，或逐行保留可复原的原始字节；19条记录的先后顺序不得改变。
3. 顶层字段顺序、列表顺序、精确字符串、Unicode、空白、数字类型、空字符串、空列表、`null` 与缺字段必须可区分且可复验。
4. JSON 重复键必须在 last-wins 构造前拒绝，不能静默吞掉前值。
5. 所有未知 extra 字段和值必须保留；只有 `raw_record_hash` 而没有原值，不构成无损保全。
6. 错误摘要应稳定、去敏，只给错误码、行号与字段名，不复制题干或其他业务正文。
7. 原件保全通过不得自动提升当前完整性、平台身份、写资格或平台验收。

## 最小映射账本完成标准

- 每条记录至少绑定源文件 SHA、原始行 SHA 和源顺序。
- 没有同状态权威服务端响应、证据引用和成员关系前，canonical `platform_question_id` 必须为 `null/UNBOUND`。
- `tixu`、DOM `data-key`、`rectIndex`、行号、可见题号、内容哈希和内容相同都只能记录为观察值，禁止升级为 canonical ID。
- 多候选、重复或冲突必须落为 `AMBIGUOUS/REJECTED`，不能“取第一个”。
- 不能用历史19条与当前22个可见标签推导当前分母或“缺3题”。
- 账本默认 `write_allowed=false`，不得生成 authority、activation、signature、receipt 或保存许可。

## 必测反例

| 编号 | 反例 | 必须结果 |
|---|---|---|
| N01–N04 | 分别把 `tixu`、DOM key/index、行号、正文/内容哈希当 canonical ID | 拒绝身份升级 |
| N05/N14 | 一行出现重复 JSON key，或解析器静默 last-wins | 去敏拒绝，不泄露正文 |
| N06 | 丢弃或重命名未知 extra 字段 | 拒绝有损保全 |
| N07 | 合并 missing/null/空串/空列表 | 拒绝有损保全 |
| N08 | 归一化空白、Unicode、列表顺序或记录顺序 | 拒绝有损保全 |
| N09 | 一条源记录对应多个权威 ID | `AMBIGUOUS_HOLD` |
| N10 | 多条源记录对应同一权威 ID | `DUPLICATE_ID_HOLD` |
| N11 | 用19与22推断恰好漏3条 | 拒绝分母推断 |
| N12 | 保全输出令 `write_allowed=true` 或生成授权 | 拒绝伪造授权 |
| N13 | 源文件字节数或 SHA 不符 | 拒绝源绑定 |

## 内容补丁复验清单

收到补丁后只在独立副本应用，并核查：

- 真实19条原件全部字段、精确字符串、顺序、空值与 extra 保持；
- 错误摘要不泄露正文；重复键、歧义与权威身份伪装负例全部拒绝；
- 默认 `write_allowed=false`，不生成任何授权；
- 只运行补丁直接相关回归，逐项保存命令、退出码、失败与差量；
- 任何实现通过仍只代表工程层，不替代内容人工验收或平台保存签收。

## 项目四层短评

- 工程模拟：现有 schema-readiness 有界回归14/14通过，说明部分拒绝门与结构路径可工作；不证明真实平台 schema、完整分母或业务接受。
- 实际数据：已固定2026-10-16历史19条 JSONL及2026-10-22有限 DOM 观察；没有 current fresh 原始整书导出、canonical 题 ID、完整 frame/catalog/state binding。
- 内容验收：显式校正内容有既有限定接受记录，但本轮未重验正文，也没有人工最终批准；历史19条自身不能证明五区完整。
- 平台保存：实际 save、refresh、独立 reopen 均为 `NOT_RUN`，当前 `write_allowed=false`；任何本地 PASS 都不能替代平台回执。
