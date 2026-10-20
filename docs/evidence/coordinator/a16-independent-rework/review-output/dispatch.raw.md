# A16 固定离线交付独立验收派发

2026-10-20。沿用正式独立对话 `01a15841-0d44-7272-9740-40d013839869`，不新建阶段或恢复旧额度。作者已固定交付并释放；本次只有离线验收，0 live。

- 执行任务：[A16 当前书籍、源目标、接口和首题准备](A16-current-book-source-target-readonly.md)，SHA256 `d472860d3699acc3f2629abbb104c595c0adbf4a33bd59bc481caf21e34eeda2`。
- 独立任务：[A16 独立验收](A16-independent-current-readonly-review.md)，SHA256 `86a696c1085fc6dedef6c3c64d03e0ca2ee467434058db06a17e16ff8e958e54`。
- base `7432122b9fd5602785ebfb2b3f24e407fdf76eda`；产品 `2a604c2d0b0f7781ec0d7ca4b5925ae9ff53b595`；final `4fe417d5246f20fbbbedc577495c7ca400d4ded8`。
- 交付清单 SHA256 `41d965083d188f7021cb1e64b9d9a98c2b97541aa31f5d39e267b1ff228f7ca1`；候选 SHA256 `2579b043d65e665263796d0922f080ad101f4d20c1e9ea500fd7894ba41d966c`。
- 调度机械预检：[raw-preflight.json](../evidence/coordinator/a16-author-delivery/raw-preflight.json)。47 新路径均在白名单，31,259 旧成员 mode/type/blob 保全；作者最新结果 33/33 PASS、516ms，未作独立语义接受。
- 隔离输入 `D:/1800-worktrees/a16-independent-fixed`：47 个新增 raw 加候选引用的 2 个固定 A15 native 支持文件，共 49。均从 final Git blob 导出，不能从 Windows 普通检出替换。

独立使用原准备目录 `D:/1800-worktrees/a16-review-preparation` 的固定检查标准和历史证据；不再读取作者工作目录。正式报告、自编独立离线测试及结果只新增在隔离目录的 `docs/evidence/A16/independent-offline-review/`。如运行作者的新 A16 合成 suite，唯一初次复现输出可用 `docs/evidence/A16/current-readonly/test-runs/independent-01/`，不得覆盖 run01–run09 或冻结成员。默认静态 launcher 可核候选，不能传 live 或激活参数。

按预备的 48 项逐项说明实际证据和未覆盖部分，不以测试数量代替检查。只运行相关 A16 纯离线验证；不得运行旧 suite、浏览器、网络、profile/凭据、native 真实 API、占用扫描。产品缺口报告 REWORK，不改产品；若自编验收工具需修正，可在本阶段新增文件与失败证据，避免无理由重复已通过测试。

重点核对：A16 与 A15 权限隔离及严格 TLS 默认；白名单 GET 每项一次；预期被动资源拒绝不能掩盖后续致命失败；缓存复用必须来自已捕获的同一响应；源图身份和 UI 页映射；正文与 rect_ids/顺序绑定；FULL 库存和 PARTIAL/UNKNOWN 正文严格分开；Q22 排除样题但保留库存；DOM 异步后终态守卫、各进程本地时基和精确自有释放。固定源码中的运行时调用链须完整检查，不能用测试桩通过替代真实路径已接线。

保留 run01/run05 只有重构失败摘要、完整 traceback 在原聊天的限制；保留 CRLF/LF 机械发现和原候选清单。新 native 副本应与固定 A15 Git 原字节相同，不调用旧入口。候选六框是历史草稿，不能批准新题或标 READY。

交付独立报告、实际结果/发现、raw 清单、输入保全与释放。报告明确 `task=A16`、候选摘要及有限结论；仅确实通过时可写 `result=ACCEPTED_OFFLINE_ONLY`。离线通过也不激活 live；本阶段的具体 TLS 决定和调度激活仍待后续，首题保存与刷新重开读回仍 NOT_RUN。
