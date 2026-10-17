# A01 有界 R2 来源一致性

仅修 R2-01 范围分区、R2-02 历史URL书籍/源索引绑定、R2-03 观察索引来源摘要。状态 REVIEW；不修改geometry或共享合同。新正常包在 `bundles/`，实现版本 `a01-static-1-r2`，旧格式与R1包保留原字节。

固定工作树根目录，已安装环境下离线复现：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B -m unittest discover -s tests -p 'test_a01_*.py' -v
python -B -m unittest discover -s tests -p 'test_contracts*.py' -v
python -B examples/a01/R2/probe.py '<新的R2证据目录>'
python -B examples/a01/R2/verify.py '<另一个新的R2证据目录>'
```

`probe.py` 在包内重算资源与artifact摘要后复放5个明确反例（含N14）；可选 `--official-inputs D:/1800/docs/evidence/A01/review-R1/primary-source-confirmation` 还会只读重放4个冻结的正式输入。它不运行原脚本、不改正式输入。结果记录真实模块路径、源码摘要、资源验证、错误code/location及实际预期对照；退出0不是独立验收。

`verify.py` 实际运行A01/C01套件、原16例、三代两书直接消费与完整复制后换cwd消费，核对本轮baseline中的旧文件、原输入和geometry字节。临时输出位于本任务普通目录 `tmp/`，不使用受保护`.local`。

非零缺页与全部元数据索引被选择的合法构造用例在 `tests/test_a01_rework_r2.py`：未取得expected标识仅为意图，producer标为SYNTHETIC，没有虚构原图/尺寸/摘要，也不提供完整题目分母或覆盖PASS。固定导入器仍只取得六图/两图。

URL处理仅解析归档字符串，保留主机文本，无请求或网络信任认证；N15 precision不是认证字段。S01/D01及B确认仍待主调度。详见 [R2执行报告](../../../docs/tasks/A01-rework-R2-report.md)。
