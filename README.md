# 试题标注辅助自动化

当前状态（2026-10-24，Asia/Shanghai）：**B侧内容与离线交接**已完成第二课时9题、三个阅读任务及[“一定是直角三角形吗”Q1–Q16](docs/b-section2-release-20261024.md)。当前课时收口后按用户要求停止扩章；网站直接交付由另一执行端负责。[无agent客户的封装方案](docs/b-customer-packaging-plan-20261024.md)已整理，安装包尚未开发。

[第一章逐题进度与当前缺口](docs/b-first-chapter-progress-20261024.md)：103个来源候选中当前B便携交付28项；第一课时17项来源稿已齐、C01暂停，其余58项仅来源枚举并暂停。第一章未完成；历史网站保存不替代当前B包。

此前临时接管成果：书籍 **46007447 第一课时原印刷 Q1—Q16 加 Q7 变式，共 17 个独立题目**，已由程序真实保存、独立进程读回并核对实际导出；10 张题图加载与渲染通过。Q7 主问题答案 C、变式答案 B，当时全书为 23 题节点 / 76 框。后续外部写入会改变网站库存；历史保存量不等于 B 的整章内容交付量。

- [运行索引与下一步缺口](docs/run-index.md)：环境、可直接执行的离线检查、真实运行入口与范围。
- [17 题完整流程及限制](docs/usense-first-lesson-closure-20261023.md) · [完成证据摘要](evaluation/usense-lesson1-complete-20261023.json) · [历史 194 项代码检查](evaluation/usense-lesson1-code-checks-20261023.json)。
- [分支与集成路线](docs/integration-route-20261023.md)：为什么 main 落后、PR #3 的正确基线、A 交付消费情况与冲突预检。
- [项目实施框架](docs/project-framework.md) · [架构设计](docs/architecture.md) · [协作约定](docs/collaboration.md) · [B 状态](docs/status/b.md) · [A 状态](docs/status/a.md)。公共合同仍为草案，A 接收状态由 A 自行记录。

## 开始检查

在仓库根目录使用已有的 Python 3.9+；本轮实际使用 Python 3.12.14。仓库当前采用源码入口，没有安装项目用的 `pyproject.toml`，无需先执行 `pip install .`。

```powershell
python --version
python tools/run_source_region_ocr.py --help
python tools/assemble_usense_candidates.py --help
python tools/book_coverage_inventory.py --help
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -B -m unittest discover -s tests -p 'test_source_region_ocr.py'
python -B -m unittest discover -s tests -p 'test_usense_ocr_candidates.py'
python -B -m unittest discover -s tests -p 'test_book_coverage_inventory.py'
```

上述帮助和合成测试不启动平台浏览器，不发送业务请求；71 项对应本轮 B 侧来源/OCR/覆盖账本检查，不能当识别正确率。实际 OCR 还需本机已有 RapidOCR/ONNX 模型与固定来源，见 [来源区域识别](docs/source-region-ocr.md) 和 [候选组装](docs/usense-ocr-candidates.md)。原始响应、源图和审校稿留在仓库外。此前平台工具另见 [历史运行手册](docs/usense-live-runtime.md)，不属于当前 B 侧操作任务。

## 后续工程边界

Q7 插入已改变原生题序：变式为 8，原 Q8—Q16 为 9—17。[新批次入口](docs/usense-reviewed-batch.md)用稳定节点及 question_info 身份绑定显式清单，提供 prepare/status/run；旧 `--orders` 批次命令与历史计划不可重放。[OCR 候选入口](docs/usense-ocr-candidates.md)保留来源、修订与未知项。下一次运行先固定当前完整基线、来源、授权和一次性账本；UNKNOWN 必须先独立读回调和。

本书214页原图已取得并核验，93个末级目录有来源候选映射；只有31页完成过整页OCR，不能称逐题识别整书。当前课时完整索引选取两个C01包中的16题，明确排除相邻阅读任务。整章未通过；整书题目分母、18个末级范围配答和目录外九份测试卷范围尚有缺口。

## 历史工作与离线工具

[集成前 README 全文](docs/history/readme-before-integration-20261023.md) 保留旧的研究、离线增量及当时 NOT_RUN/HOLD；其样书 46006966、250 页和 N−1 页映射不适用于当前书籍。其他历史记录按自己的固定输入与日期解释。

- [离线预框演示](docs/b-prebox-demo-20261021.md)：`python -X utf8 tools/prebox_b.py --workspace data/runs/my-prebox`，启动后打开程序打印的本机地址。
- [Q16 与三个阅读任务的固定离线交付](docs/b-q16-reading-fixed-delivery-20261021.md)：固定消费者可读，独立人工内容验收仍待完成。
- [A24 运行时保全包](docs/a24-runtime-preservation-20261022.md)：`python tools/replay_a24_runtime_preservation.py --out data/runs/a24-regression-new`，只跑固定合成回归，新目录不可覆盖。

原始来源、失败证据和历史ledger保留。本轮按用户授权，将已完成独立检查的9＋4＋15项内容、必要源图和离线验证作为有界便携包提交；第一课时私有来源和未完成草稿继续留在仓库外。凭据、浏览器状态、个人路径和原始业务响应不入库。内部实验代码；样书版权归原出版方所有。
