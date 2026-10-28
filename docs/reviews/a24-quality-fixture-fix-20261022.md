# A24 本机临时接管：独立质量与可移植性修复审计

日期：2026-10-22（Asia/Shanghai）
范围：固定 A 发布 `c5aefbc8e995c410b3babf74a251f05a7724a1c2`；共享 A24 副本与 B 仓库只读
最终判定：**测试夹具修复 PASS；真实首题保存仍 HOLD**

## 1. 结论摘要

| 项目 | 结论 |
|---|---|
| A 发布物静态完整性 | PASS：522 清单成员、111 个 `src/` 文件、81 个 Python AST 均独立核验通过 |
| controlled-capture 环境差异 | 已确认是 Windows 8.3 临时目录别名导致的路径身份失败；改用工作区规范长路径后 7/7 通过 |
| 路径保护是否放宽 | 否；产品 `owner.py` 未修改，发布 SHA 保持不变；错误/别名/reparse/marker 篡改负例仍通过 |
| first-save current-body 原测试 | 已保存原始结果：9 项中 8 通过、1 ERROR，错误为 `OWNER_CAPTURE_ALREADY_BOUND` |
| 测试夹具修复 | PASS：只修改 `tests/a24_first_save_current_body/test_minimum_gate.py`，产品改动 0 |
| 修复后定向回归 | 目标用例 1/1、相邻 owner-hash 负例 1/1、完整新套件 10/10 均通过 |
| 可移植冷安装 | 未证明；本机为 Python 3.12.14 / Pydantic 2.14.1 / Pillow 12.3.0，不等同 A 原 Python 3.9.13 / Playwright 1.58.0 |
| 真实平台就绪 | **否**；私有输入和新鲜 live authority 均缺失，实际保存/refresh/reopen 仍 NOT_RUN |

## 2. 固定发布物核验

独立从 `tree.json` 和发布 `manifest.json` 重算：

- 发布 commit：`c5aefbc8e995c410b3babf74a251f05a7724a1c2`
- manifest SHA-256：`a927a201988a277520275509791401e00cc45fdd9edcde140056bf85060633a9`
- 522/522 成员的字节数、SHA-256、Git blob SHA-1 和父 `tree.json` blob 身份一致
- `source_tree_paths`：111/111
- Python 源文件 AST：81/81
- 隔离 `source-original` 与清单原件逐字节一致

原 `selected` 目录当前另有一个未列入固定发布清单的 `docs/status/a.md`。本次重建基线时明确排除该文件，没有把它混入 522 成员发布物。

共享 B 仓库中指定基线 `b120a23d18c49fdb45f96703fc1b7aa51781a17a` 可解析为 commit。本审计没有写入共享 B 仓库；检查时共享仓库已有其他并行修改/未跟踪文件，未对其 reset、stash、清理或纳入本次补丁。

## 3. TEMP/TMP 环境修复没有削弱路径 guard

默认 `tempfile` 返回：

```text
C:\Users\LIHAOY~1\AppData\Local\Temp\...
```

而 `Path.resolve()` 返回：

```text
C:\Users\LIHAOYANG\AppData\Local\Temp\...
```

两者词法不相等。产品 `bind_capture_owner` 要求 `authority.output == authority.output.resolve()`，因此默认短别名被原有 `OWNER_CAPTURE_PATH` 规则拒绝。原报告在首个测试后有限停止：1 项运行、1 failure、后继 NOT_RUN。

把 `TEMP`/`TMP` 指向本审计工作区内的规范长路径后，临时路径与 resolved 路径完全相等，原产品代码直接得到 7/7：

- 实际资源：0
- 旧套件：0
- 模型/内容复核：0
- 错路径、词法别名、reparse、capture-owner marker 篡改等负例仍通过

产品 guard 文件未改：

- `src/annotation/runtime/live_pilot/owner.py`
- SHA-256：`fb5bcd815d075f425d97845da13b64c2e06f62ecb990f41924377dadea8aeaaf`

因此这是测试执行环境的路径规范化配置，不是放宽安全校验。

## 4. 原始 first-save 失败

长路径环境下运行原始 9 项：

- tests：9
- passed：false
- failures：0
- errors：1
- real resources：0
- old suites：0

唯一 ERROR 位于：

`EntryEvidenceTests.test_exact_navigation_timeout_step_and_close_failure_are_finite_without_retry`

旧夹具给 `owner.open` 注入了 `SimpleNamespace` guard 和模拟 framework；新增的 `bind_capture_owner` 在进入导航前检查 owner 身份与未绑定状态，因夹具缺少真实 owner hash/output 初态而先报：

```text
OWNER_CAPTURE_ALREADY_BOUND
```

所以原测试没有触及它真正想验证的 `page.goto()` → `TimeoutError`、有限 close、异常文本不外泄路径。这是过时测试夹具，不是产品回归。

## 5. 最小修复

只修改一个测试文件：

`tests/a24_first_save_current_body/test_minimum_gate.py`

修复内容：

1. 从固定发布中的 `tools/a16_current_state_probe.py` 加载真实冻结 framework；
2. 让 `make_first_save_guard` fixture 使用 `owner.open` 传入的真实 `OwnerGuard` 类，而非旧 `SimpleNamespace` guard；
3. 设置当前 authority 的真实 `owner_authority_hash` 和未绑定 `output=None`；
4. 由产品 `bind_capture_owner` 创建私有 `source-capture` 和 `capture-owner.json`；
5. 在预期 `TimeoutError` 后调用产品 `validate_capture_owner`，核对目录、marker 和完整 binding；
6. 保留原有有限导航/close 断言和私有异常文本不外泄断言；
7. 新增相邻负例：owner hash 不匹配必须在创建 `private` 目录前以 `OWNER_CAPTURE_ALREADY_BOUND` 拒绝，且不得写入 framework binding。

隔离差量核验：

- 变更清单成员：仅上述测试文件
- `src/` 产品改动：0
- 产品 guard 原 SHA：保持一致
- 补丁 `git apply --check`：PASS

## 6. 定向结果

| 运行 | 结果 |
|---|---|
| 原始 current-body 完整 9 项 | 8 通过、1 ERROR（保留） |
| 修复后 timeout 目标用例 | 1/1 PASS |
| 新增 owner-hash 相邻负例 | 1/1 PASS |
| 修复后 current-body 完整新套件 | 10/10 PASS |
| 修复后 controlled-capture | 7/7 PASS |

所有测试都是 `SYNTHETIC_ONLY`，实际资源为 0，没有 Playwright 真实浏览器、网站请求、OCR、模型、凭据、profile 或锁操作。

## 7. 仍然 HOLD 的真实交付条件

当前本机缺少 11 个必要私有对象：

- 三份 current-body 响应：`directory-snapshot.bin`、`frames-snapshot.bin`、`export-snapshot.bin`
- 原生题目请求：`request-accepted-content-v2.json`
- 六张裁片：`rect-0.jpg` 至 `rect-5.jpg`
- 已接受的 AI 校正候选：`reviewed-candidate-v1.json`

交接 index 中的原路径和 snapshot 路径在本机均不存在；私有字节未发布到 Git。除此之外：

- 所有旧 live 轮剩余额度为 0；不得继承 activation、claim、output 或窗口
- 新鲜 live authority：不存在
- 实际 save：NOT_RUN
- 实际 refresh：NOT_RUN
- 独立 fresh-context reopen：NOT_RUN

因此，7/7 和 10/10 只证明离线模拟及测试夹具正确，**不能**宣称平台就绪、保存可执行或首题已完成。恢复条件是受控取得并核哈希上述私有对象，再由接任调度建立明确的新鲜 prewrite/save/refresh/reopen authority；本审计未执行或授权该动作。

## 8. 交付物

- 机器回执：`outputs/a24-takeover-independent-audit-20261022.json`
- 原失败：`outputs/a24-first-save-current-body-original-failure-20261022.json`
- 修复后完整结果：`outputs/a24-first-save-current-body-fixed-final-20261022.json`
- controlled-capture 最终结果：`outputs/a24-controlled-capture-long-temp-fixed-20261022.json`
- 最小可应用补丁：`outputs/a24-first-save-current-body-test-fixture-20261022.patch`
- 可重跑静态审计器：`tools/a24_takeover_independent_audit.py`

共享 A24 副本与 B 仓库均未被本审计修改。
