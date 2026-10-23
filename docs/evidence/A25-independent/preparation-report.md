# A25 独立验收准备交付

`PREPARATION_COMPLETE / WAITING_EXECUTION`。已完成有限验收标准，尚无本轮冻结产品提交，因此产品验收、有限产品测试与实源/保存结论全部 `NOT_RUN`。

验收者 `01a166e8-3f23-7192-a560-4724adca74b1` 已由根状态登记为 `gpt-6.1-sol / xhigh`，协调者和执行者与任务相符。准备输入在独立私有目录原字节隔离；未读取作者活动工作树，未运行产品、浏览器、平台、OCR 或模型，也未接触 profile、根共享暂存区或根调度状态。

固定交付文件：

- `review-standard.md`：14 项最小验收边界、冻结包门槛、分层结论与剩余 live 条件。
- `preparation-inputs.json`：根指令/任务/状态快照、初始失败、B 固定基线 12 个参考文件的大小/SHA256，以及 13 条 Git 只读命令及原输出路径。
- `preparation-observations.json`：本阶段状态、身份、已核首错与零产品执行计数。
- `prepare_intake.py`：已执行一次的独立证据拷贝/哈希 helper；只读 Git 和固定输入，不导入产品。
- `preparation-verification.json`、`preparation-status.json`：交付完整性复核及本轮终点状态。
- `preparation-files.sha256`：上述公开交付文件的固定 SHA256 清单；其自身 hash 另见本对话最终交付。

原始 stderr 的 1371 字节和 SHA256 `6cf231091eb51eb51542f57bcb6ea11e15279c696e612688e3ab2d48483fbfed` 与初始登记一致，进程 exit1。该错误仍为本机 import 阶段 `annotation.runtime` 缺失，不能据此认定平台失败或消耗 live。B 已发布第一课时成功、旧 194 套件及全部旧预算/OCR 未重跑、未改写。

准备 helper 命令为 `python D:/1800/docs/evidence/A25-independent/prepare_intake.py`，exit0，实际输出为：

```json
{"status": "WAITING_EXECUTION", "baseline_reference_files": 12, "git_readonly_commands": 13, "initial_stderr_sha256": "6cf231091eb51eb51542f57bcb6ea11e15279c696e612688e3ab2d48483fbfed", "initial_exit_code": 1, "product_tests": 0}
```

验收者曾有一次 PowerShell 只读命令引号错误；原异常及修正方式已列于标准，未计为产品缺陷，未掩盖或引起产品重试。私有 helper 的工具返回执行输出见 `D:/1800/.local/stages/a25-independent-20261023/preparation/helper-process.json`；其中明确标注为工具文本观察，未冒充独立捕获的进程原 bytes。

下一步由调度提供确切冻结提交、完整 raw 依赖清单、新源与完整基线、审校材料及具体计划，再通知本对话审查。当前不自动进入产品审查、不发消息、不创建子智能体/聊天、不接触平台。任何只读 PASS 都不升级为本轮具体保存授权。
