# 专门公式观察与可恢复的离线批次

2026-10-17，B侧；基线 `6aa4ba89b720b3c7fcf1887015eb85b07446d601`。继续长期L1公式内容和L2离线处理，未修改平台、旧图谱或既有OCR。公共合同与A执行器仍待对齐。

## 专门公式后端的实际结果

在工作区独立Python3.11环境安装并实际运行RapidLaTeXOCR0.0.9，`pip check`通过。模型来自[上游项目](https://github.com/RapidAI/RapidLaTeXOCR)的固定release；三个ONNX和tokenizer使用显式本地路径，适配器不自动安装或下载。实际模型长度/SHA和可选依赖版本记录在`evaluation/formula-cpu-runtime-lock.json`、`requirements-formula-cpu.txt`，权重未提交仓库。release API未发布上游摘要，本地SHA表示本次实际测试文件身份，没有声称是作者签名。

当前11个完整分式各用两种固定预处理，实际22次CPU推理、无执行失败，逐次调用墙钟回执合计约17.19秒（不含安装、模型加载和采集准备）。保留每次原始LaTeX、源区域/像素/变换、模型/后端源码摘要、CPU providers、seed和耗时。单次解码最多128 token；注入后端只能标SYNTHETIC_TEST。

| 观察 | 结果与含义 |
|---|---|
| 20条可解析、2条未知语法 | 只表示支持当前语法树格式，不表示20条正确 |
| 8个分式有双预处理分歧或未知语法 | 原输出逐条保留，未混拼成期望公式 |
| 最后分式scale3 | 新读出`a²+1`分子；旧普通OCR两次`a+1`仍原样保留 |
| 最后分式scale4 | 幻觉为`π+1`，保留为未支持候选，不选择scale3冒充已核准 |
| 第3、第5个分式 | 四次幂仍误读；直接查看完整原裁片，字墨在区域内，当前模型不能可靠转写 |
| 两种预处理一致 | 仍有`a^t`、漏项等错误，不能作为数学完整性证明 |

新模型与旧模型的全部假设、风险分别留存，不自动覆盖或改写。整题证明中的分式外符号、普通文字及完整线性公式尚未重建；表格、共享材料、其他复杂类型及业务留出集仍在长期范围内。

## 语法投影与独立检查

`formula_syntax.py`只生成保序语法树，不执行LaTeX，不做代数等价推断。每个token和节点保留原文跨度；支持的分式、花括号、圆括号、幂次/下标及操作符明确区分。显示样式命令仍保留在token记录，只在数学结构比较时忽略。未知命令/字符、无花括号的多token脚本、重复上标等保留完整原文和最早未解析尾段，不静默删除。

`formula_quality.py`不导入或重跑公式采集器、候选生产者或语法解析器。独立扫描原文并消费实际AST，检查每个token、分母、上标和scope；同时核对所有源区域、双变换、模型/测试标签和版本。仅改AST和摘要、删除未知尾段、错侧分子/分母或将SYNTHETIC改成CPU都会拒绝。

`accepted`限于来源和投影一致；即使AST与模型原文完全一致，模型原文本身仍可能错。没有使用目视开发参考作为识别或检查输入，没有人工业务验收。所有新产物HOLD、complete=false、selected_candidate_refs为空、entire_answer_reconstructed=false，无平台动作。

冻结布局、原始观察和源裁片闭合输入依赖。默认重放重新审计冻结布局，保留原artifact身份；避免NumPy/OpenCV版本变化导致重新生成不同上游ID。已在基础环境（NumPy2.3.5/OpenCV4.13/Pillow12.2）和公式隔离环境（NumPy1.26.4/OpenCV4.11/Pillow12.3）重放，源变换及输出一致；两个进程均禁止模型运行库导入和网络连接。

## B离线批次与恢复

`batch.py`按manifest声明的完整资产集合运行，开始前核对所有原图路径、SHA和尺寸。`--max-items`只限制本次执行数量，不缩小总范围；全部资产成功后才产生合并EvidenceBundle。几何、CPU OCR和测试worker分别标明，不把几何完成称为内容识别完成。

SQLite保存job/items、attempt和事件；运行前记录RUNNING，产物通过内容地址不可覆盖发布，再提交DONE检查点。两个真正`os._exit`场景覆盖worker中途死亡及文件已发布但SQL未提交；恢复时记录INTERRUPTED、保留旧对象、重做未完成项，不把孤儿文件当成功回执。OS锁随进程退出释放，无需删旧lock文件猜测进程状态。

缓存键绑定书/范围、完整单资产描述、识别器代码/配置/依赖与模型。单页变化只重做受影响页；代码/参数/依赖变更按对应指纹失效。命中前再次核对产物文件及真实成功attempt/事件，不能只看SQL的DONE。损坏对象保留为故障证据，不在同一内容地址覆盖修复。

独立`batch_quality.py`直接核对原图、声明集合、SQL/事件、不可变文件和合并页，拒绝丢页却称完成、跨页重复归属、伪来源和同步篡改文件/SQL/report后的串页。CLI每次保存独立检查回执，批次READY与业务HOLD分开。

真实5张已有源图已验证：2/5后恢复为5/5，恢复命中2页，再运行命中5页；一页描述版本变化只执行1页、命中4页；故意损坏缓存先被独立审计拒绝，随后只恢复1页并命中其余4页。原图SHA前后不变。`invalidated`是累计事件计数，不等于本次重做页数。这里验证的是声明5页几何阶段，未称整书214页、跨页组题或业务验收完成。批次runner不接管A的平台runtime、写入锁或提交恢复。

## 重放与运行

缓存公式重放不需要专门公式模型或网络，输出目录须新建：

```sh
python -m unittest discover -s tests -q
python tools/replay_formula_b.py --out data/runs/formula-replay
python tools/run_batch_b.py --source SOURCE/source.json --workdir data/runs/batch --max-items 2
python tools/run_batch_b.py --source SOURCE/source.json --workdir data/runs/batch
```

批次workdir用于恢复，应保留原目录；默认几何模式不调用OCR，显式`--ocr`才使用本地普通OCR。公式真实采集在隔离环境安装`requirements-formula-cpu.txt`，准备并核对lock列出的四个模型后运行：

```sh
FORMULA_PYTHON tools/replay_formula_b.py --collect --layout tests/fixtures/book46007447/formula-layout.json --crop tests/fixtures/book46007447/recovery-assets/unit2-q16.png --models MODEL_DIR --out data/runs/formula-collected
```

`FORMULA_PYTHON`表示隔离环境Python路径，`MODEL_DIR`为已核对的本地权重目录；不得用普通缓存重放假称又运行了模型。Git暂存树导出到独立目录后435项回归通过（此前301+新增134：批次61、公式73）；基础环境运行完整套件，两个运行时只比较缓存公式重放，没有声称两边均运行全套测试。完整回归、Git导出、跨运行时重放和真实批次证据见`evaluation/book-46007447-formula-batch.json`。下一步改善四次幂及跨后端冲突的候选，接通后续离线组题/覆盖检查的批次依赖失效，补齐整书来源/目录和独立验收；当前阶段完成不是长期目标完成。
