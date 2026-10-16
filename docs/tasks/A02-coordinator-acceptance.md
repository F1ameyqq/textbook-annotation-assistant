# A02 主调度验收与本地集成

## 验收决定

ACCEPTED：`38aca9dcc8d027409b95193e9cc142c2336b76d3`，R1 实现 `13ddf83083224ffafc17a4f57cf2c1a1a1ae02b2`。范围为 A 侧合成样例的 targetcheck、planner 与内存 mock。独立验收已结束，主调度核对确切版本、报告及证据后确认通过。

- [独立复验报告](A02-review-R1-report.md)，SHA256 `4e664703c54996411d2500ede78514952e53299ce928c9eac30e762d4c086d31`。
- [复验清单](../evidence/A02/review-R1/sha256-manifest.json)，SHA256 `1b13baef9629300554b87def58c0845603b443558c46aa1d8d9ec19e2d9e79ea`；2,874 项长度及摘要匹配，2,039 个历史验收文件与此前 Git 原始 blob 相同。
- [主调度复现](../evidence/A02/coordinator/acceptance-R1/coordinator-check.json)及[清单](../evidence/A02/coordinator/acceptance-R1/sha256-manifest.json)：运行前核对 141 个源文件对应目标 Git blob，运行后确认未变；复现两书角色互换的 5 个混合历史场景，以及两书均只有历史 UNKNOWN、没有 pending 的 29 项断言。两条命令均退出 0。

复现命令在 `D:/1800` 执行，使用上述证据目录中绑定目标提交的源码导出，输出写入新的主调度目录：

```powershell
python -B docs/evidence/A02/review-R1/acceptance_mixed.py --output docs/evidence/A02/coordinator/acceptance-R1/mixed
python -B docs/evidence/A02/review-R1/probe_history_pair.py --output docs/evidence/A02/coordinator/acceptance-R1/history-pair
```

独立复验另重跑作者 52 项 A02、70 项 C01、16 个 R1 场景、10 组演示及原 72 项独立检查。跨书 UNKNOWN 不再误暂停当前书；同书 UNKNOWN、完整历史、重放和实际目标投影保护有效。旧证据中的探针错误及原始日志保留，不用修订后的文件冒充首次运行。

[归档检查](../evidence/A02/coordinator/archive-R1/checks.json)核对 3,117 项证据的磁盘与暂存区原始字节、16 个本地链接。完整 diff 检查报告五份原始日志／diff 文本的行尾空格，退出 2；只排除这五个确切证据路径后退出 0。原始日志保留，无生产源码例外。

## 边界

当前只覆盖同一进程、同一 MockSession。无浏览器、真实平台、模型调用或待释放会话。内容为 PENDING / CONTENT_PENDING，送审为 NOT_SUBMITTED。N1 的 EXCLUDED 区域关联仍保守拒绝；N2 不是完整证据 mode 准入门禁；S01 来源完整性及持久恢复另行解决。UPDATE、复杂组合题等仍不支持。该验收不代表 B 接受公共合同。

## 本地集成

待执行：归档本次验收证据后，正常合并上述确切提交，检查实际合并结果并运行 A02、C01 和登录工具回归。通过前保持 ACCEPTED，不能记为 INTEGRATED。未推送、未共享给 B。
