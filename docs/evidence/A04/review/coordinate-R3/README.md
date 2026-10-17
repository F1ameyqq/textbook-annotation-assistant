# A04 coordinate-R3 独立离线复验

target `6c8137a4fadddc01a47906d564ab3460277c8958`；workflow `d834bf531f95abac7ed30b89b3ca55105fa6f491`。**OFFLINE_R3=ACCEPTED；A04_OVERALL=BLOCKED**。

[报告](../../../../tasks/A04-coordinate-R3-review-report.md) · [结论矩阵](review-verdict.json) · [输入核对](snapshot-check.json) · [最终检查](closure-checks.json) · [完整清单](sha256-manifest.json) · [自身进程结束](self-release.json)

| 要求 | 本轮证据与结果 |
|---|---|
| 精确缺行反例 | [未改脚本](inputs/unchanged-R2-repro/repro_incomplete_rows.py)、[配套原guard](inputs/unchanged-R2-repro/offline_guard.py)、[结果](exact-replay/result.json)：原hash相同；wrapper0、产品2、无历史/最终包 |
| 代表布局、正常总量、反例 | [26项独立结果](independent-cases/results.json)：7种物理像素tile构造的普通/Adam7、1/2/8/16位深代表，逐例正确总量、少/多字节拒绝 |
| 发布复查 | [parse后同尺寸替换](independent-cases/U-same-size-swap/result.json)、[公开复制间替换](independent-cases/U-public-copy-swap/result.json)：无历史/有效最终包 |
| 公开入口与搬运 | 8个PNG/JPEG/P2/P5正常包；各自`P-*/input`、`output`、`relocated full package with spaces`和独立消费者原始流保留 |
| 资源 | 5项缩放包含边界、默认超限header早拒、2MiB膨胀按155字节cap、小规模限长读取；见独立`R-*`结果 |
| 兼容收紧 | 双帧APNG和尾随字节PNG公开拒绝；索引Paeth/padding有效，实际越界palette sample拒绝 |
| 相关回归 | [70项结果](initial/regression-result.json)；[原始流/命令](initial/process-results.json)；旧完整矩阵没有重复 |
| 真实与整体范围 | R01～R06和S01仍BLOCKED；不做平台/浏览器/网络/profile/凭据/模型动作 |

`inputs/frozen-inputs.tar.gz`保存从确切Git原始字节选择的212个文件，逐文件摘要在 [frozen-tree-manifest.json](inputs/frozen-tree-manifest.json)。其中未选择运行的其他测试和历史素材仅保留为输入，未计入成绩。`inputs/workflow/`保存固定规则、任务和主调度前检；作者完整852项清单的Git/磁盘检查结果在snapshot中，不将前检视为功能通过。

自己的运行脚本位于`scripts/`。`run_jobs.py --group initial`运行精确反例和4个受影响测试模块；`--group independent`运行有界自建检查。详细argv、cwd、退出码、创建时间和stdout/stderr在`initial/`、`independent/`；生成型脚本要求新的输出目录，不覆盖现有证据。只要重放精确反例即可用报告中支持新输出参数的原脚本命令，不必重跑全部矩阵。

独立PNG生成器根据物理坐标8×8 Adam7 tile、位深打包和自行编码的滤波得到期望字节；没有调用产品布局函数生成期望值。作者150组合subtest是回归覆盖，不当作独立成绩。代表范围、APNG/尾随拒绝及未做配置极限压力测试均在报告限定。

[environment.json](environment.json)给出现有环境及真实导入位置；无依赖安装/升级。`offline_guard.py`只作为自己的临时审计bootstrap，Windows子进程参数和PID复用均以已验证方式处理。只观察记录的PID＋创建时间；27个原身份已结束，1个PID后被复用但未操作新进程。授权profile当前状态未检查。

初次导出对一个不存在的可选README路径作了错误假设，archive在产品启动前失败；[记录](harness-notes/snapshot-optional-readme.txt)保留。没有产品测试失败或实现修补。原R1/R2报告、失败及其他旧证据保持；D01不重复验收；不提交、推送、集成或改state。
