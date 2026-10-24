# 46007447 Q16／阅读材料 C01 来源核查报告

日期：2026-10-21
核查方式：仅本机、只读；未修改共享仓库、既有候选包或平台状态；未打开浏览器、未调用网络／OCR／付费模型。

## 结论

本次固定交付包通过来源绑定与内容回读核查，但结论仍为 **HOLD**。

- ZIP SHA256 与给定值一致：`f96b59dc0bccb171eb43daa03a47478d44452bc1d8eb3e2fffb4800f517c7a93`。
- `delivery/bundle.json` SHA256 与给定值一致：`e347e6eef8a87a60bcf314816a0b5ff7a9f3cf24b60109891f844d998fd5e39d`。
- 只读验证器返回 `SOURCE_BOUND_CONTENT_READBACK_OK`：4 个问题候选、1 份共享材料、37 个来源窗口、26 个片段、11 个 Q16 公式诊断窗口；18 项模型来源检查仍全部等待独立人工确认，决策为 `HOLD`。
- Q16 的**完整题面**（题干及三个小问）均在 `viewer-15`，没有跨页；其三个答案行与 11 个公式诊断窗口在 `viewer-173`。
- 阅读任务 1 在同一张 `viewer-13` 上由左栏底部接到右栏顶部，属于**同页跨栏**，不是跨页；图谱中的 `cross_page=false` 正确。
- 阅读材料没有印刷主问题号；三个 `(1)(2)(3)` 是该材料下的子任务标签。三个阅读任务的 `printed_number=null` 正确。
- 当前 37 个窗口均可由固定来源图重裁得到；不过坐标仍是来源窗口，不是平台框，来源／置信状态仍为 `HISTORICAL/UNCERTAIN`。
- 本包只证明 Q16 加三项阅读任务的限定范围，不证明第一章页源齐全、章节题目总数完整、人工验收或平台接收。

## 固定输入与来源一致性

### 交付包

| 对象 | SHA256 | 结果 |
|---|---|---|
| `B-46007447-Q16-reading-C01-HOLD-2026-10-21.zip` | `f96b59dc0bccb171eb43daa03a47478d44452bc1d8eb3e2fffb4800f517c7a93` | 与给定值一致 |
| `delivery/bundle.json` | `e347e6eef8a87a60bcf314816a0b5ff7a9f3cf24b60109891f844d998fd5e39d` | 与给定值一致 |

### 三张来源图

| 资产 | 尺寸 | SHA256 | 与八来源包对照 |
|---|---:|---|---|
| `viewer-13` | 1219×1691 | `997b37d35fca57f73ab71e53f6721be145d10c436deab5fab38bf1ae0d31dc1e` | 与 `assets/46007447_page_12.jpg` 逐字节一致 |
| `viewer-15` | 1219×1703 | `7c1a4afec69a94371fa31b6111969ca3d6ec39d7d7c6b1c73764f90316a610dd` | 与 `assets/46007447_page_14.jpg` 逐字节一致 |
| `viewer-173` | 1148×1621 | `a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be` | 与 `assets/46007447_viewer_173.jpg` 逐字节一致 |

对照用八来源包 SHA256：`ec77d52ebcf25b3fec64579f63400c010cc08a623d71e20506e6ed46125ea695`。

包内页码映射为 `viewer-13 / printed 5`、`viewer-15 / printed 7`、`viewer-173 / printed 25`，但三项映射状态均明确为 `UNCERTAIN`，不得据此推出全书稳定页码偏移。

## 题目连续性核查

### Q16

`viewer-15` 右栏内的四个题面窗口依次覆盖题号 16、题干和三个小问，至 `y=855` 结束；同一来源页内闭合：

| 内容 | 来源窗口 `[x1,y1,x2,y2]` |
|---|---|
| 题干 | `[627,120,1142,348]` |
| 小问 1 | `[665,350,1140,430]` |
| 小问 2 | `[665,432,1140,779]` |
| 小问 3 | `[665,780,1140,855]` |

答案位于 `viewer-173` 右栏的三个连续行窗口：

- `[579,263,1084,299]`
- `[579,299,1084,334]`
- `[579,334,1084,367]`

11 个公式窗口嵌套在这三个答案行中，属于诊断性细分，不是重复答案。题面中的装饰性 “A” 徽标被保留为 `SOURCE_DECORATION_RETAINED`，不应解释为选项 A、小问标记或答案。

### 阅读材料与三个任务

材料标题、正文和图均在 `viewer-13`。任务 1 从左栏底部 `[56,1393,582,1596]` 开始，并在同图右栏顶部 `[655,617,1140,807]` 继续；因此是同页跨栏。任务 2、任务 3 随后位于右栏，分别为 `[621,810,1140,890]`、`[621,1135,1140,1378]`。

材料共享窗口共 8 个，三个任务各自引用同一份共享材料；没有为材料虚构印刷主题号。

## 图形范围

| 图形 | 来源 | 来源窗口 `[x1,y1,x2,y2]` | 核查边界 |
|---|---|---|---|
| 图 1（赵爽弦图） | `viewer-13` | `[431,838,573,1000]` | 当前来源窗口覆盖图形；仍保留人工范围确认 |
| 图 2（三联图、箭头及图注） | `viewer-13` | `[137,1177,504,1335]` | 当前来源窗口覆盖三联图；仍保留人工范围确认 |
| 任务 3 答案图 | `viewer-173` | `[225,1118,372,1240]` | 既有独立像素／阈值检查未发现底部裁切，但这不等于人工验收，`FIGURE_EXTENT_UNVERIFIED` 继续保留 |

## 37 个来源窗口清单

汇总：`viewer-13` 12 个、`viewer-15` 4 个、`viewer-173` 21 个；文本 23 个、图像 3 个、公式 11 个。

| # | region_id | 来源 | bbox | 类型／归属 |
|---:|---|---|---|---|
| 1 | `region-q16-stem` | viewer-15 | `[627,120,1142,348]` | text／Q16 |
| 2 | `region-q16-task1` | viewer-15 | `[665,350,1140,430]` | text／Q16 |
| 3 | `region-q16-task2` | viewer-15 | `[665,432,1140,779]` | text／Q16 |
| 4 | `region-q16-task3` | viewer-15 | `[665,780,1140,855]` | text／Q16 |
| 5 | `region-automatic-row-3c07fe7650f2739d493c9ee9` | viewer-173 | `[579,263,1084,299]` | text／Q16 答案 |
| 6 | `region-automatic-row-702e7841f43c03ec98356f12` | viewer-173 | `[579,299,1084,334]` | text／Q16 答案 |
| 7 | `region-automatic-row-a309aab8fb02f91a26d8a024` | viewer-173 | `[579,334,1084,367]` | text／Q16 答案 |
| 8 | `region-reading-title` | viewer-13 | `[275,553,930,598]` | text／共享材料 |
| 9 | `region-reading-intro` | viewer-13 | `[57,621,577,654]` | text／共享材料 |
| 10 | `region-reading-body1` | viewer-13 | `[66,682,576,832]` | text／共享材料 |
| 11 | `region-reading-body2` | viewer-13 | `[66,835,432,1023]` | text／共享材料 |
| 12 | `region-reading-figure1` | viewer-13 | `[431,838,573,1000]` | image／共享材料 |
| 13 | `region-reading-body3` | viewer-13 | `[66,1028,576,1175]` | text／共享材料 |
| 14 | `region-reading-figure2` | viewer-13 | `[137,1177,504,1335]` | image／共享材料 |
| 15 | `region-reading-task-heading` | viewer-13 | `[53,1351,130,1390]` | text／共享材料 |
| 16 | `region-reading-task1-left` | viewer-13 | `[56,1393,582,1596]` | text／任务 1 |
| 17 | `region-reading-task1-right` | viewer-13 | `[655,617,1140,807]` | text／任务 1 |
| 18 | `region-task1-line1` | viewer-173 | `[54,1012,282,1044]` | text／任务 1 答案 |
| 19 | `region-reading-task2` | viewer-13 | `[621,810,1140,890]` | text／任务 2 |
| 20 | `region-task2-line1-tail` | viewer-173 | `[282,1012,548,1044]` | text／任务 2 答案 |
| 21 | `region-task2-line2` | viewer-173 | `[54,1044,548,1084]` | text／任务 2 答案 |
| 22 | `region-task2-line3-prefix` | viewer-173 | `[54,1084,228,1104]` | text／任务 2 答案 |
| 23 | `region-reading-task3` | viewer-13 | `[621,1135,1140,1378]` | text／任务 3 |
| 24 | `region-task3-line3-suffix` | viewer-173 | `[228,1084,548,1104]` | text／任务 3 答案 |
| 25 | `region-task3-line4-continuation` | viewer-173 | `[54,1104,154,1124]` | text／任务 3 答案 |
| 26 | `region-task3-diagram` | viewer-173 | `[225,1118,372,1240]` | image／任务 3 答案 |
| 27 | `region-q16-F1` | viewer-173 | `[765,268,802,294]` | formula／Q16 诊断 |
| 28 | `region-q16-F2` | viewer-173 | `[917,267,954,295]` | formula／Q16 诊断 |
| 29 | `region-q16-F3` | viewer-173 | `[994,269,1070,296]` | formula／Q16 诊断 |
| 30 | `region-q16-F4` | viewer-173 | `[619,301,656,329]` | formula／Q16 诊断 |
| 31 | `region-q16-F5` | viewer-173 | `[686,301,761,329]` | formula／Q16 诊断 |
| 32 | `region-q16-F6` | viewer-173 | `[823,302,861,330]` | formula／Q16 诊断 |
| 33 | `region-q16-F7` | viewer-173 | `[900,303,938,330]` | formula／Q16 诊断 |
| 34 | `region-q16-F8` | viewer-173 | `[681,338,718,364]` | formula／Q16 诊断 |
| 35 | `region-q16-F9` | viewer-173 | `[727,337,764,364]` | formula／Q16 诊断 |
| 36 | `region-q16-F10` | viewer-173 | `[884,339,922,365]` | formula／Q16 诊断 |
| 37 | `region-q16-F11` | viewer-173 | `[930,339,969,365]` | formula／Q16 诊断 |

归属计数：Q16 18 个（4 个题面、3 个答案行、11 个公式诊断窗）；共享材料 8 个；任务 1、2、3 分别为 3、4、4 个。

## 发现的差异与处置建议

### 1. 七个历史答案裁剪的 PNG 文件 SHA 与本包交付裁剪不同，但像素完全一致

七组文件尺寸、色彩模式和解码后的 RGBA 像素逐一相同；差异只发生在 PNG 文件编码字节，不是来源内容或裁剪范围变化。

| 裁剪 | 历史文件 SHA256 | 本包文件 SHA256 | 解码像素 |
|---|---|---|---|
| `task1-line1.png` | `2408634a37c308e6165651aaa0e3bf924aa47e91abacf0031f26e4f5421c780f` | `7b39e8cac7ba63790873101998fce65a2eb7aff1640614ef6f0a2bb7e92d35ea` | 相同 |
| `task2-line1-tail.png` | `4b748c7dc6bff06a9583590205b1c50d1475744f511f07027f3723bd6be3eed2` | `6ffc9840352c2618dcb7ae164e5a869c33401ba9f6e4aedc0291758111f30744` | 相同 |
| `task2-line2.png` | `5282ec39bd25815eef27fb175480bb8171fe111390931c38298ac1dab179f425` | `6b01e72dbe135036c96e682c5d203408ebdab710d1fdc6b06908d92be63572ae` | 相同 |
| `task2-line3-prefix.png` | `de13eb1566a0196f03e51d34131bf9a1fcb8111a269f2ae777f75b285618158b` | `451c84651847e2a958da87211af97510c1a5c6963d8465b7dfa0cf56b6136525` | 相同 |
| `task3-line3-suffix.png` | `ba6505414add251dbce780785884158f41e1d26cddf1572b632d1938770d36de` | `dbc8bc4b315415fcd47cbcb3a7a196ccacbb97330790867edc53cd6ea9268d8e` | 相同 |
| `task3-line4-continuation.png` | `a92491e265072b776b0c7c4c8520c3946729b7198a50156813fda3fc64e6a764` | `ce1e0571d13d0e63b500d8c59f3845aac9c828ea88dc41050227ca3dd1a5760a` | 相同 |
| `task3-diagram.png` | `aa2e04a4189b8df323763b14ced98dea8c6a4fef2fbbf6866abc5e39fdff7817` | `4131586447d1eee8b272d3db4b221e69b3202092a213a852e3de54858b02e910` | 相同 |

处置建议：在交付说明中明确区分“历史 PNG 文件字节摘要”和“本次由来源图重编码的交付 PNG 摘要”，避免消费方误把编码差异判断为像素或来源差异。当前只读验证器按本包 `source_proofs.sha256` 校验交付文件，并同时验证其解码像素等于来源窗口，因此本项不阻断来源证明。

### 2. 正文 2 与图 1 有 1 像素列重叠

`region-reading-body2=[66,835,432,1023]` 与 `region-reading-figure1=[431,838,573,1000]` 在 `x=[431,432)`、`y=[838,1000)` 重叠 162 像素。除此之外，非嵌套窗口没有正面积重叠；11 个公式窗与三个 Q16 答案行的重叠是有意的诊断性嵌套。

处置建议：对当前来源证明不构成阻断，因为这些坐标被明确声明为来源窗口、不是平台生产框。若后续消费者要求互斥框，应在人工复核后把正文／图形边界规范化，并产生新修订，不能静默改动当前固定包。

## HOLD 边界

本次通过的只是固定字节、来源重裁、图谱结构与限定内容连续性核查。以下仍未通过或不在本次范围：

- 18 项独立人工来源确认；
- 图形范围的人工作业验收；
- 来源窗口到平台框的转换；
- 第一章完整页源／题目分母；
- 平台提交、平台接收、业务放行或对外发布。

因此不得把 `SOURCE_BOUND_CONTENT_READBACK_OK` 表述为人工验收、章节完成或平台通过。

## 实际执行命令

以下命令均为只读核查。完整复核脚本随报告一并落盘，内含固定绝对路径、期望摘要和所有断言：

```powershell
python -X utf8 "C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-source-sol56\outputs\46007447-Q16-reading-C01-source-audit-20261021.py"
```

验证器也被单独从解压根目录执行：

```powershell
Push-Location "C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\q16-reading-handoff-20261021\final-extracted-v2"
python -X utf8 tools\verify_q16_reading_b.py delivery
Pop-Location
```

固定包和 bundle 摘要另行直接读取：

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath "C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\textbook-annotation-assistant\handoffs\b\46007447\B-46007447-Q16-reading-C01-HOLD-2026-10-21.zip","C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\q16-reading-handoff-20261021\final-extracted-v2\delivery\bundle.json"
```

复核脚本执行的其余断言包括：直接读取八来源 ZIP 内三个 entry 与本包来源图逐字节比较；以 Pillow 解码历史／交付的 7 对 PNG 并比较 RGBA 像素；读取 `bundle.json` 统计 37 个 region 并计算同图 bbox 正面积交集。
