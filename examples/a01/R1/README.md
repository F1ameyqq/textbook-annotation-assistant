# A01 有界 R1 复现

本目录仅覆盖正式 REWORK 的 R01–R04，状态 REVIEW。原固定包保留在 `../bundles/`，本次新导入包在 `bundles/`。合同仍为 C01 `1.0.0-a-proposal`；来源实现为 `a01-static-1-r1`，几何实现为 `a01-geometry-1-r1`（G01规范和公共API不变）。

在固定工作树根目录，使用已安装环境，全程离线：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B -m unittest discover -s tests -p 'test_a01_*.py' -v
python -B -m unittest discover -s tests -p 'test_contracts*.py'
python -B examples/a01/R1/probe.py '<新的R1证据目录>'
python -B examples/a01/consume.py examples/a01/R1/bundles/46006966/exchange.json --book-id 46006966
python -B examples/a01/consume.py examples/a01/R1/bundles/46007447/exchange.json --book-id 46007447
```

`probe.py` 复放7个几何及9个重新seal的来源反例，退出0表示16个具体反例符合执行者预期，不是独立验收ACCEPTED。已保存输入、预期、实际、模块路径和源码摘要；来源变异只保留相对基准包变化的文件，资产来自保留的原固定包，可用 `cases.mutated_source` 重建。

`validate_delivery.py '<新的证据目录>'` 重跑旧/新两书消费者及新包搬运，并核对本次任务基线中的旧交付/原输入摘要。`examples/a01/verify.py '<新的证据目录>'` 运行A01/C01套件并验证旧包搬运。设置TMP/TEMP时要使用本任务普通临时目录，例如 `examples/a01/R1/tmp/`；`.local/` 是来源输出保护范围，不能作为这些套件的输出临时目录。

原独立几何脚本 F04 的构造未捕获异常；R1按任务约定选择显式拒绝不可表示的大整数。复验应按既定“明确拒绝或精确保留”条件判定，R1回归已同时验证合法上限和越界拒绝。原正式脚本和证据未改写。

S01公共自动放行门禁、D01根Pillow依赖声明仍由主调度负责；本次不修改公共合同、根依赖或父入口。没有浏览器会话或待释放资源。详见 [R1执行报告](../../../docs/tasks/A01-rework-R1-report.md)。
