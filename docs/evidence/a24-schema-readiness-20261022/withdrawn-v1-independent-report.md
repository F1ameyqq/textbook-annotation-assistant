# A24 schema-readiness 固定补丁独立复审

> **撤回状态（2026-10-22）**：本报告审查的补丁 SHA `981c4569…` 已被主审撤回，当前结论为 `HOLD_PATCH_WITHDRAWN_PENDING_REVISION`。下述 14+9 聚焦结果、行尾事实和 OPEN 发现仍是有效历史证据，但不得作为该补丁可集成结论。

## 结论

`HOLD_PATCH_WITHDRAWN_PENDING_REVISION`

固定补丁在聚焦范围内曾通过：空/缩减分母、非规范身份、已知身份容器 literal/lookup 和 directory array item alias 已由真实 `check_input → UsenseTransport.bind → validate_profile` 入口阻断；合法的 direct identity container 与非身份 lookup 保持可用。

但主回归随后发现 `FRAME_QUESTION_DENOMINATOR` 把“每题必须至少有一个 frame”当成未知 schema 的业务事实：新增14项和既有 7+10+4 均通过，而 wire_r1 20 项出现 6 FAIL、3 ERROR。该约束属于过度收紧，作者已被要求移除；因此 SHA `981c…` 当前不可集成，必须等待修订后的新固定哈希重新审查。

### wire_r1 的真实兼容基线

原 v2-final 树的同一 20 项 R1 对照并非全绿，而是 **17 PASS、0 FAIL、3 ERROR**。三个既有 ERROR 已有主审证据：

1. 旧夹具缺少 `WindowsBackend.bootstrap_steps`；
2. 旧 reopen 夹具触发 `REOPEN_OUTER_CERTIFICATE_REQUIRED`；
3. `D:/1800` 所需私有请求不存在。

`981c…` 的实质新回归是额外出现 6 FAIL；原有 3 ERROR 不能归咎于本补丁，也不能被修订版报告成已经通过。最终修订验收边界应为：恢复 **0 个新 FAIL**，并只保留与基线完全相同的 3 个已知 ERROR。修旧夹具或补造私有请求不在本差量审查范围。

这不是整体保全 PASS。raw extra、权威 catalog、snapshot/export 状态绑定等仍为 OPEN，当前继续：

- `HOLD_REAL_SCHEMA_UNBOUND`
- `write_allowed=false`
- `successors=NOT_RUN`
- `schema_profile=None`
- `qualification=NOT_RUN`

## 补丁与行尾

- 补丁 SHA-256：`981c4569354cefff1f318a54768242a9be53fec7fb5078eb036106d2eeca914f`
- 四文件差量：wire、quality、schema_capture、新聚焦测试。

普通 `git apply` 在我方首个隔离副本中退出 0，但受全局 autocrlf 影响把四个补丁文件全部写为 CRLF。实际原始 SHA 为：

- wire：`6034437bae3461641c3aec476443b67c43c31d5814cc8d205b9cd3dfe8e33d0f`
- quality：`15e3364863586b6efc555f9e9a7fc7db51884f6ea3ae1e44ffdd656e8e451174`
- schema_capture：`ed0f0d81d9c92882c5f9ef69fa2fc95dfcf6a39886bb36af439ae29e166466e5`
- tests：`d9940c15f5d20b46b94b2898c1105def52d83693e8a2127c49adfa231d80a1a4`

该变体及其 14 项通过事实已保留，但不作为固定字节结论。随后另建 `source-lf`，使用 `git -c core.autocrlf=false apply`，四文件均为实际 LF 字节且 SHA 精确等于作者固定记录：

- wire：`64885d7ac5d91d5351231a803ffeab4badb1b55528057a6abde1c03ac6131116`
- quality：`f12582cf87b9f7c365de640e33d0948b1a0a6ae0c2e3443d3843439548816a89`
- schema_capture：`a599b347c7737cb17d633b032dfe8a62403a56c91952f539ae7d5c082e96abe9`
- tests：`941e3afb892a4cc9f256a2aed8bed1d994a8345249b13239beb7a750ad78510d`

以下结论均来自实际 LF 固定字节，不用 normalized SHA 冒充运行字节。

## 独立入口复验

作者新增 14 项在 LF 树上实跑：14/14 PASS，零失败、零错误。

另增加 9 项独立测试，实际通过：

1. `view` 整体 literal：真实 bind 入口拒绝，且未发起读请求。
2. `view` 整体 lookup：真实 bind 入口拒绝。
3. `questions` 身份容器 literal：真实 bind 入口拒绝。
4. `directories` array item lookup alias：真实 bind 入口拒绝。
5. 非身份 `platform_version` lookup：真实 bind 入口允许。
6. 整个 identity container 直接从命名响应复制：真实 bind 入口允许。
7. 空 questions/frames/content 与有题无 frame：分别拒绝。
8. complete codec 的 null、数字、带首尾空白题/框 ID：拒绝。
9. natural codec 的同类非法题/框 ID：拒绝。

所有 bind 级测试中 session calls 均为 0，说明是在读取前由 profile validation 阻断，而不是等到 helper 或真实 I/O 才失败。

独立测试工具 SHA-256：`477407d0fec75e73162b358f78512e01ca36c19140eac190b91178476254d67a`。

## 新确认的 OPEN

### `parts=[{}]` 仍可通过两种 codec

complete 与 natural decoder 都只要求 parts 数组非空且元素为字典，空字典仍被接受。这比原来的 `[None]` 更严格，但仍允许没有任何内容字段的 part 充当正文骨架。

不需要猜真实字段名即可做的最小补强是要求每个 part 字典本身非空。即使补上，它也不能替代 raw-record 与当前 state binding；因此本项只应关闭明显空对象，不应宣称内容真实性已证明。

### schema_capture 的 root alias 检查依赖上游

`load_current_schema_capture()` 先对 `output_root` 调用 `resolve()`，然后检查 resolved path 的 symlink/reparse 属性。这样 helper 自身不会检查调用者传入的词法根对象是不是 symlink/junction；安全性依赖 owner 先前已经验证该路径。

最小选择：在 resolve 前对 supplied root/private 做 `lstat` 检查，或让 helper 必须接收并验证上游 owner path-validation token。不能把当前 helper 单独描述成完整的 root anti-reparse 证明。

## 仍未关闭

- 当前 catalog 全量成员证明；非空不等于完整。
- snapshot question/frame/directory 的完整 raw-record extra 字段保全。
- complete `state_version` 与 natural `state_binding` 对同次 snapshot 的绑定。
- `source_refs/evidence_refs` 的实际 SHA-256 绑定。
- 当前真实字段路径、生产 adapter、六阶段读、保存回执和保存后 readback。
- live、平台、人工和官方验收。

因此该补丁当前已撤回、不可集成。修订版应保留总体空分母与规范 ID/identity projection 门，但移除“每题必须有 frame”的未知业务假设；随后同时复跑聚焦门，并将 wire_r1 与 **17 PASS、0 FAIL、3 个已知 ERROR** 的原始基线比较，不能伪称 20/20 PASS。无论修订结果如何，都不能据此提升写资格或宣称旧题完整保全。
