# 试题标注辅助自动化

当前可交付结果（2026-10-23，Asia/Shanghai）：书籍 **46007447 第一课时原印刷 Q1—Q16 加 Q7 变式，共 17 个独立题目**，已由程序真实保存、独立进程读回并核对实际导出；10 张题图加载与渲染通过。Q7 主问题答案 C、变式答案 B，全书为 23 题节点 / 76 框。这是限定课时的真实闭环；平台正式送审/业务复审、整章无人值守和跨书泛化仍未建立。

- [运行索引与下一步缺口](docs/run-index.md)：环境、可直接执行的离线检查、真实运行入口与范围。
- [17 题完整流程及限制](docs/usense-first-lesson-closure-20261023.md) · [完成证据摘要](evaluation/usense-lesson1-complete-20261023.json) · [历史 194 项代码检查](evaluation/usense-lesson1-code-checks-20261023.json)。
- [分支与集成路线](docs/integration-route-20261023.md)：为什么 main 落后、PR #3 的正确基线、A 交付消费情况与冲突预检。
- [项目实施框架](docs/project-framework.md) · [架构设计](docs/architecture.md) · [协作约定](docs/collaboration.md) · [B 状态](docs/status/b.md) · [A 状态](docs/status/a.md)。公共合同仍为草案，A 接收状态由 A 自行记录。

## 开始检查

在仓库根目录使用已有的 Python 3.9+；本轮实际使用 Python 3.12.14。仓库当前采用源码入口，没有安装项目用的 `pyproject.toml`，无需先执行 `pip install .`。

```powershell
python --version
python tools/run_usense_live.py --help
python tools/run_usense_live.py doctor
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -B -m unittest discover -s tests -p 'test_usense_live*.py'
python -B -m unittest discover -s tests/usense_live -p 'test_*.py'
```

帮助、doctor 和以上合成测试不启动平台浏览器，不发送业务请求。`doctor` 在缺 Playwright 或缺新配置时返回 exit 2；这表示环境/配置未就绪，不能据此否定已有的真实保存记录。实际登录、采集及写入需要 Windows、Edge、兼容的 Playwright 和当前身份/范围绑定，见 [运行手册](docs/usense-live-runtime.md)。配置、原始响应、源图、审校稿及 profile 保存在仓库外的私有目录。

## 后续工程边界

Q7 插入已改变原生题序：变式为 8，原 Q8—Q16 为 9—17。[新批次入口](docs/usense-reviewed-batch.md)用稳定节点及 question_info 身份绑定显式清单，提供 prepare/status/run；旧 `--orders` 批次命令与历史计划不可重放。[OCR 候选入口](docs/usense-ocr-candidates.md)保留来源、修订与未知项。下一次运行先固定当前完整基线、来源、授权和一次性账本；UNKNOWN 必须先独立读回调和。

最新只读盘点覆盖本书全部 214 页来源索引和 93 个末级目录，返回的预标注块为 0；这不等于已识别全书。第二课时实际为印刷 Q1—Q8 加变式共 9 题，其中已有 5 题原生序号为 18—22，错挂第一课时目录。目录纠正、4 题新增和完整题答审校正在推进，尚未新增该课时真实完成量。后续还需整书题目分母、复杂公式/共享材料消费、独立留出及安装发布验收。

## 历史工作与离线工具

[集成前 README 全文](docs/history/readme-before-integration-20261023.md) 保留旧的研究、离线增量及当时 NOT_RUN/HOLD；其样书 46006966、250 页和 N−1 页映射不适用于当前书籍。其他历史记录按自己的固定输入与日期解释。

- [离线预框演示](docs/b-prebox-demo-20261021.md)：`python -X utf8 tools/prebox_b.py --workspace data/runs/my-prebox`，启动后打开程序打印的本机地址。
- [Q16 与三个阅读任务的固定离线交付](docs/b-q16-reading-fixed-delivery-20261021.md)：固定消费者可读，独立人工内容验收仍待完成。
- [A24 运行时保全包](docs/a24-runtime-preservation-20261022.md)：`python tools/replay_a24_runtime_preservation.py --out data/runs/a24-regression-new`，只跑固定合成回归，新目录不可覆盖。

原始来源、失败证据和历史 ledger 保留。新公共交付不得包含凭据、浏览器状态、真实题干、私有源图或原始业务响应。内部实验代码；样书版权归原出版方所有。
