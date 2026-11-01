# 46007447 Q9 revision 7 独立来源复核

日期：2026-10-17，Asia/Shanghai  
审核对象：`content-revision-plan-6d64c4ba624f332b536c4060` revision 7  
计划文件 SHA-256：`3f939a39dc0fb605f24391b0846f7cf4dc439c7bedf0b35fe102c5b706bcdf07`

## 结论

五处新增 `EDIT_TEXT` 都有实际来源像素支持，并已出现在最终 Q9 正文中：

1. `=400.∴AB=20cm.`：`viewer-173` 底部原图可见结论符号 `∴`。
2. `=464.∵464>400，∴蚂蚁`：`resource-173` 前缀可见 `∵`、比较式、`∴` 和“蚂蚁”。
3. `A—P—B`：像素明确显示字母间为长横线，不是 OCR 的汉字“一”。栅格图不能独立认证具体 Unicode 横线码点，故 `—` 仍只是合理的模型草稿规范化。
4. `∵625<725`：原图明确支持。
5. `，∴一只蚂蚁`：下一行原图明确支持。

没有在这五处相邻文本中发现漏掉的同类因果符号。单位前空格、句点形态和长横线码点属于排版/编码规范化，不能仅凭栅格图提升为精确人工转写。

## 谱系与跨度

- revision 7 payload SHA-256 重算为 `6e789a2b0c6160cd33d9d6849a23d52d0d92578e03f93d8521ca4a3cd081009e`，与声明相同。
- `previous_plan_archive` 与 Q16 revision 6 完全相等；13 个操作快照与计划 payload 完全相等。
- 两张原图 SHA-256 分别为 `a231f024…`、`8380f9a1…`，与声明一致。
- `resource-173-prefix.png` 与原 JPG 的 `[75,72,560,470]` RGB 裁片逐像素相等。
- 五个新 EDIT 与已有 SELECT/EDIT 使用原始 half-open span；同片段上的三组边界分别为 `11–16 / 28–39`、`20–34 / 34–41`、`5–11 / 11–16`，无重叠。

## 最终输出核对

- G07：`content-graph-ceb23a5e1a5ec1fb720922cf` / `fef9a722ee523de46503a4347024ae3887c2da7bac69fe56f8d0355b88407ca1`。
- Check07：`content-check-1f620c205eeb19ba0cfb6124` / `966821338f2d76f32502237cc910c754dbd0e820f3ae822cd5a4ee7d5f6b6ef4`。
- 两个 payload 哈希重算匹配，Check07 精确引用当前 G07。
- 34 题、66 答和 32 个未链接答案不变；questions 与 matching 精确不变。
- 除 Q9 外的 65 个答案在移除派生 ID 与 `plan_ref` 后语义相等。
- Q9 的 33 个原片段、33 个 source line、bbox 和 5 个图像区语义不变；五处目标修订均存在。
- Q16 与 revision 6 语义相等，仍以 `16.解：（1）60 61（2）…` 开头，没有回退。

Check07 当前为 132 issues、`HOLD`、`complete=false`、`transcription_verified=false`、`business_acceptance=false`。相比前版增加的 5 项全部是这五个新操作对应的 `CONTENT_EDIT_DRAFT_UNVERIFIED`；它们正确保留了模型草稿风险，不能解释为内容或人工验收。

独立复核脚本：`work/chapter_quality/audit_q9_rev7.py`。
