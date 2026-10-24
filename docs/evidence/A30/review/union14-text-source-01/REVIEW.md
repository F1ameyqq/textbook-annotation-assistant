# A30 Union14 未保存文字来源框收窄有限独立审查

结论：`ACCEPTED_OFFLINE_UNION14_UNSAVED_TEXT_SOURCE_TIGHTENING_ONLY`。

仅接受相对 accepted13 的普通UI文字框收窄能力和其离线保护。本结论不接受实际Q7新内容、全16新计划、launch、平台保存、模型运行或最终交付。原 full16-ui-01 REWORK 及作者 launch01 预检失败保持原状，`CUSTOMER_READY=false`，`1800-a PAUSED`。

## 固定身份与差异

- 输入 `D:/1800-private/a30-integrated-flow-r1-fixed-20261024-14`，独立副本 `D:/1800-private/a30-union14-independent-20261024-01/input`。
- manifest `24dd617bcc55a24a140881a4cbad29ddfdef70e5293599b20a4935a5ee71b06c`；report `598c0d954a2ffc6c28fa13b6c75f93317eff10dc79495d396ea964816d7fe647`。
- 244源码、109证据及3顶层文件，共356个输入，原始哈希全符，结尾356/356未变。父级保留证据另逐字节核对。
- 两个产品差异：`review.py` SHA `e8cc99efd2b959b0a3158fd364a7585200e8c9ddf1d453ff7cb43cd2bbbbced1`；`review_ui.js` SHA `6220376703b6da60f5bc7ba4af89bc810b9fcb3c4b8965738233dd33b5ec010e`。
- 新增两份作者检查文件；其余240个父级源码不变，无删除。native_plan、production、transport、模型/OCR代码与accepted13一致。原生产重叠保护没有放宽。

## 接受的实现语义

普通 `bind-region` 接口按 `replace_text_region_id` 分派，服务端在原书锁内重新载入并校验expected_head。候选须无acceptance且platform_status为NOT_RUN；必须显式核对来源与文字完整，不能混入题图替换、proposal或来源移交。

新框只能是原页、原分区的整数有效矩形，须严格区别于当前框且包含于当前框内；来源哈希和尺寸须匹配。其他候选的同页同区框有正面积相交即拒绝。只有原text框可进入此路径，图片仍走原接口。

修改仅收窄bbox并保留previous_source_frame历史、原始片段身份、正文及识别引用。确认记录清空，content_status转NEEDS_REVIEW，新增审校事件并要求重新确认；未经重新确认，生产计划仍被拒绝。第2次收窄以当前框为边界，不能回扩到第1次之前的原框。

UI从普通state.figures暴露未保存文字框入口；锁定页与分区、要求新的拖框及完整性勾选。新请求携带原head、候选、来源、region_id与text_complete_checked，不混带图替换或移交字段；陈旧head不发请求，已保存项不显示该入口。

## 新独立验证

未重跑任何旧suite或作者新测试。作者固定的一项Python与一项UI PASS/exit0作为输入保留；另用三道新合成材料和新的状态做独立检查。

后端3组PASS：8种拒绝变体（bool/float坐标、越出原框、仍碰已保存peer、异页、错分区、缺完整性、混合移交）均保持head/job及SQLite字节不变；陈旧head拒绝。连续两次收窄保留完整两层原框历史与正文/识别/原图，旧成功peer不变；试图回扩至较早原框被拒绝；未确认无法构建新计划，重新确认后新框进入纯合成插入计划；UNKNOWN目标同样拒绝。

UI2组PASS：使用上述真实普通adapter输出的合成state，验证入口存在、未保存编辑阻止进入、异步旧图片回调被忽略、页/分区锁定、原预置不能直接提交、拖框取消旧勾选、完整性勾选必须显式给出、缩放后原像素坐标和请求身份准确；head变更后不再提交；已保存peer无文字调整按钮。仅模拟DOM和请求，不启动浏览器、HTTP服务器、平台或模型。

原GUI检查脚本先把原像素误当画布鼠标坐标，得到 `[49,267,402,335]`，与预期 `[48,260,390,325]` 不同而FAIL。原脚本、失败JSON与exit1保留；只新增按实际canvas缩放换算坐标的检查脚本，结果PASS，没有改产品或重跑后端成功组。初次误读REPORT.md、manifest evidence_files字段和证据日志目录的读取辅助错误也分别保留，不记作产品缺陷。

## 严格后继边界

作者固定 launch01 记录为 `PREFLIGHT_FAILED_NOT_ACTIVATED`、exit2，含原overlap错误及平台/模型0声明；本轮只核收原件，不重跑预检，也不将其算作新平台权限消耗。full16-ui-01 原重叠反例没有被本次代码验收自动关闭。

协调方随后说明实际普通UI首次调整Q7的y1311切掉首行约1像素，尚未确认，并将另固定Union15以允许在最初原框内微调。这条新实际观察不是本次14冻结输入的独立验证。本次14接受范围仍是“只能相对当前框继续收窄”；不把它当成最终Q7修复或新全16计划，不借它授权继续运行。

Union15只需针对新增差异续审；14已通过的有限项可按原始字节和依赖关系复用，不重跑。新实际head、完整计划与launch须另行核验。旧9题、已接受4题、原settings、耗尽轮次、FAIL/UNKNOWN和原失败证据继续保留。
