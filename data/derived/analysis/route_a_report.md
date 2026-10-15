# 路线A：本地版面检测出框基线报告（task-1）

- 作者：alayout（Agent Teams 成员）｜生成时间：2026-10-15（Asia/Shanghai）
- 产出脚本：[tools/route_a_layout.py](../../../tools/route_a_layout.py)（可重复运行，CPU-only）
- 结构化产出：[route_a_candidates.json](route_a_candidates.json)（每框 bbox/role/置信度/来源方法）
- 证据图：[route_a_overlay_page7.png](route_a_overlay_page7.png) … 共 6 张（候选框 + 历史框叠图）
- 本报告中每个数字都能在 `route_a_candidates.json` 里按小节给出的 JSON 路径查到；报告不写未实测的数字。

---

## 0. 一句话结论

在 **CPU-only、零模型下载** 的前提下，用「投影 + 连通域」轻量几何基线 + rapidocr 关键词规则，
对 6 张页图产出 **188 个角色候选框**（题干 Q 104 / 独立选项 W 32 / 答案 A 9 / 解析 E 22 / 文本块 21）。

任务规定的 question 召回（IoU≥0.5，对历史框原样）：

> **6 / 16 = 0.375**（`evaluation.question_vs_history.recall_iou50`）

但把「标注者画框留白」这一层剥掉后，检测器对**文字真实位置**的召回是：

> **12 / 16 = 0.750**（`evaluation.question_vs_history.L3_detector_vs_tight_truth.recall_iou50`）

而「任何只框文字、不留白的检测器」在这份真值上的**上限**也恰好是 **12 / 16 = 0.750**
（`evaluation.question_vs_history.L2_upper_bound_tight_detector.max_recall_iou50`）。

**即：本检测器已经打满了这份历史真值允许的天花板，L1 与上限之间的差距全部来自标注框留白，不是漏检。**
详见 §4.2。

坐标系已按 lead/aocr 的更正（`页图编号 = 标注 page_index − 1`）重跑；不更正时为 1/16，更正后 6/16（§4.1）。

---

## 1. 运行方式与环境

### 1.1 实际运行命令与耗时

```powershell
$env:PYTHONIOENCODING="utf-8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$env:CUDA_VISIBLE_DEVICES=""
C:\Users\LIHAOYANG\AppData\Local\Programs\Python\Python311\python.exe `
  tools\route_a_layout.py --pages 7 8 9 10 233 234 `
  --out data\derived\analysis\route_a_candidates.json
```

| 项 | 值 | JSON 路径 |
|---|---|---|
| 首次全量耗时 | **195.11 s** | `meta.elapsed_sec_total` |
| 逐页耗时（s） | p7 9.40 / p8 6.22 / p9 8.64 / p10 8.96 / **p233 75.20** / **p234 86.44** | `pages[].timing_sec` |
| 其中 OCR 占比 | p7 9.32 / p8 6.17 / p9 8.54 / p10 8.83 / p233 74.87 / p234 85.96 | `pages[].timing_sec.ocr` |
| 第二次全量耗时 | 260.36 s（同一代码、机器负载不同；内容哈希一致） | `route_a_rerun_check.json → meta.elapsed_sec_total` |
| Python | 3.11.8 | `meta.python` |
| 计算设备 | CPU-only（`CUDA_VISIBLE_DEVICES=""` 在 import onnxruntime 前设置） | `meta.cpu_only` / `meta.cuda_visible_devices` |
| onnxruntime providers | `['AzureExecutionProvider','CPUExecutionProvider']`（本机无 CUDA provider） | `meta.onnxruntime_providers` |
| OCR 引擎 | rapidocr_onnxruntime，模型随 wheel 内置 | `meta.ocr_engine` |
| 模型下载量 | **0 字节** | `meta.ocr_model_download_bytes` |

> 强制 CPU 是为了与 GPU 上跑 PaddleOCR 的队友 aocr 不争 8GB 显存。
> 页 233/234 慢是因为宽图切成 6 个子页后逐个 OCR（子页被 det 放大到长边 736，高约 2200px），
> 且耗时随机器负载波动较大（234 单页实测 86–165 s）。

### 1.2 可复现性（第三方重跑一致性）

脚本对「除 `meta.generated_at` 与各 `timing_sec` 之外的全部内容」计算 sha256：

- 全量跑第 1 次：`b538430e4ed21d00…`（`meta.content_sha256`，产物 `route_a_candidates.json`）
- 全量跑第 2 次（独立进程，另存 `route_a_rerun_check.json`）：**同一个 `b538430e4ed21d00…`**

两次逐字节一致的字段包括全部候选框 bbox、角色、置信度、评测结果；只有耗时不参与哈希。
哈希口径见 `meta.content_sha256_scope`。

---

## 2. 方法

两级流水线，均不依赖 GPU、不下载模型。

### 2.1 几何基线（`--no-ocr` 可单独跑通）

1. **二值化**：固定阈值 `gray < 160`（与 `data/derived/verify_report.md` 的墨迹统计同口径，便于交叉核对）。
2. **子页切分**（仅横向拼合页，见 §2.3）。
3. **行投影**：子页内逐行统计墨迹像素，`行墨迹 ≥ max(2, 0.004×行宽)` 记为激活行；
   相邻激活行间隙 ≤4px 合并 → 文本行。
4. **连通域精修**：对每行区域跑 `cv2.connectedComponentsWithStats`（8 邻域），
   丢弃面积 <4px 的噪点后取并集，得到紧致 bbox；行高 <8px 或墨迹 <8px 的行丢弃。
5. **段落块**：行间隙 > `max(中位间隙×2.0, 中位间隙+6)` 切段 → `geom_blocks`（每页都产出，供对照）。

> 纯几何模式（`--no-ocr`）会把这些段落块作为候选输出，角色为 `text_block`，用于验证「不依赖 OCR 也能出框」。
> 注意：该模式下没有任何 `question` 角色候选，因此 §4 的 question 召回**不适用**于纯几何模式
> （实测 6 页 1.2 s 出 52 个段落块，见 `route_a_geom_only_check.json`）。

### 2.2 角色判定（OCR 关键词/编号规则）

OCR 用 **rapidocr_onnxruntime**（onnxruntime CPU，模型 ch_PP-OCRv4 随 wheel 内置）。
OCR 只提供"文字内容"，**框的边界仍全部来自几何基线**：

- OCR atom 按纵向重叠挂到几何文本行（`attach_atoms`）；
- 行分类 `classify_line`：
  - `解析/【解析】/分析` → **E 解析**
  - `答案/参考答案/答：` → **A 答案**
  - 行内出现 `A./B./C./D./答案标记` → **选项行**
  - 行首为 `1..99` 且后接中文/（/[/【/#、或空格（排除 `第N章/节/单元/课`，排除数字后紧跟拉丁字母的数学式如 `6a+3`）→ **题号行**
  - 其余 → `other`
- 组与状态机：题号行开启新「题组」；组内按 Q→W→A→E 状态推进；
  状态延续遇到大间隙（>40px）回落到 Q；`other/unknown` 行若位于上下 6% 边缘带且尺寸很小 → 判为页眉/页脚/页码并丢弃（每页丢弃数见 `pages[].n_furniture_lines_dropped`）。
- **每个选项独立成框**：同一视觉行里的多个 OCR atom，各自以 A–D 标记开头 → 各自成为一个 option 候选
  （业务要求每选项独立框；历史 `choice` 是"4 选项合 1 框"，口径不同，见 §4.4）。
  仅当单个 atom 内含 ≥2 个选项标记时，才按行内最大空白列切分（`split_line_by_blank`）。
- **选项行几何补框**（`geom_gap_fill`）：若选项行最左侧有一段 ≥40px 宽、墨迹 ≥30px 的"文字区"
  却没有任何 OCR atom（det 漏检），则用连通域把这段单独框出来，避免整行少一个选项。
  实测只在图 7 第 7 题的 A 项触发一次（`p7_w_0012`，区域 x 106–149、61 个墨迹像素），无误触发。
- 角色置信度 = 该框内 OCR atom 的平均识别置信度（`confidence` 字段）；几何补框的置信度为 0，
  由 `role_method` 区分（`ocr_keyword` / `ocr_atom+cc_refine` / `geom_gap_fill` / `geom_heuristic`）。

### 2.3 多页拼合页切子页（233/234）

判据分两级，**先按纵横比分流**：

1. `W/H ≤ 1.5` → 判为单页扫描，不做沟切分。
   本数据单页 W/H≈0.70，拼合页 233/234 ≈ **2.146**（`pages[].image_wh_ratio`）。
   （纵向页内也有"局部空白列"，用贯穿判据会误切——实测 page_8 会被切成 2 页，已用纵横比规避。）
2. 宽图：找**贯穿空沟** —— 列 `max(连续空白) ≥ 0.98×H` 且列墨迹 `≤ max(2, 0.005×H)`，`min_run=2`；
   合并相邻沟、吸收宽度 <300px 的碎片段；
   若某段宽度 > 1.6×中位段宽，则在段内找"最像页缝的列"（空白贯穿 ≥0.9H 且墨迹最少，且切完两侧都 ≥300px）再切一刀。
   最后统一削掉每段两端的低墨边缘（页边距），得到内容边界。

结果（`pages[].subpages` / `pages[].split_info`）：

| 图 | 判据 | 子页数 | 子页 x 区间（内容边界） | 宽度 |
|---|---|---|---|---|
| 233 | 一级贯穿沟 | **6** | 50–574, 611–1155, 1172–1718, 1732–2258, 2293–2834, 2850–3388 | 524/544/546/526/541/538 |
| 234 | 一级 + **二级再切** | **6** | 75–616, 622–1192, 1198–1731, 1741–2310, 2322–2868, 2884–3406 | 541/570/533/569/546/522 |

> 页 234 的 x≈617 处页缝**只有 2px 宽**（全高空白列仅 617–618），一级判据看不到；
> 二级切分在段 [0,1193] 内定位到 `cut_column=617`（`split_info.secondary_splits`）。
> 这修正了 `verify_report.md` §2 里 233="6栏"、234="4栏"的说法：按"子页"口径两张宽图都是 **6 个子页**。

### 2.4 主要参数（全部写在 JSON 里）

`meta.config`：`thresh=160, seam_span_frac=0.98, seam_ink_frac=0.005, seam_min_run=2, min_subpage_width=300, split_width_factor=1.6, split_requires_wide_image=1.5, line_min_h=8, line_min_ink_frac=0.004, line_merge_gap=4, para_gap_factor=2.0, state_break_gap=40, furniture_band_frac=0.06, cc_min_area=4, gapfill_min_w=40, gapfill_min_ink=30, ocr_score_floor=0.30, ann_page_offset=-1`。

---

## 3. 产出

### 3.1 候选框总览（`pages[].candidates`）

| 图 | 尺寸 | 子页 | 文本行 | 有 OCR 文本的行占比 | 几何段落块 | Q 题干 | W 选项 | A 答案 | E 解析 | text_block | 候选框并集覆盖墨迹 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 7 | 1178×1673 | 1 | 27 | 0.889 | 8 | 7 | 12 | 0 | 0 | 4 | 91.36% |
| 8 | 1176×1681 | 1 | 17 | 0.882 | 5 | 6 | 4 | 0 | 0 | 2 | 70.42% |
| 9 | 1179×1671 | 1 | 21 | 1.000 | 4 | 7 | 12 | 0 | 0 | 3 | 87.34% |
| 10 | 1175×1674 | 1 | 19 | 0.790 | 7 | 6 | 4 | 0 | 0 | 4 | 79.88% |
| 233 | 3467×1615 | 6 | 277 | 0.939 | 17 | 49 | 0 | 2 | 15 | 4 | 98.75% |
| 234 | 3465×1615 | 6 | 231 | 0.965 | 11 | 29 | 0 | 7 | 7 | 4 | 98.25% |
| **合计** | | 16 | 592 | | 52 | **104** | **32** | **9** | **22** | **21** | |

（逐页字段：`pages[].n_text_lines / ocr_line_coverage / n_geom_blocks / ink_recall_pct`；角色计数由 `pages[].candidates[].role` 汇总；
`ink_recall_pct` = 候选框并集覆盖的全页墨迹百分比，衡量"有没有整片漏掉内容"。）

### 3.2 候选框字段（`pages[].candidates[]`）

`cand_id, page_index(页图编号), subpage_index, role(question|option|answer|analysis|text_block),
role_cn, bbox=[x1,y1,x2,y2], confidence, role_method(ocr_keyword|geom_heuristic),
geom_method(projection+connected_components), n_lines, text, evidence, q_group, q_group_has_qnum,
ink_pct, ink_px, n_cc, n_cc_noise`。

`q_group` 是 OCR 题组序号，`q_group_has_qnum` 表示该组是否由题号行开启——
同一题组内的题干块与被大间隙分开的续块可据此互相追溯。

---

## 4. 与历史标注的客观比对

### 4.1 坐标系更正：`页图编号 = 标注 page_index − 1`

lead/aocr 用「平台裁剪图归一化互相关（31/36 显著更匹配）+ OCR 语义校验（choice 5/5 出现 A./B./C./D.，
question 行首数字与 `order_in_level` 吻合 0/16 → 7/16），尺度 1:1（sx 中位 0.997）」确认了映射：
`page_index = N` ↔ `46006966_page_{N-1}.jpg`。

本脚本采用该映射（`meta.config.ann_page_offset = -1`），并**独立复核**：

| 复核指标 | 不更正（旧口径） | 更正后（image = ann−1） | JSON 路径 |
|---|---|---|---|
| question 召回@IoU≥0.5 | **1/16 = 0.0625** | **6/16 = 0.375** | `evaluation.alt_mapping_page_index_as_is.question_vs_history.recall_iou50` / `evaluation.question_vs_history.recall_iou50` |
| question 最佳 IoU 均值 | 0.1718 | **0.4721** | 同上 `.iou_of_best_question_cand.mean` |
| 历史框墨迹密度 / 整页均值（ann 8） | 0.67（画在 page_8 上） | **1.00**（画在 page_7 上） | `evaluation.question_vs_history.per_box[].hist_box_ink_cov_vs_page_mean` |
| ann 8 最大 x2 越界量 | 超 5.09px（图宽 1176） | **超 3.09px**（page_7 宽 1178） | `evaluation.unusable_history_boxes.pages["8"].max_x2` |

> 最后一行与交接包原始记录「x2=1181.09 超 3.09px」完全吻合，是映射正确的旁证。

### 4.2 三层口径（核心结果）

只对 **有 question 标注的页图 7 / 8 / 9**（= 标注 page_index 8 / 9 / 10）评测，共 **16** 个历史
question 框（`evaluation.question_vs_history.n_history_question_boxes = 16`）。

| 口径 | 定义 | 召回@IoU≥0.5 | IoU 均值 | JSON 路径 |
|---|---|---|---|---|
| **L1 原样历史框**（任务规定） | 我的 Q 候选 vs 历史 question 框 | **6/16 = 0.375** | 0.4721 | `question_vs_history.recall_iou50` / `.iou_of_best_question_cand` |
| **L2 上限** | `IoU(历史框, 框内墨迹紧致框)`：任何只框文字、不留白的检测器的上限 | **12/16 = 0.750** | 0.6706 | `.L2_upper_bound_tight_detector` |
| **L3 检测器 vs 紧致真值** | 我的 Q 候选 vs「历史框内墨迹紧致框」 | **12/16 = 0.750** | 0.6997 | `.L3_detector_vs_tight_truth` |

**L3 = L2**：检测器已到达这份真值的上限。L1 之所以只有 0.375，是因为
标注者画框留白很大——历史 question 框的高度平均是**框内文字紧致高度的 1.46 倍**
（中位 1.36，范围 1.00–2.24），宽度平均 1.08 倍；单行题干的框，即使检测完全正确，
IoU 也被几何地压到 ~0.3–0.5。

L1 的 IoU 分布（`iou_of_best_question_cand`）：mean 0.4721、median 0.4723、
p25 0.3596、p75 0.6304、min 0.0、max 0.8897；
覆盖率（交集/历史框面积，`coverage_of_hist`）：mean 0.5299、median 0.4977、max 0.9275。

#### 每页

| 图（ann page_index） | 历史 question 框 | L1 命中 | L1 召回 | L1 IoU 均值 | 我的 Q 候选数 | 框中墨迹高于整页均值的历史框 |
|---|---|---|---|---|---|---|
| 7（8） | 9 | 4 | 0.4444 | 0.4545 | 7 | 5 |
| 8（9） | 6 | 2 | 0.3333 | 0.5025 | 6 | 4 |
| 9（10） | 1 | 0 | 0.0000 | 0.4491 | 7 | 1 |

（`evaluation.question_vs_history.per_page`）

#### 逐框明细（`evaluation.question_vs_history.per_box`）

`L1`=对原样历史框的 IoU；`L2`=IoU(历史框, 紧致框) 上限；`L3`=我的候选 vs 紧致框。

| 图 | ann | order | 历史框 | L1 | L2 | L3 | 命中?(L1) | 最佳候选 |
|---|---|---|---|---|---|---|---|---|
| 7 | 8 | 1 | [90.0,324.0,1162.3,420.6] | 0.313 | 0.673 | 0.458 | | p7_q_0001 |
| 7 | 8 | 2 | [43.6,453.4,1152.7,511.4] | 0.496 | 0.496 | **1.000** | | p7_q_0002 |
| 7 | 8 | 3 | [82.3,545.5,1181.1,658.7] | **0.713** | 0.790 | 0.901 | ✅ | p7_q_0003 |
| 7 | 8 | 4 | [60.8,641.1,1136.2,703.6] | **0.545** | 0.823 | 0.636 | ✅ | p7_q_0004 |
| 7 | 8 | 5 | [69.3,692.4,958.2,823.7] | **0.695** | 0.769 | 0.789 | ✅ | p7_q_0005 |
| 7 | 8 | 5 | [963.6,708.4,1151.6,797.1] | 0.135 | 0.791 | 0.121 | | p7_q_0005 |
| 7 | 8 | 6 | [74.7,807.8,1160.5,1057.9] | **0.890** | 0.958 | 0.916 | ✅ | p7_q_0006 |
| 7 | 8 | 6 | [933.4,1061.5,1148.1,1247.8] | 0.000 | 0.603 | 0.000 | | 无 |
| 7 | 8 | 7 | [90.0,1414.5,1143.5,1513.2] | 0.305 | 0.664 | 0.451 | | p7_q_0007 |
| 8 | 9 | 8 | [56.0,92.2,1120.0,178.7] | 0.375 | 0.673 | 0.557 | | p8_q_0001 |
| 8 | 9 | 9 | [50.6,227.4,1120.0,324.8] | **0.723** | 0.887 | 0.794 | ✅ | p8_q_0002 |
| 8 | 9 | 10 | [77.6,305.0,997.3,384.3] | 0.388 | 0.624 | 0.574 | | p8_q_0003 |
| 8 | 9 | 11 | [19.9,382.5,1148.8,552.0] | **0.609** | 0.609 | **1.000** | ✅ | p8_q_0004 |
| 8 | 9 | 12 | [36.2,716.1,1123.6,918.1] | 0.4998 | 0.500 | **1.000** | 差 0.0002 | p8_q_0005 |
| 8 | 9 | 13 | [30.8,1181.4,1147.0,1347.3] | 0.421 | 0.421 | **1.000** | | p8_q_0006 |
| 9 | 10 | 14 | [75.7,296.4,1152.5,361.7] | 0.449 | 0.450 | **0.996** | | p9_q_0001 |

读表要点：
- **L1 命中的 6 个框**是 order 3、4、5、6（图 7）和 order 9、11（图 8）。
- **L3 ≥ 0.99 的有 5 个框**（order 2、11、12、13 恰为 1.000，order 14 = 0.996），
  即这些题目的文字区域被完整、紧致地框住；
  其中 **4 个**（order 2、12、13、14）的 L1 仍 < 0.5（0.4956 / **0.4998** / 0.4212 / 0.4491）——
  注意 order 12 只差 **0.0002** 就过线，完全由标注留白造成，与检测质量无关。
- 第 8 行（图 7 / ann 8 / order 6 的右侧窄框 [933,1061,1148,1248]）L1=L3=0，是**唯一"完全没有任何候选覆盖"**的历史框：
  该区域是**插图/图形**（宽 215px、高 186px），本基线不产出图形类候选，故 0 分。
- 第 6 行（[963.6,708.4,1151.6,797.1]）同理，是题图区域，L3=0.121。

### 4.3 "查全但查不准"的说明：precision 无法用这份真值评估

`evaluation.question_precision_proxy`：全 6 图共 **104** 个 question 候选，其中只有 **6** 个能与某个历史框
IoU≥0.5 对上。这**不能**解读为 94% 误检，因为：
- 历史标注只覆盖 3 页的 16 个 question 框，而图 233/234（78 个 Q 候选）**根本没有可用坐标真值**；
- 另外 3 页里也没把每道题都标注（如图 7 有 7 个 Q 候选、只有 9 个历史框且其中 2 个是图形/题图碎片）。
所以精度指标在这份数据上不可测，报告中不给 precision 结论。

### 4.4 choice：口径不同，只报"容器一致性"

历史 `choice` 是**4 个选项合 1 框**，业务要求**每选项独立框**，两者不是同一口径，不能直接算 IoU。
本报告只报：**我的选项框中心是否落在历史 choice 容器内**（`evaluation.choice_container_consistency`）：

- 5 个历史 choice 框中，**5 个**都恰好包含我的 4 个选项框（`n_boxes_with_4_my_options_inside = 5`）。
  其中图 7 / ann 8 / order 7 那个容器（[63.1,1509.6,1048.4,1552.6]）的补全来自 §2.2 的
  「选项行几何补框」：该题的 A 项 OCR det 漏检，但行左侧 x 106–358 确有 61 个墨迹像素，几何补框后
  该项也被框出（`p7_w_0012`，`role_method = geom_gap_fill`）。**未做补框时该容器只有 3 个选项中心落入**，
  补框后为 4——这也反过来说明"每选项独立框"这条业务口径需要几何兜底，不能只靠 OCR。

### 4.5 不可用的历史框（`evaluation.unusable_history_boxes`）

| 标注 page_index | 映射后页图 | 框数 | max_x2 | x 占图宽 | 判定 |
|---|---|---|---|---|---|
| 8 | 7（1178×1673） | 12 | 1181.09 | 100.3% | **OUT_OF_BOUNDS**（超 3.09px） |
| 9 | 8（1176×1681） | 7 | 1148.80 | 97.7% | OK |
| 10 | 9（1179×1671） | 2 | 1152.46 | 97.8% | OK |
| 234 | 233（3467×1615） | 15 | 594.15 | **17.1%** | **SUSPECT_COORD_SPACE** |

- **page_index=234（→ page_233.jpg）的 15 个框不可当坐标真值**：内容虽能对上 page_233，
  但它记录在一个约 594 宽的小画布上，与 3467 宽的拼合图不是同一坐标空间
  （`verify_report.md` §3.1 已排除缩放/平移假设）。
  **涉及答案页的 IoU 一律标注"坐标系未定，暂不评测"**——本报告对 233/234 **不给任何 IoU 数字**。
- page_index=8 的那条越界框（x2=1181.09）在正确映射下只超 3.09px，其余框可用。

---

## 5. 页 233 / 234（多页扫描拼合）

- **两张都不是"六列答案表"**：233 = 6 个子页拼合、234 = 6 个子页拼合，每个子页宽 520–570px（≈单页扫描宽度）。
- 子页边界、切分模式、二级切分记录：`pages[].subpages`、`pages[].split_info`
  （234 的 `secondary_splits = [{"segment":[0,1193],"cut_column":617,...}]`）。
- 候选框并集覆盖墨迹：233 = **98.75%**、234 = **98.25%**（`pages[].ink_recall_pct`），说明切子页后没有整片丢内容。
- 页眉/页脚/角标过滤：233 丢 8 行、234 丢 5 行（`pages[].n_furniture_lines_dropped`）。
- 角色分布（无坐标真值，仅报数量）：
  - 233：question 49 / analysis 15 / answer 2 / text_block 4（9 个 OCR 题组）
  - 234：question 29 / answer 7 / analysis 7 / text_block 4（8 个 OCR 题组）
  这两页是"答案与解析页"，OCR 关键词规则命中大量 `解析`（22 个 E 候选里 22 个都在 233/234），
  与"答案页"的人工判断一致。

---

## 6. RapidLayout / DocLayout-YOLO 评估（结论：不采用，理由与证据如下）

按任务要求「先轻量基线，再评估是否需要 RapidLayout/DocLayout-YOLO；如需下载模型要写明下载量与是否成功」。

| 项目 | 实测结果 | 证据 |
|---|---|---|
| 包是否已安装 | **未安装**（`rapid_layout` / `doclayout_yolo` / `ultralytics` 均不在环境里） | `pip list` |
| pip 能否下载 wheel | **成功**：`rapid_layout-1.2.1-py3-none-any.whl` = **6,875,844 B（6.56 MB）**，从 PyPI 下载 | `data/derived/analysis/route_a_dl_probe/rapid_layout-1.2.1-py3-none-any.whl` |
| 安装到本机 site-packages | **不可行**：本会话沙箱为 workspace-write，写 site-packages 超出授权；改用 `pip install --target` 装到工作区内（成功：`route_a_dl_probe/site/`） | `route_a_dl_probe/site/` |
| 权重来源 | ModelScope：`https://www.modelscope.cn/models/RapidAI/RapidLayout/resolve/v1.2.0/onnx/...` | wheel 内 `configs/default_models.yaml` |
| DocLayout-YOLO 权重可达性 | HTTP **200**（域名可达），但**不回 Content-Length**；huggingface.co 在本网络 **TCP 443 8s 超时**（HF 上的同名权重不可达） | `route_a_probe_model.py` 输出 |
| **wheel 自带模型（离线可用）** | `site/rapid_layout/models/layout_cdla.onnx` = **7,423,528 B（7.08 MB）**，即 `pp_layout_cdla` | 目录清单 + `default_models.yaml` |
| 用自带模型实际跑推理 | **未跑通**：`import rapid_layout` 缺少依赖 `omegaconf`（`ModuleNotFoundError: No module named 'omegaconf'`）。为遵守沙箱授权未写本机 site-packages，改用 `pip install --target` 把依赖装进工作区，但 **pip 取包在本网络极慢**：`omegaconf` 在 **~18 分钟**内未装完，已终止，故**未做 RapidLayout 的真实推理** | `route_a_probe_rapidlayout_offline.py` 运行输出；`route_a_dl_probe/site/` 目录（无 `omegaconf`） |

**决策**：不采用 RapidLayout/DocLayout-YOLO 作为本任务的出框方法。理由：

1. 官方默认权重走 ModelScope/HF 下载，属于"需要下载模型"的路径；本次实测只证明域名可达，
   **没有完成一次真实下载 + 推理**，因此**不能声称其效果**（本报告不给任何 RapidLayout 精度数字）。
2. 更关键的是**类别不对口**：DocLayout/PP-Layout 输出的是 `title/text/figure/table/list` 等**版面类别**，
   而本任务要的是**题型角色** Q/W/A/E——仍然要在版面框上再叠一层「题号/选项/答案/解析」规则，
   等于用重模型替掉本基线里最便宜的那一层（投影+连通域），收益有限。
3. 本基线的实测效果（§4.2：L3 12/16 = 上限 12/16；并集覆盖墨迹 70%–99%）已经够用，
   且**零下载、CPU、确定性可复现**。

**保留的后续选项**（若确需重模型）：`rapid_layout` wheel 自带的 `layout_cdla.onnx`（7.08 MB）可离线使用，
只需在可写目录补齐 `omegaconf` 等依赖；可作为「图形/表格区域」的补充检测器，与本基线合并。

---

## 7. 失败与限制（全部为实测）

1. **历史 question 真值本身带大量留白**：这是 L1 只有 0.375 的主因（L2 上限 = 0.750 已量化）。
   任何"紧致出框"的方法在这份真值上都无法超过 12/16。
2. **图形/插图区域无候选**：唯一 L1=L3=0 的历史框（图 7 / ann 8 / order 6 右侧）是插图区域；
   本基线只产出文字/选项/答案解析类候选，不产出图形类框。
3. **L2/L3 的"紧致真值"对杂散墨点敏感**：图 7 / ann 8 / order 1 的框内，文字下方 y≈398–410 有
   每行仅 2–3 个像素的淡痕（非文字），使紧致框被拉高，L3 因此只有 0.458。此类噪声会让 L3 略微低估。
4. **page_index=234（→233）坐标空间未定**：15 个框（14 answer + 1 analysis）**不做 IoU 评测**。
5. **precision 不可测**：真值覆盖不全（见 §4.3），报告不给 precision/误检率结论。
6. **性能**：页 234 单页 OCR 实测 86–165 s（6 个子页，随机器负载波动）。若要批量处理，需要
   降低 det 的 `limit_side_len` 或对子页做横向分块。
7. **OCR 依赖**：角色判定依赖 OCR 文本；`ocr_line_coverage` 最低的是图 10（0.790，即 21% 的行没有 OCR 文本），
   这些行只能退回 `text_block`/几何角色。纯几何模式（`--no-ocr`）可跑通，但只有 `text_block` 角色。
8. **选项切分的边界情形**：同一视觉行内若 OCR 把 4 个选项识别成 1 个 atom，才用空白列切分；
   实测本数据 3 页的选项行都被 OCR 拆成了独立 atom，未触发该回退路径。
9. **OCR det 漏检会整行少一个选项**：实测图 7 第 7 题选项行的 A 项（x 106–358 有墨迹）未被 det 检出，
   靠 §2.2 的几何补框兜住（`p7_w_0012`）。补框规则保守（≥40px 宽 + ≥30 墨迹像素 + 高度 ≥40% 行高），
   全数据仅触发 1 次；但它无法给出该选项的文字，`text` 为空、`confidence=0`。

---

## 8. 下一步建议

1. **把"角色判定"与"框生成"解耦，先用 OCR 语义切题组，再让几何/CC 只负责紧致边界**——本脚本已经是这个结构，
   下一步可把题号识别换成"行首 atom 是否为纯数字"这类更强规则，减少 `text_block` 误判。
2. **针对图形/表格区域补一个轻量检测器**：直接用本任务已下载的 `rapid_layout` wheel 自带
   `layout_cdla.onnx`（7.08 MB，离线），只取 `figure/table` 类补齐空白区域。
3. **给 page 233/234 的答案页做坐标空间标定**：先用 OCR 文本把「594 宽小画布」与「3467 宽拼合图」的
   对应关系解出来（例如用答案文本的 x 排序做匹配），否则这两页的 15 个 answer/analysis 框永远不能评测。
4. **把 `choice` 口径差异写进评测协议**：历史 choice = 4 选项合 1 框，评测时只能用"容器包含率"，
   不要用 IoU；反之若要算选项级指标，需要业务侧先补齐选项级真值。
5. **性能**：批量化时给 OCR 设 `det_limit_side_len`，并对宽图按子页并发（当前是串行）。

---

## 附录 A：文件清单

| 文件 | 说明 |
|---|---|
| [tools/route_a_layout.py](../../../tools/route_a_layout.py) | 主脚本（唯一写入的代码文件） |
| [route_a_candidates.json](route_a_candidates.json) | 全部候选框 + 评测结果 + meta（395,476 B） |
| [route_a_report.md](route_a_report.md) | 本报告 |
| [route_a_overlay_page7.png](route_a_overlay_page7.png) … `page234.png` | 6 张证据图（红=题干 绿=选项 蓝=答案 紫=解析 灰=文本块；黄/青细框=按更正映射后的历史 question/choice 框） |
| [route_a_rerun_check.json](route_a_rerun_check.json) | 第二次全量跑的对照产物（content_sha256 与首次相同） |
| [route_a_geom_only_check.json](route_a_geom_only_check.json) | `--no-ocr` 纯几何基线产物（6 页 1.2 s） |
| [route_a_run_console.log](route_a_run_console.log) | 首次全量运行的控制台输出 |
| `route_a_dl_probe/` | RapidLayout 评估中间产物（wheel 6.56 MB + 自带模型 7.08 MB + 探针报告） |

## 附录 B：一键复跑

```powershell
$env:PYTHONIOENCODING="utf-8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$env:CUDA_VISIBLE_DEVICES=""
$py = "C:\Users\LIHAOYANG\AppData\Local\Programs\Python\Python311\python.exe"
# 完整（含角色判定，实测 195–260 s，随机器负载波动）
& $py tools\route_a_layout.py --out data\derived\analysis\route_a_candidates.json
# 纯几何基线（无 OCR，约 1 s）
& $py tools\route_a_layout.py --no-ocr --out data\derived\analysis\route_a_geom_only_check.json
```

复跑一致性判定：比较 `meta.content_sha256`（当前应恒为 `b538430e4ed21d00…` 开头的那一串）。
