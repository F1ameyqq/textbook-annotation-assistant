# A30 Union17 综合文字来源调整独立审查

结论：`REWORK_UNION17_INVALID_PRECISION_INPUT_SUBMITS_STALE_BBOX`。发现一项新增普通UI语义反例，按首错停止；后继新增后端回调链、定位消息及新全16 head/计划/launch 未接受。accepted14的既有限定接受继续保留，不重跑；15/16仅保留历史，不分别验收。

## 输入与差异

- 固定输入 `D:/1800-private/a30-integrated-flow-r1-fixed-20261024-17`；独立副本 `D:/1800-private/a30-union17-independent-20261024-01/input`。
- manifest `f44d63bedc8069f88628e490adcb0a09b26616bbc2f07ffb0e584ea50c881ad0`；report `bcb7ce5bd4c1c8ca3f2a93e08e7a8d0b3d879dc60a139b2357535f9c6762d68b`。
- 245源码、131证据及3顶层文件，共379项，哈希与声明匹配，结束379/379未变。accepted14的109项证据嵌套副本逐字节未变。
- 相对accepted14：3个产品文件改变（review.py、review_ui.js、native_plan.py），3个已有检查文件改变，新增1个精确输入检查文件；238个父级源码未变，无删除。未运行旧suite、作者新测试或中间版本。

## P2：无效精确输入仍可提交旧bbox

位置：冻结 `app/src/annotation/recognition/review_ui.js` 的488–495行及553行起保存回调。

数字输入事件先验证四个字段，遇到空值/非整数/越界等直接return；清除 `checked` 和更新 `boxBinding` 的逻辑位于验证之后。故已有有效框与已勾选确认不会在无效输入时失效。保存回调检查旧box、旧boxBinding和checked，却不重新验证当前四个可见数字字段。

独立新用例直接执行冻结普通 `renderRegionBinding`，输入来自accepted14真实普通adapter产生的合成state；仅复用状态，不重跑14检查。正常进入答案文字框精确调整后：

1. 可见初始原像素字段 `[48,255,390,330]`。
2. 将上边界输入254（向最初原框内回调1px），勾选“文字完整”。
3. 清空上边界；可见字段为 `[48,"",390,330]`，完整性勾选仍为true。
4. 点击“保存文字来源范围”，产生1个 `/api/bind-region` 模拟请求，bbox仍为 `[48,254,390,330]`，并带 `source_checked=true` 和 `text_complete_checked=true`。

预期无效可见输入时请求数为0；实际为1，原执行exit1。发送的是旧有效框，且仍宣称刚才已核对完整，与用户当前可见输入不一致。新数字输入会使微调失误静默保存，正影响本次用于修复1px截字的客户路径。

这次没有画布拖拽或坐标缩放假设，四个input值直接触发真实输入监听器；不是前轮reviewer缩放fixture错误。完整普通函数保留，网络请求只被记录为合成对象，没有真实HTTP、GUI、平台、OCR、模型或客户工作区修改。首个反例出现后没有继续试其他无效值、没有后端重放，也没有修改产品。

## 所需最小修正

任意数字字段变化应先撤销旧完整性确认；无效字段应明确标记为不可提交。保存时须重新校验当前四字段，并确保提交bbox与当前显示的有效整数坐标一致。不能仅取消勾选后仍允许用户在无效字段下重新勾选、发送旧框。保留原bbox/历史和原失败证据，不扩大来源边界、修改旧成功项或削弱生产重叠保护。

修订后只需续审本新增输入一致性反例及未完成差异，不重跑accepted14已通过项。原框内回调的来源链保护、错误定位消息及新Q7实际head/完整计划/launch仍需有限核验；作者累计backend3/UI2声明不能替代本次独立反例。

## 保留状态

原full16-ui-01 Q7与native27重叠REWORK、作者launch01只读预检失败、UI05过窄未确认历史均保留。本轮没有使任何平台权限消耗或激活。`CUSTOMER_READY=false`，12首次保存/独立读回、完整16原生导出及最终交付仍未由本审查成立。旧九题、成功四题、spent轮次、FAIL/UNKNOWN和 `1800-a PAUSED` 不变。

原始独立失败见 `precision-input-result.json`、`precision-check-execution.json` 和检查脚本；固定清单绑定全部审查输出。
