# 真实续页的本地图谱应用与回滚

2026-10-17，B 侧；基线 `4378b2c1149d6e0d54d0c88bf1f6f91fbb3b5072`。本轮接入上一轮已验证的结构建议，推进长期目标 L1；不修改网站，不生成 A 执行计划或提交动作。

## 当前实际行为

`continuation_apply.py` 每次重新验证当前来源、图谱、续接证明、原图捕获像素及组合标题，拒绝过期引用、被更换的图片或调用方自行标注的“通过”。输入不变，输出新的 `b-graph-trial/0.4` 及可回滚归档。

真实反思第9题已在新本地图谱中续接：

| 内容 | 结果 |
|---|---:|
| 原源页片段，逐对象保留 | 8 |
| 目标页新增来源片段 | 25 |
| 合计原始来源片段 | 33 |
| 可呈现正文文字区域 | 10 |
| 完整图片区域（图3–7） | 5 |
| 图内诊断OCR，不单独画文字框 | 23 |

15个呈现区域保留源页→目标页顺序和各自资产坐标。原始片段保留原文、字符区间、父行、引用与位置；图内OCR通过独立 `fragment_representation` 指向图片。`answer.text`只聚合正文，图片标签不混入正文。原源页顶层bbox不扩大为跨页框。

目标25行从UNASSIGNED变为CONSUMED，原其他账本行、34个题目、其余答案及原配答引用保持不变。两条新标题仍EXCLUDED，不被答案消费。当前202条答案来源账本为154 CONSUMED、29 EXCLUDED、19 UNASSIGNED；总答案片段195。第9题对应题目页未在当前四张题目样本中，不伪造新题或新增配答。

只有第9题已由结构证明解决的旧 `ANSWER_BOUNDARY_UNRESOLVED` 标为结构已解决并绑定证明/检查；旧问题对象与原flags继续归档，其他问题不删除。新 `active_assembly_flags`区分当前待处理问题。`structural_complete=true`、组装边界BOUNDED只代表局部结构，`complete=false`、`transcription_verified=false`，全局HOLD。文字、公式与图意尚未核准。

## 独立检查与回滚

`continuation_quality.py`不导入或重跑生产者生成预期。它直接比较原始图谱、证据与已重新验证的输入证明，逐项核对新片段、实际归属、类型/坐标/像素、混合呈现顺序、正文聚合、账本、标题、其他实体及状态。即使片段和账本同时修改、内部摘要重算，仍检查实际内容变化。

图谱内保存完整原图谱、证明与检查归档，但内部摘要不能充当独立版本凭据。CLI另存 `application-receipt.json`，记录原始输入及派生图谱引用；回滚必须同时提供该回执和同版证据。回滚核对外部原版本引用、图谱身份/摘要、归档及基线投影后恢复原对象。后续编辑的版本不能拿旧回执静默回滚；即使内部guard、摘要或ID被协调重算也拒绝。

这是本地版本防误覆盖机制，没有声称回执是不可篡改签名。整书任务的持久化调度、崩溃恢复及多人修改合并仍属于后续L2/L5。

## 重放与恢复命令

仓库根目录，输出目录须不存在；正常重放不需要网络、OCR引擎或原始全图：

```sh
python -m unittest discover -s tests -v
python tools/replay_apply_b.py --out data/runs/46007447-applied
python tools/replay_apply_b.py --rollback-from data/runs/46007447-applied/question-graph.json --evidence data/runs/46007447-applied/evidence.json --receipt data/runs/46007447-applied/application-receipt.json --out data/runs/46007447-restored
```

应用输出包括证据、原图谱、新图谱、证明、独立检查、独立应用回执及回滚自检结果。恢复输出原0.3图谱；不改写输入文件。提供 `--source SOURCE/source.json --adjacent-source SOURCE/46007447_resource_173.jpg` 可额外重检原5张图与相邻原图/裁片像素。

235项回归通过（此前193+新增42）；覆盖应用/回滚、独立检查、故障审计及CLI。CLI在禁止网络和OCR运行库导入的子进程中完成应用和回滚。Git导出重放与结果摘要见 `evaluation/book-46007447-local-application.json`。

## 消费者迁移与后续

0.4中受影响答案的 `regions` / `render_regions` 是 `b-render-region-trial/0.1`，使用文字/图片类型和 `source_fragment_ids`。其他答案原对象仍沿用0.3表示，新消费者须按答案的 `regions_schema` /迁移字段处理；不能把33个来源片段当33个可绘制文本框。旧0.3检查器不接收0.4，A的公共类型与消费者仍待对齐。

本轮另对11个缺失数学角色做22次局部CPU OCR探索。9组两次完全一致、2组不一致；其中一处两次均读为 `a+1`，原图可见上标，独立目视开发参考为 `a²+1`。这是“置信度或一致不能证明转写”的真实反例，未作为核准文字写入布局。原始结果、源像素/预处理/模型摘要见 `evaluation/book-46007447-math-role-probes.json`；可复用的识别后端与独立回归仍待实现。

接下来推进分子/分母的可追溯补读及上标质量检查、19条数学来源身份、整书来源/目录清点和批次恢复；同时继续A合同与独立验收样本建设。当前局部结构应用成功不代表整书、复杂题型或业务验收完成。
