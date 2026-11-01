# A24 schema readiness 修订固定版（v2）

## 结论

**HOLD_REAL_SCHEMA_UNBOUND**

首版补丁 `981c4569354cefff1f318a54768242a9be53fec7fb5078eb036106d2eeca914f` 已保留，未覆盖。修订版撤回了没有真实格式依据的“每个旧题必须至少有一个 frame”约束。

当前仍固定为：

- `write_allowed=false`
- `successors=NOT_RUN`
- `schema_profile=None`
- `qualification=NOT_RUN`

## 回归根因与产品修复

主会话首版集成回执：

`C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\a24-takeover-20261022\schema-readiness-main\regression.json`

其中新增 14 + 7 + 10 + 4 共 35 项通过；旧 R1 20 项出现 6 FAIL + 3 ERROR。6 个 FAIL 的共同产品回归是新增 `FRAME_QUESTION_DENOMINATOR`：它要求 frame 所属题集合与全部题集合完全相等，从“总体旧数据分母不得全空”越界推断成“每题必须有 frame”。

v2 做了以下修正：

- 删除题集合与 frame 所属题集合完全相等的门；
- 保留总体 questions、frames、question_content 非空的 `EMPTY_TARGET_DENOMINATOR`；
- 保留每个已有 frame 必须引用现有题的 `FRAME_QUESTION_IDENTITY`；
- 保留 question/frame/directory ID 的非空、无首尾空白字符串规则；
- 把新增测试中的“题目无 frame 必须拒绝”改成正向兼容控制，确认这种状态不会被臆造为非法。

没有改旧 R1 期望来追求测试通过，也没有放宽总体空分母或 frame 引用不存在题的门。

## v2 验证

### 新增聚焦套件

- 14/14 PASS
- 用时 0.307s
- 退出码 0

其中正向控制明确验证：总体仍有 frame 时，另一个题没有 frame，`global_order()` 正常返回最大题序。

### 首版受影响的旧 R1 定点用例

定点重跑回执中 6 个首版 FAIL：

- receipt extra / private intent
- bad receipt / no resend
- query redaction / journal
- native upload ACK
- HTTP 403 burn
- owner async adapter / page IO / outer close

结果：

- 6/6 PASS
- 用时 3.191s
- 退出码 0

这证明首版 6 个行为回归已由产品约束修正，而不是通过修改旧测试期望隐藏。

### 原固定树 R1 对照限制

固定原基线：

`C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\a24-takeover-20261022\offline-final-main-review\effective`

主会话对照记录：

`C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\a24-takeover-20261022\schema-readiness-main\baseline-r1-controls.json`

原固定树 R1 实际结果是 20 项中：

- 17 PASS
- 0 FAIL
- 3 ERROR
- 记录时长 63516ms

三个原有 ERROR 是：

1. 旧 `WindowsBackend.bootstrap_steps` 夹具缺字段；
2. 旧独立 reopen 夹具缺 `REOPEN_OUTER_CERTIFICATE_REQUIRED` 所需外层证书；
3. 缺少私有输入 `D:\1800\.local\stages\a24-first-save-r1-inputs\author-content-v1\request-accepted-content-v2.json`。

v2 不修这三个旧夹具/私有输入问题、不修改对应期望，也不宣称“全 R1 通过”。

## 补丁完整性

v2 补丁对上述固定原基线执行：

```powershell
git apply --check --whitespace=error-all a24-schema-readiness-v2.patch
```

结果：退出码 0。

- v2 补丁 SHA-256：`c0b36d24cdd8c29ad1f02c4194cd445c1dda26b3300921c9b3f0589607d63f7c`
- 首版补丁仍为：`981c4569354cefff1f318a54768242a9be53fec7fb5078eb036106d2eeca914f`

修订隔离文件哈希：

- `wire.py`：`64885d7ac5d91d5351231a803ffeab4badb1b55528057a6abde1c03ac6131116`
- `quality/live_pilot.py`：`ea23ffe0a9aa4d70d364d5404303d4254a2185b90df823c3ee5473da3d9045f7`
- `schema_capture.py`：`a599b347c7737cb17d633b032dfe8a62403a56c91952f539ae7d5c082e96abe9`
- 聚焦测试：`7222f3121cb52282ce211f4c7dc03eebf198760b69991d31415ac7f689d47cdd`

固定原基线复核：

- `wire.py`：`e89057ecdcdcb4878c22138b6de99a47dcd621bb2ce52c938d6fcc83f1a88d08`
- `quality/live_pilot.py`：`6b5b9362bfab4879f8b2b676028848b3f7009fb3cf825ea7ba9dccc722d6ace6`

## 仍为 OPEN

本次修订只撤回过度业务假设，不改变以下阻断项：

- declarative snapshot 对完整 raw extra 的保全；
- 当前权威 catalog 成员全集；
- snapshot 与 export 的 state/version 等值绑定；
- source/evidence ref 与受控捕获字节的 SHA-256 绑定；
- 六阶段读取、保存回执和保存后回读的真实端点覆盖；
- 已知身份路径以外的完整身份安全证明。

没有使用浏览器、网络、DeepSeek、外部 API 或 live authority；没有修改共享 B `2e43bcb`。

