# B 本轮验证记录

最新增量为复杂答案/解析多行组装：59 项回归通过，原图字节校验与真实 OCR 重放生成 34 个题目、56 个答案候选和 27 个唯一配答候选；9 个独立来源案例逐行、逐字符区间核对，仍为 HOLD。详见 `docs/b-multiline-46007447.md`、`evaluation/book-46007447-multiline.json`。以下记录保留先前阶段的历史结果。

本页下方保留 PR #1 的 M0 历史验证。本轮 46007447 增量：29 项回归通过，34 个题目候选、26 个唯一配答候选，4 页主编号开发清点相符，整批 HOLD。具体命令、限制及定稿需求对照见 `docs/b-offline-46007447.md`、`docs/requirements-confirmed.md` 和 `evaluation/book-46007447-offline.json`。没有平台写入。

日期：2026-10-16（Asia/Shanghai）。基线：架构提交 `79b7195`。接收方验证：待 A 记录。

- `python -m unittest discover -s tests -v`：10 项通过，0 失败。覆盖摘要/尺寸不匹配、路径逃逸、重复身份、临时合同隔离、宽图回投、空页、输入变化及新书映射拒用。
- `python tools/verify_data.py --out data/runs/m0-audit`：4 页、36 条历史框；1 条越界保留为问题，页 234 的局部坐标不再误判为缩放。
- 四张真实原图纯几何识别：34 个候选，子页数 1/1/1/6；不读取历史框或题答关联。
- 单张真实原图 CPU OCR：21 个候选、41 条 OCR 行；不是组题配答或公式质量验收。
- 将输入包复制到另一临时目录重跑：payload SHA-256 一致，未依赖个人绝对路径。
- 已目视检查宽图叠框预览。纯几何仍存在大段合框，属于待改进基线，不是逐题框选完成。

完整依赖及产物摘要见 `evaluation/b-baseline-20261016.json`。复现命令见 `docs/b-recognition.md`。
本次实测使用 NumPy 2.3.5、Pillow 12.2.0、OpenCV 4.10.0、RapidOCR 1.4.4、ONNX Runtime 1.25.1。跨环境数值差异须另行记录。

始终 `quality_decision=NOT_EVALUATED`；没有业务准确率、跨书效果、付费模型或真实平台写入验收。

本分支未启用自动 CI（现有凭据无 workflow 权限）。交付本地可复现检查，不扩展账号权限。发布状态以 PR 记录为准。
