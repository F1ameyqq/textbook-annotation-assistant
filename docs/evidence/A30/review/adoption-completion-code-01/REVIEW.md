# A30 采纳与保留恢复：固定代码/launcher 独立评审

结论：**REWORK**。产品 manifest `3ec8c073…`、launcher manifest `a7c33d41…`。本结论只针对本轮固定源码与启动包；不授权 actual，customer_ready=false，1800-a 保持 PAUSED。

## 必须返工 R1

`app/src/annotation/customer/retained_upgrade.py:266–273` 先把 reconcile-retained 操作持久化为 COMPLETE，再执行原 save 行的 store.resolve CAS。CAS 失败时，异常分支只处理仍为 INTENT 的恢复操作，因此已 COMPLETE 的恢复操作不会转为 FAILED_NO_RETRY。

独立真实工作区副本控制通过普通 reconcile_customer 入口，在 store.resolve 写入前注入 Hold。实际结果：调用失败；reconcile-retained=COMPLETE；原 save=UNKNOWN_NO_RETRY 且原 output 未变；当前 job head 和历史 events 未变。恢复并未完成，却留下 COMPLETE 且后续调用会因已有恢复操作被阻止。这违反新补充第1节“恢复失败时原save保持原state/output；新恢复操作若已开始则记为FAILED_NO_RETRY”的约定。

应使恢复完成记录与必要的原 save CAS、当前 job/event 发布一致；必要提交步骤失败不能留下 COMPLETE，亦不能丢失原 UNKNOWN/失败历史。补充 CAS 与末尾 job/event 提交故障控制，冻结新后缀后再审。评审未修改产品。

证据：`raw/probe_commit_failure.py`、`raw/commit-failure-control.json`；完整状态与路径见 decision.json。

## 已完成核验

- 两份 manifest 自身和全部声明成员逐一 SHA256/bytes 匹配：产品253源码+152证据+report=406，launcher7。完整副本与原文件字节一致；产品额外receipt包装件也复制校验，但不冒称manifest成员。
- Union20 249源码全部核验，差量7改、4增、0删，242旧源码字节未变。既有两份测试夹具修改保留了原断言：仅补原图/来源元数据及import；未以作者“132/10通过”声明替代独立验证。
- 原工作区11,176文件与协调基线逐项匹配，副本原始字节相同；控制前后原工作区全部文件字节不变。未在原工作区构造Store。
- 共享只读解析独立得到的scope与冻结scope逐字段一致：9 runs/302成员、42题、精确Q12与四尾节点/候选绑定。严格比较已到达match=true、37旧题/125旧框保留；随后才触发提交故障。
- 此控制transport构造0、平台调用0、POST0；原UNKNOWN blob、失败reconcile行、历史head/events保留。副本运行66.154秒；验证脚本以成功复现反例退出0，产品不变量失败数1。

## 未完成层

按 frozen-offline-independent-review 技能“出现使接受主张失效的语义反例立即停止”，后续回归、其他反例、名义成功副本、GUI/CLI动态链、launcher预检均NOT_RUN。构建报告精确hash未送达，浮动报告未读；这不妨碍由确定代码反例判REWORK，亦不得据此接受未审层。

协调提出的order/created_at问题已静态查看：ADOPT显式比node/info/parent/source/content/分区/rect顺序；order/created_at在retained expected_extras中，adoption_selection没有独立字段。旧任务第5项本身列node/info/rect，并未显式增加这两项新鲜读回比较。本次停止后不对该边界另作接受或缺陷结论，保留为下一轮精确复审项。record_read(kind=save:book)的COMPLETE读取记录与save intent/POST已区分，未按名称误判为新发送。

本评审是同模型家族、独立新会话，使用共享本机runtime/文件系统；不是外部或异模型独立。冻结输入先校验、隔离，再运行上述独立控制。旧“原Codex不可用/M1”说明属于历史，不用来否定本轮新Codex评审身份。

