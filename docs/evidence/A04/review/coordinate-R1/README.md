# A04 coordinate-R1 独立复验包

2026-10-17。target `a86eca6ec87ced20dc3a8bcc8f2c87d329e87c39`，review workflow `2ef3bfda20476dff3bdd23912d5bf2d1e3eb5ce1`。结论 **REWORK；真实必需项BLOCKED**，不接受整个A04或释放下游。

[完整报告](../../../../tasks/A04-coordinate-R1-review-report.md) · [28项矩阵](scenario-matrix.json) · [版本/范围](snapshot-check.json) · [最终检查](closure-checks.json) · [摘要](sha256-manifest.json)

| 原场景 | 本轮结论 | 证据 |
|---|---|---|
| P01 | PASS | 固定Git字节、依赖/public tree与范围：[snapshot-check.json](snapshot-check.json) |
| O01 | PASS | 正常公开入口、source/snapshot：[公开入口](reproduction/public-entry.json)、[独立检查](independent/results.json) |
| O02 | PASS | 完整包在含空格目录搬运、另一cwd消费：[loader日志](reproduction/public-moved-consumer.log)、[独立检查](independent/results.json) |
| O03 | PASS | 独立Pillow读取实际像素尺寸、重算原图摘要：[独立检查](independent/results.json) |
| F01 | PASS | 错书、缺目标身份；独立cases/F01输入 |
| F02 | PASS | 正文或答案页缺失；独立cases/F02输入 |
| F03 | PASS | 缺data、截断JSON经公开CLI拒绝 |
| F04 | PASS | 框引用缺目录/题/父框拒绝 |
| F05 | PASS | 原图声明摘要或尺寸错误拒绝 |
| F06 | REWORK | HTML/404拒绝；截断PNG被接受：[最小复现](minimal-repro/result.json)、[输入与公开输出](minimal-repro/output/bundle.json) |
| F07 | PASS | 过期、显式不完整、总页数冲突拒绝 |
| F08 | PASS（离线） | 401/403、HTTP200含登录失效码，合成登录确认失败后关闭 |
| F09 | PASS（离线） | TIMEOUT结果及合成导航超时拒绝、释放 |
| F10 | PASS（离线） | 真实临时文件lease冲突，首owner未被改动，释放后重获；进程计数注入 |
| F11 | PASS（离线） | 合成launch/navigation/auth/close故障；真实临时lease释放、再获取 |
| F12 | PASS（本地替身） | 7种方法mock route及临时真浏览器4种方法均发送前阻断 |
| F13 | PASS（本地替身） | 必要登录策略例外仅一次；近似路径/跨域拒绝；无平台登录 |
| F14 | PASS（本地替身） | 公开只读入口无写动作；底层修改请求由产品route拦截，本地服务器接收0 |
| F15 | PASS（合成脱敏） | 错误中的合成敏感标记不进入脱敏审计；未读真实凭据 |
| F16 | PASS | 外部映射不一致或重复页拒绝；不假设固定全局页偏移 |
| F17 | PASS | 3页实采与214页合成元数据分开，能力全UNKNOWN |
| R01 | BLOCKED | 本轮不获取真实会话或复核登录/目标；历史作者证据不算本次观察 |
| R02 | BLOCKED | 当前14/15/173原图未取得 |
| R03 | BLOCKED | 当前正文14→15→14未独立验证 |
| R04 | BLOCKED | 当前目录/题/框未独立取得 |
| R05 | BLOCKED；离线PASS | [独立13项数值/绑定检查](independent/results.json)、[12点本地像素检查](independent-renderer/result.json)不能替代真实坐标 |
| R06 | 真实BLOCKED；本地释放PASS | [释放记录](reviewer-release.json)；没有获取授权profile |
| D01（场景收口） | PASS | [收口检查](closure-checks.json)与[清单](sha256-manifest.json)；项目D01清洁安装未测试 |

F01–F17精确输入、预期/实际、错误码、定位和失败traceback集中在 [独立结果](independent/results.json) 与 `independent/cases/`。49子检查为47通过、2失败，两条失败定位同一损坏原图缺陷。

## 输入与复现索引

| 文件/目录 | 内容 |
|---|---|
| `inputs/frozen-inputs.tar.gz` | 来自确切提交的458个源文件、测试、夹具及A04/A05历史证据；解压至自己的stage，绝不替换作者工作树 |
| `inputs/contracts-examples-supplement.tar.gz` | 同一提交3个合同examples文件；首次漏导出的验收输入修正 |
| `inputs/frozen-tree-manifest.json` | 解压原始字节、摘要、尺寸清单 |
| `inputs/workflow/` | 本轮workflow确切Git字节，仅文档 |
| `reproduction/` | 作者141+8+70+8回归、初次合同失败、补输入后70通过、公开CLI/跨cwd loader和作者renderer命令/原始日志 |
| `author-renderer-replay/` | 冻结作者本地DPR2 renderer的独立重跑输出，6点通过 |
| `independent/` | 49个自建子检查、实际输入/产物、数值oracle、搬运包 |
| `minimal-repro/` | 24字节损坏PNG通过公开入口及loader的完整最小输入输出 |
| `independent-renderer/` | 自选原图裁片、独立OpenCV全图NCC、临时Edge DPR2.75、12点/12错误映射、本地服务器请求计数和自有PID释放 |
| `harness-failures/` | psutil缺失的验收脚本初稿和失败日志；发生在浏览器启动前 |
| `historical-live-evidence-review.json` | 冻结作者5次真实读取/诊断超时、释放的带摘要回执；本轮未重试 |
| `reviewer-release.json` | 本轮只关闭自有资源，无授权profile/凭据访问 |

实际运行脚本为 `scripts/snapshot_inputs.py`、`reproduce.py`、`supplement_contracts.py`、`run_author_renderer.py`、`independent_checks.py`、`independent_renderer.py`、`public_entry_and_matrix.py`。这些脚本保留有界实际路径；生成型脚本要求输出目录不存在或只用于首次归档，不在已有证据目录反复运行覆盖失败。`repro_truncated_original.py` 接受 `--root` 和新 `--output`，用于安全重复最小离线复现，命令见报告。

首次独立子检查的PowerShell封装尾随日志读取，没有保留Python退出码；不能用该工具外层exit0推定通过。逐例结果明确两条FAIL。后续最小复现显式传播退出码1并单独保存；作者公开CLI的错误退出码0、成功产物和公共loader接受证据齐备。

本包不包含授权凭据/profile/原始视频。合成marker、假URL类别及源码中的字段名不是实际账号数据。本轮只使用本机已有环境，没有进行安装验收。全部修改只在指定新报告/证据和自己的`.local/stages/A04-review/coordinate-R1/`，不改state或产品，不提交/合并/推送。
