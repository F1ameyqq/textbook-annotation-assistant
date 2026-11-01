# A24 旧题保全门绕过审计

## 结论

`HOLD_PROFILE_BINDING_GAPS_REPRODUCED`

当前 schema 未绑定入口仍然 fail-closed：`schema_profile is None` 或 `body_admission=CURRENT_SCHEMA_UNBOUND` 时只进入只读采集，返回 `write_allowed=false`、`successors=NOT_RUN`，不会进入 adapter。因此本报告不是“当前已经可以写入”的漏洞声明。

但在“某个 profile 已被绑定”的下一层，复现了 4 个会让不完整或有损投影假通过的缺口。在修复这些门、并用真实只读响应证明实际字段之前，不能把 profile 从 UNBOUND 提升，也不能据合成 metadata 或适配器自填内容声明旧题已完整保全。

## 可复现缺陷

### 1. 空分母可通过

把 observation 标为 `complete=true/read_status=OK`，保留一个目录但令 questions、frames、question_content、frame_projections 全为空，`global_order()` 会返回 `0`。

这说明当前门验证的是“这些投影之间自洽”，不是“它们确实覆盖平台完整旧题目录”。不能用历史 22 题/68 框硬编码修复；应绑定独立权威 catalog 的当前成员集合或计数。

### 2. 非字符串 ID 与自填正文结构可通过

`decode_complete_export()` 接受以下互相自洽输入：

- `platform_question_id=null`；
- `rect_ids=[null]`；
- `parts=[null]`；
- `question_info={}`；
- 五区键齐全但值全部为 `null`；
- 同一文本中自带 metadata，声明上述题 ID 与 `complete=true`。

因此“有唯一 metadata + 五区键齐全”不足以证明存在有效的旧题身份或正文。真实旧区为空可以合法保留，但平台 ID 至少应为非空、无首尾空白的字符串；正文的真实性应通过原始记录绑定而不是猜测内容字段。

### 3. 未投影的 frame extra 字段变化不可见

同一个原始 frame 记录仅把 `business_extra` 从 `A` 改为 `B`。当前 declarative projection 只抽取 ID、题 ID、type 和 box，两个投影完全相等，`check_preservation()` 随后通过。

旧题正文的 natural codec 已保留整条 raw record 的哈希，complete codec 已保留 `raw_record`；但 question/frame/directory 的 snapshot projection 没有同等的整条原始记录哈希，因此未知或漏配字段不属于保存前后分母。

### 4. many-to-one identity alias 可通过

`project.lookup` 可把两个不同原始 ID `Q-RAW-A` 与 `Q-RAW-B` 都映射为 `q-old`。保存前后原始身份已变化，但投影身份相同，`check_preservation()` 通过。

identity 字段目前没有被限制为直接 `from`，也没有要求 lookup 映射单射。只要 profile 将 identity 归一化，就可能隐藏原始 ID 变化。

## 已正确拒绝的对照项

- 重复 frame ID：`TARGET_IDENTITY_DUPLICATE`。
- 缺少第五区：`EXPORT_QUESTION_COVERAGE`。
- natural export 中未映射 extra 字段变化：由于整条 `raw_record_hash` 改变，拒绝 `OLD_QUESTION_CONTENT_CHANGED`。

因此现有门并非整体失效；缺口集中在分母权威性、身份类型/来源和 snapshot 未投影字段。

## 建议的最小差量

不为未知平台猜字段，只增加通用 fail-closed 约束：

1. 对旧 `platform_question_id`、`platform_frame_id`、`rect_id` 统一要求非空、无首尾空白字符串；snapshot 与两种 export decoder 同时执行。
2. identity 输出禁止 `literal` 和 many-to-one `lookup`；如果平台确实需要规范化，则同时保留可信 raw identity，并在保存前后比较 raw 与 canonical 两者。
3. 对每个投影后的 question/frame/directory 增加由适配器对完整原始记录计算的可信 `raw_record_hash`，保全比较必须包含该哈希。这样无需预知 extra 字段名称。
4. complete export 的 `state_version`、natural export qualification 的 `state_binding` 必须与当前 snapshot 的 catalog/version 绑定比较，不能只检查非空。
5. 空或缩减分母只有在独立权威 catalog 明确证明其成员集合时才可接受；不要把历史 22/68 当当前常量。
6. 在真实只读输入提供字段路径和状态绑定之前，继续 `CURRENT_SCHEMA_UNBOUND/HOLD`，不创建 guessed adapter。

上述建议是差量设计，不是已实施补丁；真正字段路径等待来源成员的真实响应。

## 复现范围

使用 v2-final 重建的 effective tree 和规定 bundled Python，仅运行 `tools/a24_preservation_bypass_audit.py`。4 个缺陷均稳定复现，3 个拒绝对照均通过；没有浏览器、网络、API、模型或 live authority 调用，也没有修改共享 B 仓库。
