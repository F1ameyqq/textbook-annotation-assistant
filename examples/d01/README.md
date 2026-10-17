# D01 清洁安装复现

本目录仅为执行辅助，不改变产品模块。正式运行输入为
`c6bebdf43eb93f7a6ae21e96ec07ed155686777d` 加唯一依赖改动的实现提交
`9a7b9d7e374ee7a3ee124c9ff20e0b4003e57464`；workflow 为
`f15f7bc03fac8994ade1642fa7547cbd823c6d43`。执行结果及限制见
[报告](../../docs/tasks/D01-execution-report.md)。

在本独立工作树根目录、PowerShell 中运行以下命令。`reproduce01` 三个目标目录必须不存在；
重跑时另取新名字，脚本拒绝覆盖旧运行、环境及回执。使用自己的 CPython 3.9 绝对路径。
源提交必须可从本地 Git 对象读取；脚本不 fetch/push，不修改全局配置，不下载浏览器。

```powershell
& 'C:/Users/ASUS/AppData/Local/Programs/Python/Python39/python.exe' -I examples/d01/collect.py --receipt docs/evidence/D01/execution/collector-reproduce01 -- --stage .local/d01/reproduce01 --evidence docs/evidence/D01/execution/reproduce01 --python39 C:/Users/ASUS/AppData/Local/Programs/Python/Python39/python.exe
```

`run.py` 从固定 Git blob 导出 `pyproject.toml` 与全部 `src/**`，用不存在的新 venv
和固定构建工具生成 wheel。显式 `https://pypi.org/simple` 仅用于必需的公开依赖；
所有 pip 调用均使用新环境 `python -I -m pip --isolated`。
固定 pip 25.3 的首次下载由 venv 自带 pip 完成，不要求该旧 pip 支持 `--report`；
其制品 SHA 另与 PyPI 公开发布元数据核对。后续构建工具、产品及运行依赖均保存安装报告。
传递依赖仍由当时的解析结果决定，归档清单不等于新增 lock 文件。

`probe.py consumer` 先导入并核对安装位置，再以 `runpy.run_path` 执行未修改的公开
`examples/a01/consume.py`；不插入源码或脚本目录。每次 consumer 前后均保留实际导入路径和摘要。
唯一 `sys.path.insert` 在合同回归模式中加入固定测试目录，该副本没有 `src/`。
原合同测试的子进程会设置指向不存在目录的 `PYTHONPATH`，报告明确区分这一点；
隔离 consumer 与安装探针不依赖该机制。所有功能命令的 cwd 为工作树及构建源码之外的新目录。

进程检查只读查询自有 PID 和精确任务路径，不导出命令行、不终止进程。首次观察结果也保留。
完整执行结束后，用一个不存在的输出路径保存新的观察：

```powershell
& ./examples/d01/observe-processes.ps1 -OutputPath "$((Get-Location).Path)/docs/evidence/D01/execution/process-observation-reproduce01.json"
```

冻结交付的 SHA 清单含产品依赖、所有 D01 辅助脚本、报告与全部执行证据；只排除清单自身。
清单主摘要采用 Git 原始字节；仅 `pyproject.toml` 和逐项列出的 D01 Python/PowerShell 辅助脚本
另有一个固定的整文件 LF→CRLF 摘要，匹配本项目既有自动 checkout 行为。原始日志、输入、
报告及其他证据无替代字节；这不改变旧 A01 的候选集合。具体双摘要见 checkout-byte-audit.json。
使用下面的只读命令核对字节闭包。不要先在冻结副本新增复现输出后再要求其仍等于原交付闭包；
新增复现应在另一个隔离副本进行。

```powershell
& 'C:/Users/ASUS/AppData/Local/Programs/Python/Python39/python.exe' -I examples/d01/verify.py
```
