# A05 单题写入执行报告

状态：**REVIEW，待主调度独立验收**。本报告记录执行事实与离线自检，不给出最终 ACCEPTED 结论。

2026-10-16（Asia/Shanghai）：在 `46007447`《名校课堂八年级数学上册》恰好新增一道填空题，题级保存一次；刷新及真正关闭浏览器后重开均读回同一题的两框。全量记录由 21 题 / 66 框变为 22 题 / 68 框。原 66 框全部业务字段逐项一致，原目录节点及顺序保留，书状态仍为“标注中”。未进行书级送审、送交或 OCR。

## 版本与范围

- `base_commit` / 执行时 HEAD：`79b7195dc0ff98ff6b4ce3fe5f97ae707e3bb0d5`。
- 工作区：`D:\1800`；保留当前 `codex/local-login-config` 分支。按派发要求未切分支、未 reset；执行脚本位于独立 `.local/stages/A05/`，本任务交付只包含自己的新文件。
- 本轮规则未在执行前形成单独 `workflow_commit`；采用任务单和规则文件的 SHA-256 精确绑定，见 [run-version.json](../evidence/A05/execution/run-version.json)。不能把基线提交说成已包含这些未提交规则。
- `AGENTS.md`：`1c484397a91613d35d01f8a44c58fd3c9bd6a7c0841046919e5fb9a153f03a75`。
- `docs/tasks/A05-single-question-write.md`：`ae2f741795da33b499203f99c072f526e3524a647d164264f07b3046c1c52c0a`。
- `docs/coordination.md`：`b6b73b02a041937f68a3156431ca386ab5d43b592d6de6ee50f8c0fc3db15406`。
- [代码与环境版本](../evidence/A05/execution/code-version.json)：Python 3.9.13、Playwright 1.58.0、专用无头 Edge、viewport 1600×1100。本次 context 使用已授权的 `ignore_https_errors=True`，未改变全局配置。
- 合同语义参考 `contracts-v1.md`，尚未把本试验包装成 C01/A01/A02/A03 实现。输入为原图视觉核准的固定样例，不是 B 识别算法产物；未管理 B。

## 候选与写前计划

选择“第一章 勾股定理 / 2 一定是直角三角形吗”的基础题第 5 题，正文印刷页 6：木工做长方形桌面，长 2.4 m、宽 1.8 m、对角线 3 m，填“合格”或“不合格”。同章节答案明确为“5. 合格”。正文及配答由主执行者和只读子代理分别查看原图；`2.4²+1.8²=3²` 亦一致。本题没有附图或印刷解析，上方两个图分别属于第 4、6 题，不纳入本题。

正确末级目录已存在，ID 为 `dir-1792063578574-g0n3ulsni`。该目录原先无题，前面目录的最大题序为 21，因此本题追加为 22，不调整已有题序。全量写前框中没有该正文页的历史标注。本轮没有选项框，不涉及 W 独立 / 合并政策争议。

| 来源 | 实际映射 | 尺寸 | SHA-256 |
|---|---|---|---|
| [题目原图](../evidence/A05/execution/source-viewer14.jpg) | viewer 14 → 接口源 `page_index=13` → `46007447_page_13.jpg`；保存框的 `page_index=14` | 1218×1694 | `4186d57ffad14f576fe7c967c96697d25c83ffe3512217c79b8371134181c1d9` |
| [答案原图](../evidence/A05/execution/source-viewer173.jpg) | viewer 173 → 接口源 `page_index=172` → `46007447_page_172.jpg`；保存框的 `page_index=173` | 1148×1621 | `a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be` |

映射分别由 [question-page-mapping.json](../evidence/A05/execution/question-page-mapping.json)、[answer-page-mapping.json](../evidence/A05/execution/answer-page-mapping.json) 记录，不能把源资源索引与平台保存的页号混用。只取得候选所需原图，不宣称下载或验证全部 214 页。

写前 [write-plan.json](../evidence/A05/execution/write-plan.json) 于 18:59 左右落盘，先于画框与保存。记录 Q `[67,1110,593,1229]`、A `[221,1285,279,1309]`，均为原图坐标、`content_type=text`，题型“填空”，预期原 66 框和目录不变。

## 实际动作与回执

1. 复用账户隔离的专用无头 profile，未接管日常 Edge。写前没有匹配本书专用 profile 的活跃进程；本任务是唯一写入者。重新选择书 ID 后获取书、目录、全部框、源元数据、候选页，逐记录对照调度基线一致。
2. 点击可见的“题目(Q)”控件后拖出 Q 框；点击“答案(A)”后拖出 A 框。读取 DOM，实际角色为 `question-type` 和 `answer-type`，没有 W/E 框。手工新框默认文字类型。两张实际裁片 [Q](../evidence/A05/execution/actual-q-crop.jpg)、[A](../evidence/A05/execution/actual-a-crop.jpg) 在保存前逐图核对，内容完整且不混邻题。
3. 19:01:43（Asia/Shanghai）仅点击一次“提交修改”（command-0057）。发送前守卫检查目标书、目录、`question_order=null`、`is_new_question_insertion=true`、`insert_after_order=21`、恰好两个全新 rect_id、删除列表和 OCR 内容列表均空。全部约束满足才放行；其他平台写接口被禁止。见 [commit-preflight.json](../evidence/A05/execution/commit-preflight.json)。
4. [业务回执](../evidence/A05/execution/commit-receipt.json) 为 `code=0`、`success=true`、`inserted=true`、`question_order=22`、`append_at_global_end=true`，新增目录题节点 ID `1792148510557`。随后单题 GET 读回两框；没有以上传提示或 HTTP 200 单独认定结果。
5. 刷新页面、重新选择本书、点击目录题 22 读回历史框；随后于 19:03:54 关闭整个专用 context，确认该进程退出，再以同一专用 profile 启动全新浏览器。重新读全量书 / 目录 / 框、单题框与题型，核对跨会话恢复。最后于 19:07:09 关闭第三次专用会话，核对匹配进程数为 0。

| 角色 | 新增 rect_id | 实际保存的原图 bbox（简写） | 页号 / 类型 |
|---|---|---|---|
| Q | `3c8ce7f1-13ea-4969-a1ce-45fb72473a1d` | `[66.999949,1110.000071,592.999982,1228.999972]` | 14 / text |
| A | `56100140-765c-43c9-9d89-3f0a58beb05b` | `[221.000097,1285.000085,279.000080,1309.000145]` | 173 / text |

两框都属于题序 22、`question_level`，各角色的 `image_order_in_annotation_zone=0`。原图框与计划误差小于 0.001 px。未填入 OCR 文本；payload 的 `ocr_delete_zones` 含各角色是前端对新增题的默认构造，该事务 `question_order=null`、新增题上下文明确，未覆盖历史题。

## 保存、刷新与重开核对

| 核对项 | 实测结果 | 证据 |
|---|---|---|
| 写前基线 | 21 题、66 框，目录与调度基线一致 | `prewrite-book/annotations/directory.json` |
| 题级保存 | 一次 commit；单题读回两框 | `commit-receipt.json`、`save-readback-question22.json` |
| 刷新全量 | 22 题、68 框，原 66 框逐字段一致 | `refresh-book/annotations/directory.json` |
| 真正关闭重开 | 68 框与刷新快照逐字段一致；单题框与全量一致 | `reopen-annotations.json`、`reopen-question22.json` |
| 目录保留 | 只多题节点 22；删除该新节点后，完整旧目录树字段、层级和同级顺序与写前完全相等 | `reopen-directory.json` |
| 题型 | `tishi=tiankong`、`order_in_level=22` | `reopen-question-info22.json` |
| 书状态 | 保存后、刷新、重开均“标注中”，题数 22；送审 / 送交相关返回时间字段仍 null | `after-save-book.json`、`refresh-book.json`、`reopen-book.json` |
| OCR | Q/A 均返回“未找到标注结果”；`content_check_status=PENDING` | `reopen-ocr-question22.json`、`reopen-ocr-answer22.json` |
| 会话释放 | context 已关，进程退出 0，匹配活跃进程 0，无未决写入 | [session-release.json](../evidence/A05/execution/session-release.json) |

历史比较按 rect_id 对齐，覆盖已有记录的身份、角色、`verified`、`bbox`、题序、页号、图像路径、目录、内容类型、父框关系、创建 / 更新时间及预标注字段，只有身份私密字段在导出时去除。未在写前独立快照 21 题的 OCR 文本 / 题型，不把本轮框记录保留核对扩展为这些独立数据的完整审计。

普通单击目录题 22 只导航并显示历史框，右侧编辑器仍显示下一道新题 23；该数字不是新增第二题。题 22 的题型通过只读 `get_question_info/46007447/22` 确认，未进入历史修改态。

共享截图保留实际画框和刷新 / 重开状态：[画框后](../evidence/A05/execution/after-qa-draw.png)、[刷新后](../evidence/A05/execution/after-refresh-question22.png)、[重开后](../evidence/A05/execution/after-reopen-question22.png)。截图排除了顶部账户栏与底部归属人栏；从私有原截图截取 `[0,50,1600,1050]`，保留区域逐像素相等，方法和原图 / 共享图摘要见 [screenshot-provenance.json](../evidence/A05/execution/screenshot-provenance.json)。原完整截图、命令与浏览器 profile 均保留在 `.local/`。

## 复现与自检

可共享验证脚本：[tools/a05_verify_evidence.py](../../tools/a05_verify_evidence.py)。仅校验落盘证据，不启动平台会话，不重放线上写入：

```powershell
cd D:\1800
$env:PYTHONUTF8='1'
python tools/a05_verify_evidence.py
```

实跑退出码 0，34 项检查均满足，见 [self-check.json](../evidence/A05/execution/self-check.json)。该 PASS 仅为执行证据离线自检，不代替主调度安排的独立平台验收。

本机过程命令为 `python .local/stages/A05/session.py`，由 `control.py` 写入新编号命令逐条驱动。旧命令在启动时全部跳过，禁止重放；仅修改规则后的第二次会话承担写入，第三次只读复核。新增脚本摘要见 `code-version.json`。后续复核应采用只读流程，不重发 command-0057，也不再用旧 `.local/book46007447_session.py` 队列。

[network.json](../evidence/A05/execution/network.json) 记录 50 个 `/qieti/api/` 响应：49 GET、1 POST（本次题级 commit），无 OCR 启动、书级送审 / 送交请求。该清单不覆盖裁片向 OSS 的上传请求；上传完成由 commit 和重开图像路径读回间接支持。临时上传签名响应体不共享，认证值仅程序内部读取；共享 JSON 不含身份凭据键。

首次只读“选择书籍”点击因 PowerShell/Python 字符编码不一致超时，发生在尚未选择书籍、无框、无写请求时；显式 UTF-8 后完成。写前比较曾因基线与新响应的外层说明字段不同而暂停检查，按 rect_id 比较记录字段确认相等后才继续。两者均不是 UNKNOWN 保存，没有因此重发任何写操作。详见 [recovery-notes.json](../evidence/A05/execution/recovery-notes.json)。

## 未验证项与结束状态

- 结果仅支持本样例的“单题框保存及关闭重开恢复”；完整识别内容验收仍为 `PENDING`，不能宣称完整题识别合格或整个自动标注程序完成。
- 无 OCR 触发，无付费识别 / 模型 API 调用，实际调用与花费为 0；代理视觉核查不算 B 算法评测。OCR 质量、成本、批量稳定性、跨页、图表类型切换、W 政策和其他题型未测。
- 未测未保存草稿跨重启恢复；本轮只在业务保存已确认后关闭。未测 UNKNOWN 保存恢复；没有发生未知保存。
- 没有删除、移动或修复已有标注，未更名 / 重构目录，未处理其他书；旧历史题的目录归属保持原样。
- 没有书级送审 / 送交，`submission_status=NOT_SUBMITTED`，书仍“标注中”。专用 profile 已释放，无未决动作；可由独立只读验收者接续。

最终交付提交 ID 由 Git 交付记录与执行对话回执提供；主调度读取本报告后独立给出验收结论。
