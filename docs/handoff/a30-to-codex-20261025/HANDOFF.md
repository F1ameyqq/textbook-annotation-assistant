# A30 交接给 Codex（2026-10-25）

## 0. 一句话状态

书 `46007447`《名校课堂八年级数学上册》第 "2 一定是直角三角形吗" 小节的 16 题中，**11 题已正式/根接受**；Q12 平台保存 `UNKNOWN_NO_RETRY`（有 HTTP200 与回执，读回未完成）；Q13–16 在平台上已存在（orders 39–42）但来源未归因，**永不重发、永不覆盖**；full16 原生导出/展示 **NOT_RUN**；`customer_ready=false`；`1800-a` **PAUSED**。

下一步不是再跑一次平台，而是**离线构建**"采纳四个先存尾节点 + 用保留读回升级 Q12"，构建**尚未开始**（见 §4）。本交接只交 A30 客户流程的剩余工作，不等于全书完成。

## 1. 交接范围与身份

- 交接方：Claude Code 协调会话 `1800-39`（只做调度/根核验/收口，不写产品）。
- 接管方：Codex。接管后由 Codex 自行决定用几个会话执行/评审；**执行者不得自我接受**，独立评审与根接受必须分开。
- 全部输入都是文件，全部步骤都是命令/测试；不依赖任何 Claude 子会话的上下文（那些会话已被根在交接时停止或以 idle 结束）。

## 2. 业务状态

| 项 | 状态 |
|---|---|
| 小节题数 | 16 |
| 已正式接受 | 11（Q1 对账 + 打印 5/10/11 + 此前 4 题 + 旧 9 题中在本节的部分） |
| Q12 | `UNKNOWN_NO_RETRY`：原 POST HTTP200 有回执，节点 `1792848391723`，回执 info `2113985491617890305`；读回未完成 |
| Q13–16 | 平台存在 orders 39–42，无绑定保存回执，归因 `UNKNOWN` |
| full16 原生导出/展示 | `NOT_RUN` |
| `customer_ready` | `false` |
| `1800-a` 自动化 | `PAUSED` |

Q13–16 绑定值（根已从工作区字节复算，见 §6）：node/info/order/created_at 见 `STATE.json` → `business.q13_16.nodes`；逐区 `rect_id` 顺序由 `D:/1800-private/a30-root-20261025/print_tail_node_rect_ids.py`（只读）复现。

## 3. 已正式/根接受的事实（可直接依赖，不要重开）

1. **launch03-r1 实际运行已收口**：`docs/evidence/coordinator/a30-launch-r1-actual-closure/receipt.json`（`9b6a05a5…`，9147 B），状态 `ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY`；`root-index.json`（`a837dec0…`，57 成员）。
   - Hold 在 `native_plan.py:256`：`len(new_questions) == len(old_questions) + 1` 失败（42 vs 38），`book_id` 两侧一致；92.099 s，exit 2，spent 1/remaining 0，661 GET / 0 POST，9 分片 / 302 成员，`save_attempts: 0`，自有释放已证。
2. **比较器离线重建已接受**：`docs/evidence/coordinator/a30-launch-r1-actual-closure/addendum-receipt.json`（`19fe0c6f…`，4916 B）。
   - 仅移除 orders 39–42 的四个节点及其 15 个题框后，冻结源码的 `compare_readback` **PASS**：`old_questions_preserved=37`、`old_frames_preserved=125`、`new_node_id=1792848391723`、`new_info_id=2113985491617890305`、`readback_hash=cceb4298fb93bb8b4afd01c489bf4cdf7284bc52834594bb92dfc7a38094d449`、`native_clock_tolerance_seconds=5`、`runtime_actor_and_send_window_checked=true`。
   - 复核者与根**两次独立重建逐字段一致**；重建脚本无网络/浏览器/子进程引用。
   - 该补充**不**等于 Q12 业务接受，不授权重发/补对账/新运行。
3. **v1.1.4 客户包离线接受**（`docs/evidence/coordinator/a30-release-v114-independent-closure/receipt.json`，`d15ff82e…`）——离线接受，实际打包启动仍未作为客户交付验证。
4. `docs/coordination-state.json` 为当前权威状态（`STATE.json` 记录了它的交接时 sha）。

## 4. 剩余工作（按顺序，五步）

### Step 1 —— 离线构建（**未开始**）

任务书：`docs/tasks/A30-preexisting-tail-nodes-adoption-and-q12-retained-upgrade-20261025.md`
（sha256 `3132a89043f1dc6c0a9af9036d897d5cdd5ba0924353aafc4d44ab2d876fe5bd`，17357 B）

该任务书包含六项产品增量、冻结包成员清单、全部绑定值、Q13–16 全 UUID 表、测试要求、禁止事项。六项增量摘要：

1. `compare_readback` 增加**绑定式** `preexisting_extras` 剪除（缺省 `None`，行为与旧版逐字节等价；只有调用方显式传入四个绑定 node_id 才剪；同时要求 `order_in_level` 大于新题 order、`created_at` 在原发送窗口（±5 s 容差）之外、四个 node_id 互不相同）。
2. 新 op kind `reconcile-retained`：只读绑定 capture group `native/008bb17292dd4399a4d8e9d3f3351470`（9 runs / 302 成员），key `digest([identity, previous['output'], 'retained-upgrade:1'])`，**零平台调用**，一次性；失败写 `FAILED_NO_RETRY` 且原 save op 仍为 `UNKNOWN_NO_RETRY`。
3. `existing_candidate` 的 `rect_id` 比较改为**候选顺序**（`image_order_in_annotation_zone`），其余校验（`ocr_result` 全文、分区 success、未覆盖分区 absent、`bound_frames` 几何/地址）**不变**。这一项修 Q15（数组顺序 `b945fc57, df78ab22, e4f9448a, e9bdfd9a, f72e1317` vs 候选顺序 `b945fc57, e9bdfd9a, e4f9448a`）。
4. `existing_fill.make/compare` 同一不变量（按 `image_order_in_annotation_zone` 升序，0..n-1 全排列校验）。
5. `_execution_plan` 支持 `ADOPT_EXISTING_MATCH`（只校验后返回 `None`，`produce` 允许 `None` 且采纳后 `pending` 为空）。
6. 新冻结包 `D:/1800-private/a30-adoption-completion-launch-fixed-20261025-01`，`--preflight` 只读。

产物应落在：
- 产品新修订 `D:/1800-private/a30-integrated-flow-r1-fixed-20261025-01`
- 构建报告 `D:/1800-private/a30-adoption-completion-build-20261025-01/`（`REPORT.md`、`build-report.json`、`manifest.json`、`raw/`）

> 交接时状态：Claude 执行者两次 `API Error: 402 Insufficient Balance`，恢复后运行约两小时**零文件产出**，根已在交接时将其停止。因此上述三个目录目前**都不存在**，构建按"未开始"处理。

### Step 2 —— 独立代码评审

任务书：`docs/tasks/A30-adoption-completion-code-review-20261025.md`（九项强制核验；`actual_run_authorized` 必须为 `false`，`customer_ready` 必须为 `false`）。
评审产物：`D:/1800-private/a30-adoption-completion-code-review-20261025-01/` + 公开版 `docs/evidence/A30/review/adoption-completion-code-01/REVIEW.md`。

### Step 3 —— 根绑定唯一 actual 授权

评审 `ACCEPTED_OFFLINE_CODE_AND_PACKAGE` 后，由根（Codex 的协调层）绑定**一条**唯一 authority，写进 `docs/coordination-state.json` 与私有 authority JSON。必须复用的绑定值：

| 绑定 | 值 |
|---|---|
| 工作区 | `D:/1800-private/a30-continuation-live-20261024-01/workspace` |
| head | `28274dab55969aa33d365ee2e4078c6ad58593929b589aa2a7581a3de20b1abc` |
| settings | `56f07eb98e9712b662a13b016d9758c3d2c12109421a7b1f557a972e2b565f5f` |
| 操作数 | 86（其中 12 条 save op） |
| Q12 save key | `56232bbf755aaf07…`（`UNKNOWN_NO_RETRY`，不得改写） |
| Q12 reconcile key | `d779d3db6997363af73144a23b74ac02529d433bcadd16ff7e86ec602dde07db`（`FAILED_NO_RETRY`，不得改写） |
| 保留 capture group | `native/008bb17292dd4399a4d8e9d3f3351470`（9 runs / 302 成员） |
| Q13–16 | orders 39/40/41/42，node 见 STATE.json，仍为平台既有、不得覆盖 |

`limits` 必须含：`save_posts_max: 0`、`native_exports_max: 1`、`local_display_max: 1`、`official_bound_crop_downloads_max: 11`、`platform_contexts_max: 59`、`business_get_responses_max: 2997`、`readonly_reconcile_calls_max: 0`、`retained_reconcile_calls_max: 1`、`automatic_retries: 0`、OCR/公式/付费模型/登录/重发均为 0。

> 说明：虽然只有 4 个待采纳项，`produce` 仍会做**整书只读 capture**（launch03-r1 实测 9 个分片上下文、661 GET），`finish()` 还要 1 次原生导出上下文、1 次本地展示上下文，交付时最多 11 次绑定图下载；因此上下文/GET/图下载预算必须沿用已接受的 full-run 值，写小了会在预算处 Hold 掉一次性 actual。

窗口 1800 s + 60 s 释放宽限；单次 launch intent；不重试。

### Step 4 —— 一次 actual

固定 launcher 一次：`reconcile_retained`（0 平台调用）→ 校验 → `produce`（`ADOPT_EXISTING_MATCH`，0 POST）→ 校验 16 条 acceptance → 1 次原生导出（GET）→ 1 次本地展示 → 自有释放。任一校验失败即 Hold 且不继续。

### Step 5 —— 独立 actual 评审 + 根接受

评审实际结果 → 根接受 → 再决定 `customer_ready` 与 v1.1.x 客户包。在此之前 `customer_ready=false`、`1800-a` PAUSED。

## 5. 环境

- Python：`D:/1800/.local/stages/a30-customer-independent-20261024/runtime-support/venv-customer-py312/Scripts/python.exe`（3.12.14，Playwright 1.58 / Pillow 11.3 / greenlet 3.5.6）。
- 一次性启动器：`app/tools/run_usense_owned.py`（嵌套 Windows Job，发布原始 stdout/stderr 与进程身份）。
- 产品基线（diff 用）：`D:/1800-private/a30-integrated-flow-r1-fixed-20261024-20`（manifest `19a3497ef23fa8e128d88b286f65267c5291a674ffe6fa0c68b07e34c6ad817a`，249 源文件）。
- 平台 profile：专用 Edge profile；**凭据/profile 内容不得输出、不得入库**，`.local/` 不入 git。

## 6. 产物索引

`docs/handoff/a30-to-codex-20261025/STATE.json` 是机器可读的权威索引（每个成员带 sha256/bytes，私有目录带文件数与总字节）。交接时生成，`missing_private` 里只有三个"尚未构建"的目录——这是预期，不是丢失。

关键公开文件：

| 路径 | sha256（前 16） | 字节 |
|---|---|---|
| `docs/evidence/coordinator/a30-launch-r1-actual-closure/receipt.json` | `9b6a05a5d1eaff1c` | 9147 |
| `docs/evidence/coordinator/a30-launch-r1-actual-closure/root-index.json` | `a837dec0938ed717` | 12205 |
| `docs/evidence/coordinator/a30-launch-r1-actual-closure/addendum-receipt.json` | `19fe0c6f282d5ba0` | 4916 |
| `docs/evidence/A30/review/launch-r1-actual-01/REVIEW.md` | `570e42e3e449699f` | 6731 |
| `docs/tasks/A30-preexisting-tail-nodes-adoption-and-q12-retained-upgrade-20261025.md` | `3132a89043f1dc6c` | 17357 |
| `docs/tasks/A30-adoption-completion-code-review-20261025.md` | 见 STATE.json | 6800+ |

私有（`D:/1800-private/`）：执行者报告、复核目录、authority、根核验报告、Q13–16 分析、冻结包、live 目录、产品 v1.1.4、工作区。

## 7. 红线（违反即作废）

1. 永不重发 Q12、Q13–16（这五个 key 不得再出现 save POST）。
2. 永不覆盖/删除四个先存尾节点。
3. 不重放已接受的 11 次保存、旧九题、OCR、公式/模型调用、登录、已花额度。
4. 不提交书籍、不对外发布。
5. 凭据与 profile 内容不入库、不打印；`.local/` 不进 git。
6. `1800-a` 保持 PAUSED，直到另有一次明确决定。
7. 证书忽略只在明确授权的单次运行内使用，永不成为默认。
8. 不提交 A03 长路径删除与无关脏文件。

## 8. 已知缺陷与限制（如实保留，不要"洗白"）

- 执行者 `RUN.md` 把 reconcile key 抄错（只有 20 位前缀正确，真实值为 §4 Step 3 表中那条）。
- 复核者 manifest 漏列自己的 `decision.json`/`REVIEW.md`。
- `decision-addendum.json` 的 `results.uncleaned_compare_at_line_256.message` 是乱码；同一 Hold 文本在收口报告、output blob `521de423…`、公开 `REVIEW.md` 中均正确，无实质影响。
- 公开 `REVIEW.md` 在收口后被追加：收口时 `732570e9…`/4440 B，现 `570e42e3…`/6731 B；原文保留，收口报告与 root-index 未被改写。
- 评审独立性限制：同模型家族、新会话；原 Codex 复核不可用；不要把它说成外部独立。
- 内容正确性：更早的视觉抽查为 6 一致 / 6 错误 / 4 不完整（样本），不是 16 题全部正确。
- Q12 的"清理后比较通过"是**离线重建**，不是平台再次读回。

## 9. 交接时根做了什么（可复核）

- 生成 `STATE.json`（只读扫描公开与私有产物，重算 sha）。
- 停止空闲的 Claude 执行者（约 2 小时零产出），未产生任何产品/包。
- 未连平台、未写工作区、未改产品、未生成 ZIP。

## 10. 建议的接管第一步

1. 读本文件与 `STATE.json`，确认 `missing_private` 与 §4 Step 1 描述一致。
2. 读两份任务书（构建 + 评审）。
3. 用 Codex 自己的会话完成 Step 1，然后按 Step 2–5 推进；每一步落盘报告/哈希，根接受与执行分离。
