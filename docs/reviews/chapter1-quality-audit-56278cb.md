# 46007447 第一章独立质量与回归审核

审核时间：2026-10-17，Asia/Shanghai  
角色：第一章 B 侧独立质量成员（机器审核，不替代人工内容签核或 A 接收）  
初始缺陷基线：`c3cc2df7a0be24c125c83681c0499c0d328d78f6`  
首轮修复：`3b6b88ef47f60286f998c1095c7c06660429b6db`  
本报告固定审核提交：`56278cbb7e65c613e723ce7c34168e9190e77cf1`

## 结论

第一章仍为 **HOLD**，不能称为完整章节交付。六个已观察资产的字节与尺寸可复核，但章节来源库存尚未冻结，题页、答页、目录、viewer/resource/印刷页之间也没有完整稳定映射。题、答案和材料分母仍为 `UNKNOWN`。当前局部图谱仍只有 34 题、66 答、34 个唯一候选关系、32 个未链接答案、19 条未归属数学来源及 127 项未决检查；所有内容仍待独立人工核对。

机器门禁层的 11 类独立恶意/真负例在固定提交上全部 fail closed：陈旧内容哈希、无当前绑定、页角色错置、资产别名、重复/悬空关系、不完整或重复人工声明、材料页角色及多分片页阅读顺序均不能静默通过。相关 34 项仓库回归和 11 项独立回归均通过。工具的 G2 结论仍恒为 HOLD，机器结构通过也不会冒充人工或业务验收。

Q16 已形成来源绑定的 revision 6 模型草稿。三行正文、11 个分式槽、17 个来源片段和原图区域均进入实际 14 阶段重放；独立目视复核发现 revision 5 在“60 61”之间无证据插入逗号，revision 6 已改回空格。当前 G07/Check07 内容哈希与引用可独立重算一致，仍为 `HOLD`、`complete=false`、`transcription_verified=false`、`business_acceptance=false`。这是一项有来源的模型草稿改进，不是人工 gold。

固定提交还有一项 P2 版本边界：仓库中的 `book-46007447-chapter-candidate.json` 仍引用 Q16 revision 6 之前的 G07/Check07。用当前 revision 6 对象重适配后，34 题、66 答及材料对象逐项不变，只有 `source_basis` 的不可变引用更新；门禁仍为 8 gaps、machine/G2 均 HOLD。旧候选可作为历史负例，但不应称为 revision 6 当前图谱的精确投影。

## 验收队列

### 来源分母与页身份

| 队列项 | 固定提交证据 | 状态 / 关闭条件 |
|---|---|---|
| 章节稳定身份 | 目录候选 `dir-1792063578574-ug3232apl`；章节候选仍 `chapter_id=null` | OPEN：需独立目录核对并绑定冻结 manifest |
| 完整页分母 | 只观察 6 个资产；`inventory_frozen=false`；可见印刷页为 2、3、4、6、25、26 | OPEN：至少缺印刷页 5，且全章起止、题页、答页均未冻结 |
| 真实字节 | 六图 6/6 SHA-256 和解码尺寸复算一致 | LOCAL VERIFIED：只证明六个已观察字节，不证明整章完整 |
| viewer/resource 映射 | `viewer-173` 与 `resource-173` 的 SHA、尺寸不同；后者只消费前缀 | OPEN：不得按数字 173 合并 |
| 题、答案、材料分母 | 均为 `UNKNOWN`；全书 214 页及目录 22 个已有题节点都不是章分母 | OPEN：需独立逐页清点，保留缺失和争议项 |
| 来源重复/别名 | 同一路径或同一 SHA 冒充两个页的负例现已拒绝 | FIXED IN TOOL；真实页身份仍须来源证明 |
| 多资产页顺序 | `required_asset_ids` 明确为页内阅读顺序，输出不再按资产名替代 | FIXED IN TOOL；仍需调用方提供正确顺序 |

### 题答、材料与未归属来源

| 队列项 | 当前证据 | 状态 / 关闭条件 |
|---|---|---|
| 题候选 | 34，全部 `UNVERIFIED`，无来源 page_id | OPEN：与独立题分母逐项对账 |
| 答案候选 | 66，全部 `UNVERIFIED`；34 个候选链接、32 个未链接 | OPEN：逐答绑定稳定 question_id 与答页 |
| 共享材料 | 当前安全投影为 0，但 `material_inventory=UNKNOWN` | OPEN：0 只能由冻结分母证明 |
| 19 条未归属来源 | 4 组：`topic1-examples` 2、`math-world` 5、`topic2-example` 6、`topic2-training` 6 | OPEN：补题页/公共身份后逐条归属或排除 |
| 重复/悬空关系 | 重复 answer ID、非数组关系和悬空 answer ref 均拒绝 | FIXED IN ADAPTER |
| 页角色 | question/answer/material 引用错误角色均拒绝 | FIXED IN GATE |

19 条来源行固定为：

- `topic1-examples`：`viewer-173/ocr/86,87`
- `math-world`：`viewer-173/ocr/102,104,108,110,112`
- `topic2-example`：`viewer-173/ocr/111,113,114,115,116,117`
- `topic2-training`：`viewer-173/ocr/119,120,121,122,123,125`

G07 账本中的 19 个 `UNASSIGNED` line_id 与 Check07 的 19 个 `ANSWER_UNASSIGNED_CONTENT` issue 精确相等，缺失 0、额外 0。这只证明当前投影没有漏报这些行，不解决题目身份、公式转写、混合行几何或阅读材料图形范围。

### Q4、Q9、Q16 与图形

| 对象 | 独立核对结果 | 当前状态 |
|---|---|---|
| Q4 | 已知 OCR 标量为 `13`；历史 `1:3` 错误由规则拦截；revision 6 集成前后六个 Q4 答案对象逐字段不变 | HOLD：还需原图逐字符人工核对 |
| Q9 | 33 原片段、15 呈现区及正文语义在 Q16 修订前后不变；相邻 `resource-173` 仍只作为前缀来源 | HOLD：缺对应题页、完整续页及稳定跨页映射 |
| Q16 | revision 6 计划 `content-revision-plan-70c5d835c849ff68047554f9`，hash `540f9f7f…`；17 片段按 7/3/7，11 公式槽；原图 crop 绑定通过 | MODEL_DRAFT / HOLD：所有选择均非内容验证，仍需人工逐字逐符号核对 |
| 图形 | 当前 5 图；仍有图形/公式、范围和共享材料结构问题 | HOLD：逐图绑定页、bbox、题/材料身份并核对完整范围 |

Q16 当前文本开头为 `16.解：（1）60 61（2）…`。revision 5 曾写作 `60，61`，但原图只显示空隔，OCR 也是两个独立片段，没有逗号证据；revision 6 只把这一字符从逗号改为空格，其余七个 Q9 操作及 Q16 公式修订保持不变。revision 6 完整归档 revision 5，两个计划 payload 哈希均重算匹配。

当前 revision 6 G07：`content-graph-2761436bca06fe2cd4f33e36` / `43db5fa9d0becf97d37f9465d524ed4c81b66b22e1e812606cbaebae0c1604c4`。  
当前 revision 6 Check07：`content-check-acef084b0cc35a112c5122fd` / `a367b50031820abc9bddb065e6e4679cb9ad25304e129ff1843714a64130e9f7`。

两个 payload 的规范化 SHA-256 均等于声明值，Check07 的 `graph_ref` 也精确绑定上述 G07。实际结果仍是 34 题、66 答、32 未链接答案、127 issues、HOLD。

## 机器 fail-open 修复核对

初始基线复现的 11 类缺陷及固定提交结果：

1. 不完整或空 reviewer 声明仍 machine PASS：已修复，明确产生 gap/HOLD。
2. 重复 reviewed question/answer ID 只经 set 比较而通过：已修复，要求非空且唯一。
3. `PASS+0` 检查不绑定当前 manifest/candidate：已修复，缺失或陈旧 binding 拒绝。
4. G07/Check07 只信声明哈希：已修复，重算 payload hash。
5. question/answer 页角色互换：已修复。
6. material 引用 question 页角色：第二轮已修复。
7. 同一资产身份别名到两个页：已修复。
8. 范围清单同一路径/复制字节冒充两个页：已修复。
9. adapter 接受重复 answer ID：已修复。
10. adapter 静默丢失悬空 answer ref：已修复。
11. 多资产页按 asset_id 排序而破坏声明阅读顺序：第二轮已修复并写入文档。

固定提交未发现上述类别的新 fail-open。人工声明字段仍只是输入声明，工具不会签发 G2 人工认证。

## 当前性与版本边界

仓库固定候选 SHA-256 为 `ab104f491d41d68088d5f06e97ee499d17f9ad1cc53a0522664b32549924fa61`，其 `source_basis` 指向旧 G07 `content-graph-d8d0…` 和旧 Check07 `content-check-a620…`。从 revision 6 当前 G07/Check07 独立重适配得到候选 SHA-256 `52bc31898e8905e3abafc05c1989d98e3e4125a93781247aa1a14529ad076d69`。

两候选的 questions、answers、materials 逐对象相等；差异只在 `source_basis` 的图谱/检查不可变引用。用同一未完整 manifest 运行新候选，报告 SHA-256 `ad7216e5dd8e8a6bc122372532ba78daa0825f388a36e60eb565b69bff0d7665`，仍有同样 8 个 gaps，machine/G2 均 HOLD。因此这是 P2 的谱系/命名一致性问题，不改变业务结论；关闭方式是保留旧候选为历史文件，并把“当前候选/负例”刷新到 revision 6 引用。

## 测试、真实样本与人工验收边界

- 34 项仓库测试通过，只说明编码的门禁性质在固定提交上成立。
- 11 项独立恶意/真负例通过，覆盖初始发现和第二轮残余；它们不证明未知的新攻击面不存在。
- revision 6 的实际冷/暖重放、内容哈希与引用闭合证明产物可复现，不证明公式和中文逐字符正确。
- 6 张图 SHA/尺寸一致只证明字节身份，不证明 page_id、章节归属、页角色或完整分母。
- `accepted:true` 仅表示内部结构/执行接受；与 `decision=HOLD`、`complete=false`、`transcription_verified=false` 并存时，不得写作内容或业务验收。
- 本审核不填写人工核准、不修改 A 状态、不宣布 A 接收、不操作网站、不重做交接包。

## 固定提交上的命令与实际结果

| 命令 / 检查 | 退出码 | 实际结果 |
|---|---:|---|
| `git show --check --stat --oneline 56278cb` | 0 | 无 whitespace error |
| `python -X utf8 -m unittest tests.test_adapt_chapter_candidate_b tests.test_prepare_chapter_scope_b tests.test_chapter_delivery_b tests.test_source_coverage_report_b -v` | 0 | 34 tests OK，1.086s |
| `python -X utf8 work/chapter_quality/proposed_regressions.py -v` | 0 | 11 tests OK，1.533s |
| revision 6 graph/check payload 规范化 SHA 重算与 `graph_ref` 对账 | 0 | 两 hash 匹配，Check07 精确绑定 G07 |
| revision 5/6 plan payload、文件 SHA、previous archive、operations 快照对账 | 0 | 均匹配；7 个非 Q16 操作相同，Q16 唯一内容差异为逗号→空格 |
| revision 6 当前 G07/Check07 适配 | 0 | 34 题、66 答、0 source pages、PARTIAL/HOLD；候选 SHA `52bc3189…` |
| revision 6 候选 + 未完整 manifest 门禁 | 0 | 8 gaps，machine HOLD，G2 HOLD；报告 SHA `ad7216e5…` |

## 复现文件

- 初始行为复现：`work/chapter_quality/repro_gate_false_passes.py`
- 独立 11 项回归：`work/chapter_quality/proposed_regressions.py`
- revision 6 当前候选：`work/chapter_quality/candidate-q16-rev6.json`
- revision 6 当前负门禁：`work/chapter_quality/delivery-q16-rev6.json`

这些文件位于独立质量成员自己的工作目录；共享仓库未由本审核修改。后续若新增来源页，应先更新冻结来源分母，再复跑同一组内容哈希、身份、重复/遗漏、角色、顺序和人工边界检查。
