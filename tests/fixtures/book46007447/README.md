# 46007447 开发回归材料

来源为用户授权只读取得的 5 张原图。完整来源包由用户侧交接；原图摘要、尺寸、真实 viewer/resource 映射在 source-descriptor.json。本目录不含账号、Cookie、浏览器状态、网络授权头或历史框。

context.json：从原图标题目视整理的章节/课时窗口，不含题目编号或配答标签。review.json：独立于输出图谱的主编号清点和 Q4 的开发参考值。作者为 Codex 视觉检查，不是人工验收；不是留出集。

ocr-evidence.json：真实 RapidOCR 全页与答案行放大 OCR 快照，保留模型依赖、源码摘要、原图引用和回投证据。快照会故意保留错误，如 Q7 的 C/0 分歧，供检查器捕获。快照测试只重放组题/配答/检查，不等于重新运行 OCR。

q4-answer.jpg / q4-stem.jpg / q4-figure.jpg：实际原图的裁片；来源框、父资产摘要、重编码说明和裁片摘要在 crop-provenance.json。q4-export-record.json 是原始历史导出的单条参考，答案 1:3 未被修改，不用于组题配答。

详见 docs/b-offline-46007447.md。若来源、上下文窗口或 OCR 后端发生变化，重新生成证据并独立核对清点，不能把旧快照当新评测成绩。
