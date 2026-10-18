# A01 离线样例

本目录 `bundles/46006966/exchange.json`、`bundles/46007447/exchange.json` 是实际归档导入结果。图像、目录和历史导出均来自已存在的离线证据，不是合成识别结果。**scope_manifest 只是参考记录，完整性未知；禁止当作整页/全书独立分母。**

在仓库根目录运行（PowerShell，已安装 Python 3.9、Pydantic 2.12.5、Pillow 11.3.0）：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python examples/a01/consume.py examples/a01/bundles/46006966/exchange.json --book-id 46006966
python examples/a01/consume.py examples/a01/bundles/46007447/exchange.json --book-id 46007447
python -m unittest discover -s tests -p 'test_a01_*.py' -v
```

重新导入要使用不存在的新目录，命令不会覆盖已有产物：

```powershell
python examples/a01/build.py '<新的独立目录>/a01 bundles'
python examples/a01/verify.py '<新的独立目录>/a01 evidence'
```

完整复制单本书目录后，从不同 cwd 使用脚本的绝对路径和已设好的 PYTHONPATH 运行同一个消费者；公共 `annotation.contracts.load_bundle` 不依赖本仓库资料路径。A01 消费者额外完整解码 JPEG、检查映射及书籍绑定，并始终报告 `coverage_eligible=false`。

旧书六图/250元数据页，新书两图/214元数据页；十条/四条图像来源关系分别去重。历史越界框按原字节保存在 history，不生成合法 OriginalBox。四份缺失原始 JSON 不由脱敏数据补冒；第五条外机截图来源不可访问，但仓库现存同摘要 `workspace1.jpg` 已单独保留。

规范和增量提案见 [说明](../../docs/a01-source-geometry.md)，实际验证及限制见 [执行报告](../../docs/tasks/A01-execution-report.md)。本目录不包含平台快照、平台操作、OCR、模型输出或 coverage PASS。
