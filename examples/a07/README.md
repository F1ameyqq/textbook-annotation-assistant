# A07 固定 Q1 离线入口

仅消费任务指定的原 B ZIP、新 Q1 旁文件 ZIP、历史 E0.1 和 raw Git 用户授权。保留真实输入 `OBSERVED`，内存目标/计划/回执为 `SYNTHETIC / SIMULATED`。此入口只支持书 46007447 的固定 Q1，不支持平台、题22、全书、其他 B 版本、持久化或恢复。

使用现成 Python 3.9 环境、Pydantic 2.12.5、Pillow 11.3.0；无需安装新依赖。先在独立的固定候选检出目录运行下面命令。输入目录与输出目录必须新建，已有产物不覆盖。`stage_inputs.py` 只复制本机固定原件，不执行 B 附带文件；用户授权从固定工作流的 Git blob 导出，不能用 CRLF checkout 文件替代。

```powershell
$env:GIT_NO_LAZY_FETCH='1'
$env:PYTHONPATH='src'
$env:PYTHONIOENCODING='utf-8'
python examples/a07/stage_inputs.py --destination .local/a07/review-inputs
```

窄单元检查只准备计划和执行拒绝调用，正常业务 dispatch 为零：

```powershell
$env:A07_INPUT_DIR='.local/a07/review-inputs'
$env:A07_UNIT_EVIDENCE='.local/a07/review-unit-calls.json'
python -m unittest discover -s tests -p test_a07_q1.py -v
```

仅在调度派发固定候选后，使用明确的该候选 SHA，运行**一次**完整试验。执行方与独立验收方各自遵守任务额度，正常成功后不得重复跑成功证据。

```powershell
python examples/a07/run_once.py --input-dir .local/a07/review-inputs --output .local/a07/review-candidate-1 --run-id a07-review-1 --expected-candidate <调度指定的完整候选SHA>
```

`run/exchange.json` 是经 C01 验证的完整新信封；`run/receipt.json` 是模拟回执。`run/assets/before.json`、`run/assets/readback.json` 来自实际内存目标的两次独立读取；`run/comparison.json` 由公共效果比较函数计算。`run/summary.json` 明确 `NOT_SUBMITTED / PENDING`，`run/replay-rejection.json` 是实际消费后重放的零变更拒绝，`supervisor.json` 记录子进程退出与回收。该 CLI 启动零服务、零浏览器、零平台/模型调用。

五项 PRE_APPLY 独立比较真实资源/坐标、结构/正文、原题答关系/跨度、批准的单题库存与30条排除、独立授权/内部政策。TARGET 检查固定内存实例、当前空状态、目录、同会话读回及 CREATE_FRAMES 能力。写前从原始输入重算整个来源/检查/目标/计划并逐对象比较，重封装的任意 PASS 或计划不能授权执行。

原 B `HOLD / human_verified=false / business_acceptance=false`、原31项/78依据、原 Check 的127项及19条未归属账本保存在输入资源与映射中。新 A 授权只处置本固定单题离线范围；不声明 B 联合采用、人工视觉复核、平台文本去号/呈现或真实平台资格。
