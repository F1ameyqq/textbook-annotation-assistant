# A02 R1 离线复现

只修 `MockSession.is_paused` 对完整多书包回执遗漏 book_id 筛选的问题。全部输入 SYNTHETIC，执行 SIMULATED；
保留外书所有产物与 UNKNOWN 历史，不拒绝合法多书包，不改同书 pending/UNKNOWN 或重放门。

在本任务 checkout 根目录运行作者回归：

```powershell
$env:PYTHONPATH = "$PWD\src"
python -B -m unittest discover -s tests -p 'test_a02*.py' -v
python -B -m unittest discover -s tests -p 'test_contracts*.py' -v
```

正式证据建议采用 raw Git blob 导出，避免 Windows checkout CRLF 改变文件字节。以下目录均须不存在；
将 `<实现提交完整SHA>` 换成 R1 执行报告指定提交，`--identity-repo` 必须指向实际 Git 顶层：

```powershell
python -B examples/a02/R1/export.py --repo "$PWD" --commit <实现提交完整SHA> --output "$env:TEMP/a02-r1-source-new"
python -B "$env:TEMP/a02-r1-source-new/examples/a02/R1/verify.py" `
  --source-root "$env:TEMP/a02-r1-source-new" --source-commit <实现提交完整SHA> `
  --identity-repo "$PWD" --output "$env:TEMP/a02-r1-evidence-new"
```

`--matrix-only` 只运行 16 个 R1 场景；默认另运行 A02/C01 套件及 10 个原有正常/故障演示。
生成完整输入/计划/回执、独立目标、动作日志、完整书级历史、错误和结果；所有交换包按公共 API 验证实际资源。
矩阵覆盖混合包诊断再 READY、交换书籍角色、独立包/混合包、两书各 UNKNOWN、外书 APPLIED/NOT_APPLIED/NOT_EXECUTED、
同书换 run/action/question/scope 并省略历史、三类旧计划不重放，以及明确 ABSENT 后重查/重规划。
另验证同书仅有历史 UNKNOWN、没有本会话 pending/intent 时仍保持阻断。

复现器逐字验证显式提交的生产代码与测试/演示脚本 Git blob，并记录实际导入位置、源码 SHA256、argv/cwd/退出码。
无 `.git` 导出目录的 `checkout_commit` 明确为 null/unknown，身份来自外部明确提交和逐字校验；不采纳父仓库 HEAD。
若源码与指定 blob 不一致，停止并报错，不用另一个 Git 身份替代。旧 `examples/a02/verify.py` 和旧证据未改写。

N1 排除区域关联与 N2 证据注册标签准入仍是原有边界；不放宽覆盖门，不声称解决 S01 真实来源。
内容仍 PENDING、提交 NOT_SUBMITTED；无浏览器、平台、凭据、OCR、模型或真实成本测量。
跨进程持久化/重启恢复、正式 ReconciliationResult 与解暂停仍未实现；作者结果仅进入 REVIEW。
