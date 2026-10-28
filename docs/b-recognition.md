# B 最小识别入口（试验版 0.1）

本页保留 M0 的 0.1 基线说明。46007447 的离线组题/配答/质量检查增量见 [本轮说明](b-offline-46007447.md)，定稿需求对照见 [需求与实现边界](requirements-confirmed.md)。下文的“无组题配答”仅描述旧入口 `tools/recognize.py`，不代表新入口 `tools/offline_b.py`。

这是 B 的离线识别适配器，不是正式 EvidenceBundle 公共合同实现。
复用 `tools/route_a_layout.py` 的分片、行投影、连通域和可选 CPU OCR；不读取历史框、导出题答或浏览器。

## 安装与复现

Python 3.11+；`python -m pip install -r requirements-b.txt`。已有 opencv-python 环境可直接复用，不必重复安装 headless 分发。
如需 OCR：`python -m pip install rapidocr-onnxruntime==1.4.4 "onnxruntime>=1.18,<2"`。
OCR 模型由该包提供；该入口不调用付费模型或远端标注接口。

在仓库根目录执行（输出目录必须不存在）：

```sh
python -m unittest discover -s tests -v
python tools/verify_data.py --out data/runs/m0-audit
python tools/make_b_source.py --images data/raw/images/46006966_page_7.jpg data/raw/images/46006966_page_8.jpg data/raw/images/46006966_page_9.jpg data/raw/images/46006966_page_233.jpg --book-id 46006966 --scope-id research-four-assets --out data/runs/research-source
python tools/recognize.py --source data/runs/research-source/source.json --out data/runs/geometric-four-assets
```

可选 OCR 小样：

```sh
python tools/make_b_source.py --images data/raw/images/46006966_page_7.jpg --book-id 46006966 --scope-id ocr-smoke-one-asset --out data/runs/ocr-source
python tools/recognize.py --source data/runs/ocr-source/source.json --out data/runs/ocr-one-asset --ocr
```

## 临时输入与输出

输入 schema：`b-source-trial/0.1`。必需 `artifact_id/book_id/scope_id/assets`；每张图带独立 `asset_id`、相对路径、SHA-256、尺寸、唯一阅读顺序。
路径相对 source.json 所在目录，不得逃出来源包；支持复制到另一台机器。缺图、摘要或尺寸不符直接失败，不默默跳页。
`make_b_source.py` 按命令中图片顺序建立清单；原始文件名只作外部参考，不据文件名自动推断页映射或章节。

输出 schema：`b-evidence-trial/0.1`。`evidence.json` 包含来源引用、实现和配置摘要、各图候选、OCR 行、原图框、裁片逆变换及未经独立验证的覆盖线索。
`previews.json` 关联每张图的预览文件及摘要；`overlay-*.png` 仅画本次候选，不混入历史框。
`content_hash` 是 payload 的排序、紧凑 UTF-8 JSON 的 SHA-256；`created_at` 不参与该摘要。

区域身份按确切输入、代码、配置及区域顺序生成；同环境同输入可复现。改变输入/模型/代码后不保证实体续接，尚未实现人工 patch 迁移。
框为原图像素 `[x1,y1,x2,y2]` 半开区间；裁片矩阵从局部坐标回投原图。预览绘制边线不用于像素级评测。

## 范围和限制

- 默认纯几何，只提供 text block 候选，role_candidate 为空；`--ocr` 才给出启发式语义角色。
- text_hint 可能是旧后端截断的 200 字提示；完整 OCR 行另存，但两者均非经核准转写，不能据此声称公式保真。
- 不输出平台 Q/W/A/E、CSS 坐标或可执行平台动作。
- 始终 `quality_decision=NOT_EVALUATED`；覆盖线索与识别共享投影算法，不能作为独立漏题检查或自动放行。
- 没有组题配答、QuestionGraph、CheckReport(PASS)、跨书准确率或实际平台验收。
- 在 A 的可执行合同确定后新增显式适配与兼容回归，保留临时格式版本，不直接宣称冻结。
