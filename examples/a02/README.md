# A02 离线模拟入口

全部输入、原图、报告和效果证据为 **SYNTHETIC**；计划和执行为 **SIMULATED**。
PRE_APPLY 明确为合同桩，不是 B 的算法或质量结果。没有浏览器、平台、OCR 或模型调用。

从交付 checkout 根目录运行，Python 3.9+、已存在的 Pydantic 2.12.5，无新增依赖。
必须设置本树 `src`，避免本机另一个 editable checkout 被误导入：

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m unittest discover -s tests -p 'test_a02*.py' -v
python -m unittest discover -s tests -p 'test_contracts*.py' -v
python examples/a02/run.py --output "$env:TEMP/a02-normal-new"
python examples/a02/run.py --output "$env:TEMP/a02-unknown-new" --fault lost_response
python examples/a02/run.py --output "$env:TEMP/a02-absent-new" --fault not_applied
```

输出目录必须不存在。每次运行保留 `input.json`、相对资产、`planned.json`、`executed.json`、
`final.json`、`target-state.json`、`action-log.json`、完整 `receipt-history.json` 与 `summary.json`。
可独立用 `python -m annotation.contracts validate <输出目录>/final.json` 校验所有资源摘要。
写出交换包使用公共 `write_bundle`，新产物使用 `seal_artifact`，不读取预制 expected 文件。

其他故障：`--fault partial`、`contradictory`、`readback_failure` 均 UNKNOWN；
`--fault lost_response` 实际保存但响应和读回不可用，保持 UNKNOWN；
`--fault response_lost_readable` 响应丢失但独立读回完整匹配，可确认 APPLIED。
`--fault-index 1` 可在第二动作注入故障，前一动作的预期变化不会误判为外部冲突。

选择题输入：`--input tests/fixtures/a02/choice/input.json`，只支持显式 SYNTHETIC 的独立 W 假设。
异常输入：`--input tests/fixtures/a02/exceptions/input.json`，保留 4 题分母、异常、跳过及未入图谱项。
批次内容始终 PENDING、提交始终 NOT_SUBMITTED；框读回匹配不产生 COMPLETED。

完整作者证据复现：

```powershell
python examples/a02/verify.py --output "$env:TEMP/a02-full-new"
```

该命令独立设置子进程 PYTHONPATH、记录环境与代码 SHA、运行两套回归及 10 个演示，输出哈希清单。
输入样例生成器 `build_fixture.py --case normal|choice|exceptions` 只生成输入，已存在文件需逐字相同。
三个固定输入的版本为 `a02-fixtures-1`，依据 C01 `c01-fixtures-1` 的构造区域/资产，不依赖真实平台历史。

## 模块 API 与边界

- `quality.targetcheck.check_target(bundle, graph_ref, snapshot_ref, current_snapshot_ref, policy_ref, config, ...)`
  返回追加 TARGET 的已校验新交换包。逐项检查当前快照、映射、授权、能力、政策及独立范围覆盖。
- `delivery.planner.create_plan(...)` 是纯计算。两阶段 PASS 且绑定一致才生成 READY，调用
  `assert_plan_ready` 时显式传入当前快照；失败报告生成无动作 BLOCKED，缺失/错阶段/错版本抛出 ContractError。
- `SimulationConfig` 是本地模拟配置，不是新公共合同。书/目标/范围、显式目录映射、允许操作、会话模式
  全部绑定到 producer.config_version；mock 执行前复查版本并重新生成动作核对，拒绝重新封签的篡改计划。
- `MockSession.register_target(..., asset_root=...)` 验证实际资源并建立一个内存目标。
  多 SourceBundle 包可显式传 `source_ref`，不猜测新快照框的原图来源。
- `MockSession.execute(...)` 读取本会话当前快照，再走公共资格门与 A02 复算门。
  `read_target`、`read_snapshot`、`action_log`、`receipt_history` 提供与响应分离的防御性副本。

支持自由作答、跨页、共享材料与选定答案闭包、空目标新题、非空目标未映射新题、明确映射且尚无框的已有题。
内部目录通过显式配置映射到平台目录，不根据同名、印刷题号、题序或 bbox 猜测归属。
框保持原图尺寸/摘要绑定，平台角色及公式按文本投影只存在交付层。
组合题、父子投影、七选五、合并 W、多个内部题共享平台 ID 及全部 UPDATE 差量均显式阻断。
这比 C01 的结构允许范围窄；即使给出旧 APPLIED 基线和 frame_update，A02 也不会伪装支持差量或降级新建。

UNKNOWN 后会话按 **book_id** 保留完整回执和暂停依据，换 ID/运行/题/范围、调用方删减输入历史均不能解锁；
另一书可独立模拟。NOT_APPLIED 证明 ABSENT，但旧计划仍不可重放，必须重新检查目标和生成新计划。
任一非 APPLIED 后，剩余动作只读回、不派发；明确无框的未派发动作记录 NOT_APPLIED。

此会话无解除/清历史 API，也没有跨进程锁、持久 intent 或重启恢复。重新启动 Python 会失去内存保护，
不能用于真实写入。C01 没有 ReconciliationResult 类型/验证入口，A03 需由指定负责人补充解决证据和持久恢复合同；
A02 不扩展共享合同、不删 UNKNOWN 历史、不私造字段解锁。证据落盘失败发生于写后时，本会话保留 pending 暂停，
未持久化保护仍属于 A03。
