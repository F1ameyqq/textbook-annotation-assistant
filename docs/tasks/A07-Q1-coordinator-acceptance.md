# A07：固定真实第1题离线模拟的调度接受

2026-10-18。主调度核对固定独立报告、原字节清单、读回、拒绝记录及实际进程释放，并使用已接受的 C01 代码复验归档信封、资源与计划准入，记录 **ACCEPTED**。范围仅为用户核准的书46007447第1题真实来源到 A 本地模拟目标；不表示 B 共同采用、人工视觉复核或真实平台通过。本地集成须另行核对后记录。

## 固定交付与边界

- 工作流 `b1c84db9d1d5603a4fd6aa5487d7c45ec6fca50a`，运行产品 `6dad9b9a40a10989c102d91cf7b54f19c012015f`。
- 作者交付 `d2e710c817cf85505ac4fad4919dd51d1062d33a`；独立交付 `efe440d07d3600ee9755f1709778a2a742bb2f52`，后者的真实父提交是运行产品，不是作者证据交付。
- 作者 `01a14edd-f319-7b70-8993-62e04de3a2d4`；独立验收 `01a14edb-bdc9-7370-890c-3b301b6ea414`。独立最终 cursor `65496636-3236-4063-9ba6-c8ca5d3c3561:3`。均已完成释放，不续派成功业务。
- 用户[授权记录](../approvals/A07-Q1-offline-business-approval.json) raw SHA256 `cf6f675cfd98d438d7d465fc553e0ebbf1bfff71bd62f8453854f8527015cb6c`；B固定提交 `ef6ba4dd083e7fd5378e80123b2b038dd11d7052`、新ZIP SHA256 `3039645ca69c2604f542c479cb180049604788a3ca28ffac1b5063dee533afac`。
- 独立清单54成员、10,195,346 bytes，另排除清单自身；SHA256 `f9d259222d94bfe54147e4804a6cf23cbf16f6b769af6963f5b586d849485bf8`。报告 SHA256 `3b69f67172c8bb24f28c8261549f1d6b25de5a741a044787d6e037654694f242`。

## 接受证据

独立验收在自己的目标完成一次完整正常试验：1题、1计划、1次 CREATE_FRAMES 实际内存变更，由0框变为6框；独立读回序号1/2、差异为空，题干/四选项/答案D坐标及题答绑定正确，辅助裁片、括号、解析未新增成框。真实来源保持 OBSERVED，目标、计划和回执为 SYNTHETIC / SIMULATED；政策 A_INTERNAL_PROPOSAL / PROPOSAL_ONLY。五项 PRE_APPLY 和显式 TARGET 由代码计算，写前复算及 C01 门均通过。

独立计划摘要 `085db1af2db83282603a655150099b9fdc79ff9a6c28879f725753e6cc307456`；模拟回执 `a07-receipt-a07-review-1` revision1，摘要 `e9c63fcbc8fa3571dcb1d943d1a30be627e193efc061ceb501e7cb537d6921d3`。状态继续 NOT_SUBMITTED / PENDING，未连接平台。

九项独立拒绝检查及正常试验后的单独重放拒绝，共10次调用，均零新增变更。覆盖缺/假授权、输入替换、历史身份替换、平台模式、错目标、越范围、目标漂移、七框重封计划及真实执行后重放。作者与独立各消耗1次正常尝试、1次成功、1次dispatch；不重复成功试验，不重跑旧A03/A06/I01。

主调度以 raw Git blobs 逐成员重算54项独立清单，确认候选/工作流旧路径全保全；另由只读子代理核对20个报告链接、作者63成员及主线合并范围。作者新增64路径和独立新增55路径无交集，预计仅新增119路径。独立41552/59684/73044三个PID现场复查均不存在，工作目录干净。

主调度只导出归档结果和原主线 C01 源码，执行 `load_bundle(exchange.json)`、`load_bundle(pre-execution.json)`（含资源核验）及 `assert_plan_ready`，再核对六框坐标、题答关联和原始读回摘要；没有创建新目标、执行计划或重跑业务。记录见[有限复核](../evidence/coordinator/a07-acceptance-20261018/fixed-artifact-recheck.json)，脚本为[check_fixed_delivery.py](../evidence/coordinator/a07-acceptance-20261018/check_fixed_delivery.py)。首次调度脚本误将独立9项拒绝列表当作含重放的10项，已明确另读 `replay-rejection.json` 后通过；[计数纠正记录](../evidence/coordinator/a07-acceptance-20261018/checker-count-correction.json)保留，未更改产品或复跑业务。

## 后续与限制

拟分别正常合并作者及独立兄弟提交，保留主线全部已有路径及两方证据，核对119新增路径的 mode/type/blob，并只做导入和归档合同有限复验，再记录 INTEGRATED。旧源码、pins、根依赖、A06/I01、B原件/HOLD/原Check/未归属账本不改。

该结论闭合 A 本地的“一道真实B题 → 新C01 → A计划 → 模拟回执”。B共同采用、共同验收、平台资格和A04真实项仍未证明。新Q1确认、授权和A07材料未推送，也未向B发送消息。
