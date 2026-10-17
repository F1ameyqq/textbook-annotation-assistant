# D01：Pillow 依赖集成准备

日期：2026-10-17。状态：**PREPARED / NOT_IMPLEMENTED**。本轮只读盘点，不构成依赖修复或清洁安装验收。等待 A01 被接受并完成范围明确的本地集成，再由主调度实施根依赖变更。

## 本地事实与候选

- 根代码 `0e80621ea945dca17b23f95db7bb35ce15aa5c77` 的 `pyproject.toml` 只声明 `pydantic==2.12.5`，Python 要求为 `>=3.9`。
- A01 冻结交付 `c3aff9598b6705ab4122062615a13ae3774698b2` 中 `src/annotation/source/static/importer.py` 顶层直接导入 `from PIL import Image`；来源消费需要 `open/verify/load/format/size/DecompressionBombError`。这属于默认离线来源流程。
- 本机 CPython 为 3.9.13；已安装 Pillow 11.3.0 的本地包元数据声明 `Requires-Python: >=3.9`。该证据不能确定最低可用 Pillow 版本。
- A04 冻结交付 `3e4dba5676c2dc4a71d7826827a76df11017a68b` 未补根依赖；报告环境包含 Pillow 11.3.0、Playwright 1.58.0。PIL/Playwright 在采集/启动会话处延迟导入。

最小候选是在根 `[project].dependencies` 增加 `Pillow==11.3.0`，保留 Python 要求不变。选择 core 是因为 A01 默认入口导入即依赖 Pillow；若以后明确提供仅合同安装形式，再讨论 `source` extra。此候选不扩展到 Playwright、浏览器安装或新的基础设施。

## 后续独立安装验证

以下命令尚未运行。实施时使用已接受 A01 加 D01 的确切集成提交，记录解释器、实际安装来源、依赖版本、命令、退出码、样例及结果。创建不存在的新虚拟环境；不要覆盖已有环境或使用 `--system-site-packages`、editable 安装替代验证。

```powershell
py -3.9 -m venv .local\d01-clean
.local\d01-clean\Scripts\python.exe -m pip install .
.local\d01-clean\Scripts\python.exe -m pip check
.local\d01-clean\Scripts\python.exe -I -c "import annotation.source.static, PIL; print(annotation.source.static.__file__); print(PIL.__file__)"
.local\d01-clean\Scripts\python.exe -I examples\a01\consume.py examples\a01\bundles\46007447\exchange.json --book-id 46007447
```

`consume.py` 已静态核对参数和实现：不注入源码路径，调用公共加载与 A01 来源加载并做完整图像解码。使用 `-I` 忽略外部 PYTHONPATH/用户包，核对导入来自新环境安装位置。后续应再搬运两书样例并换 cwd 消费，确认非仓库源码偶然可用；来源输出目录不得违反 A01 路径保护规则。

尚未验证：清洁安装、包发现、实际 JPEG 解码、样例消费、干净环境中的相关回归。单个 Pillow 版本固定不等于完整传递依赖锁定。本轮未安装、联网、跑测试或修改依赖；D01 仍未解决。范围与来源限制见 [A01 R2 复验交接](A01-review-R2-handoff.md)；来源完整性是独立的 [S01](S01-eligibility-preparation.md)。
