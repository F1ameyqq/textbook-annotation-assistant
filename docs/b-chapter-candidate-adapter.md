# G07/Check07 到章节候选的只读投影

`tools/adapt_chapter_candidate_b.py` 将明确绑定、版本一致的 B 内部图谱与检查投影为 `chapter-candidate-b/1`。接受 `b-graph-trial/0.7` + `b-check-trial/0.7`，或带显式来源几何修订的0.8配对；混合版本和未知版本拒绝。0.8仅投影同样的候选身份、关系与风险字段，不把几何草稿当作已审核来源。适配器不消费 source descriptor；固定 fixture descriptor 与扩展后的图谱 scope 不同，不能安全地作为同一来源输入。历史0.7负例复现使用：

```powershell
python tools/adapt_chapter_candidate_b.py `
  --graph data/runs/46007447-region-automatic-v1/graph.json `
  --check data/runs/46007447-region-automatic-v1/check.json `
  --out work/46007447-chapter-candidate.json
```

适配器只读输入。它重算两个payload哈希，校验book、scope、精确artifact引用，并拒绝重复身份和悬空关系。上述历史对象为34题、66答、127项问题；后续修订使用其当前检查数，Q9 revision7为132项。输出必须保持 `candidate_state=PARTIAL`、`chapter_id=null`、`source_pages=[]`、章节及各类分母 `UNKNOWN`、全部内容 `OPEN`、checks `HOLD`、人工复核不完整。

图谱中的内部题目/答案 ID 原样保留为候选身份；34 个唯一反向候选链接只作为 `CANDIDATE_OPEN` 关系投影，另 32 个未链接答案的 `question_id` 保持 null。题目和答案的 `page_ids` 都为空并带 `source_page_status=UNKNOWN`；内部 `asset_id` 仅在 `observed_asset_id` 中作为原始观察值保留，不将其转为页面身份。材料数组为空表示没有可安全投影的稳定材料 ID，另有 `material_inventory=UNKNOWN`，不声明章节没有共享材料。

这是可复现的当前负例，不是章节清点。固定证据只有局部观察数据，缺冻结章节/目录身份、独立页/题/答/材料分母和答案来源页映射。输出虽有候选 schema 字段，`chapter_id=null` 是有意保留的未知值；章节 gate 会因缺稳定章节身份拒绝它。G07 与 Check07 指向扩展 scope，但固定 fixture source descriptor 仍绑定较窄的五页 base scope，因此适配器不把它错配成同一来源、也不输出任何 source page 记录。Check07 的 127 项和 G07 的 `HOLD` 也原样限制候选状态。适配器没有调用模型、写平台、制造题目/答案/材料身份、补全目录或人工核准。
