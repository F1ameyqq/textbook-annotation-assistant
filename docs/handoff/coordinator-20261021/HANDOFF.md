# D:/1800 A 侧调度交接

2026-10-21，Asia/Shanghai。用户因原对话上下文过长，准备由新对话接任。项目未完成；交接不新增平台、模型或写入权限。本文优先于历史心跳中的旧状态，实际 JSON、固定 Git/raw 和接任时的新线程快照优先于本文的时间快照。

## 先读这几个入口

1. 本文与同目录 `PROMPT.md`。
2. 根 `AGENTS.md`、`docs/coordination.md`、`docs/development-plan.md` 的最新段落，以及 `docs/coordination-state.json` 中 `tasks.A24`、`coordinator_handoff`、`automation`。无需先重读所有历史失败。
3. `docs/tasks/A24-first-save-wire-fixed-independent-review.md` 和 `docs/evidence/coordinator/a24-first-save-wire-delivery/`。
4. 同目录 `thread-snapshot.json`、`fixed-input-index.json`、`preexisting-worktree-status.json`。以登记 cursor 获取新快照；不要读取活动作者或验收目录。

## 调度所有权交接

- 原调度：`01a15768-1e2d-7781-b29f-1f7376270216`。新调度 ID 尚未产生，不把原 ID 当作自己。
- 原调度完成交接后停止新业务派发；**已运行的独立验收继续完成，不打断或重复创建**。
- 唯一自动化 `1800-a` 暂停等待接任，保留 ID、不删除、不新建。工具暂停回执及磁盘核对见 `automation-pause-receipt.json`。
- 接任者先确认自己的实际 threadId 与 host，登记到 `docs/coordination-state.json` 的 `coordinator_thread_id` / `coordinator_handoff.successor_thread_id`，把交接状态改为 `TAKEN_OVER`，记录接任时间和来源；先完成这次登记再恢复调度。
- 然后通过 `automation_update` 更新**同一个** `1800-a` 的 `targetThreadId` 为新调度、`status=ACTIVE`。保留名称、通知偏好与实际周期，不另建 cron/heartbeat。暂停时 TOML 实际为 50 分钟，旧 JSON 写 30 分钟，原因未知；迁移已明确记下差异，不能把旧 JSON 当成实际配置。
- 新旧调度不得并行派发。若接任时已有其他 successor 已登记，先核所有权，不能覆盖抢占。
- 原对话停留在交接，不自动恢复平台工作。恢复的是调度；不会恢复任何已耗尽 live 或写入额度。

## 当前完成到了哪里

**真实当前书源已经读取并正式独立/调度接受；首题真实保存尚未执行。**

书 `46007447`，214 页，121 个目录项、22 个题节点、68 个框。A24 `current-context-r1` 的 book/directory/frames/source/page14/page173 六逻辑 JSON 槽和两张原图完成；来源明确 `LEGACY_DB`。正式结果为 `ACCEPTED_FIXED_CURRENT_SOURCE_READ_WITH_GAPS_AND_OWN_RELEASE_ONLY`，不是生产或首题保存验收。

- 实际冻结 final：`dceda09db31487d64654e23dd36ccd3705c740fc`。
- 根接受 commit：`97b6f8e0afe6c7db1ded99caca11a4cbc968373c`。
- 根证据：`docs/evidence/coordinator/a24-current-context-r1-live-independent-closure/`，8 报告成员+self、92 输入；机器报告 SHA `f27fcc1bf7e0f9dc82d2b4b7038781f513665ee6ae843f96f15bd3ea16e6e0fa`。
- 正文/全旧正文保全、最终 save-page 和合法新增、实际保存仍未证明。目录及框计数一致不等于全正文完整。
- A24 原始只读轮和修订只读轮都已用完；不能重开 output、activation、claim 或清理标记。A03-A23 的旧轮/旧 suite 按历史记录保持，不重跑求 PASS。

## 现在要接住的两个正式聊天

| 职责 | threadId | 当前状态和工作区 |
|---|---|---|
| 执行 | `01a15cf8-0c63-70d3-b374-ce85e6f29fd7` | 首题 wire 已固定释放；`D:/1800-worktrees/a24-first-save`，分支 `codex/a24-first-save` |
| 独立验收 | `01a15cf8-68e0-7b63-91a3-657a567b344c` | 首题 wire 独立验收正在运行；冻结隔离 `D:/1800-worktrees/a24-first-save-wire-review` |

均为 `hostId=local`，沿用当前模型及 `thinking=xhigh`。同 A24 后续继续这两个正式聊天，不建新诊断阶段，不拿辅助子代理替代正式验收。用户已授权 A 侧必要派发及同阶段继续；B/外部联系人消息和推送没有授权。

作者最后 cursor：`0d524930-f946-4765-8053-ad5865e326fb:27`，turn `01a15d91-c5cd-7f51-88f1-a9472969e9f5`，completed `1792576197`。正式释放、无保留资源。

验收最新时间快照及 cursor 以同目录 `thread-snapshot.json` 和根 JSON 为准。交接准备时 cursor `9962b7f7-cacc-4c19-9a31-45759f3976b5:13`，turn `01a15de7-19a9-7351-8a9d-5ebe47caa458`，仍 ACTIVE。验收已报告新 45 Python / 8 JS fake 通过，但一个独立纯内存反例 1 FAIL：正常 synthetic 保存结束后，commit 回应中的未批准字段原样进入 event-000004.json，失败原件保留，后续控制停止。验收正在准备 REWORK，集中两项最小修正：接通真实 owner/激活/新 guard/外层释放入口；收紧 journal 的回执与敏感查询记录边界。schema、裁片和保全等实际输入另列待绑定。**目前仍是活动中的结果预告，不是已固定释放的最终报告，不读取活动输出或提前派修订。**

## 首题代码冻结身份

- Base：`dceda09db31487d64654e23dd36ccd3705c740fc`。
- Product：`851cf6fce217df8f64a6f3bdeaa99b5e5e2c234d`。
- Final：`680bd5f624659f1091db974d5ed30b332ff946dc`。直接 base -> product -> final。
- Candidate：`docs/evidence/A24/first-save-wire/candidate-manifest.json`，SHA `ac9573448692f313076a02489a9727cb9131040e22a6c55e5797c11a3e01cf19`。
- **权威**交付：`delivery-final-manifest.json`，SHA `03366e94a4b7d3672322839f5581a118c26190df3d5274b41bcd73fa0cb382d1`。同目录旧 `delivery-manifest.json` 是首次包装失败证据，不能用它接收。
- Root input：`docs/evidence/coordinator/a24-first-save-wire-delivery/input-raw-manifest.json`，SHA `165b840054cc18ecaaa1cc89f17c3678c3450f26c842509351a4a78d2cba0326`。
- 根已核 92 依赖、144 交付成员+self、225 去重 raw；32459 旧成员仅四获准产品修改，32455 其余及 31188 旧 evidence mode/type/blob 保持，141 新增、0 删除。
- 新/改产品为 `delivery/live_pilot/{plan,usense,wire}.py`、`quality/live_pilot.py`、`runtime/live_pilot/runner.py`。既有 journal/native/readonly/auth/OS 释放保持。
- 原作者和 raw 的 45 Python / 8 JS 是作者证据，独立结论尚待固定。首次 CRLF fixture、asyncio self-pipe、JS checkout/raw 摘要和打包错误均已保留，不改旧报告、不重跑旧 suite。
- 派验收 workflow `e0bcd85ec419a69d492aebac918917401fef5926`；接单登记 commit `3ab2d67efcf31a1b6b4ef52beca6fdf7b5b2f05e`。派发意图及 ACK 已落盘，不重复派。

冻结代码有页面内 fetch/FormData、async PLATFORM runner、单 intent/claim 下签名/六裁片/commit、严格回执和 get/refresh/reopen 比较。**实际 owner 启动集成与实际 schema/保全/裁片/预算未绑定的缺口仍须解决。**不能把可注入适配器或 fake 成功直接当作真实可运行命令。

## 接任第一步和后续顺序

1. 用 `wait_threads(timeoutMs:0)` 对原独立 ID、host=local、最新 `afterCursor` 取紧凑快照并存 cursor。仍在运行就不重复派发、不读取输出；可同时做已授权的静态准备。
2. 独立固定报告/机器结果/完整清单/释放到达后，机械核 raw 与输入保全，再按实际结果收口。若 REWORK，先封存实际报告，一次集中给原作者最小实质修正；正常新离线迭代允许，旧失败留存，不人为“一候选一次测试”。同独立验差量，不拆新 A25 诊断。
3. 在同 A24 补齐真实 owner/guard/runner 接线与首题完整计划。防止写错题、覆盖旧数据、重复提交、伪回执/读回；正确停止且原件完整的格式/报告差异列限制，不为此反复修订。
4. 集中计划应把新鲜 book/directory/frames 与一次自然聚合正文验证、当前 schema/合法新增/最终裁片/签名 host-policy-expiry/完整写集/精准次数一起固定。聚合若不能证明全部旧题五 zone 的完整语义及稳定身份，就不能冒称保全；不对 Q22 另抽样或重放。
5. 实现、具体计划和有限独立/根核证完成后，按用户已明确“尽快首题保存和读回”的指令落实实际首题 authority/activation。不要泛泛重新询问平台许可；只有真正新增的未授权边界，才在完整具体方案就绪后问。不能借用旧只读 activation 直接切写。
6. 作者 save + fresh get + refresh，释放后原独立 fresh context reopen 核正文、六框与旧数据保全；首题过后总量最多 5 题。保存 UNKNOWN 时只读对账，绝不重发或清锁。

当前 `activation-request-plan.json` 仍为提案：签名 GET <=1、六对象上传 POST <=6、commit POST <=1；其 32 个业务 GET / 1 签名 / 7 POST 是待集中优化和冻结的提案，不是现成批准。bootstrap/session/static/refresh 的实际槽须一起固定，不能用不完整计划上线。

## 首题和原图

候选仍为书 46007447 第2节《一定是直角三角形吗》基础印刷1，四组三边 `1,2,3 / 2,3,4 / 3,4,5 / 4,5,6`，答案页已目视本节 `1.C`。Q/W/W/W/W/A 六区域，普通单选 `xuanze`，leaf `dir-1792063578574-g0n3ulsni`。

计划在全局尾 after22 新增、不改旧题序，23 仅期待值，必须采用真实服务端回执；不静默插到旧印刷5之前，不换题，不沿旧 A07/Q1 批准。候选区域无已观测框相交，**不等于无正文重复或已证明未录入**。

原图仅在受控 `.local`，不重新下载或复制 Git：

- `D:/1800/.local/stages/a24-current-context-r1-live/original-viewer-14.jpg`，1218x1694，396099 bytes，SHA `4186d57ffad14f576fe7c967c96697d25c83ffe3512217c79b8371134181c1d9`。
- `D:/1800/.local/stages/a24-current-context-r1-live/original-viewer-173.jpg`，1148x1621，428192 bytes，SHA `a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be`。
- 原响应 resource index 分别13/172，提案 savepage 为14/173；二者不是同一语义。准确 bbox/文字见 `docs/evidence/coordinator/a24-first-save-source-plan/candidate-source-draft.json`。
- 最终六个 JPEG crop bytes 尚未生成/验收，上传前需绑定准确字节、像素、尺寸/hash、对象 key 和目视结果。完整原图不能冒充新裁片。

## 权限、保留物与用户偏好

- 截止仍 **2026-10-22 晚**，不因换对话重起算。用户多次要求加速、可激进、同阶段集中完成；只处理实质缺口，不串行堆叠诊断和元数据等待。
- 既有平台连接、测试书、普通浏览器和 Work 开关已确认，不重问、不循环 MCP 握手。
- A17 用户“一直批准”的同类专用 context 临时 TLS 只读许可在 `docs/approvals/A17-excluded-static-user-decision.json`，SHA `f5ceacf9028f773ead882f3e6601004c2c3e28171be31abb85c5be99a1d67b46`。不扩大成登录、写入、新来源或全局/默认证书忽略。A20/A21 一次登录批准已消费。
- 原 profile 非敏感指纹 `b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00`。保留 Edge/profile；不读用户名密码配置、不登录/refresh-token/自动重发，不换 profile、复制/注入 token、批量 kill 或清锁。
- 旧原件、失败、UNKNOWN、耗尽额度全部保留。三持有创建身份进程/两 Job/context/runtime 有限释放与 launcher 自身 OS 身份 UNKNOWN 分开；不为历史计时、stdout 或报告限制重跑。
- Q22 不导航/样题/重放；自然全书保全快照应包含旧 Q22，不能删。其他三例 HOLD。无书级送审/送交。
- 根工作区预存 87 个 dirty/untracked 项，见清单；不能 reset/clean/stash/全量 add。当前根分支是调度材料分支，产品应从固定 Git/raw 或原作者 worktree 读取，不能误将根旧 checkout 当最新产品。
- Git 每条设 `GIT_NO_LAZY_FETCH=1` 且 `git -c core.longpaths=true`。用 raw blob，不将 Windows CRLF checkout 当原 bytes。UTF-8 用 apply_patch/write_bytes；Python3.9 无 tomllib，元数据脚本尽量 ASCII。仅明确路径 staging。

## 模型与 B 侧并行准备

首题当前固定内容保存测试不调用模型。模型接入准备与保存验收并行，不能等整个保存阶段结束才开始，也不能把人工整理内容算作模型实际输出。

现有 B 固定 head `6d3d29f16e20f1521a3ff17239ce2830bec903c3` 已接收22份非 ZIP raw。报告含普通文字 RapidOCR 1.4.4 / PP-OCRv4 det+rec / v2 cls、本地 CPU，以及独立公式后端。不是当前新题已实际跑模型的证明。ZIP/部分本地 blob 未取得是 A 接收缺口，不说 B 未交；不盲重试获取或跑 B 脚本。

已静态读 `tools/route_c_ocr.py`、`src/annotation/recognition/baseline.py`；后者默认 `use_ocr=False`，产出 EvidenceBundleTrial，明确非 QuestionGraph/已核题答。`pipeline.py` 和 `tools/run_pipeline_b.py` tree 可见但 blob 本地不可得。本次模型调用0。

`docs/tasks/A-B-model-e2e-minimum-handoff-2026-10-21.md` 已将交接缩为：指出既有版本/一题入口；一题实际输出（若 A 能跑则由 A 生成）；影响本题的关键缺口。已有证据复用、消费者转换优先 A 承担，不要求重做五套材料、整章或复杂公式。文档 LOCAL_DRAFT / NOT_SENT / NOT_PUSHED，不擅发 B 消息。当前没有固定模型实际运行的新预算。

## 必要工具与文件

- 紧凑跟踪：`wait_threads`，同 ID/host/cursor，先 `timeoutMs:0`；不要反复 `read_thread` 大量历史。
- 根已准备 raw 机械核工具 `.local/stages/coordinator/a24-actual-intake-preparation/intake_fixed.py` 和 `dispatch_review.py`。可读取复用 `tree`、`BlobBatch` 等工具函数，**不能执行历史 main**，其中历史 identity 固定。新回执 schema 必须先核。
- 当前 intake helper：`.local/stages/coordinator/a24-first-save-wire-intake.py` 已运行一次；输出隔离已存在，不再次执行覆盖。
- 正式验收交付只在隔离 `docs/evidence/A24/independent-first-save-wire-review/`，未固定释放前不读。
- `fixed-input-index.json` 只登记固定关键文件，不是实际写入许可。`handoff-verification.json` 只验证交接完整性，不是产品独立验收。

交接完成后，旧调度不再派业务。新对话按上面顺序取得当前实际状态，然后继续同 A24。
