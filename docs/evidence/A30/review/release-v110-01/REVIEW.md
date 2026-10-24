# A30 v1.1.0 本机候选包独立审查

结论：`ACCEPTED_OFFLINE_CURRENT_MACHINE_V110_PACKAGE_BYTES_AND_HANDOFF_ONLY`。

本次接受冻结包与 accepted13 源码的一致性、发布目录与 ZIP 的字节对应、普通客户启动接线和交付说明，以及明确列出的书籍缓存收录边界。没有发现本范围的产品阻塞项。结论仅适用于本机候选包，`CUSTOMER_READY=false`；不构成客户启用、实际启动、公式内容正确、剩余生产或完整章节交付的接受。

## 固定输入与原始身份

- 独立副本：`D:/1800-private/a30-release-v110-independent-20261024-01/input`，279 个固定输入，结尾复核 279/279 未变。
- 送审支持清单：`f3b35564ec4a6ac1135a9201e4e5618c305e9aea395651fa351e663ed80edecf`，22 项及清单自身。
- fixed-result：`9495d569c1e410a110f90a6c5f2271389c2b6ed51b4d7243727ed9ca9f9ffc92`。
- accepted13 源码清单：`c23545415522828c1328f86ec63ff123ae25411f3398d40a1b8d4d6f5258bec5`。与既有独立冻结副本的清单相同，包内 242 个源码成员全部匹配其原始字节哈希，无额外 app 文件。
- release-manifest：`0f229bb50223a523787edc94966d4b5e46a4fc36585f4ee0403257f431456409`，253 项及清单自身共 254 文件。
- ZIP：`D:/1800/.local/releases/A30-v1.1.0-customer-local-win64.zip`，2,699,057 字节；SHA-256 `2d6767a9c450ce9ab7343d86d0a3b7a5ef1a2a524b08c7b90c4d2e1bd92212c6`。
- ZIP 254 项逐项与发布副本字节一致，唯一外层目录 `A30-v1.1.0-customer-local-win64/`；大小写去重、排序和路径边界检查通过，没有绝对路径、穿越、反斜线或符号链接条目。

## 新增离线检查

独立 `verify_package_static.py` 六组静态检查 PASS。只读取冻结副本和 Python 标准库，没有导入产品或打包器，也没有重跑旧测试、打包、实际启动、GUI、OCR、模型、浏览器或平台。

1. 打包器唯一逻辑差异为 `runtime/customer-formula-history/46007447/` 下五个精确文件：`actual-partial-ocr-manifest.json`、`continuation-evidence.json`、`fixed-result-r1-summary.json`、`model-input-manifest.json`、`registry.json`。未增加通配权限。另有整文件 CRLF→LF：原件 206 个 CRLF，新件 0；仅在差异比较时统一行尾，原始字节身份分别保留。去除五个新增字面量后，归一化文本完全一致。路径、私有目录、文件身份和排他新建规则未改变。
2. 9 项打包支持输入原始哈希匹配。原始阶段清单的 251 个文件保持原字节，finalizer 仅新增 `CANDIDATE-STATUS.json` 与 `BOOK-DATA-CACHE-BOUNDARY.json` 并重写该新包自有清单。两段固定执行记录 exit 0。`package-record.json` 的 `zip=NOT_CREATED` 是保留的打包前阶段记录，后续 build-result 与 ZIP 字节验证另行成立，未涂改历史记录。
3. 根 `START_CUSTOMER.cmd` 和 `START_HERE.txt` 可由固定模板、版本、源码身份和三项交付值逐字节还原，没有未填写占位符。`FINAL_RUNTIME_WIRING`、`FINAL_EXPORT_LOCATION`、`FINAL_NEW_PARAMETERS` 已完整写入说明。两个依赖锁及 CLI 参考文件逐字节匹配。
4. 11 个书籍缓存恰好等于 accepted13 声明范围；8 个本地 registry 引用及哈希闭合。公式历史中 7 个已用区域保持 consumed 且不是 TeX 缓存。历史绝对路径仅作来源记录，本轮没有打开它们。嵌套 ZIP 恰好 5 个 JSON 和 1 个 JPG，未加入程序或私有状态文件。
5. 有限凭据检查覆盖 10 个外层 JSON、5 个嵌套 JSON、6,225 个字符串、18,443 个结构节点，以及认证头/查询模式；0 个明确命中，敏感值未写入报告。尝试解析 JSON 字符串的分支本次命中 0。JPG 只核对类型，没有 OCR 或隐藏数据扫描。因此这不是全面秘密扫描或无私密数据保证；该包明确包含已授权的书籍数据，不能称作通用无数据发行包。
6. 候选状态保留 `CUSTOMER_READY=false`、题 1/5/10/11 已接受、剩余 12 题待生产、完整 16 题导出 `NOT_COMPLETE`、公式执行候选未被此包批准或应用。6/6/4 质量分组仍是协调方提供的记录，本审查没有将其提升为独立内容接受。

## 普通入口、恢复与输出边界

`START_CUSTOMER.cmd` 明确传入保留的原工作区和 `--customer-deployment`。缺少解释器、入口、原 `state.sqlite` 或 `settings.json` 时停止，没有新建替代工作区的回退。启动返回码原样保留，失败提示保留任务和日志。

静态追踪 `app/tools/customer.py`：`main` 将该标志绑定到 store，无子命令时进入普通向导；带开发子命令与该标志的组合被拒绝。`settings` 在内存中移除开发窗口字段并合并随包运行时，不改原 settings；`packaged_runtime` 校验双解释器身份，不下载或初始化模型。普通界面操作使用该 settings provider。客户无需代理生成候选 JSON 或开发者 authority 文件来完成普通输入流程。此路径继承 accepted13 的既有范围，本次未重跑其测试或认定任何新的实际操作权限。

START_HERE 明确要求回到原任务：已成功项复用，未知保存只读对账，保留账本；输出说明指向原 workspace 的 `native-deliveries/<job>/` 和 `exports/`，找不到输出时不重发保存。已有九题保护继续保留。

本包依赖原机的两套 venv、两套基础 Python、四个模型、已安装 Edge、原工作区、原 profile 和账本。这些对象没有被打包或重新校验；本轮也未读取其私有内容。`formula_inference_activated=true` 是显式客户动作使用的内存接线，不代表打包或本审查执行过推理。此包状态文件声明尚未启用交付，并不是额外的程序运行锁。

## 保留的失败与尚未成立的状态

两次 reviewer 读取辅助错误单独保留在 `read-helper-failures.json`：对含点版本目录使用 `with_suffix` 得到错误 ZIP 路径；初次 ZIP 名称比较遗漏合法外层目录。原 `intake.py` 保留，随后仅修正读取路径与比较规则，没有改包、重打包或执行产品。它们不被伪装成产品失败或删除的 PASS 历史。

实际 packaged START 启动、GUI 观察、外部运行时当前可用性、客户全程耗时/人工次数、剩余 12 题真实保存及独立读回、完整 16 题导出和最终启用 sidecar 仍未由本包审查证明。实际运行留在唯一作者的另行绑定范围；本结论不授予新运行或旧输入重放。首个失败 ROI、旧 1147 已耗尽轮次、历史 FAIL/UNKNOWN、旧九题及四题成功记录均不被重置。`1800-a PAUSED` 不变。

独立详细结果、有限扫描、输入清单和决定见同名 private 审查目录；它们由最终 review-manifest 绑定。公开报告不包含私有响应正文或凭据。
