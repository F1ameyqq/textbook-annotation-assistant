# A04 coordinate-R3：独立离线复验

2026-10-17。继续原独立验收对话，明确 `xhigh`。只审固定 R3 缺行 PNG 修复；整个 A04、真实 R01～R06 及 S01 仍未通过。本轮禁止真实平台、浏览器、网络、profile、凭据、OCR及模型动作，不重试此前 GET。

## 固定输入与前检

- 工作目录：`C:/Users/ASUS/.codex/worktrees/a04-headless-readonly/1800`。
- base：`76898657e76ac2db071327e90c6ca5031d17571f`。
- 实现：`81d62255b545b88f344849d08011a2a859c49c5e`。
- 冻结交付：`6c8137a4fadddc01a47906d564ab3460277c8958`。
- 报告：该提交 `docs/tasks/A04-coordinate-R3-execution-report.md`，SHA256 `9e80fb8e715da518b1e999c951b9798ad5cb0b7dbfc12c09d325ea0f5f850334`。
- 清单：`docs/evidence/A04/execution/coordinate-R3/sha256-manifest.json`，SHA256 `634c254021f91ec2f6ed2b0737a3b234f4fb382c4e8878490abedf3b428d1b92`，852项。
- 任务：[R3有界修复](A04-coordinate-R3-rework.md)；旧缺陷和判据：[R2独立报告](A04-coordinate-R2-review-report.md)、[调度重现](A04-coordinate-R2-coordinator-decision.md)。
- [主调度前检](../evidence/coordinator/heartbeat-20261017-0649/A04-delivery-preflight.json)核对852项磁盘/raw Git、清单自身、853处允许范围变化及干净工作树；完成回执与自有61个记录进程结束证据已核对。没有当前系统/profile扫描，也没有用这些证明功能已接受。

请从 exact Git bytes 隔离导出必要源码与输入；避免 checkout EOL 差异造成版本混淆，不读取浮动主树作为被验实现。原R1/R2报告、失败日志和主调度初次EOL预检失败均保留；D01无需重复验收。

## 有界验收要求

1. 先重放未改精确反例脚本：180字节/37×29 RGB8，仅一行112字节而完整应3248，SHA256 `205543876fb32bb14f003bfeec32279e9fd4886bd1949eee9810999e468969bd`。公共CLI应退出2且只含固定脱敏错误/字段；无历史写入与最终有效包。
2. 独立核对新 PNG 行布局/有界解压判据，并选不同尺寸/位深/Adam7 的代表反例、正确总量和正常边界。检查没有只针对一个尺寸/hash，正常空白图片不会被误拒；资源超限应在有界资源使用内拒绝。作者声明的30布局/150subtest只作覆盖线索，不能直接算独立通过。
3. 在解析后、发布前替换成同尺寸坏图，验证 `build_source` 也拒绝且不污染历史。正常PNG及现有JPEG/PGM经公共入口和含空格目录搬运，未改公共loader消费、原字节/格式/尺寸/hash及状态语义成立。
4. 记录支持组合、APNG/尾随内容等显式兼容收紧和未证明部分。检查必要相关回归；原Node deadline和Windows junction因Python-only边界未执行的项目诚实单列，不当作通过。禁止为消除这些skip启动浏览器/扩大边界。
5. 有确定缺口时保留最小反例及影响后冻结，不无限搜索新图片格式或重复跑整套测试。没有缺口则只对本次离线修复给范围清晰的结论；不得将原图修复等同于真实坐标、全书来源或整体A04通过。

## 输出和所有权

仅新增 `docs/tasks/A04-coordinate-R3-review-report.md`、`docs/evidence/A04/review/coordinate-R3/`。报告给精确版本、实际独立命令/导入位置/原始流/退出结果、可消费样例与统一清单、明确skip/限制和自有进程结束证明。主调度决定接受与集成；验收者不改产品、依赖、调度state、旧原件，不提交或推送，不联系执行者/B或其他chat。

结果分别记录 `OFFLINE_R3=ACCEPTED/REWORK/BLOCKED` 与 `A04_OVERALL=BLOCKED`。完成后结束等待，不自行释放真实平台或I01依赖。
