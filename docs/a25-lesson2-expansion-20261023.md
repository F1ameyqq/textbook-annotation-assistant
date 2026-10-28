# A25 第二课时五题：固定执行交付

执行对话 `01a166e7-cfd7-7da2-a76e-bcb612b9646b`，协调对话 `01a166c5-f93f-76e3-baf4-a3545ccddebd`；独立验收对话由根 JSON 登记为 `01a166e8-3f23-7192-a560-4724adca74b1`。基线 `ee463c800bef1ec5010ee5950662b9726d474e42`，分支 `codex/a25-lesson2-expansion-20261023`。本页是作者交付，不是独立验收。

## 已完成的代码

- 为本地 `annotation` 添加常规包入口。原环境有另一个 worktree 的已安装同名常规包；此前本地命名空间包被它遮蔽。实际原导入失败和全部原始输出保持；没有修改安装环境或其他 worktree。冲突包、其他 cwd 的真实子进程检查及本机 configure/doctor 现已通过。
- 批入口改为[摘要绑定的目标清单](usense-reviewed-batch-manifest.md)。原始题序不能独自选题；印刷题号、语义课时、原生题序、稳定 node/info 和服务器实际父目录分别保留。旧 `--orders` / 固定第一课时 qN 候选目录入口被拒绝，不把上限从 16 放宽后继续旧身份。
- 首个 configure/writer 前，整批核当前捕获、所有目标完整原生状态、来源页、候选/来源/审校哈希、重复稳定 ID/题序、已有 ledger 与可选前序验收。调用现有单题 `make_plan`、`validate_inputs` 和严格前序验证器；writer、保存载荷和读回比较器未改。
- 任一失败/UNKNOWN 停止，不自动补发或读取；其后目标逐项 `NOT_RUN`。成功 writer 退出后才启动另一个 reader 进程，比较完整原生状态，再创建 accepted 标记。私有 process stdout/stderr 原始 bytes 和进程结果分开保留。完整合成成功案例覆盖五题顺序执行及五个 accepted 标记，但未触达平台。

## 本轮新检查

|固定原件标签|实际结果|范围|
|---|---|---|
|`a25-new-checks-01`|14/14，exit 0|初版新增边界，输出原件保留|
|`a25-new-checks-02`|15/15，exit 0|增加生成后计划哈希保护；涵盖重排、旧序拒绝、稳定 ID 错配、重复、第五题缺件、UNKNOWN 和后继 NOT_RUN|
|`a25-affected-boundaries-01`|11/11，exit 0|现有便携入口 6 项、配置/GET 原始字节边界 5 项|
|`a25-final-orchestration-delta-01`|3/3，exit 0|最终五题合成成功链、首写前缺件逐项 NOT_RUN、计划变更停止；与前述检查有重叠，不相加为独立覆盖量|
|`a25-local-resource-check-01`|exit 0|实际本机 Python/Playwright WebSocket guard、Edge 文件和原 profile 锁名检查，0 browser|

最终新增测试文件含 16 个不同测试：其中 15 个在第二次完整新增检查执行，新增的第 16 个及两个受影响检查在最终三项差量执行。旧首课时 17 题、旧 194 项套件、旧 OCR 和旧 A 轮次没有重跑。

末次 AST 检查 5 文件 exit 0。随后外层哈希辅助脚本有一次 AssertionError：它用正斜杠排除批入口，但预冻结清单键是 Windows 反斜杠。逐项比较只显示 live 结束后补充资源检查/逐项 NOT_RUN 报告的批入口变化，capture 入口及所有包内 Python 原件摘要一致；没有重跑 live。该辅助断言失败单独登记，外层 traceback 原 bytes 未落盘，不伪造 stderr。Windows Job 内的 AST 子进程 exit 0 原输出保持。

## 唯一当前源只读轮

2026-10-23 12:07:04—12:07:05（Asia/Shanghai），新配置 `8e25a3b8bbd5ae0e54441dd32733bf12a5aa45d4ba1517d8982342f18b8b6c75`，实现摘要 `31f268add44773ec35b939644d5fefff98a646a4e6d7687164f2c2ff8e200cc8`。固定 B 证书实现、原专用 profile、1 context/1 inert 同源导航/900 秒上限、原生 18—22、来源 12/173、source 元数据。启动前私有 authority 从 spent 0 记为 1，原件另存；没有借用或恢复旧额度。

本次 exit 2 / `CAPTURE_FAILED_NO_RETRY` / `SSLEOFError`，发生于 TLS 握手阶段。没有取得任何业务响应，`captures={}`，网络审计原件为 `[]`；没有建立浏览器 context/runtime。SSLEOFError 的完整异常文本/traceback 未由原采集器留存，stderr 原件为 0 bytes；网络原因、证书内容及服务端原因均 UNKNOWN，没有把离线检查当根因证明。没有重试、换 profile、登录、凭据配置读取、扩 origin 或平台写入。

`capture-summary.json` 保留原始 `release:null`：采集器只在 `__aenter__` 成功后给 owner 赋值，TLS 前置异常没有把已生成的 release 对象回填摘要。单独 `release.json` 记录 context/runtime 释放 true、pending 0、errors 空；该文件没有被写回摘要或替代原件。

外层使用独立 Windows Job，进程在恢复执行前已入 Job；持有 Python PID 24672 和 conhost PID 50132 的 creation FILETIME/镜像/句柄。两者已 signaled，Job 活动进程 0，进程/线程/Job 句柄关闭。前后原 profile 匹配 Edge 进程及锁名均为 0。外层监督本身只证明其持有的进程和 Job；不把未观察到的瞬时进程列为已持有身份。

## 当前交付与缺口

五题仍只是已授权范围：印刷 17—21 / B 报告原生 18—22。新 stable ID、服务器实际父目录、完整基线及来源没有取得，不能用 B 旧报告或旧捕获补成当前身份。五题来源候选、内容审校、保存计划、逐题保存、独立读回和真实导出全部 `NOT_RUN`，没有生成可执行的伪候选或填补正文。

根目录不改产品、调度 JSON、AGENTS 或历史 dirty 文件；sole `1800-a` 保持 PAUSED。未推送、未联系 B 或其他对话、未自验收。本次只读额度 1/1，余 0。后续由调度读取此冻结交付和独立结果；任何新的实际读取或写入都必须另行绑定具体当前授权，不能自行重开此轮配置/claim/output。

原件统一在 `D:/1800/.local/stages/a25-lesson2-expansion-20261023/`；公开[结果摘要](../evaluation/a25-lesson2-execution-20261023.json)与执行目录下 raw 清单只列安全结果、摘要和私有引用，不含 profile、令牌、Cookie 或业务正文。
