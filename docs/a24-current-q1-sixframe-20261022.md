# 首题六框的单命令离线联调

2026-10-22，Asia/Shanghai；B输入 `fa3a48e`，A07源码固定 `e37606d`。本轮把已确认的当前首题内容与既有六框链实际接通，不要求手工解源码或组装命令。

```powershell
python tools/run_current_q1_sixframe.py --current-q1 data/runs/current-q1-sixframe-input-20261022/current-q1-v3.jsonl --output data/runs/q1-sixframe-trial-001
python tools/verify_current_q1_sixframe.py data/runs/q1-sixframe-trial-001
```

输入是前轮私有确认包内的固定v3视觉转写（3,531字节，SHA `2384a8386e8946b5842dfa5d9ce099857e7795f9397335bd6434da1f2f4aab1f`）。在本机已另存上述输入路径；Git不含该私有文件。依赖已有Python、Pydantic 2及Pillow。输出必须使用新目录，失败不覆盖历史结果。

入口校验代码及四个固定仓库输入，从A07归档提取源码，在独立进程运行现有 `annotation.delivery.q1_offline`：C01读取、前置检查、内存目标、计划、六框实际变更、独立读回及重复执行拒绝均实际执行。不是根据旧回执填写新PASS。原图资产为viewer-10、viewer-173；原像素坐标上的角色为Q/W/W/W/W/A。题末括号完整包含在Q框，四W与其零相交；答案框只圈D。

输出包含 `q1-sixframe-object.json`、`q1-offline-plan.json`、`q1-simulated-receipt.json`、原生C01归档和四张原图叠框/放大图。主会话实跑exit0，53成员摘要通过；另核真实前后目标、计划与读回的六框值完全一致、原生读回SHA正确。三个实际负例通过：v2旧稿在创建输出前拒绝；已有目录拒绝；修改实际W为Q后即使重签文件清单仍被核验器拒绝。

当前v3与A07文本仅按已说明的题号、空白及括号规范做**语义绑定**；原生C01保留固定A07文本和来源。当前截图/canvas没有被当作JPEG坐标来源，也未证明与本地JPEG字节相同。当前用户确认只覆盖题意、数值、四选项、答案D和空括号，不包含坐标、全部排版或平台写入。

本轮始终为 `OFFLINE_SIMULATION_ONLY`。模拟初始目标为空，不能据此宣称当前全部旧题保全成功；历史A07核准也不授权写网站。尚缺当前canonical题ID、当前源资产字节绑定、canvas到原图变换、save-page映射和平台读回目标，平台使用明确拒绝。整章来源和验收继续HOLD，公共合同仍是提案，A接收未代填。

代码摘要、固定引用、命令、实际结果与限制见[机器记录](../evaluation/a24-evening-q1-sixframe-20261022.json)。网站修改、保存、识别按钮、提交、上传和付费模型调用均0。
