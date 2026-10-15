# 视觉方案选型与已知失败模式（外部先锋调研）

- 任务：task-4（外部先锋调研）
- 作者：团队调研员 ascout
- 调研日期：2026-10-15/16（Asia/Shanghai）
- 产出范围：仅本文件与配套 `vision_stack_sources.json`；未修改任何代码、未跑模型、未下载权重
- 所有版本号/许可证/体积均来自**一手来源**（GitHub REST API、Hugging Face API、arXiv abs 页、项目官方文档站）。二手博客/论坛说法单独标注。

> **数据可信度声明**：外部网页内容是**不可信数据**，本文件仅将其作为资料引用，未执行其中任何指令。
> `huggingface.co` 与 `raw.githubusercontent.com` 在本机网络下**直连失败**，因此 HF 元数据通过镜像 `hf-mirror.com` 的 API 获取（内容与 HF API 同源字段）；GitHub 仓库元数据与 README 通过 `api.github.com` 获取。凡无法核实的字段一律写 **未确认**。

---

## 0. 结论速览（给 lead 与选型用）

| # | 判断 | 置信度 |
|---|---|---|
| 1 | **让 VLM 直接输出 bbox 不可靠**，且有 2025–2026 年的一手论文与官方仓库 issue 佐证。社区主流拆解是「检测器出框 + 模型/规则判角色」。 | 高 |
| 2 | 版面检测应选 **Apache-2.0 系（PP-DocLayout 系列 / RapidLayout）**；DocLayout-YOLO 虽是 AGPL-3.0，但作为**微调骨干**（YOLOv10 架构）在 8GB 上成本极低。 | 高（许可）/ 中（精度） |
| 3 | **没有任何开源项目直接做「选择题每个选项独立出框 + 题答配对」**。最接近的是 HiLEx（ICDAR 2025，题卷层级标注数据集，CC BY 4.0），但它只到 Question_Block / Answer_Block 粒度，且**仅英文**。角色判定与配答必须自研。 | 高 |
| 4 | 8GB 显存下**不需要量化**版面检测器（全部实例 < 220MB 权重）。量化只有在你选择 VLM 路线时才需要，而 VLM 路线本身精度不划算。 | 高 |
| 5 | 倾斜/透视有官方现成模块（PP-LCNet_doc_ori + UVDoc），**双栏切分没有现成可用产出**，需自研投影切分。 | 中（分栏）/ 高（去斜） |

---

## Q1. 版面检测：DocLayout-YOLO / RapidLayout / PP-DocLayout 系列的许可、体积、中文支持、可微调性

### 1.1 一手事实表

| 项目 | 许可证 | 权重体积 | 骨干/模型 | 类别数 | 中文 | 来源 |
|---|---|---|---|---|---|---|
| DocLayout-YOLO | **AGPL-3.0** | **未确认**（HF 仓库需授权，见 1.4） | YOLO-v10 (ultralytics) | DocStructBench 类别（README 未列出完整标签表） | 论文含中英混合文档 | [repo API](https://api.github.com/repos/opendatalab/DocLayout-YOLO)、[README](https://github.com/opendatalab/DocLayout-YOLO/blob/main/README.md)、[arXiv:2410.12628](https://arxiv.org/abs/2410.12628) |
| PP-DocLayout-S | **Apache-2.0** | 约 **4.8 MB** | 未在卡片说明 | 未在卡片说明 | 卡片 language: en, zh | [HF API (mirror)](https://hf-mirror.com/api/models/PaddlePaddle/PP-DocLayout-S) |
| PP-DocLayout-M | **Apache-2.0** | **未确认**（未取到 usedStorage） | 未在卡片说明 | 未在卡片说明 | en, zh | [HF page](https://huggingface.co/PaddlePaddle/PP-DocLayout-M) |
| PP-DocLayout-L | **Apache-2.0** | 约 **129 MB** | RT-DETR-L | **23 类** | en, zh；自建评测集含**中文试卷** | [HF API (mirror)](https://hf-mirror.com/api/models/PaddlePaddle/PP-DocLayout-L)、[卡片 README](https://huggingface.co/PaddlePaddle/PP-DocLayout-L) |
| PP-DocLayoutV2 | **Apache-2.0** | 约 **214 MB** | — | 25 类（社区整理，见 1.3） | en, zh, multilingual | [HF API (mirror)](https://hf-mirror.com/api/models/PaddlePaddle/PP-DocLayoutV2) |
| PP-DocLayoutV3 | **Apache-2.0** | 约 **131 MB** | 任务标为 image-segmentation | 同上 25 类 | en, zh, multilingual | [HF API (mirror)](https://hf-mirror.com/api/models/PaddlePaddle/PP-DocLayoutV3) |
| RapidLayout | **Apache-2.0** | 依所选子模型而定 | 推理库（ONNXRuntime 等），聚合多种模型 | 依子模型 | 中英文版面分析 | [repo API](https://api.github.com/repos/RapidAI/RapidLayout) |

关键官方原文（PP-DocLayout-L 卡片）：

> "A high-precision layout area localization model trained on a self-built dataset containing Chinese and English papers, magazines, contracts, books, **exams**, and research reports using **RT-DETR-L**. The layout detection model includes **23 common categories** … mAP(0.5) **90.4**"
> "the evaluation set … is a self built layout area detection data set, including 500 document type images such as Chinese and English papers, newspapers, research papers and **test papers**."

这两点直接回答「是否支持中文教材」：**官方自述的训练/评测集明确包含中文试卷**，但**并未给出「教材扫描件」专项指标**，且 90.4 mAP 是自建集上的数字，不可与公开榜直接比较。

### 1.2 官方近期动态（重要，影响选型）

- PP-DocLayoutV2 的 arXiv 关联为 **arXiv:2510.14528**（Hugging Face 卡片 tag），即 **PaddleOCR-VL: Boosting Multilingual Document Parsing via a 0.9B Ultra-Compact Vision-Language Model**（[abs 页](https://arxiv.org/abs/2510.14528)）。该报告说明版面检测模型是 PaddleOCR-VL 系的前置组件。[RapidLayout 官方博客](https://rapidai.github.io/RapidLayout/latest/blog/2026/02/10/support-PP-DocLayoutv2-v3/) 亦如此表述：
  > "PP-DocLayout 系列模型在版面分析方面效果很好，目前已经作为 PaddleOCR-VL 系列模型的前置"
- **PP-DocLayoutV3 是目前下载量最高的版本**（HF API downloads **41,937**，likes **121**，lastModified 2026-09-30），远超 PP-DocLayout-L（1,632）。这是社区活跃度的客观信号。

### 1.3 关于「能不能微调出 Q/W/A/E 角色」

- **技术上可以**：DocLayout-YOLO 明确给出微调流程（D4LA / DocLayNet 的 YOLO 格式数据 + ultralytics 训练脚本，见 [README](https://github.com/opendatalab/DocLayout-YOLO/blob/main/README.md)）。PP-DocLayout 系列为 RT-DETR 系，官方提供训练模型与微调入口（[Text Image Rectification 页面](https://www.paddleocr.ai/latest/en/version3.x/module_usage/text_image_unwarping.html) 说明官方模块「supports secondary development, allowing you to fine-tune the models on your own datasets」）。
- **但类别是固定的通用语义**：PP-DocLayout 的类别为 text / paragraph_title / doc_title / table / figure / formula 等版面**类型**，**没有 Q/W/A/E 这种业务角色**。把通用标签映射到业务角色，会丢失「这是选项还是题干」的区分信息。
- **结论**：要拿到 Q/W/A/E，只有两条路——(a) 自标注 + 微调检测器；(b) 通用检测器出框 + 规则/模型判角色。**没有任何官方模型开箱给出 Q/W/A/E。**

### 1.4 必须标注的不确定项

- **DocLayout-YOLO 权重文件体积：未确认。** 官方文档指向 `julioz/DocLayout-YOLO-DocStructBench`，但该仓库经镜像 API 访问返回 **401 Invalid username or password**（可能为 gated/受限或镜像鉴权失败），无法读取文件大小。请勿引用任何具体 MB 数。
- **PP-DocLayoutV2/V3 的 25 类标签表**：来自 RapidLayout 维护者博客中插入 ONNX metadata 的 `paper_label` 列表，**属二手整理**，未在 PaddlePaddle 官方卡片中找到同样列表，标注为**社区来源**。
- 搜索命中的 `JulioZhao97/DocLayout-YOLO` 是**仅 3 star 的 fork**（AGPL-3.0，2024-10 后无推送）。规范上游是 `opendatalab/DocLayout-YOLO`（**2,292 star**，178 fork，last push 2025-04-14）。引用时不要引用 fork。

### 1.5 建议

- **采纳**：Apache-2.0 的 **PP-DocLayoutV3**（或 V2）作为「通用版面出框 + 公式/图/表区域」的基线；若需最小依赖，**RapidLayout**（Apache-2.0，ONNXRuntime 路线，恰好匹配本机 `onnxruntime 1.25`）作为集成层。
- **采纳（有条件）**：**DocLayout-YOLO 作为可微调骨干**——架构是 YOLOv10，微调成本低、生态成熟、有明确的 YOLO 格式训练链路。但必须先确认 **AGPL-3.0 对交付形态是否可接受**（网络服务分发会触发 AGPL 义务）。
- **不采纳**：任何「直接用通用版面标签当 Q/W/A/E」的省事做法。
- **不需要量化**：全部候选权重 ≤ ~220 MB，8GB 显存跑 fp16 有巨大余量。量化只在你走 VLM 路线时才成为议题（而 VLM 路线见 Q4，不推荐）。
- **8GB 定量说明**：上述体积是**磁盘体积**，不是显存占用。显存峰值约等于权重 + 激活 + 框架开销；以 <220 MB 权重的检测器计，8GB 下不会 OOM。**精确显存峰值未实测，标注为未确认**——需由 alayout 在本机实测（这正是他的任务）。

---

## Q2. 公式识别：Pix2Text / LaTeX-OCR 及 2025 后的替代品

### 2.1 一手事实

| 项目 | 许可证 | star | 最近推送 | 说明 |
|---|---|---|---|---|
| **Pix2Text**（`breezedeus/Pix2Text`） | **MIT** | 3,273 | 2026-08-23 | 自述「SMALL models」做版面/表格/公式(LaTeX)/文本 → Markdown，定位 Mathpix 免费替代，支持 80+ 语言 |
| **LaTeX-OCR**（pix2tex，`lukas-blecher/LaTeX-OCR`） | **MIT** | **16,593** | 2025-01-18 | ViT 把公式图转 LaTeX；issue 158 个（活跃度高但**上游推送已停在 2025-01**） |
| **PP-FormulaNet_plus-L** | **Apache-2.0** | — | 2025-07-22 | 官方公式识别模型 |
| **PP-FormulaNet_plus-S** | **Apache-2.0** | — | 2025-07-22 | 同上，小号 |

来源：[Pix2Text repo API](https://api.github.com/repos/breezedeus/Pix2Text)、[LaTeX-OCR repo API](https://api.github.com/repos/lukas-blecher/LaTeX-OCR)、[PP-FormulaNet_plus-L](https://hf-mirror.com/api/models/PaddlePaddle/PP-FormulaNet_plus-L)、[PP-FormulaNet_plus-S](https://hf-mirror.com/api/models/PaddlePaddle/PP-FormulaNet_plus-S)。

**体积（重要口径澄清）**：HF API 的 `usedStorage` 是**整个仓库**的占用，包含 `inference.pdiparams`（推理权重）**和训练权重**，因此不能当作部署体积：
- PP-FormulaNet_plus-L：`usedStorage` = 727,598,255 B ≈ **728 MB（仓库口径，≠ 部署体积）**
- PP-FormulaNet_plus-S：`usedStorage` = 256,845,006 B ≈ **257 MB（同上口径）**

各模型的**纯推理权重文件大小：未确认**（需读 `inference.pdiparams` 的 Content-Length，本次未取到）。

### 2.2 判断

- **可用性口径**：Pix2Text 和 LaTeX-OCR 都是 MIT，许可证上最宽松，可放心本地用。
- **LaTeX-OCR 的活跃度风险**：16.6k star 但上游 `pushed_at` 为 **2025-01-18**，此后无推送（截至 2026-10）。这不等于不能用，但意味着**无上游修复**。作为「一个 MIT 的小模型」仍是低成本选项。
- **2025 年后的替代品**：本次调研**未取得**可核实的「明显优于上述两者的 2025+ 开源公式识别专用模型」的一手对比证据。PaddleOCR 的 PP-FormulaNet_plus 系列（Apache-2.0，官方背书）是最可信的国产替代候选，但**中文数学教辅上的公开精度对比未确认**。
- **教辅场景的真实难点**：数学教辅里公式与中文混排、行内公式（inline）与行间公式（display）混合。PP-DocLayoutV2/V3 的类别表（社区来源）里**显式区分了 `display_formula` / `inline_formula` / `formula_number`**，这对「先出框再识别」的流水线是有利的结构信号。

### 2.3 建议

- **采纳**：**PP-FormulaNet_plus-S/M**（Apache-2.0，与已装 paddleocr 3.7 同生态，零新增依赖）作为首选；**Pix2Text（MIT）** 作为交叉验证/备选。
- **有条件采纳**：LaTeX-OCR（pix2tex，MIT）——许可证友好、star 高，但**上游 2025-01 后停更**，不要作为唯一路径。
- **不采纳**：以「模型体积」为唯一选型依据。数学公式识别的瓶颈在符号结构（分式/根式/上下标）而非图像分辨率，需 acocr 在真实样张上实测 CER。

---

## Q3.（关键业务问题）有没有开源项目直接做「选项独立出框」与「题答配对」？

### 3.1 直接回答：**没有**。

本次检索未发现任何开源项目同时提供「选择题每个选项独立出框 + 题号配对 + 答案解析配对」。**角色判定与配答必须自研。** 以下是能找到的最接近参考。

### 3.2 最接近的项目：HiLEx（ICDAR 2025）—— **强烈建议作为标注规范与数据模板**

- 论文：Aich et al., *HiLEx: Image-Based Hierarchical Layout Extraction from Question Papers*, **ICDAR 2025**, Springer pp. 485–505，[DOI/章节页](https://link.springer.com/chapter/10.1007/978-3-032-04627-7_28)，[项目页](https://hilex-dla.github.io/HiLEx/)，[GitHub](https://github.com/HiLEx-DLA/HiLEx)。
- 规模与许可：**1,965 页**，8 类考试（GMAT/GRE/SAT/JEE/GATE/UPSC/UGC-NET/BANK），标注格式 **YOLO + COCO**，**CC BY 4.0**，Cohen's κ > 0.90。
- **六类层级标签**（与我们的 Q/W/A/E 高度同构）：
  - `Question_Paper_Area` — 整页试卷内容区
  - `Question_Answer_Block` — **一道完整的 Q + 它的选项**（≈ 我们的 Q+W 组合，天然带配对关系）
  - `Question_Block` — 题干文本（不含选项）（≈ **Q**）
  - `Answer_Block` — 选项区（选择题选项 / 作答区）（≈ **W**）
  - `Instruction` — 大题指示语
  - `Description` — 解析/解答说明（≈ **E**）
- 其官方 baseline（同一 train/test 划分）：

| 模型 | 类型 | 训练 | mAP@50 | mAP@50–95 |
|---|---|---|---|---|
| Detectron2 (Faster R-CNN) | 两阶段 | 微调 | **94.0%** | 67.3% |
| YOLOv8 | 单阶段 | 微调 | 84.8% | 66.1% |
| PaLI-Gemma2 | VLM | **零样本** | 83.5% | 59.0% |
| YOLOv11 | 单阶段 | 微调 | 82.2% | **68.9%** |
| Florence-2 | VLM | **零样本** | 81.0% | 59.0% |
| RT-DETR | Transformer | 微调 | 60.6% | 44.8% |
| DETR | Transformer | 微调 | 50.2% | 35.0% |

（参数列：Detectron2 ~41M，YOLOv8 ~35M，YOLOv11 ~50M，RT-DETR ~50M，DETR ~86M，VLM >1B。均来自其项目页 leaderboard。）

**其自身报告的关键失败模式（可直接复用为我们的风险清单）**：
- 最难的类别是 **Instruction 与 Description**（体积小、格式多变）；
- 「over-detection in densely packed answer sections (multiple boxes around the same answer block)」——**密集选项区重复出框**，正是「选项独立出框」会遇到的坑；
- 「Vision-language models occasionally confused descriptions for question text blocks」——**VLM 混淆解析与题干**。

**限制（务必诚实标注）**：
- **仅英文**（8 类考试均为英文试卷）。**没有中文教辅数据**，不能直接当预训练权重迁移到苏科版中文教材。
- 粒度只到 **Answer_Block（整块选项区）**，**不提供单个选项 A/B/C/D 的独立框**。所以即便拿它微调，也只能得到「题干 / 选项区 / 解析」粒度，**每个选项独立出框仍需自己再加一层**。
- 仓库 **license 字段为 null**（数据 CC BY 4.0，**代码许可未声明**）——[repo API](https://api.github.com/repos/HiLEx-DLA/HiLEx)。用它当**标注规范参考**没问题，复用其代码前需确认。
- star 仅 8，工程成熟度低。

### 3.3 其他参考（弱相关，仅供借鉴思路）

- `blue-sky-sea/Paper-Question-recognition`（原仓，12 star，2021 后无推送，**无 license**）：自述用「image processing and regular expression」做题目区域识别。思路与我们「路线C：OCR + 规则」一致，可作为规则法的历史参照，但年代久远、工程价值有限。[repo API](https://api.github.com/repos/blue-sky-sea/Paper-Question-recognition)
- `Lazily01/homework-grader`：自述「上传试卷照片自动切题、识别手写答案、评分并生成详细解析」，走多模态大模型路线。**未见其公开题答配对的算法细节与评测**，仅作为「有人在做同类事」的存在性证据。**未确认**其许可证与可用性。
- 数据集侧还有 `MiliLab/LogicOCR`（搜索命中），**未核实其许可与内容**，标注为未确认。

### 3.4 建议

- **采纳**：以 **HiLEx 的六类层级 schema 作为我们 Q/W/A/E 的标注设计蓝本**，并用其 **YOLO 格式**（`<cls> <cx> <cy> <w> <h>` 归一化）作为自标注数据格式——这样未来可直接用 ultralytics/YOLOv8/v11 训练，迁移成本最低。
- **采纳**：把 HiLEx 报告的三类失败模式（Instruction/Description 漏检、密集选项区重复出框、VLM 混淆解析与题干）写进我们的验收指标。
- **不采纳**：指望 HiLEx 现成权重直接解决中文教辅。它是**英文 benchmark + 标注数据**，不是「配答解决方案」。
- **明确写入方案**：**「角色判定（Q/W/A/E）与题答配对必须自研」**。可拆解为：通用检测器给候选框 → 规则/OCR 文本特征判角色 → 版式几何（上下相邻、x 对齐、行距）做配对。

---

## Q4.（核心判断）VLM 直接输出 bbox 是否可靠？社区怎么拆解？

### 4.1 结论：**不可靠。不建议让 VLM 直接生成像素/归一化坐标作为主路径。**

### 4.2 一手证据（论文/官方仓库 issue，非博客）

1. **同任务直接对比（最有力的证据）**：HiLEx（ICDAR 2025）在同一题卷版面任务上，**微调检测器全面胜过零样本 VLM**：Detectron2 **94.0%** / YOLOv8 **84.8%** vs Florence-2 **81.0%**、PaLI-Gemma2 **83.5%**（且严格 IoU 下 VLM 仅 **59.0%**）。VLM 还出现「把解析当成题干」的语义混淆。[项目页](https://hilex-dla.github.io/HiLEx/)
2. **机制性解释**：VLM-FO1（[arXiv:2509.25916](https://arxiv.org/abs/2509.25916)）原文：
   > "This failure stems from a fundamental mismatch, as **generating exact numerical coordinates is a challenging task for language-centric architectures**."
   其解法是**把「脆弱的坐标生成」重构为「特征检索」**（HFRE 区域编码器 + token-based referencing），即**不由 LLM 生成坐标**。
3. **细粒度检测退化**：InspectVLM（[arXiv:2508.01921](https://arxiv.org/abs/2508.01921)，ICCV 2025 VISION Workshop）原文：
   > "the model exhibits brittle behavior under low prompt variability, **produces degenerate outputs for fine-grained object detection**, and **frequently defaults to memorized language responses regardless of visual input**."
   —— 即「格式不稳 / 幻觉 / 无视图像」三类失败模式同时出现。
4. **真实场景 grounding 差距**：GroundingME（[arXiv:2512.17495](https://arxiv.org/abs/2512.17495)）评测 **25 个 SOTA MLLM**：
   > "the best model achieves only **45.1% accuracy**, while **most score 0% on rejection tasks**."
   其中 Rejection = 识别「不可定位的查询」。**对题干/选项这类同质文本块，拒答能力为 0 意味着模型会硬给一个框。**
5. **坐标系本身就不稳**：Qwen 官方仓库 issue [Qwen3-VL #1485](https://github.com/QwenLM/Qwen3-VL/issues/1485)（19 条评论，35 reactions，作者 `gpt-dance`）原文指出：
   > "从 Qwen2-VL 到 Qwen2.5-VL，再到 Qwen3-VL，坐标体系经历了从 0-1000 到绝对坐标，又回到 0-1000 的变化。在最新的 Qwen3-VL 演示案例中，模型在思考过程中展示的是绝对坐标，而最终生成的动作却又是 0-1000 的范围。"
   —— **同一代模型内部「思考过程的坐标」与「最终输出的坐标」都可以不是同一套**。另有 issue #830「Grounding 归一化问题」、#676「Qwen 2.5 VL grounding mode - coordinates scaling?」、#866「Problem about Visual Grounding in Qwen2 and Qwen2.5」佐证这是长期反复的痛点。**这些是 issue，不是官方规范说明**——恰恰说明官方缺少清晰稳定的坐标契约。

### 4.3 社区提高可靠性的做法（按工程可行性排序）

| 做法 | 依据 | 对本题的适用性 |
|---|---|---|
| **A. 检测器出坐标，模型只判语义** | VLM-FO1 把坐标生成改为特征检索；HiLEx 实测微调检测器胜 VLM | **强烈推荐**。检测器给框 → 裁图 → 模型只回答「这是题干/选项/解析/答案」 |
| **B. 坐标降级为「点」而非「框」** | Point-then-Count（[arXiv:2603.21746](https://arxiv.org/abs/2603.21746)）：先产出目标点坐标再推理，**点被正确 ground 的比例 >94%（F1）**，且优于多种微调/免训练方案 | 可用作辅助定位，但**该证据来自 counting 任务，不是文档版面**，迁移性未验证 |
| **C. 用参考 token / 离散 id 代替数值坐标** | VLM-FO1 的 token-based referencing | 需改模型结构，工程成本高，不适合本项目 |
| **D. 后处理校验与拒答训练** | GroundingME：数据混合训练把 rejection 准确率 **0% → 27.9%** | 成本高（要训练），收益仍只有 27.9%，**性价比低** |
| **E. 约束输出格式并重试** | 无一手证据支持具体增益 | 只能压「格式不稳」，压不住「坐标不准」与「幻觉」 |

### 4.4 8GB 显存下 VLM 路线的实测口径（回答「可行性」）

- **Qwen2.5-VL-3B-Instruct**：HF API 给出 `safetensors.parameters.BF16 = 3,754,622,976`，`usedStorage = 7,509,337,976 B ≈ 7.51 GB`。即**官方仓库 bf16 权重约 7.5 GB**，在 8GB 卡上**几乎刚好塞满**，留给视觉 token 激活与 KV cache 的空间极小（尤其在扫描件高分辨率输入下）。[HF API (mirror)](https://hf-mirror.com/api/models/Qwen/Qwen2.5-VL-3B-Instruct)
- **许可证**：该卡片 `cardData.license_name` = **`qwen-research`**（非 Apache-2.0）。Qwen2.5-VL 系列使用研究用途许可，**商用前必须单独确认**。[许可证文件](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct/blob/main/LICENSE)
- 7B 级 VLM（Qwen2.5-VL-7B / InternVL 7B / MiniCPM-V 8B 量级）在 bf16 下权重即 ≥14 GB，**8GB 必然需要 4-bit 量化 + offload**，而量化会进一步削弱本就不可靠的坐标精度。**具体量化后的显存与精度：未确认**。
- **重要例外（值得 lead 注意）**：PaddleOCR-VL 是 **0.9B 的文档解析专用 VLM**（NaViT 风格动态分辨率视觉编码器 + ERNIE-4.5-0.3B），自述在页面级解析与元素级识别上达 SOTA，**且用 PP-DocLayoutV2 作前置版面检测**（[arXiv:2510.14528](https://arxiv.org/abs/2510.14528)）。这恰好印证了 4.3 的做法 A：**连官方 VLM 方案也不让 VLM 自己出坐标，而是用检测器出框。**

### 4.5 建议

- **采纳**：**「检测器出框 + 规则/VLM 判角色」两阶段**。禁止把「VLM 直接吐 bbox」作为主路径。
- **有条件采纳**：若确实要引入 VLM 做角色判定，**只让它处理已裁切的小图**并输出**离散标签**（Q/W/A/E），不输出坐标；此时候选为 **PaddleOCR-VL-0.9B**（文档专用、体积小、与现有 paddle 生态一致）优先于 Qwen2.5-VL-3B（7.5GB 吃满显存 + research 许可）。
- **不采纳**：Qwen2.5-VL-3B bf16 直接跑在 8GB 上做全页出框。
- **不采纳**：Point-then-Count 直接迁移（语料是自然图像 counting，非文档版面）。

---

## Q5. 扫描件倾斜/透视/双栏的开源常规做法

### 5.1 倾斜与透视：**官方有现成模块，直接采纳**

PaddleOCR 官方的 **Document Image Preprocessing Pipeline**（[官方文档](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/doc_preprocessor.html)）原文：

> "The Document Image Preprocessing Pipeline integrates two key functions: **document orientation classification** and **geometric distortion correction**. The document orientation classification module automatically identifies the four possible orientations of a document (**0°, 90°, 180°, 270°**) … The **text image unwarping** model is designed to correct geometric distortions that occur during document photographing or scanning, restoring the document's original shape and proportions."

一手模型指标（同页官方表格）：

| 模块 | 模型 | 指标 | 体积 | 备注 |
|---|---|---|---|---|
| 方向分类 | `PP-LCNet_x1_0_doc_ori` | Top-1 Acc **99.06%** | **7 MB** | 0/90/180/270 四方向 |
| 文本图像矫正 | `UVDoc` | CER **0.179**（DocUNet 基准），GPU 19.05 ms | **30.3 MB** | 校正扭曲、透视形变 |

同时 PP-StructureV3 的开关也印证了工程入口（见 [PP-DocLayout-L 卡片](https://huggingface.co/PaddlePaddle/PP-DocLayout-L)）：
```
ocr = PPStructureV3(use_doc_orientation_classify=True)
ocr = PPStructureV3(use_doc_unwarping=True)
ocr = PPStructureV3(use_textline_orientation=True)
```

**关键实践提醒**：`use_doc_orientation_classify` / `use_doc_unwarping` / `use_textline_orientation` **默认关闭**，需要显式开启。很多人抱怨「坐标偏了」的原因就是没开这几项——**这直接关系到 acoord 正在查的坐标空间问题**。

### 5.2 双栏切分：**没有现成可直接用的开源产出，需自研**

- 本次检索**未找到**任何开源项目明确提供「双栏切分」这个独立功能模块的输出（既非 PaddleOCR 的模块清单项，也非独立库）。PaddleOCR 模块清单里没有 column segmentation 条目（[模块总览](https://www.paddleocr.ai/latest/en/version3.x/module_usage/module_overview.html)）。
- 业界通用做法是**间接实现**：版面检测先给出 text/formula/figure 等块框 → 在**页级**统计块框 x 中心的投影直方图 → 找「竖向空白谷」作为栏缝 → 按「栏内自上而下、栏间自左至右」重排阅读顺序。**本结论属通行工程实践推断，未取得一手文档佐证，标注为未确认。**
- HiLEx 的贡献在此有间接价值：它明确覆盖 **single-column 与 multi-column** 两类版式，且 `Question_Paper_Area` 是最容易检测的类（体积大、贴近页边界），说明**「先用整页区域框定内容范围、再在内部切栏」**是可行的分层策略。[项目页](https://hilex-dla.github.io/HiLEx/)
- 另一类参考是 MinerU（`opendatalab/MinerU`，**81,811 star**，最近推送 2026-10-14，[repo API](https://api.github.com/repos/opendatalab/MinerU)），但它输出的是内容级 Markdown/JSON，**不提供题目级框与配答**。且其 GitHub license 字段为 **`other` / NOASSERTION**（不是标准 OSI 标识），**实际许可条款未确认**，用作依赖前需核实。

### 5.3 建议

- **采纳**：先跑 **PP-LCNet_x1_0_doc_ori（7MB）+ UVDoc（30.3MB）** 做方向与几何矫正；两个模型都极小，8GB 无压力，且官方支持自数据集微调。
- **采纳（自研）**：双栏切分用「版面框 x 投影 + 栏缝检测 + 阅读顺序重排」自行实现，并**在流水线早期完成**——否则后续所有框的坐标与配对都会错。
- **不采纳**：把 MinerU 当版面检测依赖（它解决的是另一个问题，且许可不清）。
- **未确认**：UVDoc 在**中文教辅扫描件**（而非 DocUNet 摄影失真基准）上的实际收益。需要 alayout/acocr 用真实样张实测。

---

## 6. 最终选型建议（3 条最强）与风险（2 条）

### 6.1 推荐路线：两阶段「检测器出框 → 语义判角色 → 几何配答」

```
扫描页
 ├─(预处理) PP-LCNet_x1_0_doc_ori (7MB) ─ 方向矫正 0/90/180/270
 ├─(预处理) UVDoc (30.3MB) ─ 几何/透视矫正
 ├─(版面)   PP-DocLayoutV3 (Apache-2.0, ~131MB) 或 DocLayout-YOLO(AGPL) 微调
 │            └ 输出: text / formula / inline_formula / figure / table 等区域框
 ├─(自研)   栏缝投影切分 + 阅读顺序重排        ← 必须自研
 ├─(自研)   角色判定: OCR 行文本 + 规则 → Q / W / A / E   ← 必须自研
 ├─(自研)   配答: 题号正则 + 几何相邻/对齐      ← 必须自研
 └─(公式)   PP-FormulaNet_plus-S/M (Apache-2.0) 或 Pix2Text (MIT)
```

**最强 3 条建议**

1. **架构上坚持「检测器出坐标、模型只判语义」**。依据：HiLEx 实测微调检测器 94.0% vs VLM 零样本 81–83.5%（严格 IoU 仅 59%）；VLM-FO1 明确指出「精确数值坐标生成对语言中心架构本身就是难任务」；PaddleOCR-VL 官方方案自己也是用 PP-DocLayoutV2 当前置。**禁止让 VLM 直接吐 bbox 做主路径。**
2. **数据契约抄 HiLEx 的六类层级 schema（CC BY 4.0，YOLO 格式），但中文教辅数据必须自建**。HiLEx 覆盖 1,965 页、κ>0.90、含单双栏，是**标注规范与验收指标的最佳蓝本**；但**仅英文、且只到 Answer_Block 粒度**，拿不到单个选项 A/B/C/D 的独立框。第一个里程碑应该是「用现有样张跑通 + 人工标 20–30 页」来验证类别可分性。
3. **8GB 下选 Apache-2.0 小模型全本地跑，暂不引入 VLM、不需要量化**。PP-DocLayoutV3 ~131MB + UVDoc 30.3MB + PP-LCNet_doc_ori 7MB + PP-FormulaNet_plus 系列，全部远低于显存上限；反而 **Qwen2.5-VL-3B 的 bf16 权重就是 7.5GB**，还带 `qwen-research` 非商用许可——**成本与许可两头都不划算**。等本地规则/检测基线跑不通时，再考虑 API 或 PaddleOCR-VL-0.9B。

### 6.2 风险 2 条

1. **许可风险（会改变交付形态）**：
   - `opendatalab/DocLayout-YOLO` = **AGPL-3.0**（网络服务分发触发开源义务），与我方可能的分发形态冲突；
   - `Qwen/Qwen2.5-VL-3B-Instruct` = **`qwen-research`（研究用途）**，**非 Apache-2.0**；
   - `opendatalab/MinerU` = **`other`/NOASSERTION**，条款不明；
   - `HiLEx` 数据 CC BY 4.0 但**代码 license 为 null**；`Paper-Question-recognition` **无 license**。
   → **缓解**：主干依赖全部锁定在 **Apache-2.0（PP-DocLayout 系列 / RapidLayout / PP-FormulaNet）** 与 **MIT（Pix2Text / LaTeX-OCR）**；AGPL 组件只做「离线评测对照」，不进交付物。
2. **精度与坐标风险（会让配答整体错位）**：
   - 三项叠加：PP-DocLayout 精度是**自建集口径**（90.4 mAP，非公开榜），中文教辅无专项验证；HiLEx 已证 **Instruction/Description 漏检**与**密集选项区重复出框**；Qwen 系坐标系在 2-VL→2.5-VL→3-VL 间反复变动（官方 issue #1485）。任何一环出问题，下游 Q/W/A/E 与配答都会连锁错。
   → **缓解**：(a) 流水线**第一步**就开 `use_doc_orientation_classify=True` + `use_doc_unwarping=True`（默认关闭，这是坐标偏移的高频根因）；(b) 所有中间产物**同时落盘「原图像素坐标」与「所用参考系」元数据**（与 acoord 的调查对齐）；(c) 在真实样张上定「出框召回 / IoU@0.5 / 选项切分正确率 / 配答正确率」四个可量化指标，用 HiLEx 的三类已知失败模式做对照测例。

---

## 6.3 与队友本地产出的对齐（跨任务核对，非外部资料）

调研期间读取了队友已落盘的只读状态文件，发现两点与本报告结论直接相关，供 lead 做一致性核对：

1. **Q5 的「双栏切分需自研」已被本地产出证实。** `data/derived/image_layout.json`（alayout 产出）已经实现了**投影/分栏检测**，字段包括 `min_run` / `span_frac` / `thresh` / `max_ink`、`n_inner_v_gutters`、`panels_v` / `panels_h`。这与本报告 5.2 推断的「版面框 x 投影 + 栏缝检测」路径**一致**，属独立佐证。
2. **样张确实同时存在单栏与多栏两种版式。** 同一文件的跨页统计：

   | 页 | 尺寸 | 内部竖向栏缝数 | 竖向面板数 | 横向面板数 |
   |---|---|---|---|---|
   | 7 | 1178×1673 | 0 | 1 | 25 |
   | 8 | 1176×1681 | 0 | 1 | 16 |
   | 9 | 1179×1671 | 0 | 1 | 19 |
   | 10 | 1175×1674 | 0 | 1 | 20 |
   | 233 | 3467×1615 | **5** | **6** | 2 |
   | 234 | 3465×1615 | **3** | **4** | 2 |

   第 233/234 页为**横向跨页（3467×1615）且含 3~5 条内部竖向栏缝**，即典型多栏版式；第 7–10 页为纵向单栏。这直接支撑本报告 Q5 的判断：**分栏必须作为流水线早期步骤**，且**同一本书内就要处理两种版式**——HiLEx 也报告了 single-column 与 multi-column 并存（见 [项目页](https://hilex-dla.github.io/HiLEx/)）。
3. **Q3 的「数据已按题/选项/答案分别标注」已被本地产出证实。** `data/derived/analysis/coord_evidence/annimg/` 下的文件名形如 `..._<idx>_question_0@page_N_*.jpg`、`..._<idx>_choice_0@page_N_*.jpg`、`..._<idx>_answer_0@page_N_*.jpg`，说明**「选项独立出框」在数据侧已经存在**（维度为 question / choice / answer）。
   - 对本报告 Q3 的修正/细化：外部**没有**开源方案直接做「选项独立出框 + 配答」，但**我们自己的数据标注已经具备选项级粒度**。因此缺的不是数据，而是**算法（角色判定与配答）**——进一步支撑 Q3 的「必须自研」结论。
   - 同时提醒：`question` / `choice` / `answer` 三个维度的**坐标参考系必须统一**，这正与 acoord 在查的坐标空间问题相关（见 6.2 风险 2 的缓解措施 (b)）。

> 说明：以上仅为本报告的**交叉核对**，不是外部一手资料，不作为选型依据；若与 alayout/acoord 的最终结论冲突，以他们的实测为准。

---

## 7. 未确认清单（请勿当成事实引用）

1. **DocLayout-YOLO 权重文件体积** —— HF 仓库经镜像返回 401，未取到。
2. **PP-DocLayout-M 的具体体积** —— 未取到 `usedStorage`。
3. **PP-DocLayoutV2/V3 的 25 类标签表** —— 仅有 RapidLayout 博客（社区来源），未见 PaddlePaddle 官方列表。
4. **PP-FormulaNet_plus-L/S 的纯推理权重体积** —— 仅有仓库总占用（含训练权重），非部署体积。
5. **中文数学教辅上各公式识别模型的公开 CER 对比** —— 未取得一手评测。
6. **Pix2Text 所捆绑各子模型（MFD/MFR/CNSTD 等）的许可证** —— 仅主仓 MIT 已确认，子模型未逐个核实。
7. **InternVL / MiniCPM-V 在 8GB 上的量化后显存与精度** —— 未取得官方数字（未做无根据推算）。
8. **PaddleOCR-VL-0.9B 的权重磁盘体积与显存占用** —— 未取到官方数字。
9. **双栏切分的「开源标准做法」** —— 未找到一手文档，5.2 的投影法是工程通行推断。
10. **UVDoc 对中文教辅扫描件的增益** —— 官方指标是摄影失真基准（DocUNet），场景不同。
11. **`Lazily01/homework-grader`、`MiliLab/LogicOCR` 的许可与算法细节** —— 仅存在性，未核实。

---

## 8. 来源索引

一手来源（官方文档 / 论文 / API 元数据）已内联标注。结构化列表见同目录 [vision_stack_sources.json](./vision_stack_sources.json)。
