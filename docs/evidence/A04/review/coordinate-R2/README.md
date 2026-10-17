# A04 coordinate-R2 独立离线复验

target `76898657e76ac2db071327e90c6ca5031d17571f`；review workflow `e7ff892776f53636fcddfe136d1659204c4ff738`。**R2 REWORK；整体A04 BLOCKED**。浏览器、授权profile、登录、网络、模型和书籍动作0。

[报告](../../../../tasks/A04-coordinate-R2-review-report.md) · [结论与条款矩阵](review-verdict.json) · [收口](closure-checks.json) · [清单](sha256-manifest.json) · [自有释放](self-release.json)

## 新的必修反例

37×29 RGB PNG只有1行解压像素。CRC/zlib有效，Pillow verify/load接受，但独立行数检查为112/3248字节，OpenCV完整解码拒绝。**未经人为改包，公开A04入口仍发布最终bundle，公共loader接受。**

- [最小结果](minimal-repro/result.json)、[原始控制台](minimal-repro-console.txt)、[输入](minimal-repro/input/capture.json)、[最终包](minimal-repro/output/bundle.json)
- [两种解码器及行数核对](pixel-diagnostics-cases/short-row-observation.json)、[直接公开命令](pixel-diagnostics-cases/short-row-public-command.json)、[原始stderr](pixel-diagnostics/pixel-diagnostics-stderr.txt)
- [可指定新目录的最小脚本](scripts/repro_incomplete_rows.py)：退出1表示缺陷仍在；产品CLI错误退出0。复现命令见报告，不在既有证据目录重跑覆盖。

原24字节PNG、截断JPEG/PGM、CRC和非法滤波字节拒绝已通过；正常PNG/渐进JPEG/P2/P5搬运消费通过；状态语义修正通过。完整原图拒绝条款仍未满足。

## 固定输入、运行和失败

| 文件或目录 | 含义 |
|---|---|
| [snapshot-check.json](snapshot-check.json) | 158项交付清单原Git/磁盘、148旧执行项、公共范围和旧准备/R1保全 |
| `inputs/frozen-inputs.tar.gz` | 362个确切交付文件；包含源代码、测试、夹具、合同examples及作者R2报告/证据 |
| [原字节清单](inputs/frozen-tree-manifest.json) | 固定输入路径、大小、SHA256 |
| `inputs/historical-test-supplement.tar.gz` | 同一固定提交6个历史A05测试所需文件；不是当前平台观察 |
| [历史补充清单](inputs/history-supplement-manifest.json) | 历史离线回归输入绑定 |
| `inputs/workflow/` | 本轮workflow文档和主调度预检原Git字节 |
| `regression/` | 初轮A04/合同原始stdout/stderr；审计脚本错误未擦除 |
| `guard-correction/`、`guard-correction-remaining/` | 仅受审计错误影响的方法补跑；6方法通过、junction方法按范围跳过 |
| [独立15项](independent-cases/results.json) | 11 PASS / 4 FAIL原始结果；输入、公开CLI stdout/stderr、便携包、发布前检查及人工重封包分别保留 |
| [定向4项](pixel-diagnostics-cases/results.json) | 3 PASS / 1 FAIL：确认缺行PNG仍发布，另证实独立非法滤波像素及发布前复查拒绝 |
| `guard-records/` | 每个测试Python进程的本地审计退出记录；无实际网络/profile读取 |
| `harness-notes/` | namespace快照假设和Windows审计兼容问题；原脚本保留 |
| [environment.json](environment.json) | 现有环境，无安装或依赖变更 |

首轮失败逐项解释保存在 [review-verdict.json](review-verdict.json)。尤其：N02错误预期Pillow会拒绝，因此首轮尚未触及CLI；随后通过精确像素行数与另一解码器独立核实。U01虽未返回期待的解码错误，但摘要层实际拒绝了换图。U03是真实公开发布的同一缺行漏洞。L01人为重封包始终标为`SYNTHETIC_TEST_FORGERY`，不冒充A04合法来源。

## 任务条款结论

| 交接条款 | 结论 | 限定 |
|---|---|---|
| 1 完整图像拒绝 | REWORK | 原24字节修复；新缺行PNG通过公开入口 |
| 2 正常格式和搬运 | PASS | 自建PNG/JPEG/P2/P5，公共loader、完整解码、尺寸/摘要/MIME/相对路径 |
| 3 发布前复查与容忍 | REWORK | 摘要/非法滤波像素复查通过；缺行PNG仍可进入最终包 |
| 4 状态语义 | PASS | 依赖ACCEPTED但坐标NOT_PERFORMED，验收NOT_ASSERTED |
| 5 差异与回归 | PASS（两项排除） | A04 151通过1跳过；合同69通过1跳过；原R1矩阵按旧版本保留 |
| 6 保全与释放 | PASS | 清单、旧失败、原始输出及自己的PID退出；不是整体A04通过 |

两项跳过为未改动的Node截止时间测试和需要cmd junction的路径测试，保持本轮“离线Python”边界。初轮审计参数处理错误不归因产品，修正后仅补跑受影响项，没有修改产品来让测试通过。

`scripts/offline_guard.py`作为额外临时`sitecustomize.py`放在自己的stage，阻断真实网络、非Python子进程和授权私有路径；任何冻结产品文件均未替换。首次审计错误发生在Windows创建子进程之前，未执行被排除的Node或cmd。

全部真实R01～R06仍BLOCKED；A01依赖已接受，D01由主调度另行接受，不将本轮未重测安装解释成D01退回。S01、B确认、真实坐标、保存/OCR/恢复和内容质量仍按各自证据边界处理。本轮未提交、集成、推送、回写state或发送其他对话消息。
