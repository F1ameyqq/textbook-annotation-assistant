# Q16 自动候选接入离线复核

2026-10-17，Asia/Shanghai。基线 `5df4c9820eb57b6e1587f3bcb0dee23cfb19f264`；交付版本以本文所在提交和 PR #2 head 为准。B 内部试验入口，公共合同仍是草案，A 接收 `PENDING_A`。这一步推进长期目标 G1 的复核流程，不代表 Q16 全文正确或已获人工核准。

## 可用流程

此前自动草稿的公式候选只能在独立 HTML 中对照并复制。本轮可在来源绑定的离线复核工作区中打开 Q16 的三行草稿，逐个公式查看原图裁片、完整原始 LaTeX、整式模型观察或分量派生组合的来源，显式选一条用于对应文字段。选择不会自动保存；保存时只提交当前答案实际改变的块，生成新计划、当前正文/呈现及 Check07。可以继续显式改写正文、恢复历史版本，并分别导出当前计划和冻结候选目录。

候选目录加载时检查原始 JPG 的资产 ID、SHA、尺寸、裁片逐像素一致、旧 OCR 快照、当前 G05 可见片段与账本的行归属，并由归档观察重建草稿。不同来源但同文的候选保留不同 ID；44 条整式原始观察和 298 条派生组合分开显示，未知语法的原文仍可查看。编辑一个已选公式会清除该段待保存的候选引用；改变文字段数量、格式或顺序会暂停公式位置映射。正文风险独立显示，不混入 Check07 的问题计数，也不会因选择、保存或恢复而自动消失。

普通计划导出记录未核准的文字和选择来源说明；若要在另一环境重新核验候选身份，须同时导出候选目录并提供相同原图。独立 14 阶段流水线会核验计划和当前内容，但不替代可选目录的来源重放，也不签发人工核准。`MODEL_DRAFT`、`HUMAN_DRAFT` 均是编辑者类别，不等于已验证文字。

## 启动

沿用[离线复核工作区](b-content-review-46007447.md)的 E/G05/Check05、review、来源 manifest 和全新工作区，加上本轮自动计划及 `--region-catalog`：

```text
python tools/review_content_b.py --evidence <evidence.json> --graph <graph.json> --base-check <base-check.json> --review <review.json> --plan <automatic-content-plan.json> --source <original-source.json> --source <adjacent-source.json> --region-catalog <region-catalog.json> --workdir data/runs/my-region-review
```

`region-catalog.json` 为 `b-region-review-inputs-trial/0.1`，每条包含 `answer_id`、相对于目录的 `draft` JSON 文件及 `crop` PNG 文件。Q16 的 answer ID 是 `a-7302d4870826c53aea0bcd16`；`draft.json` 由[自动草稿重放命令](b-region-automatic-46007447.md#重放入口)生成，裁片采用同页固定原图像素的 `unit2-q16.png`。目录成员须在 manifest 同一目录下或其本地子目录，不能通过 `..`、网络路径或 URL 引用。可以先把草稿与裁片复制进全新的本地目录，再写入以下 manifest；原图 manifest 仍须覆盖 E 中六个完整资产：

```json
{"schema_version":"b-region-review-inputs-trial/0.1","entries":[{"answer_id":"a-7302d4870826c53aea0bcd16","draft":"draft.json","crop":"unit2-q16.png"}]}
```

工作区会冻结目录内容。开启或重开时要用完全相同的输入、来源及兼容代码/依赖；已创建的旧工作区不能直接补挂目录，须开新的工作区。缺少完整原图时不能以固定裁片冒充来源核验。页面只访问本机 loopback 服务，网站标注不参与。

## 真实 Q16 验证与限制

在现有六资产局部样本上，工作区读到 11 个公式组、44 条整式观察、298 条派生组合及 50 项像素/上下文来源风险。显式选定一个 F5 派生组合，并同时修订第三行一处正文；保存、恢复初版、再次恢复所选版和重开工作区均保留了版本及来源回执。跨分式候选、伪造核准字段和陈旧 head 均拒绝。当前仍为 34 题候选、66 答案候选、127 项 Check07 问题、19 条未归属来源，全部 `HOLD`，`transcription_verified=false`、`business_acceptance=false`，没有新增题答关联。选中的 F5 公式只证明有来源的开发选择；其它错字、漏符号和幂次仍在，不据此宣布 G1 通过。

代码回归：14 项候选来源测试、19 项原工作区测试、10 项真实 loopback HTTP 测试及 4 项端口绑定测试通过；隔离导出的源码和固定输入已核对。首轮 HTTP 10 项中 2 项遇到 Windows `WinError 10013`，原失败记录保留，随后同一快照 10 项全通过。Node DOM 模拟覆盖 342 条候选、50 项来源风险与 127 项检查问题分开显示、同文不同源、编辑/保存/恢复、陈旧请求保留草稿和未知 LaTeX 原文；它不替代本轮真实浏览器视觉验收。本轮没有重跑完整千项测试；详细回执见[评估](../evaluation/book-46007447-region-review.json)。

本轮新增模型调用、标注网站请求/动作、原图上传、模型下载和额外付费调用均为 0；真实验证仅在本地生成未核准工作区版本。下一步先减少 Q16 外围符号与幂次错误，安排独立逐字核对，再处理章节完整来源、19 条材料身份和 A 的固定消费者。整书、跨书及平台交付关口继续按[长期目标](b-long-term-goal.md)推进。
