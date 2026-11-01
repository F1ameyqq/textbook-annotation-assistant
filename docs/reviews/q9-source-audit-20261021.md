# 46007447 第一章来源清单、Q9题页定位与网站只读恢复报告

日期：2026-10-21（Asia/Shanghai）
范围：B侧第一章来源与页码核查；共享仓库只读，网站只读；未编辑、保存、提交或送审任何标注。

## 结论

1. **网站标注现在不能安全启动。** 新开的独立 `https://www.usense.com/qieti/annotateUnified` 标签实际落到 `https://www.usense.com/qieti/login`；旧 `/qieti/home` 标签属于另一个浏览器会话，当前会话不能接管。Windows窗口通道两次激活失败，浏览器原生通道随后两次超时并重置。未尝试读取凭据、绕过保护或进行登录。
2. 固定八来源包重新逐项校验通过：ZIP SHA、8个成员文件SHA和解码尺寸都与清单一致；但它只是已观察子集，仍是 `PARTIAL/HOLD`，不能作为第一章完整分母。
3. **目标Q9题页仍未定位。** 目标唯一绑定为“☆问题解决策略：反思”的答案 `a-9a6c21dd0fe88b1059b7919e`；固定六张题页（模型观察印刷2–7页）经直接核图均不是该反思Q9题页，不允许用其他同号9替换。
4. Q9答案来源已经独立闭合到两张固定原图：`viewer-173`（模型观察印刷25页）右栏底部开始，`resource-173`（模型观察印刷26页）左栏顶部续接；包含两个小问、20cm/25cm结论及图3–7。第二张图只在顶部前缀属于第一章，随后进入“回顾与思考（一）”，再进入第二章。
5. 静态目录快照中第一章有9个一级组，“☆问题解决策略：反思”排第7，“回顾与思考（一）”排第8，“周测（第一章）”排第9，下一顶级目录是“第二章 实数”。这只能证明历史目录顺序；周测是否计入本轮章节交付、第一章题页/答页完整起止和总题数仍未知。

## 固定输入与当前仓库状态

| 对象 | 实测SHA256／状态 |
|---|---|
| 八来源包 | `ec77d52ebcf25b3fec64579f63400c010cc08a623d71e20506e6ed46125ea695` |
| Q15 revision9包 | `8c812330b93cc60b920f6ccd1cd7784f0afe8d293336166a586e1aeaab8231ad` |
| Q4/Q9/Q16下一批暂存包 | `b646fad9008e03e79a3dddfb4ead912d7ceadefbcee331c2e2af2415abf6f673` |
| 目录快照 | `a639dbdf852298540a5b5ac4351f1562c1ec1249a6001cd7c95708fa044b08b5` |
| 共享仓库只读观察HEAD | `a55b2d4fce17b55fc117ebf83602267daaf35b84`，分支 `b-side/readonly-book-46007447`，工作区无未提交条目 |

主线交接中给出的固定基线为 `2b818eba275b0a80160e1dbb5bf2b0cbb540f78b`，但本次只读检查时共享工作区HEAD已经是上表的 `a55b2d4…`。本会话没有执行 checkout、reset、commit 或 push；以下来源结论以固定包SHA和实际观察文件为绑定依据。

## 八张原图独立清单

所有成员均直接从八来源ZIP读取，重新计算SHA并用Pillow解码尺寸；8/8与清单一致。

| 阅读序 | 资产 | ZIP成员 | 字节 | SHA256 | 尺寸 | 模型观察印刷页 | 角色 |
|---:|---|---|---:|---|---:|---:|---|
| 0 | `viewer-10` | `assets/46007447_viewer_10.jpg` | 478123 | `eb7cc17e6b58a55a005ce1cdef5bd5058ad258c3dd44dc891b3d830ed3db3626` | 1217×1691 | 2 | 题页 |
| 1 | `viewer-11` | `assets/46007447_viewer_11.jpg` | 379245 | `7c433368bbe7ccea76c1c2b8a53559a87a9e2b99e23d692ba9ca005e16f507a3` | 1222×1692 | 3 | 题页 |
| 2 | `viewer-12` | `assets/46007447_viewer_12.jpg` | 467691 | `774c8a29bbdcaa35fcb88479129d2b523ec077edfa4e0ac3db6f11e9bcae9b87` | 1220×1692 | 4 | 题页 |
| 3 | `viewer-13` | `assets/46007447_page_12.jpg` | 417144 | `997b37d35fca57f73ab71e53f6721be145d10c436deab5fab38bf1ae0d31dc1e` | 1219×1691 | 5 | 题页 |
| 4 | `viewer-14` | `assets/46007447_viewer_14.jpg` | 396099 | `4186d57ffad14f576fe7c967c96697d25c83ffe3512217c79b8371134181c1d9` | 1218×1694 | 6 | 题页 |
| 5 | `viewer-15` | `assets/46007447_page_14.jpg` | 435723 | `7c1a4afec69a94371fa31b6111969ca3d6ec39d7d7c6b1c73764f90316a610dd` | 1219×1703 | 7 | 题页 |
| 6 | `viewer-173` | `assets/46007447_viewer_173.jpg` | 428192 | `a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be` | 1148×1621 | 25 | 答案页 |
| 7 | `resource-173` | `assets/46007447_resource_173.jpg` | 484200 | `8380f9a1872c830b1cf4fba12fa00e3b6d9c50ddaed357587de7333086e9cdbf` | 1145×1620 | 26 | 答案页／第一章仅顶部前缀 |

页码是模型目视观察，不是已人工冻结的viewer/resource全局映射。`viewer-173` 与 `resource-173` 是不同字节、不同尺寸的相邻来源，不能互换。

## 第一章静态目录顺序

目录ID：`dir-1792063578574-ug3232apl`。历史快照中有22个已有问题节点，其中21个在“1 探索勾股定理”，1个在“2 一定是直角三角形吗”；其余组为空不等于没有题，因此节点数不能作为章节分母。

| 顺序 | 目录ID | 标签 | 快照问题节点数 |
|---:|---|---|---:|
| 1 | `dir-1792063578574-b5kz24rtf` | 1 探索勾股定理 | 21 |
| 2 | `dir-1792063578574-qfhemzkmn` | 漫话勾股世界——教材P6“阅读·思考”变式 教材回归专练 | 0 |
| 3 | `dir-1792063578574-g0n3ulsni` | 2 一定是直角三角形吗 | 1 |
| 4 | `dir-1792063578574-cmekhlsae` | 3 勾股定理的应用 | 0 |
| 5 | `dir-1792063578574-6n9eryan5` | 小专题1 方程思想在勾股定理中的运用 | 0 |
| 6 | `dir-1792063578574-yzhjtylax` | 小专题2 勾股定理在折叠问题中的运用 | 0 |
| 7 | `dir-1792063578574-iv9ig1hci` | ☆问题解决策略：反思 | 0 |
| 8 | `dir-1792063578574-hzrhienmk` | 回顾与思考（一） 勾股定理 | 0 |
| 9 | `dir-1792063578574-8wdh4l41q` | 周测（第一章） 周测小卷 | 0 |

下一顶级目录为 `dir-1792063578574-yvji75vuo / 第二章 实数`。目录把周测放在第一章树下，但是否纳入本轮章节交付仍需当前网站目录／原书来源边界确认。

## Q9题页定位结果

目标身份：

- 章节路径：`第一章 勾股定理 / ☆问题解决策略：反思`
- 目标答案ID：`a-9a6c21dd0fe88b1059b7919e`
- 目标问题ID：`null`（尚未建立）
- 检索线索仅供定位：蚂蚁沿长方体表面从A到B；小问1使用8、8、12并得20cm；小问2使用10、20、5并得25cm。

对六张固定题页的直接核图结果：

- 印刷2页：第一章开头“探索勾股定理”，题1–9的一部分；
- 印刷3页：题10–16；
- 印刷4页：“第2课时 勾股定理的验证及简单应用”，题1–7；
- 印刷5页：该课时后续、阅读材料和下一节起始；
- 印刷6页：“2 一定是直角三角形吗”，题1–10；
- 印刷7页：同节题11–16；
- 六页均未出现“☆问题解决策略：反思”目标Q9的完整题干、两个小问和相应长方体图。

因此当前状态继续为 `NOT_LOCATED_IN_FIXED_LOCAL_SOURCE_SET`。这不是“网站或全机不存在”的结论，只说明固定八图与本轮静态材料中未定位。不得把印刷2页的普通同号9、印刷6页的同号9或其他目录中的Q9替换为该目标。

## Q9答案两页续接与五图来源

直接核图可见：

- `viewer-173`（印刷25）右栏底部以“9.解：（1）”开始，给出第一种20cm路线，并含图3、图4；该页在Q9答案处结束。
- `resource-173`（印刷26）左栏顶部从图4分析继续，完成小问1的20cm结论，随后完整给出小问2的三种展开、25cm结论和图5–7。
- `resource-173` 左栏在图7下方进入“回顾与思考（一） 勾股定理”，再往下进入“第二章 实数”；因此Q9续接只使用其顶部前缀，不把整页都归为Q9或第一章反思段。

五图当前来源搜索窗口：

| 图 | 来源 | bbox `[x1,y1,x2,y2]` |
|---|---|---|
| 图3 | `viewer-173` | `[700,1395,847,1542]` |
| 图4 | `viewer-173` | `[870,1379,966,1542]` |
| 图5 | `resource-173` | `[145,249,231,441]` |
| 图6 | `resource-173` | `[246,291,382,441]` |
| 图7 | `resource-173` | `[394,267,493,441]` |

跨页固定关系为 `viewer-173 → resource-173` 的来源邻接；没有声称 `resource-173` 对应某个已核实的 `viewer-174`。这些窗口是本地开发几何，图形语义与精确转写仍未获人工验收。

## 网站只读恢复记录

### Windows窗口通道

- 发现唯一Edge窗口：ID `3215216`，标题“注销页 和另外 10 个页面 - 个人 - Microsoft Edge”。
- 按技能要求从返回对象绑定后激活；首次和刷新窗口清单后的唯一一次重试都返回：`failed to activate captured window`。
- 随即停止Windows窗口通道，没有复用旧坐标或自动化终端／安全界面。

### 浏览器原生通道

- Edge浏览器连接ID `3`，配置“用户配置 1”。
- 旧只读组标签：ID `1199071786`，URL `https://www.usense.com/qieti/home`，标签组“46007447只读核查”。绑定时返回：`Tab 1199071786 is already part of browser session 01a1445e-2f9f-7c73-8a2a-1f16b0f341fb`；未抢占。
- 使用用户明确给出的目标地址新建独立标签；调用超时并重置会话，但恢复后的浏览器清单显示新标签ID `1199071952`，URL已变为 `https://www.usense.com/qieti/login`。
- 绑定新标签再次超时并重置。至此停止，不输入账号、密码、验证码，不读取Cookie，不绕过调试连接或权限保护。

### 恢复条件

满足下列任一项即可继续Q9题页只读定位：

1. 用户在一个可由本会话附着的独立Edge标签中完成登录，并保持该标签打开；或
2. 用户直接提供Q9完整题页／相邻页原图或PDF；或
3. 平台导出第一章当前目录和原图清单，至少包含观察URL或资产身份、原字节、顺序和边界信息。

即使恢复，也只进行读取和来源保存；任何编辑、保存、提交或送审仍需新的明确授权。

## 仍未知／不得宣称

- 第一章完整题页和答案页起止；
- Q9题页的原图、viewer/resource身份、印刷页和问题ID；
- 周测是否计入本轮章节交付分母；
- 第一章问题、答案和共享材料的完整数量；
- 任何人工内容验收、平台接收或业务放行。

结论保持 `PARTIAL/HOLD`。

## 实际命令与工具动作

```powershell
git -C "C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\textbook-annotation-assistant" rev-parse HEAD
git -C "C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\textbook-annotation-assistant" status --short --branch
```

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath "C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\textbook-annotation-assistant\handoffs\b\46007447\B-46007447-observed-eight-sources-v2-PARTIAL-2026-10-17.zip","C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\textbook-annotation-assistant\handoffs\b\46007447\B-46007447-Q15-revision9-current-baseline-HOLD-2026-10-18.zip","C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\textbook-annotation-assistant\handoffs\b\46007447\B-46007447-Q4-Q9-Q16-next-batch-HOLD-2026-10-19.zip"
```

```powershell
python -X utf8 "C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-source-sol56\outputs\46007447-chapter1-Q9-local-source-verify-20261021.py"
```

该脚本只读打开八来源ZIP，重算全部成员SHA、解码尺寸，读取目录快照，并核对Q9跨页答案和五图来源窗口。全文检索实际命令为：

```powershell
rg -n -S "a-9a6c21dd0fe88b1059b7919e|问题解决策略.?反思|20cm|25cm|蚂蚁|8/8/12|10/20/5" "C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\textbook-annotation-assistant"
```

图像使用本地查看工具按原像素／高细节读取固定题页与两张答案页；网页动作严格按Computer Use技能和浏览器原生CUA流程执行，错误与恢复条件如上记录。
