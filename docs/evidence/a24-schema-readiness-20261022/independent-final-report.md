# A24 schema-readiness v2 最终独立复审

## 结论

`PASS_BOUNDED_SCHEMA_READINESS_V2_LIVE_HOLD`

修订补丁 `c0b36d…` 在限定范围内通过独立复审。首版 `981c…` 仍为撤回件、不可发布。v2 已删除无真实格式依据的“每题必须有 frame”集合相等约束，同时保留总体空分母、已有 frame 引用现有题、规范身份和 identity projection 入口门。

当前仍为：

- `HOLD_REAL_SCHEMA_UNBOUND`
- `write_allowed=false`
- `successors=NOT_RUN`
- `schema_profile=None`
- `qualification=NOT_RUN`

本结论不是 live、写授权、平台、人工或官方验收。

## 固定补丁与实际运行字节

- v2 patch SHA-256：`c0b36d24cdd8c29ad1f02c4194cd445c1dda26b3300921c9b3f0589607d63f7c`
- v1 撤回 patch SHA-256：`981c4569354cefff1f318a54768242a9be53fec7fb5078eb036106d2eeca914f`

从原 v2-final effective tree 新建隔离副本，使用 `git -c core.autocrlf=false apply`。实际运行文件全部为 LF，原始 SHA 与作者固定值一致：

- wire：`64885d7ac5d91d5351231a803ffeab4badb1b55528057a6abde1c03ac6131116`
- quality：`ea23ffe0a9aa4d70d364d5404303d4254a2185b90df823c3ee5473da3d9045f7`
- schema_capture：`a599b347c7737cb17d633b032dfe8a62403a56c91952f539ae7d5c082e96abe9`
- focused tests：`7222f3121cb52282ce211f4c7dc03eebf198760b69991d31415ac7f689d47cdd`

没有使用 normalized SHA 冒充实际运行字节。

## 实际测试

| 组别 | 实跑 | 失败 | 错误 | 结果 |
|---|---:|---:|---:|---|
| 作者聚焦 schema-readiness | 14 | 0 | 0 | PASS |
| 独立入口与 codec 边界 | 9 | 0 | 0 | PASS |
| 首版受影响的 R1 定点用例 | 6 | 0 | 0 | PASS |
| 合计 | 29 | 0 | 0 | PASS |

独立9项通过真实 `check_input → UsenseTransport.bind → validate_profile` 验证：

- view 整体 literal/lookup、questions 容器 literal、directories array item lookup 均在读取前拒绝；
- direct identity container 与非身份 lookup 保持合法；
- 总体 questions/frames/content 全空被拒绝；
- 当总体仍有 frame 时，另一个题无 frame 被允许，确认首版业务假设已撤回；
- complete 与 natural 两种 codec 的 null、数字、带首尾空白题/框 ID 均拒绝；
- bind 入口 session calls 为 0。

独立测试工具 SHA-256：`9b8f279cc379e09d82311b14e5df457215e2113ec257366e2bb9a03f9be1537c`。

## R1 兼容性边界

我方定点重跑首版新增的六个 FAIL，结果 6/6 PASS，证明 v2 对相应产品回归已恢复。

完整 R1 20 项未在本成员重复运行。主审固定基线仍是 17 PASS、0 FAIL、3 个已知 ERROR：旧 `bootstrap_steps` 夹具、旧 reopen 外层证书、缺失 `D:/1800` 私有请求。不得据此声称 20/20 PASS，也无需修旧夹具或补造私有输入。

主审最终新目录回归共运行 55 项：新增14、controlled-capture 7、minimum-gate 10、book-snapshot 4 均全过；R1 为 17 PASS、0 FAIL、同3 ERROR。合计 52 PASS、0 FAIL、3 ERROR，命令退出码 1 被原始记录如实保留。该结果与原 R1 基线完全一致，证明 v2 没有留下首版的6个新增 FAIL，但仍不能描述为全绿。

## 仍然 OPEN

1. 两种 codec 仍接受 `parts=[{}]`。可在不猜字段名的前提下要求每个 part 字典非空，但内容真实性仍依赖 raw/state 证据。
2. `schema_capture` helper 先 resolve `output_root` 再检查 symlink/reparse；helper 单独使用时，词法根 alias 安全仍依赖上游 owner 路径验证。
3. 当前权威 catalog 全量成员集合；总体非空不等于完整。
4. snapshot question/frame/directory 的完整 raw-record extra 字段保全。
5. snapshot 与 export 的 state/version 等值绑定。
6. `source_refs/evidence_refs` 对受控字节的 SHA-256 绑定。
7. 当前真实字段路径、生产 adapter、六阶段读、保存回执及保存后 readback。

因此 v2 可以作为**有限 schema-readiness 加固**进入后续集成，但不能提升写资格或宣称旧题完整保全。

本次独立 v2 差量复审未发现既有 OPEN 之外的新产品阻断。
