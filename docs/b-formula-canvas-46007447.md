# 保留完整裁片范围的公式预处理与开发对照

2026-10-17，基线`01c55a39e263aa3bce56a1d380d253b0e8affc9a`。继续长期L1内容识别与L3评测准备。对象是46007447“第一章 勾股定理 / 2 一定是直角三角形吗”第16题的同一完整原裁片（unit2-q16），包含11个分式；未扩大为整书或独立留出集。本轮不访问标注平台、不修改图谱或网站标注，公共合同仍为草案。

## 实际问题与改法

旧完整分式裁片包含高位小字，但RapidLaTeXOCR0.0.9的内部pad还会在归一化后以128阈值找墨迹边界并裁边，再调用学习式尺寸模型。外部放大不能证明上标在最终输入中仍完整，也不能保证字体处于识别模型合适的大小。

先做了36次有界本地探索，原始结果与失败输出均保留。直接跳过自动尺寸调整、放大4或6倍的12次结果出现重复array/hat等幻觉；原始大小的直接输入能识别部分四次幂，但仍有多余表达式或错误分母。该直接输入路径没有作为发布采集模式。第三组保留自动尺寸调整，仅取消按阈值裁墨，在原始大小下读出第3个完整分式的`a⁴+2a²+1`及分母4。

新`formula_canvas.py`保留旧完整分式及两像素上下文的空间范围：灰度、float32 min-max归一化、向32倍数扩展白画布并左上放置，不做阈值boundingRect裁切。灰度、uint8量化和插值仍改变像素值，不是无损保留原像素或字形细节。保留原后端的尺寸限制和最多10轮学习式缩放；固定原始大小与3倍两种输入，随后使用同一锁定CPU模型和seed0/最多128解码token。没有把开发参考文字传入采集器。

每轮保存输入/输出尺寸及像素摘要、插值、实际resizer logits/argmax/后继宽度、白边、归一化tensor摘要和源坐标变换，最终记录停止原因与encoder输入。学习式缩放仍可能丢失细节或达到迭代上限；保留全画布仅说明没有阈值裁墨，不能证明最终转写完整。错误、未知语法、额外符号和分歧都不删去。

正式22次观察包含97轮尺寸模型推理：14次以WIDTH_STABLE停止，只表示预测宽度等于当前canvas宽，不证明高度或字形收敛；8次达到MAX_ITERATIONS，第10轮后沿用最后tensor解码，明确不是宽度收敛。最后分式3倍路径即为该上限情形。所有22次解码完成，无执行失败；17条支持当前语法、5条不支持，11组新路径内部及跨旧路径均存在分歧。

旧后端、固定观察、布局和图谱不改写。新观察为`b-formula-canvas-observation-trial/0.1`，新候选为`b-formula-canvas-candidate-trial/0.1`；候选归档全部旧观察和投影，分别记录新路径内部及跨路径AST一致性，`selected_candidate_refs=[]`、HOLD、未核准，不混拼“正确”分子分母。

## 检查及开发比较

`formula_canvas_quality.py`不导入或运行新生产者、旧采集器或公式语法解析器。它从实际源像素和记录的尺寸模型输出独立重放预处理、核对每次tensor与变换，再逐token/span核对原始LaTeX与AST；同时保留旧观察及候选。它不重新运行模型来证明raw logits或文字正确，也不提供执行签名或人工标准。`accepted`仅是来源及投影一致。

内容比较使用此前已提交的`math-reading-source-review.json`：22个角色的MODEL_VISUAL开发观察。固定全部11个分式，以显式AST构造对比完整分式、分子和分母，记录新旧候选均有、仅旧路径有、仅新路径有和仍无匹配的情况。未知语法及额外项计为不匹配，不按代数关系补写或删掉。该对照不作为识别或完整性检查的输入。

这11项均来自同一道第16题，含重复公式，不能随机拆为11个独立训练/留出问题。后续需按题、页及书分组，取得独立人工盲标与验收回执，才能报告业务准确率和冻结自动放行范围。当前候选命中数和两遍一致都不代替该证据。

正式开发对照：旧22候选中7条完整AST匹配参考、涉及6个分式；新22候选中5条匹配、涉及5个分式。合并保留两路径后，9/11至少有一个匹配候选，新增第2、3、4个分式；第6、8、10、11个分式只有旧路径有匹配，第5、9个分式两路径都未匹配。不能用新路径整体替代旧路径，9/11是同题开发候选覆盖，不是被自动选中的答案或留出准确率。

第5个分式仍有四次幂与分母的路径冲突；最后分式的高位小字和右邻“是”的左缘可能共同影响识别，既有两像素上下文与旧观察完整保留，未按期望答案剪去或删除多余输出。整题证明中的分式外符号和文字仍待重建，19条来源身份、整书页目录和A消费者也仍待推进。

## 复现

默认从固定新观察重放，禁止隐式模型初始化或下载；输出目录必须不存在：

```sh
python tools/replay_formula_canvas_b.py --out data/runs/formula-canvas-replay
python -m unittest discover -s tests -q
```

先独立核对旧布局、原裁片和旧公式观察，再检查新结果。五份输出分别是`math-layout.json`、`canvas-observations.json`、`canvas-candidates.json`、`canvas-check.json`及`summary.json`。`summary.integrity_accepted`和`canvas-check.payload.accepted`仅限离线来源和投影检查，退出0不表示转写核准；decision为HOLD，business_acceptance与transcription_verified均为false，不生成平台动作。

明确新增CPU观察时，用锁定环境及已经存在、核对过SHA的三个ONNX权重及tokenizer.json：

```sh
FORMULA_PYTHON tools/replay_formula_canvas_b.py --collect --layout tests/fixtures/book46007447/formula-layout.json --crop tests/fixtures/book46007447/recovery-assets/unit2-q16.png --models MODEL_DIR --out data/runs/formula-canvas-new
```

`FORMULA_PYTHON`和`MODEL_DIR`为本地路径占位，安装锁与权重身份仍见`requirements-formula-cpu.txt`及`evaluation/formula-cpu-runtime-lock.json`。缺模型、参数冲突或旧来源检查失败时不回退其他后端。显式注入测试后端只标SYNTHETIC_TEST，不能改成真实CPU或人工核准。

最终Git导出目录619项完整回归通过，新增生产者18、独立检查29、CLI14项；源码最后一项坏整数logits边界补丁之前，工作目录618项也已通过，旧运行回执保留。固定观察在主环境及公式隔离环境禁止模型导入和网络重放，布局、观察、候选和检查四个payload摘要一致。实际采集、开发对照和完整证据汇总在`evaluation/book-46007447-formula-canvas.json`。

本轮实际公式encoder-decoder共58次（探索36+正式22），尺寸模型另有131次（探索34+正式97）；两种调用不能相互混记或当作token数。没有新增普通OCR、模型下载、样本上传、标注平台请求/操作或付费调用。新预处理仍是单独的公式候选入口，没有接入持久pipeline或Q9的0.4应用。A接收验证仍为PENDING_A，长期目标继续进行。
