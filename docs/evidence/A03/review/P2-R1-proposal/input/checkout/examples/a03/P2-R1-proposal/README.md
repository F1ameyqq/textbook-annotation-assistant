# P2-R1 静态提案

当前候选为 [candidate-v2/profile.json](candidate-v2/profile.json)，其完整 Schema pins 和 API supplement SHA 必须一起选择。根目录早期 schemas/cases/profile/event-catalog 是未批准草稿，保留原字节及证据归档，不能与 candidate-v2 混用。

[交付报告](../../../docs/tasks/A03-P2-R1-amendment-delivery.md)列出字段语义、明确未闭合项、受影响路径与后续 NOT_RUN 矩阵。

本目录只有新静态作者脚本与 stdlib 检查器。所有样例为 PROPOSAL_UNIMPLEMENTED，不具备原生运行历史、目标观察或接纳权威；报告包中的独立 fact 见证不组成同一合法账本。PRE 五项均 UNAVAILABLE；转换映射为 UNIMPLEMENTED，无已完成新包。

在原执行工作树检查：

```powershell
python -B examples/a03/P2-R1-proposal/check_static.py
python -B examples/a03/P2-R1-proposal/verify_delivery.py --check
```

需要重编写静态值时，`build_static.py --output-dir <尚不存在的新子目录>`；可用 `check_static.py --data-dir <该子目录>` 检查。默认不覆盖现有数据。所有脚本均不导入或运行产品、不打开 DB、不访问网络。
