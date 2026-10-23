# 当前运行与交付索引

更新时间：2026-10-23，Asia/Shanghai。第一课时完成时实现为 `ee463c800bef1ec5010ee5950662b9726d474e42`；四条并行交付现已本地集成至 `3c15026`。后者增加稳定身份批次、来源候选组装及源页绑定修复，真实运行前必须重新冻结配置。本页不授予平台操作权限。

## 已经完成的范围

46007447 第一课时原印刷 Q1—Q16 加 Q7 变式，共 17 个独立题目，已真实保存、独立进程完整读回并核对实际导出，10 张图加载与渲染通过。Q7 主问题 C / 变式 B；当前全书 23 题节点、76 框。详见[闭环记录](usense-first-lesson-closure-20261023.md)、[脱敏完成证据](../evaluation/usense-lesson1-complete-20261023.json)。这些是前轮真实运行证据，本轮只复核代码和文档入口。

旧记录中的 15 题、22 节点、68 框及 NOT_RUN 是各自时点的事实；[10 月 22 日状态](project-status-20261022.md)和[集成前 README](history/readme-before-integration-20261023.md)继续保留。平台正式送审/复审、独立人工业务验收、A 所有者签收及整章无人值守均未由上述结果证明。

## 环境与离线检查

在仓库根目录执行；`python` 必须是 Python 3.9+。本次复用已安装的 Python 3.12.14，没有下载或安装依赖。当前 B 源码树没有 `pyproject.toml`，工具脚本自动定位同仓库 `src`；模块入口和 unittest 需要设置 `PYTHONPATH`。不要把旧 A 分支的安装说明直接套用到 B 树。

```powershell
python --version
python tools/run_usense_live.py --help
python tools/run_usense_live.py doctor
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -B -m unittest discover -s tests -p 'test_usense_live*.py'
python -B -m unittest discover -s tests/usense_live -p 'test_*.py'
```

两组对应 143 项内容/保存/修订/拆分测试与 51 项运行时/可移植入口测试。本轮实际结果、首次失败和复核环境见[集成检查记录](../evaluation/integration-checks-20261023.json)。这是限定合成回归，未运行完整历史仓库套件；不会证明当前账号或平台状态。

`doctor` 不打开浏览器。没有 Playwright 或新配置时，exit 2 和 `platform_ready=false` 是预期的未就绪结果。`save_implemented=false` 是这个读取/登录 doctor 的字段，不能用来推断独立 writer 模块不存在。本轮环境缺 Playwright，未声称真实运行环境安装完成。真实运行需 Windows、已安装 Edge 和兼容 Playwright（前轮实测 1.64.0，需 `route_web_socket`）；安装命令供接收方准备环境时使用，本轮未执行：

```powershell
python -m pip install playwright==1.64.0
python tools/run_usense_live.py doctor
```

OCR 入口另依赖现有 RapidOCR/ONNX 及其本地模型；参考[识别调用边界](usense-first-lesson-closure-20261023.md)，不把基础离线依赖列表当成完整 live/OCR 安装锁。空白机器安装与跨版本验收仍待接收方验证。

## 按目的选择现有入口

| 目的 | 入口与文档 | 执行边界 |
|---|---|---|
| 依赖/配置诊断 | `python tools/run_usense_live.py doctor` | 不联网、不建浏览器；缺配置返回未就绪 |
| 登录/只读采集 | `python tools/run_usense_live.py configure --help`、`capture --help`、`login --help`；[运行手册](usense-live-runtime.md) | 每批最多 6 题、8 页；新身份/短时配置，原字节落盘 |
| 来源 OCR | `python tools/run_usense_ocr.py --help`；[课时流程](usense-first-lesson-closure-20261023.md) | 本地现有模型、来源 SHA 及审校，输出不等于核准 |
| 已有题更新 | `python tools/run_usense_live.py --writer --help` | 复用稳定题框，审校计划/新基线/一次 ledger；之后另进程读回 |
| Q7 专用历史拆分 | `python tools/run_usense_live.py --insert-writer --help`、`--finalize-writer --help`；[专用流程](usense-live-runtime.md#q7-主题与变式的专用流程) | 已完成的两阶段流程；不是通用拆题器，不重放历史计划 |
| 稳定身份批次 | `python tools/run_usense_reviewed_batch.py --help`；[批次说明](usense-reviewed-batch.md) | 显式清单、prepare/status/run、900 秒当前基线及完整前序证据；旧 orders 方式拒绝 |
| 来源候选组装 | `python tools/assemble_usense_candidates.py --help`；[候选说明](usense-ocr-candidates.md) | 本地证据及审校修订，输出不是写入载荷 |
| 无外网离线 CI | `python -I -S tools/run_offline_ci.py --report offline-ci-report.json`；[CI 说明](offline-ci.md) | 222 项标准库合成检查；批次与 OCR 专项另跑，不代表全历史测试通过 |
| 固定 A24 保全回归 | `python tools/replay_a24_runtime_preservation.py --out data/runs/a24-regression-new`；[包说明](a24-runtime-preservation-20261022.md) | 56 项固定合成回归、独立命名空间、新目录，非 live launcher |
| 离线预框演示 | `python -X utf8 tools/prebox_b.py --workspace data/runs/my-prebox`；[说明](b-prebox-demo-20261021.md) | 本机界面，候选需核对，与平台保存分开 |

以上带 `--help` 的命令可用于检查参数；真实操作的完整参数由当前配置、基线、计划和授权决定。原始业务数据、profile、ledger 和审校输入放仓库外，不能复制进发布包。

## 下一次工程与验收顺序

1. **集成与可复现入口**：按[分支路线](integration-route-20261023.md)保留 PR #3 的已审范围；集成其他工作线后，在最终提交重跑 194 项及受影响的专项回归，核对源码闭包和公开产物。
2. **当前目标与来源**：重新只读取得完整当前基线和稳定身份；Q7 变式原生序号为 8，原 Q8—Q16 为 9—17。第二课时已有题的印刷号实际是 1—5，历史原生序号为 17—21，当前为 18—22；旧记录曾误称印刷 Q17—Q21，现予纠正。第二课时源图为 viewer 12/13，共 Q1—Q8 加变式 9 题；viewer 13 下方阅读材料另属自己的目录。印刷号、原生序号、导出紧凑编号分别记录，纠正目录时保全已有身份。
3. **扩展入口准入**：先证明批次 runner 能拒绝陈旧题序/基线，再扩大范围。通用拆题、复杂公式/共享材料精框政策及 A 公共消费者要有固定输入的接受/拒绝回执，不能把本次 Q7 专用链直接泛化。
4. **真实运行验收**：仅由当前指定的平台操作者执行新计划；每次保存后确认写进程退出，再新配置/新进程完整读回、保全其余题与未知字段、核实际导出及图片。UNKNOWN 保留原记录，先独立调和，禁止自动重发。
5. **更大范围交付**：冻结完整章节来源、题/页/材料分母和独立核对者；另验正式平台复审、独立留出、安装/恢复/升级和另一书版式。A 所有者记录自己的接收结果，不能用本轮代码检查代签。

这些缺口分别验收，已完成的 17 题保持完成记录。公共合同和历史 A/B 验收字段本轮不变。
