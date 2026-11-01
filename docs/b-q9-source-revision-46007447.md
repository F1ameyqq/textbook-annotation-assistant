# Q9 来源修订 revision 7

反思第9题的五处原图转写已进入实际正文：补回四组因果符号、修正“妈蚁”为“蚂蚁”，并把路径字母间误识别的汉字“一”改作长横线。完整操作及父版本位于 `tests/fixtures/book46007447/q9-source-revision-plan-v1.json`，内部 revision 7；它保留 Q16 revision 6 的三行与11分式、旧Q9公式选择和全部原始观察。

原图分别为 `viewer-173`（印刷25页）和不同的 `resource-173`（印刷26页前缀）。声明的原片段、范围、前后文字见 `evaluation/book-46007447-q9-source-revision-prepare-v1.json`。独立成员对照两原图及最终输出复核五项，见[原样审核报告](reviews/q9-rev7-independent-audit.md)。栅格可支持长横线不是汉字“一”，但不能精确认证 Unicode 码点；当前 `A—P—B` 仍为模型规范化草稿。

沿既有14阶段实跑，首次12前序缓存与末2阶段重建，重复全14缓存，运行审计均接受。最终 G07 `content-graph-ceb23a5e1a5ec1fb720922cf`、Check07 `content-check-1f620c205eeb19ba0cfb6124`。引用及完整hash见 `evaluation/book-46007447-q9-master-integration.json`。运行对象在本机 `data/runs/46007447-q9-source-revision-master-v1/`，模型导入和网络连接均禁止，没有新识别调用。

总控和独立复核均比较确认：34题及配答逐字段不变；其他65答案在排除计划引用和派生ID后语义相同；Q9的33原片段、33来源行和边界不变，五个图区未修改；Q16“60 61”及全部公式未回退。当前132项检查比revision6多5项，均为新增编辑的 `CONTENT_EDIT_DRAFT_UNVERIFIED`，不是准确率或自动核准。

章节候选已同步当前引用，revision6候选另存 `book-46007447-chapter-candidate-q16-rev6.json`。完整题页、19未归属身份和人工验收仍开放，MODEL_DRAFT/HOLD，A接收PENDING_A。既有Q16后继包继续固定其revision6，不冒充本次Q9输出。
