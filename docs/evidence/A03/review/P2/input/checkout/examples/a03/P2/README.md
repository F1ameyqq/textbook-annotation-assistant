# A03 P2 离线进程演示

这里所有输入、资产、历史和目标效果均为 `SYNTHETIC / SIMULATED`。每个命令使用新的 Python 进程；运行库和目标库独立。输出目录必须为新路径，失败现场不覆盖。作者测试不替代独立验收。

在交付工作目录设置 `PYTHONPATH` 为该目录的 `src` 后，三条最短复现为：

```powershell
python -B examples/a03/P2/run.py --scenario normal --output <全新目录>
python -B examples/a03/P2/run.py --scenario effect-crash --output <另一个全新目录>
python -B examples/a03/P2/run.py --scenario absent --output <第三个全新目录>
```

`normal` 验证多动作效果、重启后读取和旧动作重放拒绝；`effect-crash` 在独立目标提交后以退出码 87 结束进程，再由新进程实际读回并通过 MATCH 解决，效果次数仍为 1；`absent` 在 intent 提交后、目标调用前以退出码 90 结束，再实际读回 ABSENT。两种核对都不能自动重发旧动作。

完整作者过程检查：

```powershell
$env:A03_TEST_EVIDENCE_ROOT = '<全新证据目录>'
python -B -m unittest discover -s tests -p test_a03_process.py -v
```

每个场景保存不可变请求、`argv/cwd/PID`、实际导入位置、stdout/stderr、退出码、独立目标日志、查询/导出结果和 `process-release.json`。故障点标记只证明进程到达控制点；目标效果由 `probe_target.py` 在新进程经公开 API 直接打开目标库核对，不从运行库回执推导。两个 owner 竞争使用双方真实到达的屏障，SQLite busy 使用独立进程实际持有排他事务，不以固定等待时间推断竞争结果。

`prepare.py` 从只读旧合成输入显式转换并重新检查、规划。`history.py` 单独生成旧版真实模拟 UNKNOWN 归档，仅用于 `LEGACY_UNRECORDED` 和跨 scope/书隔离检查；不会补造历史 intent。原始输入、归档和失败字节保留，旧未知状态不能因转换获得新恢复资格。

V01–V10 的作者场景索引在 [scenario-matrix.json](../../../tests/fixtures/a03/P2/scenario-matrix.json)。各项实际通过、失败或未运行，以执行报告和该次保留的 `scenario-result.json` 为准；矩阵条目本身不是运行结果。合同单元检查、过程功能检查及独立验收结论分开记录。真实来源资格、平台能力、内容完成、书级提交和 I01 仍不由这些演示证明。
