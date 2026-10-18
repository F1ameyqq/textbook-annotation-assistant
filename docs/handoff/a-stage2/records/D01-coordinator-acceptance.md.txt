# D01 主调度接受与本地集成

2026-10-17，Asia/Shanghai。D01 结论：**ACCEPTED 后已 INTEGRATED（仅本地）**。

- 固定交付：`48accd7d885fbc7ecdd8b438ada33a0eafd5bc55`；唯一产品差异为根依赖增加 `Pillow==11.3.0`。
- [独立报告](D01-review-report.md)和[清单](../evidence/D01/review/formal/sha256-manifest.json)的199份文件按原字节核对并归档。清单SHA256：`37e48f96b4dd57e006a8f3a518745537b1ce66cbe1cf9e0be00546f3f671f2e9`。
- 主调度在独立验收环境重查 pip check、wheel/安装来源、两个搬运来源包的公开消费，4条命令均退出0，输出写入新的[接受证据](../evidence/D01/coordinator/acceptance/checks.json)。这是复核现成的独立清洁环境，没有宣称再次创建新环境。
- 正常合并确切交付，集成提交 `c78c8a123437e6c53096e0c48f1dd14aad10c2c3`。实际根目录15份产品/配置Git blob与接受版本相同；两书公开consumer均退出0，见[集成检查](../evidence/D01/coordinator/integration/checks.json)。未重复未变化的全套测试。
- 独立验收首次合同测试的helper采集遗漏及其单项续跑原件保持；不把首次70项运行改写为一次全通过。

仅证明记录的 CPython 3.9.13 / Windows 非editable安装与6/2张参考来源消费。没有平台、模型或B兼容验收，不解除A03/I01阻断。该集成未推送；远端 `codex/a-stage1-handoff` 仍是此前发布版本，文档中的显式安装Pillow步骤仍适用于该远端版本。
