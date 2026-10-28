# 印刷7页的独立题目内容投影

原始单页识别虽找到了11–16六个题号，但Q13的5/2错挂、Q13/Q15缺图、Q15末尾证明要求和Q16一般式等内容不完整。本增量按原图重建六题的独立内容投影，不修改原OCR、原questions/fragments或既有Q4/Q9/Q16答案链，不生成新的题答匹配。

`tools/rebuild_question_content_b.py` 接受固定source、E0.2、G0.2、题目草稿JSON及外部保存的计划文件SHA。只支持这一明确版本组合；其他版本拒绝。输出独立 `QuestionContentApplicationTrial` 和内容来源检查，不把材料伪装为可供旧消费者使用的新图谱。

当前草稿v4保留六题、23块、12个独立A–D选项、两幅原像素图、Q16三个子任务、七个值为null的响应空格及四个编辑badge。六个分式逐一保留分子/分数线/分母来源框并绑定正文run_index；框及文字都是模型草稿。计划保存完整62行原OCR、六个原question快照和全部来源归属，列标题与页脚分别记录。题号16只属于viewer15来源，不能使用viewer11月牙题的答案。

生产者与独立消费者分别验证固定计划文件SHA、E/G引用、原图SHA/尺寸、整题和块的边界、选项/子问原OCR锚点、空格未填、分式几何以及导出PNG逐像素和文件摘要。原图导出不缩放，应用归档原G和计划并绑定生产代码摘要。上述核对只证明来源和投影一致；不能证明每个模型转写正确、图形范围精确或整章完整。应用和检查始终HOLD，保留文字、图形、公式、章节身份及人工审核风险。

首次v2模型内容复核发现数学/几何与源图一致，但boxed A及NEW编辑badge未显式记录；v3补来源标记并细分页边装饰账本。独立代码审计又发现旧引用未约束run_id/producer等顶层字段，以及分式列表可逆序。v4固定完整E/G canonical artifact摘要，要求精确envelope、完整input_refs/context引用和相同run_id；分式按源几何重叠行及横向顺序重建，并逐一绑定LaTeX run。v2/v3原文件和测试fixture保留。v4计划文件SHA为 `a7a5c43eb33d2e1378d0f82dc7375603a462dba64a60adbdb06f09a3a2f4ac99`。[独立代码/负例终审](reviews/viewer15-question-content-v4-independent-audit.md)已通过来源和投影完整性检查（独立11项测试，2.998秒），不能把accepted当成人工签核。消费者必须固定上述外部SHA，不能对收到的替换计划自行重算SHA并视为授权。

对四个缺陷区域各做原尺度/3倍的八次本地普通OCR入口调用。Q15末尾部分文字重现，但角号和分数仍错；Q16一般式仍失败。全部原输出、四边形、置信度、裁片/输入像素摘要、变换、模型权重摘要及时间保存在 `tests/fixtures/book46007447/viewer15-local-ocr-probes-v1.zip`，所有结果UNSELECTED，没有按最高分或多数票覆盖原OCR。执行期间禁止网络，没有模型下载或新增付费调用。

实际入口示例（先将 `viewer15-question-draft-v4.zip` 解压到工作目录）：

```powershell
python tools/rebuild_question_content_b.py --source work/input/source.json --evidence work/input/evidence.json --graph work/input/graph.json --plan work/input/plan.json --plan-sha256 a7a5c43eb33d2e1378d0f82dc7375603a462dba64a60adbdb06f09a3a2f4ac99 --out work/question-content
```

已运行新入口及 `python -X utf8 -m unittest tests.test_question_content -v`，11项通过，含12种E/G完整对象字段篡改、两种分式逆序及原有源像素、选项、空格、丢图、跨题、假审核和错版本拒绝。实际从fixture解压后的输入新目录运行、同目录重复、第二新目录运行，三次应用完全相同，禁止模型导入和网络；这是确定性重放，不称流水线缓存。确切引用与源码摘要见 `evaluation/book-46007447-question-content-viewer15.json`。未跑全套，固定 `7d5c3b738a3e28b528e510d16d7cfe2640936964` Git代码导出中实际CLI新目录、重复、第二新目录重放均通过（0.703/0.688/0.687秒，23裁片，应用和检查完全相同）；沿用本机依赖、禁止模型与网络。独立v4可搬运包已完成，48成员加清单、23裁片；包校验与总控再次解包重放通过，详见 `evaluation/book-46007447-question-package-integration.json`。完整章节来源及人工内容验收未齐。
