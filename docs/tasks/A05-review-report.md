# A05 独立验收报告

结论：**ACCEPTED（仅 46007447 的该单题框保存与关闭重开恢复试验）**。

2026-10-16（Asia/Shanghai），验收者在执行对话完成、正式执行报告和释放证明齐备后，独占重开专用无头浏览器，读取平台实际业务响应并重新获取原图和保存裁片。当前为 **22 题 / 68 框**；新增恰好题 22 的 Q/A 两框，66 个旧框的全部导出字段和原目录树保留。书仍“标注中”，未送审、送交；OCR 内容检查保持 **PENDING / CONTENT_PENDING**。

本结论不包含完整识别录入、批量自动标注、UNKNOWN 恢复、书级提交或 B 侧研发验收。主调度决定集成与后续派发；本验收未修复线上题、未管理 B、未切共享分支或提交任何文件。

## 被验版本与独立性

- 执行对话：`01a14454-610f-75f0-8baa-225518a51136`（local）；`wait_threads` 观察到 turn `01a14454-643b-7c21-9fb2-4cc87491020c` 为 completed 后才重开。见 [完成状态](../evidence/A05/review/execution-completion-observed.json)。
- 执行交付 / 验收时 HEAD：`a56ce0e23ee613cd81c09f7f21392ffc2ff17d60`；原基线为 `79b7195dc0ff98ff6b4ce3fe5f97ae707e3bb0d5`。
- 被验 [执行报告](A05-execution-report.md) SHA-256：`aa7389c538d10a2106ef49b1d5fd8081e6714bc3d8bb3c27211a337a0a5b8481`。报告摘要为：单次题级保存、追加题 22 的两框、刷新和关闭重开恢复、历史框和目录保留、OCR 待检查、无书级提交、会话释放。
- 任务单、AGENTS、coordination 等采用的确切摘要见 [开始版本](../evidence/A05/review/start-provenance.json)。执行前规则尚无独立 workflow_commit，不能声称原基线提交已包含这些本地规则。
- 检查了 `tools/a05_verify_evidence.py` 及执行者的 `session.py / prepare_plan.py / control.py / export_final.py / share_screenshots.py`。实际摘要均与执行版 `code-version.json` 一致；代码和报告摘要完整记录于 [reviewed-version.json](../evidence/A05/review/reviewed-version.json)。临时执行代码仍在本机 `.local/`，不是完整可共享运行应用。
- 离线只读子代理复核基线、原图候选和操作序列；验收者本人完成新的平台重开、业务读取及裁片检查。没有使用执行者自报完成代替实际读回。

## 会话与实际读回

执行者的 [释放证明](../evidence/A05/execution/session-release.json) 为 released=true、活跃专用进程 0、pending_write=false、unknown_save=false。验收重开前再次检查匹配 profile / 写入会话进程数为 0，见 [独立 preflight](../evidence/A05/review/independent-preflight.json)。凭据只在程序内部读取，复用既有授权的专用 profile 和本次 context 证书忽略配置。

独立读取发生于 **19:21:45–19:21:56**。只通过可见控件选择书 46007447 和已保存题 22，随后读取该页使用的书、全量框、目录、单题框、题型、OCR 查询及源页 GET。浏览器安装非读取请求拦截；本次 16 条平台 API 请求全部 GET，拦截计数为 0，另有四次 OSS 图片 GET。见 [独立网络](../evidence/A05/review/independent-network.json) 和 [运行结果](../evidence/A05/review/independent-run-result.json)。

验收浏览器于 **19:21:56** 关闭、进程退出码 0；19:25 再查专用活跃进程为 0，无未决动作。见 [验收释放状态](../evidence/A05/review/session-release.json) 和 [postflight](../evidence/A05/review/independent-postflight.json)。本验收没有点击画框、编辑、保存、OCR、目录修改或送审/送交入口。

## 逐项结果

| 要求 | 结果 | 独立证据与判断 |
|---|---|---|
| 基线有效且写前新鲜 | 通过 | 原始 manifest 六份摘要匹配；原始 21 题 / 66 个唯一框。写前快照的 66 框全部导出字段和完整目录树与基线一致。[写前比较](../evidence/A05/review/comparison-fresh-prewrite.json) |
| 仅目标书、恰好新增一道题 | 通过 | 独立全量业务响应 code=0，68 个唯一 rect_id，22 个题关联；只多预期 Q/A 两框，均为 46007447、题序 22。[全量读回](../evidence/A05/review/independent-response-0007.json)、[独立比较](../evidence/A05/review/comparison-independent.json) |
| 历史 21 题 / 66 框保留 | 通过 | 以 rect_id 对齐，全部导出字段精确相等，含身份、角色、bbox、题序、目录、页号、图像路径、父框、verified、时间和预标注字段；无旧 ID 缺失、无旧记录变化。只排除本来不共享的用户身份字段。独立读回亦与执行者最终重开记录完全相同。 |
| 原目录名称、层级、顺序不变 | 通过 | 只新增节点 `1792148510557`，挂在既有 `dir-1792063578574-g0n3ulsni`。移除该节点后，原完整树精确相等；121 个非题目录节点未改。[实际目录](../evidence/A05/review/independent-response-0003.json) |
| 原图、题干、配答、图和解析 | 通过，限框与配答 | 独立阅读印刷第 6 页该章节基础题 5：长 2.4m、宽 1.8m、对角线 3m；同章节参考答案为“5.合格”。无本题附图、解析；第 4/6 题图及邻题答案未纳入。Q 三行和填空要求完整，A 仅含本题答案。[视觉记录](../evidence/A05/review/independent-visual-review.json) |
| 原图摘要、页映射、bbox、内容类型 | 通过 | 新获取正文 / 答案原图摘要与计划相同，尺寸 1218×1694 / 1148×1621；viewer 14→source 13，viewer 173→source 172，平台框页号分别 14/173。Q/A bbox 与计划差值小于 0.001px，均在图内、content_type=text。[原图读回](../evidence/A05/review/independent-originals.json) |
| 真实保存回执及刷新 / 重开 | 通过 | 业务回执 code=0、success=true、inserted=true、question_order=22、append_at_global_end=true；执行者刷新与真重开证据经独立比较通过。本验收新会话再次读取两框，并从平台 image_path 重新 GET 裁片，与执行裁片字节相同。[平台裁片](../evidence/A05/review/independent-persisted-crops.json) |
| 单次保存、删除与题序风险 | 通过，限本次实际轨迹 | 76 个 command 均有一致 intent / result；仅 command-0057 点“提交修改”。50 条执行 API 响应只有一次 commit POST；payload 无历史 ID、annotations_delete_rect_ids=[]，新增题上下文和 insert_after_order=21 明确。唯一 UNKNOWN 为写前选书定位超时，网络数 0；保存没有 UNKNOWN 或重发。[操作审计](../evidence/A05/review/independent-operation-audit.json) |
| 题型和 OCR 边界 | 通过，内容仍 PENDING | 题 22 专属 GET 的 tishi=tiankong；Q/A OCR 查询均“未找到标注结果”。未触发 OCR，不能把视觉配答 / 框保存验收当成最终 OCR 文字核验。[题型](../evidence/A05/review/independent-question-info22.json)、[Q OCR](../evidence/A05/review/independent-ocr-question22.json)、[A OCR](../evidence/A05/review/independent-ocr-answer22.json) |
| 书状态与禁止动作 | 通过 | 当前书 question_count=22、status=标注中，reviewed_at / delivered_at / delivery_submitted_at 均 null。执行写请求没有 OCR 启动、submit-review、submit-delivery；验收会话没有任何平台写请求。[当前书](../evidence/A05/review/independent-book.json) |
| 脱敏、截图、相对引用 | 通过，限已检查产物 | 共享 JSON / 报告未检出本地凭据的精确字符串；认证、临时上传签名与身份字段已去除或脱敏。截图排除账户和归属栏；独立截图直接裁取 viewport `[0,50,1600,1050]`，没有重绘证据。[独立截图](../evidence/A05/review/independent-reopen.png)、[清单](../evidence/A05/review/manifest.json) |

新增框身份：Q `3c8ce7f1-13ea-4969-a1ce-45fb72473a1d`；A `56100140-765c-43c9-9d89-3f0a58beb05b`。目录为“第一章 勾股定理 / 2 一定是直角三角形吗”。单击保存题 22 后右侧仍显示下一道新题 23，这是已观测的平台显示行为；独立 UI 摘要的 fill_question_type_text_visible=false 反映该编辑器，并非题 22 的已保存题型失败。题型以专属 GET 核实，题数以全量框、目录和书业务响应核实。

## 复现命令与实际结果

在 `D:\1800` 运行以下离线命令，不会连接平台或重放写入：

```powershell
$env:PYTHONUTF8='1'
python tools/a05_verify_evidence.py --output docs/evidence/A05/review/execution-self-check-reproduced.json
python docs/evidence/A05/review/compare_snapshots.py --annotations D:\1800\docs\evidence\A05\review\independent-response-0007.json --directory D:\1800\docs\evidence\A05\review\independent-response-0003.json --label independent
python docs/evidence/A05/review/verify_independent_evidence.py
```

实跑均退出码 0：执行方离线检查 **34 项通过**，本验收独立证据检查 **33 项通过**，无失败项。结果见 [执行自检复现](../evidence/A05/review/execution-self-check-reproduced.json) 和 [独立检查](../evidence/A05/review/independent-checks.json)。

本次平台重开的确切脚本为 [independent_readback.py](../evidence/A05/review/independent_readback.py)，本机运行命令原为 `python .local/stages/A05-review/independent_readback.py`，同内容副本已纳入验收证据。该脚本只做固定 GET 和已保存题导航，先核查报告、释放证明与进程独占，最后关闭 context；不要在另一写入会话运行期间启动它，也不要重放执行者的命令队列。运行环境为本机 Python 3.9.13、Playwright 1.58.0、无头 Edge、1600×1100，证书忽略仅本次 context 使用既有授权。

## 失败、未测与限制

本次规定范围内没有失败项，也没有需要在验收任务中修复的线上题。

- **未执行** OCR 及最终文字 / 公式核验、付费模型 API：实际付费识别调用 0；代理的视觉阅读不算 B 算法测评。content_check_status=PENDING，submission_status=NOT_SUBMITTED。
- **未执行** 全书覆盖、其他题型、W 独立 / 合并规则、图表类型切换、跨页、批量稳定性、未保存草稿重启、书级送审 / 送交。
- **未执行** UNKNOWN 保存注入和自动恢复。临时会话的单次 commit 门禁不是持久化事务保护，通用 UNKNOWN 捕获也不能证明自动暂停后续写入；本次只有非写入定位 UNKNOWN，未触发这些路径。不能由本次成功推断 A03 或恢复机制已验收。
- **未完整审计** 旧 21 题的独立 OCR 文本和题型：写前没有这些完整快照。payload 的 ocr_delete_zones 是新增题事务默认字段；本次上下文为新题、未覆盖历史框，但不能据此宣称历史 OCR 数据已逐项证明不变。
- 网络审计覆盖 `/qieti/api/`；未完整记录执行者向 OSS 上传的全部请求。独立重新下载平台保存裁片并核对字节，补足了这两份最终裁片的持久化证据。
- 验收只证明报告所列时点与这一个固定候选；本机临时执行脚本、规则散列与证据不等于通用运行程序或双方共享合同已经交付。

集成状态：尚未由主调度集成。可交回主调度的是这一个明确样例的单题保存 / 真重开能力证据；C01、A01、A02、A03、其他题型或 B 接口状态不因此自动通过。
